"""Operating the thing: the error log, the content push, and the server.

`push-content` and the state snapshot are the two halves of "Cloud Run scales
to zero and its disk goes with it".
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ._helpers import _row_of

def cmd_verify_backup(args: argparse.Namespace) -> int:
    import json

    from ..recovery import verify_export

    print(json.dumps(verify_export(Path(args.file)), indent=2))
    return 0


def cmd_notion(args: argparse.Namespace) -> int:
    """Review queued errors and, only with `--push`, send them to the `Vead` log.

    Dry-run by default: the log is curated (three rows sharing a tag set the week's
    focus), so nothing is sent without a decision.
    """
    from ..notion import connect, mark_pushed, pending, push

    from ..config import NOTION_DB

    conn = connect(NOTION_DB)
    rows = pending(conn)
    if not rows:
        print("Nothing queued.")
        return 0

    print(f"{len(rows)} correction(s) queued for the Vead log:\n")
    for row in rows:
        print(f"  [{row['tag']}] {row['wrong']}  ->  {row['correct']}")
        if row["why"]:
            print(f"      {row['why'][:100]}")
        print(f"      {row['on_date']}")

    if not args.push:
        print("\nNothing was sent. Re-run with --push to write these to Notion.")
        return 0

    sent = failed = 0
    for row in rows:
        ok, detail = push(
            _row_of(row), token=os.environ.get("NOTION_TOKEN")
        )
        if ok:
            mark_pushed(conn, row["id"])
            sent += 1
        else:
            failed += 1
            print(f"  kept queued: {row['wrong']} — {detail}")
    print(f"\n{sent} pushed, {failed} still queued.")
    return 1 if failed else 0


def cmd_push_content(args: argparse.Namespace) -> int:
    """Send the harvested library to the deployment, once.

    The corpus is owner-only (so not in the image) and Cloud Run's disk is
    ephemeral, so the Worker keeps it and restores it to each fresh container. The
    target is the Cloud Run origin (guarded by `PROXY_TOKEN`), since a script cannot
    pass Cloudflare Access. Tokens come from the environment, never arguments.
    """
    import base64
    import json
    import os
    import urllib.error
    import urllib.request

    from .. import config

    token = os.environ.get("STATE_TOKEN")
    proxy = os.environ.get("PROXY_TOKEN")
    if not (token and proxy):
        print("STATE_TOKEN and PROXY_TOKEN must both be set. They are the "
              "values the deployment already holds -- deploy/push-content.sh "
              "reads them out of Cloud Run for you, so you never handle them.")
        return 2

    path = Path(args.database or config.CONTENT_DB)
    if not path.exists():
        print(f"{path} does not exist. Run `harvest` and `harvest-reading` first.")
        return 2

    from ..sources import connect as content_connect
    from ..topiclinks import rebuild
    from ..wordlist import available, connect as wordlist_connect

    with content_connect(path) as conn:
        items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    if not items:
        print(f"{path} holds no items. Nothing to push.")
        return 2
    if not available():
        print("The word list is missing. Run `python -m eesti.cli build` before "
              "pushing: topic links must be rebuilt against the current corpus.")
        return 2
    # Rebuild even when the count is non-zero: old links say nothing about newly
    # harvested texts. Only this local publication step pays for morphology.
    with content_connect(path) as conn, wordlist_connect() as words:
        counts = rebuild(conn, words)
        links = sum(counts.values())
    print(f"  rebuilt {links} topic links")
    if not links:
        print(f"  WARNING: {path} has {items} items but no topic links. "
              "No texts met the topic's evidence threshold; review the corpus "
              "with `python -m eesti.cli link-topics`.")

    payload = json.dumps(
        {"database": base64.b64encode(path.read_bytes()).decode("ascii")}
    ).encode("utf-8")
    print(f"pushing {path} — {items} items, {len(payload) / 1e6:.1f} MB encoded")

    request = urllib.request.Request(
        args.url.rstrip("/") + "/api/content/import",
        data=payload,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-state-token": token,
            "x-proxy-token": proxy,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            print("stored:", response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"refused: {exc.code} {exc.read().decode('utf-8', 'replace')[:200]}")
        return 1
    except (urllib.error.URLError, OSError) as exc:
        print(f"unreachable: {exc}")
        return 1

    print("The Worker will archive it on its next look, and every container "
          "after that starts with it.")
    return 0


def cmd_push_keys(args: argparse.Namespace) -> int:
    """Make the VAPID key pair reminders are signed with, once.

    The private key never appears on screen: it is written into the git-ignored
    `.env`, and `deploy/set-push-keys.sh` reads it from there into the Worker's
    secrets. Only the public key is printed, because the browser is given it
    anyway.
    """
    from ..env import ENV_FILE, load
    from ..vapid import generate

    load()
    existing = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    if "VAPID_PRIVATE_KEY=" in existing and not args.force:
        print(f"{ENV_FILE} already holds a VAPID key pair. Replacing it would "
              "silence every browser already subscribed; pass --force if that "
              "is what you want.")
        return 2

    public, private = generate()
    subject = args.subject or "mailto:none@example.org"

    kept = [line for line in existing.splitlines()
            if not line.startswith(("VAPID_PUBLIC_KEY=", "VAPID_PRIVATE_KEY=",
                                    "VAPID_SUBJECT="))]
    kept += [f"VAPID_PUBLIC_KEY={public}", f"VAPID_PRIVATE_KEY={private}",
             f"VAPID_SUBJECT={subject}"]
    ENV_FILE.write_text("\n".join(kept).strip() + "\n", encoding="utf-8")
    ENV_FILE.chmod(0o600)

    print(f"written to {ENV_FILE} (private key not shown)")
    print(f"  VAPID_PUBLIC_KEY={public}")
    print(f"  VAPID_SUBJECT={subject}")
    print("\nNext: bash deploy/set-push-keys.sh   (in Cloud Shell, with .env)")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .. import config
    from ..wordlist import available

    # Refuse to serve without a word list that has rows (`available`, not `exists`):
    # an empty file would serve the app with no lexicon and no message.
    if not available(config.DB_PATH):
        print("No database yet — run `python -m eesti.cli build` first.", file=sys.stderr)
        return 1
    uvicorn.run("eesti.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def cmd_asr_serve(args: argparse.Namespace) -> int:
    """The home speech service (`eesti/asrserver.py`) for the Worker's tunnel."""
    import os

    import uvicorn

    missing = [n for n in ("HOME_ASR_TOKEN",) if not os.environ.get(n)]
    if not (os.environ.get("VOXTRAL_RT_MODEL") or os.environ.get("ASR_REFERENCE_MODEL")):
        missing.append("VOXTRAL_RT_MODEL or ASR_REFERENCE_MODEL")
    if missing:
        print(f"Set {', '.join(missing)} first (deploy/home-asr/README.md).", file=sys.stderr)
        return 1
    uvicorn.run("eesti.asrserver:app", host=args.host, port=args.port)
    return 0


def register(sub) -> None:
    """Register this group's commands beside their handlers."""
    p = sub.add_parser("verify-backup", help="replay a private event export in temporary stores")
    p.add_argument("file")
    p.set_defaults(func=cmd_verify_backup)

    p = sub.add_parser(
        "notion",
        help="review queued errors; --push writes them to the Vead log",
    )
    p.add_argument("--push", action="store_true",
                   help="actually send them (needs NOTION_TOKEN)")
    p.set_defaults(func=cmd_notion)

    p = sub.add_parser(
        "push-content",
        help="send the harvested library to the deployment (needs STATE_TOKEN)",
    )
    p.add_argument("--url", required=True,
                   help="the Cloud Run URL, not the Worker's — see the docstring")
    p.add_argument("--database", help="defaults to the configured content database")
    p.set_defaults(func=cmd_push_content)

    p = sub.add_parser("push-keys",
                       help="make the VAPID key pair reminders are signed with")
    p.add_argument("--subject", help="mailto: the push service can complain to")
    p.add_argument("--force", action="store_true",
                   help="replace an existing pair (silences current subscribers)")
    p.set_defaults(func=cmd_push_keys)

    p = sub.add_parser("asr-serve",
                       help="home speech service: Voxtral for the deployed app, via a tunnel")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8790)
    p.set_defaults(func=cmd_asr_serve)

    p = sub.add_parser("serve", help="run the local web app")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=cmd_serve)
