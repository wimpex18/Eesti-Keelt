"""EKI's learner dictionary: definitions written for someone learning the word.

The two behaviours worth pinning are both about *not losing* something:

* a PSV row must not stop `remember()` asking Sõnaveeb, or importing a
  dictionary would strip the Russian translation from the 6 000 commonest
  words — the trap the shipped seed glossary already hit once;
* a Sõnaveeb answer must not overwrite the learner-level definition, or the
  first time a learner opens a card the simple wording is replaced by the
  native-level one and the import has bought nothing.
"""

from __future__ import annotations

import pytest

from eesti import gloss, psv

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
    # No seed: these tests are about this store's own mechanics, and 294 rows
    # nobody put here would only obscure them.
    return gloss.connect(tmp_path / "vocab.db", seed_glosses=False)


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

    def test_the_definition_reaches_a_gloss(self, store, xml):
        psv.store(store, psv.parse(xml))
        kept = gloss.stored(store, "raamat")
        assert kept.simple_definition == "kokku köidetud lehed, millel on tekst"
        assert kept.examples == ("Huvitav raamat.",)

    def test_the_learner_definition_is_what_a_card_shows(self, store, xml):
        psv.store(store, psv.parse(xml))
        assert gloss.stored(store, "raamat").best_definition.startswith("kokku")

    def test_importing_twice_changes_nothing(self, store, xml):
        first = psv.store(store, psv.parse(xml))
        again = psv.store(store, psv.parse(xml))
        assert again == first
        assert psv.imported(store) == 2


class TestItDoesNotLoseWhatIsAlreadyThere:
    def test_a_sonaveeb_answer_survives_the_import(self, store, xml):
        """Rection, muuttüüp and the Russian are things PSV does not have."""
        gloss.save(store, "raamat", _Info())
        psv.store(store, psv.parse(xml))
        kept = gloss.stored(store, "raamat")
        assert kept.russian == ("книга",)
        assert kept.rection == "mida"
        assert kept.inflection_type == "2"
        assert kept.simple_definition.startswith("kokku"), "and it gained PSV's"

    def test_sonaveeb_never_overwrites_the_learner_definition(self, store, xml):
        """The other order, and the one that matters: import first, then the
        learner opens the card and Sõnaveeb answers."""
        psv.store(store, psv.parse(xml))
        gloss.save(store, "raamat", _Info())
        kept = gloss.stored(store, "raamat")
        assert kept.definition == "trükitud ja köidetud teos"   # Sõnaveeb's
        assert kept.simple_definition.startswith("kokku")       # EKI's, intact
        assert kept.best_definition.startswith("kokku")

    def test_a_psv_row_is_a_baseline_not_a_ceiling(self, store, xml):
        """The trap. `remember()` returns early for a row it considers
        complete — so a PSV import would have filled 6 000 rows and denied
        every one of them the Russian translation, for ever."""
        psv.store(store, psv.parse(xml))
        assert gloss._is_baseline(store, "raamat")
        assert psv.SOURCE in gloss.BASELINES

    def test_the_lookup_that_triggered_the_fetch_already_shows_the_simple_one(
        self, store, xml
    ):
        """`save()` returns what the row now holds, not what Sõnaveeb just said.

        The request that triggers a lookup is the request the learner is
        waiting on. Returning the locally-built object would have shown them
        the native-level definition exactly once — on the first view of the
        card — and the learner-level one only if they came back.
        """
        psv.store(store, psv.parse(xml))
        returned = gloss.save(store, "raamat", _Info())
        assert returned.simple_definition.startswith("kokku")
        assert returned.examples == ("Huvitav raamat.",)
        assert returned.best_definition.startswith("kokku")

    def test_a_real_answer_is_not_a_baseline(self, store):
        gloss.save(store, "raamat", _Info())
        assert not gloss._is_baseline(store, "raamat")


class TestTheOldStoreStillOpens:
    def test_a_store_written_before_these_columns_reads_as_no_definition(
        self, tmp_path
    ):
        """`vocab.db` travels in the state snapshot, so a learner can be
        carrying one older than this module. A missing column must degrade to
        "no learner definition", never to an exception on every word card."""
        import sqlite3

        path = tmp_path / "old.db"
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE word_gloss (lemma TEXT PRIMARY KEY, russian TEXT,"
            " definition TEXT, rection TEXT, inflection_type TEXT,"
            " found INTEGER, fetched TEXT)")
        conn.execute(
            "INSERT INTO word_gloss VALUES ('kass','кошка','kodulooma liik',"
            "NULL,NULL,1,'2026-01-01')")
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM word_gloss WHERE lemma='kass'").fetchone()
        kept = gloss._row_to_gloss(row)
        assert kept.simple_definition is None
        assert kept.examples == ()
        assert kept.best_definition == "kodulooma liik"


class _Info:
    """A stand-in for `sonapi.WordInfo` — the fields `gloss.save` reads."""

    russian = ("книга",)
    definition = "trükitud ja köidetud teos"
    rection = "mida"
    inflection_type = "2"
