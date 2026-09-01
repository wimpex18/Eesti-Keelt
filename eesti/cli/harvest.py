"""Filling the library from other people's servers.

Every one of these is a one-time crawl with a licence attached: ERR and Selges
keeles are owner-only and never redistributed, HARNO material is indexed as
pointers with an empty body, and none of it is committed. The parsers these
call are pure functions over a string and are tested; the fetching is not.
"""

from __future__ import annotations

import argparse

from ._helpers import content_path

def cmd_harvest(args: argparse.Namespace) -> int:
    """Crawl the ERR language-course archives into the content store.

    One-time: the archives are closed, and every page is cached, so a re-run
    issues no requests. Content is (c) ERR and stored owner-only.
    """
    from ..harvest.err import harvest, to_items
    from ..sources import add_items, connect, register

    result = harvest(max_pages=args.max_pages)
    conn = connect(content_path(args))
    register(conn)
    items = to_items(result)
    add_items(conn, items)

    for series, episodes in result.items():
        words = sum(e.word_count for e in episodes)
        audio = sum(1 for e in episodes if e.audio_url)
        print(f"  {series}: {len(episodes)} episodes, {words:,} words, {audio} with audio")
    print(f"\nstored {len(items)} items in {content_path(args)} (owner-only, (c) ERR)")
    return 0


def cmd_harvest_reading(args: argparse.Namespace) -> int:
    """Harvest simplified-Estonian reading material (Selges keeles).

    This is the actual reading corpus. The ERR radio archives measured 12%
    Estonian — Russian grammar lessons with Estonian examples — so they are
    filed as grammar, not reading.
    """
    from ..harvest.selges import fetch, to_items
    from ..sources import add_items, clear_source, connect, register

    posts = fetch(limit=args.limit)
    conn = connect(content_path(args))
    register(conn)
    clear_source(conn, "selges-keeles")
    items = to_items(posts)
    add_items(conn, items)

    words = sum(p.word_count for p in posts)
    bands: dict[str, int] = {}
    for item in items:
        bands[item.band or "?"] = bands.get(item.band or "?", 0) + 1
    print(f"  {len(items)} texts, {words:,} words, 100% Estonian")
    print(f"  difficulty: {bands}")
    return 0


def cmd_evkk(args: argparse.Namespace) -> int:
    """Weight the curriculum by real learner errors, not just one person's log.

    Fetches the public EVKK error taxonomy (51 467 linguist-annotated errors in
    learner Estonian) and reports how the nine tags rank in it. One request,
    cached; the learner texts themselves are deliberately left alone.
    """
    from ..config import CACHE
    from ..harvest.evkk import fetch, store, tag_weights, unmapped
    from ..sources import connect, register

    # A third party being down must never look like a crash. `fetch` raises
    # when there is no cached copy and `elle.tlu.ee` cannot be reached -- which
    # is a Tuesday for these research hosts, and the reason this command is
    # excluded from the test suite. Say what happened and what would fix it,
    # and leave with a code rather than a traceback.
    try:
        marks = fetch(cache=CACHE / "evkk_marks.html")
    except RuntimeError as exc:
        print(f"EVKK taxonomy unavailable: {exc}")
        print("It is one cached request. Retry when elle.tlu.ee answers, or "
              "drop a saved copy of the taxonomy page at "
              f"{CACHE / 'evkk_marks.html'} to work offline.")
        return 1
    if not marks:
        print("EVKK returned nothing parseable — the page shape may have "
              "changed. Nothing was written.")
        return 1

    weights = tag_weights(marks)
    rest = unmapped(marks)
    total = sum(weights.values()) + rest

    conn = connect(content_path(args))
    register(conn)
    store(conn, marks)

    print(f"{len(marks)} taxonomy nodes, {total:,} annotated errors\n")
    print(f"  {'tag':<12}{'marks':>8}{'share':>8}")
    for tag, n in sorted(weights.items(), key=lambda kv: -kv[1]):
        print(f"  {tag:<12}{n:>8,}{n / total:>8.1%}")
    print(f"  {'(unmapped)':<12}{rest:>8,}{rest / total:>8.1%}")
    print(
        "\nAnnotation frequency, not incidence: parent categories absorb marks a"
        "\nfiner child would have taken, and exam essays dominate the corpus."
        "\nRead the ordering, not the absolute numbers."
    )
    return 0


def cmd_harvest_exam(args: argparse.Namespace) -> int:
    """Index the exam board's own practice tasks.

    Pointers, not copies: the tasks are copyright Haridus- ja Noorteamet, they
    live in an iframe on their site, and the scoring and feedback that make them
    worth doing only work there. A link buys everything a copy would, and holds
    none of their material.
    """
    from .. import config
    from ..harvest.eis import LEVELS, catalogue, to_items
    from ..sources import add_items, connect as content_connect, register

    from ..harvest import harno

    levels = tuple(args.levels.split(",")) if args.levels else LEVELS
    conn = content_connect(config.CONTENT_DB)
    register(conn)
    stored = 0

    # Two official sources, and they are not the same thing. EIS publishes
    # interactive tasks that score themselves; harno.ee publishes the task PDFs
    # and the listening audio. A learner wants both, for different sittings.
    tasks = catalogue(levels)
    if tasks:
        stored += add_items(conn, to_items(tasks))
        by_level: dict[str, int] = {}
        for task in tasks:
            by_level[task.level] = by_level.get(task.level, 0) + 1
        print("EIS interactive tasks:")
        for level in sorted(by_level):
            print(f"  {level}: {by_level[level]}")
    else:
        print("EIS returned nothing — check https://eis.harno.ee/publicitems "
              "by hand before assuming a bug.")

    try:
        materials = [m for m in harno.catalogue() if m.level in levels]
    except Exception as exc:  # noqa: BLE001 - one source failing is not fatal
        materials = []
        print(f"\nharno.ee unavailable: {str(exc)[:100]}")
    if materials:
        stored += add_items(conn, harno.to_items(materials))
        counts: dict[tuple[str, str], int] = {}
        for m in materials:
            counts[(m.level, m.skill)] = counts.get((m.level, m.skill), 0) + 1
        print("\nharno.ee task material:")
        for (level, skill), n in sorted(counts.items()):
            print(f"  {level} {skill:<12} {n}")

    print(f"\nindexed {stored} official items (pointers only, (c) HARNO)")
    return 0 if stored else 1


def cmd_harvest_news(args: argparse.Namespace) -> int:
    """Fetch ERR's simplified weekly news.

    The only live source in this project. Everything else read is frozen -- the
    radio courses ended in 2019, Selges keeles is a fixed set -- and will say
    the same thing in spring 2027. This keeps producing sentences about things
    that happened this month, which is what a reading exam is made of.

    Re-runnable: items are keyed by content hash, so a weekly `--limit 5` costs
    five requests and updates nothing that has not changed.
    """
    from .. import config
    from ..harvest import lihtsad
    from ..sources import add_items, connect as content_connect, register

    issues = lihtsad.harvest(limit=args.limit)
    if not issues:
        print("Nothing fetched. The feed is at news.err.ee/k/lihtsad-uudised — "
              "check it by hand before assuming a bug.")
        return 1

    conn = content_connect(config.CONTENT_DB)
    register(conn)
    stored = add_items(conn, lihtsad.to_items(issues))
    words = sum(i.word_count for i in issues)
    newest = max((i.published or "") for i in issues)[:10]
    print(f"  {len(issues)} issues, {words:,} words, newest {newest}")
    print(f"\nstored {stored} items (owner-only, (c) ERR)")
    return 0


def cmd_link_topics(args: argparse.Namespace) -> int:
    """Work out which harvested texts demonstrate which grammar topic.

    Run after a harvest and before pushing: the links live inside content.db,
    so the deployment gets them for free and no container ever repeats the work.

    Slow -- every sentence goes through Vabamorf -- and that is the trade. The
    alternative is deciding it per request, which would put a morphological
    analysis of the whole corpus in front of a learner waiting for a page.
    """
    from .. import config
    from ..topiclinks import link_labelled, link_topics
    from ..sources import connect as content_connect
    from ..wordlist import connect as wordlist_connect

    content = content_connect(config.CONTENT_DB)
    counts = link_topics(content, wordlist_connect())
    # After the derived links, never before: a lesson label outranks anything
    # inferred from a transcript, and `link_topics` clears the table.
    for topic, n in link_labelled(content).items():
        counts[topic] = counts.get(topic, 0) + n
    if not counts:
        print("No text demonstrated any topic often enough to be worth "
              "offering. Has the corpus been harvested?")
        return 1
    for topic, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {topic:<16} {n} texts")
    return 0


def cmd_rections(args: argparse.Namespace) -> int:
    """Fetch EKK's list of error-prone rections, once, and store it.

    Deliberate and separate from practice: a lesson must never depend on EKI
    being reachable. One page, cached on disk, stored in the word database.
    """
    from ..config import CACHE
    from ..rection import at_levels, fetch, load, store
    from ..wordlist import connect

    conn = connect()
    rections = fetch(cache=CACHE / "ekk_su64.html")
    store(conn, rections)
    usable = at_levels(conn, load(conn), tuple(args.levels.split(",")))
    print(f"{len(rections)} unambiguous contrasts stored, "
          f"{len(usable)} at {args.levels}")
    for r in usable:
        print(f"  {r.headword:<14} {r.correct_frame} ({r.correct_case})"
              f"  NOT {r.wrong_frame} ({r.wrong_case})")
    return 0


def register(sub) -> None:
    """Add this group's commands to the subparser table.

    Beside the handlers rather than a thousand lines away in one
    argparse block: a flag and the code that reads it drift apart
    when they cannot be seen together.
    """
    p = sub.add_parser("harvest", help="crawl ERR language archives (one time)")
    p.add_argument("--max-pages", type=int, default=300)
    p.add_argument("--db", default=None)
    p.set_defaults(func=cmd_harvest)

    p = sub.add_parser("harvest-reading", help="harvest simplified Estonian texts")
    p.add_argument("--limit", type=int)
    p.add_argument("--db", default=None)
    p.set_defaults(func=cmd_harvest_reading)

    p = sub.add_parser(
        "harvest-news",
        help="fetch ERR Lihtsad uudised — the live weekly reading feed",
    )
    p.add_argument("--limit", type=int, default=20,
                   help="how many recent issues (default 20)")
    p.set_defaults(func=cmd_harvest_news)

    p = sub.add_parser(
        "harvest-exam",
        help="index the official EIS practice tasks (links, not copies)",
    )
    p.add_argument("--levels", help="comma-separated, default A2,B1,B2,C1")
    p.set_defaults(func=cmd_harvest_exam)

    p = sub.add_parser(
        "link-topics",
        help="link harvested texts to the grammar topics they demonstrate",
    )
    p.set_defaults(func=cmd_link_topics)

    p = sub.add_parser("evkk", help="rank error tags by real learner-corpus data")
    p.add_argument("--db", default=None)
    p.set_defaults(func=cmd_evkk)

    p = sub.add_parser("rections", help="fetch and store EKK's rection table (once)")
    p.add_argument("--levels", default="A1,A2,B1")
    p.set_defaults(func=cmd_rections)
