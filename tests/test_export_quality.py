"""The build-time export, and the two paradigms it was inventing.

`export.py` sat at 22 % coverage. Reading it found the same defect twice over,
and both reached the learner through `/api/lookup`'s citation line — the one
that prints `raamat, raamatu, raamatut` in the format a textbook uses.

**It asked for a genitive of words that have none.** Vabamorf refuses to
decline a verb, and that quietly implied it would refuse for anything else
without a paradigm. It does not: asked for the genitive of the adverb
`alguses` it answers `algusese`, of `dna` it answers `dnad`, of the imperative
`õpi` a full declension. 319 of 7 256 drillable entries were invented that
way. `wordlist.nouns_at_level` already gated the drill path on part of speech;
this path never did.

**And it took whichever candidate came first.** `next(iter(synthesize(...)))`
shipped `kool, koola, koola` — the declension of *koola*, cola — for the word
meaning "school", and `reis, reie, reit`, which is *reis* the thigh rather
than *reis* the journey. `morph.case_forms` exists precisely to stop that, and
names both words in its docstring. This module reimplemented the naive version
it replaced.
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
        """This inverts the CEFR rule elsewhere in the project, deliberately.

        There an absent tag meant "nobody rated this" and dropping it lost real
        words. Here an absent tag correlates with the entry not being a lemma:
        the untagged set is acronyms (`dna`, `nato`, `who`), genitives filed as
        headwords (`kahe`, `linna`, `panga`) and imperatives (`küsi`, `õpi`).
        """
        assert declines(None) is False
        assert declines("") is False

    def test_the_rule_is_stated_once(self):
        """`nouns_at_level` gates the drill path in SQL; this gates the export
        in Python. They answer different questions — "is a noun" against "can
        take a case ending" — so both must exist, and both must agree that a
        noun declines."""
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
    """The measurement that found this, as an assertion. Skipped where the
    dataset has not been built — it is 47 MB and git-ignored."""

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
        """Named individually because each was printed to the learner in
        citation format: `kool, koola, koola` and `reis, reie, reit`."""
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
    """The 40 lines nothing had executed.

    The tests above check the *rule*; this checks the build. `export()` is what
    the Dockerfile runs at image build time — `RUN python -m eesti.cli export`
    — so if it raises, the image does not exist. It had never been called by a
    test.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def built(cls, tmp_path_factory, fixture_data):
        """Built from the fixture word list, named explicitly.

        The first version called `connect()` with no argument and let it read
        `config.DB_PATH`. A class-scoped fixture is set up *before* the
        function-scoped autouse redirect in `conftest`, so it got the real
        path -- and `sqlite3.connect` on a path with no file creates one. On a
        machine with a built word list the export quietly used 160 316 real
        lemmas; on CI it created an empty `data/eesti.db`, exported nothing,
        and left the phantom file behind to break two unrelated theme tests.

        Pass the connection; never reach for a module-level path. Same lesson
        as the readiness verdict reading the developer's real Notion queue.
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
    """`edge.db` is the export; `eesti.db` is what the running app reads.

    The class above guards the dataset shipped to Cloudflare. The FastAPI app
    generates its drills from `eesti.db.object_cases` — a different table,
    written by `wordlist.index_object_cases` — and **nothing guarded that one**.
    Found during the UAT pass, from the other end: a drill offered
    `kook · A1` and marked the answer `koogu`, pairing the genitive of *kook*
    the hooked pole with the partitive of *kook* the cake. `case_forms` refuses
    ambiguous words precisely so this cannot happen, and the local database
    predated that fix.

    It does not ship — the Dockerfile rebuilds the dataset from scratch — but
    that is a property of the build, not a test, and it is exactly the kind of
    thing that stops being true quietly. So: same questions, asked of the table
    the learner's answers are actually graded against.
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
        """A word with two real paradigms has no single right answer, so it
        must not be drilled at all. `kool` (school / cola), `reis` (journey /
        thigh) and `kook` (cake / hooked pole) are the three that have actually
        reached a learner."""
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
