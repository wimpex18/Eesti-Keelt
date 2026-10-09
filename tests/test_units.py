"""The course as units (`eesti/units.py`, ADR-0007).

What a learner would notice if these broke: a topic that appears in no unit (or
two), a unit that asks for a topic before the one it is built on, an exam topic
no unit serves, a companion link to nowhere, a start at A1 that still opens on
greetings.
"""

from __future__ import annotations

import pytest

from eesti import units
from eesti.curriculum import TOPICS


def test_the_map_is_one_the_course_can_follow():
    units.validate()


def test_every_topic_has_exactly_one_home():
    homes = [t for u in units.UNITS for t in u.topics]
    assert sorted(homes) == sorted(t.id for t in TOPICS)
    assert len(homes) == len(set(homes))


def test_no_unit_comes_before_what_it_builds_on():
    from eesti.curriculum import by_id

    for u in units.UNITS:
        for t in u.topics:
            for need in by_id(t).requires:
                assert units.home(need).n <= u.n, (u.id, t, need)


def test_every_harno_topic_is_served_at_its_stage():
    a2 = {h for u in units.UNITS if u.stage != "B1" for h in u.harno}
    b1 = {h for u in units.UNITS if u.stage == "B1" for h in u.harno}
    assert set(units.HARNO_A2) <= a2
    assert set(units.HARNO_B1) <= b1


def test_a_unit_names_only_harno_s_own_topics():
    named = {h for u in units.UNITS for h in u.harno}
    assert named <= set(units.HARNO_A2) | set(units.HARNO_B1)


def test_every_companion_link_is_a_public_course_map():
    for u in units.UNITS:
        assert u.course is not None, u.id
        kind, n = u.course
        assert (kind, u.stage == "B1") in (("KK", False), ("KT", True)), u.id
        assert 1 <= n <= (16 if kind == "KK" else 13)
        link = units.course_link(u, "uk")
        assert link.startswith("https://www.keeleklikk.ee/")
        # Keeletee has no Ukrainian; the link falls back to English, not 404.
        assert ("/ua/" in link) == (kind == "KK")


def test_a_revisited_rule_exists_in_its_generator():
    from eesti.drills import RULE_ET
    from eesti.existential import FRAMES
    from eesti.phrases import BASE_RULES as PHRASE_RULES

    known = {"obj-case": set(RULE_ET), "osaalus": {f.rule for f in FRAMES},
             "fraasid": set(PHRASE_RULES)}
    for u in units.UNITS:
        for r in u.revisits:
            assert set(r.rules) <= known[r.topic], (u.id, r)


def test_a_rule_above_its_stage_says_so():
    """The *da*-infinitive object and the plural partial subject are B2 in EKI's
    profile; a B1 unit that teaches them must say it."""
    for u in units.UNITS:
        for r in u.revisits:
            if {879, 1328} & set(r.eki):
                assert "B2" in r.note_ru, (u.id, r)


def test_first_words_are_words_vabamorf_knows():
    from eesti.morph import parts_of_speech

    words = units.words_for(units.by_id("tere"))
    assert len(words) >= 20
    assert all(parts_of_speech(w) for w in words)


def test_the_curriculum_carries_the_units(client):
    body = client.get("/api/curriculum").json()
    got = body["units"]
    assert [u["id"] for u in got][:2] == ["tere", "tutvume"]
    first = got[0]
    assert first["stage"] == "algus" and first["topics"] == ["tahestik", "fraasid", "arvud"]
    assert first["course_url"].endswith("/A/coursemap/list/1")
    assert first["words"] and all(w["et"] for w in first["words"])
    assert sum(u["current"] for u in got) == 1


def _master(conn, *topics):
    from eesti.progress import mark_mastered

    for t in topics:
        mark_mastered(conn, t, via="test")


def test_resume_follows_the_units(tmp_path):
    """After *põhivormid* the unit goes on to numbers (*Minu pere*), though the
    graph alone would offer the genitive stem first."""
    from eesti.progress import connect, resume

    conn = connect(tmp_path / "p.db")
    _master(conn, "tahestik", "fraasid", "arvud", "asesonad", "kusisonad", "olevik",
            "pohivormid")
    assert resume(conn) == "arvsonad"


@pytest.mark.parametrize("band,moved", [
    ("a1", {"algus"}),
    ("a1-a2", {"algus"}),
    ("a2", {"algus", "A1"}),
    ("a2-b1", {"algus", "A1", "A2"}),
])
def test_a_chosen_start_moves_past_earlier_stages(tmp_path, band, moved):
    from eesti.course import apply_start, skipped
    from eesti.progress import connect

    conn = connect(tmp_path / "p.db")
    apply_start(conn, {"start_band": band, "navigate": True}, "2026-10-09T00:00:00Z")
    expected = {t.id for t in TOPICS if units.stage_of(t.id) in moved}
    assert skipped(conn) == expected


def test_starting_from_the_beginning_moves_past_nothing(tmp_path):
    from eesti.course import apply_start, skipped
    from eesti.progress import connect

    conn = connect(tmp_path / "p.db")
    apply_start(conn, {"start_band": "a0", "navigate": True}, "2026-10-09T00:00:00Z")
    assert skipped(conn) == set()


def test_placement_does_not_probe_the_first_week(tmp_path):
    """The assessment is for learners who know some Estonian: it starts at A1."""
    from eesti.placement import candidates
    from eesti.progress import connect

    first = {t.id for t in candidates(connect(tmp_path / "p.db"))}
    assert not first & set(units.by_id("tere").topics)


def test_the_a1_checkpoint_waits_for_a1_not_the_first_week(tmp_path):
    """A learner who started at A1 and mastered its topics is ready for the
    checkpoint without the greetings week they moved past."""
    from eesti.checkpoint import ready, topics_at
    from eesti.progress import connect

    a1 = topics_at("A1")
    assert not set(a1) & set(units.by_id("tere").topics)
    conn = connect(tmp_path / "p.db")
    _master(conn, *a1)
    assert ready(conn, "A1")


def test_without_recordings_the_sound_topic_reads_as_reference(client):
    """No test-out or lesson is offered for what this server cannot play."""
    rows = {t["id"]: t for t in client.get("/api/curriculum").json()["topics"]}
    assert rows["tahestik"]["state"] == "reference" and not rows["tahestik"]["drillable"]


def test_with_recordings_it_is_a_topic_like_any(client, eki_recordings):
    rows = {t["id"]: t for t in client.get("/api/curriculum").json()["topics"]}
    assert rows["tahestik"]["drillable"] and rows["tahestik"]["state"] != "reference"


def test_a_learner_past_the_first_week_is_not_sent_back(tmp_path):
    """Someone who has mastered grammar (an existing learner, or one the
    assessment placed) goes on in the course, not to greetings."""
    from eesti.progress import connect, resume

    conn = connect(tmp_path / "p.db")
    _master(conn, "asesonad")
    assert units.stage_of(resume(conn)) != "algus"
    # The first week is still there to open: nothing was skipped.
    from eesti.course import skipped
    assert not skipped(conn)


def test_a_beginner_starts_with_the_first_week(tmp_path):
    from eesti.progress import connect, resume

    assert units.stage_of(resume(connect(tmp_path / "p.db"))) == "algus"
