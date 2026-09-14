"""Validate Vabamorf against TalTech's native-curated inflection data.

Every drill answer inherits Vabamorf's forms. `TalTechNLP/inflection_et`
(Estonian Native LLM Benchmark, LREC 2026) has 1 400 noun phrases with their
correct form per case.

Agreement is about 98 %. Disagreements are a narrow class: invariant adjectives
(`täis pudeli`, where Vabamorf gives `täie pudeli`).
"""

from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path

from estnltk.vabamorf.morf import synthesize

from ..config import DATA

# Estonian case names as the dataset labels them -> Vabamorf tags.
CASE_TAG = {
    "nimetav": "n", "omastav": "g", "osastav": "p", "sisseütlev": "ill",
    "seesütlev": "in", "seestütlev": "el", "alaleütlev": "all", "alalütlev": "ad",
    "alaltütlev": "abl", "saav": "tr", "rajav": "ter", "olev": "es",
    "ilmaütlev": "ab", "kaasaütlev": "kom",
}
NUMBER = {"ainsuse": "sg", "mitmuse": "pl"}

DATASET = DATA / "raw" / "bench" / "inflection_et.json"
URL = "https://huggingface.co/datasets/TalTechNLP/inflection_et"


def run(path: Path | None = None, show: int = 8) -> dict:
    """Compare Vabamorf's synthesis with the gold forms. Returns per-case agreement."""
    path = Path(path or DATASET)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — run `python -m eesti.cli fetch-bench` first.\nSource: {URL}"
        )

    rows = json.loads(path.read_text(encoding="utf-8"))
    stats: Counter[str] = Counter()
    misses: list[tuple[str, str, list[str], list[str]]] = []

    for row in rows:
        tag = CASE_TAG.get(row["case"])
        number = NUMBER.get(row["plurality"])
        if not tag or not number:
            stats["skipped"] += 1
            continue

        # A noun phrase inflects as a unit: the adjective agrees with its noun.
        per_word = [synthesize(w, f"{number} {tag}") or [] for w in row["noun_phrase"].split()]
        if not all(per_word):
            stats["no_synthesis"] += 1
            continue

        gold = {g.lower() for g in row["inflection"]}
        produced = {" ".join(c).lower() for c in itertools.product(*per_word)}
        key = f"{number} {tag}"
        if produced & gold:
            stats["match"] += 1
            stats[f"match:{key}"] += 1
        else:
            stats["miss"] += 1
            stats[f"miss:{key}"] += 1
            if len(misses) < show:
                misses.append(
                    (row["noun_phrase"], key, sorted(gold), sorted(produced)[:3])
                )

    total = stats["match"] + stats["miss"]
    return {
        "total": total,
        "match": stats["match"],
        "agreement": round(stats["match"] / total, 4) if total else 0.0,
        "no_synthesis": stats["no_synthesis"],
        "per_case": {
            key: (stats[f"match:{key}"], stats[f"match:{key}"] + stats[f"miss:{key}"])
            for key in ("sg g", "sg p", "pl g", "pl p")
            if stats[f"match:{key}"] + stats[f"miss:{key}"]
        },
        "misses": misses,
    }
