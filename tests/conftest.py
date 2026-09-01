"""Fixture databases, so no test depends on the developer's own build.

This exists because of a failure that has now happened twice: a test passes
locally because `data/eesti.db` is sitting there from a real `cli build`, and
fails in CI where it is not. The second time it took out 21 tests at once.

The cause was structural rather than careless. `config.DB_PATH` was read at
**import** time, so the database location could not be redirected once the
module was loaded — a test had no way to point the code somewhere else even if
it wanted to. `wordlist.connect` and `lookup._db` now resolve their paths when
called, and this file redirects all three databases at every test.

The fixture data is small and real: genuine Estonian words with their genuine
forms, so a test that says `läksin` is the past of `minema` is checking Vabamorf
rather than checking a mock. What it is not is *complete* — 25 words instead of
160 316 — which keeps the suite fast and means a test that needs breadth has to
say so.
"""

from __future__ import annotations

import sqlite3

import pytest

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
    """Every themed lemma, so theme tests measure the themes and not the fixture.

    Deliberately *not* how the "are these real Estonian words?" check is run —
    inserting them here would make that check circular. That one uses the real
    160 316-word lexicon and skips when it is not built.
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
    conn.executemany("INSERT OR REPLACE INTO words VALUES (?,?,?,?)", WORDS)
    # Inserted second so a word named in WORDS keeps its declared level.
    conn.executemany(
        "INSERT OR IGNORE INTO words VALUES (?,?,?,?)", _theme_words()
    )
    # Rections live in the word database and are fetched by a deliberate `cli
    # rections` run, never during a lesson. Seeding two here means the generator
    # is exercised offline — CI proved why that matters by getting a 403 from
    # EKI when a test reached for the live page.
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
    """A content database built by the app's own opener, not by hand.

    This used to write one `CREATE TABLE items` of its own. That is a second
    copy of a schema `eesti/sources.py` already owns, and it had drifted:
    `sources` was missing entirely, so anything reading the library through
    `library.sections` — the `library` and `status` commands, `/api/library` —
    hit "no such table: sources" against a fixture that looked complete.

    Using the real opener means the fixture cannot drift from the schema again,
    and a test that passes here is testing the shape production actually has.
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
    """The actual 160 316-word Ekilex build, or a skip.

    A handful of tests check curated content *against the lexicon* — "is
    `kingad` a word?" — and a fixture cannot answer that about itself. They opt
    out of the redirect and skip loudly where the build is absent, which is what
    CI sees.
    """
    import sqlite3 as _sqlite3
    from pathlib import Path

    real = Path("data/eesti.db")
    if not real.exists():
        pytest.skip("needs the full wordlist — run `cli fetch-data && cli build`")
    conn = _sqlite3.connect(f"file:{real}?mode=ro", uri=True)
    conn.row_factory = _sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


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
def _redirect_data(monkeypatch, tmp_path, fixture_data):
    """Point every database at a fixture or a scratch file, for every test.

    Autouse rather than opt-in: the failure mode is a test that *accidentally*
    reads real data and passes, which no one notices until CI. Making the safe
    thing automatic is the only version of this that works.

    It said "every database" and redirected three. The learner's own four --
    progress, review, vocabulary, queued corrections -- were left pointing at
    `data/`, so running the suite on a machine where somebody actually studies
    wrote into their record of what they had practised. Reading the
    developer's data makes a test lie; writing to it loses their work.
    """
    from eesti import config, lookup

    monkeypatch.setattr(config, "DB_PATH", fixture_data["words"])
    monkeypatch.setattr(config, "CONTENT_DB", fixture_data["content"])
    monkeypatch.setattr(config, "CACHE", fixture_data["cache"])
    monkeypatch.setattr(lookup, "EDGE_DB", fixture_data["edge"])

    # Writable, per-test, and never the real ones. `config` is the one place
    # these are read from -- every helper in `eesti/api/deps.py` resolves them
    # when it opens the file. `app` is redirected too because it re-exports the
    # four names and a couple of tests read them back off it; nothing in the
    # application reads that copy.
    scratch = tmp_path / "live"
    scratch.mkdir(exist_ok=True)
    from eesti import app as app_module

    for name in ("PROGRESS_DB", "REVIEW_DB", "VOCAB_DB", "NOTION_DB"):
        target = str(scratch / f"{name.split('_')[0].lower()}.db")
        monkeypatch.setattr(config, name, target)
        monkeypatch.setattr(app_module, name, target, raising=False)

    # `app.py` calls `_bind_breaker()` at *import* time, so the circuit breaker
    # holds a connection to the real `data/progress.db` from the first moment
    # anything imports the app -- before any redirect can apply, and for the
    # rest of the session, because it lives in a module global. Every
    # `breaker.reset()` in the suite then wrote to the learner's own database.
    # Drop it; the tests that exercise the breaker bind their own store.
    from eesti.providers import breaker

    breaker.bind(None)
    breaker.reset()

    lookup._db.cache_clear()
    yield
    lookup._db.cache_clear()


@pytest.fixture(scope="session")
def page() -> str:
    """The single-page app's source, for tests that check page↔API contracts."""
    from pathlib import Path

    return (Path(__file__).resolve().parents[1] / "eesti" / "web" / "index.html"
            ).read_text(encoding="utf-8")


@pytest.fixture
def client():
    """A TestClient over the real app, on the redirected fixture databases."""
    from fastapi.testclient import TestClient

    from eesti.app import app

    return TestClient(app)
