"""Who a request is for (ADR-0006): the scope a front door's secret selects, and
the databases that scope gets. `eesti/identity.py`, `config.learner_db`."""

from __future__ import annotations

from pathlib import Path

import pytest

from eesti import config, identity
from eesti.identity import GUEST, OWNER, Scope

GUARDED = {"PROXY_TOKEN": "worker-secret"}
WORKER = {"x-proxy-token": "worker-secret"}


class TestBehindTheWorker:
    def test_no_scope_header_is_the_owner_as_before(self):
        assert identity.resolve(WORKER, {}, GUARDED) == Scope(OWNER)

    def test_the_owner_carries_the_access_email(self):
        scope = identity.resolve(
            {**WORKER, "x-eesti-scope": "owner", "x-eesti-email": "me@example.com"},
            {}, GUARDED)
        assert scope == Scope(OWNER, email="me@example.com")

    def test_a_second_account_is_a_guest_with_its_email(self):
        scope = identity.resolve(
            {**WORKER, "x-eesti-scope": "guest", "x-eesti-email": "test@example.com",
             "x-eesti-guest": "codex-run"}, {}, GUARDED)
        assert scope == Scope(GUEST, sandbox="codex-run", email="test@example.com")

    def test_a_service_token_guest_has_no_email(self):
        scope = identity.resolve({**WORKER, "x-eesti-scope": "guest"}, {}, GUARDED)
        assert scope.is_guest and scope.email is None

    @pytest.mark.parametrize("token", ["", "wrong"])
    def test_without_the_worker_token_nothing_is_answered(self, token):
        headers = {"x-proxy-token": token, "x-eesti-scope": "owner"}
        assert identity.resolve(headers, {}, GUARDED) is None

    def test_an_unknown_scope_is_refused_rather_than_written_to_the_owner(self):
        assert identity.resolve({**WORKER, "x-eesti-scope": "gust"}, {}, GUARDED) is None

    def test_the_local_default_does_not_apply_behind_the_worker(self):
        env = {**GUARDED, "EESTI_SCOPE": "guest"}
        assert identity.resolve(WORKER, {}, env) == Scope(OWNER)


class TestLocally:
    def test_the_default_is_the_owner(self):
        assert identity.resolve({}, {}, {}) == Scope(OWNER)

    def test_a_header_or_the_environment_chooses_a_guest(self):
        assert identity.resolve({"x-eesti-scope": "guest"}, {}, {}).is_guest
        assert identity.resolve({}, {}, {"EESTI_SCOPE": "guest"}).is_guest


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
