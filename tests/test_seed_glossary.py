"""Translations for the words drills actually use.

Measured across every generator on a fresh deployment: **0 %** of drill lemmas
had a Russian translation. The gloss store fills one word at a time on demand
from Sõnaveeb, so `etendus` stayed untranslated until somebody looked it up —
and a B1 object-case drill on a word the learner cannot translate teaches
morphology on a token. `CLAUDE.md` names that failure; nothing had closed it.

`data/seed_glossary.tsv` ships with the app. It is **written, not scraped**:
Sõnaveeb asks not to be batched, `sonapi` has no bulk helper by design, and
seeding from it was never an option.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from eesti import gloss

SEED = Path(__file__).resolve().parents[1] / "data" / "seed_glossary.tsv"


@pytest.fixture
def store():
    return gloss.connect(tempfile.mktemp(suffix=".db"))


class TestTheFileItself:
    def test_it_ships_with_the_app(self):
        assert SEED.exists(), "the glossary must be in the repository, not generated"

    @staticmethod
    def _rows() -> list[tuple[str, str]]:
        out = []
        for line in SEED.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            lemma, _, russian = line.partition("\t")
            out.append((lemma.strip(), russian.strip()))
        return out

    def test_every_line_is_a_lemma_and_a_translation(self):
        for lemma, russian in self._rows():
            assert lemma and russian, f"malformed entry: {lemma!r} -> {russian!r}"

    def test_no_lemma_appears_twice(self):
        lemmas = [l for l, _ in self._rows()]
        dupes = {l for l in lemmas if lemmas.count(l) > 1}
        assert not dupes, f"duplicate entries: {sorted(dupes)}"

    def test_the_translations_are_russian(self):
        """An Estonian word glossed in Estonian teaches nothing, and the rule
        this project states first is that explanation is in Russian."""
        for lemma, russian in self._rows():
            assert any("Ѐ" <= ch <= "ӿ" for ch in russian), (
                f"{lemma!r} is glossed {russian!r}, which carries no Cyrillic")

    def test_it_is_not_git_ignored(self):
        """It is our own writing, so it belongs in the repository — unlike the
        runtime databases beside it."""
        import subprocess

        r = subprocess.run(["git", "check-ignore", str(SEED)],
                           capture_output=True, cwd=SEED.parents[1])
        assert r.returncode != 0, "the glossary is git-ignored and would not ship"


class TestLoading:
    def test_opening_the_store_loads_it(self, store):
        """A loader nothing calls is this project's oldest recurring bug, so
        seeding is wired into the one opener rather than left to a caller."""
        n = store.execute(
            "SELECT COUNT(*) FROM word_gloss WHERE fetched = 'seed'").fetchone()[0]
        assert n > 200

    def test_loading_twice_changes_nothing(self, store):
        before = store.execute("SELECT COUNT(*) FROM word_gloss").fetchone()[0]
        gloss.seed(store)
        assert store.execute(
            "SELECT COUNT(*) FROM word_gloss").fetchone()[0] == before

    def test_a_real_answer_is_never_overwritten(self, store):
        """A Sõnaveeb answer carries senses, rection and muuttüüp; this file
        carries one line. The richer one wins."""
        store.execute(
            "INSERT OR REPLACE INTO word_gloss (lemma, russian, fetched)"
            " VALUES ('etendus', 'настоящий ответ', '2026-08-21')")
        store.commit()
        gloss.seed(store)
        row = store.execute(
            "SELECT russian, fetched FROM word_gloss WHERE lemma='etendus'"
        ).fetchone()
        assert row[0] == "настоящий ответ" and row[1] == "2026-08-21"

    def test_the_source_stays_distinguishable(self, store):
        """So a later session asking where a translation came from gets an
        answer rather than assuming Sõnaveeb said it."""
        row = store.execute(
            "SELECT fetched FROM word_gloss WHERE lemma='raamat'").fetchone()
        assert row and row[0] == "seed"

    def test_a_missing_file_does_not_break_the_app(self, tmp_path):
        conn = sqlite3.connect(tmp_path / "v.db")
        conn.executescript(gloss.SCHEMA)
        assert gloss.seed(conn, tmp_path / "nope.tsv") == 0

    def test_seeding_never_reaches_the_network(self, store, monkeypatch):
        """The whole point is that it works on a deployment with no key and no
        outbound call, and without asking Sõnaveeb for 294 words."""
        import urllib.request

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (
            _ for _ in ()).throw(AssertionError("seeding went to the network")))
        gloss.seed(store)


class TestItCoversWhatDrillsActuallyAsk:
    def test_most_drill_words_are_translated(self, store):
        """The measurement that motivated the file: 0 % before. This asserts a
        floor well under what it achieves, so ordinary drift in the generators
        does not fail the build — the point is that it is not near zero."""
        from eesti.curriculum import TOPICS
        from eesti.practice import items_for

        total = found = 0
        for topic in TOPICS:
            if not topic.generator:
                continue
            try:
                items = items_for(topic.id, count=8, seed=2)
            except Exception:  # noqa: BLE001 - generators needing a corpus
                continue
            lemmas = [i.lemma for i in items if getattr(i, "lemma", "")]
            if not lemmas:
                continue
            marks = ",".join("?" * len(lemmas))
            hits = {r[0] for r in store.execute(
                f"SELECT lemma FROM word_gloss WHERE lemma IN ({marks})"
                " AND russian <> ''", lemmas)}
            total += len(lemmas)
            found += len(hits)
        assert total, "no drill produced a lemma to check"
        assert found / total > 0.5, f"only {found}/{total} drill words translated"
