"""Test-out and placement, with `ask` injected so the real generators and progress
database are used.
"""

from __future__ import annotations

import pytest

from eesti.placement import (MAX_FAILURES, MAX_PROBES, PROBE_ITEMS,
                             PROBE_REQUIRED, candidates,
                             entry_points, probe, sweep)
from eesti.progress import connect, is_mastered, mark_mastered, mastered


@pytest.fixture
def db(tmp_path):
    return connect(tmp_path / "p.db")


def perfect(item):
    return item.answer


def wrong(item):
    return item.distractor


def knows(topics):
    """An `ask` that answers correctly only on the given topics."""
    def _ask(item):
        return item.answer if item.topic in topics else "vale"
    return _ask


class TestProbe:
    def test_a_clean_sweep_marks_the_topic_known(self, db):
        result = probe(db, "kusisonad", perfect, seed=1)
        assert result.passed and result.correct == result.asked == PROBE_ITEMS
        assert is_mastered(db, "kusisonad")

    def test_one_mistake_is_not_enough(self, db):
        """The probe bar (5 of 5) is stricter than the practice gate (8 of 10)."""
        calls = {"n": 0}

        def almost(item):
            calls["n"] += 1
            return item.distractor if calls["n"] == 2 else item.answer

        result = probe(db, "kusisonad", almost, seed=1)
        assert result.correct == PROBE_ITEMS - 1
        assert not result.passed
        assert not is_mastered(db, "kusisonad")

    def test_probe_attempts_are_recorded_as_real_attempts(self, db):
        """They are real graded answers; the rolling window should know."""
        probe(db, "kusisonad", wrong, seed=1)
        n = db.execute(
            "SELECT COUNT(*) FROM attempts WHERE topic='kusisonad'"
        ).fetchone()[0]
        assert n == PROBE_ITEMS

    def test_a_failed_probe_leaves_the_answers_for_the_error_log(self, db):
        probe(db, "kusisonad", wrong, seed=1)
        answers = [r[0] for r in db.execute("SELECT answer FROM attempts")]
        assert all(answers)

    def test_an_already_known_topic_is_not_re_probed(self, db):
        mark_mastered(db, "kusisonad", via="practice")

        def explode(item):  # pragma: no cover - must never be called
            raise AssertionError("re-probed a topic already known")

        result = probe(db, "kusisonad", explode)
        assert result.passed and not result.ran and result.skipped

    def test_a_topic_with_no_generator_is_reported_not_crashed(self, db):
        result = probe(db, "lauseehitus", perfect)
        assert not result.ran and "no generator" in result.skipped
        assert not is_mastered(db, "lauseehitus")

    def test_passing_is_recorded_as_placement_not_practice(self, db):
        probe(db, "kusisonad", perfect, seed=1)
        via = db.execute(
            "SELECT via FROM topic_state WHERE topic='kusisonad'"
        ).fetchone()[0]
        assert via == "placement"


class TestSweep:
    def test_it_stops_once_failures_accumulate(self, db):
        results = sweep(db, wrong, seed=1)
        failed = [r for r in results if r.ran and not r.passed]
        assert len(failed) <= MAX_FAILURES
        assert len(results) <= MAX_PROBES

    def test_a_failure_on_one_branch_does_not_end_the_other(self, db):
        """The defect this replaced: two consecutive noun failures concluded the
        placement without ever asking about a verb. Being strong on verbs and
        shaky on nouns is an ordinary way to be."""
        verbs = {"olevik", "verb-form", "lihtminevik", "ma-da-inf", "kusisonad"}
        results = sweep(db, knows(verbs), seed=1)
        reached = {r.topic for r in results}
        asked = {r.topic for r in results if r.ran}

        # The noun branch is entered at `pohivormid`, a real prerequisite; the fixture word
        # list has no `object_cases`, so it is reached rather than asked.
        assert {"pohivormid", "gen-stem"} & reached, sorted(reached)
        assert asked & {"olevik", "verb-form"}   # and the verb branch was asked
        assert {"olevik", "verb-form"} <= mastered(db)

    def test_a_failure_prunes_what_depends_on_it(self, db):
        """Asking about `obj-case` after failing `osastav` only confirms what
        the failure already established."""
        from eesti.curriculum import unlocks

        results = sweep(db, knows({"kusisonad"}), seed=1)
        failed = {r.topic for r in results if r.ran and not r.passed}
        asked = {r.topic for r in results}
        for topic in failed:
            assert not (set(unlocks(topic)) & asked)

    def test_entry_points_are_reported_per_branch(self, db):
        results = sweep(db, knows({"olevik", "verb-form", "kusisonad"}), seed=1)
        points = entry_points(results)
        assert len(points) >= 1
        assert not (set(points) & mastered(db))

    def test_a_complete_beginner_is_placed_at_the_first_topic(self, db):
        results = sweep(db, wrong, seed=1)
        assert entry_points(results)
        assert mastered(db) == set()

    def test_passing_a_topic_unlocks_what_depends_on_it_mid_sweep(self, db):
        """`gen-stem` gates eleven topics; the candidate list has to be
        recomputed as the sweep goes or they are never offered."""
        before = {t.id for t in candidates(db)}
        assert "mitmus" not in before
        probe(db, "gen-stem", perfect, seed=1)
        assert "mitmus" in {t.id for t in candidates(db)}

    def test_a_topic_is_never_probed_twice_in_one_sweep(self, db):
        results = sweep(db, knows({"kusisonad"}), seed=1)
        topics = [r.topic for r in results]
        assert len(topics) == len(set(topics))

    def test_candidates_are_drillable_and_unblocked(self, db):
        for topic in candidates(db):
            assert topic.generator is not None
            # Reference topics come from `progress.reference_topics()`.
            from eesti.progress import reference_topics

            assert set(topic.requires) <= reference_topics() | mastered(db)

    def test_level_filter_is_honoured(self, db):
        assert all(t.level == "A1" for t in candidates(db, levels=("A1",)))

    def test_the_first_entry_point_is_the_first_real_failure(self, db):
        results = sweep(db, knows({"kusisonad"}), seed=1)
        first_fail = next(r for r in results if r.ran and not r.passed)
        assert entry_points(results)[0] == first_fail.topic

    def test_a_probe_budget_bounds_the_session(self, db):
        """These are stopping rules for the learner's patience, not claims
        about their level."""
        results = sweep(db, perfect, seed=1, max_probes=3)
        assert len(results) <= 3

    def test_there_is_no_entry_point_when_nothing_failed(self, db):
        from eesti.placement import ProbeResult

        assert entry_points([ProbeResult("x", 5, 5, True)]) == []


def test_the_probe_bar_is_stricter_than_the_practice_gate():
    from eesti.progress import MASTERY_CORRECT, MASTERY_WINDOW

    assert PROBE_REQUIRED / PROBE_ITEMS > MASTERY_CORRECT / MASTERY_WINDOW


class TestTheWebTestOut:
    """Test-out from the app: the server rebuilds the items from the seed and runs
    the same probe the CLI does."""

    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx2")
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    def test_five_of_five_marks_the_topic_known(self, client):
        from eesti.placement import PROBE_ITEMS

        got = client.get("/api/testout/tingiv?seed=4").json()
        assert len(got["items"]) == PROBE_ITEMS and got["required"] == PROBE_ITEMS
        r = client.post("/api/testout/tingiv", json={
            "seed": got["seed"], "given": [i["answer"] for i in got["items"]]}).json()
        assert r["passed"] and r["correct"] == PROBE_ITEMS
        rows = {t["id"]: t for t in client.get("/api/curriculum").json()["topics"]}
        assert rows["tingiv"]["state"] == "mastered"

    def test_one_miss_leaves_the_topic_where_it_was(self, client):
        got = client.get("/api/testout/tingiv?seed=4").json()
        given = [i["answer"] for i in got["items"]]
        given[0] = "vale"
        r = client.post("/api/testout/tingiv",
                        json={"seed": got["seed"], "given": given}).json()
        assert not r["passed"] and r["correct"] == len(given) - 1
        rows = {t["id"]: t for t in client.get("/api/curriculum").json()["topics"]}
        assert rows["tingiv"]["state"] != "mastered"

    def test_a_topic_without_a_generator_says_so(self, client):
        assert client.get("/api/testout/lauseehitus").status_code == 400
        assert client.get("/api/testout/nonesuch").status_code == 404

    def test_the_wrong_number_of_answers_is_refused(self, client):
        got = client.get("/api/testout/tingiv?seed=4").json()
        assert client.post("/api/testout/tingiv", json={
            "seed": got["seed"], "given": ["x"]}).status_code == 400
