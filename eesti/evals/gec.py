"""Estonian grammar eval: does this model actually know Estonian?

Whether an object should be genitive (completed) or partitive (ongoing,
partial, negated) depends on aspect, which thins out in multilingual models.

  recall     — of sentences with a planted error, how many were caught
  clean pass rate (legacy key `precision`) — of sentences already correct,
  how many were left alone

Precision separates models: flagging everything scores perfect recall and
teaches that every partitive is wrong. Half the set is correct Estonian.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..providers.grammar import SYSTEM_PROMPT as SYSTEM
from ..providers.grammar import why_failed
from ..providers.llm import complete, parse_json

# The prompt under test is the one the app ships (`providers/grammar.py`), so the
# score describes what learners get. `_flagged` reads only `wrong`; the extra
# Russian `why` field costs nothing.

#: Lanes of the grammar chain that are not LLMs, scored through their own
#: client. Public GEC and translation normalization are evaluation-only.
NON_LLM = ("tartunlp", "tartunlp-mt")


def _ask(provider: str, sentence: str, model: str | None, evidence: bool) -> dict:
    """One sentence through one lane, as `{"corrections": [{"wrong": ...}]}`."""
    if provider in NON_LLM:
        from ..providers.grammar import NeurotolgeCorrection, TartuNLPGrammar

        # A service, not a prompt: no model choice and no evidence to attach.
        lane = TartuNLPGrammar() if provider == "tartunlp" else NeurotolgeCorrection()
        result = lane.check(sentence)
        return {"corrections": [c.to_dict() for c in result.corrections]}
    prompt = with_evidence(sentence) if evidence else sentence
    return parse_json(complete(provider, SYSTEM, prompt, model=model))


def with_evidence(sentence: str) -> str:
    """Attach Vabamorf's reading of each object-position word, so the model only
    judges whether the case fits the aspect. The app does not send this yet
    (`LLMGrammar.check` sends the bare text), so the default run, without it, is
    the one that describes what learners get. Falls back to the bare sentence
    when Vabamorf is unavailable.
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
    # Label provenance: docs/evaluations/hand-set.md (EKI rule and Sõnaveeb
    # form/usage links). These are our sentences, not a gold learner corpus.
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
    """Did the model propose an actual change to the target token?"""
    return any(
        target.lower() in (c.get("wrong") or "").lower()
        and (c.get("wrong") or "").strip() != (c.get("correct") or "").strip()
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
    caught, false_flags, no_op_flags, changed_flags, failures, broken = 0, 0, 0, 0, [], 0

    for case in cases:
        # One retry on a malformed reply: returning prose instead of JSON is a
        # real weakness, but scoring a model on a single bad sample overstates
        # it. Two failures in a row is the model, not luck.
        result = None
        for attempt in range(2):
            try:
                result = _ask(provider, case.sentence, model, evidence)
                break
            except json.JSONDecodeError:
                if attempt:
                    failures.append((case.sentence, "ERROR: no valid JSON after retry"))
            except Exception as exc:
                # The provider's own name for the failure, via the live chain's renderer.
                failures.append((case.sentence, f"ERROR {why_failed(exc)}"))
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
                edits = result["corrections"]
                changed = [c for c in edits if
                           (c.get("wrong") or "").strip() !=
                           (c.get("correct") or "").strip()]
                if changed:
                    changed_flags += 1
                    kind = "proposed edit"
                else:
                    no_op_flags += 1
                    kind = "no-op correction"
                got = [(c.get("wrong"), c.get("correct")) for c in edits]
                failures.append((case.sentence, f"{kind} {got} ({case.note})"))

    # Cases that never reached the model are excluded from scoring; with too few
    # answers no score is reported (all-429 runs must not read as precision 1.0).
    answered_errors = len(errors) - sum(
        1 for c in errors if any(c.sentence == s and "ERROR" in w for s, w in failures)
    )
    answered_clean = len(clean) - sum(
        1 for c in clean if any(c.sentence == s and "ERROR" in w for s, w in failures)
    )

    usable = broken < len(cases) * 0.25
    recall = (caught / answered_errors) if (usable and answered_errors) else None
    precision = (
        1 - (false_flags / answered_clean) if (usable and answered_clean) else None
    )

    score = {
        "provider": provider,
        "model": model or "default",
        "evidence": evidence,
        "recall": round(recall, 3) if recall is not None else None,
        "precision": round(precision, 3) if precision is not None else None,
        "clean_pass_rate": round(precision, 3) if precision is not None else None,
        "caught": f"{caught}/{answered_errors}",
        "left_alone": f"{answered_clean - false_flags}/{answered_clean}",
        "no_op_flags": no_op_flags,
        "changed_flags": changed_flags,
        "broken": broken,
        "valid": usable,
        "failures": failures,
    }
    if not usable:
        score["invalid_reason"] = (
            f"{broken}/{len(cases)} cases never reached the model "
            "(rate limit, timeout or unparseable reply) — no score reported"
        )
    if verbose:
        print(json.dumps({k: v for k, v in score.items() if k != "failures"}, indent=2))
        for sentence, why in failures:
            print(f"  ✗ {sentence}\n      {why}")
        if not usable:
            print(f"\n!! {score['invalid_reason']}")
    return score
