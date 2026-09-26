"""Fixture databases, so no test depends on the developer's own build or data.

Paths resolve at call time, and this file redirects every database for every
test. The fixture data is small and real — genuine Estonian words with forms
from Vabamorf — so tests check real morphology; a test that needs the full
lexicon uses `real_wordlist`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from pagesrc import markup_and_script

# Everyday A1-B1 vocabulary, chosen to exercise every generator: verbs for
# conjugation, adjectives with attested comparatives, countable nouns for the
# numeral and object-case drills, and nouns whose genitive and partitive differ.
WORDS: tuple[tuple[str, int, str | None, str], ...] = (
    ("minema", 12, "A1", "v"), ("tegema", 15, "A1", "v"), ("saama", 18, "A1", "v"),
    ("õppima", 40, "A2", "v"), ("elama", 45, "A1", "v"), ("lugema", 60, "A1", "v"),
    ("ostma", 70, "A1", "v"), ("liikuma", 90, "B1", "v"), ("rääkima", 55, "A1", "v"),
    ("suur", 100, "A1", "adj"), ("ilus", 110, "A1", "adj"),
    ("raske", 130, "A2", "adj"), ("kiire", 140, "A2", "adj"),
    # The comparatives themselves must be present and corpus-attested, because
    # that pair of conditions is exactly what the comparison generator checks.
    ("suurem", 1160, None, "adj"), ("ilusam", 5000, None, "adj"),
    ("raskem", 3000, None, "adj"), ("kiirem", 4000, None, "adj"),
    ("raamat", 200, "A1", "s"), ("pilet", 210, "A1", "s"), ("auto", 220, "A1", "s"),
    ("leib", 230, "A1", "s"), ("kohv", 240, "A1", "s"), ("film", 250, "A1", "s"),
    ("kiri", 260, "A2", "s"), ("võti", 270, "A2", "s"), ("tool", 280, "A1", "s"),
    ("laud", 290, "A1", "s"), ("telefon", 300, "A1", "s"), ("arvuti", 310, "A1", "s"),
    ("lill", 320, "A1", "s"), ("kook", 330, "A1", "s"), ("õun", 340, "A1", "s"),
    ("supp", 350, "A2", "s"), ("kala", 360, "A1", "s"), ("liha", 370, "A1", "s"),
    ("sai", 380, "A1", "s"), ("jäätis", 390, "A2", "s"), ("särk", 400, "A2", "s"),
    ("kleit", 410, "A2", "s"), ("dokument", 420, "B1", "s"),
    ("aadress", 430, "A2", "s"), ("kingitus", 440, "A2", "s"),
    ("mäng", 450, "A1", "s"), ("saade", 460, "B1", "s"), ("video", 470, "A2", "s"),
    ("rahakott", 480, "A2", "s"), ("jalgratas", 490, "A2", "s"),
    ("ajaleht", 500, "A2", "s"), ("artikkel", 510, "B1", "s"),
    # Words the grammar and mining tests name specifically: gradating stems
    # (sõber/sõbra, pood/poe, tuba/toa) and words whose genitive and partitive
    # coincide (maja, kino), which is the case those tests exist to check.
    ("sõber", 150, "A1", "s"), ("pood", 160, "A1", "s"), ("tuba", 170, "A1", "s"),
    ("maja", 180, "A1", "s"), ("kino", 190, "A1", "s"), ("kets", 195, "B1", "s"),
    ("kohanema", 520, "B1", "v"), ("teavitama", 530, "B1", "v"),
    ("põhinema", 540, "B1", "v"), ("nautima", 550, "B1", "v"),
    ("sarnanema", 560, "B1", "v"), ("lähedane", 570, "B1", "adj"),
)

# Real simplified-Estonian prose, in the shape the harvester stores it. Short,
# but carrying the cases and the negation the cloze generators look for.
TEXTS: tuple[str, ...] = (
    "Ma elan Tallinnas ja käin iga päev tööl. "
    "Eile ostsin poest uue raamatu ja lugesin selle õhtul läbi.",
    "Riigikohus ei võtnud tema kaitsja kaebust arutusele. "
    "Kohtunik selgitas otsust pikalt ja rahulikult kõigile osapooltele.",
    "Laeva, millega nad pidid merele minema, tabas tehniline rike. "
    "Reisijad said sellest teada alles sadamas ootamise ajal.",
    "Kui rehvid on liiga halvas seisundis, ei luba politsei juhtidel teekonda jätkata. "
    "Uus seadus jõustub järgmise aasta alguses kogu riigis.",
)


def _theme_words() -> list[tuple[str, int, str, str]]:
    """Every themed lemma, so theme tests measure the themes. The "are these real
    words?" check uses the real lexicon instead, or it would be circular.
    """
    from eesti.themes import THEMES

    rows: dict[str, tuple[str, int, str, str]] = {}
    for offset, theme in enumerate(THEMES):
        for i, word in enumerate(theme.nouns):
            rows.setdefault(word, (word, 1000 + offset * 100 + i, "A2", "s"))
        for i, word in enumerate(theme.verbs):
            rows.setdefault(word, (word, 2000 + offset * 100 + i, "A2", "v"))
    return list(rows.values())


def _build_wordlist(path) -> None:
    from eesti.wordlist import SCHEMA

    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    # Columns named, not positional, so schema additions do not break the fixture.
    cols = "INSERT OR %s INTO words(word, freq_rank, proficiency, pos) VALUES (?,?,?,?)"
    conn.executemany(cols % "REPLACE", WORDS)
    # Inserted second so a word named in WORDS keeps its declared level.
    conn.executemany(cols % "IGNORE", _theme_words())
    # Seed two rections, so the generator runs offline (rections are normally fetched
    # once by `cli rections`).
    from eesti.rection import SCHEMA as RECTION_SCHEMA

    conn.executescript(RECTION_SCHEMA)
    conn.executemany(
        "INSERT OR REPLACE INTO rections VALUES (?,?,?,?,?)",
        [
            ("kohanema", "millega", "millele", "sg kom", "sg all"),
            ("teavitama", "keda", "kellele", "sg p", "sg all"),
        ],
    )
    conn.commit()
    conn.close()


def _build_edge(path) -> None:
    """A miniature of what `cli export` produces, built with Vabamorf itself."""
    from eesti.export import EXPORT_SCHEMA
    from eesti.morph import case_forms

    conn = sqlite3.connect(path)
    conn.executescript(EXPORT_SCHEMA)
    conn.executemany(
        "INSERT OR REPLACE INTO words (lemma,proficiency,freq_rank,pos) VALUES (?,?,?,?)",
        [(w, prof, rank, pos) for w, rank, prof, pos in WORDS],
    )
    for word, _rank, _prof, pos in WORDS:
        if pos != "s":
            continue
        forms = case_forms(word)
        if not forms:
            continue
        genitive, partitive = forms["genitive"], forms["partitive"]
        conn.execute(
            "INSERT OR REPLACE INTO object_cases VALUES (?,?,?,?)",
            (word, genitive, partitive, int(genitive != partitive)),
        )
        conn.executemany(
            "INSERT OR REPLACE INTO forms (form,lemma,tag) VALUES (?,?,?)",
            [(word, word, "sg n"), (genitive, word, "sg g"), (partitive, word, "sg p")],
        )
    conn.commit()
    conn.close()


def _build_content(path) -> None:
    """A content database built by the app's own opener, so the fixture has the
    production schema.
    """
    from eesti.sources import Item, add_items, connect as open_content, register

    conn = open_content(path)
    # `register` first: `add_items` refuses an unregistered source, which is
    # the licence gate and must not be bypassed even here.
    register(conn)
    add_items(conn, [
        Item(source_id="selges-keeles", skill="lugemine",
             title=f"Fixture {i}", body=body, level=None, band="keskmine",
             meta={"words": len(body.split())})
        for i, body in enumerate(TEXTS)
    ])
    conn.close()


@pytest.fixture
def real_wordlist():
    """The real Ekilex word list, or a skip.

    For tests that check curated content against the lexicon. Skips unless the
    build has rows (an empty file does not count).
    """
    import sqlite3 as _sqlite3
    from pathlib import Path

    from eesti.wordlist import available

    real = Path("data/eesti.db")
    if not available(real):
        pytest.skip("needs the full wordlist — run `cli fetch-data && cli build`")
    conn = _sqlite3.connect(f"file:{real}?mode=ro", uri=True)
    conn.row_factory = _sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# What this machine has, said out loud
# ---------------------------------------------------------------------------
#
# `data/` is git-ignored and Playwright optional, so the same command runs
# different suites on different machines. The header and summary line say which
# inputs were present.


def dataset_state() -> dict[str, object]:
    """Which optional inputs are present and how much they hold, read-only (opening a
    database to look would create it).
    """
    from pathlib import Path

    state: dict[str, object] = {
        "words": 0, "corpus": 0, "browsers": [], "evkk": False,
    }
    try:
        from eesti import config
        from eesti.sources import available as corpus_available
        from eesti.wordlist import available as words_available

        if words_available(config.DB_PATH):
            conn = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
            state["words"] = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
            conn.close()
        if corpus_available(config.CONTENT_DB):
            conn = sqlite3.connect(f"file:{config.CONTENT_DB}?mode=ro", uri=True)
            state["corpus"] = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            conn.close()
    except Exception:  # noqa: BLE001 - a header must never break a run
        pass

    try:
        import importlib.util

        # No `playwright` package and an empty browser directory both mean the journeys
        # skip; the directory scan is a separate function so it can be tested anywhere.
        if importlib.util.find_spec("playwright") is not None:
            state["browsers"] = installed_engines()
        state["evkk"] = (Path(config.CACHE) / "evkk_marks.html").exists()
    except Exception:  # noqa: BLE001
        pass
    return state


def browsers_root(env: "dict | None" = None, home: "Path | None" = None,
                  platform: "str | None" = None,
                  container: Path = Path("/opt/pw-browsers")) -> Path:
    """Where Playwright's browsers are: `PLAYWRIGHT_BROWSERS_PATH`, else
    `/opt/pw-browsers` where it exists, else Playwright's platform default.
    """
    import os
    import sys

    env = os.environ if env is None else env
    home = Path.home() if home is None else home
    platform = sys.platform if platform is None else platform
    if env.get("PLAYWRIGHT_BROWSERS_PATH"):
        return Path(env["PLAYWRIGHT_BROWSERS_PATH"])
    if container.is_dir():
        return container
    if platform == "darwin":
        return home / "Library" / "Caches" / "ms-playwright"
    return home / ".cache" / "ms-playwright"


def chromium_binary(root: Path) -> "str | None":
    """The Chromium executable under `root`, on Linux (`chrome-linux/chrome`) or macOS
    (an app bundle); the folder name carries a build number.
    """
    if not root.is_dir():
        return None
    for pattern in ("chromium-*/chrome-linux*/chrome",
                    "chromium-*/chrome-mac*/*.app/Contents/MacOS/*",
                    "chromium*/**/chrome"):
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                return str(path)
    return None


def installed_engines(root: "Path | None" = None) -> list[str]:
    """Which browser engines Playwright has unpacked, each named once (Chromium and its
    headless shell are one engine).
    """
    root = Path(root) if root else browsers_root()
    found = set()
    try:
        for path in root.glob("*-*"):
            for engine in ("chromium", "webkit", "firefox"):
                if path.name.startswith(engine):
                    found.add(engine)
    except OSError:
        return []
    return sorted(found)


def describe_dataset(state: dict[str, object]) -> str:
    """One line naming what will and will not run."""
    words, corpus, browsers = state["words"], state["corpus"], state["browsers"]
    parts = [
        # EVKK is listed because two tag-map checks skip without it.
        "evkk: cached" if state.get("evkk")
        else "evkk: absent (tag-map check vs the live page skips -- `cli evkk`)",
        f"word list: {words:,} words" if words
        else "word list: absent (some tests skip -- `cli fetch-data && cli build`)",
        f"corpus: {corpus:,} items" if corpus
        else "corpus: absent (reading journeys skip -- `cli harvest-reading`)",
        f"browsers: {', '.join(browsers)}" if browsers
        else "browsers: none (the journey suite skips entirely)",
    ]
    return "eesti | " + " | ".join(parts)


def pytest_report_header(config) -> str:
    """Printed before the run, so the result can never be read out of context."""
    return describe_dataset(dataset_state())


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """The same line at the end, because `-q` hides the header."""
    skipped = terminalreporter.stats.get("skipped", [])
    line = describe_dataset(dataset_state())
    if skipped:
        line += f" | {len(skipped)} skipped"
    terminalreporter.write_line(line)


@pytest.fixture(scope="session")
def fixture_data(tmp_path_factory):
    """Built once per session — Vabamorf synthesis is not free."""
    root = tmp_path_factory.mktemp("eesti-data")
    paths = {
        "words": root / "eesti.db",
        "edge": root / "edge.db",
        "content": root / "content.db",
        "cache": root / "cache",
    }
    paths["cache"].mkdir()
    _build_wordlist(paths["words"])
    _build_edge(paths["edge"])
    _build_content(paths["content"])
    return paths


@pytest.fixture(autouse=True)
def _no_accidental_network(request, monkeypatch):
    """Outbound HTTP fails at once, unless the test is about a live service.

    Every provider degrades when its service is unreachable, so an unstubbed call
    passes either way; left open, each one waited out a 5-second timeout on the
    real TartuNLP API. Classes named `TestAgainstTheLive…` keep the network and
    skip when the service is down. Localhost stays open for the test server.
    """
    if "Live" in (request.cls.__name__ if request.cls else ""):
        return
    import urllib.error
    import urllib.request
    from urllib.parse import urlsplit

    real = urllib.request.urlopen

    def guarded(url, *args, **kwargs):
        target = url.full_url if isinstance(url, urllib.request.Request) else url
        if urlsplit(str(target)).hostname in ("127.0.0.1", "localhost", "::1"):
            return real(url, *args, **kwargs)
        raise urllib.error.URLError(f"network blocked in tests: {target}")

    monkeypatch.setattr(urllib.request, "urlopen", guarded)


@pytest.fixture(autouse=True)
def _no_real_keys(monkeypatch):
    """No test sees a key from the developer's `.env` (`eesti/__init__.py` loads it on
    import); a test that needs a key sets one.
    """
    from eesti.env import KNOWN_KEYS

    for name in KNOWN_KEYS:
        monkeypatch.delenv(name, raising=False)
    # Local engines the developer's `.env` may point at: a test that wants one
    # sets it, so the owner's Voxtral install never reorders the chain under test.
    for name in ("VOXTRAL_RT_MODEL", "VOXTRAL_MODEL_PATH", "WHISPER_CPP_MODEL",
                 "ASR_REFERENCE_MODEL"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _redirect_data(monkeypatch, tmp_path, fixture_data):
    """Point every database at a fixture or a scratch file, for every test (autouse):
    the word list, corpus, form index, and the four learner databases.
    """
    from eesti import config, lookup

    monkeypatch.setattr(config, "DB_PATH", fixture_data["words"])
    monkeypatch.setattr(config, "CONTENT_DB", fixture_data["content"])
    monkeypatch.setattr(config, "CACHE", fixture_data["cache"])
    monkeypatch.setattr(lookup, "EDGE_DB", fixture_data["edge"])

    # Writable, per-test learner databases; every helper reads them from `config`.
    scratch = tmp_path / "live"
    scratch.mkdir(exist_ok=True)

    for name in ("PROGRESS_DB", "REVIEW_DB", "VOCAB_DB", "NOTION_DB", "EVENTS_DB"):
        target = str(scratch / f"{name.split('_')[0].lower()}.db")
        monkeypatch.setattr(config, name, target)

    # The downloaded exam material: empty unless a test puts a file there, so a
    # test never serves the learner's own copy of HARNO's PDFs.
    exam_dir = tmp_path / "exam"
    exam_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(config, "EXAM_DIR", str(exam_dir))

    # Unbind the breaker, which importing the app binds to the real `progress.db`;
    # tests that exercise it bind their own store.
    from eesti.providers import breaker

    breaker.bind(None)
    breaker.reset()

    lookup._open.cache_clear()
    yield
    lookup._open.cache_clear()


@pytest.fixture(scope="session")
def page() -> str:
    """The single-page app's source, for tests that check page↔API contracts."""

    return markup_and_script()


@pytest.fixture
def client():
    """A TestClient over the real app, on the redirected fixture databases."""
    from fastapi.testclient import TestClient

    from eesti.app import app

    return TestClient(app)


# --------------------------------------------------------------------------
# Browser journeys: opt-in, and two pairings unless asked for all four
# --------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption("--browser", action="store_true",
                     help="also run the browser journeys (tests/test_e2e_journeys.py): "
                          "Chromium at desktop size and WebKit at phone size")
    parser.addoption("--all-browsers", action="store_true",
                     help="the browser journeys in every engine x viewport pairing")


#: The pairings the owner actually uses: a desktop browser, and the installed PWA
#: on an iPhone, which is WebKit. Chromium stands in for WebKit where it is absent.
DEFAULT_PAIRS = {("chromium", "desktop"), ("webkit", "phone")}


def pytest_collection_modifyitems(config, items):
    everything = config.getoption("--all-browsers")
    wanted = everything or config.getoption("--browser")
    webkit = "webkit" in installed_engines()
    pairs = DEFAULT_PAIRS if webkit else {("chromium", "desktop"), ("chromium", "phone")}
    keep, drop = [], []
    for item in items:
        if "test_e2e_journeys.py" not in item.nodeid:
            keep.append(item)
            continue
        if not wanted:
            drop.append(item)
            continue
        params = getattr(getattr(item, "callspec", None), "params", {})
        pair = (params.get("_pw"), params.get("page"))
        if everything or None in pair or pair in pairs:
            keep.append(item)
        else:
            drop.append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep
