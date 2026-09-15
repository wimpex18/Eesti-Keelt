"""Relative difficulty for harvested prose, and why it is not a CEFR level.

Scoring a text's vocabulary against CEFR tags does not give a level: only 6.2 %
of lemmas carry a tag, so simplified news scores as B2. The scale is not
calibrated and no threshold can fix it.

Instead texts are ranked **within their source** and split into thirds:
`kergem`, `keskmine`, `raskem`. Within a source, because different registers
would otherwise be ranked by register.
"""

from __future__ import annotations

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
