"""One-time harvest of ERR's Estonian-for-Russian-speakers radio archives.

Three archives, ~170 episodes, each pairing a **full transcript** with **audio** —
so a single harvest supplies both Lugemine and Kuulamine material. Several
episodes teach exactly the completed/incomplete object contrast behind the
`obj-case` gap.

All three archives are closed and static: nothing new is being added. So this
runs once, caches to disk, and never touches ERR again. That is both polite and
the reason the result can be treated as a local corpus.

Two extraction paths, because the site needs both:

  listing  — the archive page renders its episode list in JavaScript, so plain
             HTTP returns nothing. Rendered once per archive with Chromium.
  episode  — the article page is server-rendered: `window.pageControlData`
             carries the transcript in `mainContent.body` and the MP3 in
             `playerClips[*].src`. Plain HTTP, no browser.

Content is © ERR. Registered as owner-only in `eesti.sources`: fine to study
from, never to republish.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..config import CACHE

# Archive index pages, for reference. They render their episode lists in
# JavaScript, so they are not fetchable — the crawl uses seeds instead.
ARCHIVES = {
    "kak_eto_po_estonski": "https://r4.err.ee/arhiiv/kak_eto_po_estonski",
    "ekeel": "https://r4.err.ee/arhiiv/ekeel",
    "keelekodi": "https://r4.err.ee/arhiiv/keelekodi",
}

# One known episode per series; the crawl expands outward from each.
SEEDS = {
    "kak_eto_po_estonski": "https://r4.err.ee/755936/kak-jeto-po-jestonski-28",
}

# Deliberately slow. This is somebody else's server and the whole corpus is
# fetched exactly once.
POLITE_DELAY = 1.0
USER_AGENT = "Eesti-Keelt/0.1 (personal language study; one-time archive fetch)"

_PCD_RE = re.compile(r"window\.pageControlData\s*=\s*(\{.*?\});\s*\n", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Episode:
    url: str
    title: str
    body: str          # plain-text transcript
    audio_url: str | None
    published: str | None

    @property
    def word_count(self) -> int:
        return len(self.body.split())

    @property
    def content_key(self) -> str:
        """Identity by transcript, not by URL.

        ERR publishes the same episode under several content ids — a crawl of
        one series returned "Как это по-эстонски? 21" three times at three
        different ids. The transcript is what makes an episode distinct.
        """
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()[:16]


def _balanced(raw: str) -> str:
    """Trim to the first balanced {...}; the regex can overrun into later script."""
    depth = 0
    for i, ch in enumerate(raw):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[: i + 1]
    return raw


def _page_data(html: str) -> dict:
    match = _PCD_RE.search(html)
    if not match:
        return {}
    try:
        return json.loads(_balanced(match.group(1)))
    except json.JSONDecodeError:
        return {}


def _get(url: str, timeout: float = 45.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_episode(html: str, url: str) -> Episode | None:
    """Pull transcript and audio out of an episode page."""
    content = _page_data(html).get("mainContent") or {}
    body_html = content.get("body") or ""
    text = " ".join(_TAG_RE.sub(" ", body_html).split())
    if not text:
        return None

    audio = None
    for clip in _page_data(html).get("playerClips") or []:
        src = clip.get("src") or ""
        if src.endswith(".mp3"):
            audio = f"https:{src}" if src.startswith("//") else src
            break

    published = content.get("publicStart")
    return Episode(
        url=url,
        title=content.get("heading") or "",
        body=text,
        audio_url=audio,
        published=str(published) if published else None,
    )


def fetch_episode(url: str) -> Episode | None:
    return parse_episode(_get(url), url)


_LDJSON_RE = re.compile(
    r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S
)
_EPISODE_URL_RE = re.compile(r"^https://r4\.err\.ee/\d{5,}/")


def _sibling_urls(html: str) -> list[str]:
    """Related-episode links from the page's ld+json ItemList.

    ERR's archive listing is rendered client-side, so plain HTTP sees no episode
    links at all — and a headless browser cannot reach the host from a sandboxed
    session (ERR_CONNECTION_RESET even through the proxy). But every episode page
    carries an ItemList of sibling episodes, which makes the series a graph that
    can be walked with ordinary requests. Note the slugs in those URLs are
    inherited from the current page and are misleading; only the numeric id is
    meaningful.
    """
    urls: list[str] = []
    for blob in _LDJSON_RE.findall(html):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if data.get("@type") != "ItemList":
            continue
        for item in data.get("itemListElement") or []:
            url = item.get("url") or ""
            if _EPISODE_URL_RE.match(url):
                urls.append(url)
    return urls


def _series_name(html: str) -> str:
    return (_page_data(html).get("serialName") or "").strip()


def crawl_series(
    seed_url: str,
    max_pages: int = 400,
    cache_dir: Path | None = None,
) -> dict[str, str]:
    """Walk a series from one known episode, following sibling links.

    Returns {url: html}. Pages whose series name differs from the seed's are
    fetched once (there is no way to know without looking) but not expanded, so
    the crawl stays inside the series.
    """
    cache = Path(cache_dir or CACHE) / "err"
    cache.mkdir(parents=True, exist_ok=True)

    def load(url: str) -> str:
        path = cache / f"{url.rstrip('/').split('/')[-2]}.html"
        if path.exists():
            return path.read_text(encoding="utf-8")
        html = _get(url)
        path.write_text(html, encoding="utf-8")
        time.sleep(POLITE_DELAY)
        return html

    seed_html = load(seed_url)
    target = _series_name(seed_html)
    found = {seed_url: seed_html}
    queue = [seed_url]

    while queue and len(found) < max_pages:
        html = found[queue.pop(0)]
        for url in _sibling_urls(html):
            if url in found:
                continue
            try:
                sibling = load(url)
            except Exception:
                continue
            found[url] = sibling
            if not target or _series_name(sibling) == target:
                queue.append(url)

    return {u: h for u, h in found.items() if not target or _series_name(h) == target}


def harvest(
    seeds: dict[str, str] | None = None,
    max_pages: int = 400,
    cache_dir: Path | None = None,
) -> dict[str, list[Episode]]:
    """Crawl each series from a seed episode and parse every page found.

    Everything is cached to disk, so a re-run issues no requests at all. The
    archives are closed and static, which is what makes one pass sufficient.
    """
    seeds = seeds or SEEDS
    out: dict[str, list[Episode]] = {}
    for name, seed in seeds.items():
        unique: dict[str, Episode] = {}
        for url, html in crawl_series(seed, max_pages, cache_dir).items():
            episode = parse_episode(html, url)
            if episode and episode.word_count > 100:
                unique.setdefault(episode.content_key, episode)
        out[name] = sorted(unique.values(), key=lambda e: e.published or "")
    return out


def to_items(harvested: dict[str, list[Episode]]) -> list:
    """Convert episodes into content items.

    Each episode becomes ONE item carrying both transcript and audio, because it
    is genuinely one artefact — the same material read and heard. The reading and
    listening views select on `skill`, and an episode serves both, so it is filed
    under `lugemine` with its audio attached rather than duplicated into two rows.
    """
    from ..sources import Item

    items = []
    for series, episodes in harvested.items():
        for episode in episodes:
            items.append(
                Item(
                    source_id="err-r4",
                    skill="lugemine",
                    title=episode.title,
                    body=episode.body,
                    audio_url=episode.audio_url,
                    meta={
                        "series": series,
                        "url": episode.url,
                        "words": episode.word_count,
                        "published": episode.published,
                        "has_audio": bool(episode.audio_url),
                    },
                )
            )
    return items
