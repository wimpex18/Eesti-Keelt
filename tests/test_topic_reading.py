"""The join between a grammar topic and something to read.

The plan called this "what makes it one tool rather than four", and it was the
one MVP item that never got built. Practice on its own is a drill machine; a
reading list on its own is a folder of texts. The value is in *"you keep missing
the completed-object contrast — here is an episode that is about it."*

The link is earned rather than asserted: a text is offered for a topic only if
the topic's own generator can cut a valid exercise out of it. So the claim has
already been checked by the machinery that refuses ambiguous cases, instead of
being a label somebody typed.
"""

from __future__ import annotations

import pytest

from eesti.library import MIN_HITS, link_topics, related
from eesti.sources import Item, add_items, connect, register


@pytest.fixture
def corpus(tmp_path):
    """Two texts: one that drills the object contrast, one that cannot."""
    conn = connect(tmp_path / "content.db")
    register(conn)
    source = conn.execute("SELECT id FROM sources LIMIT 1").fetchone()["id"]
    add_items(conn, [
        Item(
            source_id=source, skill="lugemine", level="B1",
            title="Lõpetatud tegevus",
            # Every sentence uses a noun whose genitive and partitive differ,
            # because a noun with identical object forms demonstrates nothing —
            # which is exactly the bar `has_distinct_object_cases` enforces.
            body=(
                "Ma lugesin raamatu läbi ja panin selle riiulile. "
                "Ta ostis auto ära ning sõitis sellega koju. "
                "Me lõpetasime töö valmis ja läksime puhkama. "
                "Ta ostis pileti ära ning astus rongi peale. "
                "Poiss parandas arvuti korda ja pani laua peale. "
                "Õpetaja kirjutas lause tahvlile ja luges ette."
            ),
        ),
        Item(
            source_id=source, skill="lugemine", level="A1",
            title="Tervitused",
            body="Tere. Head aega. Palun. Aitäh. Vabandust.",
        ),
    ])
    return conn


@pytest.fixture
def words():
    from eesti.wordlist import connect as wordlist_connect

    return wordlist_connect()


class TestLinking:
    def test_a_text_that_demonstrates_the_topic_is_offered(self, corpus, words):
        link_topics(corpus, words, topics=("obj-case",))
        titles = [r["title"] for r in related(corpus, "obj-case", limit=5)]
        assert "Lõpetatud tegevus" in titles

    def test_a_text_that_does_not_is_never_offered(self, corpus, words):
        """Five one-word greetings contain no object at all. Offering them as
        reading for the object contrast would be worse than offering nothing."""
        link_topics(corpus, words, topics=("obj-case",))
        titles = [r["title"] for r in related(corpus, "obj-case", limit=5)]
        assert "Tervitused" not in titles

    def test_relinking_replaces_rather_than_accumulates(self, corpus, words):
        """A re-harvest must not leave the previous run's links behind."""
        link_topics(corpus, words, topics=("obj-case",))
        first = related(corpus, "obj-case", limit=10)
        link_topics(corpus, words, topics=("obj-case",))
        assert related(corpus, "obj-case", limit=10) == first

    def test_an_unlinked_topic_returns_nothing_rather_than_failing(
        self, corpus, words
    ):
        link_topics(corpus, words, topics=("obj-case",))
        assert related(corpus, "tingiv") == []

    def test_the_threshold_is_a_real_bar(self):
        """One passing mention is not a text about the contrast."""
        assert MIN_HITS >= 3


class TestLicence:
    def test_owner_only_material_is_withheld_from_a_public_view(
        self, corpus, words
    ):
        """A follow-up suggestion is still a way of serving a text, so the
        licence check has to apply here too, not only to the library list."""
        link_topics(corpus, words, topics=("obj-case",))
        assert related(corpus, "obj-case", limit=5)          # owner sees them
        public = related(corpus, "obj-case", limit=5, public_only=True)
        assert all(r["licence"] for r in public)
