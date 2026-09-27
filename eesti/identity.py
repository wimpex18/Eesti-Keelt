"""Who a request is for: the owner, or a guest sandbox (ADR-0006).

Both come through the one Worker behind Cloudflare Access. The Worker reads
the Access identity and says which scope it is (`x-eesti-scope`): the owner's
email is the owner; any other Access identity (the owner's second, testing
account, or a service token for a headless agent) is a guest. The origin
trusts that header only on a request that carries `PROXY_TOKEN`, which only
the Worker holds. A request with no scope header is the owner, as before this
existed, so an older Worker keeps working unchanged.

Without `PROXY_TOKEN` (`cli serve`, tests) the origin guard is off and the
same header, or `EESTI_SCOPE`, chooses; the default is the owner.

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

#: Set by the Worker from the Access identity; locally, by a test or developer.
SCOPE_HEADER = "x-eesti-scope"
#: Names a guest sandbox: agents and tests pick a readable one.
SANDBOX_HEADER = "x-eesti-guest"
#: Keeps a browser in the sandbox it was given on first contact.
SANDBOX_COOKIE = "eesti_guest"
#: The Access email, set by the Worker from `ctx.access.getIdentity()`.
EMAIL_HEADER = "x-eesti-email"

#: A sandbox name is also a directory name: short, lower case, no dots.
_SANDBOX = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


@dataclass(frozen=True)
class Scope:
    kind: str = OWNER
    #: The guest sandbox; None for the owner.
    sandbox: str | None = None
    #: The Access email when the front door knows it (a service token has none).
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
    if kind != GUEST:
        return None   # a typo must not write into the owner's log

    named = sandbox_name(headers.get(SANDBOX_HEADER)) or sandbox_name(
        cookies.get(SANDBOX_COOKIE))
    if named:
        return Scope(GUEST, sandbox=named, email=email)
    return Scope(GUEST, sandbox=f"g-{secrets.token_hex(6)}", email=email, issued=True)
