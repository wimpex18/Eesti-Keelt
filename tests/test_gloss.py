"""Word meanings: the layer the app did not have, and the request it kept repeating.

Two separate defects meet here.

**The app could not say what any word meant.** 160 316 words, each with a CEFR
level and a full paradigm, and no meaning attached to one of them. Generate
twelve B1 object-case drills and you get `etendus`, `luuletus`, `rahakott`,
`kingitus`, `kleit` — a learner produces `kleidi` for "Ma ostsin ____", is
marked correct, and has practised morphology on a token. The project's stated
scope is learning Estonian, not only sitting the exam.

**And it asked Sõnaveeb the same questions forever.** `sonapi`'s cache was in
`data/cache/`, which is git-ignored, is not the content volume, and is not in
the state snapshot. Cloud Run scales to zero, so every cold start began with an
empty cache and re-requested every word the learner looked at — and spaced
repetition guarantees the same words come back. The module whose central promise
is "single lookups only, they ask not to be batched" had storage that made it
re-ask indefinitely. Same shape as the circuit breaker keeping its counts in a
module-level dict: state that protects against restarts must survive one.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import gloss
from eesti.providers import sonapi


def info(word="kleit", ru=("платье",), rection=None, itype="2"):
    return sonapi.WordInfo(
        word=word, word_classes=("noomen",), rection=rection,
        inflection_type=itype, definition="…", examples=(),
        translations={"ru": ru, "en": ("dress",)},
    )


@pytest.fixture
def conn(tmp_path):
    # Without the shipped glossary: these tests are about the store's own
    # mechanics, and 294 rows they did not write would make every count assert
    # against a number that moves whenever the glossary grows.
    return gloss.connect(tmp_path / "v.db", seed_glosses=False)



def _redirect(monkeypatch, app_module, tmp_path):
    """Point the learner databases at a scratch directory, on both names.

    `config` is the single source the application reads; `app` keeps copies
    that several tests here write through. Setting them together means a test
    cannot write to one file while the endpoint under test reads another --
    which is precisely what happened when the application stopped reading its
    own copies.
    """
    from eesti import config as config_module

    for name, stem in (("VOCAB_DB", "v"), ("PROGRESS_DB", "p"),
                       ("REVIEW_DB", "r"), ("NOTION_DB", "n")):
        target = str(tmp_path / f"{stem}.db")
        monkeypatch.setattr(config_module, name, target)
        monkeypatch.setattr(app_module, name, target, raising=False)


class TestAWordIsAskedAboutOnce:
    def test_a_stored_word_never_reaches_the_network(self, conn, monkeypatch):
        gloss.save(conn, "kleit", info())

        def explode(*a, **k):
            raise AssertionError("asked Sõnaveeb for a word it already had")

        monkeypatch.setattr(sonapi, "lookup", explode)
        assert gloss.remember(conn, "kleit").russian == ("платье",)

    def test_a_miss_is_stored_too(self, conn, monkeypatch):
        """"No such word" is a fact worth keeping. Re-asking for it every
        session is the same load on someone else's server with none of the
        benefit."""
        calls = []
        monkeypatch.setattr(sonapi, "lookup",
                            lambda w, **k: calls.append(w) or None)
        assert gloss.remember(conn, "mitteolemasolev").found is False
        assert gloss.remember(conn, "mitteolemasolev").found is False
        assert len(calls) == 1

    def test_it_survives_a_restart(self, tmp_path, monkeypatch):
        """The whole point. A store that lives in the container's disk is a
        store Cloud Run empties every time it scales to zero."""
        first = gloss.connect(tmp_path / "v.db")
        monkeypatch.setattr(sonapi, "lookup", lambda w, **k: info())
        gloss.remember(first, "kleit")
        first.close()

        second = gloss.connect(tmp_path / "v.db")   # a brand new process
        monkeypatch.setattr(sonapi, "lookup", lambda w, **k: (_ for _ in ()).throw(
            AssertionError("re-fetched after a restart")))
        assert gloss.remember(second, "kleit").russian == ("платье",)

    def test_it_lives_where_the_snapshot_will_carry_it(self):
        """`vocab.db` is in STATE_DATABASES. Any other file and the store would
        reproduce exactly the bug it was written to fix."""
        from eesti import app as app_module
        from eesti.api import state as state_module

        assert "vocab" in state_module.STATE_DATABASES
        assert app_module.gloss_db.__doc__ and "snapshot" in app_module.gloss_db.__doc__


class TestNothingHereCanBecomeAHarvest:
    """Sõnaveeb's maintainers ask not to be batch-requested. A daily cap turns
    that from a promise into arithmetic: at this rate the full 160 316-word list
    takes about three and a half years."""

    def test_the_budget_is_a_persons_pace_not_a_scrapers(self):
        assert 30 <= gloss.DAILY_BUDGET <= 500

    def test_the_cap_is_enforced(self, conn, monkeypatch):
        monkeypatch.setattr(gloss, "DAILY_BUDGET", 3)
        monkeypatch.setattr(sonapi, "lookup", lambda w, **k: info(word=w))
        got = [gloss.remember(conn, f"sona{i}") for i in range(6)]
        assert sum(g is not None for g in got) == 3
        assert gloss.budget_left(conn) == 0

    def test_a_dead_service_cannot_be_retried_into_a_flood(self, conn, monkeypatch):
        """Budget is spent on the attempt. Charging only successes would let a
        service that is down be hammered without limit."""
        monkeypatch.setattr(gloss, "DAILY_BUDGET", 3)

        def boom(*a, **k):
            raise OSError("refused")

        monkeypatch.setattr(sonapi, "lookup", boom)
        for i in range(10):
            assert gloss.remember(conn, f"sona{i}") is None
        assert gloss.budget_left(conn) == 0

    def test_the_budget_survives_a_restart(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gloss, "DAILY_BUDGET", 2)
        monkeypatch.setattr(sonapi, "lookup", lambda w, **k: info(word=w))
        first = gloss.connect(tmp_path / "v.db")
        gloss.remember(first, "aa")
        first.close()
        second = gloss.connect(tmp_path / "v.db")
        assert gloss.budget_left(second) == 1

    def test_the_bulk_read_is_local_only(self, conn, monkeypatch):
        """`stored_many` is a SELECT. Giving it a live fallback would be the
        loop over `sonapi` this design exists to prevent, under another name."""
        def explode(*a, **k):
            raise AssertionError("stored_many went to the network")

        monkeypatch.setattr(sonapi, "lookup", explode)
        gloss.save(conn, "kleit", info())
        got = gloss.stored_many(conn, ["kleit", "puudub", "veelüks"])
        assert set(got) == {"kleit"}

    def test_stored_many_does_not_spend_budget(self, conn):
        gloss.stored_many(conn, ["a", "b", "c"])
        assert gloss.budget_left(conn) == gloss.DAILY_BUDGET


class TestTheStoreItself:
    def test_an_empty_lemma_is_not_a_lookup(self, conn, monkeypatch):
        monkeypatch.setattr(sonapi, "lookup", lambda w, **k: info())
        assert gloss.remember(conn, "  ") is None
        assert gloss.budget_left(conn) == gloss.DAILY_BUDGET

    def test_a_re_save_replaces_rather_than_duplicates(self, conn):
        gloss.save(conn, "kleit", info(ru=("платье",)))
        gloss.save(conn, "kleit", info(ru=("платье", "платьице")))
        assert gloss.stats(conn)["words"] == 1
        assert gloss.stored(conn, "kleit").russian == ("платье", "платьице")

    def test_russian_with_a_separator_in_it_round_trips(self, conn):
        """Stored with a unit separator, not a comma: Sõnaveeb's own glosses
        contain commas."""
        gloss.save(conn, "lavastus", info(ru=("театральное представление", "пьеса")))
        assert gloss.stored(conn, "lavastus").russian == (
            "театральное представление", "пьеса")

    def test_stats_counts_what_it_says(self, conn):
        gloss.save(conn, "kleit", info())
        gloss.save(conn, "puudub", None)
        s = gloss.stats(conn)
        assert (s["words"], s["found"], s["with_russian"]) == (2, 1, 1)


class TestThePracticeSetShowsWhatTheWordsMean:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        # Redirected, because a path opened inside a function cannot be pointed
        # anywhere else by its caller -- and a test that writes into the
        # developer's real vocab.db reports differently in CI.
        #
        # On `config` *and* on `app`. `config` is what the application reads
        # now; the copies on `app` are kept in step because tests in this file
        # write their fixtures through `app_module.VOCAB_DB`, and two names for
        # one file that disagree is the bug this consolidation removed.
        _redirect(monkeypatch, app_module, tmp_path)
        return TestClient(app_module.app)

    def test_a_practice_set_never_waits_on_sonaveeb(self, client, monkeypatch):
        """Ten items would be ten live lookups — the batch request `sonapi`
        deliberately has no helper for, in front of a learner who is waiting."""
        def explode(*a, **k):
            raise AssertionError("building a practice set went to the network")

        monkeypatch.setattr(sonapi, "lookup", explode)
        got = client.post("/api/practice", json={"count": 5, "topic": "osastav"})
        assert got.status_code == 200
        assert got.json()["glosses"] == {}

    def test_a_stored_gloss_reaches_the_set(self, client, tmp_path, monkeypatch):
        from eesti import app as app_module

        conn = gloss.connect(app_module.VOCAB_DB)
        first = client.post(
            "/api/practice", json={"count": 3, "topic": "osastav"}).json()
        lemma = first["items"][0]["lemma"]
        gloss.save(conn, lemma, info(word=lemma, ru=("платье",)))

        def explode(*a, **k):
            raise AssertionError("went to the network for a word it had")

        monkeypatch.setattr(sonapi, "lookup", explode)
        again = client.post(
            "/api/practice", json={"count": 3, "topic": "osastav", "seed": 1}).json()
        seen = {i["lemma"] for i in again["items"]}
        if lemma in seen:
            assert again["glosses"][lemma] == ["платье"]

    def test_answering_glosses_exactly_the_word_just_answered(
        self, client, monkeypatch
    ):
        """One lookup, for the one word the learner spent thought on — and
        after the struggle with the form, which is when a meaning sticks."""
        asked = []
        monkeypatch.setattr(sonapi, "lookup",
                            lambda w, **k: asked.append(w) or info(word=w, ru=("платье",)))
        got = client.post("/api/practice/answer", json={
            "topic": "osastav", "prompt": "Ma ostsin ____.", "answer": "kleiti",
            "given": "kleiti", "lemma": "kleit"}).json()
        assert got["russian"] == ["платье"]
        assert asked == ["kleit"]

    def test_a_dead_dictionary_never_costs_a_grade(self, client, monkeypatch):
        def boom(*a, **k):
            raise OSError("refused")

        monkeypatch.setattr(sonapi, "lookup", boom)
        got = client.post("/api/practice/answer", json={
            "topic": "osastav", "prompt": "Ma ostsin ____.", "answer": "kleiti",
            "given": "kleiti", "lemma": "kleit"})
        assert got.status_code == 200
        assert got.json()["correct"] is True

        # It used to assert `russian == []` here, and that is no longer the
        # right guarantee: `kleit` is in the shipped glossary, so a dead
        # dictionary now costs the learner nothing at all rather than costing
        # them the translation. The grade was never at risk either way.
        assert got.json()["russian"] == ["платье"]

    def test_an_unseeded_word_degrades_quietly(self, client, monkeypatch):
        """The other half: a word the glossary does not carry still shows no
        translation rather than an error, which is what the dead-dictionary
        path has always promised."""
        def boom(*a, **k):
            raise OSError("refused")

        monkeypatch.setattr(sonapi, "lookup", boom)
        got = client.post("/api/practice/answer", json={
            "topic": "osastav", "prompt": "Ma ostsin ____.", "answer": "seinamaalingut",
            "given": "seinamaalingut", "lemma": "seinamaaling"})
        assert got.status_code == 200
        assert got.json()["correct"] is True and got.json()["russian"] == []

    def test_an_item_with_no_lemma_asks_nothing(self, client, monkeypatch):
        """Question-word items have no lemma — the word itself is the answer."""
        def explode(*a, **k):
            raise AssertionError("looked up the empty string")

        monkeypatch.setattr(sonapi, "lookup", explode)
        got = client.post("/api/practice/answer", json={
            "topic": "kusisonad", "prompt": "____ sa oled?", "answer": "kes",
            "given": "kes", "lemma": ""})
        assert got.status_code == 200 and got.json()["russian"] == []


class TestThePageShowsIt:
    @staticmethod
    def _page() -> str:
        from pathlib import Path

        return (Path(__file__).resolve().parent.parent
                / "eesti" / "web" / "index.html").read_text(encoding="utf-8")

    def test_the_practice_item_is_handed_the_gloss_map(self):
        page = self._page()
        assert "res.glosses || {}" in page
        assert "function renderPracticeItem(it, topic, i, glosses)" in page

    def test_the_verdict_shows_a_freshly_fetched_meaning(self):
        assert "res.russian?.length" in self._page()


class TestTheReviewQueueIsGlossedToo:
    """The queue is where the same words come back on purpose, so a missing
    meaning compounds there: an item can be answered from the form alone,
    review after review, without the word ever meaning anything."""

    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        _redirect(monkeypatch, app_module, tmp_path)
        return TestClient(app_module.app)

    def test_the_queue_carries_glosses(self, client):
        from eesti import app as app_module

        client.post("/api/review", json={
            "kind": "obj-case", "lemma": "kleit", "prompt": "Ma ostsin ____.",
            "answer": "kleidi"})
        gloss.save(gloss.connect(app_module.VOCAB_DB), "kleit",
                   info(ru=("платье",)))
        got = client.get("/api/review?limit=20").json()
        assert got["glosses"]["kleit"] == ["платье"]

    def test_loading_the_queue_never_goes_to_the_network(self, client, monkeypatch):
        def explode(*a, **k):
            raise AssertionError("twenty queue items became twenty lookups")

        monkeypatch.setattr(sonapi, "lookup", explode)
        assert client.get("/api/review?limit=20").status_code == 200

    def test_the_page_reads_the_map(self):
        from pathlib import Path

        page = (Path(__file__).resolve().parent.parent
                / "eesti" / "web" / "index.html").read_text(encoding="utf-8")
        assert "function renderReview(it, glosses)" in page
        assert "renderReview(it, glosses || {})" in page
