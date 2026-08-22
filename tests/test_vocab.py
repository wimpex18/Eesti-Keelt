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


class TestFrequencyBands:
    """Speakly's ordering: vocabulary has no prerequisites, only usefulness."""

    def test_bands_cover_the_a1_b1_target(self, tmp_path):
        from eesti.vocab import BAND_SIZE, BAND_TOP, band_progress, connect
        from eesti.wordlist import connect as wordlist_connect

        bands = band_progress(connect(tmp_path / "v.db"), wordlist_connect())
        assert bands[0]["from"] == 1
        assert bands[-1]["to"] == BAND_TOP
        assert all(b["to"] - b["from"] + 1 <= BAND_SIZE for b in bands)

    def test_known_words_land_in_the_right_band(self, tmp_path):
        from eesti.vocab import KNOWN, band_progress, connect, set_status
        from eesti.wordlist import connect as wordlist_connect

        words = wordlist_connect()
        vocab = connect(tmp_path / "v.db")
        row = words.execute(
            "SELECT word, freq_rank FROM words WHERE freq_rank BETWEEN 1 AND 400"
            " LIMIT 1"
        ).fetchone()
        set_status(vocab, row[0], KNOWN)

        bands = band_progress(vocab, words)
        assert bands[0]["known"] == 1
        assert all(b["known"] == 0 for b in bands[1:])

    def test_the_denominator_is_a_band_not_the_language(self, tmp_path):
        """"1 200 of the top 2 000" means something; "12 % of Estonian" does
        not, because the tail is endless and nobody is trying to finish it."""
        from eesti.vocab import band_progress, connect
        from eesti.wordlist import connect as wordlist_connect

        for band in band_progress(connect(tmp_path / "v.db"), wordlist_connect()):
            assert band["size"] <= band["to"] - band["from"] + 1
            assert 0.0 <= band["share"] <= 1.0

    def test_unranked_words_are_excluded(self, tmp_path):
        """`freq_rank` 0 means the corpus never saw the word, which is not the
        same as it being rare — counting them would invent a denominator."""
        from eesti.vocab import band_progress, connect
        from eesti.wordlist import connect as wordlist_connect

        words = wordlist_connect()
        total = sum(b["size"] for b in band_progress(connect(tmp_path / "v.db"), words))
        ranked = words.execute(
            "SELECT COUNT(*) FROM words WHERE freq_rank BETWEEN 1 AND 4000"
        ).fetchone()[0]
        assert total == ranked

    def test_ignored_words_do_not_count_as_known(self, tmp_path):
        from eesti.vocab import IGNORED, band_progress, connect, set_status
        from eesti.wordlist import connect as wordlist_connect

        words = wordlist_connect()
        vocab = connect(tmp_path / "v.db")
        word = words.execute(
            "SELECT word FROM words WHERE freq_rank BETWEEN 1 AND 400 LIMIT 1"
        ).fetchone()[0]
        set_status(vocab, word, IGNORED)
        assert band_progress(vocab, words)[0]["known"] == 0


class TestEveryRungOnTheLadderCanBeReached:
    """A status nothing can set is a status that does not exist.

    `FAMILIAR` (3, `tuttav`) sat in `STATUS_NAMES` between "met it" and "know
    it" with **no writer anywhere**: no endpoint set it, no encounter produced
    it, and the store held zero rows at that value. Its one reader was an
    `in (LEARNING, FAMILIAR)` whose second term could never be true, so nothing
    misbehaved and nothing pointed at it.

    Same shape as the measurement with no writer, the endpoint with no caller,
    `[data-theme]` with nothing setting it, and `kind="vocab"` that no code
    produced — four found in four sprints, which is why this one is a test
    rather than a note.
    """

    #: How each rung is reached. `LEARNING` comes from meeting a word while
    #: reading; the settled three are choices the learner makes on the card.
    WRITERS = {
        "LEARNING": "record_encounter",
        "KNOWN": "set_status",
        "IGNORED": "set_status",
        "WELL_KNOWN": "set_status",
    }

    def test_every_named_status_has_a_way_in(self):
        from eesti import vocab

        named = {name for name, value in vars(vocab).items()
                 if name.isupper() and isinstance(value, int)
                 and value in vocab.STATUS_NAMES}
        assert named == set(self.WRITERS), (
            "a rung was added or removed without saying how it is reached: "
            f"{sorted(named ^ set(self.WRITERS))}")

    def test_the_writers_exist(self):
        from eesti import vocab

        for rung, writer in self.WRITERS.items():
            assert hasattr(vocab, writer), f"{rung} names a writer that is gone"

    def test_each_one_round_trips_through_its_writer(self, tmp_path):
        """The check that matters: not that a name exists, but that setting it
        and reading it back gives the value asked for."""
        from eesti import vocab

        conn = vocab.connect(tmp_path / "vocab.db")
        vocab.record_encounter(conn, ["kohtuma"])
        assert vocab.statuses(conn, ["kohtuma"])["kohtuma"] == vocab.LEARNING

        for value in (vocab.KNOWN, vocab.IGNORED, vocab.WELL_KNOWN):
            vocab.set_status(conn, "kohtuma", value)
            assert vocab.statuses(conn, ["kohtuma"])["kohtuma"] == value

    def test_a_settled_word_is_one_the_app_stops_proposing(self):
        """`SETTLED` is the boundary the whole ladder exists to draw, and the
        code reads it as a threshold rather than by equality."""
        from eesti import vocab

        assert vocab.SETTLED == {vocab.KNOWN, vocab.IGNORED, vocab.WELL_KNOWN}
        assert all(v >= vocab.KNOWN for v in vocab.SETTLED)
        assert vocab.LEARNING < vocab.KNOWN
