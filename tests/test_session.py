"""The session and the next task (ADR-0009): built by code from the evidence,
graded by code, and only the first attempt counts.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from eesti import session as S


def inputs(**kw) -> S.Inputs:
    base = dict(today="2026-10-11", unit="poes", topic="obj-case", n=1, due=4, yesterday=2,
                words_new=("leib", "piim"), words=("leib", "piim", "sai"), walk=True,
                contrast="eitus", material=("dialoog", "tekst"), stage="A1", writing=True,
                check_size=10)
    return S.Inputs(**{**base, **kw})


def ids(session: S.Session) -> list[str]:
    return [s.id for s in session.steps]


class TestTheSevenSteps:
    def test_a_session_has_the_seven_steps_in_order_under_three_phases(self):
        made = S.compose(inputs())
        assert ids(made) == list(S.STEPS)
        assert [s.phase for s in made.steps] == [
            "opi", "opi", "harjuta", "harjuta", "harjuta", "harjuta", "kontrolli"]

    def test_review_is_capped_at_five_minutes(self):
        made = S.compose(inputs(due=80, yesterday=10))
        review = made.step("kordamine")
        assert review.count == S.REVIEW_CAP and review.minutes <= 5

    def test_nothing_due_leaves_review_out(self):
        assert "kordamine" not in ids(S.compose(inputs(due=0, yesterday=0)))

    def test_yesterdays_misses_join_review_even_when_not_due(self):
        made = S.compose(inputs(due=0, yesterday=3))
        assert made.step("kordamine").count == 3

    def test_a_session_lasts_about_twenty_to_thirty_minutes(self):
        for n in range(1, 6):
            assert 20 <= S.compose(inputs(n=n)).minutes <= 32, n

    def test_the_rule_step_asks_six_to_ten_items(self):
        for n in range(1, 6):
            assert 6 <= S.compose(inputs(n=n)).step("reegel").count <= 10

    def test_the_current_step_is_the_first_not_done(self):
        made = S.compose(inputs(done=("kordamine", "reegel")))
        states = {s.id: s.state for s in made.steps}
        assert states["kordamine"] == states["reegel"] == "done"
        assert states["harjutamine"] == "current"
        assert states["kontroll"] == "todo"
        assert not made.done
        everything = S.compose(inputs(done=tuple(S.STEPS)))
        assert everything.done

    def test_a_unit_without_words_has_no_words_step(self):
        assert "sonad" not in ids(S.compose(inputs(words_new=(), words=())))

    def test_words_already_in_review_are_still_practised(self):
        made = S.compose(inputs(words_new=(), words=("leib",)))
        assert made.step("sonad").count == 1

    def test_the_first_stage_repeats_after_the_recording_with_no_open_task(self):
        made = S.compose(inputs(stage="algus", material=()))
        assert made.step("raakimine").detail["tasks"] == 0
        assert made.step("kuulamine").detail["material"] == "heli"

    def test_listening_is_the_units_dialogue_or_dictation(self):
        assert S.compose(inputs()).step("kuulamine").detail["material"] == "dialoog"
        assert S.compose(inputs(material=())).step("kuulamine").detail["material"] \
            == "dikteerimine"

    def test_a_topic_session_is_its_rule_practice_and_check(self):
        made = S.compose(inputs(focus=True))
        assert ids(made) == ["reegel", "harjutamine", "kontroll"]
        assert made.kind == "topic" and made.id.endswith(":obj-case")


class TestTheRotation:
    def test_the_emphasis_moves_across_a_units_five_sessions(self):
        assert [S.compose(inputs(n=n)).emphasis for n in range(1, 7)] == [
            "reeglid", "sonad", "raakimine", "kirjutamine", "kontroll", "reeglid"]

    def test_the_rule_session_is_the_longest_rule_step(self):
        sizes = [S.compose(inputs(n=n)).step("reegel").count for n in range(1, 6)]
        assert sizes[0] == max(sizes)

    def test_words_and_listening_grow_in_the_second_session(self):
        first, second = S.compose(inputs(n=1)), S.compose(inputs(n=2, words_new=tuple("abcdefgh")))
        assert second.step("kuulamine").count > first.step("kuulamine").count
        assert second.step("sonad").count > first.step("sonad").count

    def test_the_speaking_session_has_more_speaking(self):
        assert S.compose(inputs(n=3)).step("raakimine").detail["tasks"] > \
            S.compose(inputs(n=1)).step("raakimine").detail["tasks"]

    def test_the_fourth_session_reads_and_writes_where_the_unit_allows(self):
        made = S.compose(inputs(n=4))
        assert "lugemine" in ids(made) and "kirjutamine" in ids(made)
        assert "kuulamine" not in ids(made) and "raakimine" not in ids(made)
        plain = S.compose(inputs(n=4, material=("dialoog",), writing=False))
        assert "kuulamine" in ids(plain) and "raakimine" in ids(plain)

    def test_the_fifth_session_ends_with_the_unit_check(self):
        check = S.compose(inputs(n=5)).step("kontroll")
        assert check.detail["unit_check"] and check.count == 10
        assert not S.compose(inputs(n=1)).step("kontroll").detail["unit_check"]


class TestTheNextTask:
    def test_todays_session_leads_with_two_alternatives_and_their_reasons(self):
        i = inputs()
        task = S.next_task(i, S.compose(i))
        assert task["primary"]["kind"] == "session"
        assert len(task["alternatives"]) == 2
        assert all(a["why_ru"] for a in task["alternatives"])
        assert len({a["href"] for a in task["alternatives"]} | {task["primary"]["href"]}) == 3

    def test_a_long_queue_puts_review_first(self):
        i = inputs(due=S.LONG_QUEUE + 5)
        task = S.next_task(i, S.compose(i))
        assert task["primary"]["kind"] == "review"
        assert task["alternatives"][0]["kind"] == "session"

    def test_a_failed_unit_check_brings_remediation_first(self):
        i = inputs(check_failed=("osaalus",))
        task = S.next_task(i, S.compose(i))
        assert task["primary"]["kind"] == "remedy"
        assert task["primary"]["href"] == "#session/osaalus"

    def test_after_the_session_the_least_practised_skill_leads(self):
        i = inputs(done=tuple(S.STEPS), skills={"kuulamine": 1, "lugemine": 0,
                                                 "raakimine": 6, "kirjutamine": 2})
        task = S.next_task(i, S.compose(i))
        assert task["primary"]["href"] == "#speak"
        assert "6 дней" in task["primary"]["why_ru"]
        assert "говорение" not in task["primary"]["why_ru"].casefold()

    def test_a_near_sitting_brings_exam_tasks_and_leads_in_the_last_two_weeks(self):
        far = inputs(sitting_days=40, exam_level="B1")
        task = S.next_task(far, S.compose(far))
        assert task["primary"]["kind"] == "session"
        assert any(a["kind"] == "exam" for a in task["alternatives"])
        near = inputs(sitting_days=10, exam_level="B1", done=tuple(S.STEPS))
        assert S.next_task(near, S.compose(near))["primary"]["kind"] == "exam"
        none = inputs(sitting_days=None)
        assert all(a["kind"] != "exam" for a in S.next_task(none, S.compose(none))["alternatives"])


class TestTheHint:
    ITEM = {"answer": "leiba", "lemma": "leib", "why_ru": "После «ei» объект в osastav. "
            "Например *leiba*."}

    @pytest.mark.parametrize("given", ["leib", "leiva", "leibba", "kala", "x"])
    def test_a_hint_never_contains_the_key(self, given):
        pytest.importorskip("estnltk")
        said = S.hint(self.ITEM, given)
        assert said and "leiba" not in said.casefold()

    def test_the_dictionary_form_is_named_as_such(self):
        assert "словарная форма" in S.hint(self.ITEM, "leib")

    def test_another_form_of_the_right_word_says_so_with_the_rule(self):
        pytest.importorskip("estnltk")
        said = S.hint(self.ITEM, "leiva")
        assert said.startswith("Слово верное") and "osastav" in said

    def test_a_slip_points_at_the_ending(self):
        pytest.importorskip("estnltk")
        assert "окончание" in S.hint({"answer": "rahakotti", "lemma": "rahakott"}, "rahakotty")

    def test_a_rule_that_spells_the_key_is_not_offered(self):
        item = {"answer": "Kellele", "lemma": "", "why_ru": "**Kellele** — кому.",
                "hint": "küsisõna"}
        assert "kellele" not in S.hint(item, "Kellelt").casefold()


class TestPlacement:
    def test_it_asks_at_most_twelve_items(self):
        answers, steps = [], 0
        while True:
            placed = S.place(answers)
            if placed["done"]:
                break
            answers += [(placed["unit"], True)] * placed["left"]
            steps += 1
        assert len(answers) <= 12 and steps <= S.PLACE_ROUNDS

    def test_knowing_nothing_starts_at_unit_one(self):
        answers = []
        while not (placed := S.place(answers))["done"]:
            answers += [(placed["unit"], False)] * placed["left"]
        assert placed["start"] == "tere" and placed["skip"] == []

    def test_knowing_more_moves_the_start_later(self):
        answers = []
        while not (placed := S.place(answers))["done"]:
            answers += [(placed["unit"], True)] * placed["left"]
        from eesti.units import by_id

        assert by_id(placed["start"]).n > 10
        assert "tere" in placed["skip"]


# --------------------------------------------------------------------------
# Through the API
# --------------------------------------------------------------------------

def _events(type_: str) -> list[dict]:
    from eesti import evidence

    with evidence.connect() as log:
        return [e.payload for e in evidence.since(log, (type_,), "")]


def _attempts() -> list[dict]:
    return _events("attempt")


def _no_keys(item: dict) -> None:
    assert not {"answer", "distractor", "why_ru", "solution"} & set(item), item


class TestTodayThroughTheApi:
    def test_a_new_learner_gets_a_session_and_a_next_task(self, client):
        body = client.get("/api/session").json()
        assert body["session"]["steps"]
        assert body["next"]["primary"]["kind"] == "session"
        assert len(body["next"]["alternatives"]) == 2
        assert body["first"] is True

    def test_starting_twice_records_one_session(self, client):
        client.post("/api/session/start")
        client.post("/api/session/start")
        assert len(_events(S.STARTED)) == 1


class TestTheTopicSession:
    TOPIC = "tingiv"

    def test_its_steps_hold_no_key(self, client):
        made = client.get(f"/api/session/topic/{self.TOPIC}").json()["session"]
        assert [s["id"] for s in made["steps"]] == ["reegel", "harjutamine", "kontroll"]
        for step in ("reegel", "harjutamine", "kontroll"):
            body = client.get(f"/api/session/step/{step}", params={"topic": self.TOPIC}).json()
            assert body["items"], step
            for item in body["items"]:
                _no_keys(item)
                assert item["token"]

    def test_the_rule_step_offers_two_forms_and_names_neither(self, client):
        body = client.get("/api/session/step/reegel", params={"topic": self.TOPIC}).json()
        chosen = [it for it in body["items"] if it.get("choices")]
        assert chosen
        for item in chosen:
            assert len(item["choices"]) == 2 and not item.get("label")
        assert body["after"]["sources"] or body["after"]["rule"]

    def test_a_reload_shows_the_same_items(self, client):
        one = client.get("/api/session/step/harjutamine", params={"topic": self.TOPIC}).json()
        two = client.get("/api/session/step/harjutamine", params={"topic": self.TOPIC}).json()
        assert [i["prompt"] for i in one["items"]] == [i["prompt"] for i in two["items"]]


class TestOnlyTheFirstAttemptCounts:
    TOPIC = "tingiv"

    def _typed(self, client, step="harjutamine"):
        body = client.get(f"/api/session/step/{step}", params={"topic": self.TOPIC}).json()
        return next(it for it in body["items"] if it["typed"])

    def _key(self, item) -> str:
        from eesti.itemref import verify

        return verify(item["token"])["item"]["answer"].split(" ~ ")[0]

    def test_a_first_miss_gets_a_hint_and_no_key(self, client):
        item = self._typed(client)
        got = client.post("/api/session/answer", json={
            "kind": "item", "step": "harjutamine", "token": item["token"],
            "given": "vale", "event_id": "e-1"}).json()
        assert got["retry"] and got["hint_ru"] and not got["correct"]
        assert "answer" not in got and self._key(item) not in got["hint_ru"]
        assert len(_attempts()) == 1 and _attempts()[0]["correct"] is False

    def test_the_retry_is_graded_and_never_recorded(self, client):
        item = self._typed(client)
        client.post("/api/session/answer", json={
            "kind": "item", "step": "harjutamine", "token": item["token"],
            "given": "vale", "event_id": "e-2"})
        got = client.post("/api/session/answer", json={
            "kind": "item", "step": "harjutamine", "token": item["token"],
            "given": self._key(item), "attempt": 2}).json()
        assert got["correct"] and not got["retry"] and got["answer"]
        attempts = _attempts()
        assert len(attempts) == 1 and attempts[0]["correct"] is False

    def test_the_exit_check_reveals_at_once(self, client):
        item = self._typed(client, "kontroll")
        got = client.post("/api/session/answer", json={
            "kind": "item", "step": "kontroll", "token": item["token"],
            "given": "vale", "event_id": "e-3"}).json()
        assert not got["retry"] and got["answer"] and got["solution"]

    def test_a_choice_has_no_retry(self, client):
        item = self._typed(client)
        got = client.post("/api/session/answer", json={
            "kind": "item", "step": "harjutamine", "token": item["token"],
            "given": "vale", "choice": True, "event_id": "e-4"}).json()
        assert not got["retry"]

    def test_a_right_first_answer_is_recorded_right(self, client):
        item = self._typed(client)
        got = client.post("/api/session/answer", json={
            "kind": "item", "step": "harjutamine", "token": item["token"],
            "given": self._key(item), "event_id": "e-5"}).json()
        assert got["correct"] and _attempts()[0]["correct"] is True


class TestWords:
    WORD = {"lemma": "leib", "answer": "leiba", "prompt": "Ma ei söö ____.",
            "lemma_ru": "хлеб", "sentence_ru": "Я не ем хлеба.", "source_id": "eki-evs"}

    def _cards(self) -> list:
        from eesti import config, review

        rev = review.connect(config.learner_db("REVIEW_DB"))
        return [r[0] for r in rev.execute("SELECT id FROM review_items WHERE kind='vocab'")]

    def test_a_first_correct_recall_puts_the_word_in_review(self, client):
        token = S.sign_word(self.WORD)
        got = client.post("/api/session/answer", json={
            "kind": "word", "token": token, "given": "leiba"}).json()
        assert got["correct"] and got["queued"]
        assert self._cards() == ["vocab:leib:meaning"]

    def test_a_retry_does_not(self, client):
        token = S.sign_word(self.WORD)
        first = client.post("/api/session/answer", json={
            "kind": "word", "token": token, "given": "leib"}).json()
        assert not first["correct"] and "answer" not in first and first["hint_ru"]
        second = client.post("/api/session/answer", json={
            "kind": "word", "token": token, "given": "leiba", "attempt": 2}).json()
        assert second["correct"] and not second["queued"]
        assert self._cards() == []

    def test_a_word_token_is_never_graded_as_a_drill(self, client):
        token = S.sign_word(self.WORD)
        got = client.post("/api/practice/answer", json={
            "topic": "obj-case", "prompt": "x", "answer": "y", "given": "leiba",
            "token": token})
        assert got.status_code == 400
        assert _attempts() == []


class TestFinishingASession:
    def test_the_last_step_finishes_the_session(self, client, monkeypatch):
        made = client.post("/api/session/start").json()
        for step in [s["id"] for s in made["steps"]]:
            body = client.post(f"/api/session/step/{step}/done", json={
                "session": made["id"], "asked": 3, "correct": 2}).json()
        assert body["session"]["done"]
        assert len(_events(S.DONE)) == 1
        assert body["next"]["primary"]["kind"] != "session"
        assert client.get("/api/session").json()["first"] is False

    def test_a_finished_step_stays_finished_on_reload(self, client):
        made = client.post("/api/session/start").json()
        first = made["steps"][0]["id"]
        client.post(f"/api/session/step/{first}/done", json={"session": made["id"]})
        steps = client.get("/api/session").json()["session"]["steps"]
        assert steps[0]["state"] == "done" and steps[1]["state"] == "current"


class TestTheGoal:
    def test_a_goal_and_sessions_a_week_are_kept(self, client):
        assert client.post("/api/session/goal", json={"goal": "b1", "per_week": 4}).status_code == 200
        assert client.get("/api/session/goal").json()["goal"] == {"goal": "b1", "per_week": 4}

    def test_an_unknown_goal_is_refused(self, client):
        assert client.post("/api/session/goal", json={"goal": "c2"}).status_code == 400


class TestThePlacementCheck:
    def test_it_places_by_unit_and_masters_nothing(self, client):
        from eesti.itemref import verify

        answers, rounds = [], 0
        while True:
            body = client.post("/api/session/placement", json={"answers": answers}).json()
            if body["done"]:
                break
            rounds += 1
            assert 1 <= len(body["items"]) <= S.PLACE_ITEMS
            for item in body["items"]:
                _no_keys(item)
                key = verify(item["token"])["item"]["answer"].split(" ~ ")[0]
                answers.append({"unit": body["unit"], "token": item["token"], "given": key})
        assert len(answers) <= 12 and rounds <= S.PLACE_ROUNDS
        applied = client.post("/api/session/placement",
                              json={"answers": answers, "apply": True}).json()
        assert applied["start"] == body["start"] and applied["review"]
        from eesti import config, progress

        conn = progress.connect(config.learner_db("PROGRESS_DB"))
        assert not progress.mastered(conn)
        from eesti.course import skipped

        assert skipped(conn)
        assert _attempts() == []


# --------------------------------------------------------------------------
# Haiku in the app: labelled, grounded, never deciding
# --------------------------------------------------------------------------

@pytest.fixture
def model(monkeypatch):
    """Make every LLM lane answer with the JSON the test gives."""
    def answer(reply: dict):
        from eesti.providers import llm

        monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(reply, ensure_ascii=False))
        for lane in llm.PROVIDERS.values():
            monkeypatch.setattr(type(lane), "available", property(lambda self: True),
                                raising=False)
    return answer


class TestTheModelsFeedback:
    TEXT = "Tere! Ma ei saa homme tulla, sest ma olen haige. Lähme kinno laupäeval."

    def test_comments_quote_the_text_and_carry_their_engine(self, client, model):
        pytest.importorskip("estnltk")
        model({"points": [
            {"criterion": "laused", "quote": "Ma ei saa homme tulla",
             "comment": "Короткие предложения на бытовую тему."},
            {"criterion": "sidesonad", "quote": "Me läksime koju",
             "comment": "Цитата не из текста."},
            {"criterion": "endast", "quote": "", "comment": "Это 7/10 баллов."},
        ]})
        got = client.post("/api/session/feedback", json={
            "kind": "kirjutamine", "text": self.TEXT, "level": "A2"}).json()
        assert [p["criterion"] for p in got["points"]] == ["laused"]
        assert got["dropped"] == 2 and got["engine"].startswith("llm:")
        assert got["graded"] is False and "lk 135" in got["source"]["label"]

    def test_an_invented_form_in_a_comment_is_dropped(self, client, model):
        pytest.importorskip("estnltk")
        model({"points": [{"criterion": "laused", "quote": "",
                           "comment": "Лучше *haigendama*: короче."}]})
        got = client.post("/api/session/feedback", json={
            "kind": "kirjutamine", "text": self.TEXT, "level": "A2"}).json()
        assert got["points"] == [] and got["degraded"]

    def test_no_engine_says_so(self, client):
        got = client.post("/api/session/feedback", json={
            "kind": "raakimine", "text": self.TEXT, "level": "B1"}).json()
        assert got["degraded"] and got["engine"] == "none" and got["note"]


class TestTheRuleQuestion:
    def test_an_answer_from_the_sources_is_kept_and_labelled(self, client, model):
        pytest.importorskip("estnltk")
        model({"explanation_ru": "После отрицания дополнение стоит в **osastav**."})
        got = client.post("/api/rule/obj-case/ask", json={"question": "Почему после ei?"}).json()
        assert got["text"].startswith("После") and got["source"] == "model"
        assert got["engine"].startswith("llm:") and got["lang"] == "ru"

    def test_an_invented_form_is_refused(self, client, model):
        pytest.importorskip("estnltk")
        model({"explanation_ru": "Говорят *raamatuid* и *leibqx*."})
        got = client.post("/api/rule/obj-case/ask", json={"question": "Как во мн. ч.?"}).json()
        assert got["degraded"] and not got["text"]

    def test_an_empty_question_is_refused(self, client):
        assert client.post("/api/rule/obj-case/ask", json={"question": "  "}).status_code == 400


class TestMiksInTheExplanationLanguage:
    def test_english_marks_estonian_words_and_checks_them(self, model):
        pytest.importorskip("estnltk")
        from eesti import tutor

        allowed = {"leiba", "leib"}
        assert tutor._grounded_in("After *ei* the object is *leiba*.", allowed, "en")
        assert not tutor._grounded_in("After *ei* the object is *leibqx*.", allowed, "en")
        assert not tutor._grounded_in("After ei the object is leiba.", allowed, "en")

    def test_an_unknown_language_is_refused(self, client):
        assert client.post("/api/session/miks", json={"event_id": "x", "lang": "de"}).status_code in (400, 404)
