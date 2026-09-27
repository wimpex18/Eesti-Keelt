"""Who a request is for (ADR-0006): the scope a front door's secret selects, and
the databases that scope gets. `eesti/identity.py`, `config.learner_db`."""

from __future__ import annotations

from pathlib import Path

import pytest

from eesti import config, identity
from eesti.identity import GUEST, OWNER, Scope

GUARDED = {"PROXY_TOKEN": "owner-secret", "GUEST_PROXY_TOKEN": "guest-secret"}


class TestOnTheDeployment:
    def test_the_owner_token_is_the_owner_with_the_access_email(self):
        scope = identity.resolve(
            {"x-proxy-token": "owner-secret", "x-eesti-email": "me@example.com"},
            {}, GUARDED)
        assert scope == Scope(OWNER, email="me@example.com")

    def test_the_guest_token_is_a_public_guest(self):
        scope = identity.resolve(
            {"x-proxy-token": "guest-secret", "x-eesti-guest": "codex-run"}, {}, GUARDED)
        assert scope.kind == GUEST and scope.public and scope.sandbox == "codex-run"

    def test_no_header_promotes_a_guest(self):
        scope = identity.resolve(
            {"x-proxy-token": "guest-secret", "x-eesti-scope": "owner"}, {}, GUARDED)
        assert scope.is_guest

    def test_a_guest_never_carries_an_email(self):
        scope = identity.resolve(
            {"x-proxy-token": "guest-secret", "x-eesti-email": "me@example.com"},
            {}, GUARDED)
        assert scope.email is None

    @pytest.mark.parametrize("token", ["", "wrong", "guest-secret"])
    def test_anything_else_is_refused(self, token):
        env = {"PROXY_TOKEN": "owner-secret"}   # no guest Worker configured
        assert identity.resolve({"x-proxy-token": token}, {}, env) is None


class TestLocally:
    def test_the_default_is_the_owner(self):
        assert identity.resolve({}, {}, {}) == Scope(OWNER)

    def test_a_header_chooses_a_private_guest(self):
        scope = identity.resolve({"x-eesti-scope": "guest"}, {}, {})
        assert scope.is_guest and not scope.public

    def test_an_unknown_scope_is_refused_rather_than_written_to_the_owner(self):
        assert identity.resolve({"x-eesti-scope": "gust"}, {}, {}) is None


class TestSandboxes:
    def test_a_cookie_keeps_the_sandbox(self):
        scope = identity.resolve({"x-eesti-scope": "guest"}, {"eesti_guest": "g-abc"}, {})
        assert scope.sandbox == "g-abc" and not scope.issued

    def test_a_new_caller_is_issued_one(self):
        scope = identity.resolve({"x-eesti-scope": "guest"}, {}, {})
        assert scope.issued and identity.sandbox_name(scope.sandbox) == scope.sandbox

    @pytest.mark.parametrize("raw", ["../owner", "a/b", "", "x" * 41, ".hidden", "Ä"])
    def test_a_name_that_is_not_a_safe_directory_is_ignored(self, raw):
        assert identity.sandbox_name(raw) is None

    def test_guest_events_name_their_sandbox(self):
        assert Scope(GUEST, sandbox="t1").learner == "guest:t1"
        assert Scope().learner == "owner"


class TestLearnerDatabases:
    def test_the_owner_keeps_the_redirected_paths(self):
        assert config.learner_db("PROGRESS_DB") == config.PROGRESS_DB

    def test_a_guest_gets_its_own_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "GUEST_DIR", str(tmp_path / "guest"))
        with identity.use(Scope(GUEST, sandbox="t1")):
            paths = {config.learner_db(n) for n in config._LEARNER_FILES}
        assert {Path(p).parent for p in paths} == {tmp_path / "guest" / "t1"}
        assert config.PROGRESS_DB not in paths

    def test_the_scope_is_restored_after_the_block(self):
        with identity.use(Scope(GUEST, sandbox="t1")):
            pass
        assert identity.current() == Scope()
