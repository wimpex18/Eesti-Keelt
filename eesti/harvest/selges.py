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

import html as _html
import json
import re
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime

API = "https://public-api.wordpress.com/rest/v1.1/sites/{site}/posts/"
SITE = "selgeskeeles.wordpress.com"
# 100 posts per page reliably times out; 25 is comfortably inside the limit.
PAGE_SIZE = 25
POLITE_DELAY = 0.4
TIMEOUT = 90.0
RETRIES = 3

_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+")
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
    """Strip tags, decode entities, drop URLs.

    Entities must be decoded here, not in the UI: the reader escapes what it
    renders, so an undecoded "&#8211;" arrives as the literal text "&amp;#8211;".
    Decoding twice is deliberate — WordPress double-encodes some entities.

    URLs are removed because the reader makes every word clickable for lookup,
    and the fragments of a link ("kultuur", "err", "ee") are not Estonian words.
    """
    text = _TAG_RE.sub(" ", markup)
    text = _html.unescape(_html.unescape(text))
    text = _URL_RE.sub(" ", text)
    return " ".join(text.split())


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
    """Order the corpus by difficulty, relative to itself.

    An earlier version tried to assign an absolute CEFR level from vocabulary
    coverage and rated 342 of 349 deliberately-simplified news items as B2 —
    obviously wrong. The cause is structural: only 9 951 of 160 316 lemmas
    (6.2 %) carry a CEFR tag, so "share of words at A1-A2" systematically
    undercounts. Measured across this corpus, coverage runs 0.25-0.87 with a
    median of 0.53, nowhere near the 0.85 an "A2 text" would need.

    So this does not claim a CEFR level. It ranks posts against each other and
    splits them into thirds, which is all that is needed for the real job:
    letting the reader start with the easier texts. Labels are Estonian and
    deliberately relative — `kergem` / `keskmine` / `raskem`.
    """
    from ..lookup import annotate

    scored = []
    for post in posts:
        profile = annotate(post.body, levels=("A1", "A2"))
        scored.append((post.url, profile.get("coverage", 0.0)))

    ranked = sorted(scored, key=lambda pair: -pair[1])
    third = max(1, len(ranked) // 3)
    bands = {}
    for index, (url, _) in enumerate(ranked):
        if index < third:
            bands[url] = "kergem"
        elif index < 2 * third:
            bands[url] = "keskmine"
        else:
            bands[url] = "raskem"
    return bands


def to_items(posts: list[Post]) -> list:
    from ..sources import Item

    bands = rank_difficulty(posts)
    return [
        Item(
            source_id="selges-keeles",
            skill="lugemine",
            title=post.title,
            body=post.body,
            # A relative difficulty band, not a CEFR claim — see rank_difficulty.
            level=bands.get(post.url, "keskmine"),
            meta={
                "url": post.url,
                "words": post.word_count,
                "published": post.published,
                "estonian_share": post.estonian_share,
            },
        )
        for post in posts
    ]
