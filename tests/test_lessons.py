"""The Reegel page: every topic has one, its forms come from Vabamorf, and every
written point names where it came from."""

from __future__ import annotations

import pytest

from eesti.curriculum import TOPICS
from eesti.lessons import NOUN_TABLES, VERB_TABLES, lesson, table
from eesti.lessontext import LESSONS

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")


class TestEveryTopic:
    @pytest.mark.parametrize("topic", [t.id for t in TOPICS])
    def test_has_something_to_read(self, topic):
        L = lesson(topic)
        assert L["rule"] or L["points_ru"], f"{topic} has neither a summary nor points"

    def test_written_points_cite_a_source(self):
        for topic, text in LESSONS.items():
            assert text.sources, topic
            assert all(s.url.startswith("https://") for s in text.sources), topic

    def test_written_points_are_for_real_topics(self):
        assert set(LESSONS) <= {t.id for t in TOPICS}

    def test_tables_are_for_real_topics(self):
        assert set(NOUN_TABLES) | set(VERB_TABLES) <= {t.id for t in TOPICS}


class TestTables:
    def test_a_case_table_comes_from_the_synthesiser(self):
        rows = {r[0]: r[3:] for r in table("kohakaanded")["rows"]}
        assert rows["seesütlev"][0] == "raamatus"
        assert rows["sisseütlev"][2] == "tuppa ~ toasse"

    def test_a_case_row_names_its_question_and_ending(self):
        rows = {r[0]: r[1:3] for r in table("kohakaanded")["rows"]}
        assert rows["seesütlev"] == ["kelles? milles? kus?", "s"]

    def test_a_short_illative_spelled_like_the_partitive_is_left_out(self):
        rows = {r[0]: r[3:] for r in table("kohakaanded")["rows"]}
        assert rows["sisseütlev"][3] == "sõbrasse"

    def test_a_compound_tense_is_built_from_its_parts(self):
        assert table("taisminevik")["rows"][2][2] == "on laulnud"

    def test_negation(self):
        assert table("eitus")["rows"][0][3] == "ei tule"

    def test_a_numeral_gets_no_forms_of_a_homonymous_noun(self):
        """`viisi` is the noun `viis` (tune), not the numeral five."""
        rows = {r[0]: r[1:] for r in table("arvsonad")["rows"]}
        assert rows["viis"] == ["viie", "viit"]
        assert rows["kaks"] == ["kahe", "kaht ~ kahte"]

    def test_every_table_names_its_source(self):
        assert table("kohakaanded")["source"] == "Формы построены Vabamorf."
        assert "закрытый список" in table("jargarvud")["source"]
        assert "teatmik" in table("asesonad")["source"]


class TestTheRoute:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    def test_known_topic(self, client):
        r = client.get("/api/lesson/kaassonad")
        assert r.status_code == 200 and r.json()["points_ru"]

    def test_unknown_topic(self, client):
        assert client.get("/api/lesson/nope").status_code == 404


class TestRussianForEveryTopic:
    def test_every_topic_has_points_and_a_tip(self):
        from eesti.lessontext import TIPS

        for t in TOPICS:
            assert t.id in LESSONS and LESSONS[t.id].points_ru, t.id
            assert t.id in TIPS and TIPS[t.id].wrong != TIPS[t.id].right, t.id

    def test_the_tip_reaches_the_page(self):
        assert lesson("obj-case")["tip"]["right"] == "Ma ostsin raamatu."
