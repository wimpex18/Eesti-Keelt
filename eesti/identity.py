"""Who a request is for: a signed-in learner, or a guest sandbox (ADR-0006).

Klint opens publicly and accounts live in the app. The
Worker owns sign-up, sign-in and the session cookie (`deploy/worker.ts`), and
tells the origin who is signed in (`x-eesti-scope`, `x-eesti-learner`,
`x-eesti-email`):

- `owner`: the operator-provisioned account. It inherits the progress recorded
  before accounts existed: the old file paths and the old Durable Object.
- `learner`: every public sign-up, each with its own permanent store.
  Permanent, with its own files and Durable Object, named by its account id.
- `guest`: no session. Claude, Codex and tests use the full app in a throwaway
  sandbox and never sign up.

The origin trusts those headers only on a request carrying `PROXY_TOKEN`,
which only the Worker holds. A request with no scope header is the owner, as
before accounts existed, so an older Worker keeps working unchanged. Without
`PROXY_TOKEN` (`cli serve`, tests) the guard is off and the same headers, or
`EESTI_SCOPE`, choose; the default is the owner.

The scope travels in a context variable for the length of one request, so
`config.learner_db` can hand each request its own databases without any route
knowing. Nothing here opens a file.
"""

from __future__ import annotations

import hmac
import re
import secrets
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

OWNER = "owner"
LEARNER = "learner"
GUEST = "guest"
SCOPES = (OWNER, LEARNER, GUEST)

#: Set by the Worker from the session; locally, by a test or developer.
SCOPE_HEADER = "x-eesti-scope"
#: A learner's account id, set by the Worker from the session.
LEARNER_HEADER = "x-eesti-learner"
#: The account's email, set by the Worker from the session.
EMAIL_HEADER = "x-eesti-email"
#: Names a guest sandbox: agents and tests pick a readable one.
SANDBOX_HEADER = "x-eesti-guest"
#: Keeps a browser in the sandbox it was given on first contact.
SANDBOX_COOKIE = "eesti_guest"

#: A sandbox name is also a directory name: short, lower case, no dots.
_SANDBOX = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


#: An account id as the Worker issues it: `l-` and 16 lower-case hex digits.
_LEARNER_ID = re.compile(r"^l-[0-9a-f]{16}$")


def learner_id(raw: str | None) -> str | None:
    """A learner account id from the Worker, or None when it is malformed."""
    value = (raw or "").strip()
    return value if _LEARNER_ID.fullmatch(value) else None


@dataclass(frozen=True)
class Scope:
    kind: str = OWNER
    #: `owner`, the account id for a learner, the sandbox name for a guest.
    id: str = OWNER
    #: The account's email; None for a guest.
    email: str | None = None
    #: The sandbox was made up for this request; the response sets the cookie.
    issued: bool = False

    @property
    def is_guest(self) -> bool:
        return self.kind == GUEST

    @property
    def permanent(self) -> bool:
        return self.kind in (OWNER, LEARNER)

    @property
    def learner(self) -> str:
        """The `learner` field of an event recorded in this scope."""
        return self.id if self.kind != GUEST else f"{GUEST}:{self.id}"


OWNER_SCOPE = Scope()

_current: ContextVar[Scope] = ContextVar("eesti_scope", default=OWNER_SCOPE)


def current() -> Scope:
    """The scope of the request being answered; the owner outside a request."""
    return _current.get()


@contextmanager
def use(scope: Scope) -> Iterator[Scope]:
    """Answer everything inside the block in `scope`, then restore the previous one."""
    token = _current.set(scope)
    try:
        yield scope
    finally:
        _current.reset(token)


def sandbox_name(raw: str | None) -> str | None:
    """A caller's sandbox name, or None when it is not a safe directory name."""
    name = (raw or "").strip().lower()
    return name if _SANDBOX.fullmatch(name) else None


def resolve(headers: Mapping[str, str], cookies: Mapping[str, str],
            env: Mapping[str, str]) -> Scope | None:
    """The request's scope, or None when it must be refused (403).

    `headers` must be case-insensitive or lower-cased (Starlette's are).
    """
    expected = env.get("PROXY_TOKEN") or ""
    if expected and not hmac.compare_digest(headers.get("x-proxy-token") or "", expected):
        return None

    email = (headers.get(EMAIL_HEADER) or "").strip() or None
    default = OWNER if expected else (env.get("EESTI_SCOPE") or OWNER)
    kind = (headers.get(SCOPE_HEADER) or default).strip().lower()

    if kind == OWNER:
        if not expected:
            email = email or (env.get("EESTI_OWNER_EMAIL") or "").strip() or None
        return Scope(OWNER, email=email)
    if kind == LEARNER:
        # A permanent learner is known by their account id: none, no store.
        lid = learner_id(headers.get(LEARNER_HEADER))
        return Scope(LEARNER, id=lid, email=email) if lid else None
    if kind != GUEST:
        return None   # a typo must not write into anyone's permanent log

    named = sandbox_name(headers.get(SANDBOX_HEADER)) or sandbox_name(
        cookies.get(SANDBOX_COOKIE))
    if named:
        return Scope(GUEST, id=named)
    return Scope(GUEST, id=f"g-{secrets.token_hex(6)}", issued=True)
