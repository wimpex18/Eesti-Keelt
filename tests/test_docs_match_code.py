"""Numbers and structures in the documentation, checked against the code.

A true sentence in a doc goes stale silently, and a later session plans against
it. A claim that can be derived is asserted against its source, so the build
fails when the two disagree. Narrow by design: counts, the tab diagram and cited
file paths; prose is not verified.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pagesrc import markup_and_script

ROOT = Path(__file__).resolve().parents[1]

#: Every document states the current state; history lives in git. `CLAUDE.md`
#: and `.claude/rules/` hold instructions, not counts, and are not scanned.
LIVE = tuple(["README.md"] + sorted(f"docs/{p.name}" for p in (ROOT / "docs").glob("*.md")))
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
        """"N of M drillable topics link to the handbook": both numbers are checked."""
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
        """The fenced list of topics without a generator matches the code."""
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
        """Route decorators across the API package (a glob over `eesti/api/*.py`)."""
        modules = sorted((ROOT / "eesti" / "api").glob("*.py"))
        assert modules, "no API modules found -- this check would measure zero"
        return sum(len(re.findall(r"@router\.(?:get|post)",
                                  m.read_text(encoding="utf-8")))
                   for m in modules)

    def test_the_count_is_not_zero(self):
        """Every assertion below compares against this number."""
        assert self._declared() > 40

    def test_the_api_endpoint_count(self):
        """"N API endpoints" counts `/api/*` paths from `api.paths()` — the set the caller
        guarantee in `test_route_inventory.py` covers.
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
    """The app-structure diagram lists exactly the tabs the page has."""

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
    """Every backticked file name in the docs and rules exists. Names that are
    deliberately not files go in `NOT_A_FILE` with a reason.
    """

    #: Cited in backticks, correctly, and not a path in this repository.
    NOT_A_FILE: dict[str, str] = {}

    @staticmethod
    def _citations() -> dict[str, set[str]]:
        import collections

        found = collections.defaultdict(set)
        pattern = re.compile(
            r"`([A-Za-z0-9_./-]+\.(?:md|py|js|css|html|sh|ts|yml|json|tsv))`")
        for path in (sorted(ROOT.glob("*.md")) + sorted(ROOT.glob("docs/*.md"))
                     + sorted(ROOT.glob(".claude/rules/*.md"))):
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
    """A module constant nothing reads is flagged.

    Read by AST: identifier loads count, comments do not, and each read resolves to
    its module so a same-named constant elsewhere cannot cover for an orphan.
    Constants only — route handlers are bound by decorators and never named.
    """

    #: Constants deliberately declared and never read, with the reason.
    ALLOWED: set[str] = set()

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
        """Who reads what, keyed by (module, NAME).

        A constant is read when imported from its module, reached as an attribute on it,
        or loaded as a bare name inside it. Modules are keyed by basename, so same-named
        files (`eesti/sources.py`, `eesti/api/sources.py`) share a key.
        """
        import ast
        import collections

        read = collections.defaultdict(set)      # NAME -> {module, ...}
        for path in paths:
            here = path.stem
            tree = ast.parse(path.read_text(encoding="utf-8"))

            # Resolve `from pkg import module as alias`, so constants reached through the
            # alias count as read.
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
        """The mechanism itself is tested: a comment mention does not count as a read."""
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
        """A same-named constant that is read elsewhere does not clear an unread one."""
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
        """Every `ALLOWED` entry must still be needed."""
        declared, loads = self._swept()
        for name in self.ALLOWED:
            where = [path for n, path, _ in declared if n == name]
            assert where, f"{name} is exempt and no longer exists"
            assert all(self._orphan(name, path, loads) for path in where), (
                f"{name} is read now -- take it out of ALLOWED")


class TestTheLicenceLedgerStaysSeparable:
    """`eesti/licences.py` imports no database module: the ledger and the store share
    nothing at runtime.
    """

    def test_the_ledger_touches_no_database(self):
        import ast

        tree = ast.parse((ROOT / "eesti" / "licences.py").read_text(encoding="utf-8"))
        # Check every segment of an import, so `from eesti.sources import X` is caught.
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
        """Neither half of the sources/licences split grows past 700 lines again."""
        for name in ("sources.py", "licences.py"):
            lines = len((ROOT / "eesti" / name).read_text(encoding="utf-8").splitlines())
            assert lines < 700, f"eesti/{name} is {lines} lines"


class TestTheCiMatrixKnowsWhatShips:
    """One interpreter everywhere, pinned to the patch: the Dockerfile, CI, the eval
    and `.python-version` agree.
    """

    @staticmethod
    def _shipped() -> set[str]:
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        return set(re.findall(r"^FROM python:(\d+\.\d+\.\d+)-slim", dockerfile, re.M))

    def test_both_stages_pin_one_patch_release(self):
        assert len(self._shipped()) == 1, self._shipped()

    def test_the_comment_names_the_version_the_image_is_built_on(self):
        workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        claim = re.search(r"(\d+\.\d+\.\d+) is what the Dockerfile\s*#?\s*ships", workflow)
        assert claim, "the matrix comment no longer says which version ships"
        assert claim.group(1) in self._shipped()

    def test_ci_the_eval_and_local_run_the_version_that_ships_and_only_it(self):
        import yaml

        (shipped,) = self._shipped()
        tests = yaml.safe_load((ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8"))
        assert tests["jobs"]["test"]["strategy"]["matrix"]["python-version"] == [shipped]
        evals = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
        assert re.findall(r'python-version:\s*"([\d.]+)"', evals) == [shipped]
        assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == shipped

    def test_no_file_names_an_older_python(self):
        """No file names a Python older than the one that ships."""
        (shipped,) = self._shipped()
        major_minor = tuple(int(x) for x in shipped.split(".")[:2])
        older = re.compile(r"(?:[Pp]ython[ :-]?|py)(3\.(\d+))\b|python:(3\.(\d+))")
        found = []
        for path in [ROOT / "Dockerfile", ROOT / "README.md", ROOT / "CLAUDE.md", ROOT / "requirements.txt",
                     *(ROOT / ".github" / "workflows").glob("*.yml"),
                     *(ROOT / "docs").glob("*.md"), *(ROOT / "tests").glob("*.py")]:
            if path.name == "test_docs_match_code.py":
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for m in older.finditer(line):
                    minor = int(m.group(2) or m.group(4))
                    if (3, minor) < major_minor:
                        found.append(f"{path.relative_to(ROOT)}:{n}")
        assert not found, found
