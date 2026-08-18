"""Estonian grammar eval: does this model actually know Estonian?

The tempting assumption is that a model strong in English or Russian is
automatically usable for Estonian. It is a reasonable hypothesis and it is
testable, so this tests it rather than assuming either way.

Estonian is low-resource, and the specific judgement this app needs — whether an
object should be genitive (completed, whole) or partitive (ongoing, partial,
negated) — depends on aspect, which is exactly the kind of language-specific
semantics that thins out in a multilingual model's training data.

Two scores, and the second is the one that separates models:

  recall     — of the sentences that DO contain a planted error, how many were caught
  precision  — of the sentences that are ALREADY CORRECT, how many were left alone

A model that flags everything scores perfect recall and is worse than useless: it
would teach the learner that every partitive is a mistake. Half the eval set is
deliberately correct Estonian for that reason.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..config import TAGS
from ..providers.llm import complete, parse_json

SYSTEM = """\
You are an Estonian grammar checker for a Russian-speaking learner at A2-B1 level.

Return ONLY valid JSON: {"corrections":[{"wrong":"...","correct":"...","tag":"..."}]}

- "wrong" must be an exact substring of the input.
- "tag" must be one of: %s
- Use "obj-case" for genitive/partitive/nominative object-case errors.
- If the sentence is already correct, return {"corrections":[]}.
- Do NOT flag stylistic preferences. Only real grammatical errors.
""" % ", ".join(TAGS)


@dataclass(frozen=True)
class Case:
    """One eval item. `wrong` is None when the sentence is already correct."""

    sentence: str
    wrong: str | None      # the token that must be flagged
    correct: str | None    # what it should become
    tag: str | None
    note: str


CASES: tuple[Case, ...] = (
    # ---- planted obj-case errors: partitive where genitive is required -------
    Case("Ma lugesin eile selle raamatut läbi.", "raamatut", "raamatu",
         "obj-case", "completed action + 'läbi' -> total object, genitive"),
    Case("Ma ostsin eile uut autot ära.", "autot", "auto",
         "obj-case", "'ära' marks completion -> genitive"),
    Case("Ma sõin õunat ära.", "õunat", "õuna",
         "obj-case", "eaten whole -> genitive"),
    Case("Homme ma teen seda tööd valmis.", "tööd", "töö",
         "obj-case", "'valmis' = result achieved -> genitive"),
    Case("Ta leidis oma võtit üles.", "võtit", "võtme",
         "obj-case", "found completely -> genitive"),

    # ---- planted obj-case errors: genitive where partitive is required -------
    Case("Ma ei ostnud pileti.", "pileti", "piletit",
         "obj-case", "negation always takes partitive"),
    Case("Ta luges raamatu terve õhtu.", "raamatu", "raamatut",
         "obj-case", "duration -> ongoing -> partitive"),
    Case("Ma otsin oma rahakoti juba kaua.", "rahakoti", "rahakotti",
         "obj-case", "still ongoing -> partitive"),

    # ---- planted verb-form errors (the secondary documented gap) -------------
    Case("Homme ma minen kooli.", "minen", "lähen",
         "verb-form", "irregular stem: minema -> lähen"),
    Case("Eile ma teesin kodutööd.", "teesin", "tegin",
         "verb-form", "irregular past: tegema -> tegin"),

    # ---- CORRECT Estonian: must NOT be flagged ------------------------------
    Case("Ma lugesin selle raamatu läbi.", None, None, None,
         "correct: completed -> genitive"),
    Case("Ma ei ostnud piletit.", None, None, None,
         "correct: negation -> partitive"),
    Case("Ta luges raamatut terve õhtu.", None, None, None,
         "correct: duration -> partitive"),
    Case("Ma ostsin uue auto.", None, None, None,
         "correct: completed purchase -> genitive"),
    Case("Ma sõin suppi.", None, None, None,
         "correct: partial/ongoing eating -> partitive"),
    Case("Homme ma lähen kooli ja tulen kell viis tagasi.", None, None, None,
         "correct: irregular stem used correctly"),
    Case("Mulle meeldib eesti keel, aga grammatika on raske.", None, None, None,
         "correct: no object-case decision at all"),
    Case("Ta ei leidnud oma võtmeid.", None, None, None,
         "correct: negation -> partitive plural"),
)


def _flagged(result: dict, target: str) -> bool:
    """Did the model flag the target token?"""
    return any(
        target.lower() in (c.get("wrong") or "").lower()
        for c in result.get("corrections", [])
    )


def run(
    provider: str,
    model: str | None = None,
    cases: tuple[Case, ...] = CASES,
    verbose: bool = True,
) -> dict:
    """Score one model. Returns recall, precision and the per-case detail."""
    errors = [c for c in cases if c.wrong]
    clean = [c for c in cases if not c.wrong]
    caught, false_flags, failures, broken = 0, 0, [], 0

    for case in cases:
        try:
            result = parse_json(complete(provider, SYSTEM, case.sentence, model=model))
        except Exception as exc:  # a model that cannot return JSON has failed the eval
            broken += 1
            failures.append((case.sentence, f"ERROR {type(exc).__name__}: {exc}"))
            continue

        if case.wrong:
            if _flagged(result, case.wrong):
                caught += 1
            else:
                failures.append((case.sentence, f"missed {case.wrong!r} ({case.note})"))
        else:
            if result.get("corrections"):
                false_flags += 1
                got = [c.get("wrong") for c in result["corrections"]]
                failures.append((case.sentence, f"false flag {got} ({case.note})"))

    recall = caught / len(errors) if errors else 0.0
    precision = 1 - (false_flags / len(clean)) if clean else 0.0
    score = {
        "provider": provider,
        "model": model or "default",
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "caught": f"{caught}/{len(errors)}",
        "left_alone": f"{len(clean) - false_flags}/{len(clean)}",
        "broken": broken,
        "failures": failures,
    }
    if verbose:
        print(json.dumps({k: v for k, v in score.items() if k != "failures"}, indent=2))
        for sentence, why in failures:
            print(f"  ✗ {sentence}\n      {why}")
    return score
