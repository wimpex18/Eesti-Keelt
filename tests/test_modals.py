"""Which infinitive a modal verb takes (`eesti/modals.py`): read off EKI EVS's
phrases, never written down, and drilled only where EVS shows one.

What a learner would notice if these broke: *saan minema* marked right, *saab
olema* graded at all, an idiom (*saan hakkama*) taught as modal + infinitive, or
a gap whose answer the phrase's own Estonian does not fix.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import evs, modals
from eesti.modals import GOVERNORS, Pair

#: Phrases from EKI EVS (CC BY 4.0), as `cli import-evs` stores them, then
#: EKK SÜ 28's examples of the saama-future (the first shortened), which must
#: never be evidence or an item.
PHRASES = (
    ("ehmatama", "teda ei tohi ehmatada"),
    ("asendama", "naelad peab asendama kruvidega"),
    ("muutuma", "ilm võib muutuda üleöö"),
    ("printima", "teksti saab printida erineva reavahega"),
    ("hakkama", "saan hakkama ilma eestkostjateta"),       # an idiom, not saama + ma
    ("lõhkuma", "hobune kardab autot, võib lõhkuma minna"),  # lõhkuma belongs to minna
    ("vaikima", "ma pidasin paremaks vaikida"),            # not right after pidama
    ("toimuma", "homme saab siin toimuma ühisistung"),
    ("olema", "elu saab seal olema raske"),
)
IDIOMS = (("hakkama", "hakkama saama"),)
VERBS = ("ehmatama", "asendama", "muutuma", "printima", "hakkama", "lõhkuma",
         "vaikima", "toimuma", "olema", "minema")


def evs_words(path, phrases=PHRASES, idioms=IDIOMS, verbs=VERBS, level="A2"):
    from eesti.wordlist import SCHEMA

    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO words(word, freq_rank, proficiency, pos) VALUES (?,?,?,?)",
                     [(v, n + 1, level, "v") for n, v in enumerate(verbs)])
    evs.store_examples(conn, [evs.Example(l, e, "—") for l, e in phrases]
                       + [evs.Example(l, e, "—", evs.IDIOM) for l, e in idioms])
    conn.commit()
    return conn


@pytest.fixture
def words(tmp_path):
    conn = evs_words(tmp_path / "w.db")
    yield conn
    conn.close()


class TestWhatEvsShows:
    def test_each_modal_takes_the_infinitive_its_phrases_show(self, words):
        assert modals.governed(words) == {
            "tohtima": "da", "pidama": "ma", "võima": "da", "saama": "da"}

    def test_an_idiom_a_chain_and_a_distant_infinitive_are_not_evidence(self, words):
        found = {(p.governor, p.lemma) for p in modals.pairs(words)}
        assert ("saama", "hakkama") not in found
        assert ("võima", "lõhkuma") not in found
        assert ("pidama", "vaikima") not in found

    def test_the_saama_future_is_not_evidence(self, words):
        assert not [p for p in modals.pairs(words) if p.governor == "saama"
                    and p.form == "ma"]

    def test_a_modal_shown_with_both_is_dropped(self, words, monkeypatch):
        """No guess about which is "really" right: the verb is not drilled."""
        both = [Pair("", "võima", frozenset({"b"}), "minema", form, "", 0, 0)
                for form in ("da", "ma")]
        monkeypatch.setattr(modals, "pairs", lambda conn, governors=GOVERNORS: both)
        assert modals.governed(words) == {}
        assert modals.drills(words, count=5, seed=1) == []

    def test_no_import_means_no_pairs(self, tmp_path):
        from eesti.wordlist import SCHEMA

        empty = sqlite3.connect(tmp_path / "e.db")
        empty.executescript(SCHEMA)
        assert modals.pairs(empty) == [] and modals.governed(empty) == {}


class TestTheDrill:
    def test_the_gap_is_the_infinitive_and_the_key_is_vabamorfs(self, words):
        items = {i.lemma: i for i in modals.drills(words, count=10, seed=1)}
        assert set(items) == {"ehmatama", "asendama", "muutuma", "printima"}
        assert items["ehmatama"].prompt == "teda ei tohi ____"
        assert (items["ehmatama"].answer, items["ehmatama"].distractor) == (
            "ehmatada", "ehmatama")
        assert (items["asendama"].answer, items["asendama"].distractor) == (
            "asendama", "asendada")

    def test_items_are_credited_and_file_under_ma_da_inf(self, words):
        for item in modals.drills(words, count=10, seed=2):
            assert item.source_id == evs.SOURCE_ID
            assert item.topic == "ma-da-inf" and item.rule == "modaal"
            assert item.label == "ma- või da-tegevusnimi"
            assert item.check(item.answer) and not item.check(item.distractor)

    def test_saab_olema_is_never_asked(self, words):
        for seed in range(6):
            for item in modals.drills(words, count=10, seed=seed):
                assert "saab" not in item.prompt or item.lemma != "olema"
                assert "toimuma" not in (item.answer, item.distractor)

    def test_the_infinitives_verb_must_be_at_the_level(self, tmp_path):
        conn = evs_words(tmp_path / "b1.db", level="B1")
        assert modals.drills(conn, levels=("A1", "A2"), count=5, seed=1) == []
        assert modals.drills(conn, levels=("B1",), count=5, seed=1)

    def test_the_same_seed_gives_the_same_items(self, words):
        a = [i.to_dict() for i in modals.drills(words, count=4, seed=9)]
        assert a == [i.to_dict() for i in modals.drills(words, count=4, seed=9)]


def test_the_committed_dictionary_gives_the_expected_mapping(real_wordlist):
    """Pinned against EKI's data: a refreshed import that moves a modal is noticed."""
    assert modals.governed(real_wordlist) == {
        "võima": "da", "saama": "da", "tohtima": "da", "pidama": "ma"}
    assert modals.governed(real_wordlist, ("hakkama",)) == {"hakkama": "ma"}
