"""Harvest "Selges keeles" — simplified Estonian news.

Short posts in plain Estonian, the reading corpus. Fetched through
WordPress.com's public REST API (no key, proper pagination). The project stopped
publishing, so this is a fixed corpus: harvest once.

Owner-only: a WordPress blog carries no reuse grant.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass

from .. import net

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
    """Markup to prose via `eesti/harvest/clean.py`."""
    from .clean import text

    return text(markup)


def fetch(site: str = SITE, limit: int | None = None) -> list[Post]:
    """Page through the archive. `limit` caps the number of posts for a dry run."""
    posts: list[Post] = []
    page = 1
    while True:
        url = f"{API.format(site=site)}?number={PAGE_SIZE}&page={page}"
        # Three attempts at 90 seconds (a WordPress.com cold start is slow), with the
        # app's User-Agent so the fetcher is identifiable.
        payload = json.loads(
            net.get(url, "Selges keeles", timeout=TIMEOUT, retries=RETRIES))

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
    """Order this corpus by difficulty relative to itself (`eesti/difficulty.py`)."""
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
            # A relative band in its own column; `level` is reserved for CEFR.
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
