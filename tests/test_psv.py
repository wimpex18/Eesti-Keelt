"""EKI's learner dictionary (PSV).

The parser survives EKI's real XML (which does not validate against its own
schema), and the definitions live in the words database — reference data baked
into the image — separate from the learner's `vocab.db`.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import gloss, psv, wordlist

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<sr>
  <A>
    <P><mg><m>lugema</m>
      <mvt><mvgp><hldf mT="mp3">lugema.mp3</hldf></mvgp></mvt></mg></P>
    <S><tp><grg><sl>v</sl></grg>
      <tg><dg><d>teksti silmadega jälgima ja <i>aru saama</i>, mis seal kirjas on</d></dg>
        <ng><n>Ma loen raamatut.</n><n>Laps õpib lugema.</n>
            <n>Loe see kiri läbi.</n><n>Neljas, mida ei hoita.</n></ng>
      </tg></tp></S>
  </A>
  <A>
    <P><mg><m>raamat</m></mg></P>
    <S><tp><grg><sl>s</sl></grg>
      <tg><dg><d>kokku köidetud lehed, millel on tekst</d></dg>
        <ng><n>Huvitav raamat.</n></ng></tg></tp></S>
  </A>
  <A><P><mg><m>tühi</m></mg></P></A>
  <A><P><mg></mg></P></A>
</sr>
"""


@pytest.fixture
def xml(tmp_path):
    path = tmp_path / "psv_EKI_CCBY40.xml"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


@pytest.fixture
def store(tmp_path):
    """The words database — reference data, baked into the image."""
    return wordlist.connect(tmp_path / "eesti.db")


class TestReadingEkiXml:
    def test_it_finds_the_headwords(self, xml):
        assert [e.lemma for e in psv.parse(xml)] == ["lugema", "raamat", "tühi"]

    def test_an_article_with_no_headword_is_skipped_not_raised(self, xml):
        """EKI warn their own XML does not validate against their schema:
        elements the schema marks required can be absent."""
        assert len(psv.parse(xml)) == 3

    def test_markup_inside_a_definition_is_flattened_not_truncated(self, xml):
        """`.text` stops at the first child, so a definition with an italic
        cross-reference in it would arrive cut off at that word."""
        entry = psv.parse(xml)[0]
        assert entry.definition == (
            "teksti silmadega jälgima ja aru saama, mis seal kirjas on")

    def test_examples_are_capped(self, xml):
        assert len(psv.parse(xml)[0].examples) == psv.MAX_EXAMPLES
        assert "Neljas" not in " ".join(psv.parse(xml)[0].examples)

    def test_a_bare_headword_yields_no_definition_rather_than_empty_string(self, xml):
        assert psv.parse(xml)[2].definition is None


class TestStoring:
    def test_only_articles_with_something_to_say_are_written(self, store, xml):
        stats = psv.store(store, psv.parse(xml))
        assert stats["entries"] == 3
        assert stats["written"] == 2, "the bare headword carries nothing"
        assert psv.imported(store) == 2

    def test_the_definition_and_its_examples_come_back(self, store, xml):
        psv.store(store, psv.parse(xml))
        kept = psv.lookup(store, "raamat")
        assert kept.definition == "kokku köidetud lehed, millel on tekst"
        assert kept.examples == ("Huvitav raamat.",)

    def test_a_word_eki_never_described_is_none_not_an_empty_gloss(self, store, xml):
        psv.store(store, psv.parse(xml))
        assert psv.lookup(store, "helikopter") is None

    def test_importing_twice_changes_nothing(self, store, xml):
        first = psv.store(store, psv.parse(xml))
        again = psv.store(store, psv.parse(xml))
        assert again == first
        assert psv.imported(store) == 2

    def test_a_corrected_file_replaces_what_was_there(self, store, xml):
        psv.store(store, psv.parse(xml))
        # A corrected file is the whole file again, one article reworded.
        corrected = [type(e)(lemma=e.lemma, definition="uus sõnastus",
                             examples=(), pos=e.pos) if e.lemma == "raamat" else e
                     for e in psv.parse(xml)]
        psv.store(store, corrected)
        assert psv.lookup(store, "raamat").definition == "uus sõnastus"
        assert psv.imported(store) == 2, "and nothing was added twice"


class TestReimporting:
    def test_a_lemma_the_new_file_dropped_is_gone(self, store):
        psv.store(store, [psv.Entry("Jäär_", "tähtkuju", (), "S")])
        psv.store(store, [psv.Entry("Jäär", "tähtkuju", (), "S")])
        assert psv.lookup(store, "Jäär_") is None
        assert psv.imported(store) == 1


class TestWhereItLives:
    def test_the_table_exists_before_anything_imports_it(self, store):
        """Absent and zero say different things. A deployment that has never
        seen the file must read as "no definitions", not as a missing table —
        the rule `eesti/vocab.py` already states for the same reason."""
        assert psv.imported(store) == 0
        assert psv.lookup(store, "raamat") is None

    def test_a_words_database_older_than_this_module_degrades_to_nothing(
        self, tmp_path
    ):
        """Opened by something that predates the table, a lookup must return
        "no learner definition", never raise on every word card."""
        conn = sqlite3.connect(tmp_path / "old.db")
        conn.row_factory = sqlite3.Row
        assert psv.lookup(conn, "raamat") is None
        assert psv.imported(conn) == 0

    def test_it_does_not_touch_the_sonaveeb_glosses(self, store, xml, tmp_path):
        """Importing PSV leaves the learner's `vocab.db` untouched."""
        glosses = gloss.connect(tmp_path / "vocab.db", seed_glosses=False)
        gloss.save(glosses, "raamat", _Info())
        psv.store(store, psv.parse(xml))

        kept = gloss.stored(glosses, "raamat")
        assert kept.russian == ("книга",)
        assert kept.definition == "trükitud ja köidetud teos"
        assert psv.lookup(store, "raamat").definition.startswith("kokku")
        assert psv.imported(glosses) == 0, "and nothing was written to vocab.db"


class TestLookingBeforeWriting:
    """`import-psv --check`. The parser has only met a fixture built from the
    schema, so the first run on EKI's real file should report and write nothing."""

    @pytest.fixture(autouse=True)
    def own_database(self, tmp_path, monkeypatch):
        """A database per test. The suite's redirected one is shared, so a
        count of zero after `--check` would otherwise depend on test order."""
        from eesti import config

        monkeypatch.setattr(config, "DB_PATH", tmp_path / "own.db")

    def test_check_reports_and_writes_nothing(self, xml, capsys):
        from eesti.cli import main

        assert main(["import-psv", str(xml), "--check"]) == 0
        out = capsys.readouterr().out
        assert "3 articles" in out and "2 with a definition" in out
        assert "Nothing was written" in out
        assert psv.imported(wordlist.connect()) == 0

    def test_without_check_it_imports(self, xml, capsys):
        from eesti.cli import main

        assert main(["import-psv", str(xml)]) == 0
        assert psv.imported(wordlist.connect()) == 2

    def test_headwords_without_definitions_are_a_refusal(self, tmp_path, capsys):
        """The failure a blind parser is most likely to have on the real file:
        it finds `m` and misses `d`. That must read as "does not fit", not as
        a clean report of zero."""
        from eesti.cli import main

        path = tmp_path / "psv_EKI_CCBY40.xml"
        path.write_text("<sr><A><P><mg><m>lugema</m></mg></P>"
                        "<S><definitsioon>teisiti nimetatud</definitsioon></S></A></sr>",
                        encoding="utf-8")
        assert main(["import-psv", str(path), "--check"]) == 1
        assert "NO DEFINITIONS FOUND" in capsys.readouterr().out
        assert psv.imported(wordlist.connect()) == 0


class _Info:
    """A stand-in for `sonapi.WordInfo` — the fields `gloss.save` reads."""

    russian = ("книга",)
    definition = "trükitud ja köidetud teos"
    rection = "mida"
    inflection_type = "2"


#: Three articles in the real file's shape: no root element, undeclared `c:`
#: prefixes, one article per line, entity codes escaped as `&amp;ba;`.
REAL_SHAPE = (
    '<c:A c:KF="psv1"><c:P><c:mg><c:m c:i="1" c:O="arm1">arm</c:m><c:sl>S</c:sl>'
    '</c:mg></c:P><c:S><c:tp c:tnr="1"><c:tg><c:dg><c:d>paranenud haavast jäänud '
    'jälg</c:d></c:dg><c:ng><c:n>Tal on põse peal suur arm.</c:n></c:ng></c:tg>'
    '</c:tp></c:S></c:A>\n\n'
    '<c:A c:KF="psv1"><c:P><c:mg><c:m c:i="2" c:O="arm2">arm</c:m><c:sl>S</c:sl>'
    '</c:mg></c:P><c:S><c:tp c:tnr="1"><c:tg><c:dg><c:d>see, kui karistus '
    'tühistatakse</c:d></c:dg></c:tg></c:tp></c:S></c:A>\n\n'
    '<c:A c:KF="psv1"><c:P><c:mg><c:sag>1</c:sag><c:m c:O="abivalmis">abivalmis'
    '</c:m><c:sl>A</c:sl></c:mg></c:P><c:S><c:tp c:tnr="1"><c:tg><c:dg><c:d>kui '
    'inimene on &amp;ba;abivalmis&amp;bl;, siis ta tahab sind aidata</c:d></c:dg>'
    '</c:tg></c:tp></c:S></c:A>\n'
)


class TestTheRealFilesShape:
    """What the real file taught, one test per surprise. `psv.parse` failed on
    byte one of it — "unbound prefix: line 1, column 0" — after passing every
    test above, which are written against the schema."""

    @pytest.fixture
    def real(self, tmp_path):
        path = tmp_path / "psv_EKI_CCBY40.xml"
        path.write_text(REAL_SHAPE, encoding="utf-8")
        return path

    def test_undeclared_prefixes_and_no_root_are_read(self, real):
        assert [e.lemma for e in psv.parse(real)] == ["arm", "arm", "abivalmis"]

    def test_entity_codes_are_resolved_not_shown(self, real):
        entry = psv.parse(real)[-1]
        assert entry.definition == "kui inimene on abivalmis, siis ta tahab sind aidata"

    def test_the_commoner_homonym_is_the_one_stored(self, real, store):
        """Tie on `sag` here, so EKI's own numbering decides: `arm` is a scar
        before it is an amnesty. An upsert in file order stored the amnesty."""
        psv.store(store, psv.parse(real))
        assert psv.lookup(store, "arm").definition == "paranenud haavast jäänud jälg"

    def test_a_frequency_tier_beats_file_order(self, tmp_path, store):
        path = tmp_path / "psv.xml"
        path.write_text(
            '<c:A><c:P><c:mg><c:m c:i="1">iga</c:m></c:mg></c:P><c:S><c:tp><c:tg>'
            '<c:dg><c:d>vanus</c:d></c:dg></c:tg></c:tp></c:S></c:A>\n'
            '<c:A><c:P><c:mg><c:sag>1</c:sag><c:m c:i="2">iga</c:m></c:mg></c:P>'
            '<c:S><c:tp><c:tg><c:dg><c:d>üks samasuguste hulgast</c:d></c:dg></c:tg>'
            '</c:tp></c:S></c:A>\n', encoding="utf-8")
        psv.store(store, psv.parse(path))
        assert psv.lookup(store, "iga").definition == "üks samasuguste hulgast"


class TestEkiXmlReader:
    def test_a_compound_boundary_is_removed_and_a_combining_form_skipped(self):
        import xml.etree.ElementTree as ET

        from eesti import ekixml

        assert ekixml.headword(ET.fromstring("<A><m>akordi+kannel</m></A>")) == "akordikannel"
        assert ekixml.headword(ET.fromstring("<A><m>akord+</m></A>")) is None

    def test_or_becomes_a_slash_and_stress_marks_go(self):
        import xml.etree.ElementTree as ET

        from eesti import ekixml

        node = ET.fromstring('<x>аз"ы &amp;v; осн"овы</x>')
        assert ekixml.russian(node) == "азы / основы"

    def test_a_broken_article_is_skipped_not_fatal(self, tmp_path):
        from eesti import ekixml

        path = tmp_path / "x.xml"
        path.write_text("<c:A><c:m>hea</c:m></c:A>\n<c:A><c:m>halb</c:A>\n"
                        "<c:A><c:m>kolmas</c:m></c:A>\n", encoding="utf-8")
        assert [ekixml.text(a.find("m")) for a in ekixml.articles(path)] == ["hea", "kolmas"]
