"""Official practice tasks from EIS, the state exam information system.

## What this is, and why it is worth having

`eis.harno.ee/publicitems` publishes the exam board's *own* practice tasks —
reading and listening, per CEFR level, with immediate scoring — and serves them
without a login. It is the only material in this project written by the people
who write the real exam. Everything else the app produces is generated from a
word list or harvested from a radio archive; this is the thing they will
actually be graded against.

## What was found, against what the plan assumed

The plan said to filter by `aine=R` (*Eesti keel teise keelena*) and described
an enumerable A2–C1 catalogue. Probed directly:

- **`aine=R` returns nothing at all.** The tasks are filed under general Eesti
  keel, so that filter finds zero.
- **`keeletase` is the filter that works**, and the catalogue is small: 23 tasks
  in total, of which **14 are A2 and B1** — 7 each, split between `Lugemine` and
  `Kuulamine`.
- A1 and C2 are empty.

Small, then, but not thin: seven official A2 tasks is a real rehearsal for
whichever sitting is chosen.

## Why this indexes rather than copies

The task body lives in an iframe on HARNO's own site, and it is **copyright
Haridus- ja Noorteamet**. Two reasons not to pull it in, and they point the same
way:

1. Scraping the iframe would yield dead text — the scoring, the immediate
   feedback and the interaction all live on their page. A copy is strictly worse
   than a link.
2. The material is owner-only. Holding it, even behind Access, is a risk that
   buys nothing when a link buys everything.

So this stores a **pointer**: level, skill, title, maximum points, URL. The app
can say "four official A2 reading tasks, here they are" and send the learner to
the exam board's own site to do them. Nothing of theirs is ever in our database.
"""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

BASE = "https://eis.harno.ee/publicitems"

#: Levels this app teaches, plus B2 so the ceiling is visible. A1 and C2 were
#: probed and are empty.
LEVELS = ("A2", "B1", "B2", "C1")

#: Somebody else's server, and the whole catalogue is 23 pages.
POLITE_DELAY = 1.0
TIMEOUT = 45.0

_RID_RE = re.compile(r'name="rid"[^>]*value="([^"]+)"')
_ITEM_RE = re.compile(r'/publicitems/(\d+)"[^>]*>\s*([^<]{3,160})')
_POINTS_RE = re.compile(r"max\s+(\d+)\s*p")

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
    # The search refuses without a browser-shaped agent and a session cookie.
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (compatible; eesti-keelt)")]
    return opener


def _skill_of(title: str) -> str | None:
    lowered = title.casefold()
    for marker, skill in _SKILLS.items():
        if lowered.startswith(marker):
            return skill
    return None


def catalogue(levels: tuple[str, ...] = LEVELS) -> list[Task]:
    """Every published practice task at the given levels.

    One request per level, a second apart. The search needs a session token from
    the form page, so that is fetched once and reused.
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
    """Pointers, not copies. See the module docstring.

    `body` is deliberately empty: there is nothing of HARNO's in here, and the
    app's own degradation rules already treat a bodyless item as something to
    link to rather than something to read.
    """
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
