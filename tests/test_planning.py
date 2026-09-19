"""Today's plan: a pure function of the evidence, so the same inputs give the same
plan, and each block's reason says why it is there."""

from __future__ import annotations

import pytest

from eesti import planning
from eesti.planning import PlanInputs, Weak, plan

EVERY_PART = {"kirjutamine": 2, "kuulamine": 1, "lugemine": 3, "raakimine": 0}


def _inputs(**kw) -> PlanInputs:
    base = dict(today="2026-09-19", due=0, activity=dict(EVERY_PART),
                frontier=("tingiv", "tingiv kõneviis"))
    return PlanInputs(**(base | kw))


def test_the_same_evidence_gives_the_same_plan():
    a = plan(_inputs(due=12), 20)
    b = plan(_inputs(due=12), 20)
    assert a == b and a.inputs == b.inputs


def test_the_budget_is_filled_exactly():
    for minutes in (10, 20, 45):
        p = plan(_inputs(due=30, reading=("t1", "Tekst")), minutes)
        assert sum(b.minutes for b in p.blocks) == minutes


def test_reviews_never_take_more_than_their_share():
    p = plan(_inputs(due=200), 20)
    assert p.blocks[0].kind == "review" and p.blocks[0].minutes == 8


def test_a_weak_rule_comes_with_its_last_mistake():
    weak = Weak("obj-case", "täissihitis ja osasihitis", "negation", 0.5, 8, None,
                {"prompt": "Ma ei ostnud ____.", "expected": "piletit",
                 "answer": "pileti", "solution": "Ma ei ostnud piletit."})
    p = plan(_inputs(weak=(weak,)), 20)
    repair = next(b for b in p.blocks if b.kind == "repair")
    assert repair.action == {"tab": "path", "topic": "obj-case", "rules": ["negation"]}
    assert "eitus" in repair.et and "50%" in repair.why
    assert repair.detail["answer"] == "pileti"


def test_the_least_practised_exam_part_gets_a_block():
    p = plan(_inputs(), 20)
    skill = next(b for b in p.blocks if b.kind == "skill")
    assert skill.action == {"tab": "speak"} and "0 занятий" in skill.why


def test_order_is_review_repair_refresh_skill_new_read():
    weak = Weak("obj-case", "x", None, 0.4, 9, None)
    p = plan(_inputs(due=4, weak=(weak,), refresh=(("gen-stem", "y"),),
                     reading=("t1", "Tekst")), 40)
    assert [b.kind for b in p.blocks] == ["review", "repair", "refresh", "skill",
                                          "new", "read"]


@pytest.mark.parametrize("n,word", [(1, "карточка"), (3, "карточки"), (11, "карточек"),
                                    (21, "карточка"), (25, "карточек")])
def test_russian_counts_agree(n, word):
    assert planning._count(n, "карточка", "карточки", "карточек") == f"{n} {word}"


class TestFromTheLearnersEvidence:
    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx2")
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    def test_repeated_misses_become_the_repair_block(self, client):
        for _ in range(8):
            it = client.post("/api/practice", json={
                "topic": "obj-case", "count": 1, "rules": ["negation"]}).json()["items"][0]
            client.post("/api/practice/answer", json={
                "topic": "obj-case", "prompt": "", "answer": "", "given": "vale",
                "token": it["token"]})
        p = client.get("/api/plan?minutes=20").json()
        repair = next(b for b in p["blocks"] if b["kind"] == "repair")
        assert repair["action"]["rules"] == ["negation"]
        assert repair["detail"]["answer"] == "vale"

    def test_a_reload_does_not_log_the_plan_twice(self, client):
        from eesti import evidence

        client.get("/api/plan")
        client.get("/api/plan")
        with evidence.connect() as log:
            issued = [e for e in evidence.events(log) if e.type == "plan-issued"]
        assert len(issued) == 1


def test_cards_never_reviewed_do_not_make_a_topic_look_forgotten():
    """Mastering a topic seeds cards nobody has reviewed; FSRS says 0 for them."""
    from eesti import config, handoff, learner, progress, review

    prog = progress.connect(config.PROGRESS_DB)
    rev = review.connect(config.REVIEW_DB)
    progress.mark_mastered(prog, "tingiv", via="placement")
    assert handoff.seed_mastered(rev, "tingiv", seed=1)
    found = learner.rule_evidence(prog, rev)
    assert not [e for e in found if e.topic == "tingiv" and e.weak]
    assert "tingiv" not in learner.needs_refresh(prog, found)
