"""`arvud`: the numbers 0–100 as words, written and heard.

The spelling is EKK O 42 (*Arvsõnade kokku- ja lahkukirjutamine*): *-teist(kümmend)*
and *-kümmend* join the numeral before them, so both *kolmteist* and
*kolmteistkümmend* are right; any other numeral stands apart (*nelikümmend
kolm*). Every word is one Vabamorf reads as a numeral (a test holds this).

Two rules:

- **kirjuta** — see the digits, write the words. The distractor is the confusion
  the spelling invites: *-teist* against *-kümmend* (13 and 30), or a compound
  written as one word.
- **kuula** — hear the number (EKI's recording where there is one, synthesis
  otherwise) and write it in digits.
"""

from __future__ import annotations

import random

from .item import BLANK
from .patterns import PatternDrill

UNITS = ("null", "üks", "kaks", "kolm", "neli", "viis", "kuus", "seitse",
         "kaheksa", "üheksa", "kümme")

BASE_RULES = ("kirjuta", "kuula")


def written(n: int) -> str:
    """`n` (0–100) in words; parallel forms joined by ` ~ ` (`item.accepts`)."""
    if not 0 <= n <= 100:
        raise ValueError(f"{n} is outside 0–100")
    if n <= 10:
        return UNITS[n]
    if n < 20:
        stem = UNITS[n - 10]
        return f"{stem}teist ~ {stem}teistkümmend"
    if n == 100:
        return "sada"
    tens, units = divmod(n, 10)
    word = f"{UNITS[tens]}kümmend"
    return f"{word} {UNITS[units]}" if units else word


def _first(n: int) -> str:
    return written(n).split(" ~ ")[0]


def _confusion(n: int, rng: random.Random) -> str:
    """The wrong spelling a learner reaches for, never another right one."""
    if 11 <= n <= 19:
        return f"{UNITS[n - 10]}kümmend"            # 13 written as 30
    if n >= 20 and n % 10 == 0 and n < 100:
        return f"{UNITS[n // 10]}teist"             # 30 written as 13
    if 21 <= n <= 99:
        return _first(n).replace(" ", "")           # one word, against EKK O 42
    other = rng.choice([m for m in range(11) if m != n])
    return UNITS[other]


_WHY_WRITE = ("Числительные на **-teist** и **-kümmend** пишутся слитно "
              "(*kolmteist*, *viiskümmend*), остальные — раздельно: *nelikümmend "
              "kolm*. Можно и *kolmteistkümmend* (EKK O 42).")
_WHY_HEAR = ("Слушай окончание: **-teist** — от 11 до 19 (*kolmteist* = 13), "
             "**-kümmend** — десятки (*kolmkümmend* = 30).")


def drills(count: int = 10, seed: int | None = None,
           rules: tuple[str, ...] | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    wanted = [r for r in (rules or BASE_RULES) if r in BASE_RULES]
    if not wanted:
        return []
    numbers = list(range(101))
    rng.shuffle(numbers)
    out: list[PatternDrill] = []
    for i in range(count):
        n = numbers[i % len(numbers)]
        rule = wanted[i % len(wanted)]
        if rule == "kirjuta":
            out.append(PatternDrill(
                f"{n} = {BLANK}", written(n), _confusion(n, rng), "", "sõnadega",
                "kirjuta", _WHY_WRITE, "arvud"))
        else:
            near = [m for m in (n + 10, n - 10, n + 1, n - 1) if 0 <= m <= 100]
            out.append(PatternDrill(
                f"Kuula ja kirjuta numbritega: {BLANK}", str(n), str(rng.choice(near)),
                "", "numbritega", "kuula", _WHY_HEAR, "arvud", say=_first(n),
                translate=False))
    return out
