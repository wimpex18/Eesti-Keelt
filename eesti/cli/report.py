"""Where you stand: the path, the syllabus, the shelf and the verdict.

Read-only, all of them, which is why every one runs in the test suite with
stdin at EOF. `--help` proves the parser; only running the body proves the
command.
"""

from __future__ import annotations

import argparse

from ..config import LEVELS
from ._helpers import content_db, learner_db

def cmd_curriculum(args: argparse.Namespace) -> int:
    """Show the syllabus: the study path, and what can actually be practised.

    The path is derived from the prerequisite graph, not hand-written, so it
    cannot offer a case before the stem that case is built from.
    """
    from ..curriculum import at_level, coverage, order, practice_order, validate

    from ..curriculum import TOPICS

    validate()
    topics = at_level(args.level) if args.level else TOPICS

    if args.priority:
        print("Ranked by share of annotated errors in the EVKK learner corpus:\n")
        for t in practice_order(topics)[: args.limit]:
            mark = "drillable" if t.generator else "no generator"
            print(f"  {t.weight:>5.1f}%  {t.level}  {t.id:<16} {t.et:<34} {mark}")
        return 0

    level = None
    for t in order(topics):
        if t.level != level:
            level = t.level
            print(f"\n{level}")
        needs = f"  <- {', '.join(t.requires)}" if t.requires else ""
        flag = " *" if t.generator else "  "
        print(f" {flag} {t.id:<16} {t.et}{needs}")

    c = coverage(topics)
    print(
        f"\n{c['topics']} topics, {c['with_generator']} with a drill generator, "
        f"{c['with_reference']} linked to the EKK handbook."
        "\n* = practice exists today; the rest is step 2 of the curriculum plan."
    )
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    """Where you stand on every topic, in study order."""
    from ..progress import connect, report, resume

    progress = connect(learner_db(args, "progress_db"))
    rows = report(progress)
    # Same substitution the API makes: `blocked_by` holds ids, and a learner
    # reading "<- gen-stem" has been shown a database key rather than the name
    # of the thing they have to study. The terminal prints the topic id in its
    # own column already, so nothing is lost by naming the prerequisite.
    names = {row.topic: row.et for row in rows}
    level = None
    for row in rows:
        if args.todo and row.state in ("mastered", "locked"):
            continue
        if row.level != level:
            level = row.level
            print(f"\n{level}")
        acc = f"{row.accuracy:.0%}" if row.accuracy is not None else "  -"
        blocked = (f"  <- {', '.join(names.get(b, b) for b in row.blocked_by)}"
                   if row.blocked_by else "")
        print(f"  {row.state:<12} {row.topic:<16} {row.et[:30]:<32}"
              f" n={row.attempts:<4} {acc:>4}{blocked}")

    done = sum(1 for r in rows if r.state == "mastered")
    print(f"\n{done}/{len(rows)} topics mastered.")
    nxt = resume(progress)
    print(f"next: {nxt}" if nxt else "next: nothing unlocked to practise")
    return 0


def cmd_themes(args: argparse.Namespace) -> int:
    """The situations a grammar topic can be drilled inside.

    Keeleklikk's insight — grammar arrives in service of a situation — but with
    theme and rule as separate axes, so eleven themes times twenty-one drillable
    topics come out of the same generators.
    """
    from ..themes import coverage, validate
    from ..wordlist import connect

    conn = connect()
    unknown = validate(conn)
    for theme, words in unknown.items():
        print(f"  !! {theme}: not in the lexicon — {', '.join(words)}")

    levels = tuple(args.levels.split(","))
    print(f"  {'theme':<12}{'words':>6}{'nouns':>7}{'verbs':>7}   name")
    for theme_id, info in coverage(conn, levels).items():
        print(f"  {theme_id:<12}{info['usable']:>6}{info['nouns']:>7}"
              f"{info['verbs']:>7}   {info['et']}")
    print("\nUse with practice: `practice --topic lihtminevik --theme reisimine`")
    return 0


def cmd_library(args: argparse.Namespace) -> int:
    """Browse the material: unordered, ungated, measured only by exposure."""
    from ..library import browse, exposure, sections
    from ..progress import connect as progress_connect

    content = content_db(args)
    if content is None:
        return 1

    if not args.section:
        for row in sections(content):
            print(f"  {row['id']:<11}{row['items']:>5} items"
                  f"{'  (' + str(row['with_audio']) + ' with audio)' if row['with_audio'] else '':<22}"
                  f" {row['et']}")
        public = sum(s["items"] for s in sections(content, public_only=True))
        print(f"\n{public} item(s) may be served publicly — the rest is owner-only "
              "by licence,\nwhich is what Cloudflare Access exists to enforce.")
        print("Browse one: `library --section lugemine`")
        return 0

    rows = browse(content, args.section, level=args.level, limit=args.count)
    if not rows:
        print(f"nothing in {args.section} — run the harvest commands first")
        return 1
    for row in rows:
        title = (row["title"] or "")[:58]
        audio = " ♪" if row["audio_url"] else ""
        print(f"  {row['id'][:10]}  [{row['level'] or '-':<3}] {title}{audio}")

    if args.seen:
        from ..library import open_item
        from ..vocab import connect as vocab_connect

        progress = progress_connect(learner_db(args, "progress_db"))
        vocabulary = vocab_connect(learner_db(args, "vocab_db"))
        met = sum(
            open_item(content, row["id"], progress, vocabulary, args.minutes)["lemmas"]
            for row in rows
        )
        print(f"\nopened {len(rows)} item(s): {exposure(progress)}")
        print(f"{met} word encounter(s) recorded — encounters, not knowledge. "
              "Mark words known with `vocab --know`.")
    return 0


def cmd_vocab(args: argparse.Namespace) -> int:
    """Track which words you actually know, and how far into the frequency list."""
    from ..vocab import (KNOWN, STATUS_NAMES, WELL_KNOWN, band_progress, connect,
                        set_status, summary)
    from ..wordlist import connect as wordlist_connect

    vocabulary = connect(learner_db(args, "vocab_db"))
    words = wordlist_connect()

    if args.know:
        status = WELL_KNOWN if args.long_known else KNOWN
        for lemma in args.know:
            set_status(vocabulary, lemma.lower(), status)
        print(f"marked {len(args.know)} word(s) as {STATUS_NAMES[status]}")

    info = summary(vocabulary)
    print(f"\n{info['known_total']} known of {info['tracked']} tracked: "
          f"{info['by_status']}")
    print("\nKnown within each frequency band — the denominator is the band, "
          "not the language:")
    for band in band_progress(vocabulary, words):
        bar = "#" * int(band["share"] * 20)
        print(f"  top {band['from']:>4}-{band['to']:<5} {band['known']:>4}/"
              f"{band['size']:<4} {band['share']:>6.0%} {bar}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Where you stand across every section — with no single number."""
    from ..overview import overview
    from ..progress import connect as progress_connect
    from ..review import connect as review_connect
    from ..vocab import connect as vocab_connect
    from ..wordlist import connect as wordlist_connect

    # A missing corpus must not take the whole status page down: every other
    # section still has something true to say.
    content = content_db(args)
    data = overview(
        progress=progress_connect(learner_db(args, "progress_db")),
        reviews=review_connect(learner_db(args, "review_db")),
        vocabulary=vocab_connect(learner_db(args, "vocab_db")),
        words=wordlist_connect(),
        content=content,
    )

    rada = data["sections"].get("rada")
    if rada:
        print(f"Rada          {rada['mastered']}/{rada['total']} topics mastered, "
              f"{rada['available']} available   next: {rada['next'] or '-'}")
    sonavara = data["sections"].get("sonavara")
    if sonavara:
        print(f"Sõnavara      {sonavara['known_in_top']} known within the top "
              f"{sonavara['top']}")
        for band in sonavara["bands"]:
            if band["known"] or band["from"] == 1:
                print(f"                top {band['from']:>4}-{band['to']:<5}"
                      f" {band['known']:>4}/{band['size']:<4} {band['share']:>6.0%}")
    kordamine = data["sections"].get("kordamine")
    if kordamine:
        print(f"Kordamine     {kordamine['due']} due now, "
              f"{kordamine['scheduled']} scheduled")
    lib = data["sections"].get("raamatukogu")
    if lib:
        print(f"Raamatukogu   {lib.get('items', 0)} item(s) opened, "
              f"{lib.get('minutes', 0)} minute(s)")
        for section, n in (lib.get("available") or {}).items():
            print(f"                {section:<11} {n} available")

    print("\nNo overall percentage: the exam scores four parts separately and "
          "fails you\nfor a zero in any one, so an aggregate would hide the "
          "thing that decides it.")
    return 0


def cmd_readiness(args: argparse.Namespace) -> int:
    """Say what the evidence shows about sitting a level, and what is missing.

    Deliberately not a score. Nothing here has seen a graded exam, so a number
    would be invented — and the number is exactly what someone facing a
    registration deadline would most want to believe.
    """
    from ..config import PROGRESS_DB, VOCAB_DB
    from ..progress import connect as progress_connect
    from ..readiness import readiness
    from ..vocab import connect as vocab_connect
    from ..wordlist import connect as words_connect

    from .. import config
    from ..sources import connect as content_connect

    r = readiness(args.level, progress=progress_connect(PROGRESS_DB),
                  vocabulary=vocab_connect(VOCAB_DB), words=words_connect(),
                  content=content_connect(config.CONTENT_DB))

    print(f"{args.level}: {r.verdict}")
    print(f"  решение через {r.days_to_decide} дн., "
          f"экзамен через {r.days_to_sitting} дн.\n")
    for part in r.parts:
        mark = {True: "+", False: "-", None: "?"}[part.touched]
        print(f"  [{mark}] {part.et:<13} {part.evidence}")
    if r.grammar:
        g = r.grammar
        print(f"\n  грамматика: {g['mastered']}/{g['topics']} тем, "
              f"контрольная "
              f"{'сдана' if g['checkpoint_passed'] else 'не сдана'}")
    if r.reasons:
        print("\n  почему ещё нет:")
        for reason in r.reasons:
            print(f"    - {reason}")
    print("\n  " + r.to_dict()["caveat"])
    return 0


def register(sub) -> None:
    """Add this group's commands to the subparser table.

    Beside the handlers rather than a thousand lines away in one
    argparse block: a flag and the code that reads it drift apart
    when they cannot be seen together.
    """
    p = sub.add_parser("progress", help="where you stand on every topic")
    p.add_argument("--todo", action="store_true", help="hide mastered and locked")
    p.add_argument("--progress-db", default=None)
    p.set_defaults(func=cmd_progress)

    p = sub.add_parser("status", help="where you stand, section by section")
    p.add_argument("--content-db", default=None,
                   help="defaults to EESTI_CONTENT_DB, then data/content.db")
    p.add_argument("--progress-db", default=None)
    p.add_argument("--review-db", default=None)
    p.add_argument("--vocab-db", default=None)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser(
        "readiness", help="what the evidence says about sitting a level")
    p.add_argument("--level", default="A2", choices=list(LEVELS))
    p.set_defaults(func=cmd_readiness)

    p = sub.add_parser("curriculum", help="show the A1-B1 syllabus and study path")
    p.add_argument("--level", choices=list(LEVELS))
    p.add_argument("--priority", action="store_true",
                   help="rank by learner-corpus error frequency instead")
    p.add_argument("--limit", type=int, default=12)
    p.set_defaults(func=cmd_curriculum)

    p = sub.add_parser("themes", help="themed word sets a topic can be drilled over")
    p.add_argument("--levels", default="A1,A2,B1")
    p.set_defaults(func=cmd_themes)

    p = sub.add_parser("vocab", help="words you know, by frequency band")
    p.add_argument("--know", nargs="*", help="mark these lemmas as known")
    p.add_argument("--long-known", action="store_true",
                   help="mark as well known rather than newly known")
    p.add_argument("--vocab-db", default=None)
    p.set_defaults(func=cmd_vocab)

    p = sub.add_parser("library", help="browse material: ungated, unordered")
    p.add_argument("--section", choices=("lugemine", "kuulamine", "saated", "eksam"))
    p.add_argument("--level")
    p.add_argument("-n", "--count", type=int, default=15)
    p.add_argument("--seen", action="store_true", help="record these as opened")
    p.add_argument("--minutes", type=float, default=0.0)
    p.add_argument("--content-db", default=None,
                   help="defaults to EESTI_CONTENT_DB, then data/content.db")
    p.add_argument("--progress-db", default=None)
    p.add_argument("--vocab-db", default=None)
    p.set_defaults(func=cmd_library)
