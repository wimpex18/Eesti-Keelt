"""Listening practice that can be got wrong: dictation.

- Sentences come from the harvested corpus, so the answer is correct because a
  native wrote it.
- Grading is deterministic: the submission is aligned against the sentence
  word by word, with no model and no recogniser caveat.
- Writing down what you hear trains decoding; nothing can be skipped.

Missed words are **not** queued for review: a dictation miss may be about
hearing, not grammar. No comprehension questions — they would have to be
generated. Sentences are short so the exercise measures listening, not memory;
replays are unlimited and untracked.
"""

from __future__ import annotations

import hashlib
import random
import re
import sqlite3
from dataclasses import dataclass, field

#: Long enough to carry a case ending in context, short enough that holding it
#: is not the task.
MIN_WORDS = 4
MAX_WORDS = 12

#: Word-level agreement at or above this counts as heard. Borrowed from
#: `checkpoint.PASS_MARK` rather than invented here — one pass mark in the app,
#: applied to the same kind of thing.
from .checkpoint import PASS_MARK  # noqa: E402

#: Russian, like every other explanation the learner has to act on.
CAVEAT = (
    "Проверяется каждое слово, которое ты **расслышал и записал**; опечатка — "
    "ошибка, как и на экзамене. Слушать можно сколько угодно."
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS dictation (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    key      TEXT NOT NULL,           -- stable hash of the sentence
    text     TEXT NOT NULL,
    typed    TEXT NOT NULL,
    matched  INTEGER NOT NULL,
    total    INTEGER NOT NULL,
    correct  INTEGER NOT NULL,
    at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dictation_key ON dictation(key, id);
"""


#: Sentences ending in a bare number were usually cut at an ordinal (`28.`), so
#: they are excluded.
_TRUNCATED = re.compile(r"\b\d+\.$")


def _writable(sentence: str) -> bool:
    """Can this reasonably be written down from hearing it once?"""
    sentence = sentence.strip()
    if not sentence or _TRUNCATED.search(sentence):
        return False
    # A lowercase opening means this is the tail of a bad split.
    return not sentence[:1].islower()


def voice_for(sentence: str) -> str:
    """Which TTS voice reads this sentence.

    Varied across speakers like the exam, but deterministic from the sentence so a
    replay sounds identical.
    """
    from .providers.tts import VOICES

    digest = hashlib.sha1(sentence.strip().encode("utf-8")).digest()
    return VOICES[digest[0] % len(VOICES)]


def key_of(text: str) -> str:
    """Stable id for a sentence, so a repeat is recognisable as one."""
    from .pronunciation import normalise

    return hashlib.sha1(" ".join(normalise(text)).encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Passage:
    text: str
    key: str
    words: int
    coverage: float | None = None      # share of lemmas the learner knows
    band: str | None = None            # iseseisev | arendav | raske
    source_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text, "key": self.key, "words": self.words,
            "coverage": self.coverage, "band": self.band,
            "source": self.source_id,
            # Who reads it. The exam is not one person; see `voice_for`.
            "voice": voice_for(self.text),
        }


@dataclass
class Result:
    passage: Passage
    typed: str
    words: list[dict] = field(default_factory=list)
    matched: int = 0
    total: int = 0
    correct: bool = False
    missed: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.passage.text,
            "key": self.passage.key,
            "typed": self.typed,
            "words": self.words,
            "matched": self.matched,
            "total": self.total,
            "ratio": round(self.matched / self.total, 3) if self.total else 0.0,
            "correct": self.correct,
            "missed": self.missed,
            "extra": self.extra,
            "pass_mark": PASS_MARK,
            "caveat": CAVEAT,
        }


def connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def ensure(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Add the table to `progress.db`, so dictation rides the existing snapshot."""
    conn.executescript(SCHEMA)
    return conn


def choose(
    content: sqlite3.Connection,
    *,
    vocabulary: sqlite3.Connection | None = None,
    words: sqlite3.Connection | None = None,
    count: int = 1,
    seed: int | None = None,
    source_id: str = "selges-keeles",
) -> list[Passage]:
    """Sentences to dictate, easiest first for this learner by known-word coverage;
    random among workable lengths when there is no vocabulary history.
    """
    from .cloze import sentences

    pool = [s for s in sentences(content, source_id=source_id,
                                 min_words=MIN_WORDS, max_words=MAX_WORDS)
            if _writable(s)]
    if not pool:
        return []

    rng = random.Random(seed)
    known: set[str] = set()
    if vocabulary is not None:
        from .difficulty import known_lemmas

        known = known_lemmas(vocabulary)

    if not known:
        rng.shuffle(pool)
        return [
            Passage(s, key_of(s), len(s.split()), source_id=source_id)
            for s in pool[:count]
        ]

    from .difficulty import comprehensible

    # Sampled, not scored end to end: `comprehensible` lemmatises, and doing
    # that to every sentence in the corpus to serve one is a lot of work for a
    # choice this forgiving.
    rng.shuffle(pool)
    scored: list[Passage] = []
    for sentence in pool[: max(count * 40, 200)]:
        fit = comprehensible(sentence, known)
        scored.append(Passage(
            sentence, key_of(sentence), len(sentence.split()),
            coverage=fit["coverage"], band=fit["readability"],
            source_id=source_id,
        ))
    # Most comprehensible first: i+1, not i+5.
    scored.sort(key=lambda p: -(p.coverage or 0.0))
    return scored[:count]


def grade(passage: Passage, typed: str) -> Result:
    """Align what was written against what was said, word by word
    (`pronunciation.compare`), so one dropped word does not fail the rest.
    """
    from .pronunciation import compare

    got = compare(passage.text, typed or "")
    total = got.total
    matched = got.matched
    return Result(
        passage=passage,
        typed=(typed or "").strip(),
        words=[{"target": w.target, "heard": w.heard, "ok": w.ok}
               for w in got.words],
        matched=matched,
        total=total,
        correct=bool(total) and matched / total >= PASS_MARK,
        missed=got.missed,
        extra=got.extra,
    )


def record(progress: sqlite3.Connection, result: Result) -> None:
    """Record the attempt; the readiness verdict counts dictations as listening
    evidence.
    """
    from . import evidence

    payload = {"key": result.passage.key, "text": result.passage.text,
               "typed": result.typed, "matched": result.matched,
               "total": result.total, "correct": bool(result.correct)}
    ev = evidence.record("dictation", payload)
    _record(progress, payload, ev.ts)


def _record(progress: sqlite3.Connection, p: dict, at: str) -> None:
    ensure(progress)
    progress.execute(
        "INSERT INTO dictation (key, text, typed, matched, total, correct, at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (p["key"], p["text"], p["typed"], p["matched"], p["total"],
         int(p["correct"]), at),
    )
    progress.commit()


def _apply_dictation(stores, ev) -> None:
    _record(stores["progress"], ev.payload, ev.ts)


def _register() -> None:
    from . import evidence

    evidence.applies("dictation")(_apply_dictation)


_register()


def stats(progress: sqlite3.Connection) -> dict:
    """What listening practice has actually happened."""
    ensure(progress)
    row = progress.execute(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT key) AS distinct_, "
        "       COALESCE(SUM(correct), 0) AS ok, "
        "       COALESCE(SUM(matched), 0) AS matched, "
        "       COALESCE(SUM(total), 0) AS total "
        "FROM dictation"
    ).fetchone()
    total = row["total"] or 0
    return {
        "attempts": row["n"] or 0,
        "passages": row["distinct_"] or 0,
        "passed": row["ok"] or 0,
        "words_heard": row["matched"] or 0,
        "words_total": total,
        "accuracy": round((row["matched"] or 0) / total, 3) if total else None,
    }
