"""The syllabus graph.

Most of these are structural: a curriculum that silently drops a topic or
teaches a case before its stem is worse than no curriculum, and both failures
are invisible at a glance.
"""

from __future__ import annotations

import pytest

from eesti import curriculum as c
from eesti.config import LEVELS


def test_the_declared_graph_is_well_formed():
    c.validate()  # duplicate ids, unknown levels/tags, dangling prereqs, cycles


def test_order_contains_every_topic_exactly_once():
    """The failure this guards against is silent: a cycle or a dropped edge
    removes topics from the path without removing them from the syllabus."""
    path = c.order()
    assert [t.id for t in path] == list(dict.fromkeys(t.id for t in path))
    assert {t.id for t in path} == {t.id for t in c.TOPICS}


def test_no_topic_appears_before_something_it_requires():
    seen: set[str] = set()
    for topic in c.order():
        assert set(topic.requires) <= seen, f"{topic.id} taught before {topic.requires}"
        seen.add(topic.id)


def test_the_genitive_stem_precedes_everything_built_from_it():
    """The one ordering claim the module makes about Estonian specifically."""
    path = [t.id for t in c.order()]
    stem = path.index("gen-stem")
    for dependent in c.unlocks("gen-stem"):
        assert path.index(dependent) > stem


def test_gen_stem_unlocks_most_of_the_noun_system():
    downstream = c.unlocks("gen-stem")
    assert {"kohakaanded", "obj-case", "mitmus", "vordlusastmed"} <= set(downstream)


def test_a_lower_level_never_depends_on_a_higher_one():
    for topic in c.TOPICS:
        for need in topic.requires:
            assert LEVELS.index(c.by_id(need).level) <= LEVELS.index(topic.level)


def test_order_is_deterministic():
    assert [t.id for t in c.order()] == [t.id for t in c.order()]


def test_path_order_ignores_corpus_weight():
    """Sequencing and practice priority are different questions.

    Weighting the path by error frequency put verb stems ahead of the genitive
    and the alphabet last; the tie-break is declaration order for that reason.
    """
    path = [t.id for t in c.order()]
    assert path.index("pohivormid") < path.index("verb-form")
    assert path[0] == "tahestik"


def test_practice_order_does_use_corpus_weight():
    ranked = [t.id for t in c.practice_order()]
    assert ranked[0] == "sonajark"      # 11.4 % of annotated learner errors
    assert ranked[1] == "rektsioon"     # 10.0 %
    assert ranked.index("obj-case") < ranked.index("kirjavahemargid")


def test_available_offers_only_unblocked_unknown_topics():
    assert c.available({t.id for t in c.TOPICS}) == []

    start = c.available(set())
    assert all(t.requires == () for t in start)
    assert "obj-case" not in {t.id for t in start}

    known = {"pohivormid", "gen-stem", "osastav", "eitus"}
    offered = {t.id for t in c.available(known)}
    assert "obj-case" in offered
    assert not (known & offered)


def test_skipping_a_topic_unlocks_its_dependants():
    """Skip and complete are the same operation on the graph, which is why the
    placement test can reuse the mastery check."""
    assert "obj-case" not in {t.id for t in c.available(set())}
    skipped = {"pohivormid", "gen-stem", "osastav", "eitus"}
    assert "obj-case" in {t.id for t in c.available(skipped)}


def test_blocked_by_names_what_is_missing():
    assert c.blocked_by("obj-case", {"gen-stem"}) == ["eitus", "osastav"]
    assert c.blocked_by("obj-case", {"gen-stem", "osastav", "eitus"}) == []


def test_corpus_weights_use_the_error_log_vocabulary():
    from eesti.config import TAGS

    assert set(c.CORPUS_WEIGHT) <= set(TAGS)


def test_tagged_topics_resolve_to_a_handbook_section():
    tagged = [t for t in c.TOPICS if t.tag]
    assert tagged
    for topic in tagged:
        assert topic.reference is not None, topic.id
        assert topic.reference.url.startswith("https://")


def test_validate_rejects_a_dangling_prerequisite(monkeypatch):
    broken = c.TOPICS + (c.Topic("bogus", "A1", "x", "x", requires=("nope",)),)
    monkeypatch.setattr(c, "TOPICS", broken)
    monkeypatch.setattr(c, "_BY_ID", {t.id: t for t in broken})
    with pytest.raises(ValueError, match="unknown topic"):
        c.validate()


def test_order_rejects_a_cycle():
    a = c.Topic("a", "A1", "a", "a", requires=("b",))
    b = c.Topic("b", "A1", "b", "b", requires=("a",))
    with pytest.raises(ValueError, match="cycle"):
        c.order((a, b))


def test_coverage_reports_the_gap_rather_than_hiding_it():
    cov = c.coverage()
    assert cov["topics"] == len(c.TOPICS)
    # Most topics have no generator yet. That is the point of step 2, and the
    # number is meant to be embarrassing until it moves.
    assert cov["with_generator"] < cov["topics"]
