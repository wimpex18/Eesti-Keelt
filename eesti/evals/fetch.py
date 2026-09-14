"""Download the public Estonian benchmark datasets.

From TalTechNLP's Estonian Native LLM Benchmark (LREC 2026, arXiv:2510.21193),
built from native sources without machine translation.

  inflection_et        1 400 noun phrases with correct forms per case —
                       validates Vabamorf, and so every drill answer
  grammar_et  (test)   1 000 (erroneous, corrected) pairs — the GEC eval
                       track in `evals/external.py`
  grammar_et  (train)  7 937 more pairs     } word-order drill pool only
  grammar2_et            446 more pairs     } (`wordorder.py`)

The eval track reads only `grammar_et.json`; the train split is a separate,
disjoint file, so the eval score does not move. `DATASETS` is keyed by filename
because one dataset lands in two files.

429 backs off and honours `Retry-After`; `fetch_all` collects failures instead
of raising; only `REQUIRED` datasets make `cli fetch-bench` fail. CI passes
`--required-only`.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..config import DATA

ROWS_API = "https://datasets-server.huggingface.co/rows"

# The datasets server returns transient 5xx under load: retry with backoff.
RETRIES = 4
TIMEOUT = 60.0
#: The longest a `Retry-After` will be honoured. Past this, back off our own
#: way and let the caller decide -- an optional dataset is allowed to fail.
RETRY_AFTER_CAP = 30.0
BENCH_DIR = DATA / "raw" / "bench"

#: filename -> (dataset, split, rows), keyed by file because `grammar_et` is fetched
#: twice. Row counts may over-estimate; the fetch stops when the server runs out.
DATASETS = {
    "inflection_et": ("inflection_et", "train", 1400),
    # The eval track's file. Do not repoint this.
    "grammar_et": ("grammar_et", "test", 1000),
    "grammar_et_train": ("grammar_et", "train", 7937),
    "grammar2_et": ("grammar2_et", "train", 446),
}

#: Datasets whose failure fails the command: the morphology gold forms and the
#: eval track. The word-order pools only widen a pool.
REQUIRED = frozenset({"inflection_et", "grammar_et"})


def _backoff(exc: urllib.error.HTTPError, attempt: int) -> float:
    """How long to wait: the server's `Retry-After` where given, capped."""
    try:
        asked = float(exc.headers.get("Retry-After", ""))
    except (TypeError, ValueError):
        asked = 0.0
    return max(2 ** attempt, min(asked, RETRY_AFTER_CAP))


def fetch(name: str, split: str, total: int, out_dir: Path | None = None,
          key: str | None = None) -> Path:
    """Download one split and write it to `<key or name>.json`."""
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
                # 4xx means the request was wrong — except 429, which is retried.
                if exc.code != 429 and (exc.code < 500 or attempt == RETRIES - 1):
                    raise
                if attempt == RETRIES - 1:
                    raise
                time.sleep(_backoff(exc, attempt))
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


def fetch_all(out_dir: Path | None = None,
              required_only: bool = False) -> tuple[dict[str, int], dict[str, str]]:
    """Fetch the datasets and return `(counts, failures)` without raising; the caller
    decides which failures are fatal (`REQUIRED`).
    """
    counts: dict[str, int] = {}
    failures: dict[str, str] = {}
    for key, (name, split, total) in DATASETS.items():
        if required_only and key not in REQUIRED:
            continue
        try:
            path = fetch(name, split, total, out_dir, key=key)
        except Exception as exc:  # noqa: BLE001 - somebody else's server
            failures[key] = f"{type(exc).__name__}: {exc}"
            continue
        counts[key] = len(json.loads(path.read_text(encoding="utf-8")))
    return counts, failures
