"""One retrying GET, for published documents fetched once and cached.

Used by `rection.py` (EKK SÜ 65) and `harvest/evkk.py` (the EVKK taxonomy). Not
for crawls (`harvest/err.py` has its own per-request timeout) or provider calls
(`providers/` need the circuit breaker and must tell a rate limit from an
outage). Three attempts with exponential back-off, then an error naming what was
unreachable.
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


class Unreachable(OSError, RuntimeError):
    """A host this project asked did not answer.

    Subclasses both `OSError` (caught per issue by `harvest/lihtsad.py`) and
    `RuntimeError` (caught by `cli harvest`'s EVKK path), so existing handlers keep
    working.
    """


def get(url: str, what: str, *, timeout: float = TIMEOUT,
        retries: int = RETRIES, ua: str = UA, binary: bool = False):
    """Fetch `url`, retrying, or raise `Unreachable` naming `what` (e.g. "EKK SÜ 65").

    Text by default; `binary` returns the bytes, which is what a PDF or a
    listening recording needs.
    """
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                return raw if binary else raw.decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001 - retry anything, then give up
            last = exc
            # No sleep after the final attempt: it delays the exception and
            # changes nothing.
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise Unreachable(f"{what} unreachable: {last}") from last
