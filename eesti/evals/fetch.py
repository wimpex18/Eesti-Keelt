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

The train split is five times the whole previous pool and
nothing had ever asked for it: every earlier pass read the dataset card, saw
one number, and fetched the split the eval track names. `grammar2_et` was
missed the same way -- the benchmark paper lists seven datasets and it is an
eighth sitting beside them.

Fetching them is not free, and the cost landed on the wrong thing. The two
extra pools took a CI leg from 14 requests to 94; two legs run in parallel on
every push, and the datasets server answered **429 Too Many Requests**. 429 was
not retried (the loop re-raised anything under 500), one failure ended the whole
command although `inflection_et` had already downloaded, and the workflow step
is `continue-on-error` — so the morphology gate that checks Vabamorf against
native gold forms was skipped and the run reported success. A check that reads
green because it never ran is this project's most-repeated defect.

All three seams are closed: 429 backs off and honours `Retry-After`,
`fetch_all` collects failures instead of raising, and only `REQUIRED` datasets
make `cli fetch-bench` exit non-zero. CI passes `--required-only`, because
nothing there reads the word-order pools — asking someone else's server for
7 937 rows this job will not open is the thing this project has a rule about.

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
#: The longest a `Retry-After` will be honoured. Past this, back off our own
#: way and let the caller decide -- an optional dataset is allowed to fail.
RETRY_AFTER_CAP = 30.0
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

#: The two a failed fetch must actually fail on. `inflection_et` is what the
#: morphology gate checks Vabamorf against, and everything this app generates
#: inherits that; `grammar_et` is the eval track. The other two only widen the
#: word-order pool, which already degrades to "fewer items" by design -- and
#: letting them be fatal is what skipped the gate.
REQUIRED = frozenset({"inflection_et", "grammar_et"})


def _backoff(exc: urllib.error.HTTPError, attempt: int) -> float:
    """How long to wait. The server's own `Retry-After` wins where it sends one.

    Guessing at a rate limit when the other side has said how long to wait is
    both ruder and slower than doing what it asked. Capped, because a header
    asking for an hour is not something a build should honour silently.
    """
    try:
        asked = float(exc.headers.get("Retry-After", ""))
    except (TypeError, ValueError):
        asked = 0.0
    return max(2 ** attempt, min(asked, RETRY_AFTER_CAP))


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
                # 4xx means we asked wrongly -- except 429, which means we
                # asked too often and is the single most retryable status
                # there is. It was excluded, and that cost the morphology gate:
                # adding `grammar_et`'s train split took the fetch from 14
                # requests to 94, two CI legs run it in parallel, and the
                # datasets server answered 429 on the fifth minute. Raised on
                # the spot, it failed the step, skipped the gate that checks
                # Vabamorf against gold forms, and the run still read green.
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
    """Fetch the datasets and report what arrived and what did not.

    Returns `(counts, failures)` rather than raising, because the datasets are
    not equally important and treating them as one unit cost the thing that
    mattered most. `inflection_et` is fetched first and had already landed when
    the run that prompted this note died on the *fourth* dataset -- and because
    one exception ended the whole command, the morphology gate that only needs
    `inflection_et` was skipped over a file sitting on disk.

    So: keep going, collect the failures, and let the caller decide which ones
    are fatal. `REQUIRED` says which those are.
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
