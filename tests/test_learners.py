"""A household of permanent learners (ADR-0006, `docs/identity.md`).

SKELETON: every test names a requirement. Remove the skip and implement each
against the real app with the `HER` headers the Worker sends.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="ADR-0006 skeleton: implemented with the feature")

HER = {"x-eesti-scope": "learner", "x-eesti-learner": "l-0123456789abcdef",
       "x-eesti-email": "her@example.com"}


def test_two_learners_keep_separate_permanent_progress(client):
    """Owner answers topic A, the learner topic B: `/api/status`, `/api/review`
    and `/api/me` differ accordingly, and the learner's files are under
    `config.LEARNERS_DIR/l-0123456789abcdef/` while the owner's files are untouched."""


def test_a_learner_has_her_own_back_channel(client, monkeypatch):
    """With STATE_TOKEN and her scope headers, `/api/state/export`,
    `/api/events`, `/api/events/import` and `/api/reminders` read and write her
    files only; the owner's export is unchanged."""


def test_a_learner_is_restored_like_the_owner(client, monkeypatch):
    """With `EESTI_WORKER_RESTORES=1`, her first write before her restore is
    503; after `/api/events/import` with `settle`, writes succeed."""


def test_a_new_learner_is_registered_once(client, monkeypatch):
    """Settling an empty learner log records one `joined` event; settling again
    records none; `/api/me` `since` is its timestamp."""


def test_x_events_seq_reports_the_callers_own_log(client):
    """The header follows the learner's log, not the owner's."""


def test_owner_only_actions_are_refused_to_a_learner(client):
    """`/api/notion/push`, every `/api/eval/*`, `/api/content/*` and
    `/api/progress/reset` answer 403 with Russian text in learner scope."""


def test_learners_share_the_household_allowance(client, monkeypatch):
    """A learner's provider calls count in the owner's `progress.db` budget."""


def test_events_carry_the_learner_id(client):
    """Her events have `learner == "l-0123456789abcdef"`."""
