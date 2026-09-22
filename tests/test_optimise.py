"""Fitting FSRS to this learner's own reviews.

The failure this guards is a silent one: parameters fitted on a handful of
answers schedule worse than FSRS's published defaults, and nothing about the
app would look wrong — cards would simply come back at the wrong time for
months.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from eesti import config, evidence, optimise, review


@pytest.fixture
def cards():
    with review.connect(config.REVIEW_DB) as conn:
        yield conn


def a_review(cards, n: int) -> None:
    """`n` recorded reviews, graded the way the app grades them."""
    for i in range(n):
        item = review.add(cards, "obj-case", f"sõna{i}", "küsimus", "vastus",
                          tag="obj-case")
        review.grade(cards, item, "good", auto=True, latency_ms=2000)


class TestItRefusesUntilThereIsHistory:
    def test_too_little_history_is_said_plainly(self, cards):
        a_review(cards, 3)
        with evidence.connect() as log:
            done = optimise.fit(log)
        assert done["fitted"] is False
        assert done["reviews"] == 3
        assert str(review.MIN_REVIEWS_TO_FIT) in done["why_ru"]

    def test_nothing_is_recorded_when_it_refuses(self, cards):
        a_review(cards, 3)
        with evidence.connect() as log:
            optimise.fit(log)
        assert review.parameters() is None


class TestTheHistoryItReads:
    def test_every_recorded_review_becomes_a_review_log(self, cards):
        a_review(cards, 5)
        with evidence.connect() as log:
            assert len(optimise.review_logs(log)) == 5

    def test_a_card_keeps_one_identity_across_its_reviews(self, cards):
        """FSRS fits per card; two reviews of the same card must not look like
        two different cards."""
        item = review.add(cards, "obj-case", "raamat", "küsimus", "vastus",
                          tag="obj-case")
        review.grade(cards, item, "good", auto=True)
        review.grade(cards, item, "again", auto=True)
        with evidence.connect() as log:
            ids = {entry.card_id for entry in optimise.review_logs(log)}
        assert len(ids) == 1


class TestParametersAreEvidence:
    def test_the_scheduler_uses_what_was_fitted(self):
        """A fit is a small move from the defaults, and it is what schedules."""
        from fsrs.scheduler import DEFAULT_PARAMETERS

        fitted = [round(p * 1.1, 4) for p in DEFAULT_PARAMETERS]
        evidence.record("fsrs-parameters", {"parameters": fitted, "reviews": 1200})
        assert review.parameters() == tuple(fitted)
        assert list(review._scheduler().parameters) == fitted

    def test_the_defaults_stand_until_something_was_fitted(self):
        from fsrs import Scheduler

        assert review.parameters() is None
        assert list(review._scheduler().parameters) == list(Scheduler().parameters)

    def test_parameters_that_fsrs_refuses_do_not_break_review(self):
        """A bad fit must cost the defaults, never the review screen."""
        evidence.record("fsrs-parameters", {"parameters": [1.0, 2.0], "reviews": 1200})
        from fsrs import Scheduler

        assert list(review._scheduler().parameters) == list(Scheduler().parameters)

    def test_they_survive_a_rebuild(self, cards):
        """They are derived from the learner's history, so they travel with it."""
        from fsrs.scheduler import DEFAULT_PARAMETERS

        fitted = [round(p * 1.1, 4) for p in DEFAULT_PARAMETERS]
        evidence.record("fsrs-parameters", {"parameters": fitted, "reviews": 1200})
        evidence.rebuild()
        assert review.parameters() == tuple(fitted)


def test_forced_small_data_fit_never_changes_the_live_schedule(cards, monkeypatch):
    import fsrs
    from fsrs.scheduler import DEFAULT_PARAMETERS

    class Trial:
        def __init__(self, history):
            pass

        def compute_optimal_parameters(self):
            return DEFAULT_PARAMETERS

    monkeypatch.setattr(fsrs, 'Optimizer', Trial, raising=False)
    a_review(cards, 3)
    with evidence.connect() as log:
        result = optimise.fit(log, force=True)
    assert result['fitted'] and not result['applied']
    assert review.parameters() is None
