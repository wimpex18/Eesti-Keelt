"""Read-aloud comparison.

The claim this file has to earn: comparing a transcript against a *known
target* is a real measurement, unlike scoring pronunciation from audio. So the
tests are about the alignment being right — including the case that makes a
naive implementation useless, a dropped word early in the sentence.
"""

from __future__ import annotations

import pytest

from eesti.pronunciation import (ReadAloud, compare, normalise,
                                 sentences_to_say, words_to_say)


class TestNormalise:
    def test_punctuation_and_case_are_ignored(self):
        assert normalise("Ma lähen KOOLI!") == ["ma", "lähen", "kooli"]

    def test_decomposed_and_composed_estonian_letters_match(self):
        """`ä` can arrive as one codepoint or as `a` + combining diaeresis
        depending on the recogniser; two strings that render identically must
        compare equal."""
        assert normalise("täna") == normalise("täna")

    def test_empty_input_is_empty_not_an_error(self):
        assert normalise("") == [] and normalise(None) == []


class TestCompare:
    def test_a_perfect_reading_matches_everything(self):
        c = compare("Ma lugesin eile raamatu läbi.", "ma lugesin eile raamatu läbi")
        assert c.matched == c.total == 5
        assert c.missed == [] and c.ratio == 1.0

    def test_a_dropped_word_costs_only_that_word(self):
        """The case that makes a naive zip useless: everything after the gap
        would misalign and the score would measure the alignment, not the
        speech."""
        c = compare("Ma lugesin eile raamatu läbi.", "ma lugesin raamatu läbi")
        assert c.missed == ["eile"]
        assert c.matched == 4

    def test_a_substituted_word_reports_what_was_heard_instead(self):
        c = compare("Ma lähen kooli.", "ma lähen kohli")
        assert c.missed == ["kooli"]
        assert [w.heard for w in c.words] == ["ma", "lähen", "kohli"]

    def test_extra_words_are_reported_separately(self):
        c = compare("Tere", "tere ja tere tulemast")
        assert c.matched == 1
        assert c.extra == ["ja", "tere", "tulemast"]

    def test_nothing_heard_misses_everything_without_crashing(self):
        c = compare("Ma lähen kooli.", "")
        assert c.matched == 0 and c.ratio == 0.0
        assert c.missed == ["ma", "lähen", "kooli"]

    def test_the_caveat_travels_with_the_number(self):
        """A miss can mean a mispronunciation or a recogniser weak on accented
        Estonian. The ratio must never appear without saying so."""
        got = compare("Tere", "tere").to_dict()
        assert got["caveat"]
        assert "hääldushinnet" in got["caveat"]

    def test_word_level_detail_is_the_output_not_a_percentage(self):
        got = compare("Ma lähen kooli", "ma lähen kohli").to_dict()
        assert len(got["words"]) == 3
        assert got["missed"] == ["kooli"]


class TestMaterial:
    def test_words_come_from_the_frequent_end(self):
        from eesti.wordlist import connect

        items = words_to_say(connect(), count=5, seed=1)
        assert len(items) == 5
        assert all(isinstance(i, ReadAloud) and i.kind == "sona" for i in items)
        assert all(len(i.text) > 2 for i in items)

    def test_sentences_are_real_and_sayable_in_a_breath(self, tmp_path):
        from eesti.sources import Item, add_items, connect, register

        content = connect(tmp_path / "c.db")
        register(content)
        add_items(content, [Item(
            "selges-keeles", "lugemine",
            body="Ma elan Tallinnas ja käin iga päev tööl. "
                 "Eile ostsin poest uue raamatu.",
        )])
        items = sentences_to_say(content, count=5, seed=1)
        assert items
        for item in items:
            assert item.kind == "lause"
            assert 4 <= len(item.text.split()) <= 12

    def test_generation_is_reproducible(self):
        from eesti.wordlist import connect

        a = [i.text for i in words_to_say(connect(), count=6, seed=3)]
        b = [i.text for i in words_to_say(connect(), count=6, seed=3)]
        assert a == b


class TestApi:
    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    def test_read_aloud_serves_both_kinds(self, client):
        for kind in ("sona", "lause"):
            data = client.get(f"/api/speaking/readaloud?kind={kind}&n=3").json()
            assert data["kind"] == kind and data["items"]

    def test_an_unknown_kind_is_rejected(self, client):
        assert client.get("/api/speaking/readaloud?kind=laul").status_code == 400

    def test_feedback_treats_a_transcript_as_text(self, client):
        """Once transcribed, a spoken answer is text — and this project already
        knows what to do with Estonian text."""
        data = client.post("/api/speaking/feedback", json={
            "transcript": "Ma lugesin eile raamatut läbi.", "seconds": 6,
        }).json()
        assert data["words"] == 5
        assert data["pace_wpm"] == 50.0
        assert "corrections" in data and data["engine"]

    def test_pace_is_omitted_when_no_duration_is_given(self, client):
        data = client.post("/api/speaking/feedback",
                           json={"transcript": "Tere hommikust."}).json()
        assert data["pace_wpm"] is None

    def test_feedback_says_it_is_not_about_pronunciation(self, client):
        data = client.post("/api/speaking/feedback",
                           json={"transcript": "Tere."}).json()
        assert "häälduse" in data["note"]
