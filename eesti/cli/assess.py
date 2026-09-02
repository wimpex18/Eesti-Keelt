"""Measuring rather than practising: review, placement, checkpoint, test-out.

The difference from `study.py` is what the answer is *for*. A drill teaches;
these four decide something — what is due, where in the syllabus to start,
whether a level is finished, whether a topic can be skipped. All four schedule
or gate, and all four are deterministic.
"""

from __future__ import annotations

import argparse

from ..config import LEVELS
from ._helpers import _ask_terminal, learner_db

def cmd_placement(args: argparse.Namespace) -> int:
    """Find where to start, instead of starting at lesson one.

    Walks the syllabus in study order, probing each topic with a short set, and
    stops once failures accumulate. It places you; it does not audit you — use
    `test-out --topic X` for any single topic you already know.
    """
    from ..placement import PROBE_ITEMS, PROBE_REQUIRED, entry_points, sweep
    from ..progress import connect

    progress = connect(learner_db(args, "progress_db"))
    print(
        f"Placement: {PROBE_ITEMS} items per topic, all {PROBE_REQUIRED} correct "
        "to skip it.\nA miss skips what depends on that topic, not the whole "
        "sweep — so the\nverb branch is still asked about after a noun topic "
        "goes wrong. Ctrl-C to leave early.\n"
    )

    def report(result) -> None:
        if not result.ran:
            return
        mark = "✓ known" if result.passed else "→ start here"
        print(f"\n   {result.topic}: {result.correct}/{result.asked}  {mark}")

    results = sweep(progress, _ask_terminal, seed=args.seed, on_result=report)
    known = [r.topic for r in results if r.passed]
    starts = entry_points(results)

    print(f"\n{len(known)} topic(s) marked known: {', '.join(known) or 'none'}")
    if starts:
        # One per independent branch: being at A2 on verbs and A1 on nouns is an
        # ordinary way to be, and a single "you are here" cannot say it.
        print(f"start at: {', '.join(starts)}")
    else:
        print("start at: nothing left to place")
    print("run `practice` to begin, or `progress` to see the whole syllabus.")
    return 0


def cmd_test_out(args: argparse.Namespace) -> int:
    """Skip one topic you already know, by demonstrating it."""
    from ..curriculum import by_id
    from ..placement import PROBE_REQUIRED, Stopped, probe
    from ..progress import connect

    progress = connect(learner_db(args, "progress_db"))
    meta = by_id(args.topic)
    print(f"\nTest-out: {meta.level}  {meta.et}")

    try:
        result = probe(progress, args.topic, _ask_terminal, seed=args.seed)
    except Stopped:
        print("\nstopped — nothing was marked known.")
        return 0
    if not result.ran:
        print(f"\nnot probed: {result.skipped}")
        return 1
    print(f"\n{result.correct}/{result.asked}")
    if result.passed:
        print(f"✓ {meta.et} marked known — it unlocks what depends on it.")
    else:
        print(f"needs {PROBE_REQUIRED}/{result.asked}. Those attempts were "
              "recorded, so practice picks up from here.")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """Interleaved review: whatever is due, mixed across topics by construction.

    This is the second half of the blocked-then-interleaved schedule. Items
    arrive here two ways — missed during practice, or seeded when their topic
    was mastered — and FSRS decides when each comes back.
    """
    from .. import handoff, review
    from ..progress import connect as progress_connect

    reviews = review.connect(learner_db(args, "review_db"))
    progress = progress_connect(learner_db(args, "progress_db"))

    # Catch topics mastered before the handoff existed, or in a session that
    # ended early, so nothing sits outside the review pool forever.
    for topic in handoff.pending_handoffs(progress, reviews):
        added = handoff.seed_mastered(reviews, topic)
        if added:
            print(f"  seeded {len(added)} item(s) from mastered topic {topic}")

    items = review.due(reviews, limit=args.count)
    if not items:
        info = review.stats(reviews)
        nxt = reviews.execute(
            "SELECT MIN(due) FROM review_items"
        ).fetchone()[0]
        print(f"nothing due. {info['total']} item(s) in the queue.")
        if nxt:
            # Worth saying: an item missed a minute ago is *supposed* to be a
            # few minutes out, and an empty queue right after practice
            # otherwise reads as a bug.
            print(f"next due at {nxt}.")
        return 0

    right = 0
    for i, item in enumerate(items, 1):
        print(f"\n{i}/{len(items)}  [{item.kind}]  {item.prompt}")
        try:
            given = input("     > ")
        except (EOFError, KeyboardInterrupt):
            print("\nstopped.")
            break
        ok = given.strip().casefold() == item.answer.casefold()
        right += ok
        result = review.grade(reviews, item.id, "good" if ok else "again")
        if ok:
            print(f"     ✓  next in {result['interval_days']} day(s)")
        else:
            print(f"     ✗  {item.answer}")
            if item.why_ru:
                print(f"        {item.why_ru}")

    print(f"\n{right}/{len(items)} correct.")
    print(f"{review.stats(reviews)['due']} still due.")
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    """A mixed quiz across a whole level — interleaved by construction."""
    from ..checkpoint import PASS_MARK, ready, run, topics_at
    from ..placement import Stopped
    from ..progress import connect as progress_connect
    from ..review import connect as review_connect

    progress = progress_connect(learner_db(args, "progress_db"))
    reviews = review_connect(learner_db(args, "review_db"))

    topics = topics_at(args.level)
    if not topics:
        print(f"no drillable topics at {args.level}")
        return 1
    if not ready(progress, args.level) and not args.force:
        from ..progress import mastered

        missing = sorted(set(topics) - mastered(progress))
        print(f"{args.level} is not finished yet — still to master: "
              f"{', '.join(missing)}")
        print("Run it anyway with --force; it is a diagnosis, not a gate.")
        return 1

    print(f"\n{args.level} checkpoint: {args.count} questions across "
          f"{len(topics)} topics, mixed.\nNo hint which rule applies — that is "
          "the point.\n")
    try:
        result = run(progress, args.level, _ask_terminal, count=args.count,
                     seed=args.seed, reviews=reviews)
    except Stopped:
        print("\nstopped — no checkpoint recorded. What you answered is kept "
              "as ordinary practice.")
        return 0
    print(f"\n{result.correct}/{result.asked} — {result.score:.0%} "
          f"(pass is {PASS_MARK:.0%})")
    if result.weakest:
        # Show the tallies, not just the names: one or two items per topic
        # points at where to look, it does not measure the topic.
        detail = ", ".join(
            f"{t} {result.by_topic[t][0]}/{result.by_topic[t][1]}"
            for t in result.weakest
        )
        print(f"look at: {detail}")
    print("✓ passed" if result.passed else
          "not passed. Nothing is un-mastered; the missed items are in the "
          "review queue.")
    return 0


def register(sub) -> None:
    """Add this group's commands to the subparser table.

    Beside the handlers rather than a thousand lines away in one
    argparse block: a flag and the code that reads it drift apart
    when they cannot be seen together.
    """
    p = sub.add_parser("review", help="interleaved review of whatever is due")
    p.add_argument("-n", "--count", type=int, default=20)
    p.add_argument("--review-db", default=None)
    p.add_argument("--progress-db", default=None)
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("checkpoint", help="mixed end-of-level quiz")
    p.add_argument("--level", default="A1", choices=list(LEVELS))
    p.add_argument("-n", "--count", type=int, default=15)
    p.add_argument("--force", action="store_true")
    p.add_argument("--seed", type=int)
    p.add_argument("--progress-db", default=None)
    p.add_argument("--review-db", default=None)
    p.set_defaults(func=cmd_checkpoint)

    p = sub.add_parser("placement", help="find where to start in the syllabus")
    p.add_argument("--seed", type=int)
    p.add_argument("--progress-db", default=None)
    p.set_defaults(func=cmd_placement)

    p = sub.add_parser("test-out", help="skip one topic by demonstrating it")
    p.add_argument("--topic", required=True)
    p.add_argument("--seed", type=int)
    p.add_argument("--progress-db", default=None)
    p.set_defaults(func=cmd_test_out)
