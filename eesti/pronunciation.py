"""Read-aloud practice: say a known sentence, and see what the recogniser heard.

## Correcting an over-broad claim

This project has said, repeatedly and correctly, that it does not score
pronunciation: forced alignment yields timings rather than correctness, turning
that into feedback is a research project, and EKI already publishes free
pronunciation exercises.

That is true of **acoustic** scoring. It was stated too broadly, because it also
ruled out something quite different and entirely sound: when the learner is
asked to read a **known target**, comparing what the recogniser heard against
what they were asked to say is a deterministic measurement with no model
judgement in it at all. Duolingo's and Babbel's speaking exercises are this, and
they work. The two are not the same thing:

| | Acoustic scoring | Read-aloud comparison |
|---|---|---|
| Input | waveform | two strings |
| Needs | phoneme models, alignment, a scale someone invented | `difflib` |
| Says | "your /õ/ is 62 % correct" | "it heard *kool* where you were asked to say *kohl*" |
| Honest? | not without a research programme | yes, with one caveat |

**The caveat, stated wherever the number is shown:** this measures what an ASR
model heard, which is a proxy for intelligibility and not a phonetics grade. A
miss can mean the learner mispronounced it *or* that the recogniser is weak on
accented Estonian — both are informative, neither is a mark. Which is why the
output names the words rather than producing a percentage on its own.

## Why word-level and not sentence-level

"7/9 words" is actionable in a way "78 %" is not: the two that were missed are
the ones to say again. So the comparison returns the alignment, and the ratio is
derived from it rather than being the point.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

from .config import LEVELS

_PUNCT = re.compile(r"[^\w\s-]", re.UNICODE)


def normalise(text: str) -> list[str]:
    """Words, lowercased, punctuation gone, Unicode composed.

    Composition matters more than it looks: `ä` can arrive as one codepoint or
    as `a` + combining diaeresis depending on the recogniser, and two strings
    that render identically would otherwise never compare equal.
    """
    text = unicodedata.normalize("NFC", text or "")
    return _PUNCT.sub(" ", text).lower().split()


@dataclass(frozen=True)
class WordResult:
    target: str
    heard: str | None      # None when the word was not heard at all
    ok: bool


@dataclass(frozen=True)
class Comparison:
    target: str
    heard: str
    words: list[WordResult]
    extra: list[str]       # words heard that were not asked for

    @property
    def matched(self) -> int:
        return sum(1 for w in self.words if w.ok)

    @property
    def total(self) -> int:
        return len(self.words)

    @property
    def ratio(self) -> float:
        return self.matched / self.total if self.total else 0.0

    @property
    def missed(self) -> list[str]:
        return [w.target for w in self.words if not w.ok]

    def to_dict(self) -> dict:
        return {
            "target": self.target, "heard": self.heard,
            "words": [asdict(w) for w in self.words],
            "extra": self.extra, "matched": self.matched, "total": self.total,
            "ratio": round(self.ratio, 3), "missed": self.missed,
            # Russian, deliberately. This sentence exists to stop the learner
            # reading a low score as "my pronunciation is bad" when the honest
            # reading is "the recogniser may not know accented Estonian". In
            # Estonian it would be unreadable to the person it protects, and a
            # caveat nobody can read does the opposite of its job.
            "caveat": (
                "Это то, что услышало распознавание речи, а не оценка "
                "произношения. Промах может означать произношение — или то, "
                "что модель плохо знает эстонский с акцентом."
            ),
        }


def compare(target: str, heard: str) -> Comparison:
    """Align what was asked against what was heard, word by word.

    `SequenceMatcher` rather than a naive zip: a learner who drops one word
    would otherwise fail every word after it, which would be a measurement of
    the alignment rather than of the speech.
    """
    want, got = normalise(target), normalise(heard)
    results: list[WordResult] = [WordResult(w, None, False) for w in want]
    extra: list[str] = []

    matcher = SequenceMatcher(None, want, got, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                results[i1 + offset] = WordResult(want[i1 + offset],
                                                  got[j1 + offset], True)
        elif tag == "replace":
            for offset in range(i2 - i1):
                sub = got[j1 + offset] if j1 + offset < j2 else None
                results[i1 + offset] = WordResult(want[i1 + offset], sub, False)
            if j2 - j1 > i2 - i1:
                extra += got[j1 + (i2 - i1):j2]
        elif tag == "insert":
            extra += got[j1:j2]
    return Comparison(target.strip(), heard.strip(), results, extra)


# --------------------------------------------------------------------------
# What to read aloud
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ReadAloud:
    text: str
    kind: str            # sona | lause
    level: str | None
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


def words_to_say(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
) -> list[ReadAloud]:
    """Single words, frequency-ordered.

    Deliberately the frequent end: the point of saying a word aloud is the
    sounds in it, and a learner gets more from the ones they will say again.
    """
    import random

    rows = conn.execute(
        f"""SELECT word, proficiency FROM words
            WHERE proficiency IN ({','.join('?' * len(levels))})
              AND freq_rank > 0 AND length(word) > 2
            ORDER BY freq_rank LIMIT 400""",
        levels,
    ).fetchall()
    pool = [ReadAloud(r[0], "sona", r[1], "ekilex") for r in rows]
    random.Random(seed).shuffle(pool)
    return pool[:count]


def sentences_to_say(
    content: sqlite3.Connection,
    count: int = 10,
    seed: int | None = None,
    min_words: int = 4,
    max_words: int = 12,
) -> list[ReadAloud]:
    """Real sentences from the harvested corpus, short enough to say in a breath.

    Authentic rather than authored, for the same reason the cloze drills are:
    the sentence is correct because a native wrote it, and reading real prose
    aloud rehearses real rhythm rather than a textbook's.
    """
    import random

    from .cloze import sentences

    pool = [
        ReadAloud(s, "lause", None, "selges-keeles")
        for s in sentences(content, min_words=min_words, max_words=max_words)
    ]
    random.Random(seed).shuffle(pool)
    return pool[:count]
