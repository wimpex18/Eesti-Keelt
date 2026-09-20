"""Reading questions: written by a model, keyed by the text (ADR-0004).

The learner-visible failures these prevent: a question whose answer is not in
the text at all; a question that hands over its own answer; and an answer
graded by anything other than the text's own words.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import comprehension, config, evidence  # noqa: E402
from eesti.sources import Item, add_items, connect, register  # noqa: E402

TEXT = (
    "Eelmisel nädalal avati Tartus uus raamatukogu. Maja ehitati kaks aastat "
    "ja see maksis kaksteist miljonit eurot. Raamatukogus on üle saja tuhande "
    "raamatu ning kolm lugemissaali. Direktor ütles, et maja on avatud igal "
    "päeval kella kümnest kaheksani. Esimesel nädalal käis seal viis tuhat "
    "inimest ja kõik said endale lugejakaardi."
)


@pytest.fixture
def text_item(tmp_path, monkeypatch):
    db = str(tmp_path / "content.db")
    conn = connect(db)
    register(conn)
    item = Item(source_id="selges-keeles", skill="lugemine", level="A2",
                title="Uus raamatukogu", body=TEXT, meta={})
    add_items(conn, [item])
    conn.close()
    monkeypatch.setattr(config, "CONTENT_DB", db)
    return item.id


class TestWhatCountsAsAQuestion:
    @pytest.mark.parametrize("question,answer", [
        # The answer is not in the text: the model made it up.
        ("Kus asub raamatukogu?", "Tallinnas"),
        # The question carries its own answer.
        ("Mitu lugemissaali on kolm lugemissaali?", "kolm lugemissaali"),
        # Not a question.
        ("Raamatukogu avati eelmisel nädalal.", "eelmisel nädalal"),
        # A whole retelling is not a key.
        ("Mida tehti?", "Eelmisel nädalal avati Tartus uus raamatukogu ja maja "
                        "ehitati kaks aastat"),
        # A span the text uses twice cannot key anything.
        ("Millal?", "nädalal"),
    ])
    def test_a_proposal_that_is_not_keyed_by_the_text_is_refused(self, question, answer):
        assert comprehension.verify(TEXT, question, answer) is None

    def test_a_verified_answer_comes_back_in_the_text_s_own_words(self):
        assert comprehension.verify(TEXT, "Kui kaua maja ehitati?",
                                    "KAKS AASTAT.") == "kaks aastat"


class TestGradingIsCodeAlone:
    def question(self):
        return comprehension.Question(0, "Kui kaua maja ehitati?", "kaks aastat",
                                      "llm:test")

    def test_the_span_in_a_sentence_is_right(self):
        """A learner who answers in a sentence has still found the answer."""
        assert comprehension.grade(self.question(), "Maja ehitati kaks aastat.")["correct"]

    def test_a_different_answer_is_wrong_and_says_what_the_text_said(self):
        verdict = comprehension.grade(self.question(), "kolm aastat")
        assert not verdict["correct"]
        assert "kaks aastat" in verdict["why_ru"]

    def test_burying_the_span_in_a_paragraph_is_not_an_answer(self):
        long = ("ma arvan et see maja mida ehitati seal linnas oli ehitatud "
                "kaks aastat ja veel midagi muud")
        assert not comprehension.grade(self.question(), long)["correct"]


class TestTheAnswerNeverTravelsToThePage:
    def test_the_page_is_sent_questions_without_answers(self, client, text_item):
        with evidence.connect() as log:
            comprehension.save(log, text_item, [
                comprehension.Question(0, "Kui kaua maja ehitati?", "kaks aastat",
                                       "llm:test")])
        body = client.get(f"/api/read/questions/{text_item}").json()
        assert body["questions"] == [
            {"idx": 0, "question": "Kui kaua maja ehitati?", "engine": "llm:test"}]
        assert "kaks aastat" not in str(body)

    def test_answering_is_graded_and_recorded_as_reading_practice(
            self, client, text_item):
        from datetime import datetime, timezone

        from eesti import learner

        with evidence.connect() as log:
            comprehension.save(log, text_item, [
                comprehension.Question(0, "Kui kaua maja ehitati?", "kaks aastat",
                                       "llm:test")])
        r = client.post("/api/read/answer", json={
            "item_id": text_item, "idx": 0, "answer": "kaks aastat"})
        assert r.status_code == 200 and r.json()["correct"]
        with evidence.connect() as log:
            counts = learner.skill_activity(log, now=datetime.now(timezone.utc))
        assert counts["lugemine"] == 1, "reading practice did not reach the skill floor"


class TestMakingThemDoesNotTrustTheModel:
    def test_only_the_proposals_the_text_keys_survive(self, text_item, monkeypatch):
        from eesti import tutor

        monkeypatch.setattr(tutor, "propose_questions", lambda text, want=5: ([
            {"q": "Kui kaua maja ehitati?", "a": "kaks aastat"},
            {"q": "Kus asub maja?", "a": "Tallinnas"},          # invented
            {"q": "Kui kaua ehitati maja?", "a": "kaks aastat"},  # duplicate key
        ], "llm:test"))
        with evidence.connect() as log:
            made = comprehension.make(log, text_item, TEXT)
            assert [(q.question, q.answer) for q in made] == [
                ("Kui kaua maja ehitati?", "kaks aastat")]
        # Recorded as learner state, so the same text asks the same question
        # tomorrow — and on a container that has just been restored.
        with evidence.connect() as fresh:
            assert [q.answer for q in comprehension.stored(fresh, text_item)] == [
                "kaks aastat"]

    def test_a_text_too_short_to_ask_about_asks_nothing(self, text_item, monkeypatch):
        from eesti import tutor

        monkeypatch.setattr(tutor, "propose_questions",
                            lambda *a, **k: pytest.fail("asked a model about a fragment"))
        with evidence.connect() as log:
            assert comprehension.make(log, text_item, "Maja on suur.") == []
