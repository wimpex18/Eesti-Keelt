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


class TestTheCard:
    def test_each_eki_source_is_credited_under_its_own_guard(self):
        from pathlib import Path

        card = (Path(__file__).resolve().parents[1] / "eesti" / "web" / "js"
                / "vocab.js").read_text(encoding="utf-8")
        for guard, credit in (('russian_source === "eki-har"', "EKI haridussõnastik"),
                              ('definition_source === "eki-vsl"', "EKI võõrsõnade leksikon"),
                              ('definition_source === "eki-ekss"', "EKI eesti keele seletav")):
            assert 0 < card.index(credit) - card.index(guard) < 200, guard
