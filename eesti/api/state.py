"""The state snapshot, and the reset.

Cloud Run disk is ephemeral and scales to zero, so the Worker exports and
re-imports the learner's databases around cold starts. Paths come from `config`
at call time.
"""

from __future__ import annotations

import base64
import hmac
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from .deps import progress_db

router = APIRouter()

# --------------------------------------------------------------------------
# State snapshots
# --------------------------------------------------------------------------
#
# The durable copy lives in the Worker's Durable Object; these endpoints move it
# in and out. Only the learner's databases travel — the word list, form index and
# corpus are baked into the image or pushed separately.

def _state_paths() -> dict[str, Path]:
    """Every database the snapshot carries, resolved from `config` when asked."""
    from .. import config

    return {
        "progress": Path(config.learner_db("PROGRESS_DB")),
        "review": Path(config.learner_db("REVIEW_DB")),
        "vocab": Path(config.learner_db("VOCAB_DB")),
        # Queued corrections are learner data and travel too.
        "notion": Path(config.learner_db("NOTION_DB")),
    }


def _require_state_token(request: Request) -> None:
    """Snapshots are for the platform, not the browser: they require `STATE_TOKEN`, and
    refuse outright when it is unset.
    """
    expected = os.environ.get("STATE_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="STATE_TOKEN is not configured")
    if not hmac.compare_digest(request.headers.get("x-state-token", ""), expected):
        raise HTTPException(status_code=403, detail="bad state token")
    from ..identity import current

    if current().is_guest:
        raise HTTPException(status_code=403,
                            detail="Гостевая песочница не имеет доступа к журналу.")


def _require_owner() -> None:
    from ..identity import OWNER, current

    if current().kind != OWNER:
        raise HTTPException(status_code=403,
                            detail="Эта операция доступна только владельцу приложения.")


class ResetRequest(BaseModel):
    topic: str | None = None
    everything: bool = False


class AccountRemovalRequest(BaseModel):
    id: str = Field(min_length=1)


@router.post("/api/progress/reset")
def progress_reset(req: ResetRequest, request: Request) -> dict:
    """Forget a topic's attempts (operator action, guarded by `STATE_TOKEN`).

    A missing `topic` is refused unless `everything` is set explicitly.
    """
    _require_state_token(request)
    _require_owner()
    from ..progress import reset

    if not req.topic and not req.everything:
        raise HTTPException(
            status_code=400,
            detail="Pass a topic, or everything=true to clear all of it.",
        )
    return reset(progress_db(), req.topic)


@router.post("/api/state/remove-account")
def remove_account_files(req: AccountRemovalRequest, request: Request) -> dict:
    """Remove one learner's ephemeral origin files during account deletion."""
    _require_state_token(request)
    _require_owner()
    from .. import config
    from ..identity import learner_id

    account_id = learner_id(req.id)
    if account_id is None:
        raise HTTPException(status_code=400, detail="Некорректный ID ученика.")
    directory = Path(config.LEARNERS_DIR) / account_id
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise HTTPException(status_code=409,
                            detail="Путь данных ученика имеет неожиданный вид.")
    if directory.is_dir():
        shutil.rmtree(directory)
    return {"id": account_id, "removed": not directory.exists()}


@router.get("/api/state/export")
def state_export(request: Request) -> dict:
    """The learner's databases, base64'd, for the Worker to persist.

    `rows` counts the learner rows in each (see `LEARNER_ROWS`), so the Worker can
    refuse to let an instance that holds nothing replace a snapshot that holds
    something. Byte size cannot tell them apart: an empty schema is not empty.
    """
    _require_state_token(request)
    out, rows = {}, {}
    for name, path in _state_paths().items():
        out[name] = (
            base64.b64encode(path.read_bytes()).decode("ascii")
            if path.exists() else ""
        )
        rows[name] = _learner_rows(path, LEARNER_ROWS[name])
    return {
        "databases": out,
        "bytes": sum(len(v) for v in out.values()),
        "rows": rows,
        "learner_rows": sum(rows.values()),
    }


class StateBlob(BaseModel):
    databases: dict[str, str]


# The table that means "this learner has done something" in each database; a
# file with only its schema does not count.
LEARNER_ROWS = {
    "progress": "attempts",
    "review": "review_items",
    "vocab": "vocab_status",
    "notion": "notion_queue",
}


def _learner_rows(path: Path, table: str) -> int:
    """How many learner rows a database holds; 0 for a missing file or a bare
    schema. Raises `sqlite3.Error` for a file that is not a readable database.
    """
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        try:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.OperationalError as error:
            if "no such table" in str(error):
                return 0
            raise


def _has_learner_data(path: Path, table: str) -> bool:
    """True only if there are learner rows worth protecting, not just a schema."""
    try:
        return _learner_rows(path, table) > 0
    except sqlite3.Error:
        # Unreadable or not a database: not something worth preserving, but not
        # something to overwrite blindly either.
        return True


class ContentBlob(BaseModel):
    database: str = Field(min_length=1)


@router.post("/api/content/import")
def content_import(blob: ContentBlob, request: Request) -> dict:
    """Receive the harvested library, which cannot ship in the image.

    The corpus is owner-only and Cloud Run's disk is ephemeral, so the Worker holds
    it and pushes it into each fresh instance. Unlike the learner snapshot this
    overwrites: the corpus is derived, so there is no learner work to lose.
    """
    _require_state_token(request)
    _require_owner()
    from .. import config

    path = Path(config.CONTENT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        raw = base64.b64decode(blob.database, validate=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".db", delete=False) as file:
            staged = Path(file.name)
            file.write(raw)
        # Validate without the forgiving opener: it would turn a broken upload
        # into an empty library and conceal the failure after overwriting it.
        with closing(sqlite3.connect(f"file:{staged}?mode=ro", uri=True)) as conn:
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("invalid SQLite database")
            items = conn.execute(
                "SELECT COUNT(*) FROM items i JOIN sources s ON s.id=i.source_id"
            ).fetchone()[0]
            if not items:
                raise ValueError("empty library")
            conn.execute("SELECT id,source_id,skill,level,title,body,audio_url,meta,added_on FROM items LIMIT 1")
        staged.replace(path)
    except (ValueError, sqlite3.Error) as exc:
        raise HTTPException(status_code=422,
                            detail="Библиотека пуста или повреждена. Существующие материалы сохранены.") from exc
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    return {"bytes": path.stat().st_size, "items": items}


@router.get("/api/content/export")
def content_export(request: Request) -> dict:
    """Hand the library back so the Worker can archive it (a script cannot pass
    Access, so pushes go to the origin). `full` returns the file; otherwise just
    presence and size.
    """
    _require_state_token(request)
    _require_owner()
    from .. import config
    from ..sources import available

    path = Path(config.CONTENT_DB)
    present = available(path)
    out = {
        "present": present,
        "bytes": path.stat().st_size if path.exists() else 0,
    }
    if present and request.query_params.get("full"):
        out["database"] = base64.b64encode(path.read_bytes()).decode("ascii")
    return out


@router.post("/api/state/import")
def state_import(blob: StateBlob, request: Request) -> dict:
    """Restore a snapshot into a fresh container.

    Refuses to overwrite a database that already holds learner rows (newer work
    wins); an empty schema is overwritten.
    """
    _require_state_token(request)
    restored, skipped = [], []
    for name, path in _state_paths().items():
        payload = blob.databases.get(name) or ""
        if not payload:
            continue
        if _has_learner_data(path, LEARNER_ROWS[name]):
            skipped.append(name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(payload))
        restored.append(name)

    # After a restore, run the idempotent repair of fabricated placement attempts;
    # at import it would clean a database the restore is about to replace.
    repair = None
    if "progress" in restored:
        from ..progress import connect as progress_connect
        from ..progress import repair_fabricated_attempts

        # `_state_paths()` rather than a second way of naming the same file:
        # its own docstring is about exactly that, and it resolves at call time.
        repair = repair_fabricated_attempts(
            progress_connect(_state_paths()["progress"]))
    return {"restored": restored, "skipped": skipped, "repair": repair}


# --------------------------------------------------------------------------
# The evidence log
# --------------------------------------------------------------------------
#
# The Worker's Durable Object holds the durable copy of the log. It pulls new
# events after requests (the `x-events-seq` header says when there are any) and
# pushes the whole log into a fresh instance, which then rebuilds its
# projections from it (`evidence.settle`).

@router.get("/api/events")
def events_export(request: Request, after: int = 0, limit: int = 500) -> dict:
    """Events after an origin sequence number, oldest first."""
    _require_state_token(request)
    from .. import evidence

    limit = max(1, min(limit, 2000))
    with evidence.connect() as conn:
        batch = evidence.events(conn, after=after, limit=limit)
        return {
            "events": [ev.to_dict() | {"seq": ev.seq} for ev in batch],
            "last_seq": evidence.last_seq(conn),
        }


class EventsImport(BaseModel):
    events: list[dict] = Field(default_factory=list)
    # Sent with the last batch of a restore: rebuild (or first backfill) now.
    settle: bool = False


@router.post("/api/events/import")
def events_import(body: EventsImport, request: Request) -> dict:
    """Append events this instance lacks (by id); with `settle`, make the
    projections agree with the log."""
    _require_state_token(request)
    from .. import evidence

    with evidence.connect() as conn:
        try:
            added = evidence.ingest(conn, body.events)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"bad event: {exc}") from exc
        # Where the imported log ends. Settling may append to it (the first
        # backfill); the Worker resumes pulling from here, so those reach it too.
        ingested = evidence.last_seq(conn)
        settled = evidence.settle(conn) if body.settle else None
        return {"added": added, "ingested_seq": ingested,
                "last_seq": evidence.last_seq(conn), "settled": settled}


@router.get("/api/me/export")
def my_export() -> PlainTextResponse:
    """Everything the app has recorded about the learner, one event per line."""
    import json

    from .. import evidence

    with evidence.connect() as conn:
        lines = [json.dumps(ev.to_dict(), ensure_ascii=False)
                 for ev in evidence.events(conn)]
    return PlainTextResponse(
        "\n".join(lines) + ("\n" if lines else ""),
        media_type="application/x-ndjson",
        headers={"content-disposition": 'attachment; filename="eesti-keelt-events.jsonl"'},
    )


# --------------------------------------------------------------------------
# Reminders: what the Worker's cron may tell the learner
# --------------------------------------------------------------------------
#
# The decision is here, where the evidence is; the sending is in the Worker,
# which holds the subscription and the VAPID keys. A reminder carries counts
# only (`eesti/reminders.py`).

class ReminderChoice(BaseModel):
    on: bool | None = None
    hour: int | None = Field(default=None, ge=0, le=23)
    quiet_from: int | None = Field(default=None, ge=0, le=23)
    quiet_to: int | None = Field(default=None, ge=0, le=23)


@router.get("/api/reminders")
def reminders_due(request: Request) -> dict:
    """What is worth a notification right now. Back-channel: the cron asks it."""
    from .. import config, evidence, reminders, review

    _require_state_token(request)
    with evidence.connect() as log:
        prefs = reminders.settings(log)
        with review.connect(config.learner_db("REVIEW_DB")) as cards:
            found = reminders.due(log, cards, progress_db())
    return {"on": prefs["on"], "quiet": reminders.quiet(prefs),
            "reminders": [r.to_dict() for r in found]}


@router.get("/api/reminders/settings")
def reminder_settings() -> dict:
    """The learner's own choices — the page reads these to draw the switch."""
    from .. import evidence, reminders
    from ..identity import current

    if current().is_guest:
        raise HTTPException(status_code=403,
                            detail="Настройки напоминаний доступны только аккаунту.")

    with evidence.connect() as log:
        return reminders.settings(log)


@router.post("/api/reminders/settings")
def choose_reminders(choice: ReminderChoice) -> dict:
    """Turn reminders on or off, and say when. Recorded as learner state."""
    from .. import reminders
    from ..identity import current

    if current().is_guest:
        raise HTTPException(status_code=403,
                            detail="Настройки напоминаний доступны только аккаунту.")

    return reminders.choose(**{k: v for k, v in choice.model_dump().items()
                               if v is not None})


# --------------------------------------------------------------------------
# Web Push: what the origin can honestly say about it
# --------------------------------------------------------------------------
#
# The subscription and the VAPID keys live in the Worker, which is what sends a
# notification (`deploy/worker.ts`), and the Worker answers `/api/push/*` before
# it proxies. These exist so the same page is honest when it is served by
# `cli serve` with no Worker in front: reminders are simply not configured, the
# switch says so, and no browser is asked for permission it cannot use.


@router.get("/api/push/key")
def push_key() -> dict:
    """No Worker, no push. A key here would be a key nothing can sign with."""
    return {"key": None, "configured": False, "subscribers": 0,
            "note": "Напоминания отправляет Worker; локально их нет."}


@router.post("/api/push/subscribe")
def push_subscribe() -> dict:
    raise HTTPException(status_code=503, detail=(
        "Напоминания отправляет Worker; локально подписка не нужна."))


@router.post("/api/push/unsubscribe")
def push_unsubscribe() -> dict:
    return {"subscribers": 0}
