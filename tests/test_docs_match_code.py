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
        found = _claims(r"(\d+) curriculum topics have no generator")
        for doc, line, value, text in found:
            assert int(value) == actual, (
                f"{doc.relative_to(ROOT)}:{line} says {value}; "
                f"the code has {actual}.\n  {text}")

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

    def test_route_count(self):
        actual = self._declared()
        for doc, line, value, text in _claims(r"(\d+) API routes"):
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
