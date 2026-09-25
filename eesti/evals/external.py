"""Second eval track: TalTech's grammar_et, 1 000 real error/correct pairs.

`gec.py` is 18 targeted sentences written for this app's weakness; `grammar_et`
(Estonian Native LLM Benchmark, LREC 2026) is broad, attested and large enough
to say something per error class. Nothing here is invented: the sentences and
their corrections are the dataset's.

Two halves, as in `gec.py`:

- **recall** — of sentences with a real error, how many were caught, reported
  per category (object case, locative, plural, verb form, word order, other);
- **precision** — the same dataset's *corrected* sentences are correct
  Estonian, so flagging one is a false positive. A checker that flags every
  partitive scores perfect recall and teaches the wrong rule.

Error classes in the data:

    ülikoolid → ülikoole      object case
    käigul → käigus           locative case
    inimesteid → inimesi      plural partitive
    täiusliku → täiuslikuks   translative

Scored **token-level** — did the model change the words that differ between
original and gold to the gold values — because several whole-sentence fixes can
be valid.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from ..config import DATA
from ..providers.grammar import why_failed
from .gec import _ask

DATASET = DATA / "raw" / "bench" / "grammar_et.json"
URL = "https://huggingface.co/datasets/TalTechNLP/grammar_et"


# A targeted correction changes one or two words. Beyond that the "correction"
# is usually a rewrite, and positional alignment stops being meaningful.
MAX_CHANGES = 2

_PUNCT = ".,;:!?\"'()«»"


def _bare(word: str) -> str:
    """A token as the scorer compares it: no edge punctuation, case folded."""
    return word.strip().strip(_PUNCT).casefold()


def changed_tokens(original: str, correct: str) -> dict[str, str]:
    """Words that differ between the erroneous and corrected sentence.

    Positional alignment, right for substitutions. Returns nothing for different
    lengths, for reorderings (same words: nothing was substituted), and for more
    than `MAX_CHANGES` differences (a rewrite).
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


#: Which rule an attested correction is about, decided by morphology so the
#: category is the data's, not a label someone wrote.
def category(wrong: str, right: str) -> str:
    """The error class of one attested change (`obj-case`, `loc-case`, ...)."""
    from ..morph import _readings

    forms_wrong = {f for _, f in _readings(wrong)}
    forms_right = {f for _, f in _readings(right)}
    lemmas = ({lemma for lemma, _ in _readings(wrong)}
              & {lemma for lemma, _ in _readings(right)})
    part, gen = {"sg p", "pl p"}, {"sg g", "pl g", "sg n", "pl n"}
    locative = {"sg in", "pl in", "sg el", "pl el", "sg ill", "pl ill",
                "sg ad", "pl ad", "sg all", "pl all", "sg abl", "pl abl"}
    if not forms_wrong:
        # Vabamorf does not know the written form at all: a misspelling, which
        # the deterministic checker owns.
        return "spelling"
    if lemmas and ((forms_wrong & gen and forms_right & part)
                   or (forms_wrong & part and forms_right & gen)):
        return "obj-case"
    if lemmas and (forms_wrong & locative or forms_right & locative):
        return "loc-case"
    if lemmas and ({f.split()[0] for f in forms_wrong if f[:2] in ("sg", "pl")}
                   != {f.split()[0] for f in forms_right if f[:2] in ("sg", "pl")}):
        return "number"
    if lemmas and any(f.startswith(("sin", "b", "d ", "vad", "n ")) for f in forms_right):
        return "verb-form"
    return "other"


def run(
    provider: str,
    model: str | None = None,
    sample: int = 30,
    seed: int = 0,
    verbose: bool = True,
) -> dict:
    """Score a lane on a sample of grammar_et: recall per error class, and
    precision on the dataset's own corrected sentences.

    The default sample is small so a free-tier daily quota can finish it; the
    weekly run uses more.
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
    by_class: dict[str, list[int]] = {}

    for row, changed in chosen:
        try:
            result = _ask(provider, row["original"], model, False)
        except Exception as exc:  # noqa: BLE001 - a dead lane is a reported state
            broken += 1
            failures.append((row["original"], f"ERROR {why_failed(exc)}"))
            continue

        # Compared as bare words: `kõigele` -> `kõigile` fixes the pair the
        # corpus writes as `kõigele.` -> `kõigile.`, and a capital at the start
        # of a sentence is not a different correction.
        proposed = {
            _bare(c.get("wrong") or ""): _bare(c.get("correct") or "")
            for c in result.get("corrections", [])
        }
        changed = {_bare(wrong): _bare(right) for wrong, right in changed.items()}
        hit = any(
            wrong in proposed and proposed[wrong] == right
            for wrong, right in changed.items()
        )
        # Which rule this pair is about, so a lane's weakness has a name.
        for wrong, right in changed.items():
            tally = by_class.setdefault(category(wrong, right), [0, 0])
            tally[1] += 1
            tally[0] += int(proposed.get(wrong, "") == right)
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

    # Precision: the dataset's corrected sentences are correct Estonian, so any
    # correction proposed on one is a false flag.
    clean = [r["correct"] for r, _ in scorable[sample:sample + max(5, sample // 2)]]
    false_flags = clean_answered = 0
    for sentence in clean:
        try:
            result = _ask(provider, sentence, model, False)
        except Exception:  # noqa: BLE001 - counted as unanswered, never as clean
            continue
        clean_answered += 1
        if result.get("corrections"):
            false_flags += 1
            if len(failures) < 12:
                failures.append((sentence[:70], "false flag on a correct sentence"))

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
        "by_class": {name: {"caught": hit, "of": n,
                            "recall": round(hit / n, 3) if n else None}
                     for name, (hit, n) in sorted(by_class.items())},
        "clean_sentences": clean_answered,
        "false_flags": false_flags,
        "precision": (round(1 - false_flags / clean_answered, 3)
                      if (usable and clean_answered) else None),
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
