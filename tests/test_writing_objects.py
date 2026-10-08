"""Deterministic writing checks around the object (DEV-50).

Seen in Kirjutamine and the B1 writing mock with the model lanes off: *loen
raamat*, *jõin kohv* and *vaatasime uus film* passed as clean; *poodi* (short
illative, "to the shop") was flagged as a partitive object; *Tallinas* was
corrected to *Tallina* instead of *Tallinnas*. Precision first: a flag here is
code's claim, so it is made only where the morphology settles it.
"""

from __future__ import annotations

import pytest

from eesti import evs, morph, wordlist
from eesti.providers import grammar

#: What EKI's dictionaries say take an object, for the hermetic database below.
OBJECT_VERBS = ("lugema", "jooma", "vaatama", "ootama", "rääkima", "ostma", "saama",
                "paluma", "teadma", "ajama", "tundma", "arvama", "sööma", "kuulma")


@pytest.fixture
def words_db(tmp_path, monkeypatch):
    from eesti import config

    path = tmp_path / "eesti.db"
    conn = wordlist.connect(path)
    # `wordlist.available()` asks for a word list with words in it.
    conn.execute("INSERT INTO words(word, freq_rank, proficiency, pos) VALUES (?,?,?,?)",
                 ("raamat", 1, "A1", "s"))
    evs.store_object_verbs(conn, OBJECT_VERBS)
    conn.commit()
    monkeypatch.setattr(config, "DB_PATH", path)
    return conn


def _found(text):
    return {c.wrong: c for c in grammar.nominative_objects(text)}


class TestAMissingObjectCase:
    """A nominative singular right after a 1st/2nd-person or negated verb that
    takes an object cannot be its object: the object is osastav or omastav."""

    def test_the_reported_sentences(self, words_db):
        for text, wrong in [("Ma loen raamat.", "raamat"), ("Eile jõin kohv.", "kohv"),
                            ("Me vaatasime uus film.", "uus film"),
                            ("Me jõime kohv.", "kohv")]:
            assert wrong in _found(text), text

    def test_one_form_for_both_cases_is_the_correction(self, words_db):
        """*kohvi* is both omastav and osastav, so it is right either way."""
        got = _found("Eile jõin kohv.")["kohv"]
        assert got.correct == "kohvi"
        assert got.tag == "obj-case" and got.source == "deterministic"

    def test_omastav_is_offered_only_for_a_completed_action(self, words_db):
        """Some verbs never take omastav (*räägime eesti keelt*): the genitive is
        named with its condition, never as an equal choice."""
        why = _found("Me räägime eesti keel.")["eesti keel"].why
        assert "только если действие завершено" in why

    def test_two_forms_are_named_and_neither_is_imposed(self, words_db):
        """*loen raamatut* (process) and *loen raamatu läbi* (completed) are both
        Estonian; code knows only that *raamat* is not."""
        got = _found("Ma loen raamat.")["raamat"]
        assert got.correct == ""
        assert "raamatut" in got.why and "raamatu" in got.why
        phrase = _found("Me vaatasime uus film.")["uus film"]
        assert "uut filmi" in phrase.why and "uue filmi" in phrase.why

    def test_after_a_negation_the_partitive_is_the_correction(self, words_db):
        assert _found("Ma ei loe raamat.")["raamat"].correct == "raamatut"
        assert _found("Ära joo kohv!")["kohv"].correct == "kohvi"

    def test_a_genitive_attribute_stays_as_it_is(self, words_db):
        assert "eesti keelt" in _found("Me räägime eesti keel.")["eesti keel"].why

    @pytest.mark.parametrize("text", [
        "Ma loen raamatut.",            # already partitive
        "Ma olen õpetaja.",             # predicative, not an object
        "Ma ei ole õpetaja.",
        "Loe raamat läbi!",             # imperative: the total object is nimetav
        "Ma ootasin terve päev.",       # a time adverbial, not an object
        "Ta loeb raamat.",              # third person: the noun could be the subject
        "Teda ei armasta mees.",        # no 1st/2nd-person subject before ei
        "Ma lähen kool.",               # minema takes no object: wrong, but not this error
        "Ma saan arst.",                # saama + predicative
        "Ma loen, raamat on laual.",    # another clause
        "Pane palun aken kinni.",       # palun is "please" here
        "(Teate pikkus kuni 50 sõna.)", # teate: the genitive of teade
        "Ajasime raasike juttu.",       # a quantity before a partitive
        "Ma tunnen professor Tamme.",   # a title before a name does not decline
        "Me ootame direktor Kaske.",    # ... even when the name reads as a noun
        "Eile vaatasime vend ja mina filmi.",   # a coordinated subject
        "Ma arvan eesti keel on raske.",        # a comma left out
        "Ma tean poiss on tark.",
    ])
    def test_no_claim_where_the_morphology_does_not_settle_it(self, words_db, text):
        assert not grammar.nominative_objects(text), text

    def test_nothing_without_the_reference_data(self, tmp_path, monkeypatch):
        from eesti import config

        monkeypatch.setattr(config, "DB_PATH", tmp_path / "missing.db")
        assert grammar.nominative_objects("Ma loen raamat.") == []

    def test_the_writing_mock_counts_it(self, words_db):
        from eesti.mock import check_writing

        got = check_writing("Eile jõin kohv.", "B1")
        assert got["errors"] == 1
        assert got["findings"][0]["wrong"] == "kohv"

    def test_a_phrase_finding_replaces_a_model_edit_of_its_word(self, words_db):
        class Partial:
            name = "pretend-llm"

            def available(self):
                return True

            def check(self, text):
                return grammar.GrammarResult(self.name, [
                    grammar.Correction("film", "filmi", "", "obj-case")])

        answer = grammar.check("Me vaatasime uus film.", providers=[Partial()])
        assert [c.wrong for c in answer.corrections if "film" in c.wrong] == ["uus film"]

    def test_it_is_merged_into_every_answer(self, words_db):
        class Silent:
            name = "pretend-llm"

            def available(self):
                return True

            def check(self, text):
                return grammar.GrammarResult(self.name, [])

        answer = grammar.check("Eile jõin kohv.", providers=[Silent()])
        assert any(c.wrong == "kohv" for c in answer.corrections)


class TestLocalCasesAreNotObjects:
    """*poodi* is a partitive or a short illative; the disambiguator picks the
    partitive in *Ma pean minema poodi*."""

    @staticmethod
    def _flagged(text):
        return {c.wrong for c in grammar.VabamorfFallback().check(text).corrections
                if c.tag == "obj-case"}

    def test_a_short_illative_after_a_verb_of_motion_is_not_flagged(self, words_db):
        assert "poodi" not in self._flagged("Ma pean minema poodi.")

    def test_the_same_shape_after_a_verb_with_an_object_still_is(self, words_db):
        """*leiba* is also a short illative; after *söön* it is the object."""
        assert "leiba" in self._flagged("Ma söön leiba ära.")

    def test_without_the_word_list_no_place_is_offered_as_an_object(
            self, tmp_path, monkeypatch):
        from eesti import config

        monkeypatch.setattr(config, "DB_PATH", tmp_path / "missing.db")
        assert "poodi" not in self._flagged("Ma pean minema poodi.")
        assert not (tmp_path / "missing.db").exists(), "a check must not create it"

    def test_other_readers_keep_every_candidate(self):
        """Topic links and the GEC eval read candidates without the filter."""
        assert "leiba" in {t.text for t in morph.object_case_candidates("Ma söön leiba.")}


class TestSpellingSuggestions:
    def test_the_suggestion_keeps_the_form_the_learner_wrote(self):
        """*Tallinas* reads as an inessive; *Tallina* reads back as the essive of
        *tall*, *Tallinnas* as the inessive of *Tallinn*."""
        got = {c.wrong: c.correct for c in grammar.spelling("Ma elan Tallinas.")}
        assert got["Tallinas"] == "Tallinnas"

    def test_an_odd_compound_is_not_promoted(self):
        """The guesser's form matches *jaks_jaama*; Vabamorf's first choice stays."""
        got = {c.wrong: c.correct for c in grammar.spelling("Ma jaksaama.")}
        assert got.get("jaksaama") != "jaksjaama"

    def test_an_order_with_no_better_evidence_is_kept(self):
        got = {c.wrong: c.correct for c in grammar.spelling("Ma ostsin raamtut.")}
        assert got["raamtut"] == "raamatut"


class TestObjectVerbsFromEki:
    def test_evs_russian_government_marks_a_verb_that_takes_an_object(self, tmp_path):
        """`jooma` «пить что» takes an object; `elama` «жить где» does not."""
        path = tmp_path / "evs.xml"
        path.write_text(
            '<x:A><x:P><x:mg><x:m>jooma</x:m><x:sl>v</x:sl></x:mg></x:P><x:S><x:tp><x:tg>'
            '<x:xp xml:lang="ru"><x:xg><x:x>пить</x:x><x:vrek>что</x:vrek></x:xg></x:xp>'
            '</x:tg></x:tp></x:S></x:A>\n'
            '<x:A><x:P><x:mg><x:m>elama</x:m><x:sl>v</x:sl></x:mg></x:P><x:S><x:tp><x:tg>'
            '<x:xp xml:lang="ru"><x:xg><x:x>жить</x:x><x:vrek>где</x:vrek></x:xg></x:xp>'
            '</x:tg></x:tp></x:S></x:A>\n', encoding="utf-8")
        assert evs.object_verbs(path) == ["jooma"]

    def test_psv_rection_counts_too(self, words_db):
        """`õppima` «учиться чему» in EVS, but PSV's rection says `mida`."""
        from eesti import psv

        psv.store(words_db, [psv.Entry("õppima", "omandama", (), "V",
                                       rection=("mida", "kelleks"))])
        assert "eesti keel" in _found("Ma õpin eesti keel.")
