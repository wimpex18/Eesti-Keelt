"""Numbers in the documentation, checked against the code that produces them.

Every count in `docs/` was written by hand from a measurement taken once. Four
of them were wrong on 2026-08-21 — 13 topics without a generator when there
were 11, 42 API routes when there were 49, 1 141 tests when there were 1 283,
21 of 36 topics with practice when it was 25 — and every one of them had been
true when written. That is the whole failure mode: **a true sentence goes stale
silently**, and a document nobody can trust is worse than no document, because
the next session plans against it.

This is the same remedy this project applies everywhere else. A claim that can
be derived is asserted against its source, so the build fails at the moment the
two disagree rather than the next time somebody reads carefully.

Deliberately narrow. It checks the counts that have actually drifted and are
unambiguous to parse; it does not try to verify prose, and a doc is free to
record a historical figure as long as it is marked as one — `curriculum-plan.md`
keeps "21 of 36 at the time of writing" beside the current number, which is a
record rather than a claim.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pagesrc import markup_and_script

ROOT = Path(__file__).resolve().parents[1]

#: Documents whose job is to state the current state. `CLAUDE.md` is not one of
#: them: it records habits, and a habit about a number that was wrong has to be
#: able to quote the wrong number. The first version of this check read the
#: sentence "13 topics without a generator when there were 11" as a claim that
#: there are 13, and failed on the very habit written to prevent it.
#:
#: `docs/lessons.md` is excluded for exactly that reason and no other: it is
#: where those habits now live, moved out of `CLAUDE.md` verbatim. Every number
#: in it is a record of what was measured when the bug was found, which is the
#: point of the entry.
#:
#: `curriculum-plan.md` and `roadmap.md` are excluded for the same reason from
#: the other direction: they narrate what a build step achieved, which is a
#: record of a past state by construction.
#:
#: `docs/changelog.md` is excluded on the same ground, and its exclusion is the
#: cleanest of them: since the 2026-09-12 split it holds *only* records of past
#: states, so there is no live claim in it to miss. That is the half of
#: `status.md` the `HISTORICAL` regex below was guessing at from wording; the
#: guess now has 1 195 fewer lines to be wrong about.
LIVE = ("README.md", "docs/status.md", "docs/app-structure.md",
        "docs/architecture.md", "docs/qa-status.md")
DOCS = [ROOT / name for name in LIVE if (ROOT / name).exists()]

#: A claim that says "at the time of writing" is a record of a past state, not
#: an assertion about now, and is skipped. Anything else is live.
HISTORICAL = re.compile(r"at the time of writing|went \*\*\d+ →")


def _claims(pattern: str) -> list[tuple[Path, int, str, str]]:
    """(file, line, matched number, the line) for each live claim."""
    out = []
    for doc in DOCS:
        for n, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            if HISTORICAL.search(line):
                continue
            m = re.search(pattern, line)
            if m:
                out.append((doc, n, m.group(1), line.strip()))
    return out


def _where(found) -> str:
    return "; ".join(f"{d.relative_to(ROOT)}:{n} says {v}" for d, n, v, _ in found)


class TestCurriculumCounts:
    def test_topics_with_practice(self):
        from eesti.curriculum import TOPICS

        actual = sum(1 for t in TOPICS if t.generator)
        found = _claims(r"(\d+) of 36 (?:curriculum |grammar )?topics")
        assert found, "no document states how many topics have practice"
        for doc, line, value, text in found:
            assert int(value) == actual, (
                f"{doc.relative_to(ROOT)}:{line} says {value} of 36; "
                f"the code has {actual}.\n  {text}")

    def test_topics_without_a_generator(self):
        from eesti.curriculum import TOPICS

        actual = sum(1 for t in TOPICS if not t.generator)
        # `\w+ ` for an adverb: README says "10 curriculum topics **still**
        # have no generator", which the tighter pattern skipped -- a live claim
        # in a covered document, unchecked because of one word.
        found = _claims(r"(\d+) curriculum topics (?:\w+ )?have no generator")
        for doc, line, value, text in found:
            assert int(value) == actual, (
                f"{doc.relative_to(ROOT)}:{line} says {value}; "
                f"the code has {actual}.\n  {text}")

    def test_topics_that_link_to_the_handbook(self):
        """`status.md` said 22 of 23 for three weeks while drills landed; it is
        25 of 26. The shape of the claim stayed right — one topic has no link,
        and it is still `kusisonad` — which is exactly why nobody noticed the
        counts underneath it moving."""
        from eesti.curriculum import TOPICS
        from eesti.grammar import describe

        def linked(topic) -> bool:
            # Same fallback as `render._topic_reference`: by error tag where
            # there is one, by topic id otherwise. Counting only the tagged
            # ones gives 7 and is the wrong measure of the same words.
            if topic.tag and describe(topic.tag).get("known"):
                return True
            return bool(describe(topic.id).get("known"))

        drillable = [t for t in TOPICS if t.generator]
        have = [t for t in drillable if linked(t)]
        # Both halves. Capturing only the numerator left "25 of 26" green if
        # `drillable` grew to 27 -- the claim would then be quietly wrong in
        # the direction that matters, a topic shipped with no rule to read.
        found = _claims(r"(\d+ of \d+) drillable topics link to the handbook")
        assert found, "no document states the handbook coverage"
        for doc, line, value, text in found:
            assert value == f"{len(have)} of {len(drillable)}", (
                f"{doc.relative_to(ROOT)}:{line} says {value}; "
                f"the code has {len(have)} of {len(drillable)}.\n  {text}")

    def test_the_one_topic_with_no_handbook_link_is_named(self):
        """A wrong link is worse than none, so the exception is deliberate and
        the document names it. If a second one ever appears, the sentence stops
        being true in a way no count would show."""
        from eesti.curriculum import TOPICS
        from eesti.grammar import describe

        missing = [t.id for t in TOPICS if t.generator
                   and not (t.tag and describe(t.tag).get("known"))
                   and not describe(t.id).get("known")]
        assert missing == ["kusisonad"], (
            f"status.md names `kusisonad` as the only topic with no handbook "
            f"link; the code has {missing}")

    def test_the_shipped_glossary_count(self):
        """294 is a row count in a file, and a file people add rows to."""
        seed = ROOT / "data" / "seed_glossary.tsv"
        if not seed.exists():
            pytest.skip("seed glossary is not in this checkout")
        actual = sum(1 for line in seed.read_text(encoding="utf-8").splitlines()
                     if line.strip() and not line.startswith("#"))
        found = _claims(r"\*\*(\d+) Russian glosses ship")
        assert found, "no document states how many glosses ship"
        for doc, line, value, text in found:
            assert int(value) == actual, (
                f"{doc.relative_to(ROOT)}:{line} says {value}; "
                f"the file has {actual}.\n  {text}")

    def test_the_named_list_matches_the_derived_one(self):
        """`status.md` prints the eleven topic ids for reading. A snapshot is
        fine; a snapshot that has drifted is what sent a previous session
        looking for `eitus` in a list it had already left."""
        from eesti.curriculum import TOPICS

        actual = {t.id for t in TOPICS if not t.generator}
        text = (ROOT / "docs" / "status.md").read_text(encoding="utf-8")
        after = text[text.index("curriculum topics have no generator"):]
        # The ids live in a fenced block so this reads the list and not the
        # paragraph under it -- which legitimately names the two topics that
        # *left* the list, and had this check reporting them as stale entries.
        start = after.index("```")
        named = set(after[start + 3:after.index("```", start + 3)].split())
        assert named == actual, (
            f"status.md names {sorted(named)};\n"
            f"the code has  {sorted(actual)}")


class TestApiSurface:
    @staticmethod
    def _declared() -> int:
        """Route decorators across the API package.

        It read `app.py` alone while every handler was declared there. The
        routes live in `eesti/api/*.py` now, one module per thing the learner
        is doing, so the count is taken across the package -- a glob rather
        than a list of module names, or this check acquires the drift it
        exists to catch.
        """
        modules = sorted((ROOT / "eesti" / "api").glob("*.py"))
        assert modules, "no API modules found -- this check would measure zero"
        return sum(len(re.findall(r"@router\.(?:get|post)",
                                  m.read_text(encoding="utf-8")))
                   for m in modules)

    def test_the_count_is_not_zero(self):
        """Every assertion below compares against this number."""
        assert self._declared() > 40

    def test_the_api_endpoint_count(self):
        """The number the *guarantee* is about.

        `status.md` said "52 API routes, every one with a caller" and cited
        `test_route_inventory.py`. Two measures welded together: 52 is the
        `@router` decorator count, and the caller guarantee is over the 44
        `/api/*` paths that test actually walks. Both were right about their
        own measure and the sentence was right about neither.
        """
        from eesti import api
        from eesti.app import app

        actual = len([p for p in api.paths(app) if p.startswith("/api/")])
        found = _claims(r"(\d+) API endpoints")
        assert found, "no document states how many API endpoints there are"
        for doc, line, value, text in found:
            assert int(value) == actual, (
                f"{doc.relative_to(ROOT)}:{line} says {value}; "
                f"`api.paths()` has {actual}.\n  {text}")

    def test_route_count(self):
        actual = self._declared()
        for doc, line, value, text in _claims(r"(\d+) route handlers"):
            assert int(value) == actual, (
                f"{doc.relative_to(ROOT)}:{line} says {value} API routes; "
                f"app.py defines {actual}.\n  {text}")


class TestTheModeStructure:
    """`app-structure.md` drew a structure that was never built — a top-level
    `Raamatukogu`, `Kordamine` nested inside `Õppimine`, no speaking or writing
    tab. It was a plan being read as a map for long enough that a later session
    planned against it."""

    @staticmethod
    def _diagram_tabs() -> set[str]:
        text = (ROOT / "docs" / "app-structure.md").read_text(encoding="utf-8")
        block = text[text.index("## The structure, as built"):]
        start = block.index("```")
        block = block[start:block.index("```", start + 3)]
        # Lines of the form "├── Rada          ..." -- take the Estonian label.
        return {m.group(1) for m in
                re.finditer(r"[├└]── (\S+)", block)}

    @staticmethod
    def _page_tabs() -> set[str]:
        html = markup_and_script()
        return set(re.findall(r'data-tab="[a-z]+"[^>]*>.*?<span class="lbl">([^<]+)',
                              html, re.S))

    def test_the_diagram_lists_every_tab_the_page_has(self):
        missing = self._page_tabs() - self._diagram_tabs()
        assert not missing, (
            f"the app has tabs the structure diagram omits: {sorted(missing)}")

    def test_the_diagram_invents_no_tab(self):
        invented = self._diagram_tabs() - self._page_tabs()
        assert not invented, (
            f"the structure diagram names sections the app does not have: "
            f"{sorted(invented)}")


class TestEveryFileTheDocsPointAtExists:
    """A pointer to a file that is not there sends the reader nowhere.

    `roadmap.md` said "see `sources.md`" for why a monologue recorder trains
    the wrong thing. There has never been a `sources.md`; the argument is in
    `speaking.md`. Nothing catches that kind of rot — a stale *pointer* reads
    exactly like a live one, and only somebody following it finds out.

    Backticked filenames are the form this project uses for a reference, so
    that is what gets checked. Names that are deliberately not files live in
    `NOT_A_FILE` with a reason, the same posture `test_route_inventory` takes
    towards a route with no caller: an entry is a decision, not a snooze.
    """

    #: Cited in backticks, correctly, and not a path in this repository.
    NOT_A_FILE = {
        "Search/search_results.html": "a path on EVKK's server, in the note "
                                      "about what their search returns",
        "cli.py": "history: it was one module before the split, and the "
                  "lessons and status entries about it name what it was",
        "eesti/cli.py": "history, as above — the Was/Is table in status.md and "
                        "the docstring in test_cli_smoke.py both name the old "
                        "path deliberately",
        "stack-2026.md": "history: architecture.md records that it was merged "
                         "from that file, which is why the name appears",
        "grammar_et.json": "a dataset `cli fetch-bench` downloads into the "
                           "git-ignored data/raw/bench. CI passed only because "
                           "it fetches first -- and that fetch is allowed to "
                           "fail, which would have failed this doc check "
                           "for a Hugging Face outage",
    }

    @staticmethod
    def _citations() -> dict[str, set[str]]:
        import collections

        found = collections.defaultdict(set)
        pattern = re.compile(
            r"`([A-Za-z0-9_./-]+\.(?:md|py|js|css|html|sh|ts|yml|json|tsv))`")
        for path in sorted(ROOT.glob("*.md")) + sorted(ROOT.glob("docs/*.md")):
            for match in pattern.finditer(path.read_text(encoding="utf-8")):
                found[match.group(1)].add(path.relative_to(ROOT).as_posix())
        return found

    def test_there_are_citations_to_check(self):
        assert len(self._citations()) > 40

    def test_every_cited_file_exists(self):
        missing = {
            name: sorted(where)
            for name, where in self._citations().items()
            if name not in self.NOT_A_FILE
            and not (ROOT / name).exists()
            and not list(ROOT.glob(f"**/{name}"))
        }
        assert not missing, (
            f"the docs point at files that are not there: {missing}. Fix the "
            f"pointer, or add the name to NOT_A_FILE with the reason it is not "
            f"a path.")

    def test_the_exemptions_are_still_needed(self):
        """An exemption for a name nobody cites any more is a stale note that
        would silently excuse a future typo of the same name."""
        cited = set(self._citations())
        stale = sorted(set(self.NOT_A_FILE) - cited)
        assert not stale, f"NOT_A_FILE names nothing cites: {stale}"

    def test_every_exemption_says_why(self):
        for name, reason in self.NOT_A_FILE.items():
            assert len(reason) > 25, f"{name} is exempt without a reason"


class TestNothingIsDefinedForNobody:
    """The counterpart to "a measurement with no writer": a writer with no
    reader. Both are the same defect and this project has paid for it eight
    times; the sweep that produced this class found four, of which three were
    real and are gone.

    Read by **AST**, not by grepping words out of the file text. The first
    version did the latter and was three-quarters ornamental:

    * a name merely *mentioned in a comment* counted as read, which in a
      codebase written in essays is the common case rather than the corner one;
    * `ALLOWED` was inert -- naming a constant there put the word in this file,
      which raised its own occurrence count past the threshold, so the
      exemption could never be needed and its staleness could never be caught;
    * one global counter meant a name declared in two modules could never be
      flagged at all: 24 names covering 85 declarations were invisible.

    Counting identifier *loads* fixes all three at once. A string inside a set
    literal is not a load, so `ALLOWED` does its job; a word in a comment is not
    a load; and a name loaded nowhere is orphaned wherever it is declared.

    Deliberately constants only. Every *function* the sweep flagged was a
    FastAPI route handler, bound by its decorator and referenced by name
    nowhere, which is correct and must not be reported.
    """

    #: Kept on purpose, with the reason. `ARCHIVES` is a provenance record: the
    #: three ERR archive index pages, noted because the harvester deliberately
    #: does *not* fetch them (they render their episode lists in JavaScript) and
    #: a future session should not rediscover that by trying. Same category as
    #: the provenance-only rows in `sources.REGISTRY`.
    ALLOWED = {"ARCHIVES"}

    @staticmethod
    def _declarations(root):
        import ast

        out = []
        for path in sorted(root.rglob("*.py")):
            for node in ast.parse(path.read_text(encoding="utf-8")).body:
                targets = (node.targets if isinstance(node, ast.Assign)
                           else [node.target] if isinstance(node, ast.AnnAssign)
                           else [])
                for target in targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        out.append((target.id, path, node.lineno))
        return out

    @staticmethod
    def _loads(paths):
        """Who reads what, keyed by **(module, NAME)** rather than by name.

        One global tally was the counting bug: `TIMEOUT` is declared in two
        modules, one of them reads it, and a global count of "is TIMEOUT read
        anywhere" therefore clears an orphan on the strength of its twin.
        Planting an unused `TIMEOUT` proved it -- swept clean.

        A constant is read when something imports it from its module, reaches
        it as an attribute on that module, or -- inside the declaring module
        itself -- loads it as a bare name. Those are the three ways to reach
        one, so resolving each read to a module is enough to tell twins apart.

        Modules are keyed by basename, so two files of the same name (there
        are: `eesti/sources.py` and `eesti/api/sources.py`) share a key and the
        check falls back to today's leniency for those. Lenient in the same
        place as before, precise everywhere else.
        """
        import ast
        import collections

        read = collections.defaultdict(set)      # NAME -> {module, ...}
        for path in paths:
            here = path.stem
            tree = ast.parse(path.read_text(encoding="utf-8"))

            # `from eesti.api import state as state_module` -- without this the
            # alias is an unknown module and every constant reached through it
            # reads as unread. `STATE_DATABASES` was the false positive that
            # found this.
            alias_of = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for a in node.names:
                        if a.asname:
                            alias_of[a.asname] = a.name.rsplit(".", 1)[-1]
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        if a.asname:
                            alias_of[a.asname] = a.name.rsplit(".", 1)[-1]

            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    # A bare name can only see this file's own -- or one this
                    # file imported, which the ImportFrom branch records too.
                    read[node.id].add(here)
                elif isinstance(node, ast.Attribute):
                    owner = node.value
                    while isinstance(owner, ast.Attribute):
                        owner = owner.value
                    if isinstance(owner, ast.Name):
                        via = (node.value.attr
                               if isinstance(node.value, ast.Attribute)
                               else owner.id)
                        read[node.attr].add(alias_of.get(via, via))
                elif isinstance(node, ast.ImportFrom) and node.module:
                    owner = node.module.rsplit(".", 1)[-1]
                    for alias in node.names:
                        read[alias.name].add(owner)
        return read

    def _swept(self):
        root = ROOT / "eesti"
        return (self._declarations(root),
                self._loads(list(root.rglob("*.py"))
                            + list((ROOT / "tests").rglob("*.py"))))

    @staticmethod
    def _orphan(name, path, reads) -> bool:
        """Read from the module that declares it, or by nobody."""
        return path.stem not in reads.get(name, set())

    def test_no_module_constant_is_read_by_nothing(self):
        declared, loads = self._swept()
        orphans = sorted(
            f"{name} ({path.relative_to(ROOT)}:{line})"
            for name, path, line in declared
            if self._orphan(name, path, loads) and name not in self.ALLOWED)
        assert not orphans, (
            "declared and read by nothing -- delete it, or add it to ALLOWED "
            f"with the reason: {orphans}")

    def test_a_comment_does_not_count_as_a_read(self):
        """The weakness that made the first version ornamental, pinned.

        Every flaw it had was invisible from its own green result, so the
        mechanism gets its own test rather than being trusted.
        """
        import ast
        import tempfile

        source = ("# TIMEOUT is named here, in prose, and prose is not a read.\n"
                  "TIMEOUT = 30.0\n"
                  "USED = 1\n"
                  "print(USED)\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text(source, encoding="utf-8")
            loads = self._loads([path])
            declared = [n.targets[0].id
                        for n in ast.parse(source).body
                        if isinstance(n, ast.Assign)]

        assert declared == ["TIMEOUT", "USED"]
        assert not loads["TIMEOUT"], "a mention in a comment is not a read"
        assert loads["USED"], "and a real use is"

    def test_a_twin_that_is_read_does_not_cover_for_one_that_is_not(self):
        """The counting bug, pinned at the case that actually bit.

        Not "two declarations and no reader" -- that one the global tally
        caught. The hole was two declarations where *one* is read: planting an
        unused `TIMEOUT` in a module while `estgec.TIMEOUT` is used elsewhere
        swept clean.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reader.py").write_text(
                "from .used import TIMEOUT\nprint(TIMEOUT)\n", encoding="utf-8")
            (root / "used.py").write_text("TIMEOUT = 1\n", encoding="utf-8")
            (root / "idle.py").write_text("TIMEOUT = 2\n", encoding="utf-8")
            reads = self._loads(sorted(root.rglob("*.py")))

            assert not self._orphan("TIMEOUT", root / "used.py", reads), (
                "the one that is imported is read")
            assert self._orphan("TIMEOUT", root / "idle.py", reads), (
                "and its twin is still an orphan")

    def test_a_constant_reached_as_an_attribute_counts_as_read(self):
        """`config.PROVIDER_TIMEOUT` is how most of this codebase reads one."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "conf.py").write_text("BUDGET = 1\n", encoding="utf-8")
            (root / "app.py").write_text(
                "from . import conf\nprint(conf.BUDGET)\n", encoding="utf-8")
            reads = self._loads(sorted(root.rglob("*.py")))
            assert not self._orphan("BUDGET", root / "conf.py", reads)

    def test_the_exemption_is_still_needed(self):
        """`ALLOWED` stays honest only if an entry that stopped being necessary
        fails. It could not before: naming a constant here was what made it
        look read."""
        declared, loads = self._swept()
        for name in self.ALLOWED:
            where = [path for n, path, _ in declared if n == name]
            assert where, f"{name} is exempt and no longer exists"
            assert all(self._orphan(name, path, loads) for path in where), (
                f"{name} is read now -- take it out of ALLOWED")


class TestTheLicenceLedgerStaysSeparable:
    """`eesti/licences.py` was split out of `sources.py` because the two halves
    share nothing at runtime: the store never reads a `note`, the ledger never
    opens a database. That is the property the file boundary encodes, and it is
    exactly the kind of property that rots silently — one convenient import and
    the ledger is a database module again, with nobody the wiser until the next
    person wonders why it was split.
    """

    def test_the_ledger_touches_no_database(self):
        import ast

        tree = ast.parse((ROOT / "eesti" / "licences.py").read_text(encoding="utf-8"))
        # Every segment, not the first. `from eesti.sources import X` resolves
        # to "eesti" on a first-segment split and sails through -- so the one
        # import this guard exists to catch, the circular one back into the
        # store, was the one it could not see.
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported |= set(a.name.split("."))
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported |= set(node.module.split("."))
                imported |= {a.name for a in node.names}
        assert "sqlite3" not in imported, (
            "the ledger has grown a database dependency; that is the seam the "
            "split exists to keep")
        assert not (imported & {"sources", "urllib", "requests"}), imported

    def test_that_guard_would_catch_the_import_it_is_for(self):
        """A guard whose failure mode nobody has seen is a guard nobody has
        tested. Both spellings of the circular import must be visible."""
        import ast

        for line in ("from .sources import connect",
                     "from eesti.sources import connect",
                     "import eesti.sources"):
            imported = set()
            for node in ast.walk(ast.parse(line)):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        imported |= set(a.name.split("."))
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported |= set(node.module.split("."))
                    imported |= {a.name for a in node.names}
            assert "sources" in imported, line

    def test_the_old_import_path_still_works(self):
        """Fifteen call sites say `from ..sources import REGISTRY`, and moving
        a file is not a reason to touch fifteen files."""
        from eesti import licences
        from eesti.sources import REGISTRY, Source

        assert REGISTRY is licences.REGISTRY
        assert Source is licences.Source

    def test_neither_half_is_large_again(self):
        """The split bought a reader ~250 lines they did not need. A guard on
        the number is cruder than the reason, and the reason is not checkable —
        but a file creeping back over 700 lines is the signal that the next
        cohesive piece is waiting to come out."""
        for name in ("sources.py", "licences.py"):
            lines = len((ROOT / "eesti" / name).read_text(encoding="utf-8").splitlines())
            assert lines < 700, f"eesti/{name} is {lines} lines"
