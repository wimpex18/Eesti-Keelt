"""Beginner reading support follows known frames without exposing Estonian forms."""

from eesti.pronouns import drills
from eesti.scaffolding import pronoun_support
from eesti.api.render import item_for_page


def test_every_generated_pronoun_item_has_reading_support():
    for seed in range(20):
        for item in drills(count=30, seed=seed):
            shown = item_for_page(item)
            assert shown["sentence_ru"]
            assert shown["lemma_ru"]
            assert "____" not in shown["sentence_ru"]
            assert shown["answer"] == item.answer
            assert item.check(item.answer.split(" ~ ")[0])


def test_nemad_allative_is_comprehensible_without_the_answer():
    shown = {"topic": "asesonad", "lemma": "nemad", "prompt": "Anna see raamat ____."}
    assert pronoun_support(shown) == {"lemma_ru": "они", "sentence_ru": "Дай эту книгу им.", "form_ru": "кому?"}


def test_unknown_frames_and_other_topics_do_not_get_guessed_translations():
    assert not pronoun_support({"topic": "asesonad", "lemma": "nemad", "prompt": "New frame"})
    assert not pronoun_support({"topic": "obj-case", "lemma": "nemad", "prompt": "Anna see raamat ____."})


def test_russian_possessive_agrees_with_car():
    assert pronoun_support({"topic": "asesonad", "lemma": "mina", "prompt": "See on ____ auto."})["sentence_ru"] == "Это моя машина."
