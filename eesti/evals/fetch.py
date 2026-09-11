"""Download the public Estonian benchmark datasets.

From the Estonian Native Large Language Model Benchmark (LREC 2026,
arXiv:2510.21193), released by TalTechNLP. Built from native Estonian sources
with no machine translation, which is what makes it a fair check on a language
this app cannot afford to be approximately right about.

What is fetched, and what each file is for:

  inflection_et        1 400 noun phrases with correct forms per case ->
                       validates Vabamorf, and therefore every drill answer
                       this app generates
  grammar_et  (test)   1 000 (erroneous, corrected) sentence pairs -> the GEC
                       eval track in `evals/external.py`
  grammar_et  (train)  7 937 more pairs, same two columns
  grammar2_et            446 more pairs, same two columns again

The last two exist here for one reason, and it is not evaluation. `wordorder.py`
refuses to *generate* word-order items -- measuring V2 over 1 000
native-corrected sentences gave 75.4 % inversion, so a generated distractor
would sometimes be correct Estonian -- and takes its items only from
corrections that purely re-order. That filter is severe, which makes the size
of the pool it is filtering the only thing that moves the number:

| pairs | re-orderings kept |
|---|---|
| `grammar_et` test, 1 000 | 47 |
| `grammar2_et` train, 446 | 17 |
| `grammar_et` **train, 7 937** | **312** |

Measured 2026-09-11. The train split is five times the whole previous pool and
nothing had ever asked for it: every earlier pass read the dataset card, saw
one number, and fetched the split the eval track names. `grammar2_et` was
missed the same way -- the benchmark paper lists seven datasets and it is an
eighth sitting beside them.

**The eval track keeps reading `grammar_et.json` and only that.** Its score is
compared across runs, so what it scores must not move; the train split is a
separate file with a separate name, and the two splits are disjoint. This is
also why the key in `DATASETS` is the *filename* rather than the dataset:
one dataset now lands in two files, and letting the key be the dataset name
would have meant one overwriting the other -- silently, and in the direction
that empties the eval track.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..config import DATA

ROWS_API = "https://datasets-server.huggingface.co/rows"

# The datasets server returns transient 5xx under load — a 502 broke a CI run.
# Retry with backoff rather than failing the build on somebody else's bad minute.
RETRIES = 4
TIMEOUT = 60.0
BENCH_DIR = DATA / "raw" / "bench"

#: filename -> (dataset, split, rows). Keyed by the file it writes, not by the
#: dataset, because `grammar_et` is fetched twice -- both its splits -- and two
#: entries sharing a key would silently leave one of them on disk.
#:
#: Row counts are the dataset's own, and the fetch stops early when the server
#: runs out, so an over-estimate costs nothing and an under-estimate silently
#: truncates.
DATASETS = {
    "inflection_et": ("inflection_et", "train", 1400),
    # The eval track's file. Do not repoint this.
    "grammar_et": ("grammar_et", "test", 1000),
    "grammar_et_train": ("grammar_et", "train", 7937),
    "grammar2_et": ("grammar2_et", "train", 446),
}


def fetch(name: str, split: str, total: int, out_dir: Path | None = None,
          key: str | None = None) -> Path:
    """Download one split and write it to `<key or name>.json`.

    `key` exists because a dataset can be fetched more than once -- `grammar_et`
    is, for both its splits -- and the file has to be named after the *fetch*,
    not after the dataset, or the second one lands on top of the first.
    """
    out_dir = Path(out_dir or BENCH_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    offset = 0
    while offset < total:
        url = (
            f"{ROWS_API}?dataset=TalTechNLP%2F{name}&config=default"
            f"&split={split}&offset={offset}&length=100"
        )
        batch = None
        for attempt in range(RETRIES):
            try:
                with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
                    batch = json.loads(resp.read()).get("rows", [])
                break
            except urllib.error.HTTPError as exc:
                # 4xx means we asked wrongly; only 5xx is worth retrying.
                if exc.code < 500 or attempt == RETRIES - 1:
                    raise
                time.sleep(2 ** attempt)
            except (TimeoutError, OSError):
                if attempt == RETRIES - 1:
                    raise
                time.sleep(2 ** attempt)
        if batch is None:
            break
        if not batch:
            break
        rows.extend(item["row"] for item in batch)
        offset += len(batch)
        time.sleep(0.15)  # be polite to the datasets server

    path = out_dir / f"{key or name}.json"
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return path


def fetch_all(out_dir: Path | None = None) -> dict[str, int]:
    result = {}
    for key, (name, split, total) in DATASETS.items():
        path = fetch(name, split, total, out_dir, key=key)
        result[key] = len(json.loads(path.read_text(encoding="utf-8")))
    return result
