"""The list the app did not have.

`/api/lookup/{word}` answers "what is this word". Nothing answered "which
words should I learn", and only the second question is askable by somebody who
does not yet know the vocabulary — which is the entire user base of a language
app. 160 316 words were reachable only by a person who already knew what was
in there.

Three of these tests exist because the feature was wrong the first time, in
ways no assertion caught and a screenshot did:

  * ordering treated `freq_rank = 0` as the commonest word rather than as
    "unranked", so the first page was alphabetical a-words;
  * the Russian gloss column packs senses with `\\x1f`, and handing it to the
    page raw rendered the separator as tofu;
  * "veel sõnu" appended each page twice.
"""

from __future__ import annotations

import pytest

from eesti import vocab


@pytest.fixture
def words(tmp_path):
    """A wordlist with the two properties that matter: ranked and unranked
    words mixed, and a compound part-of-speech tag."""
    import sqlite3

    conn = sqlite3.connect(tmp_path / "words.db")
    conn.executescript("""
        CREATE TABLE words (word TEXT PRIMARY KEY, freq_rank INTEGER,
                            proficiency TEXT, pos TEXT);
        CREATE TABLE object_cases (word TEXT PRIMARY KEY, genitive TEXT NOT NULL,
                            partitive TEXT NOT NULL, distinct_ INTEGER NOT NULL);
    """)
    conn.executemany("INSERT INTO words VALUES (?,?,?,?)", [
        ("aabits", 0, "B1", "s"),        # unranked: must NOT lead
        ("kurat", 189, "B1", "s"),       # ranked: must lead
        ("iga", 206, "B1", "s"),
        ("ainus", 404, "B1", "adj,s"),   # compound tag
        ("jooksma", 300, "B1", "v"),
        ("maja", 50, "A2", "s"),
    ])
    conn.executemany("INSERT INTO object_cases VALUES (?,?,?,?)", [
        ("kurat", "kuradi", "kuradit", 1),
        ("maja", "maja", "maja", 0),     # no contrast: must not be shown
    ])
    conn.commit()
    return conn


@pytest.fixture
def store(tmp_path):
    return vocab.connect(str(tmp_path / "vocab.db"))


class TestOrdering:
    def test_the_commonest_word_comes_first(self, words, store):
        """`freq_rank = 0` means unranked in this dataset, not rank zero. Sorting
        on the raw column put all 597 unranked B1 words ahead of the 1 912
        ranked ones, so the first page a learner saw was alphabetical."""
        got = [i["word"] for i in vocab.browse(words, store, level="B1")["items"]]
        assert got[0] == "kurat", got
        assert got.index("kurat") < got.index("aabits")

    def test_unranked_words_are_still_offered(self, words, store):
        """Last, not absent — an unranked word is still vocabulary."""
        got = [i["word"] for i in vocab.browse(words, store, level="B1")["items"]]
        assert "aabits" in got


class TestFilters:
    def test_a_compound_part_of_speech_is_not_hidden(self, words, store):
        """`ainus` is tagged `adj,s`. Matching `pos` by equality drops it, and
        52 of the B1 adjectives carry a compound tag."""
        got = [i["word"] for i in
               vocab.browse(words, store, level="B1", pos="adj")["items"]]
        assert "ainus" in got

    def test_a_noun_filter_excludes_verbs(self, words, store):
        got = [i["word"] for i in
               vocab.browse(words, store, level="B1", pos="s")["items"]]
        assert "jooksma" not in got

    @pytest.mark.parametrize("bad", ["Z9", "b1", "A0"])
    def test_an_unknown_level_is_refused_not_ignored(self, words, store, bad):
        """Silently ignoring it would answer a different question than asked."""
        with pytest.raises(ValueError):
            vocab.browse(words, store, level=bad)

    def test_an_unknown_status_is_refused(self, words, store):
        with pytest.raises(ValueError):
            vocab.browse(words, store, status="nonsense")


class TestWhatTheLearnerHasMarked:
    def test_status_comes_from_the_same_ladder_the_reader_writes(self, words, store):
        vocab.set_status(store, "kurat", vocab.KNOWN)
        by_word = {i["word"]: i for i in
                   vocab.browse(words, store, level="B1")["items"]}
        assert by_word["kurat"]["status"] == vocab.KNOWN
        assert by_word["iga"]["status"] == vocab.UNKNOWN

    def test_filtering_to_new_hides_what_is_settled(self, words, store):
        vocab.set_status(store, "kurat", vocab.KNOWN)
        got = [i["word"] for i in
               vocab.browse(words, store, level="B1", status="new")["items"]]
        assert "kurat" not in got and "iga" in got

    def test_filtering_to_known_shows_only_that(self, words, store):
        vocab.set_status(store, "kurat", vocab.WELL_KNOWN)
        got = [i["word"] for i in
               vocab.browse(words, store, level="B1", status="known")["items"]]
        assert got == ["kurat"]


class TestTheGloss:
    def test_several_senses_are_joined_readably(self, words, store):
        """The column packs senses with \\x1f. Rendered raw it showed as
        `мейл\\x1fимейл` — a control character, drawn as tofu on the phone."""
        store.execute(
            "INSERT INTO word_gloss (lemma, russian, fetched) VALUES (?,?,?)",
            ("kurat", "чёрт\x1fдьявол", "2026-08-21"))
        store.commit()
        got = {i["word"]: i["russian"] for i in
               vocab.browse(words, store, level="B1")["items"]}
        assert got["kurat"] == "чёрт, дьявол"
        assert "\x1f" not in got["kurat"]

    def test_a_word_never_asked_about_has_no_gloss_and_no_error(self, words, store):
        got = {i["word"]: i["russian"] for i in
               vocab.browse(words, store, level="B1")["items"]}
        assert got["iga"] == ""

    def test_browsing_never_fetches(self, words, store, monkeypatch):
        """Sixty words on screen must not become sixty live lookups against a
        service that asks not to be batched."""
        import urllib.request

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (
            _ for _ in ()).throw(AssertionError("browsing hit the network")))
        vocab.browse(words, store, level="B1")


class TestTheCaseContrast:
    def test_it_is_shown_where_the_forms_differ(self, words, store):
        by_word = {i["word"]: i for i in
                   vocab.browse(words, store, level="B1")["items"]}
        assert by_word["kurat"]["genitive"] == "kuradi"
        assert by_word["kurat"]["partitive"] == "kuradit"

    def test_it_is_hidden_where_they_coincide(self, words, store):
        """`maja / maja` teaches nothing and reads as a mistake."""
        by_word = {i["word"]: i for i in
                   vocab.browse(words, store, level="A2")["items"]}
        assert by_word["maja"]["genitive"] is None


class TestPaging:
    def test_pages_do_not_overlap(self, words, store):
        a = vocab.browse(words, store, level="B1", limit=2, offset=0)["items"]
        b = vocab.browse(words, store, level="B1", limit=2, offset=2)["items"]
        assert not {i["word"] for i in a} & {i["word"] for i in b}

    def test_more_is_false_on_the_last_page(self, words, store):
        r = vocab.browse(words, store, level="B1", limit=50)
        assert r["more"] is False
