"""Official practice tasks from EIS, the state exam information system.

`eis.harno.ee/publicitems` serves the exam board's own reading and listening
tasks, per CEFR level, with immediate scoring and no login.

- Filter by `keeletase`; `aine=R` returns nothing (tasks are filed under Eesti
  keel).
- The catalogue is small: A2 and B1 have a handful each; A1 and C2 are empty.

**Pointers only.** Task bodies are © Haridus- ja Noorteamet and live in an
iframe whose scoring works only on their site. Stored: level, skill, title, URL.
"""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

BASE = "https://eis.harno.ee/publicitems"

#: Levels this app teaches, plus B2 so the ceiling is visible.
LEVELS = ("A2", "B1", "B2", "C1")

#: Somebody else's server, and the whole catalogue is 23 pages.
POLITE_DELAY = 1.0
TIMEOUT = 45.0

_RID_RE = re.compile(r'name="rid"[^>]*value="([^"]+)"')
_ITEM_RE = re.compile(r'/publicitems/(\d+)"[^>]*>\s*([^<]{3,160})')

#: The exam's four parts. Only two are published as public tasks -- there is no
#: automated way to sit a speaking or writing task, which is the honest reason
#: the app generates its own for those.
_SKILLS = {"lugemine": "lugemine", "kuulamine": "kuulamine"}


@dataclass(frozen=True)
class Task:
    id: str
    level: str
    skill: str
    title: str

    @property
    def url(self) -> str:
        return f"{BASE}/{self.id}"


def _opener():
    import http.cookiejar

    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    # The search requires a browser-shaped agent and a session cookie.
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (compatible; eesti-keelt)")]
    return opener


def _skill_of(title: str) -> str | None:
    lowered = title.casefold()
    for marker, skill in _SKILLS.items():
        if lowered.startswith(marker):
            return skill
    return None


def catalogue(levels: tuple[str, ...] = LEVELS) -> list[Task]:
    """Every published practice task at the given levels: one request per level, a
    second apart, reusing one session token.
    """
    opener = _opener()
    first = opener.open(BASE, timeout=TIMEOUT).read().decode("utf-8", "replace")
    match = _RID_RE.search(first)
    if not match:
        raise RuntimeError("EIS search form has changed: no rid token")
    rid = match.group(1)

    found: dict[str, Task] = {}
    for level in levels:
        query = urllib.parse.urlencode(
            {"rid": rid, "otsi": "1", "keeletase": level, "psize": "200"}
        )
        html = opener.open(f"{BASE}?{query}", timeout=TIMEOUT).read().decode(
            "utf-8", "replace"
        )
        for task_id, title in _ITEM_RE.findall(html):
            title = " ".join(title.split())
            skill = _skill_of(title)
            if skill is None:
                # Not a reading or listening task -- nothing this app can point
                # a learner at usefully.
                continue
            found[task_id] = Task(id=task_id, level=level, skill=skill, title=title)
        time.sleep(POLITE_DELAY)
    return sorted(found.values(), key=lambda t: (t.level, t.skill, t.title))


def to_items(tasks: list[Task]) -> list:
    """Pointers, not copies: `body` stays empty, so the app links out."""
    from ..sources import Item

    return [
        Item(
            source_id="eis",
            skill=task.skill,
            level=task.level,
            title=task.title,
            body="",
            meta={
                "url": task.url,
                "external": True,
                "official": True,
                "note": "Официальное тренировочное задание — решается на сайте EIS.",
            },
        )
        for task in tasks
    ]


def harvest(levels: tuple[str, ...] = LEVELS) -> dict[str, list[Task]]:
    tasks = catalogue(levels)
    by_level: dict[str, list[Task]] = {}
    for task in tasks:
        by_level.setdefault(task.level, []).append(task)
    return by_level
