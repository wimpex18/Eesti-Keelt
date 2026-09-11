"""EKI's learner dictionary: definitions written for someone learning the word.

Two things are worth pinning, and the second is the one that moved.

* The parser has to survive EKI's own XML, which they warn does not validate
  against the schema they publish for it.
* The store has to be somewhere a Cloud Run cold start cannot empty. It began
  in `vocab.db` beside the Sõnaveeb glosses, which was wrong twice over: that
  file is carried by the **state snapshot** and a restore replaces it whole, so
  six thousand reference definitions would have survived until the first
  restore and then vanished; and sharing a row with `word_gloss` meant every
  write had to be careful not to overwrite the other source. Its own table in
  the words database — the one baked into the image — dissolves both. The
  tests that used to guard the sharing are gone with the sharing; what is left
  is a test that says the two stores do not touch.
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
        fixed = [e for e in psv.parse(xml) if e.lemma == "raamat"]
        psv.store(store, [type(fixed[0])(lemma="raamat", definition="uus sõnastus",
                                         examples=(), pos="s")])
        assert psv.lookup(store, "raamat").definition == "uus sõnastus"
        assert psv.imported(store) == 2, "and nothing was added twice"


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
        """The two stores are separate files with separate lifetimes: this one
        ships in the image, `vocab.db` travels in the state snapshot. Importing
        the dictionary must leave the learner's store alone — and, the way the
        sharing used to fail, must not deny those 6 000 words their Russian."""
        glosses = gloss.connect(tmp_path / "vocab.db", seed_glosses=False)
        gloss.save(glosses, "raamat", _Info())
        psv.store(store, psv.parse(xml))

        kept = gloss.stored(glosses, "raamat")
        assert kept.russian == ("книга",)
        assert kept.definition == "trükitud ja köidetud teos"
        assert psv.lookup(store, "raamat").definition.startswith("kokku")
        assert psv.imported(glosses) == 0, "and nothing was written to vocab.db"


class _Info:
    """A stand-in for `sonapi.WordInfo` — the fields `gloss.save` reads."""

    russian = ("книга",)
    definition = "trükitud ja köidetud teos"
    rection = "mida"
    inflection_type = "2"
