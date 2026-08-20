"""Importing the word list, and the cache that outlived it.

`wordlist.py` sat at 49 % coverage. The untested half is the build path — the
TSV importer and the Vabamorf cache — which is the same shape as `export.py`,
where the two worst defects of this session were hiding.

`build()`'s docstring said "Idempotent — safe to re-run after a refresh". That
was true of `words` and false of everything derived from it. It replaced the
word list and left `object_cases` alone, and `index_object_cases` skips any
word it already has — so a refresh could neither drop a cached paradigm for a
word upstream had removed, nor recompute one whose part of speech had been
corrected. The cache was write-once for the life of the database.
"""

from __future__ import annotations

import csv

import pytest

from eesti import wordlist

FIELDS = ["word", "freq_rank", "proficiency", "pos"]


@pytest.fixture
def source(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()

    def write(rows):
        with (raw / "est_words_160k.tsv").open("w", encoding="utf-8", newline="") as fh:
            out = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t")
            out.writeheader()
            for row in rows:
                out.writerow(row)
        return raw
    return write


@pytest.fixture
def db(tmp_path):
    return wordlist.connect(tmp_path / "w.db")


def row(word, rank="100", level="A1", pos="s"):
    return {"word": word, "freq_rank": rank, "proficiency": level, "pos": pos}


class TestTheImporter:
    def test_it_reads_the_columns_it_says_it_does(self, db, source):
        wordlist.build(db, raw_dir=source([row("raamat", "200", "A1", "s")]))
        got = db.execute("SELECT * FROM words WHERE word='raamat'").fetchone()
        assert (got["freq_rank"], got["proficiency"], got["pos"]) == (200, "A1", "s")

    def test_a_missing_source_says_what_to_run(self, db, tmp_path):
        with pytest.raises(FileNotFoundError, match="fetch-data"):
            wordlist.build(db, raw_dir=tmp_path / "nothing")

    def test_a_blank_word_is_skipped(self, db, source):
        assert wordlist.build(db, raw_dir=source([row("raamat"), row("")])) == 1

    def test_a_non_numeric_rank_becomes_null_not_a_crash(self, db, source):
        wordlist.build(db, raw_dir=source([row("raamat", rank="n/a")]))
        assert db.execute(
            "SELECT freq_rank FROM words WHERE word='raamat'").fetchone()[0] is None

    def test_empty_fields_become_null(self, db, source):
        wordlist.build(db, raw_dir=source([row("raamat", level="", pos="")]))
        got = db.execute("SELECT * FROM words WHERE word='raamat'").fetchone()
        assert got["proficiency"] is None and got["pos"] is None

    def test_a_rebuild_replaces_rather_than_appends(self, db, source):
        wordlist.build(db, raw_dir=source([row("raamat"), row("ajaleht")]))
        wordlist.build(db, raw_dir=source([row("raamat")]))
        assert [r[0] for r in db.execute("SELECT word FROM words")] == ["raamat"]


class TestTheDerivedCacheCannotOutliveItsSource:
    def test_a_refresh_clears_it(self, db, source):
        wordlist.build(db, raw_dir=source([row("raamat"), row("ajaleht", "500", "A2")]))
        wordlist.index_object_cases(db)
        assert db.execute("SELECT COUNT(*) FROM object_cases").fetchone()[0] == 2

        wordlist.build(db, raw_dir=source([row("raamat")]))
        assert db.execute("SELECT COUNT(*) FROM object_cases").fetchone()[0] == 0

    def test_no_row_survives_for_a_word_that_is_gone(self, db, source):
        """The orphan this used to leave was invisible to drills — they join on
        `words` — but it accumulated, and it meant a corrected paradigm could
        never be recomputed."""
        wordlist.build(db, raw_dir=source([row("raamat"), row("ajaleht", "500", "A2")]))
        wordlist.index_object_cases(db)
        wordlist.build(db, raw_dir=source([row("raamat")]))
        orphans = db.execute(
            """SELECT COUNT(*) FROM object_cases o
               LEFT JOIN words w ON w.word = o.word WHERE w.word IS NULL"""
        ).fetchone()[0]
        assert orphans == 0

    def test_reindexing_after_a_refresh_recomputes(self, db, source):
        wordlist.build(db, raw_dir=source([row("raamat")]))
        wordlist.index_object_cases(db)
        wordlist.build(db, raw_dir=source([row("raamat")]))
        assert wordlist.index_object_cases(db)["indexed"] == 1

    def test_reindexing_without_a_refresh_is_still_cheap(self, db, source):
        """The within-run skip stays: `index_object_cases` twice in a row must
        not pay Vabamorf twice."""
        wordlist.build(db, raw_dir=source([row("raamat")]))
        wordlist.index_object_cases(db)
        assert wordlist.index_object_cases(db)["checked"] == 0


class TestTheCacheOnlyEverHoldsNouns:
    """`nouns_at_level` gates on part of speech in SQL, which is why the local
    cache never picked up the adverbs that reached the exported dataset."""

    def test_an_adverb_never_enters_the_cache(self, db, source):
        wordlist.build(db, raw_dir=source([
            row("raamat"), row("alguses", "300", "A2", "adv")]))
        wordlist.index_object_cases(db)
        cached = {r[0] for r in db.execute("SELECT word FROM object_cases")}
        assert cached == {"raamat"}, cached

    def test_a_word_that_is_both_noun_and_something_else_is_kept(self, db, source):
        wordlist.build(db, raw_dir=source([row("kuulmine", "400", "B1", "s,adj")]))
        wordlist.index_object_cases(db)
        assert db.execute("SELECT COUNT(*) FROM object_cases").fetchone()[0] == 1

    def test_the_two_gates_agree_that_a_noun_declines(self, db, source):
        """`nouns_at_level` gates the drill path in SQL and `declines` gates the
        export in Python. They answer different questions, so they must both
        exist — and they must not disagree about a noun."""
        wordlist.build(db, raw_dir=source([row("raamat")]))
        assert [w.word for w in wordlist.nouns_at_level(db)] == ["raamat"]
        assert wordlist.declines("s")
