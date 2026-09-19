"""The library: everything that is material rather than curriculum.

|            | Path (`curriculum.py`, `progress.py`) | Library |
|------------|------------------|---------------|
| ordered    | by prerequisite  | browse freely |
| gated      | on mastery       | never         |
| measurable | pass/fail per topic | exposure only |

Material that cannot be sequenced or checked (e.g. unscripted radio) belongs
here, not on the path. Opening an item records exposure, never mastery;
vocabulary coverage comes from `vocab.py`.

Licence gating is a filter: `browse(..., public_only=True)` filters on the
source's licence, so a new source cannot leak by forgetting to tag rows.
Owner-only material is why Cloudflare Access is required.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


#: The three things a learner is ever doing. Every section belongs to exactly
#: one, and material that answers none of the three questions has no home here.
#:
#:   õppimine  — "what am I learning today?"
#:   kordamine — "what am I forgetting?"
#:   eksam     — "am I ready?"
MODES = ("oppimine", "kordamine", "eksam")

MODE_LABELS = {
    "oppimine": ("Õppimine", "обучение"),
    "kordamine": ("Kordamine", "повторение"),
    "eksam": ("Eksam", "экзамен"),
}


@dataclass(frozen=True)
class Section:
    id: str
    et: str
    ru: str
    skills: tuple[str, ...]
    #: Russian. The label is Estonian because the interface is exposure; the
    #: sentence explaining what a section *is* has to be readable by someone
    #: still learning that language.
    note: str
    mode: str = "oppimine"
    #: Which `meta.kind` values belong here; empty means "any". Skill alone cannot
    #: separate official samples, videos and workbooks from tasks of the same skill.
    kinds: tuple[str, ...] = ()
    #: Exclude these kinds even when the skill matches.
    not_kinds: tuple[str, ...] = ()


# Sections group by what the learner does with material, not by origin: the ERR
# radio courses are grammar lessons and sit with grammar.
SECTIONS: tuple[Section, ...] = (
    # -- Õppimine ----------------------------------------------------------
    Section("lugemine", "Lugemine", "чтение", ("lugemine",),
            "Простые эстонские тексты, отсортированные по относительной "
            "сложности. Плюс живая еженедельная лента ERR.",
            mode="oppimine", not_kinds=("ulesanne", "sooritusnaidis",
                                        "konsultatsioon", "teave", "video",
                                        "kirjeldus")),
    Section("kuulamine", "Kuulamine", "аудирование", ("kuulamine",),
            "Аудио без расшифровки — это контакт с языком, а не шаг программы. "
            "Плюс TTS на любой текст со скоростью 0.7.",
            mode="oppimine", not_kinds=("ulesanne", "sooritusnaidis",
                                        "konsultatsioon", "teave", "video",
                                        "kirjeldus")),
    Section("saated", "Saated", "передачи", ("grammatika",),
            "Радиокурсы, у которых есть расшифровка: 28 уроков, объяснение "
            "по-русски с эстонскими примерами.",
            mode="oppimine"),

    # -- Kordamine ---------------------------------------------------------
    # The only official material that is *not* exam preparation. A consultation
    # workbook, especially the computer-fillable variant, is homework.
    Section("vihikud", "Töövihikud", "тетради",
            ("lugemine", "kuulamine", "kirjutamine", "raakimine", "eksam"),
            "Официальные консультационные тетради, в том числе заполняемые на "
            "компьютере. Это домашняя работа, а не экзамен.",
            mode="kordamine", kinds=("konsultatsioon",)),

    # -- Eksam -------------------------------------------------------------
    Section("naidised", "Sooritusnäidised", "образцы работ",
            ("lugemine", "kuulamine", "kirjutamine", "raakimine", "eksam"),
            "Настоящие экзаменационные работы с оценкой и комментариями. "
            "Единственное, что показывает, как выглядит сдача.",
            mode="eksam", kinds=("sooritusnaidis",)),
    Section("eksam", "Eksamiülesanded", "задания экзамена",
            ("lugemine", "kuulamine", "kirjutamine", "raakimine"),
            "Официальные задания по частям экзамена. Только для владельца.",
            mode="eksam", kinds=("ulesanne",)),
    # Includes `vorm`: HARNO's application and reimbursement forms.
    Section("eksamiinfo", "Eksamist", "об экзамене",
            ("lugemine", "kuulamine", "kirjutamine", "raakimine", "eksam"),
            "Видео об экзамене, описания уровней CEFR, информационный лист, "
            "бланки заявлений и регистрация.",
            mode="eksam", kinds=("video", "kirjeldus", "teave", "vorm")),
)

_BY_ID = {s.id: s for s in SECTIONS}

SCHEMA = """
-- One row per opening, with a surrogate key. Keying on (item_id, seen_at) with
-- second-granularity timestamps meant two opens in the same second collided:
-- the second REPLACEd the first, so a re-read looked like one visit and its
-- minutes were *lost* rather than added. A test that has to sleep to observe
-- correct behaviour is a test accommodating a bug.
CREATE TABLE IF NOT EXISTS exposure (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id  TEXT NOT NULL,
    seen_at  TEXT NOT NULL,
    minutes  REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_exposure_item ON exposure(item_id);
"""


def by_id(section_id: str) -> Section:
    return _BY_ID[section_id]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _kind_clause(section: Section) -> tuple[str, list]:
    """SQL restricting to a section's purpose, read from `meta.kind` with
    `json_extract`, falling back to a substring match if JSON functions fail.
    """
    kinds, not_kinds = section.kinds, section.not_kinds
    if not (kinds or not_kinds):
        return "", []

    sql, params = "", []
    if kinds:
        marks = ",".join("?" * len(kinds))
        sql += f" AND json_extract(i.meta, '$.kind') IN ({marks})"
        params += list(kinds)
    for kind in not_kinds:
        # `IS NOT` rather than `!=`: an item with no `kind` at all must survive
        # an exclusion, and SQL comparison with NULL is never true.
        sql += " AND json_extract(i.meta, '$.kind') IS NOT ?"
        params.append(kind)
    return sql, params


def sections(content: sqlite3.Connection, public_only: bool = False,
             mode: str | None = None) -> list[dict]:
    """Every section with how much material is in it; `mode` narrows to one mode."""
    out = []
    for section in SECTIONS:
        if mode is not None and section.mode != mode:
            continue
        marks = ",".join("?" * len(section.skills))
        sql = (
            f"SELECT COUNT(*), COALESCE(SUM(i.audio_url IS NOT NULL), 0)"
            f" FROM items i JOIN sources s ON s.id = i.source_id"
            f" WHERE i.skill IN ({marks})"
        )
        params = list(section.skills)
        if public_only:
            sql += " AND s.redistributable = 1"
        kind_sql, kind_params = _kind_clause(section)
        sql += kind_sql
        params += kind_params
        total, with_audio = content.execute(sql, params).fetchone()
        et, ru = MODE_LABELS[section.mode]
        out.append({
            "id": section.id, "et": section.et, "ru": section.ru,
            "items": total, "with_audio": with_audio, "note": section.note,
            "mode": section.mode, "mode_et": et, "mode_ru": ru,
        })
    return out


def _filters(level: str | None, band: str | None,
             public_only: bool) -> tuple[str, list]:
    """The conditions `browse` and `count` both apply, so a count always matches its
    rows.

    `level` (CEFR, official material only) and `band` (difficulty relative to a
    source) stay separate claims.
    """
    sql, params = "", []
    if level:
        sql += " AND i.level = ?"
        params.append(level)
    if band:
        sql += " AND i.band = ?"
        params.append(band)
    if public_only:
        sql += " AND s.redistributable = 1"
    return sql, params


def browse(
    content: sqlite3.Connection,
    section: str,
    level: str | None = None,
    band: str | None = None,
    limit: int = 20,
    public_only: bool = False,
) -> list[sqlite3.Row]:
    """Material in one section. Unordered by design — this is a shelf, not a path.

    Skills within a section are dealt round-robin so none is crowded out by the
    limit.
    """
    meta = by_id(section)
    kind_sql, kind_params = _kind_clause(meta)

    def rows_for(skill: str) -> list[sqlite3.Row]:
        # `redistributable` travels with every row: the licence gate reads it,
        # and a query that silently stopped returning it would make the gate
        # raise rather than refuse — which is the wrong direction to fail.
        sql = ("SELECT i.*, s.name AS source_name, s.licence,"
               " s.redistributable"
               " FROM items i JOIN sources s ON s.id = i.source_id"
               " WHERE i.skill = ?")
        params: list = [skill]
        where, filter_params = _filters(level, band, public_only)
        sql += where
        params += filter_params
        sql += kind_sql
        params += kind_params
        sql += " LIMIT ?"
        params.append(limit)
        return content.execute(sql, params).fetchall()

    per_skill = [rows_for(skill) for skill in meta.skills]
    out: list[sqlite3.Row] = []
    while any(per_skill) and len(out) < limit:
        for rows in per_skill:
            if rows and len(out) < limit:
                out.append(rows.pop(0))
    return out


def count(
    content: sqlite3.Connection,
    section: str,
    level: str | None = None,
    band: str | None = None,
    public_only: bool = False,
) -> int:
    """How many items a section holds, ignoring `browse`'s page size; built from the
    same filters as `browse`.
    """
    meta = by_id(section)
    kind_sql, kind_params = _kind_clause(meta)
    total = 0
    for skill in meta.skills:
        sql = ("SELECT COUNT(*) FROM items i JOIN sources s ON s.id = i.source_id"
               " WHERE i.skill = ?")
        params: list = [skill]
        where, filter_params = _filters(level, band, public_only)
        sql += where
        params += filter_params
        sql += kind_sql
        params += kind_params
        total += content.execute(sql, params).fetchone()[0]
    return total


def mark_seen(progress: sqlite3.Connection, item_id: str, minutes: float = 0.0) -> None:
    """Record that material was opened. Not a pass, and never treated as one."""
    from . import evidence

    payload = {"item_id": item_id, "minutes": float(minutes)}
    ev = evidence.record("exposure", payload)
    _seen(progress, payload, ev.ts)


def _seen(progress: sqlite3.Connection, p: dict, at: str) -> None:
    progress.executescript(SCHEMA)
    with progress:
        progress.execute(
            "INSERT INTO exposure (item_id, seen_at, minutes) VALUES (?,?,?)",
            (p["item_id"], at, p["minutes"]),
        )


def _apply_exposure(stores, ev) -> None:
    _seen(stores["progress"], ev.payload, ev.ts)


def open_item(
    content: sqlite3.Connection,
    item_id: str,
    progress: sqlite3.Connection | None = None,
    vocabulary: sqlite3.Connection | None = None,
    minutes: float = 0.0,
) -> dict:
    """Open one piece of material: record the exposure *and* the words met.

    Encounters bump a met-count and never mark a word known — that stays an
    explicit act, so coverage numbers do not inflate by opening texts.
    """
    row = content.execute(
        "SELECT id, body FROM items WHERE id = ?", (item_id,)
    ).fetchone()
    if row is None:
        raise KeyError(item_id)

    out = {"item": item_id, "lemmas": 0}
    if progress is not None:
        mark_seen(progress, item_id, minutes=minutes)
    if vocabulary is not None and row["body"]:
        from .morph import analyze
        from .vocab import record_encounter

        lemmas = sorted({
            t.lemma.lower() for t in analyze(row["body"])
            if t.pos in ("S", "V", "A", "adj") and len(t.lemma) > 1
        })
        out["lemmas"] = record_encounter(vocabulary, lemmas)
    return out


def exposure(progress: sqlite3.Connection) -> dict:
    """Texts opened and minutes spent. Two counts, deliberately no percentage: the
    library has no meaningful denominator.
    """
    progress.executescript(SCHEMA)
    rows = progress.execute(
        "SELECT COUNT(*), COUNT(DISTINCT item_id), COALESCE(SUM(minutes), 0)"
        " FROM exposure"
    ).fetchone()
    return {"openings": rows[0], "items": rows[1], "minutes": round(rows[2], 1)}


def seen_items(progress: sqlite3.Connection) -> set[str]:
    progress.executescript(SCHEMA)
    return {r[0] for r in progress.execute("SELECT DISTINCT item_id FROM exposure")}


def exam_material(content: sqlite3.Connection, level: str,
                  public_only: bool = False) -> dict:
    """Everything official for one level, grouped by `kind`, in one request: a sample
    performance, a workbook and a task are different activities.
    """
    import json as _json

    from .harvest import harno

    # Level-less material matches every level (so HARNO forms show), and
    # `harno.NOT_INDEXED` is also enforced at read time so previously harvested
    # statistics PDFs stay hidden.
    blocked = ",".join("?" * len(harno.NOT_INDEXED))

    sql = """SELECT i.id, i.title, i.skill, i.level, i.audio_url, i.meta,
                    s.name AS source_name, s.licence
             FROM items i JOIN sources s ON s.id = i.source_id
             WHERE (i.level = ? OR COALESCE(i.level, '') = '')
               AND s.id IN ('harno', 'eis')
               AND COALESCE(json_extract(i.meta, '$.kind'), '')
                   NOT IN (""" + blocked + """)"""
    params: list = [level, *sorted(harno.NOT_INDEXED)]
    if public_only:
        sql += " AND s.redistributable = 1"
    sql += " ORDER BY i.skill, i.title"

    by_kind: dict[str, list[dict]] = {}
    for row in content.execute(sql, params).fetchall():
        try:
            meta = _json.loads(row["meta"] or "{}")
        except ValueError:
            meta = {}
        by_kind.setdefault(meta.get("kind") or "ulesanne", []).append({
            "id": row["id"], "title": row["title"], "skill": row["skill"],
            "url": meta.get("url"), "format": meta.get("format"),
            "audio_url": row["audio_url"], "source": row["source_name"],
        })

    tasks = by_kind.pop("ulesanne", [])
    by_part: dict[str, list[dict]] = {}
    for task in tasks:
        by_part.setdefault(task["skill"], []).append(task)

    return {
        "level": level,
        # First, because it is what a learner who has never sat the exam needs
        # before anything else: what a pass actually looks like.
        "sooritusnaidis": by_kind.pop("sooritusnaidis", []),
        "video": by_kind.pop("video", []),
        "kirjeldus": by_kind.pop("kirjeldus", []),
        "teave": by_kind.pop("teave", []),
        # Application and reimbursement forms: level-less, so shown at every level.
        "vorm": by_kind.pop("vorm", []),
        "ulesanded": by_part,
        "muu": [item for items in by_kind.values() for item in items],
    }


def parts_touched(progress: sqlite3.Connection,
                  content: sqlite3.Connection) -> dict[str, int]:
    """How many items the learner has opened, per exam part.

    Joins `exposure` (learner, snapshotted) with `items` (corpus) in Python, since
    they are different databases.
    """
    seen = seen_items(progress)
    if not seen:
        return {}
    counts: dict[str, int] = {}
    for row in content.execute("SELECT id, skill FROM items").fetchall():
        if row["id"] in seen:
            counts[row["skill"]] = counts.get(row["skill"], 0) + 1
    return counts


def _register() -> None:
    from . import evidence

    evidence.applies("exposure")(_apply_exposure)


_register()
