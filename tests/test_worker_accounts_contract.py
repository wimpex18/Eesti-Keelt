"""Pin the Worker's identity boundary to the origin's account contract."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = (ROOT / "deploy" / "worker.ts").read_text(encoding="utf-8")
IDENTITY = (ROOT / "eesti" / "identity.py").read_text(encoding="utf-8")


def _block(signature: str) -> str:
    start = WORKER.index(signature)
    opening = WORKER.index("{", start)
    depth = 0
    for at in range(opening, len(WORKER)):
        if WORKER[at] == "{":
            depth += 1
        elif WORKER[at] == "}":
            depth -= 1
            if depth == 0:
                return WORKER[opening + 1:at]
    raise AssertionError(f"unterminated Worker block: {signature}")


def test_untrusted_scope_headers_are_removed_and_rebuilt_from_session():
    headers = _block("function applyScopeHeaders(")
    for name in ("x-eesti-scope", "x-eesti-learner", "x-eesti-email"):
        assert f'headers.delete("{name}")' in headers
    assert 'headers.set("x-eesti-scope", who.scope)' in headers
    assert 'headers.set("x-eesti-learner", who.id)' in headers
    assert 'headers.set("x-eesti-email", who.email)' in headers


def test_auth_routes_terminate_at_the_worker():
    for route in ("me", "signup", "login", "logout"):
        assert f'"/api/auth/{route}"' in WORKER


def test_guests_have_no_durable_object_and_cannot_use_push():
    object_picker = _block("async function stubFor(")
    assert 'who.scope === "guest"' in object_picker
    assert "return null" in object_picker
    push_route = WORKER[WORKER.index('if (url.pathname.startsWith("/api/push/"))'):]
    assert "if (!learner)" in push_route
    assert "status: 403" in push_route


def test_worker_and_origin_accept_the_same_learner_id_shape():
    worker = _block("export function learnerId(")
    origin = re.search(r"_LEARNER_ID\s*=\s*re\.compile\(r\"([^\"]+)\"\)", IDENTITY)
    assert origin, "Python learner ID validator was not found"
    worker_shape = re.search(r"return /([^/]+)/\.test\(raw\)", worker)
    assert worker_shape, "Worker learner ID validator was not found"
    assert worker_shape.group(1) == origin.group(1)


def test_signups_are_not_closed_after_a_fixed_number_of_accounts():
    create = (ROOT / "deploy" / "accounts.ts").read_text(encoding="utf-8")
    assert "MAX_ACCOUNTS" not in create
    assert "DEFAULT_MAX_ACCOUNTS" not in create
    assert "sign-up remains open with no account limit" in WORKER.lower() or "signupopen: true" in WORKER.lower()


def test_reminder_cron_visits_the_owner_and_each_registered_learner():
    scheduled = _block("async scheduled(")
    assert "accountList()" in scheduled
    assert 'scope: "learner"' in scheduled
    assert "ctx.waitUntil(learner.remind())" in scheduled
