"""Three sections, and nothing homeless.

The app answers three questions and each section belongs to exactly one:

    õppimine  — "what am I learning today?"
    kordamine — "what am I forgetting?"
    eksam     — "am I ready?"

Sections used to filter on skill alone, and that held only while every item was
reading or listening practice. The official material broke it: HARNO publishes
samples, videos, workbooks and information sheets that carry the *same skill* as
a task while being a completely different activity. Twenty-five of them landed
in no section at all — in the database, absent from the app, and nothing said
so.

The test that matters here is the orphan check. A missing section is visible;
an item that belongs to none is not.
"""

from __future__ import annotations

import json

import pytest

from eesti.harvest import harno
from eesti.library import MODES, SECTIONS, browse, by_id, sections
from eesti.sources import Item, add_items, connect, register


@pytest.fixture
def shelf(tmp_path):
    """One item of **every** kind the HARNO harvester can produce.

    This used to be a hand-written list of "kinds that have caused trouble",
    which is a list of things that already exist somewhere else — and it failed
    the way those lists always fail. `statistika` and `vorm` were added to the
    harvester, nobody added them here, and 20 items sat in the database and in
    no section. That is the exact bug the orphan check below was written for
    after 25 items disappeared the same way; the check was fine, its fixture
    could not see the problem.

    So the kinds come from `harno.KINDS` now. A kind added to the harvester
    appears here on the next run, and if no section claims it this fails.
    """
    conn = connect(tmp_path / "content.db")
    register(conn)
    sources = {r["id"] for r in conn.execute("SELECT id FROM sources")}
    made = [
        Item(source_id="selges-keeles", skill="lugemine", title="Lihtne tekst",
             body="Ma lugesin raamatu läbi."),
        Item(source_id="err-r4", skill="grammatika", title="Saade 22",
             body="Objekti kääne."),
    ]
    # `skill` deliberately varies: a kind reachable only when it happens to
    # carry one skill is not reachable.
    skills = ("lugemine", "kirjutamine", "eksam", "kuulamine", "raakimine")
    for n, kind in enumerate(k for k in harno.KINDS if k not in harno.NOT_INDEXED):
        made.append(Item(
            source_id="harno", skill=skills[n % len(skills)],
            title=f"B1 {kind}", body="",
            meta={"kind": kind, "external": True},
        ))
    made.append(Item(source_id="harno", skill="eksam", title="B1 video",
                     body="", meta={"kind": "video", "external": True}))
    add_items(conn, [i for i in made if i.source_id in sources])
    return conn


class TestNothingIsHomeless:
    def test_every_item_appears_in_some_section(self, shelf):
        """The check that a missing section would not give you."""
        placed: set[str] = set()
        for section in SECTIONS:
            placed |= {r["id"] for r in browse(shelf, section.id, limit=500)}
        everything = {r["id"] for r in shelf.execute("SELECT id FROM items")}
        assert everything - placed == set()

    def test_every_kind_the_harvester_makes_has_a_section_that_wants_it(self):
        """Read off the two vocabularies, with no database in the way.

        The orphan check above needs an item to exist before it can notice the
        gap. This one notices as soon as the harvester learns a kind nobody
        shows — which is the moment it becomes wrong, not the moment somebody
        harvests.
        """
        claimed = {kind for section in SECTIONS for kind in section.kinds}
        indexed = set(harno.KINDS) - set(harno.NOT_INDEXED)
        assert indexed - claimed == set(), (
            "HARNO produces these kinds and no section shows them: "
            f"{sorted(indexed - claimed)}"
        )

    def test_statistics_are_never_indexed_in_the_first_place(self):
        """Eleven PDFs of national pass rates. Not study material, and a pass
        rate beside a verdict that refuses to predict is worse than absent."""
        assert "statistika" in harno.NOT_INDEXED

    def test_the_kinds_that_were_lost_are_reachable(self, shelf):
        """Samples, workbooks, videos and the forms: the ones that vanished."""
        for section_id, expected in [("naidised", "sooritusnaidis"),
                                     ("vihikud", "konsultatsioon"),
                                     ("eksamiinfo", "video"),
                                     ("eksamiinfo", "vorm")]:
            rows = browse(shelf, section_id, limit=50)
            kinds = {json.loads(r["meta"] or "{}").get("kind") for r in rows}
            assert expected in kinds, section_id


class TestTheSectionsSeparate:
    def test_reading_practice_excludes_exam_tasks(self, shelf):
        """349 simple texts and 17 exam PDFs in one list served neither the
        person practising nor the person deciding whether to register."""
        rows = browse(shelf, "lugemine", limit=50)
        kinds = {json.loads(r["meta"] or "{}").get("kind") for r in rows}
        assert "ulesanne" not in kinds

    def test_exam_tasks_exclude_everything_that_is_not_a_task(self, shelf):
        rows = browse(shelf, "eksam", limit=50)
        kinds = {json.loads(r["meta"] or "{}").get("kind") for r in rows}
        assert kinds <= {"ulesanne"}

    def test_workbooks_are_revision_not_exam(self, shelf):
        """The one piece of official material that is homework."""
        assert by_id("vihikud").mode == "kordamine"


class TestModes:
    def test_every_section_declares_one(self):
        assert all(s.mode in MODES for s in SECTIONS)

    def test_all_three_have_something(self, shelf):
        for mode in MODES:
            found = sections(shelf, mode=mode)
            assert found, mode
            assert sum(s["items"] for s in found) > 0, mode

    def test_filtering_by_mode_is_a_partition(self, shelf):
        """Every section shows up under exactly one mode, so nothing is listed
        twice and nothing is missing from the navigation."""
        seen = [s["id"] for mode in MODES for s in sections(shelf, mode=mode)]
        assert sorted(seen) == sorted(s.id for s in SECTIONS)


class TestLanguage:
    def test_labels_are_estonian_and_notes_are_russian(self):
        """The rule from CLAUDE.md: the interface is exposure, the explanation
        is where comprehension has to win."""
        for section in SECTIONS:
            assert section.note, section.id
            assert any("Ѐ" <= ch <= "ӿ" for ch in section.note), (
                f"{section.id}: the note explains what a section is and must be "
                f"readable by a Russian speaker still learning Estonian"
            )

    def test_every_section_has_a_russian_name_too(self):
        for section in SECTIONS:
            assert section.ru and section.et


class TestTheExamTaxonomyIsStatedOnce:
    """Exam material is grouped twice, by two different code paths.

    `library.SECTIONS` declares which `kind` values belong to `naidised`,
    `eksam` and `eksamiinfo`; `library.exam_material` groups the same values
    again for the exam screen, which does not read `SECTIONS` at all. Two
    expressions of one taxonomy, and they agree today — checked, not assumed.

    They are not merged because they answer different questions: `SECTIONS`
    drives browsing by section, `exam_material` returns one level's material in
    a single request grouped by activity. But this is precisely the shape that
    produced the `TABS` bug — a hand-kept list beside the thing it describes,
    where nothing failed when they drifted because both halves still returned
    *something*. So the correspondence is asserted in both directions, which is
    what this project's own rule prescribes when a list cannot be derived away.
    """

    @staticmethod
    def _declared() -> set[str]:
        from eesti.library import SECTIONS

        return {k for s in SECTIONS if s.mode == "eksam" for k in s.kinds}

    @staticmethod
    def _grouped() -> set[str]:
        import re
        from pathlib import Path

        from eesti import library

        src = Path(library.__file__).read_text(encoding="utf-8")
        body = src[src.index("def exam_material"):]
        end = body.find("\ndef ", 10)
        if end != -1:
            body = body[:end]
        # Derived, like everything else about this vocabulary: a hand-written
        # tuple here is how `vorm` could be declared by a section, rendered by
        # nowhere, and pass both directions of this check.
        known = sorted(set(harno.KINDS) | {"konsultatsioon"}, key=len, reverse=True)
        return set(re.findall("|".join(known), body))

    def test_every_kind_the_exam_screen_groups_belongs_to_a_section(self):
        """Otherwise the exam screen shows material that browsing cannot find."""
        assert self._grouped() <= self._declared(), (
            f"grouped but unsectioned: {sorted(self._grouped() - self._declared())}")

    def test_every_kind_a_section_claims_is_grouped_by_the_exam_screen(self):
        """And the other direction: a section nothing renders is 25 items
        present in the database and absent from the app, which has happened
        here once already."""
        assert self._declared() <= self._grouped(), (
            f"sectioned but ungrouped: {sorted(self._declared() - self._grouped())}")


class TestEverySourceIdIsRegistered:
    """The ledger has to cover every source the code names.

    `sources.REGISTRY` is this project's licence record — "licensing is a
    column, not a convention" — and `add_items` refuses a row whose source is
    not in it. That gate only covers rows going into `items`, though, and a
    source id is written in two other places: `Cloze.source_id`, which records
    which corpus a drill sentence was cut from, and the harvesters' own
    `clear_source` calls.

    Asking which ids the code actually writes is how `ekk` turned up: the
    handbook every rule explanation links to, whose rection table is fetched
    once and stored, was the one third party with no entry in the ledger.
    """

    @staticmethod
    def _written_ids() -> dict[str, set[str]]:
        import collections
        import re
        from pathlib import Path

        pattern = re.compile(
            r'source_id\s*=\s*["\']([a-z0-9-]+)["\']'
            r'|clear_source\([^,]+,\s*["\']([a-z0-9-]+)["\']')
        found = collections.defaultdict(set)
        root = Path(__file__).resolve().parents[1] / "eesti"
        for path in sorted(root.rglob("*.py")):
            for match in pattern.finditer(path.read_text(encoding="utf-8")):
                sid = match.group(1) or match.group(2)
                found[sid].add(path.name)
        return found

    def test_there_are_ids_to_check(self):
        assert len(self._written_ids()) >= 5

    def test_every_id_the_code_writes_is_in_the_registry(self):
        from eesti.sources import REGISTRY

        known = {s.id for s in REGISTRY}
        unknown = {sid: sorted(where) for sid, where in self._written_ids().items()
                   if sid not in known}
        assert not unknown, (
            f"these source ids are written by the code and have no licence "
            f"entry: {unknown}. Add them to `sources.REGISTRY` — a row nobody "
            f"can name the licence of is a row nobody can reason about later.")

    def test_every_registered_source_states_a_licence(self):
        from eesti.sources import REGISTRY

        silent = [s.id for s in REGISTRY if not s.licence.strip()]
        assert not silent, f"registered with no licence stated: {silent}"

    def test_nothing_ungranted_is_marked_redistributable(self):
        """The posture that keeps owner-only material owner-only. A source
        whose licence says it is unknown or personal-study cannot also claim to
        be shareable."""
        from eesti.sources import REGISTRY

        for source in REGISTRY:
            ungranted = any(word in source.licence.lower() for word in
                            ("personal study", "no licence", "unknown",
                             "not reproduced"))
            if ungranted:
                assert not source.redistributable, (
                    f"{source.id} states {source.licence!r} and is flagged "
                    f"redistributable")
