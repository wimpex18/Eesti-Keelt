"""Harvest "Selges keeles" — simplified Estonian news.

This is the reading material the ERR radio archives turned out not to be. Those
transcripts measured **12 % Estonian** (Russian grammar lessons with Estonian
examples); these posts are **100 % Estonian**, short (35–80 words), and written
in deliberately plain language for people still learning it.

Fetched through WordPress.com's public REST API rather than by scraping: no key,
proper pagination, clean text. 349 posts at time of writing.

The project stopped publishing in 2018, which makes it a fixed corpus — harvest
once, never re-fetch. Older news is no loss for language practice: the point is
graded Estonian prose, not current affairs.

Content is the authors'. Registered as owner-only pending a licence check —
a WordPress blog carries no explicit reuse grant, and absence of a licence means
no permission, not open permission.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from dataclasses import dataclass

API = "https://public-api.wordpress.com/rest/v1.1/sites/{site}/posts/"
SITE = "selgeskeeles.wordpress.com"
# 100 posts per page reliably times out; 25 is comfortably inside the limit.
PAGE_SIZE = 25
POLITE_DELAY = 0.4
TIMEOUT = 90.0
RETRIES = 3

_LATIN_RE = re.compile(r"[A-Za-zÕÄÖÜõäöüŠŽšž]+")
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]+")


@dataclass(frozen=True)
class Post:
    url: str
    title: str
    body: str
    published: str | None

    @property
    def word_count(self) -> int:
        return len(self.body.split())

    @property
    def estonian_share(self) -> float:
        latin = len(_LATIN_RE.findall(self.body))
        cyrillic = len(_CYRILLIC_RE.findall(self.body))
        total = latin + cyrillic
        return round(latin / total, 3) if total else 0.0


def _clean(markup: str) -> str:
    """Markup to prose. See `eesti/harvest/clean.py` for what and why.

    This module's own version was the most complete of the four and is where
    the shared one came from — including decoding entities twice, which
    WordPress makes necessary.
    """
    from .clean import text

    return text(markup)


def fetch(site: str = SITE, limit: int | None = None) -> list[Post]:
    """Page through the archive. `limit` caps the number of posts for a dry run."""
    posts: list[Post] = []
    page = 1
    while True:
        url = f"{API.format(site=site)}?number={PAGE_SIZE}&page={page}"
        payload = None
        for attempt in range(RETRIES):
            try:
                with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
                    payload = json.loads(resp.read())
                break
            except (TimeoutError, OSError):
                if attempt == RETRIES - 1:
                    raise
                time.sleep(2 ** attempt)
        if payload is None:
            break

        batch = payload.get("posts") or []
        if not batch:
            break

        for item in batch:
            body = _clean(item.get("content") or "")
            if not body:
                continue
            posts.append(
                Post(
                    url=item.get("URL") or "",
                    title=_clean(item.get("title") or ""),
                    body=body,
                    published=(item.get("date") or "")[:10] or None,
                )
            )
            if limit and len(posts) >= limit:
                return posts

        if len(batch) < PAGE_SIZE:
            break
        page += 1
        time.sleep(POLITE_DELAY)
    return posts


def rank_difficulty(posts: list[Post]) -> dict[str, str]:
    """Order this corpus by difficulty, relative to itself.

    The reasoning, and the failed attempt it replaces, now live in
    `eesti/difficulty.py` — every prose source needs the same treatment, and
    the news feed and radio transcripts were getting no band at all.
    """
    from ..difficulty import rank

    return rank({post.url: post.body for post in posts})


def to_items(posts: list[Post]) -> list:
    from ..sources import Item

    bands = rank_difficulty(posts)
    return [
        Item(
            source_id="selges-keeles",
            skill="lugemine",
            title=post.title,
            body=post.body,
            # No CEFR claim: nobody credible has rated these, and the one
            # attempt to derive it rated 342 of 349 simplified items as B2.
            level=None,
            # A relative band, in its own column. It lived in `level` until a
            # learner filtering "B1" got only exam material and none of these.
            band=bands.get(post.url, "keskmine"),
            meta={
                "url": post.url,
                "words": post.word_count,
                "published": post.published,
                "estonian_share": post.estonian_share,
            },
        )
        for post in posts
    ]
