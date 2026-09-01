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

def cmd_notion(args: argparse.Namespace) -> int:
    """Review queued errors and, only if asked, push them to the `Vead` log.

    Dry-run by default, and that is the whole design. The Notion log's value is
    that it is curated -- three rows sharing a tag become the focus of the week,
    and that rule is what identified `obj-case` in the first place. A checker
    that appended every suspicion would turn a hand-picked record into a dump of
    model output and start the rule firing on noise.

    So: this prints what would be sent. `--push` sends it.
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

    The corpus cannot ride along in the image: ERR transcripts are © ERR and
    Selges keeles carries no reuse grant, so putting them inside an image built
    from a public repository would be redistribution. And Cloud Run's disk is
    ephemeral, so copying the file in by hand lasts until the next cold start.

    So it goes where the learner's progress already goes -- held by the Worker,
    pushed into each fresh container. Harvest on a laptop, push once, and no
    deploy ever re-scrapes anyone's server again.

    The target is the **Cloud Run origin**, not the Worker. Cloudflare Access
    guards the Worker and Access is an interactive login, which a script cannot
    satisfy; the origin is guarded by `PROXY_TOKEN`, which a script can send.
    The Worker archives the corpus from there on its next look, so this survives
    the cold start that wipes the disk.

    Both tokens are read from the environment rather than taken as arguments, so
    they stay out of shell history and out of the process table.
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

    with content_connect(path) as conn:
        items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        links = conn.execute("SELECT COUNT(*) FROM topic_items").fetchone()[0]
    if not items:
        print(f"{path} holds no items. Nothing to push.")
        return 2
    # The same "count the rows" check the line above makes, applied to the
    # other table that has to be populated for the corpus to do its job.
    #
    # `topic_items` is what `topiclinks.related()` reads, and `/api/practice`
    # returns it as the `reading` beside every drill -- "the join that makes
    # practice and the reading library one tool". Nothing fills it except
    # `cli link-topics`, run by hand: no harvest calls it and no deploy step
    # does, so a freshly harvested corpus pushes with the table empty, the
    # drill's `reading` list comes back `[]`, and nothing anywhere says why.
    #
    # A warning and not a refusal: the texts are worth serving on their own,
    # and a corpus whose linking genuinely found nothing is a legitimate state.
    if not links:
        print(f"  WARNING: {path} has {items} items but no topic links, so no "
              "drill will offer anything to read.\n"
              "           Run `python -m eesti.cli link-topics` and push again.")

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


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .. import config
    from ..wordlist import available

    # Two separate lessons in one line.
    #
    # `config.DB_PATH`, read here rather than a bare `DB_PATH`. The bare name
    # was never imported into `cli.py`, so the one command every document in
    # this repository tells you to run -- `python -m eesti.cli serve` -- raised
    # `NameError: name 'DB_PATH' is not defined` before it reached uvicorn.
    # Nothing caught it: `--help` proves the parser, and `serve` is the one
    # command the read-only smoke list cannot run because it blocks.
    #
    # And `available`, not `exists`. This guard exists to stop the app starting
    # against nothing, and existence is exactly the check an empty word list
    # defeats: `cli status` before `cli build` used to leave one behind, and
    # then this passed and served the whole app with a zero-word lexicon --
    # every drill empty, every lookup missing, and no message anywhere.
    if not available(config.DB_PATH):
        print("No database yet — run `python -m eesti.cli build` first.", file=sys.stderr)
        return 1
    uvicorn.run("eesti.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def register(sub) -> None:
    """Add this group's commands to the subparser table.

    Beside the handlers rather than a thousand lines away in one
    argparse block: a flag and the code that reads it drift apart
    when they cannot be seen together.
    """
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

    p = sub.add_parser("serve", help="run the local web app")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=cmd_serve)
