"""The exam board's published task material: PDFs and listening audio.

Distinct from `eis.py`, which indexes the *interactive* practice tasks at
`eis.harno.ee/publicitems`. This is the other half — the per-task PDFs and MP3s
published on the exam page itself, including the four writing task types a B1
candidate is actually graded on and the listening audio for each level.

## Indexed, never downloaded

**© Haridus- ja Noorteamet.** Studying from these is ordinary personal use;
copying them into a database that lives on a public deployment is not. So this
stores what each file *is* — level, exam part, title, URL — and links to
HARNO's own copy. `body` stays empty and a test holds it there.

That is not only caution. Roughly a hundred PDFs and twenty audio files is far
more than this app should carry, and none of it changes.

## Where the level actually comes from

The first version read it off the filename, and that was structurally wrong.
The page is four **tab panels** — `id="a2-tase"`, `b1-tase`, `b2-tase`,
`c1-tase` — and inside a panel the files are named generically: `teade`,
`Kuulamine 3`, `rääkimine1`. Requiring a level in the name threw away 72 of 111
files, including the four B1 writing task types by name and both speaking topic
cards.

So the level is taken from the panel a link sits in, and the filename is used
only for the exam part. Structure knows what the name does not.

## Not everything here is a task

The page carries at least six kinds of thing, and treating them alike would
bury the good ones. The **sooritusnäidis** — a real candidate performance,
graded and annotated, published with the author's permission — is arguably the
most useful single artefact on the page for someone who has never seen what a
pass looks like, and it was being dropped as unclassifiable.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

PAGE = "https://harno.ee/eesti-keele-tasemeeksamid"
BASE = "https://harno.ee"
TIMEOUT = 45.0

#: The value this module has always sent. Kept as it was rather than
#: standardised: what a server has been seeing is not a detail to change
#: while consolidating how the request is made.
UA = "Mozilla/5.0 (compatible; eesti-keelt)"

LEVELS = ("A2", "B1", "B2", "C1")

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

#: What a file is *for*. A learner preparing on Tuesday evening wants a task; a
#: learner deciding whether to register wants the information sheet; a learner
#: who has never seen a pass wants the annotated sample. Flattening these into
#: one list buries all three.
#:
#: Every value `_kind_of` can return, **derived** from the table above plus the
#: ones it falls through to. Exported because three other places need this list
#: and each had been keeping its own copy: `library.SECTIONS`, which decides
#: whether a kind is reachable at all, the orphan test, whose hand-written
#: fixture could only catch kinds somebody had remembered to add to it, and —
#: found on review — a hand-written `KINDS` that sat twelve lines above this
#: one and was shadowed by it. Two definitions of the same name in one module,
#: the second winning silently, is the hand-maintained copy this comment says
#: must not exist, written directly underneath the comment saying so.
#:
#: That is how `statistika` and `vorm` came to be indexed and invisible — 20
#: items in the database and in no section, which is the same failure the
#: orphan check was written for after 25 items vanished the same way.
#: `video` is not in `_KIND_MARKERS` because it is not read off a filename:
#: `catalogue()` assigns it to the embedded intro videos directly. It has to be
#: here anyway — the point of this tuple is every kind that reaches an item,
#: not every kind a filename can spell.
KINDS: tuple[str, ...] = tuple(dict.fromkeys(
    [k for k, _ in _KIND_MARKERS] + ["ulesanne", "teave", "video"]
))  # `teave` is both a marker and a fallback; ordered dedup, not a set

#: Kinds that are catalogued but deliberately **not** indexed as items.
#:
#: `statistika` is eleven PDFs of national pass rates by year. It is not study
#: material, and putting it in the app would sit a national pass rate next to a
#: readiness verdict whose whole job is to say "this is not a prediction". So
#: it is read from the page — `catalogue()` stays a faithful account of what
#: HARNO publishes — and dropped before it becomes an item.
#:
#: `vorm` is not here, and that is the other half of the fix: the application
#: and reimbursement forms are exactly what an exam candidate needs, and the
#: `eksamiinfo` section's own description already promised registration while
#: showing none of them.
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
    # The writing tasks are named by what the candidate must produce, never by
    # the part. These four are the B1 writing exam: a notice, a questionnaire, a
    # piece on a set topic, a personal letter. Filed as "information" by a
    # classifier looking for the word "kirjutamine", which is the one word
    # HARNO had no reason to put in the filename.
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

# The query string is optional and must not be part of the match: the listening
# audio is served from projektid.edu.ee with `?version=1&...`, so a pattern that
# required the URL to *end* in .mp3 found none of it — seventeen files, which is
# every audio track for every level, silently absent.
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


#: Query string optional and never part of the match: the listening audio is
#: served from projektid.edu.ee with `?version=1&...`, and a pattern requiring
#: the URL to *end* in .mp3 found none of it -- every audio track, silently.
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
    """The file type, or `link` when the URL does not name one.

    Splitting on the last dot is right for
    `.../B1_kuulamine.pdf` and wrong for everything without an extension: one
    consultation entry points at a Confluence wiki page, and the old split
    handed back `ee/spaces/tho/pages/343705183/konsultatsioonide+materjalid`
    as the file format — a whole URL path stored in a field the app renders as
    a badge, and the same field `to_items` asks whether the material is audio.
    """
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
    """`[(level, html)]`, one per level tab.

    The page repeats generic filenames inside each panel -- `teade`,
    `Kuulamine 3`, `rääkimine1` -- so the panel is the only thing that says
    which level a file belongs to. Slicing between panel openings is crude and
    correct here: the panels are siblings and the last one runs to the end of
    the document, where the remaining links are page furniture.
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
    """Everything the exam page publishes, per level, by what it is for.

    One request. The files themselves are never fetched -- that is the whole
    point: they are HARNO's copyright and this stores links, not content.
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
            # Statistics and application forms are page-wide: they are named by
            # year or by purpose and belong to no level. Attributing them to a
            # panel put eleven years of pass rates and nine administrative
            # forms under C1, purely because the last panel runs to the end of
            # the document.
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


def to_items(materials: list[Material]) -> list:
    """Pointers. `body` is empty and stays empty — see the module docstring."""
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
            body="",
            audio_url=m.url if m.fmt in ("mp3", "wav") else None,
            meta={
                "url": m.url,
                "kind": m.kind,
                "format": m.fmt,
                "external": True,
                "official": True,
                "note": "Официальный экзаменационный материал — © Haridus- ja Noorteamet.",
            },
        )
        for m in materials
        if m.kind not in NOT_INDEXED
    ]
