"""Command line entry points.

    python -m eesti.cli fetch-data    # download the word list (one time, ~82 MB)
    python -m eesti.cli build         # import + index object cases
    python -m eesti.cli drill -n 10   # practise in the terminal
    python -m eesti.cli check "..."   # grammar check a sentence
    python -m eesti.cli serve         # local web app
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

from .config import DB_PATH, LEVELS, RAW

WORDLIST_BASE = (
    "https://raw.githubusercontent.com/KristjanPikhof/"
    "Estonian-Wordlist-Enriched-Ekilex/main/data"
)
# Only the small CEFR/frequency table is needed. The 79 MB inflected-forms file
# is deliberately skipped: its form lists are de-duplicated, so position cannot
# be mapped to a case. Vabamorf synthesis supplies labelled forms instead.
WORDLIST_FILES = ("est_words_160k.tsv",)


def cmd_fetch_data(args: argparse.Namespace) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for name in WORDLIST_FILES:
        dest = RAW / name
        if dest.exists() and not args.force:
            print(f"  {name}: already present ({dest.stat().st_size:,} bytes)")
            continue
        print(f"  {name}: downloading...", flush=True)
        urllib.request.urlretrieve(f"{WORDLIST_BASE}/{name}", dest)
        print(f"  {name}: {dest.stat().st_size:,} bytes")
    print("Source: Estonian-Wordlist-Enriched-Ekilex (CC-BY-SA-4.0), from Ekilex/EKI.")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    from .wordlist import build, connect, index_object_cases

    conn = connect()
    print(f"Importing word list into {DB_PATH} ...")
    print(f"  {build(conn):,} words")
    print("Indexing object cases with Vabamorf (genitive vs partitive) ...")
    stats = index_object_cases(conn, levels=tuple(args.levels))
    print(
        f"  checked={stats['checked']} indexed={stats['indexed']} "
        f"unknown={stats['unknown']}"
    )
    total = conn.execute(
        "SELECT COUNT(*) FROM object_cases WHERE distinct_=1"
    ).fetchone()[0]
    print(f"  {total:,} nouns have a distinct genitive/partitive — these are drillable.")
    return 0


def cmd_drill(args: argparse.Namespace) -> int:
    from .drills import generate
    from .wordlist import connect

    drills = generate(
        connect(), count=args.count, levels=tuple(args.levels),
        rules=tuple(args.rules) if args.rules else None, seed=args.seed,
    )
    right = 0
    for i, d in enumerate(drills, 1):
        print(f"\n[{i}/{len(drills)}]  {d.prompt}")
        print(f"        ({d.lemma}, {d.level or '-'})")
        try:
            given = input("        > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped.")
            break
        if d.check(given):
            right += 1
            print("        ✓ õige!")
        else:
            print(f"        ✗ {d.answer}   (не {d.distractor})")
            print(f"        {d.why_ru}")
    print(f"\n{right}/{len(drills)} correct.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    from .providers import grammar

    result = grammar.check(args.text)
    print(f"engine: {result.engine}{'  (degraded)' if result.degraded else ''}")
    if result.note:
        print(f"note  : {result.note}")
    if not result.corrections:
        print("Kõik on õige — no corrections.")
    for c in result.corrections:
        arrow = f" -> {c.correct}" if c.correct else ""
        print(f"\n  [{c.tag}] {c.wrong}{arrow}\n      {c.why}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    if not Path(DB_PATH).exists():
        print("No database yet — run `python -m eesti.cli build` first.", file=sys.stderr)
        return 1
    uvicorn.run("eesti.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eesti", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch-data", help="download the word list")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_fetch_data)

    p = sub.add_parser("build", help="import and index")
    p.add_argument("--levels", nargs="+", default=list(LEVELS))
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("drill", help="practise object case")
    p.add_argument("-n", "--count", type=int, default=10)
    p.add_argument("--levels", nargs="+", default=list(LEVELS))
    p.add_argument("--rules", nargs="+", help="completed | ongoing | negation")
    p.add_argument("--seed", type=int)
    p.set_defaults(func=cmd_drill)

    p = sub.add_parser("check", help="grammar-check a sentence")
    p.add_argument("text")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("serve", help="run the local web app")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
