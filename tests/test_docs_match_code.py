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

#: Every document states the current state; history lives in git. `AGENTS.md`
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

        actual = f"{sum(1 for t in TOPICS if t.generator)} of {len(TOPICS)}"
        found = _claims(r"(\d+ of \d+) (?:curriculum |grammar )?topics")
        assert found, "no document states how many topics have practice"
        for doc, line, value, text in found:
            assert value == actual, (
                f"{doc.relative_to(ROOT)}:{line} says {value}; "
                f"the code has {actual}.\n  {text}")

    def test_topics_without_a_generator(self):
        from eesti.curriculum import TOPICS

        actual = sum(1 for t in TOPICS if not t.generator)
        # `\w+ ` allows an adverb ("topics still have no generator").
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


class TestTheMaterialPolicy:
    """The reading floor, the reach levels and the read-aloud length the docs state."""

    def test_the_reading_floor(self):
        from eesti.difficulty import FLOOR

        found = _claims(r"at least \*?\*?(\d+) %")
        assert found, "no document states the reading floor"
        for doc, line, value, text in found:
            assert int(value) == round(FLOOR * 100), (
                f"{doc.relative_to(ROOT)}:{line} says {value} %; FLOOR is {FLOOR}")

    def test_the_reach_levels(self):
        from eesti.difficulty import REACH_LEVELS

        found = _claims(r"(A\d–A\d) on the word list")
        assert found, "no document states the reach levels"
        for doc, line, value, text in found:
            assert value == f"{REACH_LEVELS[0]}–{REACH_LEVELS[-1]}", (
                f"{doc.relative_to(ROOT)}:{line} says {value}")

    def test_the_read_aloud_length(self):
        from eesti.pronunciation import SAY_MAX_WORDS, SAY_MIN_WORDS

        found = _claims(r"(\d+–\d+) words\W* (?:all within reach|in which)")
        assert found, "no document states the read-aloud length"
        for doc, line, value, text in found:
            assert value == f"{SAY_MIN_WORDS}–{SAY_MAX_WORDS}", (
                f"{doc.relative_to(ROOT)}:{line} says {value} words")


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
        return set(re.findall(r'data-tab="[a-z]+"[^>]*>.*?<span class="lbl"[^>]*>([^<]+)',
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


class TestTheCiMatrixKnowsWhatShips:
    """One Python minor everywhere: the Dockerfile, CI, the eval
    and `.python-version` agree.
    """

    @staticmethod
    def _shipped() -> set[str]:
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        return set(re.findall(r"^FROM python:(\d+\.\d+)-slim", dockerfile, re.M))

    def test_both_stages_use_one_minor_version(self):
        assert len(self._shipped()) == 1, self._shipped()

    def test_the_comment_names_the_version_the_image_is_built_on(self):
        workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        assert "the one the Dockerfile ships" in workflow

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
        for path in [ROOT / "Dockerfile", ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "requirements.txt",
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
