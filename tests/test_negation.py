"""Negation beyond the present and the past (`eesti/negation.py`): the forms EKK
M 99 names, each under the topic whose form it is.

What a learner would notice if these broke: *ärge tee* or *ei tehakse* marked
right, a negated conditional that might also take a person ending, or a phrase
gap that is not after its negation.
"""

from __future__ import annotations

import pytest

from eesti import evs, negation
from eesti.negation import NEGATED
from test_modals import evs_words

#: Phrases from EKI EVS (CC BY 4.0).
PHRASES = (
    ("tegema", "ärge tehke endale liigset tüli"),
    ("küpsetama", "nüüdisajal ei küpsetata kodus leiba"),
    ("suutma", "nii heast diilist ei suudaks keegi loobuda"),
    ("minema", "kas me ei läheks kinno?"),          # first person: left out
    ("kartma", "ärge kartke!"),
    ("tegema", "sellise tembu eest sulle pai ei tehta"),
)
VERBS = ("tegema", "küpsetama", "suutma", "minema", "kartma", "elama")


@pytest.fixture
def words(tmp_path):
    conn = evs_words(tmp_path / "w.db", PHRASES, (), VERBS)
    yield conn
    conn.close()


@pytest.mark.parametrize("topic, answer, wrong", [
    ("tingiv", "teeks", "tee"),
    ("kaskiv", "tehke", "tee"),
    ("umbisikuline", "tehta", "tehakse"),
    ("taisminevik", "teinud", "tegi"),
])
def test_the_frames_key_ekks_forms(topic, answer, wrong):
    items = negation.from_frames(NEGATED[topic], {"tegema": "A1"}, 1, seed=1)
    assert [(i.answer, i.distractor) for i in items] == [(answer, wrong)]
    item = items[0]
    assert item.topic == topic and item.rule == "eitus" and "M 99" in item.why_ru
    assert item.check(answer) and not item.check(wrong)


def test_every_frame_has_its_negation_before_the_gap():
    for kind in NEGATED.values():
        for frame in kind.frames:
            before = frame.split("____")[0].casefold()
            assert any(n in before for n in kind.before), frame


class TestPhrases:
    def test_the_gap_follows_the_negation(self, words):
        items = {i.prompt: i for topic in NEGATED for i in negation.from_phrases(
            words, NEGATED[topic], dict.fromkeys(VERBS, "A1"), 10, seed=1)}
        assert items["ärge ____ endale liigset tüli"].answer == "tehke"
        assert items["nüüdisajal ei ____ kodus leiba"].answer == "küpsetata"
        assert items["nii heast diilist ei ____ keegi loobuda"].answer == "suudaks"

    def test_a_first_person_conditional_is_left_out(self, words):
        items = negation.from_phrases(words, NEGATED["tingiv"],
                                      dict.fromkeys(VERBS, "A1"), 10, seed=1)
        assert all("kinno" not in i.prompt for i in items)

    def test_phrase_items_are_credited(self, words):
        for topic in NEGATED:
            for item in negation.from_phrases(words, NEGATED[topic],
                                              dict.fromkeys(VERBS, "A1"), 10, 2):
                assert item.source_id == evs.SOURCE_ID

    def test_one_item_per_verb(self, words):
        items = negation.from_phrases(words, NEGATED["umbisikuline"],
                                      dict.fromkeys(VERBS, "A1"), 10, seed=3)
        lemmas = [i.lemma for i in items]
        assert len(lemmas) == len(set(lemmas))


class TestTheSet:
    def test_frames_fill_what_the_phrases_cannot(self, words):
        items = negation.drills(words, "taisminevik", count=4, seed=1)
        assert len(items) == 4 and all(i.source_id == "" for i in items)

    def test_another_topic_gets_nothing(self, words):
        assert negation.drills(words, "olevik", count=4, seed=1) == []

    def test_a_verb_topic_mixes_its_negation_in(self):
        """`practice.items_for` on the fixture word list (no EVS import)."""
        from eesti.practice import items_for

        for topic in NEGATED:
            items = items_for(topic, count=6, seed=2)
            assert len(items) == 6
            assert "eitus" in {i.rule for i in items}, topic
            assert len({i.rule for i in items}) == 2, topic

    def test_narrowed_to_negation(self):
        from eesti.practice import items_for

        items = items_for("kaskiv", count=5, seed=3, rules=("eitus",))
        assert len(items) == 5 and {i.rule for i in items} == {"eitus"}
