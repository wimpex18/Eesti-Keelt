"""Who a request is for (ADR-0006): the scope the Worker's Access identity
selects, and the databases that scope gets. `eesti/identity.py`,
`config.learner_db`."""

from __future__ import annotations

from pathlib import Path

import pytest

from eesti import config, identity
from eesti.identity import GUEST, LEARNER, OWNER, Scope

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

    def test_a_learner_is_known_by_their_email(self):
        scope = identity.resolve(
            {**WORKER, "x-eesti-scope": "learner", "x-eesti-email": "Her@Example.com"},
            {}, GUARDED)
        assert scope.kind == LEARNER and scope.permanent
        assert scope.id == identity.learner_id("her@example.com")

    def test_a_learner_without_an_email_is_refused(self):
        assert identity.resolve({**WORKER, "x-eesti-scope": "learner"}, {}, GUARDED) is None

    def test_a_testing_account_is_a_guest_with_its_email(self):
        scope = identity.resolve(
            {**WORKER, "x-eesti-scope": "guest", "x-eesti-email": "test@example.com",
             "x-eesti-guest": "codex-run"}, {}, GUARDED)
        assert scope == Scope(GUEST, id="codex-run", email="test@example.com")
        assert not scope.permanent

    def test_a_service_token_guest_has_no_email(self):
        scope = identity.resolve({**WORKER, "x-eesti-scope": "guest"}, {}, GUARDED)
        assert scope.is_guest and scope.email is None

    @pytest.mark.parametrize("token", ["", "wrong"])
    def test_without_the_worker_token_nothing_is_answered(self, token):
        headers = {"x-proxy-token": token, "x-eesti-scope": "owner"}
        assert identity.resolve(headers, {}, GUARDED) is None

    def test_an_unknown_scope_is_refused_rather_than_written_anywhere(self):
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


class TestLearnerIds:
    def test_the_id_is_stable_and_ignores_case_and_spaces(self):
        assert identity.learner_id(" A@B.ee ") == identity.learner_id("a@b.ee")

    def test_the_id_is_a_safe_name_that_does_not_reveal_the_email(self):
        lid = identity.learner_id("a@b.ee")
        assert identity.sandbox_name(lid) == lid and "b.ee" not in lid

    def test_the_worker_computes_the_same_id(self):
        # `deploy/worker.ts` must derive the same value (SHA-256, first 16 hex).
        assert identity.learner_id("a@b.ee") == "l-" + __import__(
            "hashlib").sha256(b"a@b.ee").hexdigest()[:16]


class TestSandboxes:
    def test_a_cookie_keeps_the_sandbox(self):
        scope = identity.resolve({"x-eesti-scope": "guest"}, {"eesti_guest": "g-abc"}, {})
        assert scope.id == "g-abc" and not scope.issued

    def test_a_new_caller_is_issued_one(self):
        scope = identity.resolve({"x-eesti-scope": "guest"}, {}, {})
        assert scope.issued and identity.sandbox_name(scope.id) == scope.id

    @pytest.mark.parametrize("raw", ["../owner", "a/b", "", "x" * 41, ".hidden", "Ä"])
    def test_a_name_that_is_not_a_safe_directory_is_ignored(self, raw):
        assert identity.sandbox_name(raw) is None

    def test_events_name_their_learner(self):
        assert Scope(GUEST, id="t1").learner == "guest:t1"
        assert Scope(LEARNER, id="l-0123456789abcdef").learner == "l-0123456789abcdef"
        assert Scope().learner == "owner"


class TestLearnerDatabases:
    def test_the_owner_keeps_the_redirected_paths(self):
        assert config.learner_db("PROGRESS_DB") == config.PROGRESS_DB

    @pytest.mark.parametrize("kind,root", [(GUEST, "GUEST_DIR"), (LEARNER, "LEARNERS_DIR")])
    def test_everyone_else_gets_their_own_files(self, kind, root):
        with identity.use(Scope(kind, id="t1")):
            paths = {config.learner_db(n) for n in config._LEARNER_FILES}
        assert {Path(p).parent for p in paths} == {Path(getattr(config, root)) / "t1"}
        assert config.PROGRESS_DB not in paths

    def test_the_scope_is_restored_after_the_block(self):
        with identity.use(Scope(GUEST, id="t1")):
            pass
        assert identity.current() == Scope()
