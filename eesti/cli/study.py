"""The commands that put an exercise in front of you and grade it.

Generation and grading are deterministic here exactly as they are in the app —
the terminal and the web page run the same generators, which is what makes a
drill in either place gradeable without a network call.
"""

from __future__ import annotations

import argparse

from ..config import LEVELS

from ._helpers import content_db, content_path, learner_db, words_db


def cmd_drill(args: argparse.Namespace) -> int:
    from ..drills import generate

    # `words_db`, not `wordlist.connect`: the latter creates the file and
    # lays down the schema, so a run before `cli build` left an empty
    # `data/eesti.db` behind for the next run to mistake for a real one.
    words = words_db()
    if words is None:
        return 1                      # it has already said what to run

    if args.rules == ["verb-form"]:
        from ..drills import generate_verb_drills

        drills = generate_verb_drills(
            words, count=args.count, levels=tuple(args.levels), seed=args.seed
        )
    else:
        drills = generate(
            words, count=args.count, levels=tuple(args.levels),
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
    from ..providers import grammar

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


def cmd_wordorder(args: argparse.Namespace) -> int:
    """Ingest the attested word-order corrections.

    Run after `fetch-bench`. The pairs are ungranted third-party data, so they
    go into `content.db` and travel by `deploy/push-content.sh` — never into
    the image.
    """
    from collections import Counter

    from ..config import DATA
    from ..sources import connect
    from ..wordorder import SOURCE_ID, ingest, items

    path = args.file or (DATA / "raw" / "bench" / "grammar_et.json")
    conn = connect(content_path(args))
    added = ingest(conn, path)
    if not added:
        print(f"Nothing ingested. Is {path} there? Run `cli fetch-bench` first.")
        return 1
    got = items(conn, limit=1000)
    print(f"  {added} word-order items into {content_path(args)} as {SOURCE_ID!r}")
    for rule, n in Counter(i.rule for i in got).most_common():
        print(f"    {rule:10} {n}")
    print("  Ungranted source: push with deploy/push-content.sh, never commit.")
    return 0


def cmd_cloze(args: argparse.Namespace) -> int:
    """Drill on sentences Estonians actually wrote, not on templates.

    The case is named in the prompt, so the answer is forced by morphology and
    nothing is claimed about which case the sentence needed — that is what makes
    an authentic sentence safe to grade.
    """
    from ..cloze import case_clozes, negation_clozes, rection_clozes, sentences

    content = content_db(args)
    if content is None:
        return 1
    sents = sentences(content)
    if not sents:
        print("no usable sentences in the corpus — run `cli harvest-reading`")
        return 1

    words = words_db()
    if words is None:
        return 1
    topics = tuple(args.topics.split(",")) if args.topics else None
    if args.rule == "rection":
        from ..rection import at_levels, load

        levels = tuple(args.levels.split(","))
        stored = load(words)
        if not stored:
            print("no rections stored — run `cli rections` once (one page, cached)")
            return 1
        pool = at_levels(words, stored, levels)
        if not pool:
            print(f"no rections at {args.levels} — try --levels A1,A2,B1,B2")
            return 1
        items = rection_clozes(pool, words=words, count=args.count, seed=args.seed)
    elif args.rule == "negation":
        items = negation_clozes(sents, words=words, count=args.count, seed=args.seed)
    else:
        items = case_clozes(
            sents, topics=topics, words=words, count=args.count, seed=args.seed
        )

    if not items:
        print("no items matched — try other topics, or --rule negation")
        return 1

    for i, item in enumerate(items, 1):
        level = f" [{item.level}]" if item.level else ""
        print(f"\n{i}. {item.prompt}")
        print(f"   ({item.hint}){level}")
        if args.answers:
            print(f"   -> {item.answer}   (не *{item.distractor}*)")
            print(f"   {item.why_ru}")
            ref = item.reference
            if ref and ref.get("known"):
                print(f"   EKK {ref['ekk_section']} — {ref['et_term']}: {ref['url']}")
    print(f"\n{len(items)} items from {len(sents):,} authentic sentences.")
    return 0


def cmd_conjugate(args: argparse.Namespace) -> int:
    """Drill tenses, moods, infinitives and voice.

    The distractor is the neighbouring form the learner confuses this one with —
    `õpiks` against `õpib` — so what is being tested is the marker, not the stem.
    """
    from ..conjugation import FRAMES, generate

    # `words_db`, not `wordlist.connect`: the latter creates the file and
    # lays down the schema, so a run before `cli build` left an empty
    # `data/eesti.db` behind for the next run to mistake for a real one.
    words = words_db()
    if words is None:
        return 1

    topics = tuple(args.topics.split(",")) if args.topics else None
    items = generate(
        words,
        topics=topics,
        levels=tuple(args.levels.split(",")),
        count=args.count,
        seed=args.seed,
    )
    if not items:
        print("no items — check --topics against: " + ", ".join(FRAMES))
        return 1

    for i, item in enumerate(items, 1):
        level = f" [{item.level}]" if item.level else ""
        print(f"\n{i}. {item.prompt}")
        print(f"   ({item.hint}){level}")
        if args.answers:
            print(f"   -> {item.answer}   (не *{item.distractor}*)")
            print(f"   {item.why_ru}")
    print(f"\n{len(items)} items across {len(set(i.topic for i in items))} topics.")
    return 0


def cmd_patterns(args: argparse.Namespace) -> int:
    """Drill comparison, numerals and question words — the closed classes."""
    from ..patterns import comparison_drills, numeral_drills, question_drills

    # `words_db`, not `wordlist.connect`: the latter creates the file and
    # lays down the schema, so a run before `cli build` left an empty
    # `data/eesti.db` behind for the next run to mistake for a real one.
    conn = words_db()
    if conn is None:
        return 1

    levels = tuple(args.levels.split(","))
    builders = {
        "vordlusastmed": lambda n: comparison_drills(conn, levels, n, args.seed),
        "arvsonad": lambda n: numeral_drills(conn, levels, n, args.seed, ("arvsonad",)),
        "jargarvud": lambda n: numeral_drills(conn, levels, n, args.seed, ("jargarvud",)),
        "kusisonad": lambda n: question_drills(n, args.seed),
    }
    wanted = args.topics.split(",") if args.topics else list(builders)
    unknown = set(wanted) - set(builders)
    if unknown:
        print(f"no generator for: {sorted(unknown)}. Known: {', '.join(builders)}")
        return 1

    per = max(1, args.count // len(wanted))
    items = [item for topic in wanted for item in builders[topic](per)]
    for i, item in enumerate(items, 1):
        print(f"\n{i}. {item.prompt}")
        print(f"   ({item.hint})")
        if args.answers:
            print(f"   -> {item.answer}   (не *{item.distractor}*)")
            print(f"   {item.why_ru}")
    print(f"\n{len(items)} items across {len(wanted)} topics.")
    return 0


def cmd_practice(args: argparse.Namespace) -> int:
    """A graded practice session on one topic, with progress recorded.

    Defaults to wherever the learner left off, because the research on paths
    versus trees is consistent: removing the choice improves outcomes.
    """
    from .. import handoff, review
    from ..curriculum import by_id
    from ..practice import items_for
    from ..progress import (MASTERY_CORRECT, MASTERY_WINDOW, accuracy, connect,
                           is_mastered, record, resume)

    progress = connect(learner_db(args, "progress_db"))
    reviews = review.connect(learner_db(args, "review_db"))
    topic = args.topic or resume(progress)
    if topic is None:
        print("nothing available to practise — every unlocked topic is mastered.")
        return 0

    meta = by_id(topic)
    header = f"\n{meta.level}  {meta.et}  ({meta.ru})"
    if args.theme:
        from ..themes import by_id as theme_by_id

        header += f"   —   {theme_by_id(args.theme).et}"
    print(header)
    ref = meta.reference
    if ref is not None:
        print(f"EKK {ref.ekk_section}: {ref.url}")

    items = items_for(topic, count=args.count, seed=args.seed, theme=args.theme)
    if not items and args.theme:
        # Keeleklikk pairs a rule with a situation; not every pairing exists.
        # Say so and fall back rather than ending the session empty-handed.
        print(f"  ({args.theme} has no words this topic can drill — "
              "using the full vocabulary instead)")
        items = items_for(topic, count=args.count, seed=args.seed)
    if not items:
        print("the generator produced nothing for this topic today.")
        return 1

    right = 0
    for i, item in enumerate(items, 1):
        print(f"\n{i}/{len(items)}  {item.prompt}")
        print(f"        ({item.hint})")
        try:
            given = input("     > ")
        except (EOFError, KeyboardInterrupt):
            print("\nstopped.")
            break
        ok = item.check(given)
        right += ok
        record(progress, item, ok, answer=given)
        if ok:
            print("     ✓")
        else:
            print(f"     ✗  {item.answer}   (не *{item.distractor}*)")
            print(f"        {item.why_ru}")
            # Into the queue already marked missed, so it comes back soon
            # rather than being scheduled as fresh material.
            handoff.queue_failed(reviews, item)

    acc = accuracy(progress, topic)
    print(f"\n{right}/{len(items)} correct.")
    if acc is not None:
        print(f"rolling accuracy over the last {MASTERY_WINDOW}: {acc:.0%}")
    if is_mastered(progress, topic):
        print(f"✓ {meta.et} is mastered — it unlocks what depends on it.")
        seeded = handoff.seed_mastered(reviews, topic, seed=args.seed)
        if seeded:
            print(f"  {len(seeded)} item(s) moved into the interleaved review "
                  "queue — run `review`.")
    else:
        print(f"mastery gate: {MASTERY_CORRECT} of the last {MASTERY_WINDOW}.")
    return 0


def register(sub) -> None:
    """Add this group's commands to the subparser table.

    Beside the handlers rather than a thousand lines away in one
    argparse block: a flag and the code that reads it drift apart
    when they cannot be seen together.
    """
    p = sub.add_parser("drill", help="practise object case")
    p.add_argument("-n", "--count", type=int, default=10)
    p.add_argument("--levels", nargs="+", default=list(LEVELS))
    p.add_argument(
        "--rules", nargs="+",
        help="completed | ongoing | negation | verb-form",
    )
    p.add_argument("--seed", type=int)
    p.set_defaults(func=cmd_drill)

    p = sub.add_parser("cloze", help="drill on real harvested sentences")
    p.add_argument("-n", "--count", type=int, default=10)
    p.add_argument("--topics", help="comma-separated curriculum topic ids")
    p.add_argument("--rule", choices=("case-form", "negation", "rection"),
                   default="case-form")
    p.add_argument("--levels", default="A1,A2,B1",
                   help="rection only: CEFR levels of the governing word")
    p.add_argument("--answers", action="store_true", help="show answers")
    p.add_argument("--seed", type=int)
    p.add_argument("--content-db", default=None,
                   help="defaults to EESTI_CONTENT_DB, then data/content.db")
    p.set_defaults(func=cmd_cloze)

    p = sub.add_parser("conjugate", help="drill tenses, moods, infinitives, voice")
    p.add_argument("-n", "--count", type=int, default=10)
    p.add_argument("--topics", help="comma-separated curriculum topic ids")
    p.add_argument("--levels", default="A1,A2,B1")
    p.add_argument("--answers", action="store_true")
    p.add_argument("--seed", type=int)
    p.set_defaults(func=cmd_conjugate)

    p = sub.add_parser("patterns", help="drill comparison, numerals, question words")
    p.add_argument("-n", "--count", type=int, default=8)
    p.add_argument("--topics", help="comma-separated curriculum topic ids")
    p.add_argument("--levels", default="A1,A2,B1")
    p.add_argument("--answers", action="store_true")
    p.add_argument("--seed", type=int)
    p.set_defaults(func=cmd_patterns)

    p = sub.add_parser("practice", help="graded session on one topic, progress saved")
    p.add_argument("--topic", help="curriculum topic id (default: where you left off)")
    p.add_argument("--theme", help="drill this topic over a themed word set")
    p.add_argument("-n", "--count", type=int, default=10)
    p.add_argument("--seed", type=int)
    p.add_argument("--progress-db", default=None)
    p.add_argument("--review-db", default=None)
    p.set_defaults(func=cmd_practice)

    p = sub.add_parser("check", help="grammar-check a sentence")
    p.add_argument("text")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("wordorder",
                       help="ingest attested word-order corrections into content.db")
    p.add_argument("--db", default=None)
    p.add_argument("--file", default=None,
                   help="grammar_et.json (default: the fetch-bench location)")
    p.set_defaults(func=cmd_wordorder)
