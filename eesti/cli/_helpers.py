"""Resolving the databases a command reads and writes: at run time, from `config`
or the flag — never a literal argparse default, which would ignore
`EESTI_CONTENT_DB` and escape test redirection.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

def words_db(path=None) -> sqlite3.Connection | None:
    """The word list, or None (after printing what to run) when none is built.
    `wordlist.connect` would create an empty file.
    """
    from ..wordlist import available
    from ..wordlist import connect as wordlist_connect

    if not available(path):
        print("no word list built — run `python -m eesti.cli fetch-data`"
              " and then `python -m eesti.cli build`")
        return None
    return wordlist_connect(path)


def content_db(args: argparse.Namespace) -> sqlite3.Connection | None:
    """The harvested library, resolved at call time, or None (after saying why) when
    there is no corpus. `sqlite3.connect` would create an empty file.
    """
    import sqlite3

    from .. import config
    from ..sources import connect as open_content

    path = Path(getattr(args, "content_db", None) or config.CONTENT_DB)
    if not path.exists():
        print(f"no content database at {path} — run `cli harvest-reading` "
              f"first, or set EESTI_CONTENT_DB")
        return None
    # The app's own opener, so the CLI sees the schema production has rather
    # than whatever `sqlite3.connect` leaves behind on a path with no file.
    conn = open_content(path)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    except sqlite3.OperationalError:
        print(f"{path} has no items table — run `cli harvest-reading`")
        return None
    if not rows:
        print(f"{path} is empty — run `cli harvest-reading` first")
        return None
    return conn


def content_path(args: argparse.Namespace) -> str:
    """Where a harvest writes. Same resolution as `content_db`, for the
    commands that create the library rather than read it."""
    from .. import config

    return str(getattr(args, "db", None) or config.CONTENT_DB)


def learner_db(args: argparse.Namespace, which: str) -> str:
    """Path for one of the learner's databases, resolved at call time."""
    from .. import config

    return str(getattr(args, which, None)
               or getattr(config, which.upper()))


def _ask_terminal(item) -> str:
    """Ask one item at the terminal, or raise `Stopped` on EOF/Ctrl-C — never return a
    blank, which would grade as wrong (see `placement.Stopped`).
    """
    from ..placement import Stopped

    print(f"\n   {item.prompt}")
    print(f"   ({item.hint})")
    try:
        return input("   > ")
    except (EOFError, KeyboardInterrupt) as exc:
        raise Stopped from exc


def _row_of(record) -> "object":
    from ..notion import Row

    return Row(
        wrong=record["wrong"], correct=record["correct"], why=record["why"],
        tag=record["tag"], on_date=record["on_date"],
    )
