"""Blocked practice handing off to interleaved review.

Two arrows: a missed item goes into the queue already marked missed, and a
mastered topic seeds the queue with a sample. The tests care most about what
must *not* happen — a reset schedule, a collapsed identity, or a topic that
quietly never reaches the review pool.
"""

from __future__ import annotations

import pytest

from eesti import handoff, review
from eesti.practice import items_for
from eesti.progress import connect as progress_connect
from eesti.progress import mark_mastered


@pytest.fixture
def reviews(tmp_path):
    return review.connect(tmp_path / "r.db")


@pytest.fixture
def progress(tmp_path):
    return progress_connect(tmp_path / "p.db")


class TestQueueFailed:
    def test_a_missed_item_enters_already_marked_missed(self, reviews):
        """The whole trick: it comes back soon instead of being scheduled as
        fresh material."""
        item = items_for("tingiv", count=1, seed=1)[0]
        key = handoff.queue_failed(reviews, item)
        row = reviews.execute(
            "SELECT reps, lapses FROM review_items WHERE id = ?", (key,)
        ).fetchone()
        assert (row["reps"], row["lapses"]) == (1, 1)

    def test_it_works_for_every_generator(self, reviews):
        from eesti.curriculum import TOPICS

        drillable = [t.id for t in TOPICS if t.generator]
        assert len(drillable) > 15
        for topic in drillable:
            item = items_for(topic, count=1, seed=1)
            if item:
                assert handoff.queue_failed(reviews, item[0])

    def test_requeueing_does_not_reset_the_schedule(self, reviews):
        item = items_for("tingiv", count=1, seed=1)[0]
        key = handoff.queue_failed(reviews, item)
        first = reviews.execute(
            "SELECT due FROM review_items WHERE id = ?", (key,)
        ).fetchone()[0]
        handoff.queue_failed(reviews, item)
        again = reviews.execute(
            "SELECT reps FROM review_items WHERE id = ?", (key,)
        ).fetchone()[0]
        # add() keeps the existing row; grade() advances it rather than starting over
        assert again == 2
        assert first


class TestIdentity:
    def test_question_words_do_not_collapse_onto_one_entry(self, reviews):
        """They carry no lemma — the word *is* the answer — so without the
        fallback all twelve would share an id."""
        for item in items_for("kusisonad", count=6, seed=1):
            handoff.queue_failed(reviews, item)
        n = reviews.execute("SELECT COUNT(*) FROM review_items").fetchone()[0]
        assert n == 6

    def test_the_same_form_from_two_sentences_is_one_item(self, reviews):
        """The grain is the form, not the sentence it appeared in."""
        item = items_for("tingiv", count=1, seed=1)[0]
        a = handoff.queue_failed(reviews, item)
        clone = type(item)(**{**item.__dict__, "prompt": "Hoopis teine lause ____."})
        b = handoff.queue_failed(reviews, clone)
        assert a == b


class TestSeedOnMastery:
    def test_mastery_moves_items_into_the_queue(self, reviews):
        keys = handoff.seed_mastered(reviews, "kusisonad", seed=1)
        assert len(keys) == handoff.SEED_ITEMS
        kinds = {r[0] for r in reviews.execute("SELECT kind FROM review_items")}
        assert kinds == {"kusisonad"}

    def test_it_seeds_a_sample_not_the_whole_topic(self, reviews):
        """A topic can generate hundreds; a queue that spikes on every pass is
        one the learner stops opening."""
        available = len(items_for("olevik", count=10_000, seed=1))
        assert available > handoff.SEED_ITEMS
        assert len(handoff.seed_mastered(reviews, "olevik", seed=1)) == handoff.SEED_ITEMS

    def test_seeding_twice_is_harmless(self, reviews):
        handoff.seed_mastered(reviews, "kusisonad", seed=1)
        before = reviews.execute("SELECT COUNT(*) FROM review_items").fetchone()[0]
        handoff.seed_mastered(reviews, "kusisonad", seed=1)
        assert reviews.execute(
            "SELECT COUNT(*) FROM review_items"
        ).fetchone()[0] == before

    def test_a_topic_with_no_generator_seeds_nothing_rather_than_raising(self, reviews):
        assert handoff.seed_mastered(reviews, "pohivormid") == []


class TestPendingHandoffs:
    def test_a_mastered_topic_outside_the_queue_is_reported(self, progress, reviews):
        mark_mastered(progress, "kusisonad", via="placement")
        assert handoff.pending_handoffs(progress, reviews) == ["kusisonad"]

    def test_nothing_pending_once_it_is_seeded(self, progress, reviews):
        mark_mastered(progress, "kusisonad", via="placement")
        handoff.seed_mastered(reviews, "kusisonad", seed=1)
        assert handoff.pending_handoffs(progress, reviews) == []

    def test_unmastered_topics_are_not_pending(self, progress, reviews):
        assert handoff.pending_handoffs(progress, reviews) == []


class TestInterleaving:
    """Step 5's whole purpose: practice is blocked, review is interleaved.

    It did not hold when first built. Items enter in batches of six the moment a
    topic is mastered, so they carry near-identical due times, and ordering by
    due date handed them back in insertion order — all of one topic, then all of
    the next. Blocked review, from the module whose job was to end it.
    """

    def test_a_session_alternates_between_topics(self, reviews):
        for topic in ("kusisonad", "olevik", "tingiv"):
            handoff.seed_mastered(reviews, topic, seed=1)
        order = [i.kind for i in review.due(reviews, limit=50)]
        assert len(order) == 3 * handoff.SEED_ITEMS
        # No topic ever appears twice in a row.
        assert all(a != b for a, b in zip(order, order[1:]))

    def test_the_first_three_cover_all_three_topics(self, reviews):
        for topic in ("kusisonad", "olevik", "tingiv"):
            handoff.seed_mastered(reviews, topic, seed=1)
        assert len({i.kind for i in review.due(reviews, limit=3)}) == 3

    def test_nothing_is_dropped_or_duplicated(self, reviews):
        for topic in ("kusisonad", "olevik"):
            handoff.seed_mastered(reviews, topic, seed=1)
        ids = [i.id for i in review.due(reviews, limit=50)]
        stored = {r[0] for r in reviews.execute("SELECT id FROM review_items")}
        assert sorted(ids) == sorted(stored)

    def test_uneven_topics_still_drain_completely(self, reviews):
        handoff.seed_mastered(reviews, "kusisonad", count=2, seed=1)
        handoff.seed_mastered(reviews, "olevik", count=5, seed=1)
        order = [i.kind for i in review.due(reviews, limit=50)]
        assert order.count("kusisonad") == 2 and order.count("olevik") == 5

    def test_a_single_topic_request_is_left_alone(self, reviews):
        """Asking for one topic is a deliberate drill-down, not a session."""
        handoff.seed_mastered(reviews, "olevik", seed=1)
        handoff.seed_mastered(reviews, "kusisonad", seed=1)
        got = review.due(reviews, limit=10, kind="olevik")
        assert got and {i.kind for i in got} == {"olevik"}
