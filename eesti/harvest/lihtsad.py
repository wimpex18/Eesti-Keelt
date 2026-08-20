"""ERR *Lihtsad uudised* — simplified Estonian news, and the only live source here.

## Why a live feed matters when three archives already exist

Everything else harvested for reading is **frozen**. The ERR radio courses ended
in 2019; Selges keeles is a fixed set of 349 posts. They are good material and
they will say exactly the same thing in spring 2027.

*Lihtsad uudised* is published weekly, in deliberately simplified Estonian, for
people learning the language. It is the one source that keeps producing
sentences about things that happened this month — which is what a reading exam
tests and what a frozen archive cannot supply.

## What is here, and what is not

**Text: yes.** Roughly 500 words per issue, several short news items, written
plainly. HTML entities and all — ERR serves `&uuml;` rather than `ü`, so the
text needs unescaping before it is Estonian at all.

**Audio: no, and not by choice.** The page says "listen and read", and the
player is loaded by JavaScript after the fact: there is no `.mp3` or `.m3u8`
anywhere in the HTML a plain request receives. Rather than pretend, these items
carry no `audio_url` and the reading library treats them as text.

Two paragraph filters earn their place. Each issue opens with the same English
sentence explaining what the series is — useful to a first-time visitor, noise
in a corpus of Estonian. And the share widget leaks its SVG attributes into the
paragraph text, which would otherwise put `aria-label` into a reading exercise.
"""

from __future__ import annotations

import re
import time
import urllib.request
from dataclasses import dataclass

FEED = "https://news.err.ee/k/lihtsad-uudised"
TIMEOUT = 45.0
#: Somebody else's newsroom, and this runs weekly at most.
POLITE_DELAY = 1.0

#: Below this an "article" is a stub or a redirect, not a reading.
MIN_WORDS = 60

_ARTICLE_RE = re.compile(r"news\.err\.ee/(\d{6,})/")
_LD_RE = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S)
_PARA_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
_STRIP_RE = re.compile(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", re.S)
from .clean import text as _clean_markup
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")

#: The standing English introduction, present on every issue.
_BOILERPLATE = "meaning easy or simple news"
#: Markup that leaked out of the share widget.
_LEAKED = ("aria-label", "class=", "fill=", "{{")


@dataclass(frozen=True)
class Issue:
    url: str
    title: str
    body: str
    published: str | None

    @property
    def word_count(self) -> int:
        return len(self.body.split())


def _get(url: str) -> str:
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; eesti-keelt)"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace")


def _usable(paragraph: str) -> bool:
    if len(paragraph.split()) < 4:
        return False
    if _BOILERPLATE in paragraph:
        return False
    if any(marker in paragraph for marker in _LEAKED):
        return False
    # A Russian paragraph is a translation block, not Estonian reading.
    return not _CYRILLIC_RE.search(paragraph)


def _headline(html: str) -> tuple[str, str | None]:
    import json

    for blob in _LD_RE.findall(html):
        try:
            data = json.loads(blob)
        except ValueError:
            continue
        if data.get("@type") in ("NewsArticle", "Article"):
            return data.get("headline") or "", data.get("datePublished")
    return "", None


def parse_issue(html: str, url: str) -> Issue | None:
    """Pull one issue's text out of an article page."""
    title, published = _headline(html)
    clean = _STRIP_RE.sub(" ", html)
    paragraphs = [
        _clean_markup(p)
        for p in _PARA_RE.findall(clean)
    ]
    body = "\n\n".join(p for p in paragraphs if _usable(p))
    if len(body.split()) < MIN_WORDS:
        return None
    return Issue(url=url, title=title.strip(), body=body, published=published)


def issue_urls(html: str | None = None) -> list[str]:
    """Article links from the category page, newest first."""
    html = _get(FEED) if html is None else html
    seen: list[str] = []
    for article_id in _ARTICLE_RE.findall(html):
        url = f"https://news.err.ee/{article_id}/"
        if url not in seen:
            seen.append(url)
    return seen


def harvest(limit: int | None = None) -> list[Issue]:
    """Fetch issues, politely, newest first.

    `limit` exists because this is a live feed: a weekly refresh wants the last
    few, not the whole back catalogue again.
    """
    urls = issue_urls()
    if limit is not None:
        urls = urls[:limit]

    issues: list[Issue] = []
    for url in urls:
        try:
            issue = parse_issue(_get(url), url)
        except (OSError, ValueError):
            # One article failing must not lose the rest of the harvest.
            continue
        if issue is not None:
            issues.append(issue)
        time.sleep(POLITE_DELAY)
    return issues


def to_items(issues: list[Issue]) -> list:
    """Reading material. Owner-only: © ERR, personal study."""
    from ..difficulty import rank
    from ..sources import Item

    # Ranked within this feed, not against the whole library: a news item and a
    # radio transcript are different registers, and pooling them would sort by
    # register rather than by difficulty.
    bands = rank({issue.url: issue.body for issue in issues})

    return [
        Item(
            source_id="err-lihtsad",
            skill="lugemine",
            # No CEFR claim. The series is written for learners and is plainly
            # simpler than the newsroom's usual output, but "simplified" is not
            # a level and this app does not invent one.
            level=None,
            band=bands.get(issue.url, "keskmine"),
            title=issue.title,
            body=issue.body,
            meta={
                "url": issue.url,
                "published": issue.published,
                "words": issue.word_count,
                "live_feed": True,
                "audio": False,
            },
        )
        for issue in issues
    ]
