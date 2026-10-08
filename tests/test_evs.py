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
    '</x:np></x:tp></x:S><x:F><x:fg><x:f>aadressi <x:r>kellele</x:r> täpsustama</x:f>'
    '<x:fqnp><x:fqng xml:lang="ru"><x:qf>уточн"ить "адрес</x:qf><x:vrek>кому</x:vrek>'
    '</x:fqng></x:fqnp></x:fg></x:F></x:A>\n'
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

    def test_estonian_keeps_its_quotation_marks(self, tmp_path):
        path = tmp_path / "evs.xml"
        path.write_text(
            '<x:A><x:P><x:mg><x:m>hinne</x:m></x:mg></x:P><x:S><x:tp><x:np><x:ng>'
            '<x:n>tegi eksami hindele "väga hea"</x:n><x:qnp><x:qng xml:lang="ru">'
            '<x:qn>сдал экз"амен на «отл"ично»</x:qn></x:qng></x:qnp></x:ng></x:np>'
            '</x:tp></x:S></x:A>\n', encoding="utf-8")
        assert evs.parse_examples(path) == [evs.Example(
            "hinne", 'tegi eksami hindele "väga hea"', "сдал экзамен на «отлично»")]

    def test_idioms_are_kept_apart(self, phrases, tmp_path):
        idiom = evs.Example("aadress", "aadressi {kellele} täpsustama", "уточнить адрес",
                            evs.IDIOM)
        assert idiom in phrases
        conn = wordlist.connect(tmp_path / "eesti.db")
        evs.store_examples(conn, phrases)
        assert evs.examples(conn, "aadress", evs.IDIOM) == [
            {"et": "aadressi {kellele} täpsustama", "ru": "уточнить адрес"}]
        assert all(p["et"] != idiom.estonian for p in evs.examples(conn, "aadress"))

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


class TestPhrasePractice:
    """A meaning card in Järjekord shows an EVS phrase, and from the second review
    asks for it to be built from tiles (`review.js`, `wireBuilder`)."""

    @pytest.mark.parametrize("phrase, ok", [
        ("kus sa elad?", True),
        ("lapsed õpivad lugema", True),
        ("hea arst", False),                         # too short to order
        ("kriitika {kelle/mille} aadressil", False),  # an open slot
        ("loeb valjusti / kõvasti", False),          # two answers
        ("lugesin ajalehest, et ...", False),        # unfinished
    ])
    def test_buildable(self, phrase, ok):
        assert evs.buildable(phrase) is ok

    def test_a_different_phrase_each_review_buildable_first(self, tmp_path):
        conn = wordlist.connect(tmp_path / "eesti.db")
        evs.store_examples(conn, [
            evs.Example("lugema", "raamatut lugema", "читать книгу"),
            evs.Example("lugema", "lapsed õpivad lugema", "дети учатся читать"),
            evs.Example("lugema", "loeb lastele muinasjutte", "он читает детям сказки"),
        ])
        seen = [evs.practice_phrase(conn, "lugema", n)["et"] for n in range(3)]
        assert seen == ["lapsed õpivad lugema", "loeb lastele muinasjutte",
                        "lapsed õpivad lugema"]
        assert evs.practice_phrase(conn, "lugema", 0)["build"] is True
        assert evs.practice_phrase(conn, "puudub", 0) is None

    def test_short_phrases_are_shown_but_not_built(self, tmp_path):
        conn = wordlist.connect(tmp_path / "eesti.db")
        evs.store_examples(conn, [evs.Example("hea", "hea arst", "хороший врач")])
        assert evs.practice_phrase(conn, "hea", 4) == {
            "et": "hea arst", "ru": "хороший врач", "build": False}

    def test_the_queue_sends_it_with_meaning_cards_only(self, client, tmp_path, monkeypatch):
        from eesti import config, review

        path = tmp_path / "eesti.db"
        conn = wordlist.connect(path)
        evs.store_examples(conn, [
            evs.Example("lugema", "lapsed õpivad lugema", "дети учатся читать")])
        conn.commit()
        monkeypatch.setattr(config, "DB_PATH", path)
        monkeypatch.setattr(config, "REVIEW_DB", tmp_path / "review.db")
        queue = review.connect(tmp_path / "review.db")
        review.add(queue, kind="vocab", lemma="lugema", prompt="lugema", answer="читать")
        review.add(queue, kind="obj-case", lemma="lugema", prompt="Ma ____ raamatu.",
                   answer="lugesin")
        items = {i["kind"]: i for i in client.get("/api/review").json()["items"]}
        assert items["vocab"]["phrase"]["et"] == "lapsed õpivad lugema"
        assert items["obj-case"]["phrase"] is None


class TestTheCommand:
    def test_check_writes_nothing(self, xml, tmp_path, monkeypatch, capsys):
        from eesti import config
        from eesti.cli import main

        monkeypatch.setattr(config, "DB_PATH", tmp_path / "own.db")
        assert main(["import-evs", str(xml), "--check"]) == 0
        out = capsys.readouterr().out
        assert "3 lemmas with Russian" in out and "1 example phrases and 0 idioms" in out
        assert evs.imported(wordlist.connect()) == 0
        assert main(["import-evs", str(xml)]) == 0
        assert evs.imported(wordlist.connect()) == 3


# Real-shaped homographs (DEV-49): the word a learner meets is EKI's listed one.
def _art(m, pos, *senses, i=None):
    """One EVS article: `senses` are lists of Russian, or (condition, Russian)
    where the condition is the sense's `gki`."""
    tps = []
    for n, sense in enumerate(senses, 1):
        gki, words = sense if isinstance(sense, tuple) else (None, sense)
        xg = "".join(f"<x:xg><x:x>{w}</x:x></x:xg>" for w in words)
        tps.append(f'<x:tp x:tnr="{n}">' + (f"<x:gki>{gki}</x:gki>" if gki else "")
                   + f'<x:tg><x:xp xml:lang="ru">{xg}</x:xp></x:tg></x:tp>')
    number = f' x:i="{i}"' if i else ""
    return (f'<x:A x:KF="ev21"><x:P><x:mg><x:m{number}>{m}</x:m><x:sl>{pos}</x:sl>'
            f'</x:mg></x:P><x:S>{"".join(tps)}</x:S></x:A>\n')


HOMOGRAPHS = (
    _art("siin", "adv", ["здесь", "тут"], ["вот", "это"], i=1)
    + _art("siin", "s", ["шина", "рельс"], i=2)
    + _art("miks", "s", ["микс"])
    + _art("miks", "adv", ["почему", "отчего", "зачем"], ["по какой причине"], i=1)
    + _art("miks", "s", ["почему", "отчего"], i=2)
    + _art("küll", "adv", ["да [же]", "ведь"], ["да"], ["действительно"], i=1)
    + _art("küll", "s", ["обилие", "изобилие"], ["избыток"], i=2)
    + _art("hästi", "adv", ["хорошо", "неплохо"], ("eitusega", ["не очень", "не совсем"]),
           ["очень", "весьма"])
    + _art("iga", "s", ["возраст", "век"], ["стадия"], ["годы"], i=1)
    + _art("iga", "pron", ["каждый", "всякий"], i=2)
    + _art("keegi", "pron", ("jaatavas lauses", ["кто-то"]), ("eitavas lauses", ["никто"]))
    + _art("sugugi", "adv", ("eitusega", ["совсем не", "нисколько не"]))
    + _art("tee", "s", ["дорога", "путь"], ["маршрут"], i=1)
    + _art("tee", "s", ["чай"], i=2)
    # Unlisted: a first sense used with a negation keeps every sense.
    + _art("eales", "adv", ("eitusega", ["никогда", "вовек"]), ["только"])
    # Two nouns and a listed adverb: the adverb is not pushed off the card.
    + _art("vara", "s", ["имущество", "достояние"], ["состояние"], ["добро"], i=1)
    + _art("vara", "s", ["отволока"], ["паз"], i=2)
    + _art("vara", "adv", ["рано"], i=3)
    # Listed as an adjective, but the noun is the word.
    + _art("osaline", "adj", ["-частный", "-составный"])
    + _art("osaline", "s", ["участник", "участница"], ["доля"], ["пайщик"])
    # A definition's lead, not `gki`, says the sense is negated (`kuhugi`).
    + ('<x:A x:KF="ev21"><x:P><x:mg><x:m>kuhugi</x:m><x:sl>adv</x:sl></x:mg></x:P><x:S>'
       '<x:tp x:tnr="1"><x:tg><x:dg><x:d>kuhugi kohta</x:d></x:dg><x:xp xml:lang="ru">'
       '<x:xg><x:x>куда-нибудь</x:x></x:xg></x:xp></x:tg></x:tp><x:tp x:tnr="2"><x:tg>'
       '<x:dg><x:d>eitusega: mitte mingisse kohta</x:d></x:dg><x:xp xml:lang="ru">'
       '<x:xg><x:x>никуда не</x:x></x:xg></x:xp></x:tg></x:tp></x:S></x:A>\n')
)

#: EKI's level list as it is: one row per listed homograph, with its corpus count.
LEVELS = ("LEMMA\tPOS\tSAGEDUS\tTASE\n"
          "siin\tD\t1045852\tA1\nmiks\tD\t691903\tA1\nküll\tD\t1246453\tA1\n"
          "hästi\tD\t580361\tA1\niga\tP\t1445039\tA1\niga\tS\t52111\tA2\n"
          "keegi\tP\t700000\tA1\ntee\tS\t695325\tA1\n"
          "vara\tS\t90000\tA2\nvara\tD\t80000\tA1\nosaline\tA\t5000\tB1\n")


class TestHomographs:
    """`siin` showed «шина», `miks` «микс», `küll` «обилие»: a homograph of
    another part of speech merged into the word the learner met."""

    @pytest.fixture
    def glossed(self, tmp_path):
        xml = tmp_path / "evs_EKI_CCBY40.xml"
        xml.write_text(HOMOGRAPHS, encoding="utf-8")
        levels = tmp_path / "A1A2B1.txt"
        levels.write_text(LEVELS, encoding="utf-8")
        listed = evs.listed_pos(wordlist.read_official_levels(levels))
        return {e.lemma: e for e in evs.parse(xml, listed)}

    @pytest.mark.parametrize("lemma, wrong", [
        ("siin", "шина"), ("miks", "микс"), ("küll", "обилие"), ("küll", "избыток")])
    def test_another_part_of_speech_is_another_word(self, glossed, lemma, wrong):
        assert wrong not in glossed[lemma].russian

    def test_the_listed_homograph_keeps_its_own_senses(self, glossed):
        assert glossed["siin"].russian == ("здесь", "тут", "вот", "это")
        assert glossed["miks"].russian[:3] == ("почему", "отчего", "по какой причине")
        assert glossed["küll"].russian[:3] == ("да [же]", "ведь", "да")

    def test_the_stored_part_of_speech_is_the_listed_one(self, glossed):
        assert glossed["miks"].pos == "adv"

    def test_two_listed_homographs_in_ekis_frequency_order(self, glossed):
        """EKI lists *iga* "every" (P, 1.4M) before *iga* "age" (S, 52k)."""
        assert glossed["iga"].russian[:3] == ("каждый", "всякий", "возраст")
        assert glossed["iga"].pos == "pron"

    def test_homographs_of_one_part_of_speech_still_share_the_card(self, glossed):
        """*tee* is a road and tea; a reading cannot tell them apart."""
        assert glossed["tee"].russian[:3] == ("дорога", "путь", "чай")

    def test_a_sense_used_only_with_negation_is_not_the_meaning(self, glossed):
        """*hästi* is «хорошо»; «не очень» is *ei … hästi*."""
        assert glossed["hästi"].russian == ("хорошо", "неплохо", "очень", "весьма")

    def test_a_negated_sense_named_in_the_definition_goes_too(self, glossed):
        assert glossed["kuhugi"].russian == ("куда-нибудь",)

    def test_a_later_negated_sense_goes_after_an_affirmative_one(self, glossed):
        """*keegi* «кто-то» (in affirmative clauses), not «никто»."""
        assert glossed["keegi"].russian == ("кто-то",)

    @pytest.mark.parametrize("lemma, russian", [
        ("sugugi", ("совсем не", "нисколько не")),
        ("eales", ("никогда", "вовек", "только")),   # not on the list
    ])
    def test_a_word_whose_first_sense_is_negated_keeps_it(self, glossed, lemma, russian):
        assert glossed[lemma].russian == russian

    def test_each_listed_part_of_speech_leads_before_a_second_homograph(self, glossed):
        assert glossed["vara"].russian[:3] == ("имущество", "достояние", "рано")

    def test_a_homograph_richer_than_the_listed_one_stays_last(self, glossed):
        assert glossed["osaline"].russian[:3] == ("-частный", "-составный", "участник")

    def test_an_unlisted_lemma_is_read_as_before(self, tmp_path):
        xml = tmp_path / "evs.xml"
        xml.write_text(HOMOGRAPHS, encoding="utf-8")
        assert evs.parse(xml)[0].russian[:3] == ("здесь", "тут", "шина")

    def test_the_command_reads_the_level_list_beside_the_dictionary(
            self, tmp_path, monkeypatch, capsys):
        from eesti import config
        from eesti.cli import main

        xml = tmp_path / "evs_EKI_CCBY40.xml"
        xml.write_text(HOMOGRAPHS, encoding="utf-8")
        (tmp_path / "A1A2B1.txt").write_text(LEVELS, encoding="utf-8")
        monkeypatch.setattr(config, "DB_PATH", tmp_path / "own.db")
        assert main(["import-evs", str(xml)]) == 0
        assert "шина" not in evs.russian(wordlist.connect(), "siin")
        assert "EKI level list" in capsys.readouterr().out

    def test_a_named_level_list_that_is_missing_stops_the_import(self, tmp_path, monkeypatch):
        from eesti import config
        from eesti.cli import main

        xml = tmp_path / "evs_EKI_CCBY40.xml"
        xml.write_text(HOMOGRAPHS, encoding="utf-8")
        monkeypatch.setattr(config, "DB_PATH", tmp_path / "own.db")
        assert main(["import-evs", str(xml), "--levels", str(tmp_path / "none.txt")]) == 1
        assert evs.imported(wordlist.connect()) == 0

    def test_a_malformed_level_list_still_imports_the_russian(
            self, tmp_path, monkeypatch, capsys):
        """The image build runs `import-evs … || echo`: a bad list must not cost
        every word its Russian."""
        from eesti import config
        from eesti.cli import main

        xml = tmp_path / "evs_EKI_CCBY40.xml"
        xml.write_text(HOMOGRAPHS, encoding="utf-8")
        (tmp_path / "A1A2B1.txt").write_text("not\ta list\n", encoding="utf-8")
        monkeypatch.setattr(config, "DB_PATH", tmp_path / "own.db")
        assert main(["import-evs", str(xml)]) == 0
        assert "every homograph kept" in capsys.readouterr().out.lower()
        assert evs.imported(wordlist.connect()) > 0
