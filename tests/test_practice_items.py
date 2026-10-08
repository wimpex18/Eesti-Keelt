"""Practice items that taught something wrong or gave themselves away (DEV-51).

Found in the October 2026 learner walkthrough: "____ tütres" labelled
*sisseütlev*; "lahkel peal" (a postposition read as a noun); a principal-forms
item whose answer was the word in its instruction; sentence-initial blanks
filled in lower case; non-word distractors (*lehtl*, *metss*) offered as
choices; a rection label reading "TEAVITAMA?"; placement blanks with no cue and
no review of what was wrong.
"""

from __future__ import annotations

import pytest

from eesti import forms, lessons, wordlist
from eesti.item import BLANK
from eesti.morph import _readings


@pytest.fixture
def words(tmp_path):
    conn = wordlist.connect(tmp_path / "eesti.db")
    conn.executemany(
        "INSERT INTO words(word, freq_rank, proficiency, pos) VALUES (?,?,?,?)",
        [("lahke", 1, "A1", "adj"), ("ilus", 2, "A1", "adj"), ("suur", 3, "A1", "adj"),
         ("pea", 4, "A1", "s"), ("tütar", 5, "A1", "s"), ("raamat", 6, "A1", "s"),
         ("suhkur", 7, "A1", "s"), ("maja", 8, "A1", "s")])
    wordlist.object_case_rows(conn, ["pea", "tütar", "raamat", "suhkur", "maja"])
    conn.commit()
    return conn


class TestAgreement:
    @pytest.fixture
    def drills(self, words):
        return forms.agreement_drills(words, count=60, seed=4)

    def test_the_label_names_the_case_the_noun_is_in(self, drills):
        """*tütres* is seesütlev; the inessive was labelled sisseütlev."""
        assert drills
        for d in drills:
            name = d.label_et.split(": ")[1].split()[-1]
            number = "pl" if "mitmuse" in d.label_et else "sg"
            noun = d.prompt.split()[1]
            assert f"{number} {lessons._CASE[name]}" in {f for _, f in _readings(noun)}, d

    def test_no_noun_form_is_also_another_word(self, drills):
        """*peal* is *pea* "head" on the adessive, and the postposition *peal*."""
        for d in drills:
            noun = d.prompt.split()[1]
            assert len({lemma for lemma, _ in _readings(noun)}) == 1, d


def test_a_principal_form_is_never_the_word_in_the_instruction(words):
    """"Впиши форму слова suhkur. nimetav." answered itself."""
    items = forms.principal_forms(words, count=20, seed=2)
    assert items
    assert all(d.answer != d.lemma for d in items)


class TestCapitals:
    def test_a_lesson_example_opening_with_the_blank_is_capitalised(self, monkeypatch):
        from eesti import practice

        item = forms.FormDrill(prompt=f"{BLANK} palun kohe!", answer="kirjutage ~ kirjutagem",
                               distractor="", lemma="kirjutama", label_et="käskiv",
                               why_ru="", topic="kaskiv")
        monkeypatch.setattr(practice, "items_for", lambda *a, **k: [item])
        got = lessons.examples("kaskiv")
        assert got[0]["before"] + got[0]["answer"] + got[0]["after"] == "Kirjutage palun kohe!"

    def test_a_recorded_mistake_shows_its_sentence_capitalised(self):
        from eesti.learner import Mistake

        mistake = Mistake(event_id="e1", topic="possessive", rule=None,
                          prompt=f"{BLANK} on kaks last.", expected="minul",
                          answer="mina", at="2026-10-08")
        assert mistake.solution == "Minul on kaks last."


class TestCorpusItems:
    @pytest.fixture
    def items(self, words):
        from eesti.cloze import case_clozes

        sentences = ["Laane küla metsas liigub ringi ilves.",
                     "Ta tuli eile metsast koju.",
                     "Me ootame bussi peatuses.",
                     "Eestis oli ligi 12 000 vaba ametikoh ta metsas."]
        return case_clozes(sentences, topics=("kohakaanded",), words=words, count=10,
                           seed=1, levels=("A1", "A2", "B1", None))

    def test_a_distractor_offered_as_a_choice_is_a_word(self, items):
        assert items
        for it in items:
            assert not it.distractor or _readings(it.distractor), it.distractor
            assert "не *" not in it.why_ru or it.distractor

    def test_the_stem_named_in_the_explanation_is_the_answers_stem(self, items):
        """A form not built on the singular genitive (*töid*, *lapsi*) must not be
        explained as if it were."""
        import re

        for it in items:
            stem = re.search(r"omastav\*\* \(\*(\w+)\*\)", it.why_ru)
            assert not stem or it.answer.split(" ~ ")[0].startswith(stem.group(1)), it

    def test_plural_forms_keep_the_stem_claim_true(self, words):
        from eesti.cloze import case_clozes

        items = case_clozes(["Me tegime eile palju töid.", "Ta elab suurtes linnades."],
                            topics=("mitmus",), words=words, count=10, seed=1,
                            levels=("A1", "A2", "B1", None))
        assert [it.answer for it in items] == ["linnades"]   # *töid* is not on *töö*

    def test_a_sentence_with_a_broken_word_is_not_used(self, items):
        assert all("ametikoh" not in it.prompt for it in items)


def test_a_rection_item_names_what_is_asked():
    """The label read "TEAVITAMA?" under the blank."""
    from eesti.cloze import Cloze

    item = Cloze(prompt=f"Teavitasime {BLANK} ajast.", answer="kliente", distractor="klientidele",
                 lemma="klient", case="pl p", case_et="osastav", rule="rection",
                 why_ru="", topic="rektsioon", level=None, source_id="ekk",
                 governor="teavitama")
    assert item.label == "rektsioon: teavitama"


class TestPlacement:
    def test_a_choice_topic_cue_does_not_name_the_case(self, client):
        """obj-case hides its form until the verdict (`render.CHOICE_TOPICS`);
        the placement cue is built from lemma and label, so it stays hidden."""
        shown = client.get("/api/testout/obj-case?seed=3").json()
        assert shown["items"]
        for item in shown["items"]:
            assert item["label"] == "" and item["form_after"]

    def test_each_blank_is_cued_and_each_answer_reviewed(self, client):
        """A pronoun blank accepted one key where several fit (*sind / sinuga /
        mulle*): the cue says which word and form; the result says which were
        wrong and what was expected."""
        shown = client.get("/api/testout/asesonad?seed=5").json()
        assert all(item["hint"] for item in shown["items"])
        got = client.post("/api/testout/asesonad",
                          json={"seed": 5, "given": ["x"] * len(shown["items"])}).json()
        assert len(got["items"]) == len(shown["items"])
        assert all(not row["correct"] and row["solution"] and row["answer"]
                   for row in got["items"])
