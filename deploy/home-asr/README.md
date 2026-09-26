# Home speech service (Mac mini)

The deployed app sends each spoken answer to TalTech's Voxtral Realtime on an
always-on Mac, and to Workers AI Whisper whenever that Mac does not answer
within 25 seconds. On the owner's voice Voxtral misheard 7% of words, Whisper
36% (`docs/asr-evaluation.md`). The Mac is never on the public Internet: the
Worker reaches it through a Cloudflare Tunnel bound as a **Workers VPC
Service** (free on every Workers plan while in beta).

```
phone / laptop ─▶ Worker ─(VPC Service → Tunnel)─▶ Mac mini :8790  eesti.asrserver
                     └── fallback ─▶ Workers AI Whisper
```

## 1. Create the tunnel (Cloudflare dashboard, once)

1. Open **Workers & Pages → VPC → Tunnels → Create**
   (<https://dash.cloudflare.com/?to=/:account/workers/vpc/tunnels>).
2. Name it `eesti-home-asr` and select **Save tunnel**.
3. Choose **macOS**. Copy only the long **token** from the install command it
   shows (the part after `--token`). Do not run the dashboard's own command.
4. Note the **Tunnel ID** (shown in the tunnel list).

## 2. Set up the Mac mini (once)

Needs [Homebrew](https://brew.sh). In Terminal on the Mac mini:

```bash
git clone https://github.com/wimpex18/Eesti-Keelt.git ~/Eesti-Keelt
cd ~/Eesti-Keelt && zsh deploy/home-asr/install.sh <token-from-step-1>
```

It installs everything, downloads the 8.9 GB model, starts the speech service
and the tunnel, and makes both start again after a restart. At the end it
prints the **service secret**. In **System Settings → Energy**, turn on
**Prevent automatic sleeping when the display is off**.

## 3. Point the Worker at it (once, on the computer with the repo)

```bash
npx wrangler vpc service create eesti-home-asr --type http --tunnel-id <tunnel-id> --ipv4 127.0.0.1 --http-port 8790
npx wrangler secret put HOME_ASR_TOKEN
```

The first prints a **service ID**; the second asks for the service secret from
step 2. Add the service ID to `wrangler.jsonc`:

```jsonc
"vpc_services": [{ "binding": "HOME_ASR", "service_id": "<service-id>", "remote": true }]
```

Commit it; the `deploy` workflow updates the Worker. The speaking page then
says **"Сейчас тебя слушает твой Mac mini"**, or that Cloudflare is listening
when the Mac is off.

## Updating and checking

- Update: `cd ~/Eesti-Keelt && git pull && zsh deploy/home-asr/install.sh <token>`.
- Health on the Mac mini: `curl http://127.0.0.1:8790/health`.
- Logs: `~/.eesti-home-asr/asr.log` and `tunnel.log`.
- Stop: `launchctl bootout gui/$(id -u)/ee.eesti-keelt.home-asr` (and `home-tunnel`).

Recordings are held in memory for one request and never written to disk on
the Mac. The service listens on 127.0.0.1 only and refuses a recording without
the service secret.
