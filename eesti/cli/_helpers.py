"""Resolving the databases a command reads and writes.

Every path is resolved when the command runs, from `config` or from the flag —
never from a literal in an argparse default, which is what these replaced. A
literal there ignored `EESTI_CONTENT_DB` (how the Dockerfile points the app at
its content volume) and could not be redirected by a test, so the suite wrote
into the learner's own `data/progress.db`.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

def words_db(path=None) -> sqlite3.Connection | None:
    """The word list, and never an empty one invented on the spot.

    The twin of `content_db`, for the same reason and the fourth instance of
    the same bug: `wordlist.connect` creates the file and applies the schema,
    so a wrong or unbuilt path hands back a database that looks complete and
    holds nothing. Downstream that surfaces as a drill generator reporting "no
    usable templates" or a lookup finding no word -- both of which read as
    "this feature is broken" rather than "nothing has been built here yet".

    Returns None, having said what to run, when there is no word list.
    """
    from ..wordlist import available
    from ..wordlist import connect as wordlist_connect

    if not available(path):
        print("no word list built — run `python -m eesti.cli fetch-data`"
              " and then `python -m eesti.cli build`")
        return None
    return wordlist_connect(path)


def content_db(args: argparse.Namespace) -> sqlite3.Connection | None:
    """The harvested library, resolved at call time and never invented.

    Three commands carried `default="data/content.db"` in their argparse
    definition. That is a literal, so it ignored `EESTI_CONTENT_DB` -- which is
    exactly how the Dockerfile points the app at its content volume -- and no
    caller or test could redirect it.

    Worse, `sqlite3.connect` on a path that does not exist *creates* an empty
    file. So a missing corpus did not report a missing corpus: it reported
    `no such table: items`, three frames deep. That is the third time this
    project has been bitten by presence of a database being read as presence
    of data.

    Returns None, having said why, when there is no corpus to read.
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
    print(f"\n   {item.prompt}")
    print(f"   ({item.hint})")
    try:
        return input("   > ")
    except (EOFError, KeyboardInterrupt):
        return ""


def _row_of(record) -> "object":
    from ..notion import Row

    return Row(
        wrong=record["wrong"], correct=record["correct"], why=record["why"],
        tag=record["tag"], on_date=record["on_date"],
    )
