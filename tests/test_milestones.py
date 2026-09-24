"""Milestones read evidence; they never mint points or mastery."""

from eesti.milestones import for_level
from eesti.progress import connect


def test_empty_learner_has_no_completed_milestones(tmp_path):
    progress = connect(tmp_path / "progress.db")
    rows = for_level(progress, "A2")
    assert len(rows) == 4
    assert all(not row["complete"] for row in rows)


def test_milestones_count_recorded_work_only(tmp_path):
    from eesti.curriculum import TOPICS

    progress = connect(tmp_path / "progress.db")
    topic = next(t.id for t in TOPICS if t.level == "A2" and t.generator)
    progress.execute(
        "INSERT INTO attempts(topic,item_key,correct,at) VALUES (?,?,?,?)",
        (topic, "one", 1, "2026-09-24T00:00:00Z"),
    )
    progress.commit()
    rows = {row["id"]: row for row in for_level(progress, "A2")}
    assert rows["first-practice"]["complete"] is True
    assert rows["first-topic"]["complete"] is False
    assert rows["four-parts"]["current"] == 0
