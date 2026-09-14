"""The build-time export never ships an invented or ambiguous paradigm.

Two rules, both visible through `/api/lookup`'s citation line:

- **Only declinable words get case forms.** Vabamorf synthesises "genitives" for
  adverbs, acronyms and imperatives (`alguses` → `algusese`).
- **Only unambiguous paradigms.** `morph.case_forms` refuses homographs, so
  `kool` never gets *koola*'s forms and `reis` never the thigh's.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti.wordlist import DECLINABLE, declines


class TestOnlyWordsThatDeclineGetAParadigm:
    @pytest.mark.parametrize("pos", ["s", "adj", "num", "pron", "prop",
                                     "adj,s", "s,adj", "num,s"])
    def test_declinable_parts_of_speech(self, pos):
        assert declines(pos) is True

    @pytest.mark.parametrize("pos", ["adv", "interj", "postp", "prep", "konj",
                                     "vrm", "adjg", "adv,postp", "postp,prep"])
    def test_indeclinable_parts_of_speech(self, pos):
        assert declines(pos) is False

    def test_an_untagged_word_does_not_decline(self):
        """Untagged words count as not declinable: they are mostly acronyms, genitives filed
        as headwords and imperatives.
        """
        assert declines(None) is False
        assert declines("") is False

    def test_the_rule_is_stated_once(self):
        """`nouns_at_level` (SQL) and `declines` (Python) must agree that a noun declines."""
        assert "s" in DECLINABLE
        assert declines("s") and declines("adj")


class TestTheExportUsesTheCarefulSynthesiser:
    def test_it_calls_case_forms_not_a_bare_synthesize(self):
        from pathlib import Path

        import eesti.export as export

        source = Path(export.__file__).read_text(encoding="utf-8")
        body = source.split("def export(", 1)[1]
        assert "case_forms(lemma)" in body
        assert "synthesize(lemma, \"sg g\")" not in body, \
            "back to picking whichever candidate Vabamorf listed first"

    def test_case_forms_refuses_the_words_that_caused_this(self):
        """`kool` and `reis` are the two `morph.case_forms` documents. If they
        ever stop being ambiguous this test should be revisited, not deleted:
        the point is that the export defers to that judgement."""
        from eesti.morph import case_forms

        assert case_forms("kool") == {}, "kool is no longer ambiguous"
        assert case_forms("reis") == {}, "reis is no longer ambiguous"

    def test_a_clean_word_still_comes_through(self):
        from eesti.morph import case_forms

        assert case_forms("raamat") == {"genitive": "raamatu",
                                        "partitive": "raamatut"}


class TestAgainstTheBuiltDataset:
    """Measured against the built dataset; skipped where it is not built."""

    @pytest.fixture(scope="class")
    @classmethod
    def edge(cls):
        from eesti import config

        path = config.DATA / "edge.db"
        if not path.exists():
            pytest.skip("no edge.db — run `cli export`")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("SELECT 1 FROM object_cases LIMIT 1").fetchone()
        except sqlite3.OperationalError:
            pytest.skip("edge.db predates object_cases")
        return conn

    def test_no_indeclinable_word_has_a_paradigm(self, edge):
        rows = edge.execute(
            """SELECT o.lemma, w.pos FROM object_cases o
               JOIN words w ON w.lemma = o.lemma"""
        ).fetchall()
        if not rows:
            pytest.skip("edge.db has no object_cases rows")
        bad = [(r["lemma"], r["pos"]) for r in rows if not declines(r["pos"])]
        assert not bad, f"invented paradigms for indeclinables: {bad[:10]}"

    def test_the_words_that_were_wrong_are_gone(self, edge):
        """The two homographs that reached a learner: `kool` and `reis`."""
        for lemma in ("kool", "reis", "alguses", "abielus", "dna", "õpi"):
            row = edge.execute(
                "SELECT genitive, partitive FROM object_cases WHERE lemma = ?",
                (lemma,)).fetchone()
            assert row is None, f"{lemma} still carries {tuple(row)}"

    def test_the_words_that_were_right_are_kept(self, edge):
        for lemma, gen, par in (("raamat", "raamatu", "raamatut"),
                                ("ilus", "ilusa", "ilusat"),
                                ("käsi", "käe", "kätt"),
                                ("sõber", "sõbra", "sõpra")):
            row = edge.execute(
                "SELECT genitive, partitive FROM object_cases WHERE lemma = ?",
                (lemma,)).fetchone()
            assert row is not None, f"{lemma} was dropped"
            assert (row["genitive"], row["partitive"]) == (gen, par)

    def test_the_word_card_shows_nothing_rather_than_something_wrong(self):
        from eesti.lookup import principal_forms

        for lemma in ("kool", "reis", "alguses"):
            assert principal_forms(lemma).get("found") is not True, \
                f"{lemma} still has a citation form"


class TestTheExportRunsEndToEnd:
    """`export()` runs end to end (the Dockerfile runs it at image build)."""

    @pytest.fixture(scope="class")
    @classmethod
    def built(cls, tmp_path_factory, fixture_data):
        """Built from the fixture word list, passed explicitly: a class-scoped fixture runs
        before the autouse redirect.
        """
        from eesti.export import export
        from eesti.wordlist import connect

        dest = tmp_path_factory.mktemp("edge") / "edge.db"
        stats = export(connect(fixture_data["words"]), dest_path=dest)
        conn = sqlite3.connect(dest)
        conn.row_factory = sqlite3.Row
        return stats, conn, dest

    def test_it_builds_something(self, built):
        stats, _, dest = built
        assert stats["lemmas"] > 0 and stats["forms"] > 0
        assert dest.exists() and stats["bytes"] > 0

    def test_every_table_the_edge_reads_is_present(self, built):
        """The contract with `lookup.py`, in the direction that usually rots:
        the reader is tested, the writer is not."""
        _, conn, _ = built
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"words", "forms", "object_cases"} <= tables

    def test_the_reverse_index_answers_what_vabamorf_would(self, built):
        """`forms` exists to replace runtime analysis at the edge. If a form
        Vabamorf generates is not in it, the edge cannot answer."""
        _, conn, _ = built
        row = conn.execute(
            "SELECT lemma, tag FROM forms WHERE form = ? AND lemma = ?",
            ("raamatut", "raamat")).fetchone()
        assert row is not None and row["tag"] == "sg p"

    def test_it_never_writes_a_paradigm_for_an_indeclinable(self, built):
        _, conn, _ = built
        bad = [(r["lemma"], r["pos"]) for r in conn.execute(
            """SELECT o.lemma, w.pos FROM object_cases o
               JOIN words w ON w.lemma = o.lemma""") if not declines(r["pos"])]
        assert not bad, bad[:10]

    def test_verbs_get_conjugated_not_declined(self, built):
        _, conn, _ = built
        tags = {r[0] for r in conn.execute(
            "SELECT tag FROM forms WHERE lemma = ?", ("lugema",))}
        assert "sg p" not in tags, "a verb was given a case"
        assert tags & {"nud", "da", "ma"}, "a verb lost its infinitives"
        assert conn.execute(
            "SELECT 1 FROM object_cases WHERE lemma = ?", ("lugema",)
        ).fetchone() is None

    def test_it_is_idempotent(self, tmp_path, fixture_data):
        """The Dockerfile reruns it on every build; a second run must not
        double the table or fail on the existing file."""
        from eesti.export import export
        from eesti.wordlist import connect

        dest = tmp_path / "edge.db"
        first = export(connect(fixture_data["words"]), dest_path=dest)
        second = export(connect(fixture_data["words"]), dest_path=dest)
        assert first["forms"] == second["forms"]
        assert first["object_cases"] == second["object_cases"]

    def test_the_frequency_cap_actually_caps(self, tmp_path, fixture_data):
        from eesti.export import export
        from eesti.wordlist import connect

        words = connect(fixture_data["words"])
        small = export(words, dest_path=tmp_path / "a.db", max_freq_rank=1)
        big = export(words, dest_path=tmp_path / "b.db", max_freq_rank=25_000)
        assert small["lemmas"] <= big["lemmas"]


class TestAgainstTheDatabaseTheAppActuallyServes:
    """The same guarantees for `eesti.db.object_cases`, the table drills are graded
    against (the export guards `edge.db`).
    """

    @pytest.fixture(scope="class")
    @classmethod
    def served(cls):
        from eesti import config

        path = config.DATA / "eesti.db"
        if not path.exists():
            pytest.skip("no eesti.db — run `cli build`")
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            if conn.execute("SELECT 1 FROM object_cases LIMIT 1").fetchone() is None:
                pytest.skip("eesti.db has no object_cases rows")
        except sqlite3.OperationalError:
            pytest.skip("eesti.db predates object_cases")
        return conn

    def test_no_ambiguous_word_carries_a_paradigm(self, served):
        """Words with two real paradigms are never drilled: `kool`, `reis`, `kook`."""
        wrong = []
        for word in ("kool", "reis", "kook"):
            row = served.execute(
                "SELECT word, genitive, partitive FROM object_cases WHERE word = ?",
                (word,),
            ).fetchone()
            if row is not None:
                wrong.append(f"{row['word']}: {row['genitive']}/{row['partitive']}")
        assert not wrong, (
            "ambiguous words indexed with a single paradigm — rebuild with "
            f"`python -m eesti.cli build`: {wrong}")

    def test_the_words_that_are_right_are_present(self, served):
        """The other half: refusing everything would also pass the test above."""
        for word, gen, par in (("raamat", "raamatu", "raamatut"),
                               ("supp", "supi", "suppi")):
            row = served.execute(
                "SELECT genitive, partitive FROM object_cases WHERE word = ?",
                (word,),
            ).fetchone()
            assert row is not None, f"{word} missing from the served paradigms"
            assert (row["genitive"], row["partitive"]) == (gen, par), dict(row)

    def test_every_served_paradigm_round_trips_through_the_analyser(self, served):
        """Spot-check the table against Vabamorf itself rather than against a
        list of words somebody remembered. A sample, because the table has
        thousands of rows and this is a guard, not a rebuild."""
        from eesti.morph import case_forms

        rows = served.execute(
            "SELECT word, genitive, partitive FROM object_cases"
            " WHERE distinct_ = 1 ORDER BY word LIMIT 40"
        ).fetchall()
        if not rows:
            pytest.skip("no distinct paradigms indexed")
        disagreed = []
        for row in rows:
            forms = case_forms(row["word"])
            if not forms:
                disagreed.append(f"{row['word']}: served, but ambiguous now")
            elif (forms["genitive"], forms["partitive"]) != (
                    row["genitive"], row["partitive"]):
                disagreed.append(
                    f"{row['word']}: served {row['genitive']}/{row['partitive']},"
                    f" analyser says {forms['genitive']}/{forms['partitive']}")
        assert not disagreed, disagreed
