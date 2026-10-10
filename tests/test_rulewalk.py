"""The rule walk on the Reegel page (ADR-0009 step 2): notice, ask, explain,
contrast, and the form switch.

What a learner must be able to trust: every Estonian form on the walk is
Vabamorf's and named by code; a condition Vabamorf has no form for is not
offered; the ask step is graded by the server against the key it issued; the
one paragraph a model wrote is labelled, short and cited, and is refused when
it names an Estonian word that is neither code's nor the cited source's.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from eesti import rulewalk, tutor
from eesti.curriculum import TOPICS
from eesti.lessons import lesson
from eesti.lessontext import LESSONS, TIPS, WALKS, Sentence
from eesti.morph import _readings, unique_form

WALKED = sorted(WALKS)


def built_sentences(w: dict):
    """Every sentence the walk shows with a form in it."""
    yield from w["notice"]["examples"]
    yield from w["contrast"]
    yield from w["switch"]["conditions"]


class TestEveryWalk:
    @pytest.mark.parametrize("topic", WALKED)
    def test_every_step_and_the_switch_resolve(self, topic):
        w, spec = rulewalk.walk(topic, seed=1), WALKS[topic]
        assert 2 <= len(w["notice"]["examples"]) <= 4
        assert len(w["notice"]["examples"]) == len(spec.notice)
        assert len(w["ask"]["items"]) == len(spec.ask)
        assert w["explain"] and w["explain"]["text"]
        assert len(w["contrast"]) == len(spec.contrast)
        assert [c["id"] for c in w["switch"]["conditions"]] == [c.id for c in spec.switch]

    @pytest.mark.parametrize("topic", WALKED)
    def test_every_form_is_vabamorfs_and_reads_back(self, topic):
        for s in built_sentences(rulewalk.walk(topic, seed=1)):
            assert unique_form(s["lemma"], s["tag"]) == s["form"], s
            assert (s["lemma"], s["tag"]) in _readings(s["form"]), s
            if s.get("wrong"):
                assert s["wrong"] != s["form"]
                assert unique_form(s["lemma"], s["wrong_tag"]) == s["wrong"], s

    def test_the_object_form_follows_each_condition(self):
        """What the learner watches change on #rule/obj-case: the generator's own
        frames (EKK SÜ 38–40), one noun, its forms from Vabamorf."""
        shown = {c["id"]: (c["form"], c["name"])
                 for c in rulewalk.walk("obj-case", seed=1)["switch"]["conditions"]}
        assert shown == {
            "completed": ("leiva", "omastav"),
            "ongoing": ("leiba", "osastav"),
            "negation": ("leiba", "osastav"),
            "plural": ("leivad", "mitmuse nimetav"),
            "imperative": ("leib", "nimetav"),
            "impersonal": ("leib", "nimetav"),
        }

    def test_the_subject_form_follows_negation_and_the_verb(self):
        shown = {c["id"]: (c["form"], c["name"])
                 for c in rulewalk.walk("osaalus", seed=1)["switch"]["conditions"]}
        assert shown == {
            "jaatus": ("raamat", "nimetav"),
            "eitus": ("raamatut", "osastav"),
            "mitmus": ("õpilased", "mitmuse nimetav"),
            "ainsus": ("õpilasi", "mitmuse osastav"),
        }

    def test_a_form_is_named_as_its_drill_names_it(self):
        """One name per form across the app: the walk's name for a frame's form is
        the label the same frame's drill item carries."""
        from eesti.practice import items_for

        for c in rulewalk.walk("obj-case", seed=1)["switch"]["conditions"]:
            spec = next(x for x in WALKS["obj-case"].switch if x.id == c["id"])
            drilled = [d for seed in range(40)
                       for d in items_for("obj-case", count=1, seed=seed,
                                          rules=(spec.sentence.rule,))
                       if d.prompt == spec.sentence.frame]
            if drilled:
                assert drilled[0].label == c["name"]

    def test_a_condition_vabamorf_has_no_form_for_is_not_offered(self, monkeypatch):
        real = rulewalk.unique_form
        monkeypatch.setattr(rulewalk, "unique_form",
                            lambda lemma, tag: None if (lemma, tag) == ("leib", "pl n")
                            else real(lemma, tag))
        ids = [c["id"] for c in rulewalk.walk("obj-case", seed=1)["switch"]["conditions"]]
        assert "plural" not in ids
        assert {"completed", "negation", "imperative"} <= set(ids)

    def test_a_quote_must_be_in_the_cited_source(self):
        assert rulewalk.sentence("osaalus", WALKS["osaalus"].notice[0])
        invented = Sentence(quote="Laual on raamatud", form="raamatud", tag="pl n")
        assert rulewalk.sentence("osaalus", invented) is None

    def test_a_frame_must_be_the_generators(self):
        invented = Sentence(frame="Ma armastan ____ väga.", noun="leib", rule="completed")
        assert rulewalk.sentence("obj-case", invented) is None

    def test_the_notice_step_names_no_form(self):
        """The learner notices first; the names come after an attempt."""
        for topic in WALKED:
            notice = rulewalk.walk(topic, seed=1)["notice"]
            assert all("name" not in e for e in notice["examples"])
            forms = list(dict.fromkeys(e["form"] for e in notice["examples"]))
            assert len(forms) >= 2
            for form in forms:
                assert f"*{form}*" in notice["question_ru"]

    def test_a_wrong_form_is_the_frames_own_other_case(self):
        pairs = {c["id"]: (c["wrong"], c["form"]) for c in rulewalk.walk("obj-case", seed=1)["contrast"]}
        assert pairs == {"negation": ("leiva", "leiba"), "imperative": ("leiva", "leib")}

    def test_a_topic_without_a_walk_has_none(self):
        assert rulewalk.walk("asesonad") is None
        assert lesson("asesonad")["walk"] is None


class TestTheAskStep:
    def test_items_are_keyed_by_code_and_the_key_stays_on_the_server(self):
        for topic in WALKED:
            items = rulewalk.walk(topic, seed=3)["ask"]["items"]
            assert [i["rule"] for i in items] == [r[0] for r in WALKS[topic].ask]
            for it in items:
                assert "answer" not in it and "distractor" not in it
                assert len(set(it["choices"])) == 2 and it["token"]
                assert it["prompt"].count("____") == 1
                assert it["form_after"]

    def test_no_sentence_is_asked_twice(self):
        for seed in range(6):
            prompts = [i["prompt"] for i in rulewalk.walk("osaalus", seed=seed)["ask"]["items"]]
            assert len(prompts) == len(set(prompts))

    def test_without_a_generator_the_walk_still_teaches(self, monkeypatch):
        import eesti.practice

        def broken(*a, **k):
            raise ValueError("no word list built")

        monkeypatch.setattr(eesti.practice, "items_for", broken)
        w = rulewalk.walk("obj-case", seed=1)
        assert w["ask"]["items"] == []
        assert w["explain"] and w["switch"]["conditions"]

    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    @pytest.mark.parametrize("topic", WALKED)
    def test_the_server_grades_a_choice_and_records_nothing(self, client, topic):
        from eesti import evidence

        page = client.get(f"/api/lesson/{topic}").json()
        verdicts = []
        for item in page["walk"]["ask"]["items"]:
            for given in item["choices"]:
                said = client.post("/api/practice/answer", json={
                    "topic": item["topic"], "prompt": item["prompt"], "answer": "",
                    "given": given, "token": item["token"], "record": False}).json()
                verdicts.append(said["correct"])
                assert said["answer"] in item["choices"]
        assert verdicts.count(True) == len(page["walk"]["ask"]["items"])
        with evidence.connect() as log:
            attempts = log.execute(
                "SELECT COUNT(*) FROM events WHERE type = 'attempt'").fetchone()[0]
        assert attempts == 0

    def test_a_tampered_key_is_refused(self, client):
        item = client.get("/api/lesson/obj-case").json()["walk"]["ask"]["items"][0]
        body, mac = item["token"].rsplit(".", 1)
        forged = body + "." + ("0" if mac[0] != "0" else "1") + mac[1:]
        said = client.post("/api/practice/answer", json={
            "topic": item["topic"], "prompt": item["prompt"], "answer": item["choices"][0],
            "given": item["choices"][0], "token": forged, "record": False})
        assert said.status_code == 400


class TestTheExplanation:
    @pytest.mark.parametrize("topic", WALKED)
    def test_short_cited_and_labelled(self, topic):
        e = rulewalk.walk(topic, seed=1)["explain"]
        assert 0 < e["words"] <= rulewalk.MAX_WORDS
        assert e["engine"] == "Claude Opus 5.5"
        assert e["source"]["label"] == f"EKK {e['section']}"
        assert e["source"]["label"] in {s.label for s in LESSONS[topic].sources}
        assert e["id"] == WALKS[topic].explain.id and e["lang"] == "ru"

    @pytest.mark.parametrize("topic", WALKED)
    def test_the_shipped_text_passes_both_gates(self, topic):
        assert rulewalk.problems(topic) == []

    def test_an_estonian_word_from_neither_code_nor_source_is_refused(self, monkeypatch):
        """`raamatuid` is a real form, but nothing on this walk produced it and
        the cited section does not print it."""
        spec = WALKS["obj-case"]
        planted = replace(spec.explain, text_ru=spec.explain.text_ru + " Сравни *raamatuid*.")
        monkeypatch.setitem(WALKS, "obj-case", replace(spec, explain=planted))
        assert rulewalk.walk("obj-case", seed=1)["explain"] is None
        assert any("raamatuid" in p for p in rulewalk.problems("obj-case"))

    def test_the_morphology_gate_is_the_tutors_and_stands_second(self):
        """A non-word that reached the allowed set (a corrupted source, say) still
        fails: `tutor._grounded` asks Vabamorf about every word that is not a
        grammar term."""
        said = "Форма *leibat* здесь."
        assert not tutor._grounded(said, set())
        found = rulewalk.check_prose(said, allowed={"leibat"}, terms=set())
        assert found and "Vabamorf" in found[0]

    def test_a_long_explanation_is_refused(self, monkeypatch):
        spec = WALKS["osaalus"]
        long = replace(spec.explain, text_ru=spec.explain.text_ru + " Это важно." * 10)
        monkeypatch.setitem(WALKS, "osaalus", replace(spec, explain=long))
        assert rulewalk.walk("osaalus", seed=1)["explain"] is None


class TestTheGist:
    def test_it_is_the_sourced_summary_and_never_a_tip(self):
        for t in TOPICS:
            gist = lesson(t.id)["gist_ru"]
            if t.reference is None:
                assert gist is None
                continue
            assert gist and t.reference.summary_ru.startswith(gist), t.id
            assert gist != TIPS[t.id].gist_ru, t.id

    def test_a_bare_first_sentence_takes_the_next_one(self):
        """`Настоящее время.` says nothing a learner can use alone."""
        said = rulewalk.gist("Настоящее время. Личные окончания добавляются к основе.")
        assert said == "Настоящее время. Личные окончания добавляются к основе."

    def test_an_abbreviation_does_not_end_the_sentence(self):
        said = rulewalk.gist("Глагол остаётся в 3-м лице ед. ч. при частичном подлежащем. "
                             "Второе предложение.")
        assert said.endswith("подлежащем.")

    def test_a_question_mark_inside_a_sentence_does_not_end_it(self):
        said = rulewalk.gist("**käima** — где? (*käisin kinos* — был и вернулся). "
                             "**minema** — куда?")
        assert said == "**käima** — где? (*käisin kinos* — был и вернулся)."


class TestTheRoute:
    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    def test_the_lesson_carries_the_walk_and_the_gist(self, client):
        page = client.get("/api/lesson/osaalus").json()
        assert page["gist_ru"].startswith("В предложении о наличии")
        assert [c["id"] for c in page["walk"]["switch"]["conditions"]] == [
            "jaatus", "eitus", "mitmus", "ainsus"]
