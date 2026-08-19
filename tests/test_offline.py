"""Practice must never touch the network.

The claim in the README is that vocabulary, morphology, drill generation and
grading depend on no third-party service. CI caught that claim being false:
`items_for("rektsioon")` fetched EKK's page on demand, and a GitHub runner got
`403 Forbidden`, so a drill failed because someone else's server was having a
bad minute.

These tests block the network outright and then exercise every generator, so the
claim is enforced rather than asserted in a docstring.
"""

from __future__ import annotations

import socket
import urllib.request

import pytest

from eesti.curriculum import TOPICS
from eesti.practice import items_for

DRILLABLE = [t.id for t in TOPICS if t.generator]


@pytest.fixture
def no_network(monkeypatch):
    """Any attempt to open a socket or a URL fails loudly."""
    def forbidden(*args, **kwargs):
        raise AssertionError("this code path tried to use the network")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    return True


def test_there_are_enough_generators_to_make_this_meaningful():
    assert len(DRILLABLE) >= 20


@pytest.mark.parametrize("topic", DRILLABLE)
def test_every_generator_runs_offline(no_network, topic):
    """No generator may reach the network.

    An *empty* result is allowed and is not what this test is about: the fixture
    corpus is four short passages, so the plural and rare-case cloze generators
    legitimately find nothing to blank. What must never happen is a socket.
    """
    items = items_for(topic, count=2, seed=1)
    for item in items:
        assert item.check(item.answer)


@pytest.mark.parametrize(
    "topic",
    ["obj-case", "verb-form", "tingiv", "olevik", "lihtminevik", "kusisonad",
     "arvsonad", "rektsioon", "gen-stem"],
)
def test_the_core_generators_also_produce_items_offline(no_network, topic):
    """Separate from the sweep above, because "did not crash" and "produced a
    drill" are different claims and only one of them is about the network."""
    assert items_for(topic, count=2, seed=1)


def test_rections_are_read_from_storage_not_fetched(no_network):
    """The specific failure: a lesson depended on EKI being reachable."""
    items = items_for("rektsioon", count=1, seed=1)
    assert items


def test_a_missing_rection_table_says_what_to_run(monkeypatch, no_network):
    from eesti import practice

    monkeypatch.setattr("eesti.rection.load", lambda conn: [])
    with pytest.raises(ValueError, match="cli rections"):
        practice.items_for("rektsioon", count=1)


def test_grading_never_needs_the_network(no_network):
    for topic in ("obj-case", "verb-form", "tingiv", "kusisonad"):
        for item in items_for(topic, count=3, seed=2):
            assert item.check(item.answer)
            assert not item.check(item.distractor)


def test_reference_data_paths_honour_the_config(fixture_data):
    """A path frozen at import cannot be redirected.

    This has now caused three separate failures — `wordlist.connect`,
    `practice._content`, and `app.CONTENT_DB` — each time passing locally
    because the developer's `data/` exists and failing in CI because a runner's
    does not. The rule: **reference data** (the word list, the harvested
    content) resolves through `eesti.config` when called. Learner *state*
    (progress, review, vocab) may keep literal defaults, since those are
    per-deployment settings a caller overrides explicitly.
    """
    from eesti import app as app_module
    from eesti import config

    assert app_module.content_db().execute(
        "SELECT COUNT(*) FROM items"
    ).fetchone()[0] > 0
    assert str(config.CONTENT_DB) == str(fixture_data["content"])


def test_the_web_app_reads_the_redirected_content(fixture_data):
    """The endpoint that caught it: read-aloud sentences come from the corpus,
    and returned an empty list in CI while passing locally."""
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from eesti.app import app

    items = TestClient(app).get("/api/speaking/readaloud?kind=lause&n=3").json()
    assert items["items"], "read-aloud found no sentences in the fixture corpus"
