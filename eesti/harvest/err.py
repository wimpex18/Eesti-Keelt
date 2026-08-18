"""One-time harvest of ERR's Estonian-for-Russian-speakers radio archives.

**What these actually are, measured rather than assumed.** Across the 28
harvested episodes the transcripts are **12 % Estonian** — 3 214 Estonian words
against 23 147 Russian. They are Russian-language *grammar lessons* with Estonian
examples embedded, not Estonian reading material. An earlier plan filed them
under `lugemine`; that was wrong, and reading practice has to come from a source
that is actually in Estonian (Lihtsad uudised, HARNO reading tasks).

What they are good for, and it is a lot:

  * **Grammar explanation in Russian** — the learner's native language, and the
    language corrections are explained in. Several episodes cover exactly the
    completed/incomplete object contrast behind the `obj-case` gap.
  * **Listening** — the audio is bilingual, so it is graded input rather than a
    wall of native speech.
  * **Example sentences** — the Estonian fragments are teacher-curated
    illustrations of specific grammar points. `estonian_fragments()` pulls them
    out for use as drill material.

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

# One known episode per series; the crawl expands outward from each by following
# the ld+json sibling list. Any episode works as a seed — these are just ones
# whose ids were easy to find.
SEEDS = {
    "kak_eto_po_estonski": "https://r4.err.ee/755936/kak-jeto-po-jestonski-28",
    # Course two (2015-16). Episode 27 covers rektsioon and 25 the minema /
    # tulema / käima trio — both are error-log tags.
    "ekeel": "https://r4.err.ee/764574/kak-jeto-po-jestonski-kurs-vtoroj-27",
    # Keelekõdi (2019), the largest of the three at ~100 episodes.
    "keelekodi": "https://r4.err.ee/932880/keelekodi-17",
}

# Deliberately slow. This is somebody else's server and the whole corpus is
# fetched exactly once.
POLITE_DELAY = 1.0
USER_AGENT = "Eesti-Keelt/0.1 (personal language study; one-time archive fetch)"

_PCD_RE = re.compile(r"window\.pageControlData\s*=\s*(\{.*?\});\s*\n", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_LATIN_RE = re.compile(r"[A-Za-zÕÄÖÜõäöüŠŽšž]+")
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]+")
# A run of Latin-script words with Estonian-legal punctuation between them.
_FRAGMENT_RE = re.compile(r"[A-Za-zÕÄÖÜõäöüŠŽšž][A-Za-zÕÄÖÜõäöüŠŽšž \-']{8,120}")


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
    def estonian_word_count(self) -> int:
        return len(_LATIN_RE.findall(self.body))

    @property
    def estonian_share(self) -> float:
        """Fraction of words in Latin script.

        Crude but sufficient: these transcripts are Russian prose with Estonian
        examples, and script cleanly separates the two.
        """
        latin = len(_LATIN_RE.findall(self.body))
        cyrillic = len(_CYRILLIC_RE.findall(self.body))
        total = latin + cyrillic
        return round(latin / total, 3) if total else 0.0

    def estonian_fragments(self, min_words: int = 3) -> list[str]:
        """Estonian runs of `min_words`+ words — the worked examples.

        These are what a teacher wrote on the board to illustrate a rule, so they
        are better drill material than anything generated: real, idiomatic, and
        already tied to a grammar point.
        """
        out = []
        for run in _FRAGMENT_RE.findall(self.body):
            cleaned = " ".join(run.split())
            if len(cleaned.split()) >= min_words:
                out.append(cleaned)
        return out

    @property
    def content_key(self) -> str:
        """Identity by transcript, not by URL.

        ERR publishes the same episode under several content ids — a crawl of
        one series returned "Как это по-эстонски? 21" three times at three
        different ids. The transcript is what makes an episode distinct.
        """
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
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_episode(html: str, url: str) -> Episode | None:
    """Pull transcript and audio out of an episode page.

    An episode is worth keeping if it has *either* a transcript or audio. Only
    the 2010 series carries transcripts; the 2015 and 2019 series are audio-only,
    and requiring text discarded them entirely.
    """
    content = _page_data(html).get("mainContent") or {}
    body_html = content.get("body") or ""
    text = " ".join(_TAG_RE.sub(" ", body_html).split())

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
                    # Episodes with a transcript are Russian-language grammar
                    # lessons (measured 12% Estonian). Audio-only episodes are
                    # listening material and nothing else.
                    skill="grammatika" if episode.word_count > 100 else "kuulamine",
                    title=episode.title,
                    body=episode.body,
                    audio_url=episode.audio_url,
                    meta={
                        "series": series,
                        "url": episode.url,
                        "words": episode.word_count,
                        "published": episode.published,
                        "has_audio": bool(episode.audio_url),
                        "estonian_words": episode.estonian_word_count,
                        "estonian_share": episode.estonian_share,
                    },
                )
            )
    return items
