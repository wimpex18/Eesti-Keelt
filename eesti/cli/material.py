"""The material pipeline (ADR-0009): schema, gates, blind check, build, statistics.

    cli material schema                 # the JSON Schema a draft must meet
    cli material check DRAFT...         # the deterministic gates, in order
    cli material blind DRAFT...         # Haiku 5.5 answers blind (Batches API);
                                        # what passes goes to content/material/checked/
    cli material build                  # checked/ → data/material.db, re-checked
    cli material stats                  # answers, reports and retired items
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._helpers import words_db


def _words(args):
    from .. import config

    return words_db(getattr(args, "words_db", None) or config.DB_PATH)


def _root(args) -> Path | None:
    return Path(args.root) if getattr(args, "root", None) else None


def _check_all(paths: list[str], words) -> list[tuple[Path, object]]:
    """Gate every draft, printing what each gate said; (path, report) of those that pass."""
    from ..material import gates

    passed = []
    for name in paths:
        path = Path(name)
        material, report, schema = gates.check_text(path.read_text(encoding="utf-8"), words)
        print(f"{path}:")
        if schema:
            for finding in schema:
                print(f"  FAIL {finding}")
            continue
        for finding in report.failures:
            print(f"  FAIL {finding}")
        for finding in report.dropped:
            print(f"  drop {finding}")
        kept = f"{len(report.questions)} questions, {len(report.gaps)} gaps kept"
        print(f"  {'pass' if report.passed else 'fail'}: {kept}")
        if report.passed:
            passed.append((path, report))
    return passed


def cmd_material_schema(args: argparse.Namespace) -> int:
    """Print the JSON Schema a draft is held to."""
    from ..material.schema import json_schema

    print(json.dumps(json_schema(), ensure_ascii=False, indent=2))
    return 0


def cmd_material_check(args: argparse.Namespace) -> int:
    """Run the deterministic gates; exit 1 when any draft fails."""
    words = _words(args)
    if words is None:
        return 1
    passed = _check_all(args.drafts, words)
    return 0 if len(passed) == len(args.drafts) else 1


def cmd_material_blind(args: argparse.Namespace) -> int:
    """Gate, ask Haiku 5.5 blind through the Batches API, keep and write what passes."""
    from ..material import blind, gates, store
    from ..providers import claude

    words = _words(args)
    if words is None:
        return 1
    passed = _check_all(args.drafts, words)
    if not passed:
        print("nothing passed the gates; nothing to ask")
        return 1
    # Only the items the gates kept are asked about, and only they can be stored.
    materials = [report.kept() for _, report in passed]
    items = blind.asks(materials)
    import anthropic

    client = anthropic.Anthropic()
    batch_id = args.batch or blind.submit(client, items, model=args.model)
    print(f"batch {batch_id}: {len(items)} requests")
    if not blind.wait(client, batch_id, limit=args.wait):
        print(f"batch {batch_id} has not ended; collect it later with "
              f"`cli material blind --batch {batch_id}` and the same drafts")
        return 2
    answers = blind.collect(client, batch_id)
    failed = 0
    for (path, _), (kept, dropped) in zip(passed, blind.judge(materials, items, answers)):
        for finding in dropped:
            print(f"{path}: drop {finding}")
        report = gates.check(kept, words)
        if not report.passed:
            failed += 1
            for finding in report.failures:
                print(f"{path}: FAIL after the blind check {finding}")
            continue
        final = store.stamp(report.kept(), engine=args.model or claude.MODEL,
                            batch=batch_id)
        written = store.write_checked(final, _root(args))
        print(f"{path}: checked → {written} ({final.ident()})")
    return 1 if failed or len(passed) < len(args.drafts) else 0


def cmd_material_build(args: argparse.Namespace) -> int:
    """Build every checked file into `data/material.db`, re-checking each."""
    from ..material import store

    words = _words(args)
    if words is None:
        return 1
    conn = store.connect(Path(args.database) if args.database else None)
    built, refused = store.build(conn, words, _root(args))
    target = conn.execute("PRAGMA database_list").fetchone()[2] or "memory"
    conn.close()
    for path, why in refused:
        print(f"refused {path}: {why}", file=sys.stderr)
    print(f"{len(built)} built into {target}" + (f", {len(refused)} refused" if refused else ""))
    for ident in built:
        print(f"  {ident}")
    return 1 if refused else 0


def cmd_material_stats(args: argparse.Namespace) -> int:
    """Answers, reports and retired items, per item."""
    import sqlite3

    from .. import config
    from ..material import stats

    with sqlite3.connect(args.progress_db or config.PROGRESS_DB) as conn:
        rows = stats.summary(conn)
    if not rows:
        print("no answers or reports yet")
        return 0
    for r in rows:
        item = r["item"] or "(text)"
        retired = f"  RETIRED: {r['retired']}" if r["retired"] else ""
        print(f"{r['material']} {item}: {r['answers']} answers ({r['counted']} counted), "
              f"{r['right'] or 0} right, {r['reports']} reports{retired}")
    return 0


def cmd_material(args: argparse.Namespace) -> int:
    return args.material_func(args)


def register(sub) -> None:
    """Register this group's commands beside their handlers."""
    p = sub.add_parser("material", help="model-written dialogues and texts: "
                       "gates, blind check, build (ADR-0009)")
    p.set_defaults(func=cmd_material)
    actions = p.add_subparsers(dest="material_command", required=True)

    a = actions.add_parser("schema", help="print the JSON Schema a draft must meet")
    a.set_defaults(material_func=cmd_material_schema)

    a = actions.add_parser("check", help="run the deterministic gates on drafts")
    a.add_argument("drafts", nargs="+", help="draft JSON files")
    a.add_argument("--words-db", default=None)
    a.set_defaults(material_func=cmd_material_check)

    a = actions.add_parser(
        "blind", help="gates, then Haiku 5.5 answers blind (Batches API); "
        "writes what passes to content/material/checked/")
    a.add_argument("drafts", nargs="+", help="draft JSON files")
    a.add_argument("--batch", default=None,
                   help="collect this batch instead of submitting a new one")
    a.add_argument("--wait", type=float, default=6 * 3600,
                   help="seconds to wait for the batch (default 6 h)")
    a.add_argument("--model", default=None, help="defaults to claude-haiku-5-5")
    a.add_argument("--root", default=None, help="defaults to content/material")
    a.add_argument("--words-db", default=None)
    a.set_defaults(material_func=cmd_material_blind)

    a = actions.add_parser("build", help="build content/material/checked/ into data/material.db")
    a.add_argument("--database", "--content-db", dest="database", default=None,
                   help="defaults to EESTI_MATERIAL_DB, then data/material.db")
    a.add_argument("--root", default=None, help="defaults to content/material")
    a.add_argument("--words-db", default=None)
    a.set_defaults(material_func=cmd_material_build)

    a = actions.add_parser("stats", help="answers, reports and retired items")
    a.add_argument("--progress-db", default=None)
    a.set_defaults(material_func=cmd_material_stats)
