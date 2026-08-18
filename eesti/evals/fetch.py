"""Download the public Estonian benchmark datasets.

From the Estonian Native Large Language Model Benchmark (LREC 2026,
arXiv:2510.21193), released by TalTechNLP. Built from native Estonian sources
with no machine translation, which is what makes it a fair check on a language
this app cannot afford to be approximately right about.

Two of the seven datasets are directly relevant here:

  inflection_et  1 400 noun phrases with correct forms per case -> validates
                 Vabamorf, and therefore every drill answer this app generates
  grammar_et     1 000 (erroneous, corrected) sentence pairs -> a real GEC
                 benchmark, far broader than a hand-written eval set
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from ..config import DATA

ROWS_API = "https://datasets-server.huggingface.co/rows"
BENCH_DIR = DATA / "raw" / "bench"

DATASETS = {
    "inflection_et": ("train", 1400),
    "grammar_et": ("test", 1000),
}


def fetch(name: str, split: str, total: int, out_dir: Path | None = None) -> Path:
    out_dir = Path(out_dir or BENCH_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    offset = 0
    while offset < total:
        url = (
            f"{ROWS_API}?dataset=TalTechNLP%2F{name}&config=default"
            f"&split={split}&offset={offset}&length=100"
        )
        with urllib.request.urlopen(url, timeout=60) as resp:
            batch = json.loads(resp.read()).get("rows", [])
        if not batch:
            break
        rows.extend(item["row"] for item in batch)
        offset += len(batch)
        time.sleep(0.15)  # be polite to the datasets server

    path = out_dir / f"{name}.json"
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return path


def fetch_all(out_dir: Path | None = None) -> dict[str, int]:
    result = {}
    for name, (split, total) in DATASETS.items():
        path = fetch(name, split, total, out_dir)
        result[name] = len(json.loads(path.read_text(encoding="utf-8")))
    return result
