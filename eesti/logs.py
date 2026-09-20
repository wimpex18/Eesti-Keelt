"""Structured logs: one JSON object per line, on stdout, for Cloud Logging.

What is logged is what an operator needs to answer "is it working, what is it
costing, and which lane answered": the route, the status, how long it took, and
the engine. **Never the learner's text, transcript or answers** — those are
evidence, they live in the log the learner can export, and a provider's outage
is not a reason to copy them into a console.

`request_id` is Cloudflare's `cf-ray` where the Worker passed one, so a line
here can be matched with a line there.
"""

from __future__ import annotations

import json
import logging
import sys

LOGGER = "eesti"

#: Fields that must never appear in a line, whatever a caller passes.
FORBIDDEN = ("text", "transcript", "answer", "given", "written", "prompt")


class JsonLines(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        body = {"level": record.levelname.lower(), "msg": record.getMessage()}
        body.update(getattr(record, "fields", {}) or {})
        return json.dumps(body, ensure_ascii=False, sort_keys=True)


def setup() -> None:
    """Attach the formatter once; uvicorn's own handlers are left alone."""
    logger = logging.getLogger(LOGGER)
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLines())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def event(msg: str, **fields) -> None:
    """One line. Fields naming learner content are dropped, not trusted."""
    safe = {k: v for k, v in fields.items() if k not in FORBIDDEN}
    logging.getLogger(LOGGER).info(msg, extra={"fields": safe})
