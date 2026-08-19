"""Relative difficulty for harvested prose, and why it is not a CEFR level.

## The measurement that does not work

The obvious move is to score a text by how much of its vocabulary sits at A1–A2
and call the result a level. It was tried here and it failed loudly: 342 of 349
*deliberately simplified* news items came out as B2.

The cause is structural rather than a tuning problem. Only **9 951 of 160 316
lemmas (6.2 %)** in the word list carry a CEFR tag at all, so every unlisted word
counts against a text. Coverage across that corpus runs 0.25–0.87 with a median
of 0.53 — nowhere near the 0.85 an "A2 text" would need. The scale is not
calibrated and no threshold on it can be.

## The measurement that does

Rank texts **against each other** and split into thirds. That answers the
question a reader actually has — *where do I start?* — without claiming
anything about the exam's scale. The bands are Estonian and deliberately
relative: `kergem`, `keskmine`, `raskem`.

Ranking within a source, not across all of them, is the point. A radio-course
transcript and a simplified news item are different registers; pooling them
would rank register rather than difficulty, and the easiest third would be
whichever source happens to write shorter sentences.
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
    """Share of the text's words that are known A1–A2 vocabulary.

    Useful for *ordering*. Not useful as a level — see the module docstring.
    """
    from .lookup import annotate

    return annotate(text, levels=("A1", "A2")).get("coverage", 0.0)


def rank(texts: dict[str, str]) -> dict[str, str]:
    """`{key: text}` in, `{key: band}` out, split into thirds by score.

    A source with fewer than three texts gets `keskmine` for all of them:
    thirds of two items is a distinction the data cannot support, and inventing
    one would put a text in `kergem` for no reason a reader could rely on.
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


def band_counts(conn) -> dict[str, int]:
    """How much material sits in each band, for the reading view."""
    rows = conn.execute(
        "SELECT COALESCE(band, '(määramata)') b, COUNT(*) FROM items"
        " WHERE body <> '' GROUP BY b"
    ).fetchall()
    return {row[0]: row[1] for row in rows}


# ---------------------------------------------------------------------------
# Comprehensible input: is this text readable *by this learner*?
# ---------------------------------------------------------------------------
#
# Bands rank texts against each other. That answers "where do I start" and
# nothing else — a band is a property of the corpus, not of the reader.
#
# The reading research is specific about the mechanism: input works when it is
# *understood*, and understanding is gated by how much of the vocabulary the
# reader already has. The measure is known-word coverage, and it is the one
# thing here that can be computed per learner rather than per text: the app
# knows which lemmas have been met, and it can see which lemmas a text uses.
#
# The thresholds below are the ones the reading literature converges on. They
# are stated as what they are — a rule of thumb about coverage, not a claim
# about comprehension, which nothing here measures.

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
    """How much of this text the learner already has words for.

    Returns the coverage and which band it falls in. Deliberately **not** a
    comprehension score: knowing every word in a sentence does not guarantee
    understanding it, and this measures vocabulary, which is what it can see.
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
