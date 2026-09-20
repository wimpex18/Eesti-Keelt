"""The exam board's published task material: PDFs and listening audio.

Complements `eis.py` (interactive EIS tasks): these are the per-task PDFs and
MP3s on the exam page, including the B1 writing task types and listening audio.

**Indexed, and downloaded for private study** with `cli harvest-exam
--download`: the files land in `config.EXAM_DIR` (git-ignored, never
redistributed), a PDF's text becomes the item's `body`, and `/api/exam/file`
serves the file to this learner alone. © Haridus- ja Noorteamet, attributed
wherever a task is shown. Without the download the item still carries only its
URL and links out.

**Level comes from the page's tab panel** (`id="a2-tase"` …); filenames inside
a panel are generic. The filename gives only the exam part.

**Kinds matter:** tasks, information sheets, forms, videos and the annotated
sample performance (*sooritusnäidis*) are different activities.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

PAGE = "https://harno.ee/eesti-keele-tasemeeksamid"
BASE = "https://harno.ee"
TIMEOUT = 45.0

#: The User-Agent this harvester sends.
UA = "Mozilla/5.0 (compatible; eesti-keelt)"

_KIND_MARKERS = (
    # Ordered: the first match wins, and the specific ones come first.
    ("sooritusnaidis", ("sooritusnaidis", "sooritusnäidis", "sooritusnaidised",
                        "sooritusnäidised")),
    ("konsultatsioon", ("konsultatsioon",)),
    ("statistika", ("statistika",)),
    ("vorm", ("avaldus", "taotlemise", "vorm", "juhend", "hüvitamise",
              "hyvitamise")),
    # "info" alone is too weak a marker: it matched `B1 R2 infovahetus`, a
    # speaking task, and filed it as an information sheet.
    ("teave", ("teabeleht", "lisainfo", "teave")),
    ("kirjeldus", ("keelekasutaja", "raamdokument", "kirjeldus")),
)

#: What a file is *for*: task, information sheet, annotated sample, and so on.
#:
#: `KINDS` is every value `_kind_of` can return, derived from this table plus the
#: fall-through kinds; `library.SECTIONS` and the orphan test read it. `video` is
#: assigned by `catalogue()` to embedded intro videos.
KINDS: tuple[str, ...] = tuple(dict.fromkeys(
    [k for k, _ in _KIND_MARKERS] + ["ulesanne", "teave", "video"]
))  # `teave` is both a marker and a fallback; ordered dedup, not a set

#: Kinds catalogued but not indexed as items. `statistika` (national pass rates)
#: is not study material and would sit badly beside a readiness verdict that is
#: not a prediction. `vorm` (application forms) is indexed.
NOT_INDEXED: frozenset[str] = frozenset({"statistika"})

#: Filename fragments to exam parts. Estonian names the part in the file, so
#: this is reading a label rather than inferring one.
_PARTS = {
    "kirjutamine": "kirjutamine",
    "kuulamis": "kuulamine",
    "kuulamine": "kuulamine",
    "lugemis": "lugemine",
    "lugemine": "lugemine",
    "raakimine": "raakimine",
    "rääkimine": "raakimine",
    "suuline": "raakimine",
    # The B1 writing tasks are named by what the candidate produces (notice,
    # questionnaire, set topic, letter), not by the word "kirjutamine".
    "teade": "kirjutamine",
    "kuulutus": "lugemine",
    "jutt etteantud teemal": "kirjutamine",
    "küsimustiku": "kirjutamine",
    "kysimustiku": "kirjutamine",
    "kiri": "kirjutamine",
    "loovtekst": "kirjutamine",
    "lühisõnum": "kirjutamine",
    "sõnavõtt": "kirjutamine",
    "arutlev": "kirjutamine",
    "kokkuvõte": "kirjutamine",
    "teemakaardid": "raakimine",
}

#: HARNO's own abbreviations, used throughout the B1 material: `B1_Ki2B`,
#: `B1_Lu1_kuulutus`, `B1_Ku3_yl`, `B1_R2_infovahetus`. Matching only the full
#: words dropped every B1 file — the level this app exists for.
_PART_CODES = {
    "ki": "kirjutamine",
    "ku": "kuulamine",
    "lu": "lugemine",
    "r": "raakimine",
}
_CODE_RE = re.compile(r"(?:^|[ _-])(?:A2|B1|B2|C1)[ _-]?(ki|ku|lu|r)\d", re.I)

# The query string is optional and not part of the match: audio URLs carry
# `?version=1&...`.
@dataclass(frozen=True)
class Material:
    url: str
    level: str
    #: Exam part, or "" for things that belong to the level as a whole.
    skill: str
    title: str
    #: What it is for -- see KINDS.
    kind: str
    #: pdf | mp3 | wav | docx | video
    fmt: str


#: Query string optional and never part of the match (audio URLs carry
#: `?version=1&...`).
_FILE_RE = re.compile(r'href="([^"]+?\.(?:pdf|mp3|wav|docx))(?:\?[^"]*)?"', re.I)
_VIDEO_RE = re.compile(r'href="(https://youtu\.be/[\w-]+)"')
_PANEL_RE = re.compile(
    r'<div[^>]*role="tabpanel"[^>]*id="(a2|b1|b2|c1)-tase"[^>]*>', re.I
)


def _decode(url: str) -> str:
    """The readable filename, for classifying and for showing to a learner."""
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1]).split("?")[0]
    return " ".join(name.rsplit(".", 1)[0].replace("_", " ").split())


#: File extensions HARNO actually publishes. Anything else is a link.
_FORMATS = frozenset({"pdf", "docx", "doc", "mp3", "wav", "m4a", "zip", "xlsx"})


def _format_of(url: str) -> str:
    """The file type, or `link` when the URL names no extension (e.g. a wiki page)."""
    tail = url.split("?")[0].rsplit("/", 1)[-1]
    ext = tail.rsplit(".", 1)[-1].lower() if "." in tail else ""
    return ext if ext in _FORMATS else "link"


def _skill_of(name: str) -> str | None:
    lowered = name.casefold()
    # Whole words first: unambiguous, and a filename carrying both
    # ("B1 kuulamisülesanne") should be read the plain way.
    for marker, skill in _PARTS.items():
        if marker in lowered:
            return skill
    code = _CODE_RE.search(name)
    return _PART_CODES[code.group(1).casefold()] if code else None


#: Kinds that outrank a recognised exam part. A sample performance for the
#: writing task is a sample, not a task; a consultation workbook covering
#: listening is a workbook. Everything else with a part is an exercise.
_STRONG = ("sooritusnaidis", "konsultatsioon", "statistika", "video")


def _kind_of(name: str, skill: str | None) -> str:
    lowered = name.casefold()
    for kind, markers in _KIND_MARKERS:
        if any(m in lowered for m in markers):
            if skill and kind not in _STRONG:
                # A weak marker lost to a real exam part.
                continue
            return kind
    return "ulesanne" if skill else "teave"


def _panels(html: str) -> list[tuple[str, str]]:
    """`[(level, html)]`, one per level tab: the panels are siblings, so slicing
    between panel openings attributes each file to its level.
    """
    marks = [(m.group(1).upper(), m.end()) for m in _PANEL_RE.finditer(html)]
    out = []
    for i, (level, start) in enumerate(marks):
        stop = marks[i + 1][1] if i + 1 < len(marks) else len(html)
        out.append((level, html[start:stop]))
    return out


def _fetch(url: str = PAGE) -> str:
    """One page, one attempt: the exam catalogue is read once per harvest."""
    from .. import net

    return net.get(url, "HARNO exam page", timeout=TIMEOUT, retries=1, ua=UA)


def catalogue(html: str | None = None) -> list[Material]:
    """Everything the exam page publishes, per level, by what it is for. Files are
    never fetched — links only.
    """
    html = _fetch() if html is None else html

    found: dict[str, Material] = {}
    for level, panel in _panels(html):
        for href in _FILE_RE.findall(panel):
            url = urllib.parse.urljoin(BASE, href).replace("&amp;", "&")
            title = _decode(url)
            skill = _skill_of(title)
            fmt = _format_of(url)
            kind = _kind_of(title, skill)
            # Statistics and forms are page-wide (named by year or purpose) and belong to no
            # level.
            found[f"{level}|{url}"] = Material(
                url=url,
                level="" if kind in ("statistika", "vorm") else level,
                skill=skill or "", title=title, kind=kind, fmt=fmt,
            )
        for href in _VIDEO_RE.findall(panel):
            found[f"{level}|{href}"] = Material(
                url=href, level=level, skill="",
                title=f"{level}-taseme eksami tutvustav video",
                kind="video", fmt="video",
            )
    return sorted(found.values(),
                  key=lambda m: (m.level, m.kind, m.skill, m.title))


#: Where the downloaded files live. Owner-only study material, so it sits in
#: `data/` (git-ignored) and is served only to the learner behind Access.
FOLDER = "data/exam"


def local_path(material: "Material", root: Path | str | None = None) -> Path:
    """Where one file is kept: level, then the file's own name."""
    from .. import config

    name = urllib.parse.unquote(material.url.rsplit("/", 1)[-1]).split("?")[0]
    base = Path(root) if root else Path(getattr(config, "EXAM_DIR", FOLDER))
    return base / (material.level or "yldine") / name


def text_of(path: Path | str) -> str:
    """The text of one exam PDF, page by page. Empty when it cannot be read."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
        return "\n\n".join((page.extract_text() or "").strip()
                             for page in reader.pages).strip()
    except Exception:  # noqa: BLE001 - a scanned or broken PDF is not a crash
        return ""


def download(materials: list["Material"], root: Path | str | None = None,
             timeout: float = 60.0) -> dict:
    """Fetch the task files themselves, so the app can open them offline.

    The exam board publishes PDFs and listening audio; a link is only useful
    with a connection and a browser, while a file can be read in the app, played
    in a mock, and kept.
    """
    from .. import net

    got, failed, skipped = 0, 0, 0
    for material in materials:
        if material.fmt not in ("pdf", "mp3", "wav", "docx"):
            skipped += 1
            continue
        target = local_path(material, root)
        if target.exists() and target.stat().st_size:
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            body = net.get(material.url, "HARNO file", timeout=timeout,
                           retries=1, ua=UA, binary=True)
        except Exception:  # noqa: BLE001 - one missing file is not fatal
            failed += 1
            continue
        target.write_bytes(body if isinstance(body, bytes) else body.encode())
        got += 1
    return {"downloaded": got, "already_there": skipped, "failed": failed}


def to_items(materials: list[Material], root: Path | str | None = None) -> list:
    """Pointers, plus the file itself where it was downloaded."""
    from ..sources import Item

    return [
        Item(
            source_id="harno",
            # Material that belongs to the level as a whole -- the information
            # sheet, the annotated sample, the intro video -- is filed under
            # `eksam` rather than forced into one of the four parts.
            skill=m.skill or "eksam",
            level=m.level,
            title=m.title,
            # The PDF's own text when it is here, so the task can be read in the
            # app rather than only linked to.
            body=(text_of(local_path(m, root))
                  if m.fmt == "pdf" and local_path(m, root).exists() else ""),
            audio_url=m.url if m.fmt in ("mp3", "wav") else None,
            meta={
                "url": m.url,
                "kind": m.kind,
                "format": m.fmt,
                # A local copy means the app can open it; a link means it
                # cannot. The path is relative to `config.EXAM_DIR`, so the
                # folder can move without rewriting the catalogue.
                "file": (f"{m.level or 'yldine'}/"
                         f"{local_path(m, root).name}"
                         if local_path(m, root).exists() else None),
                "external": not local_path(m, root).exists(),
                "official": True,
                "note": "Официальный экзаменационный материал — © Haridus- ja Noorteamet.",
            },
        )
        for m in materials
        if m.kind not in NOT_INDEXED
    ]
