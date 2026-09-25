"""How the recogniser hears this learner, measured in ordinary practice.

A read-aloud sentence has a known target, but the target is not a transcript:
the learner may misread it (ADR-0003). The learner therefore says, right after
reading, whether they read it as written. Only those sentences are scored, so a
miss in them is the recogniser's. This is a lighter tier than a clip someone
listened to and corrected in `Hindamiskomplekt`: nothing is replayed and no
audio is kept, which is what lets it run on the deployment.

A probe sentence carries one deliberately wrong object-case form, the
distractor an `obj-case` drill offers. Read as written, the question is whether
the recogniser hands back the wrong form or quietly repairs it; a repair would
hide the learner's mistake from every check downstream.
"""

from __future__ import annotations

import sqlite3

from .pronunciation import compare, normalise

#: Below these the report shows counts and no rate (`docs/asr-evaluation.md`).
MIN_SENTENCES = 20
MIN_PROBES = 5

SAID = ("as-written", "differently")


def probe(seed: int) -> dict | None:
    """A sentence with a planted object-case error, or None when none is ready."""
    from .item import BLANK
    from .practice import items_for

    for item in items_for("obj-case", count=6, seed=seed):
        wrong = getattr(item, "distractor", "")
        if not wrong or wrong == item.answer or item.prompt.count(BLANK) != 1:
            continue
        text = item.prompt.replace(BLANK, wrong)
        index = len(normalise(item.prompt.split(BLANK)[0]))
        if normalise(text)[index:index + 1] != normalise(wrong):
            continue
        return {"text": text, "planted": wrong, "correct": item.answer,
                "index": index}
    return None


def score(target: str, transcript: str, *, index: int | None = None,
          planted: str = "", correct: str = "") -> dict:
    """Word errors against the target and, for a probe, what became of the planted form."""
    c = compare(target, transcript)
    out = {"words": c.total, "errors": (c.total - c.matched) + len(c.extra)}
    if index is not None and 0 <= index < len(c.words):
        heard = c.words[index].heard or ""
        low = heard.lower()
        out["probe"] = ("kept" if low == planted.lower()
                        else "repaired" if low == correct.lower() else "other")
        out["heard"] = heard
    return out


def report(log: sqlite3.Connection) -> dict:
    """Totals over every check in the log. Counts always; rates only past the floors."""
    from . import evidence

    sentences = words = errors = differently = 0
    probes = {"kept": 0, "repaired": 0, "other": 0}
    repaired: list[dict] = []
    engines: set[str] = set()
    for ev in evidence.since(log, ("asr-check",), ""):
        p = ev.payload
        if p.get("said") != "as-written":
            differently += 1
            continue
        sentences += 1
        words += p.get("words", 0)
        errors += p.get("errors", 0)
        if p.get("engine"):
            engines.add(p["engine"])
        if p.get("probe") in probes:
            probes[p["probe"]] += 1
            if p["probe"] == "repaired":
                repaired.append({"planted": p.get("planted", ""),
                                 "heard": p.get("heard", "")})
    n_probes = sum(probes.values())
    return {
        "sentences": sentences,
        "differently": differently,
        "words": words,
        "errors": errors,
        "word_error_rate": (round(errors / words, 3)
                            if sentences >= MIN_SENTENCES and words else None),
        "probes": probes,
        "false_acceptance": (round(probes["repaired"] / n_probes, 3)
                             if n_probes >= MIN_PROBES else None),
        "repaired": repaired[-5:],
        "engines": sorted(engines),
        "floors": {"sentences": MIN_SENTENCES, "probes": MIN_PROBES},
    }
