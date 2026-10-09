"""The independent blind check: a second model answers without the key (ADR-0009, step 3).

Claude Haiku 5.5 — not the model that wrote the draft — is asked, through the
Message Batches API (half the price; nothing here is interactive):

- each **question with the text** and without the key: if code does not grade
  its answer right (`comprehension.grade`), the question or its key is wrong;
- each **question without the text**: if code grades that answer right, the
  question can be answered without reading, so it tests nothing;
- each **gap with the text**, the word blanked and its lemma and form named: an
  answer other than the key means the sentence admits another word.

A gap is not asked without its text: it names its lemma and form, so it is
answerable from that cue by design, and the deterministic gate has already
shown that the cue allows one word.

The model's answers are evidence for dropping, never for keeping a key: a key
always comes from the draft, has passed the gates, and is compared by code.
A request that errors or expires drops its item, because an unconfirmed item
is an unchecked one.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .gates import Finding, GAP_FORMS
from .schema import Material

#: Bumped when the prompt changes; recorded nowhere else, so keep it here.
PROMPT_VERSION = "blind-1"

SYSTEM = """You check reading exercises for learners of Estonian.

You are given a question in Estonian, sometimes with the text it is about.
Answer it in Estonian with as few words as possible.

- When a text is given, answer with the text's own words, copied exactly: the
  shortest span of the text that answers the question.
- When no text is given, still give your single best guess. Never refuse and
  never say that the text is missing.
- When the task is a gap (written ___), write only the one missing word, in the
  form the task names.

Reply with JSON only: {"answer": "..."}."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}

#: Room for the answer itself; adaptive thinking gets `claude.THINKING_ROOM` more.
ANSWER_TOKENS = 200

#: How often to ask whether a batch has ended, and for how long at most.
POLL_SECONDS = 30
WAIT_SECONDS = 6 * 3600


@dataclass(frozen=True)
class Ask:
    """One request: which material, which item, with the text or without."""

    custom_id: str
    material: int
    item: str
    kind: str          # question | gap
    mode: str          # text | blind
    prompt: str


def _blank(line: str, word: str) -> str:
    import re

    return re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", "___", line, count=1)


def asks(materials: list[Material]) -> list[Ask]:
    """Every request the materials need, with ids stable for the same input."""
    out: list[Ask] = []
    for n, m in enumerate(materials):
        body = m.body()
        for q in m.questions:
            out.append(Ask(f"m{n}-{q.id}-text", n, q.id, "question", "text",
                           f"TEXT:\n{body}\n\nQUESTION: {q.question}"))
            out.append(Ask(f"m{n}-{q.id}-blind", n, q.id, "question", "blind",
                           f"No text is given.\n\nQUESTION: {q.question}"))
        lines = m.segments()
        for g in m.gaps:
            gapped = list(lines)
            gapped[g.at] = _blank(gapped[g.at], g.word)
            out.append(Ask(
                f"m{n}-{g.id}-text", n, g.id, "gap", "text",
                "TEXT:\n" + "\n".join(gapped) +
                f"\n\nTASK: write the missing word: {g.lemma}, {GAP_FORMS[g.form]}."))
    return out


def requests(items: list[Ask], *, model: str | None = None,
             effort: str | None = None) -> list[dict]:
    """The Batches API's request list. The system prompt is the cached prefix."""
    from ..providers import claude

    return [{
        "custom_id": a.custom_id,
        "params": {
            "model": model or claude.MODEL,
            "max_tokens": ANSWER_TOKENS + claude.THINKING_ROOM,
            "system": [{"type": "text", "text": SYSTEM,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": a.prompt}],
            "output_config": {
                "effort": effort or claude.EFFORT,
                "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
            },
        },
    } for a in items]


def submit(client, items: list[Ask], **kw) -> str:
    """Create the batch; its id."""
    batch = client.messages.batches.create(requests=requests(items, **kw))
    return batch.id


def wait(client, batch_id: str, *, poll: float | None = None,
         limit: float = WAIT_SECONDS, sleep=None, say=print) -> bool:
    """Wait until the batch has ended; False when `limit` passes first."""
    poll = POLL_SECONDS if poll is None else poll
    sleep = sleep or time.sleep
    waited = 0.0
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return True
        if waited >= limit:
            return False
        counts = getattr(batch, "request_counts", None)
        say(f"  {batch_id}: {batch.processing_status}"
            + (f", {counts.processing} processing" if counts else ""))
        sleep(poll)
        waited += poll


def _answer(message) -> str | None:
    from ..providers.llm import parse_json

    if getattr(message, "stop_reason", None) in ("refusal", "max_tokens"):
        return None
    text = "".join(getattr(b, "text", "") for b in message.content
                   if getattr(b, "type", "") == "text")
    try:
        parsed = parse_json(text)
    except Exception:  # noqa: BLE001 - an unreadable reply is no answer
        return None
    answer = parsed.get("answer") if isinstance(parsed, dict) else None
    return answer.strip() if isinstance(answer, str) else None


def collect(client, batch_id: str) -> dict[str, str | None]:
    """custom_id → the model's answer, or None where the request did not succeed.

    Results come in any order; they are keyed by id, never by position.
    """
    out: dict[str, str | None] = {}
    for result in client.messages.batches.results(batch_id):
        outcome = result.result
        out[result.custom_id] = (_answer(outcome.message)
                                 if outcome.type == "succeeded" else None)
    return out


def judge(materials: list[Material], items: list[Ask],
          answers: dict[str, str | None]) -> list[tuple[Material, list[Finding]]]:
    """Each material with the items the blind check drops removed, and why."""
    from ..comprehension import Question as Asked, grade, normalise

    dropped: list[dict[str, Finding]] = [{} for _ in materials]
    for a in items:
        m = materials[a.material]
        got = answers.get(a.custom_id)
        where = f"{a.kind} {a.item}"
        if a.kind == "question":
            key = next(q.answer for q in m.questions if q.id == a.item)
            right = got is not None and grade(Asked(0, "", key, ""), got)["correct"]
            if a.mode == "text" and got is None:
                why = "no blind answer came back"
            elif a.mode == "text" and not right:
                why = f"answered *{got}* with the text; the key is *{key}*"
            elif a.mode == "blind" and right:
                why = f"answered *{got}* without the text: guessable"
            else:
                continue
        else:
            key = next(g.word for g in m.gaps if g.id == a.item)
            if got is not None and normalise(got) == normalise(key):
                continue
            why = ("no blind answer came back" if got is None
                   else f"wrote *{got}* for the gap; the key is *{key}*")
        dropped[a.material].setdefault(a.item, Finding("blind", where, why))
    out = []
    for m, gone in zip(materials, dropped):
        kept = m.model_copy(update={
            "questions": [q for q in m.questions if q.id not in gone],
            "gaps": [g for g in m.gaps if g.id not in gone]})
        out.append((kept, list(gone.values())))
    return out
