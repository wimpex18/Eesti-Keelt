"""Filling the library from other people's servers.

Every one of these is a one-time crawl with a licence attached: ERR and Selges
keeles are owner-only and never redistributed, HARNO material is indexed as
pointers with an empty body, and none of it is committed. The parsers these
call are pure functions over a string and are tested; the fetching is not.
"""

from __future__ import annotations

import argparse

from ._helpers import content_path

#: Local previews can refresh immediately; `push-content` refreshes before upload.
NEXT_LINK_TOPICS = "local preview: python -m eesti.cli link-topics; push-content rebuilds links automatically"


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
    print(NEXT_LINK_TOPICS)
    return 0


def cmd_harvest_reading(args: argparse.Namespace) -> int:
    """Harvest simplified-Estonian reading material (Selges keeles), the reading corpus."""
    from ..harvest.selges import fetch, to_items
    from ..sources import add_items, clear_source, connect, register

    posts = fetch(limit=args.limit)
    if not posts:
        print("Selges keeles returned no readable posts. Existing texts were kept.")
        return 1
    items = to_items(posts)
    conn = connect(content_path(args))
    register(conn)
    clear_source(conn, "selges-keeles")
    add_items(conn, items)

    words = sum(p.word_count for p in posts)
    bands: dict[str, int] = {}
    for item in items:
        bands[item.band or "?"] = bands.get(item.band or "?", 0) + 1
    print(f"  {len(items)} texts, {words:,} words, 100% Estonian")
    print(f"  difficulty: {bands}")
    print(NEXT_LINK_TOPICS)
    return 0


def cmd_evkk(args: argparse.Namespace) -> int:
    """Weight the curriculum by learner-corpus errors: fetch EVKK's public error
    taxonomy counts and rank the nine tags. One cached request; learner texts are
    not fetched.
    """
    from ..config import CACHE
    from ..harvest.evkk import fetch, store, tag_weights, unmapped
    from ..sources import connect, register

    # A third-party outage must not look like a crash: print what happened and what
    # would fix it, and exit with a code.
    try:
        marks = fetch(cache=CACHE / "evkk_marks.html")
    except RuntimeError as exc:
        print(f"EVKK taxonomy unavailable: {exc}")
        print("It is one cached request. Retry when evkk.tlu.ee answers, or "
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

    # A tag with zero weight means a `TAG_MAP` name stopped matching the live
    # taxonomy. Checked here, where the page is in hand (the taxonomy cannot be
    # committed or fetched in CI). Counts are still stored; the exit code is non-zero.
    blank = sorted(tag for tag, n in weights.items() if n == 0)
    if blank:
        print(f"TAG_MAP no longer matches the taxonomy for: {', '.join(blank)}")
        print("Those tags now weigh nothing, so the curriculum order below is "
              "wrong. Check the names against the live page and fix TAG_MAP in "
              "eesti/harvest/evkk.py.\n")

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
    return 1 if blank else 0


def cmd_harvest_exam(args: argparse.Namespace) -> int:
    """Index the exam board's practice tasks as pointers: they are HARNO's copyright
    and their scoring only works on their site.
    """
    from .. import config
    from ..harvest.eis import LEVELS, catalogue, fetch_task, to_items
    from ..sources import (add_items, clear_source, connect as content_connect,
                           register)

    from ..harvest import harno

    levels = tuple(args.levels.split(",")) if args.levels else LEVELS
    conn = content_connect(config.CONTENT_DB)
    register(conn)
    stored = 0

    # Two official sources, and they are not the same thing. EIS publishes
    # interactive tasks that score themselves; harno.ee publishes the task PDFs
    # and the listening audio. A learner wants both, for different sittings.
    try:
        tasks = catalogue(levels)
    except Exception as exc:  # noqa: BLE001 - HARNO is an independent source
        tasks = []
        print(f"EIS unavailable ({type(exc).__name__}); existing tasks were kept.")
    bodies: dict[str, tuple[str, list[str]]] = {}
    if tasks and getattr(args, "download", False):
        # Their server: one task at a time, spaced, and a task that will not
        # load keeps its link.
        for task in tasks:
            body, audio = fetch_task(task)
            if body:
                bodies[task.id] = (body, audio)
        print(f"EIS tasks read into the app: {len(bodies)} of {len(tasks)}")
    if tasks:
        # Ids are content hashes, so a task that gained its text would otherwise
        # be added beside the pointer row it replaces.
        clear_source(conn, "eis")
        stored += add_items(conn, to_items(tasks, bodies))
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
    if materials and getattr(args, "download", False):
        got = harno.download(materials)
        print(f"\nharno.ee files: {got['downloaded']} downloaded, "
              f"{got['already_there']} already here, {got['failed']} failed")
    if materials:
        clear_source(conn, "harno")
        stored += add_items(conn, harno.to_items(materials))
        counts: dict[tuple[str, str], int] = {}
        for m in materials:
            counts[(m.level, m.skill)] = counts.get((m.level, m.skill), 0) + 1
        print("\nharno.ee task material:")
        for (level, skill), n in sorted(counts.items()):
            print(f"  {level} {skill:<12} {n}")

    print(f"\nindexed {stored} official items ((c) Haridus- ja Noorteamet; "
          "downloaded files are for private study and are never redistributed)")
    return 0 if stored else 1


def cmd_harvest_news(args: argparse.Namespace) -> int:
    """Fetch ERR's simplified weekly news — the one live reading source.

    Re-runnable: items are keyed by content hash, so a weekly `--limit 5` updates
    only what changed.
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
    print(NEXT_LINK_TOPICS)
    return 0


def cmd_link_topics(args: argparse.Namespace) -> int:
    """Work out which harvested texts demonstrate which grammar topic.

    Run after a harvest and before pushing: links live in `content.db`, so the
    Vabamorf analysis runs once, not per request.
    """
    from .. import config
    from ..topiclinks import rebuild
    from ..sources import connect as content_connect
    from ..wordlist import connect as wordlist_connect

    content = content_connect(config.CONTENT_DB)
    with wordlist_connect() as words:
        counts = rebuild(content, words)
    if not counts:
        print("No text demonstrated any topic often enough to be worth "
              "offering. Has the corpus been harvested?")
        return 1
    for topic, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {topic:<16} {n} texts")
    return 0


def cmd_rections(args: argparse.Namespace) -> int:
    """Fetch EKK's list of error-prone rections once and store it in the word database."""
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


def cmd_ingest(args: argparse.Namespace) -> int:
    """Add material the learner supplies by hand: a JSON array of item dicts, or a text
    file as one passage. Defaults to source `oma-materjal`, registered as
    not redistributable.
    """
    from pathlib import Path

    from ..sources import REGISTRY, connect, ingest_file, register

    path = Path(args.path)
    if not path.exists():
        print(f"no such file: {path}")
        return 1

    # Check the source is registered first, so the error names the source, not the
    # file.
    if args.source not in {s.id for s in REGISTRY}:
        print(f"{args.source!r} is not a registered source — a row with no "
              f"licence is a row nobody can reason about later. Use "
              f"`--source oma-materjal`, or add it to `sources.REGISTRY` "
              f"with an explicit licence first.")
        return 1

    conn = connect(content_path(args))
    register(conn)
    try:
        added = ingest_file(conn, path, args.source, args.skill, level=args.level)
    except (ValueError, KeyError) as exc:
        print(f"could not read {path}: {exc}")
        return 1
    print(f"  {added} item(s) from {path.name} as {args.skill} "
          f"({args.source})")
    if not added:
        print("  nothing was added — an empty file, or a JSON array with no "
              "items in it")
    else:
        print(NEXT_LINK_TOPICS)
    return 0


def register(sub) -> None:
    """Register this group's commands beside their handlers."""
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
        help="index the official exam material; --download fetches the files",
    )
    p.add_argument("--levels", help="comma-separated, default A2,B1,B2,C1")
    p.add_argument(
        "--download", action="store_true",
        help="fetch the task PDFs and listening audio into data/exam, and read "
             "each EIS task into the app, instead of only linking out")
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

    p = sub.add_parser("ingest",
                       help="add your own file to the library (text or JSON)")
    p.add_argument("path", help="a .json array of items, or any text file")
    p.add_argument("--skill", default="lugemine",
                   help="which exam skill it practises (default: lugemine)")
    p.add_argument("--source", default="oma-materjal",
                   help="registered source id it belongs to")
    p.add_argument("--level", default=None, help="CEFR level, if it states one")
    p.add_argument("--db", default=None)
    p.set_defaults(func=cmd_ingest)
