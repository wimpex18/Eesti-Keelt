"""Who a request is for: the owner, or a guest sandbox (ADR-0006).

The front door decides, never the page. On the deployment the origin reads the
scope off the secret the Worker presents: `PROXY_TOKEN` is the owner's Worker
(behind Cloudflare Access), `GUEST_PROXY_TOKEN` the guest Worker (no Access).
A header cannot promote a guest to the owner, because the guest Worker does
not hold the owner's token. Without `PROXY_TOKEN` (`cli serve`, tests) the
origin guard is off, and `x-eesti-scope` or `EESTI_SCOPE` chooses; the default
is the owner, as before.

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
GUEST = "guest"
SCOPES = (OWNER, GUEST)

#: Chooses the scope where the origin guard is off (local, tests).
SCOPE_HEADER = "x-eesti-scope"
#: Names a guest sandbox: agents and tests pick a readable one.
SANDBOX_HEADER = "x-eesti-guest"
#: Keeps a browser in the sandbox it was given on first contact.
SANDBOX_COOKIE = "eesti_guest"
#: The owner's Access email, set by the owner Worker from `ctx.access`.
EMAIL_HEADER = "x-eesti-email"

#: A sandbox name is also a directory name: short, lower case, no dots.
_SANDBOX = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


@dataclass(frozen=True)
class Scope:
    kind: str = OWNER
    #: The guest sandbox; None for the owner.
    sandbox: str | None = None
    #: Reached from the public guest host: owner-only material is withheld.
    public: bool = False
    #: The owner's sign-in email when the front door knows it.
    email: str | None = None
    #: The sandbox was made up for this request; the response sets the cookie.
    issued: bool = False

    @property
    def is_guest(self) -> bool:
        return self.kind == GUEST

    @property
    def learner(self) -> str:
        """The `learner` field of an event recorded in this scope."""
        return f"{GUEST}:{self.sandbox}" if self.is_guest else OWNER


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


def _guest(headers: Mapping[str, str], cookies: Mapping[str, str],
           public: bool) -> Scope:
    named = sandbox_name(headers.get(SANDBOX_HEADER)) or sandbox_name(
        cookies.get(SANDBOX_COOKIE))
    if named:
        return Scope(GUEST, sandbox=named, public=public)
    return Scope(GUEST, sandbox=f"g-{secrets.token_hex(6)}", public=public,
                 issued=True)


def resolve(headers: Mapping[str, str], cookies: Mapping[str, str],
            env: Mapping[str, str]) -> Scope | None:
    """The request's scope, or None when it must be refused (403).

    `headers` must be case-insensitive or lower-cased (Starlette's are).
    """
    owner_token = env.get("PROXY_TOKEN") or ""
    guest_token = env.get("GUEST_PROXY_TOKEN") or ""
    presented = headers.get("x-proxy-token") or ""

    if owner_token:
        if hmac.compare_digest(presented, owner_token):
            return Scope(OWNER, email=(headers.get(EMAIL_HEADER) or "").strip() or None)
        if guest_token and hmac.compare_digest(presented, guest_token):
            return _guest(headers, cookies, public=True)
        return None

    # The guard is off: a developer's machine or a test client.
    kind = (headers.get(SCOPE_HEADER) or env.get("EESTI_SCOPE") or OWNER).strip().lower()
    if kind == OWNER:
        return Scope(OWNER, email=(env.get("EESTI_OWNER_EMAIL") or "").strip() or None)
    if kind == GUEST:
        return _guest(headers, cookies, public=env.get("EESTI_GUEST_PUBLIC") == "1")
    return None
