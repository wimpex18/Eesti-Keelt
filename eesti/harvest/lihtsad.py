"""ERR *Lihtsad uudised* — simplified Estonian news, the one live reading source.

Published weekly in plain Estonian for learners, so it keeps supplying current
text while the other sources are fixed archives.

- **Text:** several short items per issue; HTML entities (`&uuml;`) are
  unescaped.
- **No audio:** the player loads by JavaScript, and no audio URL is in the HTML,
  so items are text only.
- Filtered out: the recurring English series blurb, and share-widget SVG text.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

FEED = "https://news.err.ee/k/lihtsad-uudised"
TIMEOUT = 45.0

#: The User-Agent this harvester sends.
UA = "Mozilla/5.0 (compatible; eesti-keelt)"
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
    """One attempt. `harvest` catches `OSError` per issue, so a dead URL costs
    that issue and not the run -- which is why `net.Unreachable` is an
    `OSError`."""
    from .. import net

    return net.get(url, "ERR Lihtsad uudised", timeout=TIMEOUT, retries=1, ua=UA)


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
    """Fetch issues, politely, newest first; `limit` suits a weekly refresh."""
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
