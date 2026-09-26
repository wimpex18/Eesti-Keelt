"""EKI's Estonian–Russian dictionary: the Russian on a word card, offline.

The fixture follows `evs_EKI_CCBY40.xml`'s shape, trimmed from real articles: no
root, undeclared `x:` prefixes, `xml:lang="ru"` translations, stress `"`,
perfective `*`, `&amp;v;` for "or", `_` for "no single-word translation", and
homonyms as separate articles.
"""

from __future__ import annotations

import pathlib

import pytest

from eesti import evs, wordlist

ROOT = pathlib.Path(__file__).resolve().parents[1]

REAL_SHAPE = (
    '<x:A x:KF="ev21"><x:P><x:mg><x:m x:i="1" x:O="iga1">iga</x:m><x:sl>s</x:sl>'
    '</x:mg></x:P><x:S><x:tp x:tnr="1"><x:tg><x:dg><x:d>eluiga</x:d></x:dg>'
    '<x:xp xml:lang="ru"><x:xg><x:x>в"озраст</x:x></x:xg><x:xg><x:x>век</x:x>'
    '</x:xg><x:xg><x:x>г"оды</x:x></x:xg></x:xp></x:tg><x:np><x:ng><x:n>küps iga'
    '</x:n><x:qnp><x:qng xml:lang="ru"><x:qn>зр"елый в"озраст</x:qn></x:qng>'
    '</x:qnp></x:ng></x:np></x:tp></x:S></x:A>\n\n'
    '<x:A x:KF="ev21"><x:P><x:mg><x:m x:i="2" x:O="iga2">iga</x:m><x:sl>pron</x:sl>'
    '</x:mg></x:P><x:S><x:tp x:tnr="1"><x:tg><x:xp xml:lang="ru"><x:xg><x:x>'
    'к"аждый</x:x></x:xg></x:xp></x:tg></x:tp></x:S></x:A>\n\n'
    '<x:A x:KF="ev21"><x:P><x:mg><x:m x:O="hea">hea</x:m><x:sl>adj</x:sl></x:mg>'
    '</x:P><x:S><x:tp x:tnr="1"><x:tg><x:xp xml:lang="ru"><x:xg><x:x>хор"оший'
    '</x:x></x:xg><x:xg><x:x>благ"ой</x:x><x:s>van</x:s></x:xg></x:xp></x:tg>'
    '</x:tp></x:S></x:A>\n\n'
    '<x:A x:KF="ev21"><x:P><x:mg><x:m x:O="abielluma">abielluma</x:m></x:mg></x:P>'
    '<x:S><x:tp x:tnr="1"><x:tg><x:xp xml:lang="ru"><x:xg><x:x>_</x:x></x:xg>'
    '<x:xg><x:x>жен"иться[*]</x:x></x:xg><x:xg><x:x>вступ"ать/вступ"ить* в брак'
    '</x:x></x:xg></x:xp></x:tg></x:tp></x:S></x:A>\n\n'
    '<x:A x:KF="ev21"><x:P><x:mg><x:m x:O="akord+">akord+</x:m></x:mg></x:P>'
    '<x:S><x:tp><x:tg><x:xp xml:lang="ru"><x:xg><x:x>акк"орд</x:x></x:xg></x:xp>'
    '</x:tg></x:tp></x:S></x:A>\n'
)


@pytest.fixture
def xml(tmp_path):
    path = tmp_path / "evs_EKI_CCBY40.xml"
    path.write_text(REAL_SHAPE, encoding="utf-8")
    return path


@pytest.fixture
def entries(xml):
    return {e.lemma: e for e in evs.parse(xml)}


class TestReadingTheRealShape:
    def test_homonyms_merge_into_one_lemma(self, entries):
        assert set(entries) == {"iga", "hea", "abielluma"}

    def test_another_homonym_gets_a_slot_on_a_three_slot_card(self, entries):
        """Three words for "age" must not push "every" off the card."""
        assert entries["iga"].russian[:3] == ("возраст", "век", "каждый")

    def test_marks_are_stripped_and_placeholders_skipped(self, entries):
        assert entries["abielluma"].russian == ("жениться", "вступать/вступить в брак")

    def test_a_question_hint_is_not_part_of_the_word(self):
        import xml.etree.ElementTree as ET

        from eesti import ekixml

        assert ekixml.russian(ET.fromstring('<x><xr>какой</xr>телеф"он</x>')) == "телефон"

    def test_archaic_translations_are_dropped(self, entries):
        assert entries["hea"].russian == ("хороший",)

    def test_example_translations_are_not_glosses(self, entries):
        assert "зрелый возраст" not in entries["iga"].russian

    def test_a_combining_form_is_not_a_word(self, entries):
        assert "akord" not in entries


class TestWhatComesFirst:
    """Ordering rules from `evs_tyybid.xsd`, checked on real-shaped articles."""

    @staticmethod
    def _parse(tmp_path, body):
        path = tmp_path / "evs.xml"
        path.write_text(body, encoding="utf-8")
        return {e.lemma: e.russian for e in evs.parse(path)}

    def test_an_also_label_does_not_mark_a_translation(self, tmp_path):
        """`<s l="ka">piltl</s>` is "also figurative"; counting it pushed
        `читать` off `lugema` on the real file."""
        got = self._parse(tmp_path,
            '<x:A><x:P><x:mg><x:m>lugema</x:m></x:mg></x:P><x:S><x:tp><x:tg>'
            '<x:xp xml:lang="ru"><x:xg><x:x>чит"ать</x:x><x:s x:l="ka">piltl</x:s>'
            '</x:xg></x:xp></x:tg><x:tg><x:xp xml:lang="ru"><x:xg><x:x>доч"итывать'
            '</x:x></x:xg></x:xp></x:tg></x:tp></x:S></x:A>\n')
        assert got["lugema"][0] == "читать"

    def test_a_colloquial_translation_never_comes_first(self, tmp_path):
        got = self._parse(tmp_path,
            '<x:A><x:P><x:mg><x:m>poiss</x:m></x:mg></x:P><x:S><x:tp><x:tg>'
            '<x:xp xml:lang="ru"><x:xg><x:x>мальч"ишка</x:x><x:s>kõnek</x:s></x:xg>'
            '<x:xg><x:x>м"альчик</x:x></x:xg></x:xp></x:tg></x:tp></x:S></x:A>\n')
        assert got["poiss"] == ("мальчик", "мальчишка")

    def test_the_main_sense_leads_over_a_later_senses_neutral_word(self, tmp_path):
        """`poiss` is a boy. Taking one neutral word from every sense in turn put
        its interjection sense, "смотри", third on the card."""
        body = ('<x:A><x:P><x:mg><x:m>poiss</x:m></x:mg></x:P><x:S>'
                '<x:tp x:tnr="1"><x:tg><x:xp xml:lang="ru">'
                '<x:xg><x:x>м"альчик</x:x></x:xg><x:xg><x:x>мальч"ишка</x:x><x:s>kõnek</x:s></x:xg>'
                '</x:xp></x:tg></x:tp>'
                '<x:tp x:tnr="2"><x:tg><x:xp xml:lang="ru"><x:xg><x:x>подр"осток</x:x></x:xg>'
                '</x:xp></x:tg></x:tp>'
                '<x:tp x:tnr="3"><x:tg><x:xp xml:lang="ru"><x:xg><x:x>смотр"и</x:x></x:xg>'
                '</x:xp></x:tg></x:tp></x:S></x:A>\n')
        assert self._parse(tmp_path, body)["poiss"][:3] == ("мальчик", "мальчишка", "подросток")

    def test_the_homonym_with_more_senses_leads(self, tmp_path):
        """`suu` is a mouth before it is a sou, whatever EKI's numbering."""
        sou = ('<x:A><x:P><x:mg><x:m x:i="1">suu</x:m></x:mg></x:P><x:S><x:tp><x:tg>'
               '<x:xp xml:lang="ru"><x:xg><x:x>су</x:x></x:xg></x:xp></x:tg></x:tp></x:S></x:A>\n')
        mouth = ('<x:A><x:P><x:mg><x:m x:i="2">suu</x:m></x:mg></x:P><x:S><x:tp>'
                 + "".join(f'<x:tg><x:xp xml:lang="ru"><x:xg><x:x>{w}</x:x></x:xg></x:xp></x:tg>'
                           for w in ("рот", "устье", "отверстие")) + '</x:tp></x:S></x:A>\n')
        assert self._parse(tmp_path, sou + mouth)["suu"][:3] == ("рот", "устье", "су")


class TestStoring:
    def test_round_trip_and_idempotent(self, xml, tmp_path):
        conn = wordlist.connect(tmp_path / "eesti.db")
        evs.store(conn, evs.parse(xml))
        evs.store(conn, evs.parse(xml))
        assert evs.imported(conn) == 3
        assert evs.russian(conn, "hea") == ("хороший",)
        assert evs.russian_many(conn, ["hea", "puudub"]) == {"hea": ["хороший"]}

    def test_a_database_that_never_imported_answers_empty(self, tmp_path):
        import sqlite3

        conn = sqlite3.connect(tmp_path / "bare.db")
        assert evs.russian(conn, "hea") == ()
        assert evs.imported(conn) == 0


class TestTheCardPrefersEki:
    @pytest.fixture
    def words_db(self, xml, tmp_path, monkeypatch):
        from eesti import config

        path = tmp_path / "eesti.db"
        conn = wordlist.connect(path)
        evs.store(conn, evs.parse(xml))
        conn.commit()
        monkeypatch.setattr(config, "DB_PATH", path)
        monkeypatch.setattr(config, "VOCAB_DB", tmp_path / "vocab.db")
        from eesti import gloss

        monkeypatch.setattr(gloss, "remember", lambda conn, lemma: None)
        return path

    def test_eki_russian_is_served_and_named(self, client, words_db):
        got = client.get("/api/enrich/hea").json()
        assert got["found"] is True, "a word only EVS knows must still show"
        assert got["russian"] == ["хороший"]
        assert got["russian_source"] == "eki-evs"

    def test_no_russian_names_no_source(self, client, words_db):
        got = client.get("/api/enrich/helikopterxyz").json()
        assert got["russian_source"] is None and got["russian"] == []

    def test_drill_glosses_use_it_offline(self, words_db):
        from eesti.api.render import _glosses_for

        assert _glosses_for(["iga"])["iga"] == ["возраст", "век", "каждый"]

    def test_the_card_credits_eki_only_when_eki_answered(self):
        card = (ROOT / "eesti" / "web" / "js" / "vocab.js").read_text(encoding="utf-8")
        guard = card.index('russian_source === "eki-evs"')
        credit = card.index("EKI eesti-vene sõnaraamat", guard)
        assert 0 < credit - guard < 200


EXAMPLES = (
    '<x:A x:KF="ev21"><x:P><x:mg><x:m x:O="aadress">aadress</x:m><x:sl>s</x:sl>'
    '</x:mg></x:P><x:S><x:tp x:tnr="1"><x:tg><x:xp xml:lang="ru"><x:xg><x:x>'
    '"адрес</x:x></x:xg></x:xp></x:tg><x:np>'
    '<x:ng><x:n>saatja aadress</x:n><x:qnp><x:qng xml:lang="ru"><x:qn>"адрес '
    'отправ"ителя</x:qn></x:qng><x:qng xml:lang="ru"><x:qn>обр"атный "адрес</x:qn>'
    '</x:qng><x:qng xml:lang="ru"><x:qn>тр"етий</x:qn></x:qng></x:qnp></x:ng>'
    '<x:ng><x:n>kriitika <x:r>kelle/mille</x:r> aadressil</x:n><x:qnp>'
    '<x:qng xml:lang="ru"><x:qn>кр"итика в <x:xr>чей</x:xr> "адрес</x:qn>'
    '<x:vrek>кого</x:vrek></x:qng></x:qnp></x:ng>'
    '<x:ng><x:n w="nn">aadressbüroo</x:n><x:qnp><x:v>aj</x:v><x:qng xml:lang="ru">'
    '<x:qn>адр"есное бюр"о</x:qn></x:qng></x:qnp></x:ng>'
    '<x:ng><x:n>vana aadress</x:n><x:qnp><x:qng xml:lang="ru"><x:qn>стар"инный '
    '"адрес</x:qn><x:s>van</x:s></x:qng></x:qnp></x:ng>'
    '</x:np></x:tp></x:S></x:A>\n'
)


class TestExamplePhrases:
    """EVS's example phrases, each with its Russian: the word card's *Näited*."""

    @pytest.fixture
    def phrases(self, tmp_path):
        path = tmp_path / "evs.xml"
        path.write_text(REAL_SHAPE + EXAMPLES, encoding="utf-8")
        return evs.parse_examples(path)

    def test_a_phrase_keeps_its_russian_without_marks(self, phrases):
        assert evs.Example("iga", "küps iga", "зрелый возраст") in phrases

    def test_two_renderings_at_most(self, phrases):
        got = next(p for p in phrases if p.estonian == "saatja aadress")
        assert got.russian == "адрес отправителя; обратный адрес"

    def test_an_open_slot_is_kept_in_braces(self, phrases):
        got = next(p for p in phrases if "kriitika" in p.estonian)
        assert got.estonian == "kriitika {kelle/mille} aadressil"
        assert got.russian == "критика в {чей} адрес"

    def test_domain_terms_and_archaic_renderings_are_left_out(self, phrases):
        shown = {p.estonian for p in phrases}
        assert "aadressbüroo" not in shown and "vana aadress" not in shown

    def test_stored_in_ekis_order_and_served(self, phrases, tmp_path):
        conn = wordlist.connect(tmp_path / "eesti.db")
        evs.store_examples(conn, phrases)
        evs.store_examples(conn, phrases)
        assert [p["et"] for p in evs.examples(conn, "aadress")] == [
            "saatja aadress", "kriitika {kelle/mille} aadressil"]
        assert evs.examples(conn, "puudub") == []

    def test_a_database_that_never_imported_answers_empty(self, tmp_path):
        assert evs.examples(wordlist.connect(tmp_path / "empty.db"), "iga") == []

    def test_the_word_card_gets_them_credited(self, client, tmp_path, monkeypatch, phrases):
        from eesti import config, gloss

        path = tmp_path / "eesti.db"
        conn = wordlist.connect(path)
        evs.store_examples(conn, phrases)
        conn.commit()
        monkeypatch.setattr(config, "DB_PATH", path)
        monkeypatch.setattr(config, "VOCAB_DB", tmp_path / "vocab.db")
        monkeypatch.setattr(gloss, "remember", lambda conn, lemma: None)
        got = client.get("/api/enrich/iga").json()
        assert got["found"] is True
        assert got["phrases"] == [{"et": "küps iga", "ru": "зрелый возраст"}]
        assert got["phrases_source"] == "eki-evs"
        card = (ROOT / "eesti" / "web" / "js" / "vocab.js").read_text(encoding="utf-8")
        assert "näited: EKI eesti-vene sõnaraamat · CC BY 4.0" in card


class TestTheCommand:
    def test_check_writes_nothing(self, xml, tmp_path, monkeypatch, capsys):
        from eesti import config
        from eesti.cli import main

        monkeypatch.setattr(config, "DB_PATH", tmp_path / "own.db")
        assert main(["import-evs", str(xml), "--check"]) == 0
        out = capsys.readouterr().out
        assert "3 lemmas with Russian" in out and "1 example phrases" in out
        assert evs.imported(wordlist.connect()) == 0
        assert main(["import-evs", str(xml)]) == 0
        assert evs.imported(wordlist.connect()) == 3
