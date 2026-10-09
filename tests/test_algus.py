"""Unit 1, *Tere!*: sounds and quantity, greetings and survival phrases, numbers.

Each key is a source's own: the sound items' answer is EKI's form and quantity
mark for the recording played; a phrase belongs to the function EKI's A1 phrase
collection files it under; a number is written as EKK O 42 writes numerals.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n,words", [
    (0, "null"), (7, "seitse"), (10, "kümme"),
    (13, "kolmteist ~ kolmteistkümmend"), (17, "seitseteist ~ seitseteistkümmend"),
    (30, "kolmkümmend"), (43, "nelikümmend kolm"), (99, "üheksakümmend üheksa"),
    (100, "sada"),
])
def test_numbers_are_written_as_ekk_writes_them(n, words):
    """EKK O 42: -teist(kümmend) and -kümmend join the numeral before them; the
    rest stand apart (*nelikümmend kolm*)."""
    from eesti.numbers import written

    assert written(n) == words


def test_every_number_word_is_a_numeral_vabamorf_knows():
    from eesti.morph import pos_readings
    from eesti.numbers import written

    for n in range(101):
        for variant in written(n).split(" ~ "):
            for word in variant.split():
                assert any(pos == "N" for pos, _ in pos_readings(word)), (n, word)


def test_writing_a_number_accepts_either_teen_form():
    from eesti.numbers import drills

    items = drills(count=40, seed=1, rules=("kirjuta",))
    teen = next(d for d in items if "teist ~" in d.answer)
    short, long_ = teen.answer.split(" ~ ")
    assert teen.check(short) and teen.check(long_)
    assert not teen.check(teen.distractor)


def test_hearing_a_number_is_answered_in_digits():
    from eesti.numbers import drills, written

    for d in drills(count=12, seed=2, rules=("kuula",)):
        assert d.answer.isdigit() and d.say == written(int(d.answer)).split(" ~ ")[0]
        assert d.distractor.isdigit() and d.distractor != d.answer


# ---------------------------------------------------------------------------
# Phrases
# ---------------------------------------------------------------------------

def test_a_phrase_is_chosen_for_its_function():
    from eesti.phrases import FUNCTIONS, drills

    filed = {p: f.id for f in FUNCTIONS for p in f.phrases}
    heading = {f.et: f.id for f in FUNCTIONS}
    for d in drills(count=20, seed=1, rules=("olukord",)):
        asked = heading[d.prompt.split(":")[0]]
        assert filed[d.answer] == asked
        assert d.answer in d.choices and len(set(d.choices)) == len(d.choices)
        for other in d.choices:
            if other != d.answer:
                assert filed[other] != asked


def test_no_choice_set_puts_overlapping_functions_together():
    """*Kõike head!* takes leave or congratulates, *Head reisi!* is a wish,
    *Vabandust?* can ask for a repeat: side by side, either could be right."""
    from eesti.phrases import APART, FUNCTIONS, drills

    filed = {p: f.id for f in FUNCTIONS for p in f.phrases}
    for d in drills(count=80, seed=3, rules=("olukord",)):
        kinds = {filed[c] for c in d.choices}
        assert not any(pair <= kinds for pair in APART), d.choices


def test_a_reply_is_eki_s_own_reply():
    from eesti.phrases import EXCHANGES, drills

    replies = dict(EXCHANGES)
    social = {"Kuidas läheb?", "Vabandust!", "Aitäh!"}
    for d in drills(count=20, seed=2, rules=("vastus",)):
        first = d.prompt.split(" – ")[0]
        assert replies[first] == d.answer
        # A distractor answers the other kind of exchange, and never one that
        # could answer a counter question too (*Palun!* = "yes, please").
        mine = first in social
        assert all((f in social) != mine for f, r in EXCHANGES if r == d.distractor)
        if not mine:
            assert d.distractor not in ("Palun!", "Ei ole midagi.")


def test_phrase_items_carry_eki_s_credit(client):
    items = client.post("/api/practice", json={
        "topic": "fraasid", "count": 6, "seed": 1}).json()["items"]
    assert items and all("Kasulikke väljendeid" in it["attribution"] for it in items)
    assert all(it["choices"] for it in items)


# ---------------------------------------------------------------------------
# Sounds
# ---------------------------------------------------------------------------

def test_an_item_whose_answer_is_its_meaning_offers_no_translation(client, eki_recordings):
    """A translation of *Tere!* or of a heard word would be the answer."""
    for topic in ("fraasid", "tahestik"):
        items = client.post("/api/practice", json={
            "topic": topic, "count": 4, "seed": 1}).json()["items"]
        assert items and all(it["translate"] is False for it in items), topic
    heard = client.post("/api/practice", json={
        "topic": "arvud", "count": 6, "seed": 1, "rules": ["kuula"]}).json()["items"]
    assert heard and all(it["translate"] is False for it in heard)


def test_quantity_is_keyed_by_eki_s_mark(eki_recordings):
    """*selle salli* (II) and *seda salli* (III) are spelt alike; the key is the
    mark on the recording played."""
    from eesti.sounds import drills

    items = drills(count=10, seed=1, rules=("valde",))
    assert items
    for d in items:
        form = d.say
        assert d.say_tag in ("sg g", "sg p")
        expected = f"selle {form}" if d.say_tag == "sg g" else f"seda {form}"
        assert d.answer == expected and d.distractor != d.answer
        assert set(d.choices) == {f"selle {form}", f"seda {form}"}
    # *lina* is recorded twice, both unmarked: no contrast, no item.
    assert all(d.say != "lina" for d in drills(count=30, seed=2, rules=("valde",)))


def test_a_vowel_or_length_pair_is_keyed_by_the_recorded_form(eki_recordings):
    from eesti.sounds import drills

    for rule in ("taht", "pikkus"):
        items = drills(count=6, seed=2, rules=(rule,))
        assert items, rule
        for d in items:
            assert d.answer == d.say and d.say in d.choices and len(d.choices) == 2


def test_a_doubled_stop_is_not_called_a_long_sound(eki_recordings):
    """*kapi*/*kappi* is II against III quantity (EKK O 8), not short and long."""
    from eesti.sounds import drills

    items = drills(count=20, seed=4, rules=("pikkus",))
    assert items and not {d.say for d in items} & {"kapi", "kappi"}


def test_compounds_are_left_for_later(eki_recordings):
    from eesti.sounds import drills

    assert all("+" not in d.say for d in drills(count=20, seed=3))


def test_without_recordings_the_topic_says_so(tmp_path, monkeypatch):
    from eesti import config
    from eesti.sounds import drills

    monkeypatch.setattr(config, "AUDIO_DB", str(tmp_path / "absent.db"))
    with pytest.raises(ValueError, match="recordings"):
        drills(count=5, seed=1)
    assert not (tmp_path / "absent.db").exists()


def test_sound_items_name_eki_and_stay_out_of_offline_packs(client, eki_recordings):
    items = client.post("/api/practice", json={
        "topic": "tahestik", "count": 5, "seed": 1}).json()["items"]
    assert items and all("põhisõnavara" in it["attribution"] for it in items)
    assert all(it["say"] for it in items)
    pack = client.get("/api/pack").json()
    assert not any(it.get("say") for it in pack["items"])


def test_a_new_learner_s_offline_pack_keeps_its_choices(client):
    """Phrases are chosen, not typed: the pack carries the choices the page
    renders, so *Tere hommikust!* is not marked wrong against *Tere!*."""
    pack = client.get("/api/pack").json()
    chosen = [it for it in pack["items"] if it["topic"] == "fraasid"]
    assert chosen and all(it["answer"] in it["choices"] for it in chosen)
