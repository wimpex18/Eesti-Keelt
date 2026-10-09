"""The material pipeline's schema and deterministic gates (ADR-0009, steps 1–2).

A hand-written unit-4 dialogue (`fixtures/material/kohvik-tellimine.json`) is
the draft every test bends: real Estonian, read by the real Vabamorf, against a
small copy of EKI's level list.
"""

from __future__ import annotations

import copy
import json
import re
import sqlite3
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "material" / "kohvik-tellimine.json"

#: EKI's own levels for the lemmas the drafts below use (`official_levels`).
LEVELS = {
    "A1": ("ei", "euro", "jooma", "ka", "kas", "kohv", "kokku", "kõik", "küsima",
           "maksma", "must", "olema", "paluma", "sai", "soovima", "sööma", "tere",
           "täna", "veel", "elama", "maja", "minema", "piim", "kodu", "suur",
           "ilus", "kus", "hommik", "nimi", "raamat", "lugema", "tulema", "eile"),
    "A2": ("kook", "mari", "joon", "tellima"),
}


@pytest.fixture
def words(tmp_path) -> sqlite3.Connection:
    from eesti.wordlist import SCHEMA

    conn = sqlite3.connect(tmp_path / "words.db")
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO official_levels (word, level) VALUES (?, ?)",
                     [(w, level) for level, ws in LEVELS.items() for w in ws])
    # A word list with no `words` rows counts as not built (`wordlist.available`).
    conn.execute("INSERT INTO words (word, freq_rank, proficiency, pos)"
                 " VALUES ('kohv', 1, 'A1', 's')")
    conn.commit()
    return conn


def draft(**changes) -> dict:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc = copy.deepcopy(doc)
    doc.update(changes)
    return doc


def material(**changes):
    from eesti.material.schema import Material

    return Material.model_validate(draft(**changes))


def checked(words, **changes):
    from eesti.material import gates

    return gates.check(material(**changes), words)


def turns(*lines: str) -> list[dict]:
    return [{"speaker": "ab"[i % 2], "text": line} for i, line in enumerate(lines)]


# ---------------------------------------------------------------------------
# Gate 1: the shape
# ---------------------------------------------------------------------------

class TestTheSchema:
    def test_the_fixture_is_a_valid_draft(self):
        m = material()
        assert m.kind == "dialoog" and len(m.turns) == 8

    def test_an_unknown_key_is_refused(self):
        """A misspelt `anwser` must not pass as "no answer"."""
        from pydantic import ValidationError

        doc = draft()
        doc["questions"][0]["anwser"] = doc["questions"][0].pop("answer")
        with pytest.raises(ValidationError):
            material(**doc)

    def test_a_dialogue_has_six_to_ten_turns(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="turns"):
            material(turns=turns("Tere!", "Tere!", "Aitäh!"))

    def test_a_turn_names_a_listed_speaker(self):
        from pydantic import ValidationError

        doc = draft()
        doc["turns"][0]["speaker"] = "c"
        with pytest.raises(ValidationError, match="speaker"):
            material(**doc)

    def test_at_most_three_off_list_words(self):
        from pydantic import ValidationError

        many = [{"lemma": w, "gloss_ru": "x"} for w in ("kook", "joon", "mari", "tellima")]
        with pytest.raises(ValidationError):
            material(off_list=many)

    def test_a_gap_points_inside_the_text(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="gap"):
            material(gaps=[{"id": "g1", "at": 8, "word": "saia", "lemma": "sai",
                            "form": "sg p"}])

    def test_the_id_names_unit_slug_and_content_hash(self):
        m = material()
        assert re.fullmatch(r"mat:kohvik:tellimine@[0-9a-f]{8}", m.ident())

    def test_a_changed_word_is_a_new_id(self):
        doc = draft()
        doc["turns"][6]["text"] = "Kokku viis eurot."
        assert material(**doc).ident() != material().ident()

    def test_the_pipelines_stamp_is_not_part_of_the_hash(self):
        """The stamp vouches for the content; it cannot be part of it."""
        assert material(checks={"blind": {"engine": "x"}}).sha8() == material().sha8()

    def test_the_schema_a_model_is_given_has_no_verdict_field(self):
        """A model that writes its own verdict has not been checked."""
        from eesti.material.schema import json_schema

        schema = json_schema()
        assert "checks" not in schema["properties"]
        assert {"turns", "questions", "off_list", "authoring"} <= set(schema["properties"])

    def test_an_author_may_not_write_the_pipelines_stamp(self, words):
        from eesti.material import gates

        raw = json.dumps(draft(checks={"gates": 1}), ensure_ascii=False)
        _, _, schema = gates.check_text(raw, words)
        assert schema and schema[0].gate == "schema"

    def test_a_draft_that_does_not_parse_fails_the_schema_gate(self, words):
        from eesti.material import gates

        _, report, schema = gates.check_text("{not json", words)
        assert report is None and schema[0].gate == "schema"


# ---------------------------------------------------------------------------
# The draft that passes
# ---------------------------------------------------------------------------

def test_the_fixture_passes_every_gate(words):
    report = checked(words)
    assert report.passed, [str(f) for f in report.failures]
    assert not report.dropped, [str(f) for f in report.dropped]
    assert [q.id for q in report.questions] == ["q1", "q2", "q3", "q4"]
    assert [g.id for g in report.gaps] == ["g1"]


def test_the_gates_need_ekis_list(tmp_path):
    """Without EKI's levels the level gate cannot run, and says so."""
    from eesti.material import gates
    from eesti.wordlist import SCHEMA

    empty = sqlite3.connect(tmp_path / "empty.db")
    empty.executescript(SCHEMA)
    report = gates.check(material(), empty)
    assert not report.passed and report.failures[0].gate == "level"


def test_the_level_is_ekis_not_the_frequency_estimate(tmp_path):
    """`words.proficiency` is an estimate; only `official_levels` is EKI's."""
    from eesti.material.gates import eki_levels
    from eesti.wordlist import SCHEMA

    conn = sqlite3.connect(tmp_path / "w.db")
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO words (word, freq_rank, proficiency, pos) VALUES ('kook', 1, 'A1', 's')")
    conn.execute("INSERT INTO official_levels (word, level) VALUES ('kook', 'A2')")
    assert eki_levels(conn) == {"kook": "A2"}


# ---------------------------------------------------------------------------
# Gate 2: Vabamorf
# ---------------------------------------------------------------------------

class TestVabamorf:
    def test_an_unknown_word_fails_the_draft(self, words):
        doc = draft()
        doc["turns"][6]["text"] = "Kokku neli eurrot."
        report = checked(words, **doc)
        assert not report.passed
        assert any(f.gate == "vabamorf" and "eurrot" in f.message for f in report.failures)

    def test_a_declared_name_need_not_be_known(self, words):
        """*Ivanovna* is a name the spellchecker refuses; declared, it passes."""
        doc = draft()
        doc["turns"][0]["text"] = "Tere! Mina olen Ivanovna."
        assert any(f.gate == "vabamorf" for f in checked(words, **doc).failures)
        assert not any(f.gate == "vabamorf"
                       for f in checked(words, names=["Ivanovna"], **{
                           k: v for k, v in doc.items() if k != "names"}).failures)

    def test_an_unknown_word_in_a_question_drops_only_the_question(self, words):
        doc = draft()
        doc["questions"][1]["question"] = "Mis maksab kokkku?"
        report = checked(words, **doc)
        assert report.passed
        assert [f.gate for f in report.dropped] == ["vabamorf"]
        assert "q2" not in [q.id for q in report.questions]


# ---------------------------------------------------------------------------
# Gate 3: EKI's level
# ---------------------------------------------------------------------------

class TestLevel:
    def test_an_undeclared_word_beyond_the_stage_fails(self, words):
        report = checked(words, off_list=[])
        assert any(f.gate == "level" and "kook" in f.message for f in report.failures)

    def test_a_declared_and_glossed_word_passes(self, words):
        assert checked(words).passed

    def test_a_declared_word_on_the_list_is_refused(self, words):
        """A gloss for a word the stage already has is noise, and a false label."""
        report = checked(words, off_list=[{"lemma": "kook", "gloss_ru": "пирог"},
                                          {"lemma": "kohv", "gloss_ru": "кофе"}])
        assert any(f.where == "off_list" and "kohv" in f.message for f in report.failures)

    def test_a_declared_word_the_text_never_uses_is_refused(self, words):
        report = checked(words, off_list=[{"lemma": "kook", "gloss_ru": "пирог"},
                                          {"lemma": "tellima", "gloss_ru": "заказывать"}])
        assert any("tellima" in f.message and "not used" in f.message
                   for f in report.failures)

    def test_a_homograph_on_the_list_counts(self, words):
        """The disambiguator reads *Ma joon* as the noun "line"; the verb is A1."""
        from eesti.material import gates

        assert any(r[0] == "jooma" for r in gates._all_readings("joon"))
        assert checked(words).passed

    def test_the_stage_widens_the_list(self, words):
        """At A2 (unit 11, *kodus*) an A2 word needs no declaration."""
        from eesti.material import gates

        ctx = gates._Context(material(unit="kodus", off_list=[]), words)
        assert ctx.stage_levels == ("A1", "A2")
        assert gates._level(ctx, gates._words("Ma ei söö täna kooki.")) == []


# ---------------------------------------------------------------------------
# Gate 4: forms only from introduced topics
# ---------------------------------------------------------------------------

class TestForms:
    @pytest.mark.parametrize("reading,after_negator,needs", [
        (("tulema", "V", "o"), True, {"eitus"}),            # ei tule
        (("tulema", "V", "o"), False, {"kaskiv"}),          # tule!
        (("olema", "V", "neg o"), False, {"eitus"}),        # pole
        (("ära", "V", "neg o"), False, {"kaskiv"}),         # ära tule
        (("tulema", "V", "nud"), True, {"eitus"}),          # ei tulnud
        (("tulema", "V", "nud"), False, {"taisminevik"}),   # on tulnud
        (("olema", "V", "b"), False, {"olevik"}),
        (("tulema", "V", "s"), False, {"lihtminevik"}),
        (("tulema", "V", "ks"), False, {"tingiv"}),
        (("sööma", "V", "da"), False, {"verb-form"}),
        (("kohv", "S", "sg n"), False, set()),
        (("kohv", "S", "sg p"), False, {"pohivormid"}),
        (("Tallinn", "H", "sg in"), False, {"kohakaanded"}),
        (("pood", "S", "adt"), False, {"kohakaanded"}),
        (("sõber", "S", "sg kom"), False, {"harvad-kaanded"}),
        (("maja", "S", "pl in"), False, {"mitmus", "kohakaanded"}),
        (("mina", "P", "sg all"), False, {"asesonad"}),
        (("suurem", "C", "sg n"), False, {"vordlusastmed"}),
        (("kolmas", "O", "sg n"), False, {"jargarvud"}),
        (("kõrval", "K", ""), False, {"kaassonad"}),
        (("sest", "J", ""), False, {"sidesonad"}),
        (("ja", "J", ""), False, set()),
        (("täna", "D", ""), False, set()),
        (("5", "N", "?"), False, set()),
    ])
    def test_each_form_needs_its_topic(self, reading, after_negator, needs):
        from eesti.material.gates import reading_topics

        assert reading_topics(*reading, after_negator=after_negator) == frozenset(needs)

    def test_a_form_no_topic_covers_is_refused(self):
        from eesti.material.gates import reading_topics

        assert reading_topics("tulema", "V", "xyz") is None

    def test_every_topic_named_is_a_curriculum_topic(self):
        from eesti.curriculum import TOPICS
        from eesti.material import gates

        named = (set(gates.CASE_TOPICS.values()) | set(gates.VERB_TOPICS.values())
                 | set(gates.POS_TOPICS.values()) | {"eitus", "kaskiv", "taisminevik",
                                                     "sidesonad", "mitmus", "kohakaanded"})
        assert named - {None} <= {t.id for t in TOPICS}

    def test_introduced_is_cumulative(self):
        from eesti.material.gates import introduced

        assert {"fraasid", "olevik", "pohivormid", "eitus"} <= introduced("kohvik")
        assert "kohakaanded" not in introduced("kohvik")
        assert "kohakaanded" in introduced("kodu")

    def test_a_case_the_unit_has_not_taught_fails(self, words):
        doc = draft()
        doc["turns"][3]["text"] = "Ei, aitäh. Ma elan Tallinnas. Ma joon musta kohvi."
        report = checked(words, **doc)
        assert any(f.gate == "forms" and "Tallinnas" in f.message
                   and "kohakaanded" in f.message for f in report.failures)

    def test_the_same_case_passes_once_its_unit_has_come(self, words):
        """Unit 5 (*kodu*) introduces the local cases."""
        from eesti.material import gates

        ctx = gates._Context(material(unit="kodu"), words)
        assert gates._forms(ctx, gates._words("Ma elan Tallinnas.")) == []

    def test_negation_is_unit_4_and_the_imperative_unit_11(self, words):
        from eesti.material import gates

        ctx = gates._Context(material(), words)
        assert gates._forms(ctx, gates._words("Ma ei taha.")) == []
        assert gates._forms(ctx, gates._words("Tule siia!"))

    def test_the_disambiguated_reading_is_judged(self, words):
        """Vabamorf reads *Piima ma ei taha* as the short illative: refused, reword it."""
        from eesti.material import gates

        ctx = gates._Context(material(), words)
        assert gates._forms(ctx, gates._words("Piima ma ei taha."))
        assert gates._forms(ctx, gates._words("Ma ei taha piima.")) == []

    def test_ekis_phrases_are_exempt(self, words):
        """*Tere hommikust!* is taught whole in unit 1; its elative is not taught till 5."""
        from eesti.material import gates

        ctx = gates._Context(material(unit="tutvume"), words)
        assert gates._forms(ctx, gates._words("Tere hommikust!")) == []
        assert gates._forms(ctx, gates._words("Ma tulen hommikust."))

    def test_a_declared_names_case_is_still_a_case(self, words):
        """A name is exempt from Vabamorf's lexicon, not from the grammar."""
        from eesti.material import gates

        ctx = gates._Context(material(names=["Svetlana"]), words)
        assert gates._forms(ctx, gates._words("See on Svetlana."))  == []
        assert gates._forms(ctx, gates._words("See on Svetlanale."))


# ---------------------------------------------------------------------------
# Gate 5: answers verbatim, once
# ---------------------------------------------------------------------------

class TestAnswers:
    def _with(self, words, question: str, answer: str):
        doc = draft()
        doc["questions"].append({"id": "q9", "question": question, "answer": answer})
        return checked(words, **doc)

    def test_an_answer_twice_in_the_text_is_dropped(self, words):
        report = self._with(words, "Mida Juhan ei söö?", "kooki")
        assert [(f.gate, f.where) for f in report.dropped] == [("answers", "question q9")]

    def test_an_answer_not_in_the_text_is_dropped(self, words):
        report = self._with(words, "Mida Juhan soovib?", "teed")
        assert [f.gate for f in report.dropped] == ["answers"]

    def test_a_question_giving_its_answer_is_dropped(self, words):
        report = self._with(words, "Kas kokku neli eurot?", "neli eurot")
        assert "q9" not in [q.id for q in report.questions]

    def test_the_speakers_names_are_part_of_the_text(self, words):
        """The shown text says *Mari:* four times, so *Mari* is no answer."""
        report = self._with(words, "Kes küsib?", "Mari")
        assert "q9" not in [q.id for q in report.questions]

    def test_too_few_questions_fail_the_draft(self, words):
        doc = draft()
        doc["questions"] = doc["questions"][:2]
        report = checked(words, **doc)
        assert any("fewer than" in f.message for f in report.failures)


# ---------------------------------------------------------------------------
# Gate 6: one right answer per gap
# ---------------------------------------------------------------------------

class TestGaps:
    def _gap(self, words, gap: dict, line: str, unit: str = "kohvik") -> str | None:
        from eesti.material import gates
        from eesti.material.schema import Gap

        ctx = gates._Context(material(unit=unit), words)
        return gates._gap(ctx, Gap.model_validate({"id": "g9", "at": 0, **gap}), [line])

    def test_the_fixtures_gap_has_one_answer(self, words):
        assert self._gap(words, {"word": "saia", "lemma": "sai", "form": "sg p"},
                         "Üks kohv ja kaks saia, palun.") is None

    def test_a_form_the_sentence_does_not_read_is_refused(self, words):
        why = self._gap(words, {"word": "saia", "lemma": "sai", "form": "sg g"},
                        "Üks kohv ja kaks saia, palun.")
        assert why and "not read as" in why

    def test_a_label_two_forms_answer_is_refused(self, words):
        """*sisseütlev* of *maja* is *majasse* and *majja*: two right answers."""
        why = self._gap(words, {"word": "majasse", "lemma": "maja", "form": "sg ill"},
                        "Ma lähen majasse.", unit="kodu")
        assert why and "majja" in why

    def test_a_free_variant_is_refused(self, words):
        """*kaht* and *kahte* are both the partitive of *kaks*."""
        why = self._gap(words, {"word": "kahte", "lemma": "kaks", "form": "sg p"},
                        "Ma ei taha kahte.")
        assert why and "two right answers" in why

    def test_a_form_without_a_label_is_refused(self, words):
        why = self._gap(words, {"word": "taha", "lemma": "tahtma", "form": "o"},
                        "Ma ei taha.")
        assert why and "label" in why

    def test_a_form_the_unit_has_not_taught_is_refused(self, words):
        why = self._gap(words, {"word": "Tallinnas", "lemma": "Tallinn", "form": "sg in"},
                        "Ma elan Tallinnas.")
        assert why and "not introduced" in why

    def test_a_word_twice_in_its_line_is_refused(self, words):
        why = self._gap(words, {"word": "saia", "lemma": "sai", "form": "sg p"},
                        "Kaks saia ja veel kaks saia.")
        assert why and "exactly once" in why

    def test_a_dropped_gap_does_not_fail_the_draft(self, words):
        doc = draft()
        doc["gaps"].append({"id": "g2", "at": 1, "word": "saia", "lemma": "sai",
                            "form": "sg g"})
        report = checked(words, **doc)
        assert report.passed and [g.id for g in report.gaps] == ["g1"]


# ---------------------------------------------------------------------------
# Gate 7: duplicates
# ---------------------------------------------------------------------------

def test_a_question_asked_twice_is_dropped(words):
    doc = draft()
    doc["questions"].append({**doc["questions"][0], "id": "q9"})
    report = checked(words, **doc)
    assert [(f.gate, f.where) for f in report.dropped] == [("duplicates", "question q9")]


def test_the_kept_draft_holds_only_what_passed(words):
    doc = draft()
    doc["questions"].append({"id": "q9", "question": "Mida Juhan ei söö?", "answer": "kooki"})
    kept = checked(words, **doc).kept()
    assert [q.id for q in kept.questions] == ["q1", "q2", "q3", "q4"]
