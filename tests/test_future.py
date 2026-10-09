"""Talking about the future (`eesti/future.py`, EKK SÜ 27): the present after a
future adverbial, and *hakkama* + ma.

What a learner would notice if these broke: a future item with no word saying
it is the future, a past form accepted after *homme*, *hakkan õppida* marked
right, or the *saama*-future (*saab olema*) graded at all.
"""

from __future__ import annotations

import pytest

from eesti import evs, future
from test_modals import evs_words

#: Phrases from EKI EVS (CC BY 4.0), then two built on EKK SÜ 28's examples of
#: the saama-future, which must never become an item.
PHRASES = (
    ("tulema", "tulen homme jälle"),
    ("kohtuma", "lepime nii, et kohtume homme"),
    ("jõudma", "varsti jõuab sügis"),
    ("langema", "palavik hakkab langema"),
    ("maanduma", "lennuk hakkab maanduma"),
    ("laulma", "ta hakkas laulma"),               # the past: beginning, not the future
    ("elama", "eile elasin linnas"),               # no future adverbial
    ("olema", "elu saab seal homme olema raske"),
    ("toimuma", "homme saab siin toimuma ühisistung"),
)
VERBS = ("tulema", "kohtuma", "jõudma", "langema", "maanduma", "laulma", "elama",
         "olema", "toimuma", "saama", "hakkama", "leppima")


@pytest.fixture
def words(tmp_path):
    conn = evs_words(tmp_path / "w.db", PHRASES, (), VERBS)
    yield conn
    conn.close()


def _all(words, **kw):
    return [i for seed in range(8) for i in future.drills(words, count=10, seed=seed, **kw)]


class TestThePresentAfterAFutureAdverbial:
    def test_the_present_is_the_answer_and_the_past_the_distractor(self, words):
        items = {i.lemma: i for i in future.present_from_phrases(
            words, dict.fromkeys(VERBS, "A2"), 10, seed=1)}
        assert set(items) == {"tulema", "kohtuma", "jõudma"}
        assert items["tulema"].prompt == "____ homme jälle"
        assert (items["tulema"].answer, items["tulema"].distractor) == ("tulen", "tulin")
        assert items["tulema"].label == "olevik, mina"
        assert (items["jõudma"].answer, items["jõudma"].distractor) == ("jõuab", "jõudis")

    def test_a_phrase_with_no_future_adverbial_is_not_used(self, words):
        assert "elama" not in {i.lemma for i in _all(words, rules=("olevik",))
                               if i.source_id}

    def test_the_why_names_the_adverbial_and_ekk(self, words):
        for item in future.present_from_phrases(words, dict.fromkeys(VERBS, "A2"), 10, 2):
            assert "SÜ 27" in item.why_ru
            assert any(w in item.why_ru for w in ("homme", "varsti"))


class TestHakkama:
    def test_hakkama_in_the_present_takes_the_ma_infinitive(self, words):
        items = {i.lemma: i for i in future.hakkama_from_phrases(
            words, dict.fromkeys(VERBS, "A2"), 10, seed=1)}
        assert set(items) == {"langema", "maanduma"}
        assert items["langema"].prompt == "palavik hakkab ____"
        assert (items["langema"].answer, items["langema"].distractor) == (
            "langema", "langeda")

    def test_the_past_of_hakkama_is_not_the_future(self, words):
        assert "laulma" not in {i.lemma for i in _all(words, rules=("hakkama",))
                                if i.source_id}


class TestTheSaamaFutureIsNeverGraded:
    def test_no_item_blanks_or_keys_it(self, words):
        for item in _all(words):
            assert item.lemma != "saama" and "saab" not in item.prompt.split(), item
            if item.source_id:
                assert item.lemma not in ("toimuma", "olema"), item

    def test_frames_never_use_saama_or_hakkama_as_the_verb(self, words):
        frames = future.from_frames("olevik", dict.fromkeys(VERBS, "A2"), 30, 1)
        frames += future.from_frames("hakkama", dict.fromkeys(VERBS, "A2"), 30, 1)
        assert frames and not {"saama", "hakkama"} & {i.lemma for i in frames}


class TestTheSet:
    def test_both_kinds_by_default_and_one_when_narrowed(self, words):
        assert {i.rule for i in future.drills(words, count=10, seed=3)} == {
            "olevik", "hakkama"}
        assert {i.rule for i in future.drills(words, count=6, seed=3,
                                              rules=("hakkama",))} == {"hakkama"}

    def test_phrases_are_credited_and_frames_fill_the_rest(self, words):
        items = future.drills(words, count=10, seed=4)
        assert len(items) == 10
        assert {i.source_id for i in items} == {evs.SOURCE_ID, ""}
        for item in items:
            assert item.topic == "tulevik"
            assert item.check(item.answer) and not item.check(item.distractor)

    def test_without_evs_the_frames_carry_the_topic(self):
        """The fixture word list has no EVS import, as a fresh deployment."""
        from eesti.practice import items_for

        items = items_for("tulevik", count=6, seed=1)
        assert len(items) == 6 and all(i.topic == "tulevik" for i in items)
        assert not any(i.source_id for i in items)

    def test_the_same_seed_gives_the_same_items(self, words):
        a = [i.to_dict() for i in future.drills(words, count=6, seed=5)]
        assert a == [i.to_dict() for i in future.drills(words, count=6, seed=5)]


def test_the_adverbials_are_evs_future_words(real_wordlist):
    """Each adverbial's Russian, pinned against EKI's dictionary."""
    for word, ru in {**future.ADVERBS, **future.ATTRIBUTES}.items():
        assert ru in evs.russian(real_wordlist, word), word


def test_the_topic_links_ekk_su_27():
    from eesti.curriculum import by_id

    ref = by_id("tulevik").reference
    assert ref.ekk_section == "SÜ 27" and "p=5" in ref.url
