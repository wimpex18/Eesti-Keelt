"""Questions about a text: written by a model, keyed by the text itself (ADR-0004).

`lugemine` is the one exam part this app could not practise. A text could be
read and its words looked up, but nothing asked whether it had been understood,
so reading counted as exposure and never as practice.

A model proposes questions; **code decides what is a question at all**:

- the answer must appear in the text **verbatim and exactly once**, so the key
  is the author's own words rather than the model's;
- the answer is between one and `MAX_ANSWER_WORDS` words — a span, not a
  paragraph;
- the question may not contain its own answer;
- every Estonian word in the question must be one Vabamorf knows
  (`tutor._grounded`), so an invented form drops the question.

What survives is recorded in the **evidence log** with the engine that wrote it
and `VERSION`, and that stored span is what an answer is compared against.
Nothing asks a model at answer time.

The log rather than `content.db`: the library is reference data, archived once
and restored to each new container, so questions written into it disappear at
the next cold start and the same text would be paid for again and again. In the
log they are learner state — snapshotted, replayable, and the `idx` an attempt
recorded still names the same question next month.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

#: Bumped when verification or the prompt changes, so old questions are known
#: to have been made under different rules.
VERSION = 1

#: A key must be a span, not a retelling.
MAX_ANSWER_WORDS = 8

#: How many questions one text gets. A text is practice, not an exam paper.
WANTED = 5

#: Texts shorter than this have nothing to ask about.
MIN_TEXT_WORDS = 40

_WORDS = re.compile(r"[A-Za-zÀ-ÿŠŽšžÕÄÖÜõäöü]+")


@dataclass(frozen=True)
class Question:
    idx: int
    question: str
    answer: str
    engine: str

    def asked(self) -> dict:
        """What the learner is sent: never the answer."""
        return {"idx": self.idx, "question": self.question, "engine": self.engine}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalise(text: str) -> str:
    """Compare on words alone: case, punctuation and spacing are not the answer."""
    return " ".join(_WORDS.findall(text.casefold()))


def occurrences(text: str, span: str) -> int:
    """How many times a span appears in a text, as whole words.

    Whole words, because a substring match would accept `raamat` as a span of a
    text that only says `raamatukogu` — and then show the learner a fragment of
    a word as "what the text said".
    """
    needle = normalise(span)
    if not needle:
        return 0
    hay = f" {normalise(text)} "
    found, at = 0, hay.find(f" {needle} ")
    while at != -1:
        found += 1
        # Overlapping spans are still separate occurrences: step by one word.
        at = hay.find(f" {needle} ", at + 1)
    return found


def verify(text: str, question: str, answer: str) -> str | None:
    """The answer as the text writes it, or None when this is not a question.

    Refusing is the normal outcome for a model's weaker proposals, which is why
    it is quiet: the learner sees fewer questions, never a wrong one.
    """
    question, answer = question.strip(), answer.strip(" .,:;")
    if not question.endswith("?") or len(_WORDS.findall(question)) < 3:
        return None
    words = _WORDS.findall(answer)
    if not 1 <= len(words) <= MAX_ANSWER_WORDS:
        return None
    if occurrences(text, answer) != 1:
        # Not in the text, or in it twice: either way the key is not the text's.
        return None
    if occurrences(question, answer):
        return None                      # the question gives its own answer away
    from .tutor import _grounded

    if not _grounded(question, set()):
        return None
    return _as_written(text, answer)


def _as_written(text: str, answer: str) -> str:
    """The span with the text's own capitalisation and punctuation."""
    pattern = r"\W+".join(re.escape(w) for w in _WORDS.findall(answer))
    found = re.search(pattern, text, re.IGNORECASE)
    return found.group(0) if found else answer


def stored(log: sqlite3.Connection, item_id: str) -> list[Question]:
    """The questions written for this text, newest set wins."""
    for row in log.execute(
            "SELECT payload FROM events WHERE type = 'questions-made'"
            " ORDER BY seq DESC"):
        made = json.loads(row["payload"])
        if made.get("item") != item_id or made.get("v") != VERSION:
            continue
        return [Question(q["idx"], q["question"], q["answer"], q["engine"])
                for q in made.get("questions", [])]
    return []


def save(log: sqlite3.Connection, item_id: str,
         questions: list[Question]) -> list[Question]:
    """Record one set of questions as learner state."""
    from . import evidence

    evidence.record("questions-made", {
        "item": item_id,
        "v": VERSION,
        "made": _now(),
        "questions": [{"idx": q.idx, "question": q.question, "answer": q.answer,
                       "engine": q.engine} for q in questions],
    })
    return list(questions)


def long_enough(text: str) -> bool:
    """Whether a text has enough words to ask about (`MIN_TEXT_WORDS`)."""
    return len(_WORDS.findall(text or "")) >= MIN_TEXT_WORDS


def make(log: sqlite3.Connection, item_id: str, text: str,
         want: int = WANTED) -> list[Question]:
    """The questions for one text: the stored ones, else a round of proposals.

    Returns an empty list when the text is too short, no lane is available, or
    nothing the model proposed survived verification.
    """
    have = stored(log, item_id)
    if have:
        return have
    if not long_enough(text):
        return []
    from .tutor import propose_questions

    proposed, engine = propose_questions(text, want)
    kept: list[Question] = []
    seen: set[str] = set()
    for pair in proposed:
        answer = verify(text, pair.get("q", ""), pair.get("a", ""))
        if answer is None or normalise(answer) in seen:
            continue
        seen.add(normalise(answer))
        kept.append(Question(len(kept), pair["q"].strip(), answer, engine))
        if len(kept) >= want:
            break
    return save(log, item_id, kept) if kept else []


def grade(question: Question, given: str) -> dict:
    """Code alone: the learner's words against the text's own span.

    An answer that carries the span and little else is right — a learner writing
    a whole sentence around it has still found it.
    """
    want, said = normalise(question.answer), normalise(given)
    extra = len(said.split()) - len(want.split())
    # Whole words again: `kolm` must not be found inside `kolmkümmend`.
    correct = bool(want) and f" {want} " in f" {said} " and extra <= 3
    return {
        "correct": correct,
        "expected": question.answer,
        "why_ru": ("Верно." if correct else
                   f"В тексте сказано: «{question.answer}»."),
    }
