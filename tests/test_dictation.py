"""Listening practice that can be got wrong, and that gets written down.

The Kuulamine tab was a text-to-speech box. Nothing could be answered, so
nothing could be scored, so nothing was recorded — and the readiness verdict
reported listening as untouched however much had been played. On an exam where
a zero in one part fails you regardless of the other three, that was the worst
place in the app to have no exercise at all.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import dictation
from eesti.progress import connect as progress_connect


@pytest.fixture
def content(tmp_path):
    """Real Estonian, built from scratch — not the developer's harvest, which
    would make this pass only where the harvest has been run."""
    conn = sqlite3.connect(tmp_path / "content.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE items (id TEXT PRIMARY KEY, source_id TEXT, body TEXT);"
    )
    bodies = [
        "Ma elan Tallinnas ja töötan siin.",
        "Ta läks eile kooli ja ostis uue raamatu poest.",
        "Homme tuleb sadu ja tuul on tugev.",
        "Riigikohus ei võtnud tema kaitsja kaebust arutusele.",
        "See on lühike.",                                     # 3 words: too short
        " ".join(["sõna"] * 30),                              # 30 words: too long
    ]
    conn.executemany(
        "INSERT INTO items (id, source_id, body) VALUES (?,?,?)",
        [(str(i), "selges-keeles", b) for i, b in enumerate(bodies)],
    )
    conn.commit()
    return conn


@pytest.fixture
def progress(tmp_path):
    return progress_connect(tmp_path / "p.db")


class TestWhatGetsDictated:
    def test_every_passage_is_a_workable_length(self, content):
        """Past about a dozen words the learner is holding a sentence in
        working memory, and the exercise measures memory rather than
        listening. Under four there is not enough to hear."""
        for p in dictation.choose(content, count=10, seed=1):
            assert dictation.MIN_WORDS <= p.words <= dictation.MAX_WORDS

    def test_the_sentence_is_one_a_native_wrote(self, content):
        """The whole reason to dictate from the corpus: no answer key to
        author, and no way for a generated sentence to be subtly wrong."""
        bodies = " ".join(r[0] for r in content.execute("SELECT body FROM items"))
        for p in dictation.choose(content, count=5, seed=2):
            assert p.text in bodies

    def test_an_empty_corpus_is_a_state_not_a_crash(self, tmp_path):
        conn = sqlite3.connect(tmp_path / "empty.db")
        conn.executescript("CREATE TABLE items (id TEXT, source_id TEXT, body TEXT);")
        assert dictation.choose(conn, count=3) == []

    def test_it_does_not_serve_the_same_sentence_every_session(self, content):
        """With no vocabulary history there is nothing to order by. Returning
        the corpus in table order would mean the first sentence, forever."""
        first = {dictation.choose(content, count=1, seed=s)[0].text
                 for s in range(8)}
        assert len(first) > 1

    def test_a_known_vocabulary_puts_the_comprehensible_first(self, content,
                                                              tmp_path):
        """i+1, not i+5: a short sentence of unknown words is harder to write
        down than a longer one made of words already met."""
        from eesti.vocab import KNOWN, connect, set_status

        vocab = connect(tmp_path / "v.db")
        for lemma in ("ma", "elama", "tallinn", "ja", "töötama", "siin"):
            set_status(vocab, lemma, KNOWN)
        picked = dictation.choose(content, vocabulary=vocab, count=6, seed=1)
        coverages = [p.coverage for p in picked]
        assert coverages == sorted(coverages, reverse=True)
        assert picked[0].coverage is not None


class TestGrading:
    def sentence(self):
        text = "Ma elan Tallinnas ja töötan siin."
        return dictation.Passage(text, dictation.key_of(text), 6)

    def test_a_perfect_transcription_passes(self):
        p = self.sentence()
        assert dictation.grade(p, p.text).correct

    def test_punctuation_and_case_are_not_the_exercise(self):
        p = self.sentence()
        assert dictation.grade(p, "ma elan tallinnas ja töötan siin").correct

    def test_a_wrong_word_is_named(self):
        p = self.sentence()
        got = dictation.grade(p, "Ma elan Tartus ja töötan siin.")
        assert got.missed == ["tallinnas"]
        assert got.matched == 5 and got.total == 6

    def test_a_dropped_word_does_not_fail_everything_after_it(self):
        """Aligned rather than zipped: a naive comparison would mark every
        word after the omission wrong, and measure the alignment instead of
        the listening."""
        p = self.sentence()
        got = dictation.grade(p, "Ma Tallinnas ja töötan siin.")
        assert got.matched == 5
        assert got.missed == ["elan"]

    def test_nothing_typed_scores_nothing(self):
        got = dictation.grade(self.sentence(), "")
        assert got.matched == 0 and not got.correct

    def test_the_pass_mark_is_the_one_the_app_already_uses(self):
        """One pass mark, applied to the same kind of thing, rather than a
        second number invented here."""
        from eesti.checkpoint import PASS_MARK

        assert dictation.PASS_MARK == PASS_MARK

    def test_the_caveat_is_in_russian(self):
        assert any("Ѐ" <= ch <= "ӿ" for ch in dictation.CAVEAT)


class TestItIsWrittenDown:
    """Three bugs in this project have been a reader with no writer behind it.
    Listening is where that would matter most: noticing an untouched part is
    the verdict's whole job."""

    def test_an_attempt_is_stored(self, progress):
        text = "Ma elan Tallinnas ja töötan siin."
        p = dictation.Passage(text, dictation.key_of(text), 6)
        dictation.record(progress, dictation.grade(p, text))
        assert dictation.stats(progress)["attempts"] == 1

    def test_repeats_are_recognisable_as_repeats(self, progress):
        text = "Ma elan Tallinnas ja töötan siin."
        p = dictation.Passage(text, dictation.key_of(text), 6)
        for _ in range(3):
            dictation.record(progress, dictation.grade(p, text))
        got = dictation.stats(progress)
        assert got["attempts"] == 3 and got["passages"] == 1

    def test_the_key_ignores_case_and_punctuation(self):
        assert dictation.key_of("Ma elan siin.") == dictation.key_of("ma elan siin")

    def test_it_rides_the_existing_snapshot(self, progress):
        """In progress.db rather than a database of its own. A new file would
        have had to be added to the state export, and that omission is exactly
        what once deleted the Notion queue on a cold start."""
        names = {r[0] for r in progress.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"attempts", "topic_state"} <= names
        dictation.ensure(progress)
        assert "dictation" in {r[0] for r in progress.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}


class TestTheVerdictMoves:
    """The point of recording. Before this, listening could not be practised
    into a non-zero state at all."""

    def part(self, progress):
        from eesti.readiness import readiness

        return next(p for p in readiness("A2", progress=progress).parts
                    if p.id == "kuulamine")

    def test_listening_starts_untouched(self, progress):
        assert self.part(progress).touched is False

    def test_enough_dictations_make_it_touched(self, progress):
        from eesti.readiness import CONTACT

        text = "Ma elan Tallinnas ja töötan siin."
        p = dictation.Passage(text, dictation.key_of(text), 6)
        for _ in range(CONTACT):
            dictation.record(progress, dictation.grade(p, text))
        assert self.part(progress).touched is True

    def test_the_evidence_says_which_kind_of_contact_it_was(self, progress):
        """"Opened a task" and "wrote down what was said" are different facts,
        and the stronger one should not be able to hide behind the weaker."""
        text = "Ma elan Tallinnas ja töötan siin."
        p = dictation.Passage(text, dictation.key_of(text), 6)
        dictation.record(progress, dictation.grade(p, text))
        assert "диктант" in self.part(progress).evidence

    def test_no_dictations_leaves_the_evidence_line_alone(self, progress):
        assert "диктант" not in self.part(progress).evidence
