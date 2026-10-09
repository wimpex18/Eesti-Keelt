"""`osaalus`: the partitive subject of an existential sentence.

EKK SÜ 35 (*Täis- ja osaalus*): a negated subject is always partitive (*Laual pole
raamatut*); a partial subject does not agree with the verb, which stays in the
third person singular (*Külas elab ukrainlasi*, against *Külas elavad
ukrainlased*). An affirmative subject of substance may be either case (*Vaadis on
bensiin/bensiini*), so no item asks for one.
"""

from __future__ import annotations

from eesti.existential import BASE_RULES, drills
from eesti.morph import analyze, unique_form


def _verb(prompt: str):
    return next(t for t in analyze(prompt.replace("____", "")) if t.pos == "V"
                and t.lemma != "olema")


def test_a_negated_subject_is_partitive():
    items = drills(count=12, seed=1, rules=("eitus",))
    assert items
    for d in items:
        assert d.rule == "eitus" and d.topic == "osaalus"
        assert "ei ole" in d.prompt or "pole" in d.prompt.split()
        assert d.answer == unique_form(d.lemma, "sg p")
        assert d.distractor == unique_form(d.lemma, "sg n")
        assert d.answer != d.distractor


def test_a_singular_verb_takes_a_partial_plural_subject():
    """With *mängib*, *lapsed* cannot be the subject: only *lapsi* fits."""
    items = drills(count=24, seed=2, rules=("mitmus",))
    singular = [d for d in items if _verb(d.prompt).form in ("b", "s")]
    plural = [d for d in items if _verb(d.prompt).form in ("vad", "sid")]
    assert singular and plural
    for d in singular:
        assert d.answer == unique_form(d.lemma, "pl p")
        assert d.distractor == unique_form(d.lemma, "pl n")
    for d in plural:
        assert d.answer == unique_form(d.lemma, "pl n")
        assert d.distractor == unique_form(d.lemma, "pl p")


def test_the_default_set_is_the_negated_sentence():
    """EKI's profile places the negated existential at A1–A2 (913, 1336) and
    varying the subject case at B2 (1328): a plain set asks only the first."""
    assert BASE_RULES == ("eitus",)
    assert {d.rule for d in drills(count=10, seed=3)} == {"eitus"}


def test_no_item_asks_an_affirmative_substance():
    """*Poes on leib* and *Poes on leiba* are both Estonian (EKK SÜ 35)."""
    for rule in ("eitus", "mitmus"):
        for d in drills(count=20, seed=4, rules=(rule,)):
            words = d.prompt.split()
            assert not ("on" in words and "ei" not in words), d.prompt


def test_osaalus_is_a_topic_with_a_rule_page(client):
    from eesti.curriculum import by_id

    topic = by_id("osaalus")
    assert topic.generator and {"osastav", "eitus", "mitmus"} <= set(topic.requires)
    lesson = client.get("/api/lesson/osaalus").json()
    assert lesson["points_ru"] and any("SÜ 35" in s["label"] for s in lesson["sources"])


def test_every_item_is_a_choice():
    """Typed, *Pargis mängib laps* and *Poes ei ole saiu* are Estonian too: the
    hidden case could not say which form is wanted, so the item is a choice."""
    for rule in ("eitus", "mitmus"):
        for d in drills(count=10, seed=5, rules=(rule,)):
            assert set(d.choices) == {d.answer, d.distractor}


def test_the_api_hides_the_case_until_the_answer(client):
    """Choosing the case is the exercise, as in `obj-case`."""
    items = client.post("/api/practice", json={
        "topic": "osaalus", "count": 5, "seed": 1}).json()["items"]
    assert items and all(it["label"] == "" for it in items)
    assert {it["form_after"] for it in items} == {"osastav"}
    item = items[0]
    graded = client.post("/api/practice/answer", json={
        "topic": "osaalus", "prompt": item["prompt"], "answer": item["answer"],
        "given": item["answer"], "token": item["token"], "record": False}).json()
    assert graded["correct"]
