"""EKI's last-fallback dictionaries: VSL and EKSS (definitions), HAR (Russian).

Fixtures are the real files' shapes, trimmed from real articles (measured
2026-09-13). The order these sit in is the point: they fill a gap only after
the learner-level source and Sõnaveeb have both had nothing.
"""

from __future__ import annotations

import pytest

from eesti import ekidefs, evs, har, psv, wordlist

VSL = (
    '<x:A><x:P><x:mg><x:m x:O="aktiivne">aktiivne</x:m><x:grg><x:sl>A</x:sl>'
    '</x:grg></x:mg></x:P><x:S><x:tp x:tnr="1"><x:dg><x:d>tegev, toimekas</x:d>'
    '</x:dg></x:tp></x:S><x:AA><x:AP><x:amg><x:m x:all="all">aktiivne kaubabilanss'
    '</x:m></x:amg></x:AP><x:AS><x:tp><x:dg><x:d>väljavedu ületab sisseveo</x:d>'
    '</x:dg></x:tp></x:AS></x:AA></x:A>\n\n'
    '<x:A><x:P><x:mg><x:m x:O="ab">ab-</x:m></x:mg></x:P><x:S><x:tp><x:dg><x:d>'
    'eesliide</x:d></x:dg></x:tp></x:S></x:A>\n\n'
    '<x:A><x:P><x:mg><x:m x:O="a_">à_</x:m></x:mg></x:P><x:S><x:tp><x:dg><x:d>'
    'igaüks (kaalu, hinna puhul)</x:d></x:dg></x:tp></x:S></x:A>\n'
)

HAR = (
    '<h:A h:AS="HS"><h:po>SR</h:po><h:P><h:mg><h:v>vah</h:v></h:mg><h:ep><h:terg>'
    '<h:ter h:tyyp="ee" h:O="aabits">aabits</h:ter></h:terg><h:terg><h:ter '
    'h:tyyp="sy">aabitsaraamat</h:ter></h:terg></h:ep></h:P><h:S><h:xp xml:lang="en">'
    '<h:xg><h:x>primer</h:x></h:xg></h:xp><h:xp xml:lang="ru"><h:xg><h:x h:tyyp="sy">'
    'букварь</h:x></h:xg><h:xg><h:x h:tyyp="ee">азбука</h:x></h:xg></h:xp></h:S></h:A>\n'
)


@pytest.fixture
def files(tmp_path):
    vsl, har_ = tmp_path / "vsl.xml", tmp_path / "har.xml"
    vsl.write_text(VSL, encoding="utf-8")
    har_.write_text(HAR, encoding="utf-8")
    return vsl, har_


class TestReading:
    def test_vsl_takes_the_article_definition_not_a_phrase_subentry(self, files):
        got = ekidefs.parse(files[0])
        assert got["aktiivne"] == "tegev, toimekas"

    def test_vsl_skips_affixes_and_keeps_homograph_marked_words(self, files):
        got = ekidefs.parse(files[0])
        assert "ab" not in got and "ab-" not in got
        assert got["à"] == "igaüks (kaalu, hinna puhul)"

    def test_har_maps_every_term_to_its_russian_and_only_russian(self, files):
        got = har.parse(files[1])
        assert got["aabits"] == ("букварь", "азбука")
        assert got["aabitsaraamat"] == ("букварь", "азбука"), "synonyms too"

    def test_a_gzipped_file_reads_the_same(self, files, tmp_path):
        import gzip

        packed = tmp_path / "har.xml.gz"
        packed.write_bytes(gzip.compress(files[1].read_bytes()))
        assert har.parse(packed) == har.parse(files[1])


class TestTheFallbackOrder:
    """Learner-level first, Sõnaveeb second, these last — for both fields."""

    @pytest.fixture
    def words_db(self, files, tmp_path, monkeypatch):
        from eesti import config

        path = tmp_path / "eesti.db"
        conn = wordlist.connect(path)
        ekidefs.store(conn, "eki-vsl", ekidefs.parse(files[0]))
        har.store(conn, har.parse(files[1]))
        # A word both PSV and VSL describe, and one both EVS and HAR translate.
        psv.store(conn, [psv.Entry("aktiivne", "tegutsev", (), "A")])
        evs.store(conn, [evs.Entry("aabits", "s", ("азбука",))])
        conn.commit()
        monkeypatch.setattr(config, "DB_PATH", path)
        monkeypatch.setattr(config, "VOCAB_DB", tmp_path / "vocab.db")
        # Sõnaveeb has nothing — the case these fallbacks exist for — and no
        # test reaches its server.
        from eesti import gloss

        monkeypatch.setattr(gloss, "remember", lambda conn, lemma: None)
        return path

    def test_psv_beats_vsl(self, client, words_db):
        got = client.get("/api/enrich/aktiivne").json()
        assert (got["definition"], got["definition_source"]) == ("tegutsev", "eki-psv")

    def test_vsl_answers_when_nothing_before_it_did(self, client, words_db):
        got = client.get("/api/enrich/à").json()
        assert got["definition_source"] == "eki-vsl"
        assert got["found"] is True, "a word only VSL knows must still show"

    def test_evs_beats_har(self, client, words_db):
        got = client.get("/api/enrich/aabits").json()
        assert got["russian_source"] == "eki-evs"

    def test_har_answers_when_nothing_before_it_did(self, client, words_db):
        got = client.get("/api/enrich/aabitsaraamat").json()
        assert got["russian_source"] == "eki-har"
        assert got["russian"] == ["букварь", "азбука"]


class TestLabels:
    def test_har_drops_a_translation_eki_call_wrong(self, tmp_path):
        path = tmp_path / "har.xml"
        path.write_text(
            '<h:A><h:P><h:ep><h:terg><h:ter h:tyyp="ee">hinne</h:ter></h:terg></h:ep></h:P>'
            '<h:S><h:xp xml:lang="ru"><h:xg><h:x>балл</h:x><h:s>halb</h:s></h:xg>'
            '<h:xg><h:x>оценка</h:x></h:xg></h:xp></h:S></h:A>\n', encoding="utf-8")
        assert har.parse(path)["hinne"] == ("оценка",)

    def test_vsl_prefers_a_current_sense_to_an_archaic_first_one(self, tmp_path):
        path = tmp_path / "vsl.xml"
        path.write_text(
            '<x:A><x:P><x:mg><x:m>kontor</x:m></x:mg></x:P><x:S><x:tp><x:dg><x:s>van</x:s>'
            '<x:d>kirjutuslaud</x:d></x:dg><x:dg><x:d>asutuse tööruum</x:d></x:dg></x:tp>'
            '</x:S></x:A>\n', encoding="utf-8")
        assert ekidefs.parse(path)["kontor"] == "asutuse tööruum"


class TestEveryFlowAsksTheSamePlace:
    """The Russian order was copied into three flows and missing from two.
    Each is checked against `meaning.py` with one word only EVS knows."""

    @pytest.fixture
    def evs_only(self, tmp_path, monkeypatch):
        from eesti import config, gloss

        path = tmp_path / "eesti.db"
        conn = wordlist.connect(path)
        evs.store(conn, [evs.Entry("tugitool", "s", ("кресло", "стул"))])
        conn.commit()
        monkeypatch.setattr(config, "DB_PATH", path)
        monkeypatch.setattr(config, "VOCAB_DB", tmp_path / "vocab.db")
        monkeypatch.setattr(gloss, "remember", lambda conn, lemma: None)
        return path

    def test_the_vocabulary_list_shows_it(self, evs_only):
        from eesti import gloss, vocab

        store = gloss.connect(evs_only.parent / "vocab.db")
        assert vocab._glosses(wordlist.connect(), store, ["tugitool"]) == {"tugitool": "кресло, стул"}

    def test_a_meaning_flashcard_can_be_made_from_it(self, evs_only):
        """It refused with "перевод пока неизвестен" while Sõnaveeb's store was
        the only place it looked."""
        from eesti import mining, review

        conn = review.connect(evs_only.parent / "review.db")
        got = mining._meaning_card(conn, "tugitool", "See on tugitool.")
        assert got.queued and got.kind == "vocab", got.reason
        answer = conn.execute("SELECT answer FROM review_items WHERE id = ?",
                              (got.item_id,)).fetchone()[0]
        assert answer == "кресло, стул"


class TestTheSeedIsNotOverruled:
    def test_a_drill_word_keeps_its_hand_written_gloss(self, tmp_path):
        """EVS's first sense of `palk` is a log; the drill means a salary."""
        from eesti import meaning

        conn = wordlist.connect(tmp_path / "eesti.db")
        evs.store(conn, [evs.Entry("palk", "s", ("бревно", "заработная плата"))])
        assert "palk" in meaning._seed(), "the fixture word must be a seeded one"
        found, source = meaning.russian(conn, "palk")
        assert source == "seed" and "бревно" not in found[0]
        assert meaning.russian_many(conn, None, ["palk"])["palk"] == found


class TestTheCard:
    def test_each_eki_source_is_credited_under_its_own_guard(self):
        from pathlib import Path

        card = (Path(__file__).resolve().parents[1] / "eesti" / "web" / "js"
                / "vocab.js").read_text(encoding="utf-8")
        for guard, credit in (('russian_source === "eki-har"', "EKI haridussõnastik"),
                              ('definition_source === "eki-vsl"', "EKI võõrsõnade leksikon"),
                              ('definition_source === "eki-ekss"', "EKI eesti keele seletav")):
            assert 0 < card.index(credit) - card.index(guard) < 200, guard


class TestTheOrderLivesInOnePlace:
    def test_no_module_but_meaning_reads_the_russian_tables(self):
        """The order was copied into three flows and forgotten in two. A flow
        that reads `evs`/`har` itself has started a sixth copy."""
        import re
        from pathlib import Path

        pkg = Path(__file__).resolve().parents[1] / "eesti"
        allowed = {"meaning.py", "evs.py", "har.py"}
        offenders = [
            str(p.relative_to(pkg)) for p in pkg.rglob("*.py")
            if p.name not in allowed
            and re.search(r"\b(evs|har)\.russian(_many)?\(|from \.+(evs|har) import russian",
                          p.read_text(encoding="utf-8"))
        ]
        assert not offenders, offenders


class TestHeadwordMarks:
    """Every mark a real file uses, one case each (measured 2026-09-13)."""

    @pytest.mark.parametrize("raw, lemmas", [
        ("tehase|märk", ["tehasemärk"]),          # EKSS, 28 276
        ("\\sae\\pakk", ["saepakk"]),             # EKSS, 58 814
        ("akordi+kannel", ["akordikannel"]),      # EVS
        ("ainuke[ne]", ["ainukene", "ainuke"]),   # EVS optional ending
        ("(kindel) kui ~ nagu aamen kirikus", []),  # EKSS phrase entry
        ("-keelne", []), ("akord+", []),          # affix, combining form
        ("Vähk_", ["Vähk"]),                      # homograph mark
    ])
    def test_marks(self, raw, lemmas):
        import xml.etree.ElementTree as ET

        from eesti import ekixml

        node = ET.Element("A")
        ET.SubElement(node, "m").text = raw
        assert ekixml.headwords(node) == lemmas


class TestTheCardFromEkiAndTheLiveDictionary:
    """Rektsioon and muuttüüp from EKI's files when the live dictionary has
    none — and the live dictionary is always asked, because it is current."""

    @pytest.fixture
    def words_db(self, tmp_path, monkeypatch):
        from eesti import config, gloss

        path = tmp_path / "eesti.db"
        conn = wordlist.connect(path)
        psv.store(conn, [
            psv.Entry("tugitool", "mugav tool", (), "S"),
            psv.Entry("sõltuma", "olema mõjutatud", (), "V", rection=("kellest-millest",)),
        ])
        evs.store(conn, [evs.Entry("tugitool", "s", ("кресло",), "1"),
                         evs.Entry("sõltuma", "v", ("зависеть",), "27")])
        ekidefs.store(conn, "eki-ekss", {"tugitool": "käetugedega pehme tool"})
        conn.commit()
        monkeypatch.setattr(config, "DB_PATH", path)
        monkeypatch.setattr(config, "VOCAB_DB", tmp_path / "vocab.db")
        asked = []
        monkeypatch.setattr(gloss, "remember", lambda conn, lemma: asked.append(lemma))
        return asked

    def test_the_live_dictionary_is_asked_even_when_eki_covers_the_word(self, client, words_db):
        got = client.get("/api/enrich/tugitool").json()
        assert words_db == ["tugitool"]
        assert (got["definition"], got["russian"], got["inflection_type"]) == \
            ("mugav tool", ["кресло"], "1")

    def test_with_nothing_live_the_card_uses_ekis_rection_and_type(self, client, words_db):
        got = client.get("/api/enrich/sõltuma").json()
        assert got["governs"] == ["kellest-millest"]
        assert got["governs_source"] == "eki-psv"
        assert got["inflection_type"] == "27"

    def test_the_fuller_wording_is_offered_from_ekss_when_live_has_none(self, client, words_db):
        got = client.get("/api/enrich/tugitool").json()
        assert got["full_definition"] == "käetugedega pehme tool"
        assert got["full_definition_source"] == "eki-ekss"


class TestTheFullerWordingNeverRepeatsTheCard:
    def test_a_joined_live_definition_is_split_and_the_learner_one_dropped(self):
        from eesti.api.grammar import _without

        psv_text = "rõhutab, et miski on just nii, nagu sa ütled"
        live = "(päris) kindlasti," + psv_text
        assert _without(live, psv_text) == "(päris) kindlasti"
        assert _without(psv_text, psv_text) is None


class TestTheLiveGlossOutranksEvs:
    def test_a_stored_live_gloss_beats_the_snapshot(self, tmp_path):
        from eesti import meaning

        conn = wordlist.connect(tmp_path / "eesti.db")
        evs.store(conn, [evs.Entry("tugitool", "s", ("кресло-качалка",))])
        assert meaning.russian(conn, "tugitool", ("кресло",)) == (["кресло"], "sonapi")
        assert meaning.russian(conn, "tugitool") == (["кресло-качалка"], "eki-evs")


class TestTheCardDrawsTheFullerWording:
    def test_it_is_drawn_folded_and_credited(self):
        from pathlib import Path

        card = (Path(__file__).resolve().parents[1] / "eesti" / "web" / "js"
                / "vocab.js").read_text(encoding="utf-8")
        assert "x.full_definition" in card
        assert "täpsem seletus" in card and "full_definition_source" in card


class TestOlderTablesGainTheirColumns:
    def test_a_psv_table_without_rection_is_migrated_on_import(self, tmp_path):
        import sqlite3

        path = tmp_path / "old.db"
        raw = sqlite3.connect(path)
        raw.execute("CREATE TABLE psv_gloss (lemma TEXT PRIMARY KEY, definition TEXT, examples TEXT)")
        raw.commit()
        psv.store(raw, [psv.Entry("sõltuma", "x", (), "V", rection=("millest",))])
        assert psv.lookup(raw, "sõltuma").rection == ("millest",)


class TestInflectionTypeAsTheCardShowsIt:
    @pytest.mark.parametrize("raw, shown", [
        ("02", "2"), ("17", "17"), ("11_&_09", "11 / 9"), ("12_&_10?", None), ("", None),
    ])
    def test_evs_types_are_normalised(self, raw, shown):
        assert evs._inflection_type(raw) == shown
