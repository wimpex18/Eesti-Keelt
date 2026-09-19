"""What a beginner is offered to read and to say: words within reach, a floor, and a
fallback.

A word is within reach when the learner marked it known or the word list puts it at
A1–A2. Texts are ranked by that share and never labelled with a CEFR level;
read-aloud sentences are short and made only of such words where enough exist.
"""

from __future__ import annotations

import pytest

from eesti.difficulty import (FLOOR, INDEPENDENT, INSTRUCTIONAL, REACH_LEVELS,
                              STEP, reach_lemmas, recommend, within_reach)
from eesti.pronunciation import SAY_MAX_WORDS, SAY_MIN_WORDS, sentences_to_say

EASY = frozenset({"mina", "elama", "ja", "käima", "iga", "päev", "töö", "eile",
                  "ostma", "pood", "uus", "raamat"})


def _words_db(tmp_path, rows):
    """A word list built with the app's own opener."""
    from eesti.wordlist import connect

    conn = connect(tmp_path / "words.db")
    conn.executemany(
        "INSERT OR REPLACE INTO words(word, freq_rank, proficiency, pos) "
        "VALUES (?,?,?,?)", rows)
    conn.commit()
    return conn


def _content(tmp_path, bodies):
    from eesti.sources import Item, add_items, connect, register

    conn = connect(tmp_path / "content.db")
    register(conn)
    add_items(conn, [Item("selges-keeles", "lugemine", title=f"Tekst {i}", body=b)
                     for i, b in enumerate(bodies)])
    conn.commit()
    return conn


class TestThePolicyConstants:
    def test_the_thresholds_are_the_reading_literatures(self):
        """95 % / 90 % bands (Laufer & Ravenhorst-Kalovski 2010; Hu & Nation 2000) and
        an 80 % floor, where Hu & Nation found no reader comprehending adequately."""
        assert (INDEPENDENT, INSTRUCTIONAL, FLOOR) == (0.95, 0.90, 0.80)

    def test_reach_is_a1_to_a2_for_an_a1_learner(self):
        assert REACH_LEVELS == ("A1", "A2")

    def test_read_aloud_is_one_breath(self):
        assert (SAY_MIN_WORDS, SAY_MAX_WORDS) == (3, 8)


class TestWithinReach:
    def test_counts_running_words_not_distinct_lemmas(self):
        # "raamat" twice: two of four running words, one of three lemmas.
        got = within_reach("Raamat, raamat ja pood.", set(), frozenset({"raamat"}))
        assert got["total"] == 4 and got["in_reach"] == 2
        assert got["coverage"] == 0.5

    def test_a_known_word_is_within_reach_whatever_its_level(self):
        text = "Eile ostsin poest uue raamatu."
        without = within_reach(text, set(), frozenset())
        with_known = within_reach(text, {"pood"}, frozenset())
        assert without["coverage"] == 0.0
        assert with_known["known"] == 1 and with_known["coverage"] == 0.2

    def test_names_and_numbers_are_left_out_of_a_reading_share(self):
        got = within_reach("Ma elan Tallinnas ja käin iga päev tööl.", set(), EASY)
        assert got["coverage"] == 1.0 and got["total"] == 7 and got["words"] == 8

    def test_strict_counts_an_unlisted_name_against_a_sentence(self):
        got = within_reach("Ma elan Tallinnas ja käin iga päev tööl.", set(), EASY,
                           strict=True)
        assert got["total"] == 8 and got["coverage"] == round(7 / 8, 3)

    def test_the_band_follows_the_thresholds(self):
        assert within_reach("Eile ostsin poest uue raamatu.", set(),
                            EASY)["readability"] == "iseseisev"
        assert within_reach("Eile ostsin poest uue auto.", set(),
                            EASY)["readability"] == "raske"

    def test_reach_is_read_from_the_word_list(self, tmp_path):
        words = _words_db(tmp_path, [("raamat", 1, "A1", "s"), ("pood", 2, "A2", "s"),
                                     ("riik", 3, "B1", "s"), ("uus", 4, None, "adj")])
        assert reach_lemmas(words) >= {"raamat", "pood"}
        assert not {"riik", "uus"} & reach_lemmas(words)

    def test_no_word_list_is_an_empty_reach_not_an_error(self):
        assert reach_lemmas(None) == frozenset()


def _item(id_, coverage, words):
    return {"id": id_, "coverage": coverage, "words": words}


class TestRecommend:
    def test_most_within_reach_first(self):
        got = recommend([_item("a", 0.85, 30), _item("b", 0.97, 30),
                         _item("c", 0.91, 30)], limit=5)
        assert [i["id"] for i in got["items"]] == ["b", "c", "a"]

    def test_shorter_first_inside_one_step(self):
        """0.86 and 0.89 share a 5-point step, so the shorter text leads."""
        assert STEP == 0.05
        got = recommend([_item("long", 0.89, 120), _item("short", 0.86, 30)],
                        limit=5)
        assert [i["id"] for i in got["items"]] == ["short", "long"]

    def test_a_step_outranks_length(self):
        got = recommend([_item("short", 0.86, 10), _item("long", 0.91, 300)],
                        limit=5)
        assert [i["id"] for i in got["items"]] == ["long", "short"]

    def test_texts_below_the_floor_are_not_recommended(self):
        got = recommend([_item("fit", 0.82, 40), _item("hard", 0.62, 20)], limit=5)
        assert [i["id"] for i in got["items"]] == ["fit"]
        assert got["fallback"] is False and got["recommendable"] == 1

    def test_the_whole_returned_set_clears_the_floor(self):
        items = [_item(str(n), n / 100, 50) for n in range(40, 100)]
        got = recommend(items, limit=25)
        assert len(got["items"]) == 20
        assert all(i["coverage"] >= FLOOR for i in got["items"])

    def test_nothing_clears_the_floor_falls_back_to_the_least_hard(self):
        got = recommend([_item("a", 0.40, 50), _item("b", 0.70, 50),
                         _item("c", 0.55, 50)], limit=2)
        assert got["fallback"] is True
        assert [i["id"] for i in got["items"]] == ["b", "c"]

    def test_an_empty_shelf_is_not_a_fallback(self):
        assert recommend([], limit=5) == {"items": [], "fallback": False,
                                          "recommendable": 0}


class TestTheReadingEndpoint:
    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        pytest.importorskip("httpx2")
        from fastapi.testclient import TestClient

        from eesti import config
        from eesti.app import app

        _content(tmp_path, [
            # Every word at A1 in the fixture word list.
            "Sõber ostab raamatu. Sõber loeb raamatut. Sõber elab majas.",
            # Mostly unlisted words.
            "Riigikohus ei võtnud tema kaitsja kaebust arutusele. Kohtunik "
            "selgitas otsust pikalt ja rahulikult kõigile osapooltele.",
        ])
        monkeypatch.setattr(config, "CONTENT_DB", str(tmp_path / "content.db"))
        return TestClient(app)

    def test_the_reachable_text_is_recommended_and_the_hard_one_is_not(self, client):
        got = client.get("/api/reading/next?limit=5").json()
        titles = [i["title"] for i in got["items"]]
        assert titles == ["Tekst 0"], got
        assert got["fallback"] is False
        assert got["items"][0]["coverage"] >= FLOOR

    def test_no_recommendation_carries_a_cefr_level(self, client):
        got = client.get("/api/reading/next?limit=5").json()
        assert all("level" not in item for item in got["items"])

    def test_the_note_says_why_in_russian(self, client):
        note = client.get("/api/reading/next?limit=5").json()["note"]
        assert "посильных слов" in note and "не уровень текста" in note


class TestReadAloud:
    BODY = ("Ma elan Tallinnas ja käin iga päev tööl. "
            "Eile ostsin poest uue raamatu. "
            "Nime „E-Ticketing“ all tuntud projektis osaleb viis riiki. "
            "Ta ostis raamatu. "
            "Riigikohus ei võtnud tema kaitsja kaebust arutusele ega selgitanud "
            "oma otsust kellelegi.")

    @pytest.fixture
    def content(self, tmp_path):
        return _content(tmp_path, [self.BODY])

    @pytest.fixture
    def words(self, tmp_path):
        return _words_db(tmp_path, [(w, n, "A1", "s") for n, w in enumerate(
            sorted(EASY | {"tema"}))])

    def test_every_sentence_is_within_the_word_cap(self, content, words):
        items = sentences_to_say(content, count=20, seed=1, words=words)
        assert items
        assert all(SAY_MIN_WORDS <= len(i.text.split()) <= SAY_MAX_WORDS
                   for i in items)

    def test_fully_reachable_sentences_come_first(self, content, words):
        items = sentences_to_say(content, count=20, seed=1, words=words)
        texts = [i.text for i in items]
        assert set(texts[:2]) == {"Eile ostsin poest uue raamatu.",
                                  "Ta ostis raamatu."}
        assert all(i.coverage == 1.0 for i in items[:2])

    def test_too_few_qualifying_fills_with_the_most_reachable(self, content, words):
        """The unlisted name and number rank the news sentence below the one whose
        only miss is `Tallinnas`."""
        items = sentences_to_say(content, count=20, seed=1, words=words)
        rest = [i.text for i in items[2:]]
        assert rest[0].startswith("Ma elan Tallinnas")
        assert rest[-1].startswith("Nime")
        assert [i.coverage for i in items[2:]] == sorted(
            (i.coverage for i in items[2:]), reverse=True)

    def test_enough_qualifying_means_only_qualifying(self, content, words):
        items = sentences_to_say(content, count=2, seed=4, words=words)
        assert all(i.coverage == 1.0 for i in items)

    def test_a_known_word_can_make_a_sentence_qualify(self, content, words):
        known = {"tallinn"}
        items = sentences_to_say(content, count=3, seed=1, words=words, known=known)
        assert all(i.coverage == 1.0 for i in items)

    def test_the_choice_is_reproducible(self, content, words):
        a = [i.text for i in sentences_to_say(content, count=3, seed=7, words=words)]
        b = [i.text for i in sentences_to_say(content, count=3, seed=7, words=words)]
        assert a == b
