#!/bin/zsh
# One-time setup of the home speech service on an always-on Mac (Mac mini).
#
#   git clone https://github.com/wimpex18/Eesti-Keelt.git ~/Eesti-Keelt
#   cd ~/Eesti-Keelt && zsh deploy/home-asr/install.sh <cloudflare-tunnel-token>
#
# It installs uv, cloudflared and the speech libraries, downloads TalTech's
# Voxtral Realtime model (8.9 GB), and registers two launchd services that start
# at login and restart if they stop: the speech service (127.0.0.1:8790) and the
# Cloudflare Tunnel that lets the Worker reach it. Re-running it is safe.
# See deploy/home-asr/README.md for the Cloudflare side.
set -euo pipefail

TUNNEL_TOKEN="${1:-}"
if [[ -z "$TUNNEL_TOKEN" ]]; then
  echo "Usage: zsh deploy/home-asr/install.sh <cloudflare-tunnel-token>" >&2
  echo "The token is shown when you create the tunnel (README.md, step 1)." >&2
  exit 1
fi
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
STATE="$HOME/.eesti-home-asr"
AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$STATE" "$AGENTS"
cd "$REPO"

command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh" >&2; exit 1; }
command -v uv >/dev/null || brew install uv
command -v cloudflared >/dev/null || brew install cloudflared

echo "Installing the speech service's Python environment ..."
uv venv -q --allow-existing --python 3.13 .venv-asr
uv pip install -q --python .venv-asr/bin/python -r requirements.txt \
  -r requirements-local-asr.txt huggingface_hub

echo "Downloading Voxtral Realtime Estonian (8.9 GB; resumes if interrupted) ..."
MODEL="$(HF_HUB_DISABLE_XET=1 .venv-asr/bin/python -c "
from huggingface_hub import snapshot_download
print(snapshot_download('TalTechNLP/Voxtral-Mini-4B-Realtime-estonian-2609',
      allow_patterns=['model.safetensors', '*.json']))")"

# The secret the Worker sends with every recording; made once, kept here.
if [[ ! -s "$STATE/token" ]]; then
  .venv-asr/bin/python -c "import secrets; print(secrets.token_urlsafe(32))" > "$STATE/token"
  chmod 600 "$STATE/token"
fi
print -r -- "$TUNNEL_TOKEN" > "$STATE/tunnel-token"; chmod 600 "$STATE/tunnel-token"

cat > "$STATE/run-asr.sh" <<RUN
#!/bin/zsh
export VOXTRAL_RT_MODEL="$MODEL" HF_HUB_OFFLINE=1
export HOME_ASR_TOKEN="\$(cat "$STATE/token")"
cd "$REPO" && exec .venv-asr/bin/python -m eesti.cli asr-serve --port 8790
RUN
cat > "$STATE/run-tunnel.sh" <<RUN
#!/bin/zsh
exec "$(command -v cloudflared)" tunnel --no-autoupdate run --token "\$(cat "$STATE/tunnel-token")"
RUN
chmod 700 "$STATE/run-asr.sh" "$STATE/run-tunnel.sh"

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

echo "Waiting for the model to load ..."
for i in {1..60}; do
  if curl -fs http://127.0.0.1:8790/health | grep -q '"ok":true'; then break; fi
  sleep 5
done
curl -s http://127.0.0.1:8790/health; echo
echo
echo "Done. Last step, on the computer with the repo and wrangler (README.md, step 3):"
echo "  npx wrangler secret put HOME_ASR_TOKEN    # paste: $(cat "$STATE/token")"
echo "Keep this Mac awake: System Settings > Energy > Prevent automatic sleeping."
