"""One-time harvest of ERR's Estonian-for-Russian-speakers radio archives.

The transcripts are mostly Russian: grammar lessons with Estonian examples, not
reading material. They are used for:

- **grammar explanation in Russian** (several episodes cover the object-case
  contrast);
- **listening** — bilingual audio.

The archives are closed and static, so this runs once, caches to disk and never
touches ERR again.

- listing — archive pages render in JavaScript, so series are crawled from a
  seed episode via sibling links.
- episode — server-rendered: `window.pageControlData` carries the transcript
  (`mainContent.body`) and the MP3 (`playerClips[*].src`).

Content is © ERR, owner-only: study, never republish.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from ..config import CACHE

# One known episode per series; the crawl follows the ld+json sibling list.
SEEDS = {
    "kak_eto_po_estonski": "https://r4.err.ee/755936/kak-jeto-po-jestonski-28",
    # Course two (2015-16). Episode 27 covers rektsioon and 25 the minema /
    # tulema / käima trio — both are error-log tags.
    "ekeel": "https://r4.err.ee/764574/kak-jeto-po-jestonski-kurs-vtoroj-27",
    # Keelekõdi (2019), the largest of the three at ~100 episodes.
    "keelekodi": "https://r4.err.ee/932880/keelekodi-17",
}

# Deliberately slow: somebody else's server, fetched once.
POLITE_DELAY = 1.0
USER_AGENT = "Eesti-Keelt/0.1 (personal language study; one-time archive fetch)"

_PCD_RE = re.compile(r"window\.pageControlData\s*=\s*(\{.*?\});\s*\n", re.S)
from .clean import text as _clean_markup
_LATIN_RE = re.compile(r"[A-Za-zÕÄÖÜõäöüŠŽšž]+")
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]+")
# A run of Latin-script words with Estonian-legal punctuation between them.


@dataclass(frozen=True)
class Episode:
    url: str
    title: str
    body: str          # plain-text transcript
    audio_url: str | None
    published: str | None
    #: The teacher's one-line lesson label, e.g.
    #: "Урок 22. Падеж дополнения в законченном действии." Most episodes are
    #: audio-only, so this is often the only description of the grammar point.
    summary: str = ""

    @property
    def word_count(self) -> int:
        return len(self.body.split())

    @property
    def estonian_word_count(self) -> int:
        return len(_LATIN_RE.findall(self.body))

    @property
    def estonian_share(self) -> float:
        """Fraction of words in Latin script (Estonian vs Russian prose)."""
        latin = len(_LATIN_RE.findall(self.body))
        cyrillic = len(_CYRILLIC_RE.findall(self.body))
        total = latin + cyrillic
        return round(latin / total, 3) if total else 0.0

    @property
    def content_key(self) -> str:
        """Identity by transcript, not by URL: ERR publishes one episode under several ids."""
        # Audio-only episodes in the later series all carry the same series
        # blurb, so hashing the body alone would collapse ~140 of them into one.
        # The audio URL is what distinguishes them.
        key = self.body if self.word_count > 100 else f"{self.title}|{self.audio_url}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


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
    """One attempt per page: `crawl_series` skips a page it cannot read."""
    from .. import net

    return net.get(url, "ERR", timeout=timeout, retries=1, ua=USER_AGENT)


def parse_episode(html: str, url: str) -> Episode | None:
    """Pull transcript and audio out of an episode page; keep it if it has either
    (later series are audio-only).
    """
    content = _page_data(html).get("mainContent") or {}
    body_html = content.get("body") or ""
    # Never decoded entities before, so `&#8211;` reached the reader as
    # literal characters in 27 000 words of transcript.
    text = _clean_markup(body_html)

    # Two audio shapes across the archives: the 2010 series serves plain MP3s,
    # while the 2015 and 2019 series serve HLS streams (.m3u8). Accepting only
    # MP3 silently dropped both later series, which is why they looked empty.
    audio = None
    for clip in _page_data(html).get("playerClips") or []:
        src = clip.get("src") or ""
        if src.endswith((".mp3", ".m3u8")):
            audio = f"https:{src}" if src.startswith("//") else src
            break

    published = content.get("publicStart")
    return Episode(
        url=url,
        title=content.get("heading") or "",
        body=text,
        audio_url=audio,
        published=str(published) if published else None,
        summary=_clean_markup(content.get("lead") or ""),
    )
_LDJSON_RE = re.compile(
    r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S
)
_EPISODE_URL_RE = re.compile(r"^https://r4\.err\.ee/\d{5,}/")


def _sibling_urls(html: str) -> list[str]:
    """Related-episode links from the page's ld+json ItemList.

    Only the numeric id in those URLs is meaningful; the slugs are inherited from
    the current page.
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

    Returns {url: html}. Pages from another series are fetched once but not
    expanded.
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
    """Crawl each series from a seed episode and parse every page; cached, so a
    re-run makes no requests.
    """
    seeds = seeds or SEEDS
    out: dict[str, list[Episode]] = {}
    for name, seed in seeds.items():
        unique: dict[str, Episode] = {}
        for url, html in crawl_series(seed, max_pages, cache_dir).items():
            episode = parse_episode(html, url)
            if episode is None:
                continue
            # Keep an episode with a real transcript, or one with audio even if
            # its page carries only a series blurb — the later series are
            # listening material and nothing else.
            if episode.word_count > 100 or episode.audio_url:
                unique.setdefault(episode.content_key, episode)
        out[name] = sorted(unique.values(), key=lambda e: e.published or "")
    return out


def to_items(harvested: dict[str, list[Episode]]) -> list:
    """Convert episodes into content items: one item per episode, carrying both
    transcript and audio.
    """
    from ..difficulty import rank
    from ..sources import Item

    # Only the episodes that carry a transcript can be ranked; two thirds of
    # this archive is audio with no text, and banding those would be sorting
    # nothing.
    with_text = {
        e.url: e.body
        for eps in harvested.values() for e in eps if e.word_count > 100
    }
    bands = rank(with_text)

    items = []
    for series, episodes in harvested.items():
        for episode in episodes:
            items.append(
                Item(
                    source_id="err-r4",
                    # Episodes with a transcript are Russian grammar lessons; audio-only ones are
                    # listening material.
                    skill="grammatika" if episode.word_count > 100 else "kuulamine",
                    title=episode.title,
                    band=bands.get(episode.url),
                    # An audio-only episode falls back to the teacher's label,
                    # so the library shows what it is about instead of a blank.
                    body=episode.body or episode.summary,
                    audio_url=episode.audio_url,
                    meta={
                        "series": series,
                        "url": episode.url,
                        "words": episode.word_count,
                        "published": episode.published,
                        "has_audio": bool(episode.audio_url),
                        "estonian_words": episode.estonian_word_count,
                        "estonian_share": episode.estonian_share,
                        "summary": episode.summary,
                        "transcript": bool(episode.body),
                    },
                )
            )
    return items
