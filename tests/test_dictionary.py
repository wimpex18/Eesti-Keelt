"""Sõnastik: an entry found by any form, every part from a source that is named.

The learner-visible failures these prevent: a form the learner met that finds
nothing; a level, form, recording or translation shown without its source or
from the wrong one; a model's gloss shown as a dictionary's; a Russian word
passed off as Ukrainian; a recording of one form played for another spelt alike.
"""

from __future__ import annotations

import json
import shutil

import pytest

from eesti import config, dictionary, evs, gloss, haaldus, wordlist
from eesti.providers import ekilex, sonapi

#: EKI's level list as the file has it: a lemma listed twice, as the pronoun
#: and the noun "ego", keeps its lower level and that line's part of speech.
LEVELS = "\n".join([
    "LEMMA\tPOS\tSAGEDUS\tTASE",
    "raamat\tS\t1558\tA1",
    "lugema\tV\t781342\tA1",
    "mina\tP\t12703826\tA1",
    "mina\tS\t210816\tB1",
    "kool\tS\t654962\tA1",
])


@pytest.fixture
def words(tmp_path, monkeypatch, fixture_data):
    """A copy of the fixture word list with EKI's tables written by their own
    writers, as the importers would."""
    path = tmp_path / "eesti.db"
    shutil.copy(fixture_data["words"], path)
    monkeypatch.setattr(config, "DB_PATH", path)
    conn = wordlist.connect(path)
    with conn:
        conn.executemany("INSERT OR REPLACE INTO words (word, freq_rank, proficiency, pos)"
                         " VALUES (?,?,?,?)",
                         [("mina", 47, None, "pron"), ("kool", 300, None, "s"),
                          ("kus", 67, None, "adv"), ("kass", 900, "B2", "s")])
    levels = tmp_path / "A1A2B1.txt"
    levels.write_text(LEVELS, encoding="utf-8")
    wordlist.import_official_levels(conn, levels)
    evs.store(conn, [
        evs.Entry("raamat", "s", ("книга", "книжка")),
        evs.Entry("lugema", "v", ("читать",)),
        evs.Entry("kool", "s", ("школа",)),
        evs.Entry("kus", "adv", ("где",)),
        evs.Entry("kass", "s", ("кошка",)),
        evs.Entry("maja", "s", ("дом",)),
    ])
    evs.store_examples(conn, [
        evs.Example("kool", "kooli minema", "идти в школу"),
        evs.Example("raamat", "raamatut lugema", "читать книгу"),
    ])
    yield conn
    conn.close()


def _audio(tmp_path, monkeypatch, rows):
    path = tmp_path / "audio.db"
    conn = haaldus.connect(path)
    with conn:
        conn.executemany(
            "INSERT INTO pronunciation (form, tag, spoken, lemma, mime, audio, source)"
            " VALUES (?,?,?,?,?,?,?)",
            [(haaldus.plain(s), tag, s, lemma, "audio/mpeg", b"\x00", "psv-haaldused")
             for s, tag, lemma in rows])
    conn.close()
    monkeypatch.setattr(config, "AUDIO_DB", str(path))
    return dictionary._audio(path)


def _record(**over) -> dict:
    record = {"lemma": "raamat", "lang": "en", "gloss": ["book"], "anchor": ["книга"],
              "pos": "s", "engine": "claude-opus-5-5", "prompt": "s9-gloss-1",
              "checker": "claude-haiku-5-5", "check_prompt": "s9-back-1",
              "back": ["raamat"]}
    return {**record, **over}


def _glosses(tmp_path, words, *records) -> dict:
    path = tmp_path / "glosses.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
                    encoding="utf-8")
    return dictionary.import_glosses(words, path)


class TestFoundByAnyForm:
    def test_an_inflected_form_finds_its_lemma_and_says_what_form_it_is(self, words):
        got = dictionary.search(words, "raamatut")
        first = got["results"][0]
        assert first["lemma"] == "raamat"
        assert [t["tag"] for t in first["match"]["tags"]] == ["sg p"]
        assert first["match"]["tags"][0]["name"] == "ainsuse osastav"

    def test_a_verb_form_past_the_index_is_read_by_vabamorf(self, words):
        """The fixture's form index has no verb forms: *loeb* is read by Vabamorf."""
        got = dictionary.search(words, "loeb")
        assert got["results"][0]["lemma"] == "lugema"
        assert got["results"][0]["match"]["tags"][0]["tag"] == "b"

    def test_the_headword_itself_comes_first_and_beginnings_follow(self, words):
        got = [r["lemma"] for r in dictionary.search(words, "raamat")["results"]]
        assert got[0] == "raamat"
        assert "kool" not in got

    def test_a_russian_word_finds_what_evs_translates_with_it(self, words):
        got = dictionary.search(words, "Школа")
        assert got["russian"] and got["results"][0]["lemma"] == "kool"

    def test_a_misspelling_gets_vabamorfs_suggestions_and_no_guess(self, words):
        got = dictionary.search(words, "raamatux")
        assert got["results"] == []
        assert got["suggestions"] and all(isinstance(s, str) for s in got["suggestions"])

    def test_a_query_is_cleaned_not_trusted(self, words):
        assert dictionary.search(words, "  <>!")["results"] == []
        assert dictionary.clean("<b>maja</b>") == "b maja b"
        assert dictionary.clean("x" * 500) == "x" * dictionary.MAX_QUERY


class TestTheLevelNamesWhoSaysSo:
    def test_ekis_list_wins_and_is_named(self, words):
        got = dictionary.entry(words, "raamat")["level"]
        assert (got["level"], got["source"], got["estimate"]) == ("A1", "eki-tasemesonavara", False)

    def test_a_word_listed_twice_keeps_the_lower_level_of_its_own_part_of_speech(self, words):
        """*mina* is the pronoun at A1 and the noun "ego" at B1; the last line used to win."""
        got = dictionary.entry(words, "mina")["level"]
        assert (got["level"], got["listed_as"], got["same_word"]) == ("A1", "asesõna", True)

    def test_without_the_list_the_level_is_an_estimate_and_says_so(self, words):
        got = dictionary.entry(words, "kass")["level"]
        assert (got["level"], got["source"], got["estimate"]) == ("B2", "ekilex-wordlist", True)


class TestForms:
    def test_a_verb_shows_the_forms_a_learner_needs_from_vabamorf(self, words):
        got = dictionary.entry(words, "lugema")["forms"]
        assert got["source"] == "vabamorf" and got["kind"] == "verb"
        assert {r["tag"]: r["forms"] for r in got["rows"]} == {
            "ma": ["lugema"], "da": ["lugeda"], "b": ["loeb"], "s": ["luges"],
            "nud": ["lugenud"], "tud": ["loetud"], "takse": ["loetakse"]}

    def test_a_noun_shows_its_principal_forms_and_the_full_table(self, words):
        got = dictionary.entry(words, "raamat")["forms"]
        assert [r["tag"] for r in got["rows"]] == list(dictionary.NOUN_TAGS)
        assert {r["tag"]: r["forms"] for r in got["rows"]}["sg p"] == ["raamatut"]
        assert len(got["paradigm"]) == 28

    def test_a_second_paradigm_vabamorf_keeps_is_settled_by_ekis_own_phrase(self, words):
        """Vabamorf reads *koola* as *kool* too; EVS's *kooli minema* says which."""
        rows = {r["tag"]: r["forms"] for r in dictionary.entry(words, "kool")["forms"]["paradigm"]}
        assert rows["sg g"] == ["kooli"] and rows["pl n"] == ["koolid"]

    def test_a_pronoun_comes_from_the_ekis_tables_not_vabamorf(self, words):
        got = dictionary.entry(words, "mina")["forms"]
        assert got["source"] == "eki-teatmik"
        assert {r["tag"]: r["forms"] for r in got["rows"]}["sg g"] == ["minu", "mu"]

    def test_a_word_that_does_not_inflect_invents_no_forms(self, words):
        got = dictionary.entry(words, "kus")["forms"]
        assert got["rows"] == [] and got["kind"] is None


class TestRecordings:
    def test_a_recording_is_offered_only_for_its_own_form_and_tag(self, words, tmp_path,
                                                                   monkeypatch):
        """EKI reads *kassi* twice, the genitive and the partitive, with different length."""
        audio = _audio(tmp_path, monkeypatch, [("k`assi", "sg p", ""), ("kass", "sg n", "")])
        got = dictionary.entry(words, "kass", audio=audio)
        rows = {r["tag"]: r for r in got["forms"]["rows"]}
        assert rows["sg p"]["recorded"] == ["kassi"]
        assert rows["sg g"]["recorded"] == []
        assert got["recording"] == {"form": "kass", "tag": "sg n"}
        assert "psv-haaldused" in {s["id"] for s in got["sources"]}

    def test_no_recordings_mounted_is_no_recording(self, words):
        assert dictionary.entry(words, "kass")["recording"] is None


class TestMeanings:
    def test_russian_comes_from_ekis_dictionary_and_is_named(self, words):
        got = dictionary.entry(words, "kass")["meanings"]["ru"]
        assert got == {"words": ["кошка"], "source": "eki-evs"}

    def test_a_model_gloss_is_shown_as_the_models_never_as_a_sources(self, words, tmp_path):
        assert _glosses(tmp_path, words, _record())["stored"] == 1
        got = dictionary.entry(words, "raamat")
        en = got["meanings"]["en"]
        assert en["words"] == ["book"] and en["source"] is None
        assert (en["model"]["engine"], en["model"]["checker"]) == ("claude-opus-5-5",
                                                                  "claude-haiku-5-5")
        assert {"klint-glosses", "anthropic"} <= {s["id"] for s in got["sources"]}

    def test_a_dictionarys_translation_always_wins_over_the_models(self, words, tmp_path):
        _glosses(tmp_path, words, _record(), _record(lang="uk", gloss=["книга"]))
        store = gloss.connect(tmp_path / "vocab.db", seed_glosses=False)
        gloss.save(store, "raamat", sonapi.WordInfo(
            word="raamat", rection=None, inflection_type="2", definition=None, examples=(),
            translations={"ru": ("книга",), "en": ("book",), "uk": ("книжка",)},
            sense_translations={"ru": ("книга",), "en": ("book",), "uk": ("книжка",)}))
        got = dictionary.entry(words, "raamat", store=store)["meanings"]
        assert got["uk"] == {"words": ["книжка"], "source": "sonapi"}
        assert "model" not in got["en"]

    def test_no_source_and_no_checked_draft_is_no_translation(self, words):
        assert dictionary.entry(words, "kass")["meanings"]["uk"] is None


class TestTheLiveDictionaryKeepsEnglishAndUkrainian:
    def test_ekilex_keeps_each_senses_english_and_ukrainian(self):
        from test_ekilex import _fixture

        got = ekilex.parse(_fixture("maja"))
        assert got.sense_translations["en"][0] == "house"
        assert got.russian[0] == "дом"
        group = lambda lang, *words: {"lang": lang, "synonyms": [  # noqa: E731
            {"type": "MEANING_WORD", "words": [{"wordValue": w} for w in words]},
            {"type": "MEANING_REL", "words": [{"wordValue": "not this sense"}]}]}
        made = ekilex.parse({"word": {"wordValue": "maja"}, "lexemes": [
            {"synonymLangGroups": [group("rus", "дом"), group("ukr", "будинок", "дім")]},
            {"synonymLangGroups": [group("ukr", "хата")]}]})
        assert made.sense_translations["uk"] == ("будинок", "дім", "хата")

    def test_the_mirrors_unnamed_english_list_is_not_stored_as_ekis(self, tmp_path):
        store = gloss.connect(tmp_path / "vocab.db", seed_glosses=False)
        saved = gloss.save(store, "inimene", sonapi.WordInfo(
            word="inimene", rection=None, inflection_type=None, definition=None, examples=(),
            translations={"ru": ("человек",), "en": ("human",)},
            sense_translations={"ru": ("человек",), "uk": ("людина",)}))
        assert saved.english == () and saved.ukrainian == ("людина",)

    def test_an_answer_stored_before_the_languages_is_asked_once_more(self, tmp_path,
                                                                      monkeypatch):
        store = gloss.connect(tmp_path / "vocab.db", seed_glosses=False)
        with store:
            store.execute("INSERT INTO word_gloss (lemma, russian, found, fetched)"
                          " VALUES ('maja', 'дом', 1, '2026-01-01')")
        asked = []

        def answer(word):
            asked.append(word)
            return sonapi.WordInfo(word=word, rection=None, inflection_type=None,
                                   definition=None, examples=(), translations={"ru": ("дом",)},
                                   sense_translations={"ru": ("дом",), "en": ("house",)})

        monkeypatch.setattr(sonapi, "lookup", answer)
        assert gloss.remember(store, "maja").english == ("house",)
        assert gloss.remember(store, "maja").english == ("house",)
        assert asked == ["maja"]


class TestTheImportRechecksEveryLine:
    @pytest.mark.parametrize("bad,why", [
        ({"back": ["hoone"]}, "back-translation"),
        ({"lang": "uk", "gloss": ["сыр", "книга"]}, "Russian letters"),
        ({"checker": "claude-opus-5-5"}, "different model"),
        ({"gloss": ["a book about everything and nothing at all"]}, "too long"),
        ({"lang": "de"}, "unknown language"),
    ])
    def test_a_record_that_fails_a_gate_is_refused(self, words, tmp_path, bad, why):
        assert why in dictionary.check_record(_record(**bad))
        assert _glosses(tmp_path, words, _record(**bad)) == {"stored": 0, "refused": 1}

    def test_a_form_of_the_word_is_agreement(self):
        assert dictionary.agrees("mina", ["ma"])
        assert not dictionary.agrees("mina", ["sina"])

    def test_a_missing_file_empties_the_table(self, words, tmp_path):
        _glosses(tmp_path, words, _record())
        assert dictionary.import_glosses(words, tmp_path / "none.jsonl")["stored"] == 0
        assert dictionary.model_glosses(words, "raamat") == {}


class TestTheCardDrawsTheCredit:
    """Each part is credited to whoever wrote it: crediting EKI under Sõnaveeb's
    wording would be a false statement about who wrote it."""

    def test_a_learner_definition_is_credited_to_ekis_learner_dictionary(self, words):
        from eesti import psv

        psv.store(words, [psv.Entry("raamat", "köidetud lehtede kogum", ("Loen raamatut.",), "s")])
        got = dictionary.entry(words, "raamat")
        assert got["definition"]["source"] == "eki-psv"
        named = {s["id"]: s["name"] for s in got["sources"]}
        assert "põhisõnavara" in named["eki-psv"]

    def test_a_word_psv_does_not_define_names_no_psv(self, words):
        got = dictionary.entry(words, "kass")
        assert got["definition"] is None
        assert "eki-psv" not in {s["id"] for s in got["sources"]}


class TestEveryEntryNamesItsSources:
    def test_each_part_shown_has_its_source(self, words):
        from eesti.licences import REGISTRY

        got = dictionary.entry(words, "raamat")
        ids = {s["id"] for s in got["sources"]}
        assert {"vabamorf", "eki-tasemesonavara", "eki-evs"} <= ids
        known = {s.id for s in REGISTRY} | set(dictionary.OWN)
        assert ids <= known
        assert all(s["name"] and s["what"] for s in got["sources"])


class TestTheRoutes:
    def test_search_and_entry_answer_a_guest(self, client, words):
        guest = {"x-eesti-scope": "guest", "x-eesti-guest": "dict-test"}
        found = client.get("/api/dictionary/search?q=raamatut", headers=guest).json()
        assert found["results"][0]["lemma"] == "raamat"
        got = client.get("/api/dictionary/entry/raamat", headers=guest)
        assert got.status_code == 200 and got.json()["lemma"] == "raamat"

    def test_an_unknown_word_is_a_404_the_learner_can_read(self, client, words):
        got = client.get("/api/dictionary/entry/xqzzy")
        assert got.status_code == 404 and "нет в словарях" in got.json()["detail"]

    def test_the_entry_reports_the_learners_own_review_card(self, client, words):
        assert client.get("/api/dictionary/entry/raamat").json()["in_review"] is False
        assert client.post("/api/mine", json={"word": "raamatut"}).json()["queued"]
        assert client.get("/api/dictionary/entry/raamat").json()["in_review"] is True
