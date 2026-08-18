"""Tense, mood, infinitive and voice drills.

The distinguishing claim of this generator is that the distractor is the
neighbouring form a learner confuses the answer with, not an invented string.
Most of these tests check that claim holds and that an item measuring nothing
never ships.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import conjugation
from eesti.conjugation import FRAMES, generate


@pytest.fixture
def words(tmp_path):
    """A verb table built here, not read from the developer's build."""
    conn = sqlite3.connect(tmp_path / "w.db")
    conn.executescript(
        "CREATE TABLE words (word TEXT PRIMARY KEY, freq_rank INT,"
        " proficiency TEXT, pos TEXT);"
    )
    conn.executemany(
        "INSERT INTO words VALUES (?,?,?,?)",
        [
            ("minema", 10, "A1", "v"),
            ("tegema", 20, "A1", "v"),
            ("õppima", 30, "A2", "v"),
            ("liikuma", 40, "B1", "v"),
            ("raamat", 50, "A1", "s"),   # must never be conjugated
        ],
    )
    conn.commit()
    return conn


def test_only_verbs_are_drilled(words):
    assert "raamat" not in {lemma for lemma, _ in conjugation.verbs_at_levels(words)}


def test_levels_are_honoured(words):
    got = {lemma for lemma, _ in conjugation.verbs_at_levels(words, ("A1",))}
    assert got == {"minema", "tegema"}


def test_frequent_verbs_come_first(words):
    """Bleached frames read fine with a verb met daily and oddly with a rare
    one, so frequency order is doing real work here."""
    assert [lemma for lemma, _ in conjugation.verbs_at_levels(words)][0] == "minema"


def test_every_topic_produces_items(words):
    for topic in FRAMES:
        items = generate(words, topics=(topic,), count=3, seed=1)
        assert items, topic
        assert {i.topic for i in items} == {topic}


def test_answer_and_distractor_always_differ(words):
    for item in generate(words, count=60, seed=2):
        assert item.answer.lower() != item.distractor.lower()


def test_grading_is_deterministic(words):
    for item in generate(words, count=20, seed=3):
        assert item.check(item.answer)
        assert item.check(f" {item.answer.upper()} ")
        assert not item.check(item.distractor)


def test_the_distractor_is_a_real_form_of_the_same_verb(words):
    """Not a decoy: it is what Vabamorf synthesises for the neighbouring tag,
    which is what makes the contrast worth drilling."""
    from estnltk.vabamorf.morf import synthesize

    for item in generate(words, count=30, seed=4):
        frame = next(
            f for f in FRAMES[item.topic] if f.tag == item.tag
        )
        assert item.distractor in synthesize(item.lemma, frame.against)


def test_known_contrasts_are_produced_correctly(words):
    """Pinned against Estonian, so a refactor cannot quietly change an answer."""
    seen = {}
    for item in generate(words, count=200, seed=5):
        seen[(item.lemma, item.tag)] = item.answer
    assert seen.get(("minema", "sin")) == "läksin"
    assert seen.get(("minema", "ks")) == "läheks"
    assert seen.get(("tegema", "da")) == "teha"
    assert seen.get(("tegema", "tud")) == "tehtud"
    assert seen.get(("minema", "o")) == "mine"


def test_items_file_against_a_real_curriculum_topic(words):
    from eesti.curriculum import by_id

    for item in generate(words, count=20, seed=6):
        assert by_id(item.topic).generator == "conjugation"


def test_an_unknown_topic_is_rejected_rather_than_ignored(words):
    with pytest.raises(ValueError, match="no frames"):
        generate(words, topics=("nonesuch",))


def test_a_sentence_initial_blank_is_capitalised(words):
    """The imperative frames start with the blank; a lowercase sentence start
    looks like a bug to the learner."""
    items = generate(words, topics=("kaskiv",), count=6, seed=7)
    starting = [i for i in items if i.prompt.startswith("____")]
    assert starting
    for item in starting:
        assert item.solution[0].isupper()


def test_impersonal_frames_carry_no_object(words):
    """*"Seda liikutakse"* is ungrammatical — `seda` is an object and `liikuma`
    is intransitive, with no transitivity flag in the data to filter on."""
    for frames in (FRAMES["umbisikuline"], FRAMES["kesksonad"]):
        for frame in frames:
            assert "Seda" not in frame.sentence


def test_generation_is_reproducible(words):
    a = [i.to_dict() for i in generate(words, count=15, seed=8)]
    b = [i.to_dict() for i in generate(words, count=15, seed=8)]
    assert a == b


def test_an_empty_verb_table_fails_loudly(tmp_path):
    conn = sqlite3.connect(tmp_path / "empty.db")
    conn.executescript(
        "CREATE TABLE words (word TEXT PRIMARY KEY, freq_rank INT,"
        " proficiency TEXT, pos TEXT);"
    )
    with pytest.raises(RuntimeError, match="cli build"):
        generate(conn)
