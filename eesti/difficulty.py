"""Relative difficulty for harvested prose, and why it is not a CEFR level.

Scoring a text's vocabulary against CEFR tags does not give a level: only 6.2 %
of lemmas carry a tag, so simplified news scores as B2. The scale is not
calibrated and no threshold can fix it.

Instead texts are ranked **within their source** and split into thirds:
`kergem`, `keskmine`, `raskem`. Within a source, because different registers
would otherwise be ranked by register.
"""

from __future__ import annotations

from functools import lru_cache

BANDS = ("kergem", "keskmine", "raskem")

#: Russian, because this sentence is what stops a band being read as a level.
CAVEAT = (
    "Это относительная сложность внутри одного источника, а не уровень CEFR. "
    "Уровень по вокабуляру здесь посчитать нельзя: тег CEFR есть только у 6 % "
    "слов, и попытка это сделать оценила 342 из 349 упрощённых новостей как B2."
)


def score(text: str) -> float:
    """Share of the text's words that are known A1–A2 vocabulary — for ordering only."""
    from .lookup import annotate

    return annotate(text, levels=("A1", "A2")).get("coverage", 0.0)


def rank(texts: dict[str, str]) -> dict[str, str]:
    """`{key: text}` in, `{key: band}` out, split into thirds; fewer than three texts
    all get `keskmine`.
    """
    if not texts:
        return {}
    if len(texts) < len(BANDS):
        return {key: "keskmine" for key in texts}

    ranked = sorted(texts, key=lambda key: -score(texts[key]))
    third = max(1, len(ranked) // 3)
    out: dict[str, str] = {}
    for index, key in enumerate(ranked):
        if index < third:
            out[key] = "kergem"
        elif index < 2 * third:
            out[key] = "keskmine"
        else:
            out[key] = "raskem"
    return out
# ---------------------------------------------------------------------------
# Comprehensible input: is this text readable *by this learner*?
# ---------------------------------------------------------------------------
#
# Bands are a property of the corpus. Known-word coverage is per learner: the app
# knows which lemmas were met and which a text uses. The thresholds are the
# reading literature's rule of thumb about coverage, not a comprehension measure.

#: At or above this share of known words, a text is readable without help.
INDEPENDENT = 0.95
#: Below `INDEPENDENT` and at or above this, readable with effort — the band
#: where a text teaches rather than either bores or defeats.
INSTRUCTIONAL = 0.90

READABILITY = {
    "iseseisev": "Читается самостоятельно — почти все слова знакомы.",
    "arendav": "Читается с усилием. Именно здесь текст учит.",
    "raske": "Слишком много незнакомых слов, чтобы читать это ради смысла.",
}


def known_lemmas(vocabulary) -> set[str]:
    """Lemmas the learner has marked as known."""
    if vocabulary is None:
        return set()
    try:
        return {
            row[0] for row in vocabulary.execute(
                "SELECT lemma FROM vocab_status WHERE status >= 1"
            )
        }
    except Exception:  # noqa: BLE001 - no vocabulary yet is a valid state
        return set()


def comprehensible(text: str, known: set[str]) -> dict:
    """How much of this text the learner already has words for: coverage and its band.
    Vocabulary coverage, not comprehension.
    """
    from .lookup import lemmas_in

    lemmas = lemmas_in(text)
    if not lemmas:
        return {"coverage": 0.0, "known": 0, "total": 0,
                "readability": None, "note": ""}

    hit = sum(1 for lemma in lemmas if lemma in known)
    coverage = hit / len(lemmas)
    if coverage >= INDEPENDENT:
        band = "iseseisev"
    elif coverage >= INSTRUCTIONAL:
        band = "arendav"
    else:
        band = "raske"
    return {
        "coverage": round(coverage, 3),
        "known": hit,
        "total": len(lemmas),
        "readability": band,
        "note": READABILITY[band],
    }


# ---------------------------------------------------------------------------
# Within reach: what to recommend to a beginner
# ---------------------------------------------------------------------------
#
# Known-word coverage alone says nothing to a learner who has marked few words:
# every text scores near zero and the order is noise. A word is *within reach*
# when the learner has marked it known **or** the word list puts it at A1–A2 —
# the words an A1 learner meets next. That is a property of each word (EKI's
# official level where the list has one), never a level for the text: a text is
# ranked by it and never labelled with a CEFR level.
#
# Coverage is counted over running words, as the reading literature measures it
# (Hu & Nation 2000; Laufer & Ravenhorst-Kalovski 2010), not over distinct lemmas.

#: Word levels counted as within reach for an A1 learner working toward A2.
REACH_LEVELS = ("A1", "A2")

#: Below this share a text is not recommended: at 80 % coverage no reader in Hu &
#: Nation (2000) reached adequate comprehension.
FLOOR = 0.80

#: Coverage steps within which a shorter text goes before a longer one.
STEP = 0.05

#: Vabamorf parts of speech that are not vocabulary to learn: proper names,
#: numerals, abbreviations. Left out of the share rather than counted either way.
TRANSPARENT = frozenset({"H", "N", "O", "Y"})

#: Russian: why this text sits where it does.
REACH_NOTES = {
    "iseseisev": "Почти все слова тебе знакомы или входят в уровни A1–A2.",
    "arendav": "Незнакомых слов немного — читается с усилием, именно здесь "
               "текст учит.",
    "raske": "Много слов выше A2 — пока это чтение со словарём.",
}


@lru_cache(maxsize=8192)
def _words(text: str) -> tuple[tuple[str, str], ...]:
    """`(lemma, part of speech)` for every word of `text`, punctuation dropped.

    Cached because the whole shelf is scored per request and a text never changes
    under its own string.
    """
    from .morph import analyze

    return tuple(
        (t.lemma.lower(), t.pos) for t in analyze(text)
        if t.pos != "Z" and any(ch.isalnum() for ch in t.text)
    )


def reach_lemmas(words, levels: tuple[str, ...] = REACH_LEVELS) -> frozenset[str]:
    """Lemmas the word list puts at `levels` (EKI's official level where it has one)."""
    if words is None:
        return frozenset()
    marks = ",".join("?" * len(levels))
    try:
        return frozenset(
            row[0].lower() for row in words.execute(
                f"SELECT word FROM words WHERE proficiency IN ({marks})", levels)
        )
    except Exception:  # noqa: BLE001 - no word list yet is a valid state
        return frozenset()


def within_reach(text: str, known: set[str] | frozenset[str],
                 reach: frozenset[str], *, strict: bool = False) -> dict:
    """Share of `text`'s running words that the learner knows or that sit at A1–A2.

    Names, numerals and abbreviations are left out of the share. `strict` counts
    them too — for a sentence the learner must *say*, where an unlisted name or a
    number is as hard as an unlisted word.
    """
    words = _words(text or "")
    counted = [lemma for lemma, pos in words if strict or pos not in TRANSPARENT]
    if not counted:
        return {"coverage": 0.0, "known": 0, "in_reach": 0, "total": 0,
                "words": len(words), "readability": None, "note": ""}
    hit = sum(1 for lemma in counted if lemma in known or lemma in reach)
    coverage = hit / len(counted)
    if coverage >= INDEPENDENT:
        band = "iseseisev"
    elif coverage >= INSTRUCTIONAL:
        band = "arendav"
    else:
        band = "raske"
    return {
        "coverage": round(coverage, 3),
        "known": sum(1 for lemma in counted if lemma in known),
        "in_reach": hit,
        "total": len(counted),
        "words": len(words),
        "readability": band,
        "note": REACH_NOTES[band],
    }


def order_key(item: dict) -> tuple:
    """Most within reach first; inside one `STEP` of coverage, shorter first."""
    return (-int(item["coverage"] / STEP + 1e-9), item["words"], -item["coverage"],
            str(item["id"]))


def recommend(items: list[dict], limit: int) -> dict:
    """Texts to read next, from items scored by `within_reach` (plus an `id`).

    Items at or above `FLOOR` come in `order_key` order, and a harder text never
    pads the list. When none clears `FLOOR`, the `limit` most within reach come
    back with `fallback` set, so a beginner still has something to read and is
    told it is above them.
    """
    ranked = sorted(items, key=order_key)
    fit = [item for item in ranked if item["coverage"] >= FLOOR]
    if fit:
        return {"items": fit[:limit], "fallback": False, "recommendable": len(fit)}
    return {"items": ranked[:limit], "fallback": bool(ranked), "recommendable": 0}
