"""Second eval track: TalTech's grammar_et, 1 000 real error/correct pairs.

Why both tracks
---------------
`gec.py` is 18 hand-written sentences aimed at *this* learner's documented
errors, half of them already correct so precision is measurable. It is targeted
and small.

`grammar_et` is 1 000 pairs from the Estonian Native LLM Benchmark (LREC 2026),
written by other people about other things. Measured against our CEFR word list,
**88 % of its vocabulary is A1–B1** and the median sentence is 13 words — so it
is at the right level, not an advanced-writing corpus. Its errors are the same
classes the error log tracks:

    ülikoolid → ülikoole      object case
    käigul → käigus           locative case
    inimesteid → inimesi      plural partitive
    täiusliku → täiuslikuks   translative

Targeted and broad answer different questions. A model can look good on 18
sentences by luck; 1 000 pairs it has never seen is harder to fake.

Scoring
-------
Exact sentence match would be too harsh — there are several valid ways to fix a
sentence, and a model that also improves the style is not wrong. So we score
**token-level**: which words differ between original and gold, and did the model
change those words to those values.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from ..config import DATA
from ..providers.llm import complete, parse_json
from .gec import SYSTEM

DATASET = DATA / "raw" / "bench" / "grammar_et.json"
URL = "https://huggingface.co/datasets/TalTechNLP/grammar_et"


# A targeted correction changes one or two words. Beyond that the "correction"
# is usually a rewrite, and positional alignment stops being meaningful.
MAX_CHANGES = 2

_PUNCT = ".,;:!?\"'()«»"


def changed_tokens(original: str, correct: str) -> dict[str, str]:
    """Words that differ between the erroneous and corrected sentence.

    Positional alignment, which is right for substitutions — the dominant error
    type in this corpus — and returns nothing for the cases where it would lie:

    * different lengths (an insertion or deletion);
    * **word reorderings**, which align as a cascade of bogus substitutions.
      A swap like "tuleb rahvas" → "rahvas tuleb" reads positionally as
      `tuleb→rahvas` and `rahvas→tuleb`, neither of which is a correction. If
      the two sentences contain the same words, nothing was substituted.
    * more than `MAX_CHANGES` differences, which indicates a rewrite rather
      than a targeted error.
    """
    before, after = original.split(), correct.split()
    if len(before) != len(after):
        return {}

    # Punctuation travels with the token, so "lõpeb" and "lõpeb." look like
    # different words and a swap of the two slips past a naive comparison.
    # Reordering checks therefore compare bare words.
    bare_before = [w.strip(_PUNCT).lower() for w in before]
    bare_after = [w.strip(_PUNCT).lower() for w in after]
    if sorted(bare_before) == sorted(bare_after):  # pure reordering
        return {}

    changes = {b: a for b, a in zip(before, after) if b != a}
    if len(changes) > MAX_CHANGES:
        return {}
    # A "change" whose target already appears in the original is a shuffled
    # word, not a fix.
    if any(t.strip(_PUNCT).lower() in bare_before for t in changes.values()):
        return {}
    return changes


def load(path: Path | None = None) -> list[dict]:
    path = Path(path or DATASET)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — run `python -m eesti.cli fetch-bench`.\nSource: {URL}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    provider: str,
    model: str | None = None,
    sample: int = 30,
    seed: int = 0,
    verbose: bool = True,
) -> dict:
    """Score a model on a sample of grammar_et.

    Default sample is small on purpose: OpenRouter's free tier allows 50
    requests a day, and an eval that cannot finish tells you nothing.
    """
    rows = load()
    scorable = [
        (r, changed) for r in rows
        if (changed := changed_tokens(r["original"], r["correct"]))
    ]
    rng = random.Random(seed)
    rng.shuffle(scorable)
    chosen = scorable[:sample]

    caught = missed = broken = 0
    spurious = 0
    failures: list[tuple[str, str]] = []

    for row, changed in chosen:
        try:
            result = parse_json(complete(provider, SYSTEM, row["original"], model=model))
        except Exception as exc:
            broken += 1
            failures.append((row["original"], f"ERROR {type(exc).__name__}"))
            continue

        proposed = {
            (c.get("wrong") or "").strip(): (c.get("correct") or "").strip()
            for c in result.get("corrections", [])
        }
        hit = any(
            wrong in proposed and proposed[wrong] == right
            for wrong, right in changed.items()
        )
        if hit:
            caught += 1
        else:
            missed += 1
            if len(failures) < 8:
                failures.append((
                    row["original"][:70],
                    f"expected {changed}, got {proposed or '{}'}",
                ))
        # Changes to words that were already correct.
        spurious += sum(1 for w in proposed if w not in changed)

    answered = caught + missed
    usable = broken < len(chosen) * 0.25
    score = {
        "track": "grammar_et",
        "provider": provider,
        "model": model or "default",
        "sample": len(chosen),
        "answered": answered,
        "caught": f"{caught}/{answered}" if answered else "0/0",
        "accuracy": round(caught / answered, 3) if (usable and answered) else None,
        "spurious_edits": spurious,
        "broken": broken,
        "valid": usable,
    }
    if not usable:
        score["invalid_reason"] = (
            f"{broken}/{len(chosen)} cases never reached the model — no score"
        )

    if verbose:
        print(json.dumps({k: v for k, v in score.items()}, indent=2, ensure_ascii=False))
        for sentence, why in failures:
            print(f"  ✗ {sentence}\n      {why}")
    return score
