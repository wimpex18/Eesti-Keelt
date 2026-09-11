"""Building what the app runs on: the word list, the index, the edge dataset.

Also the commands that report on the build rather than change it — which keys
are configured, how Vabamorf scores against native gold forms, and what a
provider's live model catalogue contains.
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

from ..config import LEVELS

#: Providers whose model listing is a selection rather than an inventory, so
#: "the pinned id is not in the list" does not mean the pin is broken.
PARTIAL_CATALOGUE = frozenset({"huggingface"})


def _providers() -> tuple[str, ...]:
    """Every provider the client actually knows, asked at parser-build time.

    This was a hand-written tuple, and it had drifted in both directions at
    once: it offered `huggingface`, which `llm.PROVIDERS` did not contain, so
    `--provider huggingface` was an accepted choice that could only ever raise
    `KeyError`; and it omitted `local`, so the one lane running an
    Estonian-adapted model was the one lane the eval could not score -- on the
    command whose entire job is to find out whether a model is any good at
    Estonian.

    A hand-maintained list of things that exist elsewhere is this project's
    most-repeated bug, and unlike `api.ROUTERS` or `cli.GROUPS` this one carries
    no ordering decision, so there is nothing to preserve by hand. Imported
    inside the function, not at module load, so the CLI stays importable
    without the provider dependencies installed.
    """
    from ..providers.llm import PROVIDERS

    return tuple(PROVIDERS)

WORDLIST_BASE = (
    "https://raw.githubusercontent.com/KristjanPikhof/"
    "Estonian-Wordlist-Enriched-Ekilex/main/data"
)
# Only the small CEFR/frequency table is needed. The 79 MB inflected-forms file
# is deliberately skipped: its form lists are de-duplicated, so position cannot
# be mapped to a case. Vabamorf synthesis supplies labelled forms instead.
WORDLIST_FILES = ("est_words_160k.tsv",)

def cmd_fetch_data(args: argparse.Namespace) -> int:
    from .. import config

    config.RAW.mkdir(parents=True, exist_ok=True)
    for name in WORDLIST_FILES:
        dest = config.RAW / name
        if dest.exists() and not args.force:
            print(f"  {name}: already present ({dest.stat().st_size:,} bytes)")
            continue
        print(f"  {name}: downloading...", flush=True)
        urllib.request.urlretrieve(f"{WORDLIST_BASE}/{name}", dest)
        print(f"  {name}: {dest.stat().st_size:,} bytes")
    print("Source: Estonian-Wordlist-Enriched-Ekilex (CC-BY-SA-4.0), from Ekilex/EKI.")
    return 0


def cmd_import_levels(args: argparse.Namespace) -> int:
    """Replace the derived CEFR estimates with the exam board institute's own.

    Not a download. `arhiiv.eki.ee/litsents/` asks who you are and what the
    material will be used in before it hands the file over — a request worth
    answering rather than stepping around — so this takes a path to the file
    the learner fetched, and says so when the path is wrong.
    """
    from collections import Counter

    from ..wordlist import LEVELS, connect

    path = Path(args.file)
    if not path.exists():
        print(f"{path} not found.")
        print("Download `A1A2B1.txt` from https://arhiiv.eki.ee/litsents/ "
              "(Eesti keele tasemete sõnavara, CC BY 4.0) and pass its path.")
        print("Put it in `deploy/eki/` and the image build imports it too — "
              "see deploy/eki/README.md.")
        return 1

    from ..wordlist import import_official_levels, read_official_levels

    # `--check` reads the file and reports, touching no database. The import is
    # the one command here that rewrites the CEFR level of every word the app
    # drills, and it runs against a file this project has never seen — EKI
    # serves it behind a form, so it arrives from the learner. Being able to
    # look before writing is worth twenty lines.
    if args.check:
        try:
            rows = read_official_levels(path)
        except ValueError as exc:
            print(exc)
            return 1
        by_level = Counter(r[1] for r in rows)
        phrases = [r[0] for r in rows if " " in r[0]]
        codes = Counter(r[2] for r in rows)
        from ..wordlist import EKI_POS

        print(f"  {len(rows):,} distinct lemmas, duplicates collapsed to their "
              f"lowest level")
        for level in LEVELS:
            print(f"    {level}: {by_level.get(level, 0):,}")
        print(f"  {len(phrases):,} multi-word entries — kept as vocabulary, "
              f"never drilled (e.g. {', '.join(phrases[:3]) or 'none'})")
        unknown = sorted(c for c in codes if c and c not in EKI_POS)
        print(f"  part-of-speech codes: {', '.join(sorted(c for c in codes if c))}")
        if unknown:
            print(f"  UNMAPPED codes {unknown} — they will be stored as "
                  f"non-declinable; add them to wordlist.EKI_POS if that is wrong")
        print("  Nothing was written. Drop --check to import.")
        return 0

    conn = connect()

    try:
        stats = import_official_levels(conn, path)
    except ValueError as exc:
        print(exc)
        return 1

    print(f"  {stats['levelled']:,} words levelled by EKI")
    for level in LEVELS:
        print(f"    {level}: {stats.get(level, 0):,}")
    print(f"  {stats['added']:,} words new to the word list")
    print(f"  {stats['phrases']:,} multi-word entries kept out of the drill pool")
    print(f"  {stats['changed']:,} levels that disagreed with the enriched list")
    print("  Source: Eesti keele tasemete sõnavara (2018), EKI, CC BY 4.0.")
    print("  Survives `cli build`: the levels are re-applied from their own table.")
    return 0


def cmd_import_psv(args: argparse.Namespace) -> int:
    """Give the word card a definition a learner can read.

    Not a download, for the same reason `import-levels` is not: EKI asks who
    you are and what the material will be used in before handing the file over.
    """
    from .. import psv
    from ..wordlist import connect

    path = Path(args.file)
    if not path.exists():
        print(f"{path} not found.")
        print("Download `psv_EKI_CCBY40.xml` from https://arhiiv.eki.ee/litsents/ "
              "(Eesti keele põhisõnavara sõnastik 2014, CC BY 4.0) and pass its path.")
        print("Put it in `deploy/eki/` and the image build imports it too — "
              "see deploy/eki/README.md.")
        return 1

    try:
        entries = psv.parse(path)
    except Exception as exc:  # noqa: BLE001 - a bad file is not a traceback
        print(f"{path} could not be parsed as EKI dictionary XML: {exc}")
        print("Expected the `sr` / `A` structure described in schema_psv.xsd.")
        return 1
    if not entries:
        print(f"{path} parsed but held no articles — is this the right file?")
        return 1

    conn = connect()
    stats = psv.store(conn, entries)
    print(f"  {stats['entries']:,} articles read")
    print(f"  {stats['written']:,} with a definition or examples, stored")
    print(f"  {stats.get('with_examples', 0):,} carry usage examples")
    print(f"  {psv.imported(conn):,} words now have a learner-level definition")
    print("  Source: Eesti keele põhisõnavara sõnastik 2014, EKI, CC BY 4.0.")
    print("  Stored beside the word list, not in `vocab.db`: reference data, and")
    print("  a state-snapshot restore would otherwise wipe it on the next cold start.")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    from ..wordlist import build, connect, index_object_cases

    conn = connect()
    from .. import config

    print(f"Importing word list into {config.DB_PATH} ...")
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


def cmd_export(args: argparse.Namespace) -> int:
    """Build the edge dataset. Vabamorf runs here, never at the edge."""
    from ..export import export
    from ..wordlist import connect

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
    from ..env import ENV_FILE, describe

    print(f".env: {ENV_FILE} {'(found)' if ENV_FILE.exists() else '(missing)'}\n")
    for name, is_set, masked, purpose in describe():
        mark = "✓" if is_set else " "
        print(f" {mark} {name:24} {masked:10} {purpose}")
    if not any(s for _, s, _, _ in describe()):
        print("\nNo keys set. `cp .env.example .env` and add one — "
              "OpenRouter is the recommended starting point:")
        print("  https://openrouter.ai/keys")
    return 0


def cmd_fetch_bench(args: argparse.Namespace) -> int:
    """Download the public Estonian benchmark datasets (TalTechNLP, LREC 2026).

    Fails only on a dataset something depends on. The two word-order pools are
    optional by construction — fewer pairs is fewer drill items, which the
    module already handles — and treating them as fatal is what once skipped
    the morphology gate over a file that had downloaded perfectly.
    """
    from ..evals.fetch import REQUIRED, fetch_all

    counts, failures = fetch_all(required_only=args.required_only)
    for name, count in counts.items():
        print(f"  {name}: {count:,} rows")
    for name, why in failures.items():
        mark = "ERROR" if name in REQUIRED else "skipped"
        print(f"  {name}: {mark} — {why}")
    fatal = sorted(n for n in failures if n in REQUIRED)
    if fatal:
        print(f"Required dataset(s) unavailable: {', '.join(fatal)}.")
        return 1
    if failures:
        print("  The word-order pool will be smaller. Re-run to fill it.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Check Vabamorf against native-curated gold forms.

    Everything this app generates inherits Vabamorf's correctness, so this is the
    check that the foundation is sound.
    """
    from ..evals.morphology import run

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
    from ..providers.llm import PROVIDERS, list_models

    models = list_models(args.provider)
    free = [m for m in models if m.get("id", "").endswith(":free")]
    print(f"{args.provider}: {len(models)} models, {len(free)} free")
    # Free-only unless asked, and *say* when that is not what you are seeing.
    #
    # The fallback is deliberate -- a catalogue with no `:free` ids at all is
    # worth looking at, because that is precisely the moment a pin has to move.
    # What was wrong is that it happened silently: this app runs on free tiers,
    # so a paid list printed under the same heading as a free one is a list you
    # could pin from by mistake.
    shown = free if (free and not args.all) else models
    if shown is models and not args.all:
        print("  (no `:free` ids in this catalogue — showing paid ones, which "
              "this app does not use; a pin from here needs a decision)")
    for m in sorted(shown, key=lambda x: -(x.get("context_length") or 0))[: args.limit]:
        params = m.get("supported_parameters") or []
        print(
            f"  {m['id']:52} ctx={str(m.get('context_length')):9}"
            f" json={'structured_outputs' in params}"
        )
    default = PROVIDERS[args.provider].model
    if args.provider in PARTIAL_CATALOGUE:
        # Some catalogues are not an inventory of what is callable. The HF
        # router's `/v1/models` returns ~135 warm models; a model reachable
        # through an inference-provider mapping is routable without appearing
        # there at all -- `tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125` is
        # mapped to featherless-ai and is absent from that list.
        #
        # So "ABSENT -- fix it" here would be a false alarm on the one lane
        # this project most wants to run, printed by the very step the eval
        # workflow uses to sanity-check a pin. The question this command exists
        # to answer -- has the id been silently withdrawn? -- is a real question
        # for OpenRouter's `:free` aliases and is one this endpoint cannot
        # answer. Saying so beats answering it wrongly.
        print(f"\npinned default {default!r}: NOT ANSWERABLE HERE — "
              f"{args.provider} lists warm models only, not everything routable. "
              f"Check https://huggingface.co/{default}")
        return 0
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
        from ..evals.external import run as run_external

        result = run_external(
            args.provider, model=args.model, sample=args.sample, seed=args.seed
        )
        if not result["valid"]:
            return 2
        return 0 if (result["accuracy"] or 0) >= 0.5 else 1

    from ..evals.gec import run

    result = run(args.provider, model=args.model, evidence=args.evidence)
    # An unmeasurable run must not pass. Exit 2 distinguishes "could not
    # measure" from "measured and the model is not good enough" (exit 1).
    if not result["valid"]:
        return 2
    return 0 if result["recall"] >= 0.8 and result["precision"] >= 0.8 else 1


def register(sub) -> None:
    """Add this group's commands to the subparser table.

    Beside the handlers rather than a thousand lines away in one
    argparse block: a flag and the code that reads it drift apart
    when they cannot be seen together.
    """
    p = sub.add_parser("fetch-data", help="download the word list")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_fetch_data)

    p = sub.add_parser("build", help="import and index")
    p.add_argument("--levels", nargs="+", default=list(LEVELS))
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("export", help="build the edge dataset for Cloudflare D1")
    p.add_argument("--max-freq-rank", type=int, default=25_000)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser(
        "import-levels",
        help="import EKI's official A1/A2/B1 level vocabulary (a file you downloaded)",
    )
    p.add_argument("file", help="A1A2B1.txt from arhiiv.eki.ee/litsents")
    p.add_argument("--check", action="store_true",
                   help="report what the file holds and write nothing")
    p.set_defaults(func=cmd_import_levels)

    p = sub.add_parser(
        "import-psv",
        help="import EKI's learner dictionary definitions (a file you downloaded)",
    )
    p.add_argument("file", help="psv_EKI_CCBY40.xml from arhiiv.eki.ee/litsents")
    p.set_defaults(func=cmd_import_psv)

    p = sub.add_parser("keys", help="show which API keys are configured")
    p.set_defaults(func=cmd_keys)

    p = sub.add_parser("validate", help="check Vabamorf against native gold forms")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("fetch-bench", help="download the Estonian benchmark datasets")
    p.add_argument(
        "--required-only", action="store_true",
        help="only what the morphology gate and the eval track need — skips "
             "the two extra word-order pools, which nothing in CI reads")
    p.set_defaults(func=cmd_fetch_bench)

    p = sub.add_parser("models", help="list a provider's live model catalogue")
    p.add_argument("--provider", default="openrouter", choices=list(_providers()))
    p.add_argument("--all", action="store_true", help="include paid models (this app runs on free tiers)")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_models)

    p = sub.add_parser("eval", help="score a model on the Estonian grammar eval")
    p.add_argument("--provider", default="openrouter", choices=list(_providers()))
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
