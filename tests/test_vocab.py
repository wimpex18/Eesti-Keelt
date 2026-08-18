"""Known-word tracking.

Adapted from Lute/LWT: statuses 1–5 plus ignored and well-known. The two
behaviours worth pinning are the ones that would quietly distort the coverage
number a reader uses to pick a text.
"""

import pytest

from eesti import vocab


@pytest.fixture()
def db(tmp_path):
    return vocab.connect(tmp_path / "vocab.db")


def test_unseen_words_are_unknown(db):
    assert vocab.statuses(db, ["puudub"]) == {"puudub": vocab.UNKNOWN}


def test_encounters_count_without_claiming_knowledge(db):
    """Meeting a word is exposure, not learning.

    Automatically promoting on sight is what makes 'known word' counts
    meaningless — a word skimmed past is not a word learned.
    """
    vocab.record_encounter(db, ["raamat", "auto", "raamat"])
    assert vocab.statuses(db, ["raamat"])["raamat"] == vocab.LEARNING
    met = db.execute(
        "SELECT met_count FROM vocab_status WHERE lemma = 'raamat'"
    ).fetchone()["met_count"]
    assert met == 2


def test_setting_a_status_preserves_the_encounter_history(db):
    vocab.record_encounter(db, ["raamat", "raamat", "raamat"])
    vocab.set_status(db, "raamat", vocab.KNOWN)
    row = db.execute(
        "SELECT status, met_count FROM vocab_status WHERE lemma = 'raamat'"
    ).fetchone()
    assert row["status"] == vocab.KNOWN and row["met_count"] == 3


def test_ignored_words_are_excluded_from_both_sides_of_coverage(db):
    """A proper name is neither known nor needed; counting it either way lies."""
    vocab.set_status(db, "raamat", vocab.KNOWN)
    vocab.set_status(db, "Tallinn", vocab.IGNORED)
    result = vocab.coverage(db, ["raamat", "Tallinn", "uus", "auto"])
    assert result["total"] == 3          # Tallinn excluded entirely
    assert result["known"] == 1
    assert result["coverage"] == round(1 / 3, 3)


def test_coverage_counts_unique_lemmas_not_tokens(db):
    vocab.set_status(db, "raamat", vocab.KNOWN)
    assert vocab.coverage(db, ["raamat"] * 5)["total"] == 1


def test_invalid_status_is_rejected(db):
    with pytest.raises(ValueError):
        vocab.set_status(db, "raamat", 42)


def test_summary_counts_well_known_as_known(db):
    vocab.set_status(db, "a", vocab.KNOWN)
    vocab.set_status(db, "b", vocab.WELL_KNOWN)
    vocab.set_status(db, "c", vocab.LEARNING)
    assert vocab.summary(db)["known_total"] == 2
