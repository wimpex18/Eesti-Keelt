"""Official practice tasks from EIS, the state exam information system.

`eis.harno.ee/publicitems` serves the exam board's own reading and listening
tasks, per CEFR level, with immediate scoring and no login.

- Filter by `keeletase`; `aine=R` returns nothing (tasks are filed under Eesti
  keel).
- The catalogue is small: A2 and B1 have a handful each; A1 and C2 are empty.

The task itself lives in an iframe (`/publicitems/<id>/edittask`) that carries
the whole exercise: the instruction, the questions, the options and — for
listening — the recordings. `fetch_task` reads that frame, so the task can be
**read and heard inside the app** (© Haridus- ja Noorteamet, private study).

**The key stays on their server.** EIS scores by posting back to EIS, and the
correct answers appear nowhere in the page, so nothing here grades an EIS task:
the app shows the task and links out to the scored version. That is also why a
model is not asked to supply answers (ADR-0004: only the text may key a
question).
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

#: The iframe holding the exercise, and the recordings inside it.
_FRAME_RE = re.compile(r'<iframe[^>]+src="([^"]+)"')
_AUDIO_RE = re.compile(r'src="(https?://[^"]+\.(?:mp3|wav|m4a|ogg)[^"]*)"', re.I)
_NOISE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)

#: What the frame says about its own machinery rather than about Estonian: the
#: play counter ("Kuulamiste arv: 0 /2") and the buttons around the exercise.
_CHROME = re.compile(
    r"Kuulamiste arv:\s*\d+\s*/\s*\d+|Laadin\.\.\.|Kinnita|Proovi uuesti|Tagasi")
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


def fetch_task(task: "Task", opener=None) -> tuple[str, list[str]]:
    """One task as text, and its recordings. `("", [])` when EIS changed shape.

    Their server, so: one page and one frame per task, a second apart, and a
    failure is never fatal — the item keeps its link.
    """
    from .clean import text as readable

    opener = opener or _opener()
    try:
        page = opener.open(task.url, timeout=TIMEOUT).read().decode("utf-8", "replace")
        found = _FRAME_RE.search(page)
        if not found:
            return "", []
        frame = urllib.parse.urljoin(BASE, found.group(1).replace("&amp;", "&"))
        time.sleep(POLITE_DELAY)
        markup = opener.open(frame, timeout=TIMEOUT).read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - a task that will not load still links out
        return "", []
    audio = list(dict.fromkeys(_AUDIO_RE.findall(markup)))
    body = _CHROME.sub(" ", readable(_NOISE_RE.sub(" ", markup)))
    return " ".join(body.split()), audio


def to_items(tasks: list[Task], bodies: dict[str, tuple[str, list[str]]] | None = None) -> list:
    """Items for the library: the task's own text where it was fetched, its link
    otherwise. Scoring always stays at EIS.
    """
    from ..sources import Item

    bodies = bodies or {}
    out = []
    for task in tasks:
        body, audio = bodies.get(task.id, ("", []))
        out.append(Item(
            source_id="eis",
            skill=task.skill,
            level=task.level,
            title=task.title,
            body=body,
            audio_url=audio[0] if audio else None,
            meta={
                "url": task.url,
                # An exam task, like HARNO's own: it belongs in `Eksam ->
                # Eksamiülesanded`, not among the texts read for pleasure
                # (`library.SECTIONS`).
                "kind": "ulesanne",
                # Several recordings per listening task, in the order they are
                # asked about; the reader plays them all.
                "audio": audio,
                "external": not body,
                "official": True,
                "note": ("Официальное тренировочное задание — © Haridus- ja "
                         "Noorteamet. Ответы проверяются на сайте EIS."),
            },
        ))
    return out


def harvest(levels: tuple[str, ...] = LEVELS) -> dict[str, list[Task]]:
    tasks = catalogue(levels)
    by_level: dict[str, list[Task]] = {}
    for task in tasks:
        by_level.setdefault(task.level, []).append(task)
    return by_level
