"""Read-aloud practice: say a known sentence, and see what the recogniser heard.

Acoustic pronunciation scoring is not done. Comparing what the recogniser heard
with a **known target** is different: two strings, `difflib`, no model judgement.

| | Acoustic scoring | Read-aloud comparison |
|---|---|---|
| Input | waveform | two strings |
| Says | "your /õ/ is 62 % correct" | "it heard *kool* where you were asked to say *kohl*" |

**Caveat, shown wherever the result is:** this measures what an ASR model heard
(a proxy for intelligibility); a miss may be the recogniser, not the learner.
Results name the missed words; the ratio is derived from the alignment.
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
    """Words, lowercased, punctuation removed, Unicode NFC-composed (`ä` may arrive
    decomposed from a recogniser).
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
            # Russian, so the learner can read that a miss may be the recogniser's.
            "caveat": (
                "Это то, что услышало распознавание речи, а не оценка "
                "произношения. Промах может означать произношение — или то, "
                "что модель плохо знает эстонский с акцентом."
            ),
        }


def compare(target: str, heard: str) -> Comparison:
    """Align what was asked against what was heard, word by word (`SequenceMatcher`),
    so one dropped word does not fail the rest.
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
    """Single words, frequency-ordered: the words the learner will say again."""
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
    """Real sentences from the harvested corpus, short enough to say in a breath."""
    import random

    from .cloze import sentences

    pool = [
        ReadAloud(s, "lause", None, "selges-keeles")
        for s in sentences(content, min_words=min_words, max_words=max_words)
    ]
    random.Random(seed).shuffle(pool)
    return pool[:count]
