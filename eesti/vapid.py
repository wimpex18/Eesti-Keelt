"""The key pair reminders are signed with (VAPID, RFC 8292).

One key pair, made once, kept in `.env` and pushed to the Worker as a secret.
Generating it needs a P-256 key, and the whole of that is written here rather
than pulled in as a dependency: `cryptography` is a compiled extension, and
this is thirty lines of integer arithmetic used exactly once in the life of the
project.

The curve is NIST P-256 (secp256r1), the one Web Push requires. The private key
is a random scalar `d`; the public key is `d·G` as an uncompressed point
(`0x04 || x || y`), which is the form both the browser and the push service
expect.
"""

from __future__ import annotations

import base64
import secrets

#: NIST P-256 (FIPS 186-4 D.1.2.3).
P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
A = P - 3
B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5

Point = tuple[int, int] | None


def _add(p: Point, q: Point) -> Point:
    """Point addition on P-256, with the point at infinity as None."""
    if p is None:
        return q
    if q is None:
        return p
    (x1, y1), (x2, y2) = p, q
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if p == q:
        slope = (3 * x1 * x1 + A) * pow(2 * y1, -1, P) % P
    else:
        slope = (y2 - y1) * pow(x2 - x1, -1, P) % P
    x3 = (slope * slope - x1 - x2) % P
    return (x3, (slope * (x1 - x3) - y1) % P)


def multiply(scalar: int, point: Point = (GX, GY)) -> Point:
    """`scalar · point`, double-and-add."""
    out: Point = None
    while scalar:
        if scalar & 1:
            out = _add(out, point)
        point = _add(point, point)
        scalar >>= 1
    return out


def on_curve(x: int, y: int) -> bool:
    return (y * y - (x * x * x + A * x + B)) % P == 0


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def generate() -> tuple[str, str]:
    """A fresh key pair as (public, private), both base64url.

    Public is the uncompressed point the browser subscribes with; private is the
    32-byte scalar the Worker signs with.
    """
    d = secrets.randbelow(N - 1) + 1
    x, y = multiply(d)
    if not on_curve(x, y):  # pragma: no cover - arithmetic error, not input
        raise RuntimeError("generated public key is not on P-256")
    return (b64(b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")),
            b64(d.to_bytes(32, "big")))
