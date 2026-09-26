#!/bin/zsh
# One-time setup of the home speech service on an always-on Mac.
#
#   zsh deploy/home-asr/install.sh <cloudflare-tunnel-token>
#
# Run from the app's folder (a git clone, or GitHub's "Download ZIP" unpacked).
# No Homebrew needed. It picks the engine by processor:
#   Apple silicon -> Voxtral Realtime on the GPU (8.9 GB)
#   Intel         -> TalTech Whisper et-verbatim on the CPU (1.6 GB)
# and registers two launchd services that start at login and restart if they
# stop: the speech service (127.0.0.1:8790) and the Cloudflare Tunnel that lets
# the Worker reach it. Re-running it is safe. See deploy/home-asr/README.md.
set -euo pipefail

TUNNEL_TOKEN="${1:-}"
if [[ -z "$TUNNEL_TOKEN" ]]; then
  echo "Usage: zsh deploy/home-asr/install.sh <cloudflare-tunnel-token>" >&2
  echo "The token is shown when you create the tunnel (README.md, step A)." >&2
  exit 1
fi
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
STATE="$HOME/.eesti-home-asr"
AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$STATE/bin" "$AGENTS"
cd "$REPO"
ARCH="$(uname -m)"

# uv (Python and packages) from its official installer, into ~/.local/bin.
if ! command -v uv >/dev/null && [[ ! -x "$HOME/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"

# cloudflared from Cloudflare's own GitHub release for this processor.
if [[ ! -x "$STATE/bin/cloudflared" ]]; then
  kind=$([[ "$ARCH" == arm64 ]] && echo arm64 || echo amd64)
  curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-$kind.tgz" \
    | tar -xz -C "$STATE/bin"
  chmod +x "$STATE/bin/cloudflared"
fi

echo "Installing the speech service's Python environment ..."
"$UV" venv -q --allow-existing --python 3.12 "$STATE/venv"
PY="$STATE/venv/bin/python"
if [[ "$ARCH" == arm64 ]]; then
  "$UV" pip install -q --python "$PY" fastapi uvicorn certifi huggingface_hub \
    -r requirements-local-asr.txt
  REPO_ID="TalTechNLP/Voxtral-Mini-4B-Realtime-estonian-2609"; PATTERN="model.safetensors *.json"
else
  "$UV" pip install -q --python "$PY" fastapi uvicorn certifi faster-whisper "tokenizers>=0.22"
  REPO_ID="TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604"; PATTERN="ct2/*"
fi

echo "Downloading $REPO_ID (resumes if interrupted) ..."
MODEL="$(HF_HUB_DISABLE_XET=1 "$PY" -c "
import sys
from huggingface_hub import snapshot_download
print(snapshot_download(sys.argv[1], allow_patterns=sys.argv[2].split()))" "$REPO_ID" "$PATTERN")"
if [[ "$ARCH" == arm64 ]]; then
  ENGINE_ENV="VOXTRAL_RT_MODEL=\"$MODEL\" ASR_REFERENCE_MODEL="
else
  ENGINE_ENV="ASR_REFERENCE_MODEL=\"$MODEL/ct2\" VOXTRAL_RT_MODEL="
fi

# The secret the Worker sends with every recording; made once, kept here.
if [[ ! -s "$STATE/token" ]]; then
  "$PY" -c "import secrets; print(secrets.token_urlsafe(32))" > "$STATE/token"
  chmod 600 "$STATE/token"
fi
print -r -- "$TUNNEL_TOKEN" > "$STATE/tunnel-token"; chmod 600 "$STATE/tunnel-token"

cat > "$STATE/run-asr.sh" <<RUN
#!/bin/zsh
export $ENGINE_ENV HF_HUB_OFFLINE=1 PYTHONPATH="$REPO"
export HOME_ASR_TOKEN="\$(cat "$STATE/token")"
cd "$REPO" && exec "$PY" -m uvicorn eesti.asrserver:app --host 127.0.0.1 --port 8790
RUN
cat > "$STATE/run-tunnel.sh" <<RUN
#!/bin/zsh
exec "$STATE/bin/cloudflared" tunnel --no-autoupdate run --token "\$(cat "$STATE/tunnel-token")"
RUN
chmod 700 "$STATE/run-asr.sh" "$STATE/run-tunnel.sh"

if [[ -n "${EESTI_HOME_ASR_DRY_RUN:-}" ]]; then   # tests: no launchd, run the service once
  ( "$STATE/run-asr.sh" > "$STATE/asr.log" 2>&1 & )
else
for name in asr tunnel; do
  label="ee.eesti-keelt.home-$name"
  cat > "$AGENTS/$label.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key><array><string>$STATE/run-$name.sh</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$STATE/$name.log</string>
  <key>StandardErrorPath</key><string>$STATE/$name.log</string>
</dict></plist>
PLIST
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$AGENTS/$label.plist"
done
fi

echo "Waiting for the model to load ..."
for i in {1..90}; do
  if curl -fs http://127.0.0.1:8790/health | grep -q '"ok":true'; then break; fi
  sleep 2
done
curl -s http://127.0.0.1:8790/health; echo
echo
echo "Service secret (for the Worker's HOME_ASR_TOKEN): $(cat "$STATE/token")"
echo "Keep this Mac awake: System Settings > Energy > Prevent automatic sleeping."
