"""One retrying GET, for the documents this project fetches once and keeps.

Two modules had this loop, character for character: `rection.py` fetching EKK
SÜ 64 and `harvest/evkk.py` fetching the EVKK taxonomy. Same constants, same
back-off, same "unreachable" wording -- and nothing keeping them in step. The
lesson this repository already paid for is that the same job written twice
becomes two behaviours: four harvesters each carried a private `_TAG_RE`, gave
three different answers on one line of input, and every difference reached the
learner.

Deliberately narrow. It is a *published document* fetcher: something that is
requested once, cached to disk, and does not change weekly. It is not the
right shape for a crawl (`harvest/err.py` walks a series and wants its own
per-request timeout) or for a provider call (`providers/` needs the circuit
breaker and has to tell a rate limit from an outage -- and the entry in
`docs/lessons.md` about a retry keeping a failure alive is about exactly that
case, which is why this one is not used there).

Nothing here decides whether a failure is worth retrying: three attempts with
an exponential back-off, then the last exception in a message naming what was
unreachable. That is what both callers did before, unchanged.
"""

from __future__ import annotations

import time
import urllib.request

#: The timeout both callers used. A published document is a single large page,
#: not an API call.
TIMEOUT = 60.0

#: Attempts, not retries: three tries, sleeping 1s then 2s between them.
RETRIES = 3

#: Says what this is and who runs it. A tool that fetches somebody's server
#: should be identifiable from their logs.
UA = "Eesti-Keelt/0.1 (personal language-learning tool)"


def get(url: str, what: str, *, timeout: float = TIMEOUT,
        retries: int = RETRIES, ua: str = UA) -> str:
    """Fetch `url` as text, retrying, or raise naming `what` was unreachable.

    `what` is the human name of the document -- "EKK SÜ 64", "EVKK taxonomy" --
    because the caller of a failed harvest reads the message, and "unreachable"
    without a subject is not an error report.
    """
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001 - retry anything, then give up
            last = exc
            # No sleep after the final attempt: it delays the exception and
            # changes nothing.
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"{what} unreachable: {last}")
