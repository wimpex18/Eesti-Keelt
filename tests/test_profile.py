"""The profile (ADR-0006, `docs/identity.md` "Profile").

SKELETON: remove the skip and implement each test with the feature.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="ADR-0006 skeleton: implemented with the feature")


def test_an_empty_log_is_a_profile_with_nothing_yet(client):
    """`GET /api/me` on a fresh store: every key present, name/since/last_active
    null, zero totals, 84 rhythm days, milestones for A1, A2 and B1."""


def test_the_name_is_set_trimmed_and_read_back(client):
    """POST `{"name": "  Sergey   Z "}` → name "Sergey Z"; a `profile-set`
    event is in the log; the next GET returns it."""


def test_a_blank_name_clears_it_and_a_long_one_is_refused(client):
    """Blank → null; 61 characters → 400 with a Russian detail."""


def test_profile_set_survives_strict_replay(tmp_path):
    """An export holding `profile-set` passes `recovery` strict replay
    (`cli verify-backup`)."""


def test_the_email_comes_from_the_front_door(client, monkeypatch):
    """With PROXY_TOKEN set, `x-eesti-email` is echoed as `email` in both
    scopes, `scope` says which; without the header `email` is null."""


def test_level_milestones_and_rhythm_match_their_own_routes(client):
    """After some practice, `level.current` is the resume topic's level and
    `milestones`/`rhythm` equal `/api/milestones/{level}` and `/api/status`."""
