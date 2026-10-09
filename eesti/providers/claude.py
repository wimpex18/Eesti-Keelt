"""The Claude lane: Anthropic's Messages API through the official SDK (DEV-38).

Claude Haiku 5.5 (`claude-haiku-5-5`) explains, tutors and gives advisory
feedback, like every model lane here: code owns drill keys, mastery and FSRS
(ADR-0001), and the lane answers learners only after its own grammar eval
passes (ADR-0008). Until then it is an evaluation lane.

What Haiku 5.5 requires, and this module therefore does:

- **No sampling parameters, no prefill.** A non-default `temperature` and an
  assistant prefill are rejected; output is held to shape with a JSON schema
  (`output_config.format`) where the caller has one, and by the prompt
  otherwise (`llm.parse_json` tolerates a fenced block).
- **Explicit effort.** Thinking is adaptive and on by default; `effort` sets
  how much, and `max_tokens` leaves room for it.
- **A refusal is a failed lane** (`Refused`), never an empty explanation, and
  Haiku 5.5 has no server-side fallback: the chain moves on.
- **Prompts stay under the price threshold.** Above 100K tokens the rate is
  five times higher; a prompt past `MAX_PROMPT_CHARS` is refused before it is
  sent. Nothing this app sends comes close.
- **One attempt.** The SDK's own retries are off: interactive calls make one
  attempt per lane, and the chain decides what happens next.

The learner's text goes to Anthropic, which deletes API inputs and outputs
within 30 days and does not train on them by default (`eesti/licences.py`).
"""

from __future__ import annotations

import os

MODEL = "claude-haiku-5-5"

#: Short explanation and correction tasks: the eval measures `low` against
#: `medium` before the lane is promoted (ADR-0008).
EFFORT = os.environ.get("ANTHROPIC_EFFORT", "low")

#: Room for adaptive thinking on top of the answer the caller asked for.
THINKING_ROOM = 4000

#: Well under 100K tokens in any script this app sends (Estonian and Russian
#: run at roughly three characters a token).
MAX_PROMPT_CHARS = 200_000


class Refused(RuntimeError):
    """The model declined (`stop_reason: "refusal"`)."""

    def __init__(self, category: str | None):
        super().__init__(f"refused ({category or 'no category'})")
        self.category = category


class SpendLimit(RuntimeError):
    """The account's spend limit is reached: the lane is spent, not broken."""


_CLIENT = None


def _client(timeout: float):
    """One SDK client for the process (one connection pool), per-call timeout."""
    global _CLIENT
    import anthropic

    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(max_retries=0)
    return _CLIENT.with_options(timeout=timeout)


def is_fault(exc: BaseException) -> bool:
    """Whether a failure counts against the lane's circuit breaker.

    A refusal is about one request, and a spend limit about the month: neither
    says the lane is broken, and the breaker's cooldown grows to days.
    """
    return not isinstance(exc, (Refused, SpendLimit))


def _spend_limit(exc: BaseException) -> bool:
    text = str(getattr(exc, "body", "") or "") + " " + str(exc)
    return "spend_limit" in text or "usage limits" in text


def complete(system: str, user: str, *, model: str | None = None,
             max_tokens: int = 2000, schema: dict | None = None,
             effort: str | None = None, timeout: float = 60.0) -> str:
    """One request; the reply's text. Raises `Refused`, `llm.EmptyReply`, the
    SDK's typed errors, or `ValueError` for a prompt past the threshold."""
    from .llm import EmptyReply

    if len(system) + len(user) > MAX_PROMPT_CHARS:
        raise ValueError("prompt too long for the Claude lane's price threshold")
    import anthropic

    output_config: dict = {"effort": effort or EFFORT}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    try:
        reply = _client(timeout).messages.create(
            model=model or os.environ.get("ANTHROPIC_MODEL") or MODEL,
            max_tokens=max_tokens + THINKING_ROOM,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config=output_config,
        )
    except (anthropic.RateLimitError, anthropic.BadRequestError,
            anthropic.PermissionDeniedError) as exc:
        if _spend_limit(exc):
            raise SpendLimit(str(exc)) from None
        raise
    if reply.stop_reason == "refusal":
        details = getattr(reply, "stop_details", None)
        raise Refused(getattr(details, "category", None))
    # A reply cut off by `max_tokens` is not an answer: its JSON is unfinished.
    if reply.stop_reason == "max_tokens":
        raise EmptyReply("max_tokens")
    text = "".join(block.text for block in reply.content if block.type == "text")
    if not text.strip():
        raise EmptyReply(reply.stop_reason or "unknown")
    return text


def list_models(timeout: float = 30.0) -> list[dict]:
    """The live catalogue, in the shape `llm.list_models` returns."""
    return [{"id": m.id} for m in _client(timeout).models.list()]
