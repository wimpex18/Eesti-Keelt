"""HARNO's reading and listening task types, generated and keyed by code (S6).

The task types follow HARNO's paper: its instruction, item shape, answer format
and question numbers. What is keyed is code's: a value the frame was filled
with, a word that was heard, a form a rule decides, a phrase's place in a text.
"""

from __future__ import annotations

import random
import sqlite3

import pytest

from eesti import config, harnotasks, mock
from eesti.item import BLANK


def _words():
    from eesti.wordlist import connect

    return connect(config.DB_PATH)


# --------------------------------------------------------------------------
# The task types
# --------------------------------------------------------------------------

class TestTheTypes:
    def test_b1_comes_with_its_four_types_and_a2_with_its_three(self):
        assert sorted(harnotasks.TYPES) == [
            "A2-ku1", "A2-ku3", "A2-lu5", "B1-ku1", "B1-ku3", "B1-lu3", "B1-lu4"]

    @pytest.mark.parametrize("code, first, last", [
        ("B1-ku1", 1, 7), ("B1-ku3", 14, 21), ("B1-lu3", 16, 25), ("B1-lu4", 26, 33),
        ("A2-ku1", 1, 7), ("A2-ku3", 14, 19), ("A2-lu5", 23, 30)])
    def test_questions_carry_harno_s_own_numbers(self, code, first, last):
        task = harnotasks.TYPES[code]
        assert (task.first, task.last) == (first, last)

    def test_a_task_s_time_is_its_share_of_the_part(self):
        # B1 reading: 50 minutes for 33 questions; task 3 has 10 of them.
        assert harnotasks.TYPES["B1-lu3"].minutes() == 16
        assert harnotasks.TYPES["B1-ku1"].minutes() == 7

    def test_letters_skip_g_and_j_as_the_paper_does(self):
        assert "G" not in harnotasks.LETTERS and "J" not in harnotasks.LETTERS
        assert harnotasks.LETTERS[:3] == "ABC"

    def test_every_instruction_is_estonian_vabamorf_knows(self):
        from eesti.morph import _readings, tokenize

        for task in harnotasks.TYPES.values():
            for word in tokenize(task.instruction_et + " " + task.et):
                if word.isalpha() and len(word) > 1:
                    assert _readings(word), (task.code, word)


# --------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------

class TestGrading:
    def test_a_choice_is_right_by_letter_or_by_the_option_itself(self):
        issued = {"answer": "7.30", "distractor": "8.30 | 7.30 | 7.00", "lemma": ""}
        assert harnotasks.check(issued, "B") and harnotasks.check(issued, "b")
        assert harnotasks.check(issued, "7.30")
        assert not harnotasks.check(issued, "A") and not harnotasks.check(issued, "")

    def test_a_short_answer_is_any_form_of_the_heard_word(self):
        issued = {"answer": "ujumas", "distractor": "", "lemma": "ujuma"}
        assert harnotasks.check(issued, "ujumas")
        assert harnotasks.check(issued, "ujuma")
        assert harnotasks.check(issued, "käib ujumas")
        assert not harnotasks.check(issued, "jooksmas")
        assert not harnotasks.check(issued, "ujumsa")       # not a word Vabamorf knows

    def test_a_heard_number_may_be_written_in_digits(self):
        sentence = "Vanaema kolis siia kaheksateist aastat tagasi."
        lo, hi, key, accepted = harnotasks._heard_gap(sentence, None, ("A1", "A2", "B1"))
        assert key == "kaheksateist" and "18" in accepted
        issued = {"answer": key, "distractor": "", "lemma": " ~ ".join(sorted(accepted))}
        assert harnotasks.check(issued, "18")
        assert not harnotasks.check(issued, "80")


# --------------------------------------------------------------------------
# Listening 1: two voices say a value
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def blocks():
    return [harnotasks.listening_numbers(harnotasks.TYPES["B1-ku1"], seed)
            for seed in range(12)]


class TestListeningNumbers:
    def test_seven_questions_numbered_from_one(self, blocks):
        for block in blocks:
            assert [q.no for q in block.questions] == list(range(1, 8))

    def test_each_question_has_three_options_and_one_key(self, blocks):
        for q in (q for b in blocks for q in b.questions):
            assert len(set(q.options)) == 3 and q.options.count(q.answer) == 1

    def test_the_exchange_is_two_different_voices(self, blocks):
        from eesti.providers.tts import VOICES

        for q in (q for b in blocks for q in b.questions):
            (a, _), (b, reply) = q.turns
            assert a != b and {a, b} <= set(VOICES)
            assert q.hint in reply                       # the value is said

    def test_every_word_said_or_printed_is_one_vabamorf_knows(self, blocks):
        from eesti.morph import _readings, tokenize

        for q in (q for b in blocks for q in b.questions):
            for text in (q.prompt, *(t for _, t in q.turns)):
                for word in tokenize(text):
                    if word.isalpha():
                        assert _readings(word), (word, text)

    def test_every_frame_is_estonian_vabamorf_knows(self):
        from eesti.morph import _readings, tokenize

        frames = (harnotasks.TIME_FRAMES + harnotasks.PRICE_FRAMES
                  + harnotasks.DATE_FRAMES + harnotasks.NUMBER_FRAMES)
        for frame in frames:
            for word in tokenize(" ".join(frame).replace("{}", "")):
                if word.isalpha():
                    assert _readings(word), (word, frame)

    def test_a_half_hour_counts_towards_the_next_hour(self):
        for seed in range(80):
            made = harnotasks._time(random.Random(seed))
            spoken, key, wrong, _ = made
            if spoken.startswith("pool "):
                # *pool kaheksa* is 7.30; 8.30 is the mistake on offer.
                hour = int(key.split(".")[0])
                assert key.endswith(".30")
                assert f"{hour % 12 + 1}.30" in wrong
                return
        pytest.fail("no half hour in 80 seeds")

    def test_spoken_numbers_are_the_key(self):
        from eesti.numbers import written

        for seed in range(40):
            spoken, key, wrong, _ = harnotasks._number(random.Random(seed), 2, 99)
            assert spoken == written(int(key)).split(" ~ ")[0]
            assert key not in wrong and len(set(wrong)) == 2

    def test_the_same_seed_is_the_same_task(self):
        one = harnotasks.listening_numbers(harnotasks.TYPES["A2-ku1"], 5)
        two = harnotasks.listening_numbers(harnotasks.TYPES["A2-ku1"], 5)
        assert one.questions == two.questions


# --------------------------------------------------------------------------
# Listening 3: a heard text, one word out of each sentence
# --------------------------------------------------------------------------

STORY = harnotasks.Text("Joel", (
    "Joel elab Austraalias.",
    "Tema vanaema kolis sinna kaheksateist aastat tagasi.",
    "Austraalias oli Joelil igav elada.",
    "Vabal ajal käib Joel ujumas.",
    "Talle meeldib vaadata Eesti filme.",
    "Õhtul loeb ta raamatuid.",
), "selges-keeles", ("mari", "albert") * 3)


class TestListeningGaps:
    def test_each_gap_is_a_word_of_the_heard_sentence(self):
        block = harnotasks.listening_gaps(harnotasks.TYPES["A2-ku3"], 1, [STORY], None)
        assert block is not None and len(block.questions) == 6
        heard = [t for _, t in block.audio]
        for q in block.questions:
            assert q.prompt.count(BLANK) == 1
            assert q.prompt.replace(BLANK, q.answer) in heard
            assert q.say == q.prompt.replace(BLANK, q.answer)

    def test_a_dialogue_is_heard_in_its_speakers_voices(self):
        block = harnotasks.listening_gaps(harnotasks.TYPES["A2-ku3"], 1, [STORY], None)
        assert {v for v, _ in block.audio} == {"mari", "albert"}

    def test_too_short_a_text_gives_no_task(self):
        short = harnotasks.Text("", ("Tere.", "Ma elan Tallinnas."), "selges-keeles")
        assert harnotasks.listening_gaps(harnotasks.TYPES["B1-ku3"], 1, [short], None) is None

    def test_a_word_above_the_level_is_never_the_gap(self):
        words = sqlite3.connect(":memory:")
        words.execute("CREATE TABLE words (word TEXT, proficiency TEXT)")
        words.execute("INSERT INTO words VALUES ('raamat', 'A1')")
        found = harnotasks._heard_gap("Õhtul loeb ta raamatuid.", words, ("A1", "A2"))
        assert found and found[2] == "raamatuid"
        assert harnotasks._heard_gap("Ta loeb ajakirju.", words, ("A1", "A2")) is None


# --------------------------------------------------------------------------
# Reading 3: three forms of one word, a rule leaves one
# --------------------------------------------------------------------------

READING = harnotasks.Text("Minu pere", (
    "Ma elan väikeses linnas.",
    "Meil on kolm last.",
    "Nad käivad koolis.",
    "Kass magab laua all.",
    "Isa ei osta autot.",
    "Me sõidame bussiga.",
    "Sa elad kaugel.",
), "selges-keeles")

LEVELS = ("A1", "A2", "B1")


@pytest.fixture(scope="module")
def block():
    return harnotasks.reading_gaps(harnotasks.TYPES["B1-lu3"], 3, [READING], None)


class TestReadingGaps:
    def test_the_text_is_shown_with_numbered_gaps(self, block):
        assert block is not None and len(block.questions) >= 4
        for q in block.questions:
            assert f"({q.no}) ____" in block.text
        assert [q.no for q in block.questions] == list(
            range(16, 16 + len(block.questions)))

    def test_three_options_one_key_and_the_key_is_the_text_s_word(self, block):
        for q in block.questions:
            assert len(set(q.options)) == 3 and q.options.count(q.answer) == 1
            assert q.prompt.replace(BLANK, q.answer) in READING.sentences

    def test_every_rule_names_what_decides_it(self, block):
        from eesti.curriculum import by_id

        rules = {q.rule.split("/")[1] for q in block.questions}
        assert rules <= {"agreement", "negation", "numeral", "postposition"}
        for q in block.questions:
            assert q.hint and q.hint in q.prompt     # the evidence is in the sentence
            assert by_id(q.topic)                    # the miss names a topic to practise
            assert q.why_ru

    def test_a_distractor_is_never_a_reading_of_the_key(self):
        from eesti.morph import _readings

        rng = random.Random(1)
        for sentence in READING.sentences:
            gap = harnotasks.find_gap(sentence, None, LEVELS, rng)
            if gap is None:
                continue
            for wrong in gap.options:
                assert (gap.lemma, gap.form) not in _readings(wrong), (sentence, wrong)

    def test_agreement_distractors_are_what_the_agreement_check_refuses(self):
        from eesti.morph import agreement_errors, analyze

        sentence = "Ma elan väikeses linnas."
        gap = harnotasks._agreement_gap(sentence, analyze(sentence), random.Random(0))
        assert gap.key == "elan" and gap.trigger == "Ma"
        for wrong in gap.options:
            assert agreement_errors(sentence.replace("elan", wrong))

    @pytest.mark.parametrize("sentence, key, trigger, topic", [
        ("Meil on kolm last.", "last", "kolm", "arvsonad"),
        ("Kass magab laua all.", "laua", "all", "kaassonad"),
        ("Isa ei osta autot.", "autot", "ei", "obj-case"),
    ])
    def test_each_rule_finds_its_gap(self, sentence, key, trigger, topic):
        from eesti.morph import analyze

        tokens, rng = analyze(sentence), random.Random(0)
        gap = (harnotasks._numeral_gap(sentence, tokens, rng)
               or harnotasks._postposition_gap(sentence, tokens, rng)
               or harnotasks._negation_gap(sentence, tokens, rng, None))
        assert (gap.key, gap.trigger, gap.topic) == (key, trigger, topic)

    @pytest.mark.parametrize("sentence, key, trigger", [
        ("Eile käisin ma poes.", "käisin", "ma"),          # the verb before its subject
        ("Kohtunik selgitas otsust pikalt.", "selgitas", "Kohtunik"),
        ("Uus seadus jõustub järgmisel aastal.", "jõustub", "seadus"),
    ])
    def test_agreement_with_a_subject_on_either_side(self, sentence, key, trigger):
        from eesti.morph import _readings, analyze

        gap = harnotasks._agreement_gap(sentence, analyze(sentence), random.Random(0))
        assert (gap.key, gap.trigger) == (key, trigger)
        if trigger != "ma":
            # A noun subject is offered only 1st and 2nd person forms.
            persons = {"n", "me", "te", "sin", "sime", "site", "ksin", "ksime", "ksite"}
            for wrong in gap.options:
                assert {t for _, t in _readings(wrong)} <= persons, wrong

    @pytest.mark.parametrize("sentence", [
        # A plural nominative can be the object: *Väravad lõime* is Estonian.
        "Väravad lõid Tabidze ja Qazaišvili.",
        # A time word is no subject: *Iga päev käin tööl* is Estonian.
        "Iga päev käib Mari tööl.",
        # *auto* is also the genitive: *Auto ostsin eile* is Estonian.
        "Auto ostis eile.",
        # Two subjects: the verb agrees with both.
        "Mari ja Jüri läksid koju.",
    ])
    def test_no_noun_gap_where_another_person_could_fit(self, sentence):
        from eesti.morph import analyze

        gap = harnotasks._agreement_gap(sentence, analyze(sentence), random.Random(0))
        assert gap is None, gap

    def test_a_word_of_quantity_takes_the_partitive(self):
        from eesti.morph import _readings, analyze

        sentence = "Mul on palju sõpru."
        gap = harnotasks._quantity_gap(sentence, analyze(sentence), random.Random(0))
        assert (gap.key, gap.trigger, gap.topic) == ("sõpru", "palju", "osastav")
        for wrong in gap.options:     # *palju sõpra* would fit too: never offered
            assert not {t for _, t in _readings(wrong)} & {"sg p", "pl p"}

    def test_agreement_fills_at_most_half_of_a_task(self):
        text = harnotasks.Text("", (
            "Ma elan linnas.", "Sa elad maal.", "Ta töötab koolis.",
            "Me sõidame bussiga.", "Te elate kaugel.", "Nad käivad poes.",
            "Meil on kolm last.", "Kass magab laua all.", "Isa ei osta autot.",
            "Mul on palju sõpru."), "selges-keeles")
        block = harnotasks.reading_gaps(harnotasks.TYPES["B1-lu3"], 1, [text], None)
        agreed = sum(q.rule.endswith("/agreement") for q in block.questions)
        assert agreed <= harnotasks.AGREEMENT_SHARE * 10 and len(block.questions) >= 8

    def test_a_sentence_no_rule_decides_gives_no_gap(self):
        assert harnotasks.find_gap("Bussiga on mugav sõita.", None, LEVELS,
                                   random.Random(0)) is None

    def test_a_text_with_too_few_gaps_gives_no_task(self):
        thin = harnotasks.Text("", READING.sentences[:2], "selges-keeles")
        assert harnotasks.reading_gaps(harnotasks.TYPES["B1-lu3"], 1, [thin], None) is None


# --------------------------------------------------------------------------
# Reading 4: phrases out of a checked text, one more in the bank
# --------------------------------------------------------------------------

def _material(slug: str, paragraphs: list[str]):
    from eesti.material.schema import Material

    return Material(kind="tekst", unit="kodus", slug=slug, title=slug.title(),
                    paragraphs=paragraphs,
                    questions=[{"id": "q1", "question": "Kus Mari elab?",
                                "answer": "Tallinnas"}],
                    authoring={"engine": "hand-written test fixture",
                               "prompt_version": "none"})


TEXT_ONE = [
    "Mari elab Tallinnas, kus on palju parke. Ta töötab poes, mis on kodu lähedal. "
    "Hommikul joob ta kohvi, sest ta ärkab vara. Tööle läheb ta jalgsi, kui ilm on ilus. "
    "Õhtul tuleb ta koju ja teeb süüa.",
    "Nädalavahetusel käib Mari vanematel külas. Ema küpsetab kooki, mida Mari "
    "väga armastab. Isa räägib, et aed vajab tööd. Pärast lõunat jalutavad nad "
    "metsas, aga ilm on külm. Õhtul sõidab Mari bussiga tagasi linna. Ta on väsinud, "
    "kuid rõõmus. Järgmisel nädalal tahab ta jälle minna.",
]
TEXT_TWO = [
    "Jaan õpib ülikoolis, kus ta käib iga päev. Ta elab ühiselamus koos sõbraga. "
    "Nad teevad koos süüa ja koristavad tuba. Õhtuti loeb Jaan raamatuid, mis on "
    "huvitavad. Mõnikord vaatavad nad filmi. Laupäeval mängib Jaan jalgpalli, "
    "kui ilm lubab. Pühapäeval puhkab ta kodus. Ta helistab emale ja räägib "
    "oma nädalast. Ema küsib, kas tal on kõik hästi.",
    "Suvel töötab Jaan kohvikus, sest ta vajab raha. Töö on raske, aga "
    "tore. Kohvikus käib palju turiste, kes räägivad inglise keelt. Jaan "
    "õpib nendega rääkides uusi sõnu.",
]


@pytest.fixture
def checked_texts(tmp_path):
    from eesti.material.store import SCHEMA

    conn = sqlite3.connect(tmp_path / "content.db")
    conn.executescript(SCHEMA)
    for m in (_material("mari", TEXT_ONE), _material("jaan", TEXT_TWO)):
        conn.execute("INSERT INTO material VALUES (?,?,?,?,?,?)",
                     (m.ident(), m.unit, m.slug, m.kind, m.model_dump_json(), "2026-10-09"))
    conn.commit()
    return conn


class TestPhraseBank:
    def test_the_bank_holds_every_removed_phrase_and_one_more(self, checked_texts):
        texts = harnotasks.material_texts(checked_texts, "B1", ("tekst",))
        block = harnotasks.phrase_bank(harnotasks.TYPES["B1-lu4"], 2, texts)
        assert block is not None and len(block.questions) >= 4
        keys = [q.answer for q in block.questions]
        assert len(block.bank) == len(keys) + 1 and set(keys) < set(block.bank)
        for q in block.questions:
            assert q.options == block.bank
            assert f"({q.no}) ____" in block.text
        body = " ".join(texts[0].sentences + texts[1].sentences)
        for key in keys:
            assert body.count(key) == 1

    def test_the_extra_phrase_is_from_another_text(self, checked_texts):
        texts = harnotasks.material_texts(checked_texts, "B1", ("tekst",))
        block = harnotasks.phrase_bank(harnotasks.TYPES["B1-lu4"], 2, texts)
        extra = (set(block.bank) - {q.answer for q in block.questions}).pop()
        own = next(t for t in texts if t.title == block.title)
        assert extra not in " ".join(own.sentences)

    def test_material_carries_its_label(self, checked_texts):
        from eesti.material import LABEL

        texts = harnotasks.material_texts(checked_texts, "B1", ("tekst",))
        assert all(t.label == LABEL for t in texts)

    def test_one_checked_text_is_not_enough(self, checked_texts):
        texts = harnotasks.material_texts(checked_texts, "B1", ("tekst",))[:1]
        assert harnotasks.phrase_bank(harnotasks.TYPES["B1-lu4"], 2, texts) is None

    def test_a_b1_unit_s_text_is_not_an_a2_task(self, checked_texts):
        m = _material("b1-tekst", TEXT_TWO).model_copy(update={"unit": "restoran"})
        checked_texts.execute("INSERT INTO material VALUES (?,?,?,?,?,?)",
                              (m.ident(), m.unit, m.slug, m.kind, m.model_dump_json(), "x"))
        assert len(harnotasks.material_texts(checked_texts, "A2")) == 2
        assert len(harnotasks.material_texts(checked_texts, "B1")) == 3


# --------------------------------------------------------------------------
# The re-test schedule
# --------------------------------------------------------------------------

class TestRetests:
    def test_a_miss_is_re_tested_the_next_day(self):
        assert mock.schedule([("2026-10-09T10:00:00", False, ["olevik"])]) == (
            "2026-10-10", 0, ["olevik"])

    def test_clean_results_space_the_re_tests_out_to_six_days(self):
        results = [("2026-10-09", False, ["arvud"]), ("2026-10-10", True, [])]
        assert mock.schedule(results)[:2] == ("2026-10-13", 1)
        results.append(("2026-10-13", True, []))
        assert mock.schedule(results)[:2] == ("2026-10-19", 2)
        results.append(("2026-10-19", True, []))
        assert mock.schedule(results) is None

    def test_a_new_miss_starts_again(self):
        results = [("2026-10-09", False, []), ("2026-10-10", True, []),
                   ("2026-10-13", False, ["kellaaeg"])]
        assert mock.schedule(results) == ("2026-10-14", 0, ["kellaaeg"])

    def test_no_miss_no_re_test(self):
        assert mock.schedule([("2026-10-09", True, [])]) is None


# --------------------------------------------------------------------------
# Through the API
# --------------------------------------------------------------------------

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")


def _right(task: dict) -> str:
    """The key, read back from the token the server signed."""
    from eesti.itemref import verify

    issued = verify(task["token"])["item"]
    options = issued["distractor"].split(" | ") if issued["distractor"] else []
    return harnotasks.LETTERS[options.index(issued["answer"])] if options else issued["answer"]


class TestTheApi:
    def test_listening_is_served_in_harno_s_task_types(self, client):
        body = client.get("/api/mock/B1/kuulamine?format=harno&seed=1").json()
        assert body["kind"] == "harno" and body["blocks"][0]["code"] == "B1-ku1"
        assert body["minutes"] >= harnotasks.TYPES["B1-ku1"].minutes()
        first = body["tasks"][0]
        assert first["no"] == 1 and len(first["options"]) == 3 and first["turns"]
        # The page is never handed the key.
        assert "answer" not in first and "why_ru" not in first

    def test_a_part_is_graded_and_reviewed_item_by_item(self, client):
        body = client.get("/api/mock/A2/kuulamine?format=harno&seed=2&task=1").json()
        tasks = body["tasks"]
        answers = [{"token": t["token"], "given": _right(t)} for t in tasks]
        answers[0]["given"] = next(o["letter"] for o in tasks[0]["options"]
                                   if o["letter"] != answers[0]["given"])
        got = client.post("/api/mock/A2/kuulamine", json={"format": "harno", "seconds": 60, "answers": answers, "task": 1}).json()
        assert (got["asked"], got["correct"]) == (len(tasks), len(tasks) - 1)
        miss = got["items"][0]
        assert miss["correct"] is False and miss["letter"] and miss["chosen"] != miss["answer"]
        assert miss["mark"] in miss["evidence"]          # the value, in what was heard
        assert miss["topic"] in got["practise"] and miss["topic_et"]

    def test_a_miss_is_due_for_a_re_test_tomorrow(self, client):
        from datetime import date, timedelta

        body = client.get("/api/mock/B1/kuulamine?format=harno&seed=3&task=1").json()
        answers = [{"token": t["token"], "given": ""} for t in body["tasks"]]
        got = client.post("/api/mock/B1/kuulamine", json={"format": "harno", "seconds": 30, "answers": answers, "task": 1}).json()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        assert got["retests"] == client.get("/api/mock/B1").json()["retests"]
        assert got["retests"][0]["code"] == "B1-ku1"
        assert got["retests"][0]["due"] <= tomorrow

    def test_practising_one_task_is_not_a_sitting_of_the_part(self, client):
        body = client.get("/api/mock/B1/kuulamine?format=harno&seed=4&task=1").json()
        client.post("/api/mock/B1/kuulamine", json={"format": "harno", "seconds": 5, "task": 1, "answers": [
            {"token": t["token"], "given": "A"} for t in body["tasks"]]})
        assert mock.counts(_progress(), "B1").get("kuulamine", 0) == 0
        whole = client.get("/api/mock/B1/kuulamine?format=harno&seed=4").json()
        client.post("/api/mock/B1/kuulamine", json={"format": "harno", "seconds": 5, "answers": [
            {"token": t["token"], "given": "A"} for t in whole["tasks"]]})
        assert mock.counts(_progress(), "B1")["kuulamine"] == 1

    def test_a_token_from_another_part_or_a_forged_one_is_refused(self, client):
        body = client.get("/api/mock/B1/kuulamine?format=harno&seed=5&task=1").json()
        token = body["tasks"][0]["token"]
        wrong_part = client.post("/api/mock/B1/lugemine", json={"format": "harno", 
            "seconds": 1, "answers": [{"token": token, "given": "A"}]})
        whole = client.post("/api/mock/B1/kuulamine", json={"format": "harno", 
            "seconds": 1, "answers": [{"token": token, "given": "A"}]})
        forged = client.post("/api/mock/B1/kuulamine", json={"format": "harno", 
            "seconds": 1, "task": 1, "answers": [{"token": token[:-2] + "00", "given": "A"}]})
        assert wrong_part.status_code == whole.status_code == forged.status_code == 400

    def test_an_answer_counts_once(self, client):
        body = client.get("/api/mock/B1/kuulamine?format=harno&seed=6&task=1").json()
        task = body["tasks"][0]
        got = client.post("/api/mock/B1/kuulamine", json={"format": "harno", "seconds": 1, "task": 1, "answers": [
            {"token": task["token"], "given": _right(task)}] * 5}).json()
        assert (got["asked"], got["correct"]) == (1, 1)

    def test_unknown_parts_and_tasks_are_404(self, client):
        assert client.get("/api/mock/B1/kirjutamine?format=harno").status_code == 404
        assert client.get("/api/mock/C1/lugemine?format=harno").status_code == 404
        assert client.get("/api/mock/A2/lugemine?format=harno&task=4").status_code == 404
        assert client.get("/api/mock/B1/lugemine:harno").status_code == 404

    def test_reading_without_texts_is_empty_and_says_what_is_missing(self, client):
        body = client.get("/api/mock/B1/lugemine?format=harno&seed=1").json()
        built = {b["code"] for b in body["blocks"]}
        assert "B1-lu4" not in built                      # no checked text yet
        assert "B1-lu4" in {m["code"] for m in body["missing"]}

    def test_the_section_regenerates_from_its_token(self, client):
        from eesti.itemref import regenerate, verify

        task = client.get("/api/mock/B1/kuulamine?format=harno&seed=7&task=1").json()["tasks"][2]
        again = regenerate(verify(task["token"])["ref"])
        assert (again.prompt, again.no) == (task["prompt"], task["no"])


def _progress():
    from eesti import progress

    return progress.connect(config.PROGRESS_DB)
