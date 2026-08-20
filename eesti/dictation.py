"""Listening practice that can be got wrong.

The Kuulamine tab was a text-to-speech box: paste a passage, hear it read. That
is a *tool*, not an exercise. Nothing could be answered, so nothing could be
scored, so nothing was recorded — and the readiness verdict went on reporting
listening as untouched no matter how much was played. On an exam where a zero
in any one part fails you regardless of the other three, that is the worst
place in the app to have no exercise at all.

Dictation is the exercise, for four reasons that are specific to this project
rather than to listening in general:

  * **The answer is known correct because a native wrote it.** Sentences come
    from the 349 harvested texts, the same corpus the cloze drills use. There
    is no answer key to author and no way for a generated sentence to be
    subtly wrong Estonian.
  * **Grading is deterministic and needs no model.** What was said is known
    exactly, so a submission is aligned against it word by word.
  * **A miss is a real miss.** The read-aloud loop compares a target against
    what a *recogniser* heard, and has to say so — a miss there might be the
    model's failure rather than the learner's. Here the learner types, so what
    arrives is what they understood, and the result carries no such caveat.
  * **It is the one thing that trains decoding.** Reading a transcript with the
    audio playing tests reading. Writing down what you hear does not let you
    skip a word you did not catch.

Missed words are **not** queued for review, which breaks the pattern the rest
of the app follows. A word missed in a drill is evidence about grammar; a word
missed in dictation may be evidence about *hearing* — an unstressed syllable, a
word boundary that ran together, a speaker at 0.7x still faster than the
learner reads. Queuing an object-case card because a word was mis-heard would
teach the wrong lesson from the right mistake. Listening misses stay listening
evidence.

Deliberately not built: comprehension questions. They would have to be authored
or generated, and a generated question about an Estonian text is exactly the
kind of plausible-and-wrong artefact this project refuses everywhere else.

Length is capped low on purpose. Past about a dozen words a learner is holding
a sentence in working memory and the exercise measures memory rather than
listening; the research on partial dictation uses short chunks for the same
reason. Replaying is unlimited and untracked — rationing replays would measure
memory again.
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
    "Оценивается то, что вы **расслышали и записали**, слово за словом. "
    "Опечатка засчитывается как ошибка — на экзамене тоже. Слушать можно "
    "сколько угодно раз: считать прослушивания значило бы проверять память, "
    "а не аудирование."
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


#: A sentence ending in a bare number is one the splitter cut at an Estonian
#: ordinal — `28.` is "28th", not a full stop. Fixing the splitter took the
#: rate from 7.2 % of the pool to 2.4 %; the rest genuinely end in a number,
#: and either way the learner is being asked to write down a sentence whose
#: ending was removed. Harmless in a cloze that blanks one word, unfair here.
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

    Always `mari` until now, and the exam is not one person. HARNO's listening
    tasks use several speakers, and a learner who has only ever parsed one voice
    has practised that voice rather than Estonian — the same reason the reading
    library is ranked by comprehensibility rather than served in one register.

    Deterministic from the sentence, not random: replaying must sound identical,
    or the exercise changes underneath the learner between attempts. Same
    sentence, same speaker, every time; different sentences spread across all
    twelve.
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
    """Add the table to an existing progress database.

    Dictation lives in `progress.db` rather than a database of its own so it
    rides the existing snapshot without anything else being told about it — a
    new file would have had to be added to the state export, and that is
    precisely the omission that once deleted the Notion queue on a cold start.
    """
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
    """Sentences to dictate, easiest-first for this particular learner.

    Ordered by known-word coverage rather than by length or by a difficulty
    band: a short sentence full of unknown words is harder to write down than a
    longer one made of words already met. With no vocabulary history there is
    nothing to order by, so the choice is random among sentences of a workable
    length — which is honest, and stops the first session serving the same
    sentence every time.
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
    """Align what was written against what was said, word by word.

    `pronunciation.compare` does the alignment, and it is the right tool for a
    reason worth stating: a learner who drops one word would otherwise fail
    every word after it, and the score would measure the alignment rather than
    the listening.
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
    """Write the attempt down.

    Not optional and not an afterthought. Three bugs in this project have been
    a reader with no writer behind it — a measurement nothing stored, so a
    screen that always said zero. Listening is the part where that would matter
    most: the verdict's whole job is to notice an untouched part.
    """
    from datetime import datetime, timezone

    ensure(progress)
    progress.execute(
        "INSERT INTO dictation (key, text, typed, matched, total, correct, at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (result.passage.key, result.passage.text, result.typed,
         result.matched, result.total, int(result.correct),
         datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    progress.commit()


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
