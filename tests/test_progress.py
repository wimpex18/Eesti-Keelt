"""Mastery gating and where the learner left off.

The most important test here is the reachability one. Everything else can be
slightly wrong and still be useful; a syllabus with an unreachable topic is a
course the learner cannot finish, and nothing on screen says so.
"""

from __future__ import annotations

import pytest

from eesti import progress
from eesti.progress import (MASTERY_CORRECT, MASTERY_DISTINCT, MASTERY_WINDOW,
                            accuracy, connect, distinct_recent, is_mastered,
                            mark_mastered, mastered, record, report, resume,
                            unlocked)


class Item:
    """Minimal stand-in — progress only needs the fields it stores."""

    def __init__(self, topic="olevik", prompt="Ma ____.", answer="lähen"):
        self.topic, self.prompt, self.answer = topic, prompt, answer


@pytest.fixture
def db(tmp_path):
    return connect(tmp_path / "p.db")


def _run(db, topic, results):
    for i, ok in enumerate(results):
        record(db, Item(topic=topic, prompt=f"q{i}"), bool(ok))


class TestMasteryGate:
    def test_a_full_window_at_the_threshold_masters_the_topic(self, db):
        _run(db, "olevik", [1] * MASTERY_CORRECT + [0] * (MASTERY_WINDOW - MASTERY_CORRECT))
        # ends on a wrong answer, so re-assert with a final correct one
        _run(db, "olevik", [1])
        assert is_mastered(db, "olevik")

    def test_a_short_perfect_run_does_not_master(self, db):
        """Three clean answers is not evidence about a paradigm."""
        _run(db, "olevik", [1, 1, 1])
        assert not is_mastered(db, "olevik")

    def test_below_the_threshold_does_not_master(self, db):
        _run(db, "olevik", [1, 0] * MASTERY_WINDOW)
        assert not is_mastered(db, "olevik")

    def test_a_rolling_window_lets_a_bad_start_be_outgrown(self, db):
        """Lifetime accuracy would hold this learner at 50 % forever."""
        _run(db, "olevik", [0] * 20)
        assert not is_mastered(db, "olevik")
        _run(db, "olevik", [1] * MASTERY_WINDOW)
        assert is_mastered(db, "olevik")
        assert accuracy(db, "olevik") == 1.0

    def test_mastery_is_not_revoked_by_a_later_bad_run(self, db):
        """Forgetting is the review scheduler's job. Revoking a prerequisite
        would let one bad evening lock the learner out of half the syllabus."""
        _run(db, "olevik", [1] * MASTERY_WINDOW)
        assert is_mastered(db, "olevik")
        _run(db, "olevik", [0] * MASTERY_WINDOW)
        assert is_mastered(db, "olevik")
        assert accuracy(db, "olevik") == 0.0

    def test_the_same_two_items_cannot_clear_the_gate(self, db):
        """Ten attempts, eight correct, window full — and nothing demonstrated
        but short-term memory. `item_key` was stored and never read, which is
        what made this hole invisible."""
        for i in range(MASTERY_WINDOW):
            record(db, Item(topic="olevik", prompt=f"q{i % 2}"), correct=True)
        assert distinct_recent(db, "olevik") == 2
        assert not is_mastered(db, "olevik")

    def test_enough_variety_still_masters_normally(self, db):
        """A real ten-item session produces ten distinct items, so the variety
        condition costs an honest learner nothing."""
        _run(db, "olevik", [1] * MASTERY_WINDOW)
        assert distinct_recent(db, "olevik") == MASTERY_WINDOW
        assert is_mastered(db, "olevik")

    def test_variety_is_measured_over_the_window_not_all_time(self, db):
        """Ten varied items long ago do not license ten repeats today."""
        _run(db, "olevik", [0] * MASTERY_WINDOW)          # q0..q9, all wrong
        for i in range(MASTERY_WINDOW):
            record(db, Item(topic="olevik", prompt=f"repeat{i % 2}"), correct=True)
        assert distinct_recent(db, "olevik") == 2
        assert not is_mastered(db, "olevik")

    def test_the_distinct_threshold_is_below_the_window(self, db):
        assert MASTERY_DISTINCT < MASTERY_WINDOW

    def test_the_first_mastery_date_is_kept(self, db):
        mark_mastered(db, "olevik", via="placement")
        first = db.execute(
            "SELECT mastered_at, via FROM topic_state WHERE topic='olevik'"
        ).fetchone()
        mark_mastered(db, "olevik", via="practice")
        again = db.execute(
            "SELECT mastered_at, via FROM topic_state WHERE topic='olevik'"
        ).fetchone()
        assert (again[0], again[1]) == (first[0], first[1])

    def test_skipping_and_passing_are_the_same_operation(self, db):
        """What step 4's test-out reuses instead of building a parallel gate."""
        mark_mastered(db, "olevik", via="placement")
        assert "olevik" in mastered(db)


class TestAccuracy:
    def test_untouched_topics_report_none_not_zero(self, db):
        """"Not started" and "got everything wrong" are different states, and a
        progress view that renders them alike lies to the learner."""
        assert accuracy(db, "olevik") is None
        _run(db, "olevik", [0])
        assert accuracy(db, "olevik") == 0.0

    def test_the_answer_given_is_kept_for_the_error_log(self, db):
        record(db, Item(), correct=False, answer="minen")
        assert db.execute("SELECT answer FROM attempts").fetchone()[0] == "minen"


class TestReachability:
    def test_no_drillable_topic_is_permanently_unreachable(self):
        """The defect this caught: `pohivormid` has no generator, so it could
        never be demonstrated, so `gen-stem` and everything under it stayed
        locked forever while the path offered `tahestik` on repeat."""
        from eesti.curriculum import TOPICS, order
        from eesti.progress import reference_topics

        known = reference_topics()
        reached: set[str] = set()
        for topic in order():
            if set(topic.requires) <= known | reached:
                reached.add(topic.id)
        drillable = {t.id for t in TOPICS if t.generator}
        assert drillable <= reached

    def test_topics_without_practice_do_not_gate(self, db):
        from eesti.curriculum import by_id

        assert by_id("pohivormid").generator is None
        assert "pohivormid" in unlocked(db)

    def test_they_are_shown_as_reference_not_hidden(self, db):
        states = {r.topic: r.state for r in report(db)}
        assert states["pohivormid"] == "reference"
        assert states["olevik"] == "ready"


class TestResume:
    def test_it_never_lands_on_a_topic_with_nothing_to_do(self, db):
        from eesti.curriculum import by_id

        topic = resume(db)
        assert topic is not None
        assert by_id(topic).generator is not None

    def test_an_started_topic_is_preferred_over_a_new_one(self, db):
        first = resume(db)
        _run(db, "tingiv", [1])
        # `tingiv` needs verb-form, so it is not available yet; use a topic that
        # is, and check the preference holds.
        _run(db, "kusisonad", [1])
        assert resume(db) in ("kusisonad", first)
        _run(db, "kusisonad", [1] * MASTERY_WINDOW)
        assert resume(db) != "kusisonad"

    def test_everything_mastered_reports_nothing_left(self, db):
        from eesti.curriculum import TOPICS

        for topic in TOPICS:
            mark_mastered(db, topic.id, via="placement")
        assert resume(db) is None


def test_item_key_is_stable_and_distinguishes_items():
    a, b = Item(prompt="one"), Item(prompt="two")
    assert progress.item_key(a) == progress.item_key(Item(prompt="one"))
    assert progress.item_key(a) != progress.item_key(b)


def test_report_covers_every_topic_in_study_order(db):
    from eesti.curriculum import TOPICS, order

    rows = report(db)
    assert [r.topic for r in rows] == [t.id for t in order()]
    assert len(rows) == len(TOPICS)
