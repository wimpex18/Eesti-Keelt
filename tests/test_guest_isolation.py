"""The guest never writes into the owner's permanence (ADR-0006).

SKELETON: every test names a requirement from `docs/identity.md`. Remove the
module-level skip, implement each test against the real app (`client` with
`x-eesti-scope: guest` and `x-eesti-guest: <name>`), and keep them all.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="ADR-0006 skeleton: implemented with the feature")

GUEST = {"x-eesti-scope": "guest", "x-eesti-guest": "t1"}


def test_a_guest_answer_changes_no_owner_database(client):
    """Answer a drill as a guest; every owner file under `config.*_DB` is
    byte-identical (or still absent) afterwards, and the guest's events.db has
    the attempt with `learner == "guest:t1"`."""


def test_owner_and_guest_see_their_own_progress(client):
    """Owner answers topic A, guest answers topic B: `/api/status` and
    `/api/me` differ accordingly, in both directions."""


def test_two_sandboxes_do_not_see_each_other(client):
    """`x-eesti-guest: a` and `b` have separate logs and projections."""


def test_a_new_guest_is_issued_a_sandbox_cookie(client):
    """No header and no cookie: the response sets `eesti_guest`; the next
    request with that cookie lands in the same sandbox."""


def test_guest_responses_carry_no_events_seq(client):
    """`x-events-seq` is owner-only, so the owner Worker never pulls guest events."""


def test_the_guest_log_needs_no_restore(client, monkeypatch):
    """With `EESTI_WORKER_RESTORES=1` an owner write before restore is 503;
    a guest write succeeds."""


def test_the_snapshot_and_export_routes_carry_only_the_owner(client, monkeypatch):
    """`/api/state/export` and `/api/events` (with STATE_TOKEN) list owner
    rows only, even after guest activity."""


def test_a_guest_sees_the_same_material_as_the_owner(client):
    """Library sections and counts are identical in both scopes: no licence
    gating by scope (ADR-0006, 6)."""


def test_every_route_is_classified_for_a_guest(client):
    """Each path in `eesti.api.paths()` is in exactly one row of
    `docs/identity.md` "Routes for a guest". A new route fails this until
    classified."""


def test_owner_only_actions_are_refused_to_a_guest(client):
    """`/api/notion/push`, every `/api/eval/*` route and
    `/api/reminders/settings` answer 403 with Russian text to a guest."""


def test_guest_allowances_are_shared_and_smaller(client, monkeypatch):
    """Two sandboxes spend one `budget.GUEST_CAPS` allowance in
    `config.guest_shared_db()`; the owner's `progress.db` budget is untouched."""


def test_guest_reset_empties_the_sandbox_and_refuses_the_owner(client):
    """POST /api/guest/reset: guest sandbox gone and next `/api/me` empty;
    as owner, 403."""


def test_idle_and_surplus_sandboxes_are_swept(tmp_path, monkeypatch):
    """`guest.sweep` drops sandboxes idle past IDLE_HOURS and the oldest past
    MAX_SANDBOXES, never `shared.db`."""
