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

## What the classification is read from

Filenames, because HARNO names them well: `A2_Kirjutamine_Esimene_ülesanne`,
`B1 kuulamisülesanne nr 1.mp3`. Anything whose level or part cannot be read off
the name is skipped rather than guessed — a writing task filed as listening
would send a learner to prepare the wrong thing.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

PAGE = "https://harno.ee/eesti-keele-tasemeeksamid"
BASE = "https://harno.ee"
TIMEOUT = 45.0

LEVELS = ("A2", "B1", "B2", "C1")

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
_LINK_RE = re.compile(r'href="([^"]+?\.(?:pdf|mp3))(?:\?[^"]*)?"', re.I)


@dataclass(frozen=True)
class Material:
    url: str
    level: str
    skill: str
    title: str
    kind: str  # pdf | mp3


def _decode(url: str) -> str:
    """The readable filename, for classifying and for showing to a learner."""
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1]).split("?")[0]
    return " ".join(name.rsplit(".", 1)[0].replace("_", " ").split())


def _level_of(name: str) -> str | None:
    for level in LEVELS:
        # Word-ish boundary: "B1 kuulamine" and "B1_Lu2A" both count, but a
        # stray "A2" inside a longer token does not.
        if re.search(rf"(?<![A-Za-z0-9]){level}(?![a-z0-9])", name, re.I):
            return level
    return None


def _skill_of(name: str) -> str | None:
    lowered = name.casefold()
    # Whole words first: they are unambiguous, and a filename carrying both
    # ("B1 kuulamisülesanne") should be read the plain way.
    for marker, skill in _PARTS.items():
        if marker in lowered:
            return skill
    code = _CODE_RE.search(name)
    return _PART_CODES[code.group(1).casefold()] if code else None


def catalogue(html: str | None = None) -> list[Material]:
    """Every classifiable PDF and MP3 linked from the exam page.

    One request. The page is a directory of links, and the files themselves are
    never fetched — that is the whole point.
    """
    if html is None:
        request = urllib.request.Request(
            PAGE, headers={"User-Agent": "Mozilla/5.0 (compatible; eesti-keelt)"}
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            html = response.read().decode("utf-8", "replace")

    found: dict[str, Material] = {}
    for href in _LINK_RE.findall(html):
        url = href if href.startswith("http") else urllib.parse.urljoin(BASE, href)
        url = url.replace("&amp;", "&")
        title = _decode(url)
        level, skill = _level_of(title), _skill_of(title)
        if not (level and skill):
            # Framework documents, information sheets, CEFR descriptors: real
            # material, but not a task for a particular part at a particular
            # level, and filing it as one would mislead.
            continue
        found[url] = Material(
            url=url, level=level, skill=skill, title=title,
            kind="mp3" if url.lower().split("?")[0].endswith(".mp3") else "pdf",
        )
    return sorted(found.values(), key=lambda m: (m.level, m.skill, m.title))


def to_items(materials: list[Material]) -> list:
    """Pointers. `body` is empty and stays empty — see the module docstring."""
    from ..sources import Item

    return [
        Item(
            source_id="harno",
            skill=m.skill,
            level=m.level,
            title=m.title,
            body="",
            audio_url=m.url if m.kind == "mp3" else None,
            meta={
                "url": m.url,
                "kind": m.kind,
                "external": True,
                "official": True,
                "note": "Ametlik eksamimaterjal — © Haridus- ja Noorteamet.",
            },
        )
        for m in materials
    ]
