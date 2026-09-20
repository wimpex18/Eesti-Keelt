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

What survives is stored beside the text with the engine that wrote it and
`VERSION`, and that stored span is what an answer is compared against. Nothing
asks a model at answer time.
"""

from __future__ import annotations

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

SCHEMA = """
CREATE TABLE IF NOT EXISTS comprehension (
    item_id  TEXT    NOT NULL,
    idx      INTEGER NOT NULL,
    question TEXT    NOT NULL,   -- Estonian, as the learner reads it
    answer   TEXT    NOT NULL,   -- the text's own words, verified verbatim
    engine   TEXT    NOT NULL,   -- which model wrote the question
    made     TEXT    NOT NULL,
    v        INTEGER NOT NULL,
    PRIMARY KEY (item_id, idx)
);
"""

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


def ensure(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript(SCHEMA)


def normalise(text: str) -> str:
    """Compare on words alone: case, punctuation and spacing are not the answer."""
    return " ".join(_WORDS.findall(text.casefold()))


def occurrences(text: str, span: str) -> int:
    """How many times a span appears in a text, compared on words alone."""
    hay, needle = normalise(text), normalise(span)
    if not needle:
        return 0
    return hay.count(needle)


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


def stored(conn: sqlite3.Connection, item_id: str) -> list[Question]:
    ensure(conn)
    return [Question(r["idx"], r["question"], r["answer"], r["engine"])
            for r in conn.execute(
                "SELECT * FROM comprehension WHERE item_id = ? AND v = ?"
                " ORDER BY idx", (item_id, VERSION))]


def save(conn: sqlite3.Connection, item_id: str,
         questions: list[Question]) -> list[Question]:
    ensure(conn)
    with conn:
        conn.execute("DELETE FROM comprehension WHERE item_id = ?", (item_id,))
        conn.executemany(
            "INSERT INTO comprehension (item_id, idx, question, answer, engine,"
            " made, v) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(item_id, q.idx, q.question, q.answer, q.engine, _now(), VERSION)
             for q in questions])
    return stored(conn, item_id)


def make(conn: sqlite3.Connection, item_id: str, text: str,
         want: int = WANTED) -> list[Question]:
    """The questions for one text: the stored ones, else a round of proposals.

    Returns an empty list when the text is too short, no lane is available, or
    nothing the model proposed survived verification.
    """
    have = stored(conn, item_id)
    if have:
        return have
    if len(_WORDS.findall(text or "")) < MIN_TEXT_WORDS:
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
    return save(conn, item_id, kept) if kept else []


def grade(question: Question, given: str) -> dict:
    """Code alone: the learner's words against the text's own span.

    An answer that carries the span and little else is right — a learner writing
    a whole sentence around it has still found it.
    """
    want, said = normalise(question.answer), normalise(given)
    extra = len(said.split()) - len(want.split())
    correct = bool(want) and want in said and extra <= 3
    return {
        "correct": correct,
        "expected": question.answer,
        "why_ru": ("Верно." if correct else
                   f"В тексте сказано: «{question.answer}»."),
    }
