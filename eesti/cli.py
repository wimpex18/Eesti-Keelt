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

# Named here rather than imported at module load so the CLI stays importable
# without the provider dependencies installed.
_PROVIDERS = ("openrouter", "groq", "workers-ai", "huggingface", "anthropic")

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

    if args.rules == ["verb-form"]:
        from .drills import generate_verb_drills

        drills = generate_verb_drills(
            connect(), count=args.count, levels=tuple(args.levels), seed=args.seed
        )
    else:
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


def cmd_export(args: argparse.Namespace) -> int:
    """Build the edge dataset. Vabamorf runs here, never at the edge."""
    from .export import export
    from .wordlist import connect

    print("Synthesizing forms with Vabamorf (build-time only) ...")
    stats = export(connect(), max_freq_rank=args.max_freq_rank)
    for key in ("lemmas", "forms", "object_cases", "distinct"):
        print(f"  {key:14} {stats[key]:,}")
    print(f"  {'size':14} {stats['bytes'] / 1e6:.1f} MB  ->  data/edge.db")
    print("\nImport to Cloudflare D1 with:")
    print("  npx wrangler d1 execute eesti --file=data/edge.sql --remote")
    return 0


def cmd_keys(args: argparse.Namespace) -> int:
    """Show which API keys are configured. Never prints a full key."""
    from .env import ENV_FILE, describe

    print(f".env: {ENV_FILE} {'(found)' if ENV_FILE.exists() else '(missing)'}\n")
    for name, is_set, masked, purpose in describe():
        mark = "✓" if is_set else " "
        print(f" {mark} {name:24} {masked:10} {purpose}")
    if not any(s for _, s, _, _ in describe()):
        print("\nNo keys set. `cp .env.example .env` and add one — "
              "OpenRouter is the recommended starting point:")
        print("  https://openrouter.ai/keys")
    return 0


def cmd_harvest(args: argparse.Namespace) -> int:
    """Crawl the ERR language-course archives into the content store.

    One-time: the archives are closed, and every page is cached, so a re-run
    issues no requests. Content is (c) ERR and stored owner-only.
    """
    from .harvest.err import harvest, to_items
    from .sources import add_items, connect, register

    result = harvest(max_pages=args.max_pages)
    conn = connect(args.db)
    register(conn)
    items = to_items(result)
    add_items(conn, items)

    for series, episodes in result.items():
        words = sum(e.word_count for e in episodes)
        audio = sum(1 for e in episodes if e.audio_url)
        print(f"  {series}: {len(episodes)} episodes, {words:,} words, {audio} with audio")
    print(f"\nstored {len(items)} items in {args.db} (owner-only, (c) ERR)")
    return 0


def cmd_harvest_reading(args: argparse.Namespace) -> int:
    """Harvest simplified-Estonian reading material (Selges keeles).

    This is the actual reading corpus. The ERR radio archives measured 12%
    Estonian — Russian grammar lessons with Estonian examples — so they are
    filed as grammar, not reading.
    """
    from .harvest.selges import fetch, to_items
    from .sources import add_items, clear_source, connect, register

    posts = fetch(limit=args.limit)
    conn = connect(args.db)
    register(conn)
    clear_source(conn, "selges-keeles")
    items = to_items(posts)
    add_items(conn, items)

    words = sum(p.word_count for p in posts)
    bands: dict[str, int] = {}
    for item in items:
        bands[item.level or "?"] = bands.get(item.level or "?", 0) + 1
    print(f"  {len(items)} texts, {words:,} words, 100% Estonian")
    print(f"  difficulty: {bands}")
    return 0


def cmd_fetch_bench(args: argparse.Namespace) -> int:
    """Download the public Estonian benchmark datasets (TalTechNLP, LREC 2026)."""
    from .evals.fetch import fetch_all

    for name, count in fetch_all().items():
        print(f"  {name}: {count:,} rows")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Check Vabamorf against native-curated gold forms.

    Everything this app generates inherits Vabamorf's correctness, so this is the
    check that the foundation is sound.
    """
    from .evals.morphology import run

    r = run()
    print(f"Vabamorf vs inflection_et: {r['match']}/{r['total']} = {r['agreement']:.1%}")
    for key, (match, total) in r["per_case"].items():
        print(f"  {key:6} {match}/{total} = {match / total:.0%}")
    if r["misses"]:
        print("\nsample disagreements (mostly invariant adjectives):")
        for phrase, key, gold, got in r["misses"][:5]:
            print(f"  {phrase!r} [{key}] gold={gold} vabamorf={got}")
    return 0 if r["agreement"] >= 0.95 else 1


def cmd_models(args: argparse.Namespace) -> int:
    """List a provider's live catalogue.

    Model ids get withdrawn silently, and a withdrawn ':free' id is especially
    easy to miss because the paid one with the same name keeps working. Probe
    before pinning.
    """
    from .providers.llm import PROVIDERS, list_models

    models = list_models(args.provider)
    free = [m for m in models if m.get("id", "").endswith(":free")]
    print(f"{args.provider}: {len(models)} models, {len(free)} free")
    shown = free if (free and not args.all) else models
    for m in sorted(shown, key=lambda x: -(x.get("context_length") or 0))[: args.limit]:
        params = m.get("supported_parameters") or []
        print(
            f"  {m['id']:52} ctx={str(m.get('context_length')):9}"
            f" json={'structured_outputs' in params}"
        )
    default = PROVIDERS[args.provider].default_model
    present = any(m.get("id") == default for m in models)
    print(f"\npinned default {default!r}: {'PRESENT' if present else 'ABSENT — fix it'}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    """Score a model on Estonian grammar.

    Two tracks. The default is the hand-written set: 18 sentences aimed at this
    learner's documented errors, half already correct so precision is real.
    `--track external` uses TalTech's grammar_et instead — 1000 real pairs the
    model has never seen, 88% of their vocabulary at A1-B1.
    """
    if args.track == "external":
        from .evals.external import run as run_external

        result = run_external(
            args.provider, model=args.model, sample=args.sample, seed=args.seed
        )
        if not result["valid"]:
            return 2
        return 0 if (result["accuracy"] or 0) >= 0.5 else 1

    from .evals.gec import run

    result = run(args.provider, model=args.model, evidence=args.evidence)
    # An unmeasurable run must not pass. Exit 2 distinguishes "could not
    # measure" from "measured and the model is not good enough" (exit 1).
    if not result["valid"]:
        return 2
    return 0 if result["recall"] >= 0.8 and result["precision"] >= 0.8 else 1


def cmd_evkk(args: argparse.Namespace) -> int:
    """Weight the curriculum by real learner errors, not just one person's log.

    Fetches the public EVKK error taxonomy (51 467 linguist-annotated errors in
    learner Estonian) and reports how the nine tags rank in it. One request,
    cached; the learner texts themselves are deliberately left alone.
    """
    from .config import CACHE
    from .harvest.evkk import fetch, store, tag_weights, unmapped
    from .sources import connect, register

    marks = fetch(cache=CACHE / "evkk_marks.html")
    weights = tag_weights(marks)
    rest = unmapped(marks)
    total = sum(weights.values()) + rest

    conn = connect(args.db)
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


def cmd_curriculum(args: argparse.Namespace) -> int:
    """Show the syllabus: the study path, and what can actually be practised.

    The path is derived from the prerequisite graph, not hand-written, so it
    cannot offer a case before the stem that case is built from.
    """
    from .curriculum import at_level, coverage, order, practice_order, validate

    from .curriculum import TOPICS

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


def cmd_cloze(args: argparse.Namespace) -> int:
    """Drill on sentences Estonians actually wrote, not on templates.

    The case is named in the prompt, so the answer is forced by morphology and
    nothing is claimed about which case the sentence needed — that is what makes
    an authentic sentence safe to grade.
    """
    import sqlite3

    from .cloze import case_clozes, negation_clozes, rection_clozes, sentences
    from .wordlist import connect as wordlist_connect

    content = sqlite3.connect(args.content_db)
    content.row_factory = sqlite3.Row
    sents = sentences(content)
    if not sents:
        print(f"no texts in {args.content_db} — run `cli harvest-reading` first")
        return 1

    words = wordlist_connect()
    topics = tuple(args.topics.split(",")) if args.topics else None
    if args.rule == "rection":
        from .rection import at_levels, load

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
    from .conjugation import FRAMES, generate
    from .wordlist import connect

    topics = tuple(args.topics.split(",")) if args.topics else None
    items = generate(
        connect(),
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
    from .patterns import comparison_drills, numeral_drills, question_drills
    from .wordlist import connect

    conn = connect()
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
    from . import handoff, review
    from .curriculum import by_id
    from .practice import items_for
    from .progress import (MASTERY_CORRECT, MASTERY_WINDOW, accuracy, connect,
                           is_mastered, record, resume)

    progress = connect(args.progress_db)
    reviews = review.connect(args.review_db)
    topic = args.topic or resume(progress)
    if topic is None:
        print("nothing available to practise — every unlocked topic is mastered.")
        return 0

    meta = by_id(topic)
    header = f"\n{meta.level}  {meta.et}  ({meta.ru})"
    if args.theme:
        from .themes import by_id as theme_by_id

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


def cmd_progress(args: argparse.Namespace) -> int:
    """Where you stand on every topic, in study order."""
    from .progress import connect, report, resume

    progress = connect(args.progress_db)
    rows = report(progress)
    level = None
    for row in rows:
        if args.todo and row.state in ("mastered", "locked"):
            continue
        if row.level != level:
            level = row.level
            print(f"\n{level}")
        acc = f"{row.accuracy:.0%}" if row.accuracy is not None else "  -"
        blocked = f"  <- {', '.join(row.blocked_by)}" if row.blocked_by else ""
        print(f"  {row.state:<12} {row.topic:<16} {row.et[:30]:<32}"
              f" n={row.attempts:<4} {acc:>4}{blocked}")

    done = sum(1 for r in rows if r.state == "mastered")
    print(f"\n{done}/{len(rows)} topics mastered.")
    nxt = resume(progress)
    print(f"next: {nxt}" if nxt else "next: nothing unlocked to practise")
    return 0


def _ask_terminal(item) -> str:
    print(f"\n   {item.prompt}")
    print(f"   ({item.hint})")
    try:
        return input("   > ")
    except (EOFError, KeyboardInterrupt):
        return ""


def cmd_placement(args: argparse.Namespace) -> int:
    """Find where to start, instead of starting at lesson one.

    Walks the syllabus in study order, probing each topic with a short set, and
    stops once failures accumulate. It places you; it does not audit you — use
    `test-out --topic X` for any single topic you already know.
    """
    from .placement import PROBE_ITEMS, PROBE_REQUIRED, entry_points, sweep
    from .progress import connect

    progress = connect(args.progress_db)
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
    from .curriculum import by_id
    from .placement import PROBE_REQUIRED, probe
    from .progress import connect

    progress = connect(args.progress_db)
    meta = by_id(args.topic)
    print(f"\nTest-out: {meta.level}  {meta.et}")

    result = probe(progress, args.topic, _ask_terminal, seed=args.seed)
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
    from . import handoff, review
    from .progress import connect as progress_connect

    reviews = review.connect(args.review_db)
    progress = progress_connect(args.progress_db)

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


def cmd_themes(args: argparse.Namespace) -> int:
    """The situations a grammar topic can be drilled inside.

    Keeleklikk's insight — grammar arrives in service of a situation — but with
    theme and rule as separate axes, so eleven themes times twenty-one drillable
    topics come out of the same generators.
    """
    from .themes import coverage, validate
    from .wordlist import connect

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
    import sqlite3

    from .library import browse, exposure, sections
    from .progress import connect as progress_connect

    content = sqlite3.connect(args.content_db)
    content.row_factory = sqlite3.Row

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
        from .library import open_item
        from .vocab import connect as vocab_connect

        progress = progress_connect(args.progress_db)
        vocabulary = vocab_connect(args.vocab_db)
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
    from .vocab import (KNOWN, STATUS_NAMES, WELL_KNOWN, band_progress, connect,
                        set_status, summary)
    from .wordlist import connect as wordlist_connect

    vocabulary = connect(args.vocab_db)
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
    import sqlite3

    from .overview import overview
    from .progress import connect as progress_connect
    from .review import connect as review_connect
    from .vocab import connect as vocab_connect
    from .wordlist import connect as wordlist_connect

    content = sqlite3.connect(args.content_db)
    content.row_factory = sqlite3.Row
    data = overview(
        progress=progress_connect(args.progress_db),
        reviews=review_connect(args.review_db),
        vocabulary=vocab_connect(args.vocab_db),
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


def cmd_checkpoint(args: argparse.Namespace) -> int:
    """A mixed quiz across a whole level — interleaved by construction."""
    from .checkpoint import DEFAULT_ITEMS, PASS_MARK, ready, run, topics_at
    from .progress import connect as progress_connect
    from .review import connect as review_connect

    progress = progress_connect(args.progress_db)
    reviews = review_connect(args.review_db)

    topics = topics_at(args.level)
    if not topics:
        print(f"no drillable topics at {args.level}")
        return 1
    if not ready(progress, args.level) and not args.force:
        from .progress import mastered

        missing = sorted(set(topics) - mastered(progress))
        print(f"{args.level} is not finished yet — still to master: "
              f"{', '.join(missing)}")
        print("Run it anyway with --force; it is a diagnosis, not a gate.")
        return 1

    print(f"\n{args.level} checkpoint: {args.count} questions across "
          f"{len(topics)} topics, mixed.\nNo hint which rule applies — that is "
          "the point.\n")
    result = run(progress, args.level, _ask_terminal, count=args.count,
                 seed=args.seed, reviews=reviews)
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


def cmd_rections(args: argparse.Namespace) -> int:
    """Fetch EKK's list of error-prone rections, once, and store it.

    Deliberate and separate from practice: a lesson must never depend on EKI
    being reachable. One page, cached on disk, stored in the word database.
    """
    from .config import CACHE
    from .rection import at_levels, fetch, load, store
    from .wordlist import connect

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
    p.add_argument(
        "--rules", nargs="+",
        help="completed | ongoing | negation | verb-form",
    )
    p.add_argument("--seed", type=int)
    p.set_defaults(func=cmd_drill)

    p = sub.add_parser("check", help="grammar-check a sentence")
    p.add_argument("text")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("export", help="build the edge dataset for Cloudflare D1")
    p.add_argument("--max-freq-rank", type=int, default=25_000)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("keys", help="show which API keys are configured")
    p.set_defaults(func=cmd_keys)

    p = sub.add_parser("harvest", help="crawl ERR language archives (one time)")
    p.add_argument("--max-pages", type=int, default=300)
    p.add_argument("--db", default="data/content.db")
    p.set_defaults(func=cmd_harvest)

    p = sub.add_parser("harvest-reading", help="harvest simplified Estonian texts")
    p.add_argument("--limit", type=int)
    p.add_argument("--db", default="data/content.db")
    p.set_defaults(func=cmd_harvest_reading)

    p = sub.add_parser("cloze", help="drill on real harvested sentences")
    p.add_argument("-n", "--count", type=int, default=10)
    p.add_argument("--topics", help="comma-separated curriculum topic ids")
    p.add_argument("--rule", choices=("case-form", "negation", "rection"),
                   default="case-form")
    p.add_argument("--levels", default="A1,A2,B1",
                   help="rection only: CEFR levels of the governing word")
    p.add_argument("--answers", action="store_true", help="show answers")
    p.add_argument("--seed", type=int)
    p.add_argument("--content-db", default="data/content.db")
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
    p.add_argument("--progress-db", default="data/progress.db")
    p.add_argument("--review-db", default="data/review.db")
    p.set_defaults(func=cmd_practice)

    p = sub.add_parser("progress", help="where you stand on every topic")
    p.add_argument("--todo", action="store_true", help="hide mastered and locked")
    p.add_argument("--progress-db", default="data/progress.db")
    p.set_defaults(func=cmd_progress)

    p = sub.add_parser("placement", help="find where to start in the syllabus")
    p.add_argument("--seed", type=int)
    p.add_argument("--progress-db", default="data/progress.db")
    p.set_defaults(func=cmd_placement)

    p = sub.add_parser("test-out", help="skip one topic by demonstrating it")
    p.add_argument("--topic", required=True)
    p.add_argument("--seed", type=int)
    p.add_argument("--progress-db", default="data/progress.db")
    p.set_defaults(func=cmd_test_out)

    p = sub.add_parser("review", help="interleaved review of whatever is due")
    p.add_argument("-n", "--count", type=int, default=20)
    p.add_argument("--review-db", default="data/review.db")
    p.add_argument("--progress-db", default="data/progress.db")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("themes", help="themed word sets a topic can be drilled over")
    p.add_argument("--levels", default="A1,A2,B1")
    p.set_defaults(func=cmd_themes)

    p = sub.add_parser("library", help="browse material: ungated, unordered")
    p.add_argument("--section", choices=("lugemine", "kuulamine", "saated", "eksam"))
    p.add_argument("--level")
    p.add_argument("-n", "--count", type=int, default=15)
    p.add_argument("--seen", action="store_true", help="record these as opened")
    p.add_argument("--minutes", type=float, default=0.0)
    p.add_argument("--content-db", default="data/content.db")
    p.add_argument("--progress-db", default="data/progress.db")
    p.add_argument("--vocab-db", default="data/vocab.db")
    p.set_defaults(func=cmd_library)

    p = sub.add_parser("vocab", help="words you know, by frequency band")
    p.add_argument("--know", nargs="*", help="mark these lemmas as known")
    p.add_argument("--long-known", action="store_true",
                   help="mark as well known rather than newly known")
    p.add_argument("--vocab-db", default="data/vocab.db")
    p.set_defaults(func=cmd_vocab)

    p = sub.add_parser("status", help="where you stand, section by section")
    p.add_argument("--content-db", default="data/content.db")
    p.add_argument("--progress-db", default="data/progress.db")
    p.add_argument("--review-db", default="data/review.db")
    p.add_argument("--vocab-db", default="data/vocab.db")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("checkpoint", help="mixed end-of-level quiz")
    p.add_argument("--level", default="A1", choices=list(LEVELS))
    p.add_argument("-n", "--count", type=int, default=15)
    p.add_argument("--force", action="store_true")
    p.add_argument("--seed", type=int)
    p.add_argument("--progress-db", default="data/progress.db")
    p.add_argument("--review-db", default="data/review.db")
    p.set_defaults(func=cmd_checkpoint)

    p = sub.add_parser("rections", help="fetch and store EKK's rection table (once)")
    p.add_argument("--levels", default="A1,A2,B1")
    p.set_defaults(func=cmd_rections)

    p = sub.add_parser("curriculum", help="show the A1-B1 syllabus and study path")
    p.add_argument("--level", choices=list(LEVELS))
    p.add_argument("--priority", action="store_true",
                   help="rank by learner-corpus error frequency instead")
    p.add_argument("--limit", type=int, default=12)
    p.set_defaults(func=cmd_curriculum)

    p = sub.add_parser("evkk", help="rank error tags by real learner-corpus data")
    p.add_argument("--db", default="data/content.db")
    p.set_defaults(func=cmd_evkk)

    p = sub.add_parser("fetch-bench", help="download the Estonian benchmark datasets")
    p.set_defaults(func=cmd_fetch_bench)

    p = sub.add_parser("validate", help="check Vabamorf against native gold forms")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("models", help="list a provider's live model catalogue")
    p.add_argument("--provider", default="openrouter", choices=list(_PROVIDERS))
    p.add_argument("--all", action="store_true", help="include paid models")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_models)

    p = sub.add_parser("eval", help="score a model on the Estonian grammar eval")
    p.add_argument("--provider", default="openrouter", choices=list(_PROVIDERS))
    p.add_argument("--model")
    p.add_argument(
        "--evidence", action="store_true",
        help="attach Vabamorf's case analysis, as the real app does",
    )
    p.add_argument(
        "--track", choices=("hand", "external"), default="hand",
        help="hand = 18 targeted sentences; external = TalTech grammar_et",
    )
    p.add_argument("--sample", type=int, default=30, help="external track only")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("serve", help="run the local web app")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
