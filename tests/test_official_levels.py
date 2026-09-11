"""EKI's level vocabulary: the exam board institute's own A1/A2/B1 word lists.

Until this landed, every CEFR level in this app came from the enriched Ekilex
list — a derived estimate carrying a tag for 6.2 % of its lemmas. EKI publishes
the levels outright, under CC BY 4.0, and this is the import that lets them win.

The tests worth having here are about the two things that could go quietly
wrong: a frequency **count** landing in a column that holds **ranks**, and a
rebuild silently dropping the authoritative levels.
"""

from __future__ import annotations

import pytest

from eesti import wordlist

#: EKI's real shape: `LEMMA POS SAGEDUS TASE`, tab separated, one header row.
SAMPLE = "\n".join([
    "LEMMA\tPOS\tSAGEDUS\tTASE",
    "aadress\tS\t150832\tA1",     # already known, same level
    "aabits\tS\t4117\tB1",        # already known, level disagrees
    "kõuepilv\tS\t31\tB1",        # unknown to the enriched list
    "araabia\tG\t900\tB1",        # the genitive-attribute class
    "CD\tY\t\tA2",                # an abbreviation, no frequency
    "mingi\tP\t4321\tC1",         # a level this app does not teach
])


@pytest.fixture
def words(tmp_path):
    conn = wordlist.connect(tmp_path / "eesti.db")
    conn.executemany(
        "INSERT INTO words(word, freq_rank, proficiency, pos) VALUES (?,?,?,?)",
        [("aadress", 2577, "A1", "s"), ("aabits", 0, "A2", "s")],
    )
    conn.commit()
    return conn


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "A1A2B1.txt"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


class TestReadingTheFile:
    def test_it_keeps_only_the_levels_this_app_teaches(self, sample):
        rows = wordlist.read_official_levels(sample)
        assert {r[1] for r in rows} == {"A1", "B1", "A2"}
        assert "mingi" not in {r[0] for r in rows}, "C1 is not a level here"

    def test_a_file_of_the_wrong_shape_says_what_it_wanted(self, tmp_path):
        wrong = tmp_path / "nope.txt"
        wrong.write_text("word,level\nkass,A1\n", encoding="utf-8")
        with pytest.raises(ValueError, match="LEMMA"):
            wordlist.read_official_levels(wrong)

    def test_a_missing_frequency_is_none_rather_than_zero(self, sample):
        rows = {r[0]: r for r in wordlist.read_official_levels(sample)}
        assert rows["CD"][3] is None, "blank must not become 0 and sort first"


class TestApplyingThem:
    def test_eki_wins_where_the_two_disagree(self, words, sample):
        wordlist.import_official_levels(words, sample)
        row = words.execute(
            "SELECT proficiency, level_source FROM words WHERE word = 'aabits'"
        ).fetchone()
        assert (row["proficiency"], row["level_source"]) == ("B1", "eki")

    def test_a_word_only_eki_knows_is_added_and_drillable(self, words, sample):
        wordlist.import_official_levels(words, sample)
        assert any(w.word == "kõuepilv" for w in wordlist.nouns_at_level(words, ("B1",)))

    def test_pos_codes_are_mapped_not_copied(self, words, sample):
        """`G` is this project's `adjg`; a raw `G` would fail every pos query."""
        wordlist.import_official_levels(words, sample)
        assert words.execute(
            "SELECT pos FROM words WHERE word = 'araabia'"
        ).fetchone()["pos"] == "adjg"

    def test_an_abbreviation_never_becomes_declinable(self, words, sample):
        """Vabamorf will happily synthesise a genitive for `CD`. It should not
        be asked: the same rule `declines()` already applies to untagged words."""
        wordlist.import_official_levels(words, sample)
        pos = words.execute("SELECT pos FROM words WHERE word = 'CD'").fetchone()["pos"]
        assert not wordlist.declines(pos)

    def test_a_corpus_count_never_lands_in_the_rank_column(self, words, sample):
        """The trap this table exists to avoid. EKI's `aadress` is 150 832
        occurrences; `freq_rank` 150 832 would mean the 150 832nd commonest
        word, and would drill one of the first words anybody learns last."""
        wordlist.import_official_levels(words, sample)
        assert words.execute(
            "SELECT freq_rank FROM words WHERE word = 'aadress'"
        ).fetchone()["freq_rank"] == 2577
        assert words.execute(
            "SELECT freq_rank FROM words WHERE word = 'kõuepilv'"
        ).fetchone()["freq_rank"] is None

    def test_an_untouched_word_keeps_saying_where_its_level_came_from(
        self, words, sample
    ):
        words.execute(
            "INSERT INTO words(word, proficiency, pos) VALUES ('kirjutuslaud','B1','s')"
        )
        words.commit()
        wordlist.import_official_levels(words, sample)
        assert words.execute(
            "SELECT level_source FROM words WHERE word = 'kirjutuslaud'"
        ).fetchone()["level_source"] is None

    def test_importing_twice_changes_nothing(self, words, sample):
        first = wordlist.import_official_levels(words, sample)
        again = wordlist.import_official_levels(words, sample)
        assert again["levelled"] == first["levelled"]
        assert again["added"] == 0, "the second run must add nobody"


class TestSurvivingARebuild:
    def test_the_levels_are_reapplied_after_words_is_replaced(self, words, sample):
        """`build()` deletes every row in `words`, which wipes `level_source`
        and every level EKI supplied. The levels live in their own table so
        that costs a re-apply rather than a second trip to EKI's download form.
        """
        wordlist.import_official_levels(words, sample)
        with words:
            words.execute("DELETE FROM words")          # what `build()` does
        assert wordlist.apply_official_levels(words)["added"] == 5  # the C1 row never entered
        assert words.execute(
            "SELECT proficiency FROM words WHERE word = 'aabits'"
        ).fetchone()["proficiency"] == "B1"
