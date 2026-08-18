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
