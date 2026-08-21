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


class TestSettlingAWord:
    """The status ladder has five values and, until 2026-08-21, three had no
    writer at all.

    `õpin` is set automatically on the first encounter while reading and `tean`
    by the word card's button. `tuttav`, `eiran` and `teadsin ammu` were
    modelled, stored, counted by the overview — and unreachable from anywhere a
    learner could click. That is this project's most recurring bug (a
    measurement with no writer, an endpoint with no caller) in a third costume.

    `eiran` is the one a vocabulary list needs and a reader does not: browsing
    B1 nouns turns up `riigivisiit` and `seinamaaling`, which are real words,
    correctly listed, and not what this learner will spend a morning on.
    """

    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        from eesti import app as app_module
        from eesti import config as config_module

        for name, stem in (("VOCAB_DB", "v"), ("PROGRESS_DB", "p"),
                           ("REVIEW_DB", "r"), ("NOTION_DB", "n")):
            target = str(tmp_path / f"{stem}.db")
            monkeypatch.setattr(config_module, name, target)
            monkeypatch.setattr(app_module, name, target, raising=False)
        return TestClient(app_module.app)

    def _status(self, client, lemma):
        from eesti import app as app_module
        from eesti.vocab import statuses

        return statuses(app_module.vocab_db(), [lemma])[lemma]

    def test_the_default_is_known(self, client):
        from eesti.vocab import KNOWN

        assert client.post("/api/vocab/known",
                           json={"lemmas": ["kleit"]}).status_code == 200
        assert self._status(client, "kleit") == KNOWN

    def test_ignore_is_reachable_now(self, client):
        from eesti.vocab import IGNORED

        r = client.post("/api/vocab/known",
                        json={"lemmas": ["riigivisiit"], "status": "ignore"})
        assert r.status_code == 200
        assert self._status(client, "riigivisiit") == IGNORED

    def test_long_known_is_reachable_now(self, client):
        from eesti.vocab import WELL_KNOWN

        r = client.post("/api/vocab/known",
                        json={"lemmas": ["ema"], "status": "long_known"})
        assert r.status_code == 200
        assert self._status(client, "ema") == WELL_KNOWN

    def test_the_older_flag_still_works(self, client):
        """`long_known` was the only way to reach `teadsin ammu` and no caller
        ever sent it. Kept working rather than removed, since removing it would
        be a second change riding on this one."""
        from eesti.vocab import WELL_KNOWN

        client.post("/api/vocab/known",
                    json={"lemmas": ["isa"], "long_known": True})
        assert self._status(client, "isa") == WELL_KNOWN

    def test_an_unknown_status_is_refused(self, client):
        assert client.post("/api/vocab/known",
                           json={"lemmas": ["x"], "status": "nonsense"}
                           ).status_code == 422

    def test_ignored_and_known_stay_distinguishable(self, client):
        """Collapsing them would make the known-word count wrong, and that
        count orders the reading list and feeds the readiness verdict."""
        from eesti.vocab import IGNORED, KNOWN

        client.post("/api/vocab/known", json={"lemmas": ["kleit"]})
        client.post("/api/vocab/known",
                    json={"lemmas": ["riigivisiit"], "status": "ignore"})
        assert self._status(client, "kleit") == KNOWN
        assert self._status(client, "riigivisiit") == IGNORED

    def test_both_count_as_settled(self, client):
        """Different facts, same consequence: stop proposing the word."""
        from eesti.vocab import SETTLED

        client.post("/api/vocab/known", json={"lemmas": ["kleit"]})
        client.post("/api/vocab/known",
                    json={"lemmas": ["riigivisiit"], "status": "ignore"})
        assert self._status(client, "kleit") in SETTLED
        assert self._status(client, "riigivisiit") in SETTLED

    def test_the_page_can_reach_every_settled_status(self):
        """The contract that was broken: a status the page cannot set is a
        status that does not exist for the learner."""
        from pathlib import Path

        page = (Path(__file__).resolve().parents[1]
                / "eesti" / "web" / "index.html").read_text(encoding="utf-8")
        assert '"ignore"' in page, "the page cannot reach `eiran`"
        assert "#skipBtn" in page and "#knowBtn" in page
