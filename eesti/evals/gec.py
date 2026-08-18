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

# The first real run exposed the failure mode: the model flagged four of eight
# already-correct sentences ("Ma ostsin uue auto", "Ma sõin suppi"). A checker
# that invents errors is worse than none, so the prompt is built to make silence
# the easy answer:
#
#   * the rules are stated positively, so a correct genitive is recognisably
#     correct rather than merely un-flagged;
#   * worked examples include CORRECT sentences with an empty corrections list,
#     because a model shown only errors infers that errors are expected;
#   * ambiguity is resolved toward saying nothing.
SYSTEM = """\
You are an Estonian grammar checker for a Russian-speaking learner at A2-B1 level.

Return ONLY valid JSON: {"corrections":[{"wrong":"...","correct":"...","tag":"..."}]}

ESTONIAN OBJECT CASE — the rules, stated positively:
- Completed action, whole object -> GENITIVE (omastav). "Ma ostsin uue auto" is
  CORRECT. "Ma lugesin raamatu läbi" is CORRECT.
- Ongoing, repeated, or partial action -> PARTITIVE (osastav). "Ma sõin suppi"
  is CORRECT. "Ta luges raamatut terve õhtu" is CORRECT.
- Negation -> ALWAYS PARTITIVE. "Ma ei ostnud piletit" is CORRECT.

CRITICAL: most sentences you see are already correct. Report a correction ONLY
when you are confident the sentence breaks a rule above. If in doubt, return an
empty list. Never flag a sentence merely because it contains a partitive or a
genitive — both are correct in their own context.

- "wrong" must be an exact substring of the input.
- "tag" must be one of: %s
- Use "obj-case" for object-case errors, "verb-form" for wrong verb stems.
- Do NOT flag style, word order, or punctuation preferences.

EXAMPLES

Input: Ma ostsin uue auto.
Output: {"corrections":[]}

Input: Ma sõin suppi.
Output: {"corrections":[]}

Input: Ma lugesin eile selle raamatut läbi.
Output: {"corrections":[{"wrong":"raamatut","correct":"raamatu","tag":"obj-case"}]}

Input: Homme ma minen kooli.
Output: {"corrections":[{"wrong":"minen","correct":"lähen","tag":"verb-form"}]}
""" % ", ".join(TAGS)


def with_evidence(sentence: str) -> str:
    """Attach Vabamorf's reading of each object-position word.

    Vabamorf knows which case was actually written; the model only has to judge
    whether that case fits the aspect. Supplying the fact removes the part of the
    job the model is worst at — and this is the design the app already uses, so
    the eval should measure the prompt the app will really send.

    Falls back to the bare sentence if Vabamorf is unavailable, which keeps the
    eval runnable on a bare CI image.
    """
    try:
        from ..morph import object_case_candidates
    except Exception:
        return sentence

    try:
        found = object_case_candidates(sentence)
    except Exception:
        return sentence
    if not found:
        return sentence

    lines = "\n".join(
        f"- {t.text}: {'osastav (partitiiv)' if t.is_partitive else 'omastav (genitiiv)'}"
        f" of «{t.lemma}»"
        for t in found
    )
    return f"{sentence}\n\nMorphological analysis (from Vabamorf, reliable):\n{lines}"


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
    evidence: bool = False,
) -> dict:
    """Score one model. Returns recall, precision and the per-case detail."""
    errors = [c for c in cases if c.wrong]
    clean = [c for c in cases if not c.wrong]
    caught, false_flags, failures, broken = 0, 0, [], 0

    for case in cases:
        # One retry on a malformed reply: returning prose instead of JSON is a
        # real weakness, but scoring a model on a single bad sample overstates
        # it. Two failures in a row is the model, not luck.
        result = None
        for attempt in range(2):
            try:
                prompt = with_evidence(case.sentence) if evidence else case.sentence
                result = parse_json(complete(provider, SYSTEM, prompt, model=model))
                break
            except json.JSONDecodeError:
                if attempt:
                    failures.append((case.sentence, "ERROR: no valid JSON after retry"))
            except Exception as exc:
                failures.append((case.sentence, f"ERROR {type(exc).__name__}: {exc}"))
                break
        if result is None:
            broken += 1
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
        "evidence": evidence,
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
