"""Push confirmed errors into the existing Notion `Vead` log.

## Why this feeds an existing system instead of replacing it

There is already an error log, hand-kept, with a rule attached to it: three or
more rows sharing a tag become the focus of the week. That rule is what made
`obj-case` the priority in the first place. A second log inside this app would
have split the evidence in half and quietly broken the rule.

So this appends, and it appends in exactly the shape the log already has. The
schema was read off the live database rather than remembered:

| Property | Type | What goes in |
|---|---|---|
| `Vale (wrong)` | title | the erroneous fragment |
| `Õige (correct)` | text | the correction |
| `Miks (why)` | text | Russian explanation, Estonian grammar term |
| `Tag` | multi_select | one of the fixed nine in `config.TAGS` |
| `Kuupäev` | date | when it was checked |

## Why nothing is pushed automatically

**The log's value is that it is curated.** A checker that appended every
suspicion would turn a hand-picked record of real mistakes into a dump of model
output, and the "3+ occurrences" rule would start firing on noise. So a
correction is queued locally, shown, and pushed only when a person says so.

Queueing locally also means the network is never in the way of a study session:
Notion being unreachable delays a row, it does not interrupt a lesson.
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import TAGS

API = "https://api.notion.com/v1/pages"
#: Pinned rather than floating: Notion's API is versioned by date and a silent
#: upgrade would change the request shape under us.
API_VERSION = "2025-09-03"
TIMEOUT = 10.0

#: The `Vead` data source. Overridable, because a fork of this app is a
#: different person's log.
DATA_SOURCE = os.environ.get(
    "NOTION_VEAD_DATA_SOURCE", "b14f64fa-b90b-4593-ae82-5e6e800e93a2"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS notion_queue (
    id       INTEGER PRIMARY KEY,
    wrong    TEXT NOT NULL,
    correct  TEXT NOT NULL,
    why      TEXT NOT NULL DEFAULT '',
    tag      TEXT NOT NULL,
    on_date  TEXT NOT NULL,
    pushed   TEXT,                      -- ISO timestamp, NULL while pending
    UNIQUE (wrong, correct, tag)        -- the same mistake twice is one row
);
"""


@dataclass(frozen=True)
class Row:
    wrong: str
    correct: str
    why: str = ""
    tag: str = "vocab"
    on_date: str = ""

    def __post_init__(self) -> None:
        if self.tag not in TAGS:
            raise ValueError(
                f"{self.tag!r} is not one of the fixed nine. The log's grouping "
                f"rule counts tags, so an invented one would silently never "
                f"reach three."
            )

    def properties(self) -> dict:
        """The Notion payload. Property names must match the database exactly."""
        return {
            "Vale (wrong)": {"title": [{"text": {"content": self.wrong[:2000]}}]},
            "Õige (correct)": {
                "rich_text": [{"text": {"content": self.correct[:2000]}}]
            },
            "Miks (why)": {"rich_text": [{"text": {"content": self.why[:2000]}}]},
            "Tag": {"multi_select": [{"name": self.tag}]},
            "Kuupäev": {"date": {"start": self.on_date or date.today().isoformat()}},
        }


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def queue(conn: sqlite3.Connection, row: Row) -> bool:
    """Hold a correction for review. True if it is new."""
    with conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO notion_queue"
            " (wrong, correct, why, tag, on_date) VALUES (?,?,?,?,?)",
            (row.wrong, row.correct, row.why, row.tag,
             row.on_date or date.today().isoformat()),
        )
    return cur.rowcount > 0


def pending(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM notion_queue WHERE pushed IS NULL ORDER BY id"
    ).fetchall()


def mark_pushed(conn: sqlite3.Connection, row_id: int) -> None:
    from datetime import datetime, timezone

    with conn:
        conn.execute(
            "UPDATE notion_queue SET pushed = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), row_id),
        )


def push(row: Row, token: str | None = None) -> tuple[bool, str]:
    """Send one row. Returns (ok, detail) rather than raising.

    A failed push must leave the row queued, not lost: the queue is the record
    until Notion confirms it has one.
    """
    token = token or os.environ.get("NOTION_TOKEN")
    if not token:
        return False, "NOTION_TOKEN is not set"

    body = json.dumps({
        "parent": {"type": "data_source_id", "data_source_id": DATA_SOURCE},
        "properties": row.properties(),
    }).encode("utf-8")

    request = urllib.request.Request(
        API, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": API_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return True, json.loads(response.read()).get("url", "created")
    except urllib.error.HTTPError as exc:
        return False, f"{exc.code} {exc.read().decode('utf-8', 'replace')[:200]}"
    except (urllib.error.URLError, OSError) as exc:
        return False, str(exc)[:200]


def from_correction(correction, on_date: str = "") -> Row:
    """Build a row from a `grammar.Correction`, tag and all."""
    return Row(
        wrong=correction.wrong,
        correct=correction.right,
        why=getattr(correction, "why_ru", "") or getattr(correction, "why", ""),
        tag=correction.tag if correction.tag in TAGS else "vocab",
        on_date=on_date,
    )
