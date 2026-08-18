"""End-of-level checkpoints.

What a checkpoint measures is different from what a topic gate measures, and
most of these tests are about keeping that distinction real: mixed rather than
blocked, diagnostic rather than punitive.
"""

from __future__ import annotations

import pytest

from eesti import checkpoint
from eesti.checkpoint import (DEFAULT_ITEMS, PASS_MARK, build, history,
                              passed_levels, ready, run, topics_at)
from eesti.progress import MASTERY_CORRECT, MASTERY_WINDOW, connect, mark_mastered
from eesti.review import connect as review_connect


@pytest.fixture
def db(tmp_path):
    return connect(tmp_path / "p.db")


@pytest.fixture
def reviews(tmp_path):
    return review_connect(tmp_path / "r.db")


def perfect(item):
    return item.answer


def wrong(item):
    return item.distractor


class TestBuild:
    def test_it_draws_across_the_whole_level(self, db):
        items = build("A1", count=12, seed=1)
        assert len(items) == 12
        # A level with eleven drillable topics should not produce a quiz on two.
        assert len({i.topic for i in items}) >= 8

    def test_no_two_consecutive_items_share_a_topic(self, db):
        """Interleaved by construction — there is no blocked version of
        'everything you learned at A1'."""
        topics = [i.topic for i in build("A1", count=12, seed=1)]
        assert all(a != b for a, b in zip(topics, topics[1:]))

    def test_round_robin_not_random(self, db):
        """A random draw from a level with nine verb topics and three noun
        topics measures what the syllabus contains, not the learner."""
        counts: dict[str, int] = {}
        for item in build("A1", count=11, seed=1):
            counts[item.topic] = counts.get(item.topic, 0) + 1
        assert max(counts.values()) - min(counts.values()) <= 1

    def test_a_level_with_no_drillable_topics_yields_nothing(self):
        assert topics_at("A1")
        assert build("A1", count=5, seed=1)

    def test_it_is_reproducible(self, db):
        a = [(i.topic, i.answer) for i in build("A1", count=8, seed=7)]
        b = [(i.topic, i.answer) for i in build("A1", count=8, seed=7)]
        assert a == b


class TestReadiness:
    def test_a_level_is_ready_when_every_drillable_topic_is_mastered(self, db):
        assert not ready(db, "A1")
        for topic in topics_at("A1"):
            mark_mastered(db, topic, via="placement")
        assert ready(db, "A1")

    def test_reference_topics_do_not_block_readiness(self, db):
        """`tahestik` has no generator and cannot be demonstrated, so it must
        not stand between the learner and their own checkpoint."""
        from eesti.curriculum import at_level

        assert any(t.generator is None for t in at_level("A1"))
        for topic in topics_at("A1"):
            mark_mastered(db, topic, via="placement")
        assert ready(db, "A1")


class TestRun:
    def test_a_perfect_run_passes(self, db):
        result = run(db, "A1", perfect, count=10, seed=1)
        assert result.correct == result.asked == 10
        assert result.passed and result.score == 1.0

    def test_the_bar_is_lower_than_the_topic_gate(self):
        """Across a level, unprompted, is harder at the same number — so
        holding it to the same bar would make finishing a level rarer than
        mastering every topic in it."""
        assert PASS_MARK < MASTERY_CORRECT / MASTERY_WINDOW

    def test_answers_are_recorded_as_real_attempts(self, db):
        run(db, "A1", wrong, count=8, seed=1)
        n = db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        assert n == 8

    def test_failing_un_masters_nothing(self, db):
        """The value is the diagnosis, not the score."""
        for topic in topics_at("A1"):
            mark_mastered(db, topic, via="placement")
        before = db.execute(
            "SELECT COUNT(*) FROM topic_state WHERE mastered_at IS NOT NULL"
        ).fetchone()[0]
        result = run(db, "A1", wrong, count=10, seed=1)
        assert not result.passed
        after = db.execute(
            "SELECT COUNT(*) FROM topic_state WHERE mastered_at IS NOT NULL"
        ).fetchone()[0]
        assert after == before

    def test_missed_items_go_to_the_review_queue(self, db, reviews):
        run(db, "A1", wrong, count=8, seed=1, reviews=reviews)
        queued = reviews.execute("SELECT COUNT(*) FROM review_items").fetchone()[0]
        assert queued > 0

    def test_the_weakest_topics_are_named(self, db):
        def all_but_olevik(item):
            return "vale" if item.topic == "olevik" else item.answer

        result = run(db, "A1", all_but_olevik, count=12, seed=1)
        assert "olevik" in result.weakest

    def test_a_perfect_run_has_no_weakest_topic(self, db):
        assert run(db, "A1", perfect, count=10, seed=1).weakest == []

    def test_results_are_recorded(self, db):
        run(db, "A1", perfect, count=10, seed=1)
        rows = history(db, "A1")
        assert len(rows) == 1 and rows[0]["passed"] == 1
        assert passed_levels(db) == {"A1"}

    def test_a_failed_level_is_not_in_passed_levels(self, db):
        run(db, "A1", wrong, count=10, seed=1)
        assert passed_levels(db) == set()
