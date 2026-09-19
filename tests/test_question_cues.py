"""The Russian cue on a küsisõnad blank: EKI's EVS, chosen by rule, never graded.

The cue tells a Russian speaker which question word is wanted (`____ sa elad?`
→ где) without printing the Estonian. It must come from a cited source
(`eesti/licences.py`, `eki-evs`), be chosen deterministically, and be absent
rather than guessed where the source is silent or ambiguous.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

from eesti import evs
from eesti.patterns import QUESTIONS, Question, cue_for, question_drills

ROOT = Path(__file__).resolve().parents[1]
EVS_FILE = ROOT / "deploy" / "eki" / "evs_EKI_CCBY40.xml.gz"

#: What EVS gives each answer word, pinned so a refreshed download that moves
#: a sense is noticed. Read off the committed file; see `_question_sense`.
EXPECTED = {
    "kus": ("где",),
    "kuhu": ("куда",),
    "kust": ("откуда",),
    "millal": ("когда",),
    "kes": ("кто",),
    "mis": ("что",),
    "miks": ("почему", "отчего", "зачем"),
    "kuidas": ("как",),
}

#: Deliberately cue-less, each for a reason the source states: EVS has no
#: headword for an inflected form of `kes` or for a two-word phrase.
CUELESS = {"kelle", "kellele", "kellega", "kui palju"}


def _article(word: str, pos: str, *senses: str) -> str:
    return (f'<x:A><x:P><x:mg><x:m>{word}</x:m><x:sl>{pos}</x:sl></x:mg></x:P>'
            f'<x:S>{"".join(senses)}</x:S></x:A>\n')


def _sense(ru: list[str], examples: list[str] = (), label: str = "") -> str:
    xs = "".join(f'<x:xg><x:x>{r}</x:x>{f"<x:s>{label}</x:s>" if label else ""}</x:xg>'
                 for r in ru)
    ns = "".join(f"<x:ng><x:n>{e}</x:n></x:ng>" for e in examples)
    return f'<x:tp><x:tg><x:xp xml:lang="ru">{xs}</x:xp></x:tg><x:np>{ns}</x:np></x:tp>'


def _senses(tmp_path, body: str, words) -> dict:
    path = tmp_path / "evs.xml"
    path.write_text(body, encoding="utf-8")
    return evs.question_senses(path, words)


class TestTheRule:
    def test_the_sense_is_the_one_evs_illustrates_with_a_question(self, tmp_path):
        """`mitu`'s first sense is "несколько"; its question sense is the second."""
        got = _senses(tmp_path, _article(
            "mitu", "pron",
            _sense(["н\"есколько"], ["mitu kuud tagasi"]),
            _sense(["ск\"олько"], ["mitu last sul on?"])), ["Mitu"])
        assert got == {"mitu": ("сколько",)}

    def test_a_homonym_of_another_part_of_speech_is_another_word(self, tmp_path):
        """`miks` the noun ("микс") does not compete with `miks` the adverb."""
        got = _senses(tmp_path,
                      _article("miks", "s", _sense(["микс"], ["miks?"]))
                      + _article("miks", "adv", _sense(["почем\"у"], ["miks sa kiirustad?"])),
                      ["miks"])
        assert got == {"miks": ("почему",)}

    def test_two_candidate_articles_give_no_cue(self, tmp_path):
        got = _senses(tmp_path,
                      _article("kus", "adv", _sense(["где"], ["kus sa elad?"]))
                      + _article("kus", "pron", _sense(["куда"], ["kus sa lähed?"])),
                      ["kus"])
        assert got == {}

    def test_no_question_example_gives_no_cue(self, tmp_path):
        got = _senses(tmp_path, _article("kus", "adv", _sense(["где"], ["ööbib kus juhtub"])),
                      ["kus"])
        assert got == {}

    def test_a_labelled_translation_is_not_a_cue(self, tmp_path):
        got = _senses(tmp_path, _article(
            "kus", "adv", _sense(["где"], ["kus sa elad?"], label="kõnek")), ["kus"])
        assert got == {}

    def test_a_word_that_is_not_a_headword_gets_nothing(self, tmp_path):
        got = _senses(tmp_path, _article("kes", "pron", _sense(["кто"], ["kes seal on?"])),
                      ["kellega", "kes"])
        assert got == {"kes": ("кто",)}

    def test_a_cue_the_distractor_shares_is_dropped(self):
        q = Question("Kus", "Kuhu", "", "{} x?", "")
        assert cue_for(q, {"kus": ("где",), "kuhu": ("где",)}) == ()
        assert cue_for(q, {"kus": ("где",), "kuhu": ("куда",)}) == ("где",)


@pytest.fixture(scope="module")
def real_cues():
    if not EVS_FILE.exists():
        pytest.skip("deploy/eki/evs_EKI_CCBY40.xml.gz is not in this checkout")
    return evs.question_senses(EVS_FILE, [q.word for q in QUESTIONS])


class TestTheCommittedDictionary:
    def test_every_answer_word_has_a_cue_or_is_deliberately_cueless(self, real_cues):
        answers = {q.word.casefold() for q in QUESTIONS}
        assert set(real_cues) | CUELESS == answers
        assert not set(real_cues) & CUELESS

    def test_the_mapping(self, real_cues):
        assert real_cues == EXPECTED

    def test_no_cue_is_shared_with_its_distractor(self, real_cues):
        for q in QUESTIONS:
            assert cue_for(q, real_cues) == real_cues.get(q.word.casefold(), ())

    def test_the_docs_state_the_coverage(self, real_cues):
        """`docs/curriculum.md`, `status.md` and `sources.md` give the count."""
        claims = []
        for name in ("curriculum.md", "status.md", "sources.md"):
            text = (ROOT / "docs" / name).read_text(encoding="utf-8")
            claims += re.findall(r"(\d+) of 12 (?:answer|question) words", text)
            claims += re.findall(r"(\d+) question-word cues", text)
        assert claims
        assert {int(c) for c in claims} <= {len(real_cues), len(QUESTIONS) - len(real_cues)}
        assert len(QUESTIONS) == 12


@pytest.fixture
def words(tmp_path):
    conn = sqlite3.connect(tmp_path / "words.db")
    evs.store_questions(conn, EXPECTED)
    yield conn
    conn.close()


class TestTheDrill:
    def test_items_carry_the_cue(self, words):
        items = question_drills(count=len(QUESTIONS), seed=3, words=words)
        by_answer = {i.answer.casefold(): i.answer_ru for i in items}
        for word, ru in EXPECTED.items():
            assert by_answer[word] == ru
        for word in CUELESS:
            assert by_answer[word] == ()

    def test_the_cue_never_prints_the_estonian(self, words):
        for item in question_drills(count=len(QUESTIONS), seed=3, words=words):
            shown = " ".join(item.answer_ru) + item.hint + item.prompt.split("—")[0]
            assert item.answer.casefold() not in shown.casefold().replace("____", "")
            assert "answer_ru" in item.to_dict()

    def test_grading_is_unchanged(self, words):
        """Same items, same answers, same verdicts, with and without cues; a
        Russian cue typed as the answer is wrong."""
        cued = question_drills(count=len(QUESTIONS), seed=5, words=words)
        plain = question_drills(count=len(QUESTIONS), seed=5)
        assert [(i.prompt, i.answer, i.distractor) for i in cued] == \
            [(i.prompt, i.answer, i.distractor) for i in plain]
        assert all(i.answer_ru == () for i in plain)
        for item in cued:
            assert item.check(item.answer) and item.check(f" {item.answer.lower()} ")
            assert not item.check(item.distractor)
            for ru in item.answer_ru:
                assert not item.check(ru)

    def test_no_table_means_no_cue(self, tmp_path):
        empty = sqlite3.connect(tmp_path / "empty.db")
        assert all(i.answer_ru == () for i in question_drills(count=12, words=empty))
