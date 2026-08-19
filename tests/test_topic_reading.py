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


class TestLessonLabels:
    """Two thirds of the ERR archive is audio with no transcript.

    Those episodes looked like empty rows, and the first version of this feature
    skipped them entirely — there is nothing to analyse. But every one carries
    the teacher's own one-line label saying which grammar point it teaches, and
    lessons 22 and 23 of the second course are precisely the completed and
    incomplete object contrast: the documented weakness this app exists for.

    A label is stronger evidence than a derived link. "This lesson is about the
    object case in completed actions" is someone stating the subject; three
    genitive objects going past in a news article is a program noticing a
    pattern. So labels outrank, and they are read, never guessed.
    """

    def test_the_object_case_lessons_are_recognised(self):
        from eesti.library import labelled_topics

        assert labelled_topics(
            "Урок 22. Падеж дополнения в законченном действии."
        ) == ["obj-case"]
        assert labelled_topics(
            "Урок 23. Падеж дополнения в незаконченном действии."
        ) == ["obj-case"]

    def test_a_lesson_naming_two_topics_is_linked_to_both(self):
        from eesti.library import labelled_topics

        found = labelled_topics(
            "Урок 8. Полное прошедшее время/Täisminevik и "
            "Предпрошедшее время/Enneminevik глаголов."
        )
        assert set(found) == {"taisminevik", "enneminevik"}

    def test_an_estonian_term_is_matched_on_its_own(self):
        from eesti.library import labelled_topics

        assert labelled_topics("Урок 27. Rektsioon. Управление.") == ["rektsioon"]

    def test_an_unrelated_label_names_nothing(self):
        """Matching loosely would fill every topic with irrelevant audio."""
        from eesti.library import labelled_topics

        assert labelled_topics("Урок 30. Проверочная работа.") == []

    def test_every_labelled_topic_is_a_real_curriculum_topic(self):
        """A typo here would create a link nothing can ever ask for."""
        from eesti.curriculum import TOPICS
        from eesti.library import LABEL_TOPICS

        assert set(LABEL_TOPICS) <= {t.id for t in TOPICS}

    def test_a_labelled_episode_outranks_a_demonstrating_text(self, corpus, words):
        """Ordering is the whole point: when obj-case keeps going wrong, the
        lesson about it should come before an article that happens to use it."""
        from eesti.library import link_labelled, link_topics, related

        corpus.execute(
            "UPDATE items SET meta = ? WHERE title = ?",
            ('{"summary": "Урок 22. Падеж дополнения в законченном действии."}',
             "Tervitused"),
        )
        corpus.commit()
        link_topics(corpus, words, topics=("obj-case",))
        link_labelled(corpus)

        ranked = related(corpus, "obj-case", limit=5)
        assert ranked[0]["title"] == "Tervitused"
