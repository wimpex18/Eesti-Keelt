"""Cloze drills generated from authentic corpus sentences.

The danger with a corpus is the opposite of the danger with templates. Templates
produce nonsense that a reader spots immediately; a corpus produces fluent
Estonian whose *drill* may be unsound in ways nothing on screen reveals. So most
of these tests are about what must be refused.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import cloze


@pytest.fixture
def content(tmp_path):
    """A content store with a handful of real sentences, built from scratch.

    Deliberately not the developer's `data/content.db`: a test that passes only
    where the harvest has been run is a test that fails in CI for the wrong
    reason.
    """
    conn = sqlite3.connect(tmp_path / "content.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE items (id TEXT PRIMARY KEY, source_id TEXT, body TEXT);"
    )
    bodies = [
        "Ma elan Tallinnas. Ta läks eile kooli ja ostis uue raamatu poest.",
        "Riigikohus ei võtnud tema kaitsja kaebust arutusele.",
        "Kui rehvid on halvas seisundis, ei luba politsei juhtidel teekonda jätkata.",
        "Laeva, millega nad pidid merele minema, tabas tehniline rike.",
    ]
    conn.executemany(
        "INSERT INTO items (id, source_id, body) VALUES (?,?,?)",
        [(str(i), "selges-keeles", b) for i, b in enumerate(bodies)],
    )
    conn.commit()
    return conn


def test_sentences_respect_the_length_window(content):
    sents = cloze.sentences(content, min_words=5, max_words=20)
    assert sents
    assert all(5 <= len(s.split()) <= 20 for s in sents)


def test_sentences_come_only_from_the_named_source(content):
    assert cloze.sentences(content, source_id="err-r4") == []


class TestCaseClozes:
    def test_the_answer_is_the_word_the_native_wrote(self, content):
        for item in cloze.case_clozes(cloze.sentences(content), seed=1):
            assert item.solution.replace(cloze.BLANK, "") != item.prompt
            assert item.answer in item.solution

    def test_the_blank_replaces_exactly_one_word(self, content):
        for item in cloze.case_clozes(cloze.sentences(content), seed=1):
            assert item.prompt.count(cloze.BLANK) == 1

    def test_the_prompt_names_the_case_so_the_answer_is_forced(self, content):
        """The whole safety argument. Without the case named, the item would be
        asserting which case the sentence needed — which is semantics."""
        for item in cloze.case_clozes(cloze.sentences(content), seed=1):
            assert item.case_et and item.case_et in item.hint
            assert item.lemma in item.hint

    def test_grading_is_deterministic_and_case_insensitive(self, content):
        items = cloze.case_clozes(cloze.sentences(content), seed=1)
        assert items
        for item in items:
            assert item.check(item.answer)
            assert item.check(f"  {item.answer.upper()} ")
            assert not item.check(item.distractor)

    def test_answer_and_distractor_always_differ(self, content):
        for item in cloze.case_clozes(cloze.sentences(content), seed=1):
            assert item.answer != item.distractor

    def test_items_are_filed_against_a_real_curriculum_topic(self, content):
        from eesti.curriculum import by_id

        for item in cloze.case_clozes(cloze.sentences(content), seed=1):
            assert by_id(item.topic).generator == "corpus_cloze"

    def test_topic_filter_is_honoured(self, content):
        items = cloze.case_clozes(
            cloze.sentences(content), topics=("kohakaanded",), seed=1
        )
        assert items
        assert {i.topic for i in items} == {"kohakaanded"}

    def test_one_item_per_sentence(self, content):
        items = cloze.case_clozes(cloze.sentences(content), count=99, seed=1)
        blanked = [i.prompt.replace(cloze.BLANK, i.answer) for i in items]
        assert len(blanked) == len(set(blanked))

    def test_generation_is_reproducible_for_a_seed(self, content):
        sents = cloze.sentences(content)
        a = cloze.case_clozes(sents, seed=42)
        b = cloze.case_clozes(sents, seed=42)
        assert [i.to_dict() for i in a] == [i.to_dict() for i in b]


class TestNegationClozes:
    def test_only_negated_clauses_produce_items(self, content):
        items = cloze.negation_clozes(cloze.sentences(content), count=99, seed=1)
        assert items
        for item in items:
            clause_words = set()
            solution = item.solution
            lo, hi = cloze._clause_span(solution, solution.index(item.answer))
            clause_words = {w.strip(".,").lower() for w in solution[lo:hi].split()}
            assert clause_words & (cloze.NEGATORS | cloze._CONTRACTED)

    def test_the_negator_must_be_in_the_same_clause(self):
        """The bug this caught: a partitive in one clause was explained by an
        `ei` in another, teaching a connection that is not there."""
        sentence = (
            "Kui jahipidamisõigust tõendavad dokumendid on väljastatud, "
            "siis ei pea neid kaasas olema."
        )
        assert cloze.negation_clozes([sentence], count=5, seed=1) == []

    def test_the_answer_is_partitive_and_the_distractor_genitive(self, content):
        for item in cloze.negation_clozes(cloze.sentences(content), seed=1):
            assert item.case == "sg p"
            assert item.rule == "negation"
            assert item.answer != item.distractor

    def test_negation_items_are_filed_under_object_case(self, content):
        items = cloze.negation_clozes(cloze.sentences(content), seed=1)
        assert items and {i.topic for i in items} == {"obj-case"}


class TestSafetyGates:
    def test_naive_form_declines_to_guess_when_the_stem_does_not_fit(self):
        """None, not a made-up string: the nominative-stem model of the error
        only applies where the genitive really is a prefix of the form."""
        assert cloze.naive_case_form("meri", "mere", "merele") == "merile"
        assert cloze.naive_case_form("meri", "mere", "täiesti-muu") is None
        assert cloze.naive_case_form("meri", "mere", "mere") is None

    def test_ambiguous_lemmas_are_refused(self):
        """Naming the lemma in the prompt is what pins the answer, so a form two
        lemmas could produce cannot be used."""
        assert cloze._unambiguous_lemma("merele", "meri", "sg all")
        assert not cloze._unambiguous_lemma("merele", "mereleib", "sg all")

    def test_a_form_the_synthesiser_cannot_reproduce_is_refused(self):
        assert cloze._synthesises_back("meri", "sg all", "merele")
        assert not cloze._synthesises_back("meri", "sg all", "merile")

    def test_hyphenated_tokens_are_left_alone(self):
        s = "Selges keeles -žürii valib teksti."
        start = s.index("keeles")
        assert cloze._hyphenated(s, start, start + len("keeles"))
        s2 = "Ma elan Tallinnas praegu."
        start2 = s2.index("Tallinnas")
        assert not cloze._hyphenated(s2, start2, start2 + len("Tallinnas"))

    def test_the_partitive_distractor_is_the_genitive_not_a_naive_form(self):
        """For the object cases the contrast *is* the lesson; a mechanical
        nominative-plus-ending string would teach nothing."""
        forms = {"genitive": "raamatu", "partitive": "raamatut"}
        assert cloze._distractor("raamat", "sg p", "raamatut", forms) == "raamatu"
        assert cloze._distractor("raamat", "sg g", "raamatu", forms) == "raamat"

    def test_every_declared_case_has_a_topic_and_a_name(self):
        covered = {tag for tags in cloze.TOPIC_CASES.values() for tag in tags}
        assert covered == set(cloze.CASES)

    def test_the_topics_it_files_under_are_the_ones_that_dispatch_here(self):
        """`TOPIC_CASES` is a hand-written map into the syllabus, and the
        syllabus is where a topic's generator is declared. A key that is not a
        `corpus_cloze` topic is a case this module will never be asked for —
        the same disconnect that left the negation lane unreachable, one file
        further along."""
        from eesti.curriculum import by_id

        for topic in cloze.TOPIC_CASES:
            assert by_id(topic).generator == "corpus_cloze", topic

    def test_every_corpus_topic_has_cases_to_ask_for(self):
        """And the other direction: a topic routed here with no tags in
        `TOPIC_CASES` returns an empty set for every seed, silently."""
        from eesti.curriculum import TOPICS

        routed = {t.id for t in TOPICS if t.generator == "corpus_cloze"}
        assert routed == set(cloze.TOPIC_CASES)


def test_items_carry_their_handbook_reference(content):
    """Reference and exercise ship together, or the learner has to go looking."""
    items = cloze.negation_clozes(cloze.sentences(content), seed=1)
    assert items
    for item in items:
        ref = item.reference
        assert ref and ref["known"]
        assert ref["ekk_section"] == "SÜ 37"
        assert item.to_dict()["reference"] == ref


def test_untagged_topics_report_no_reference_rather_than_a_wrong_one(content):
    items = cloze.case_clozes(
        cloze.sentences(content), topics=("harvad-kaanded",), seed=1
    )
    for item in items:
        assert item.reference is None


class TestTheNegationLaneReachedNobody:
    """`negation_clozes` was generated, tested, filed under `obj-case` — and
    never ran outside the CLI.

    `items_for` dispatches on `by_id(topic).generator`. The call sat inside the
    `generator == "corpus_cloze"` branch, guarded by `topic == "obj-case"`; but
    `obj-case`'s generator is `object_case`, so that comparison could not be
    true. A generator with no caller, this project's most-repeated bug shape,
    and this time on the topic `docs/status.md` names as the documented #1
    weakness: negation is the *one* object-case rule a corpus sentence settles
    on its own, so the learner's only authentic obj-case material was the half
    that never shipped.
    """

    def test_an_object_case_set_contains_authentic_sentences(self):
        from eesti.cloze import Cloze
        from eesti.practice import items_for

        items = items_for("obj-case", count=9, seed=1)
        assert any(isinstance(i, Cloze) and i.rule == "negation" for i in items), (
            "obj-case is back to templates only")

    def test_the_set_is_still_the_size_that_was_asked_for(self):
        """Blending must not cost items. The corpus share replaces frames, it
        does not shrink the lesson."""
        from eesti.practice import items_for

        assert len(items_for("obj-case", count=9, seed=1)) == 9

    def test_the_templates_still_carry_most_of_it(self, monkeypatch):
        """The frames supply the completed/ongoing contrast a corpus sentence
        leaves implicit, which is the topic's actual subject. Negation is the
        supplement, not the lesson.

        Asked of the *request*, not of the result. The fixture corpus is four
        short passages and yields two negation items for a set of nine, so
        counting what came back would pass however large the share was asked
        to be — a guard that holds for a reason unrelated to what it claims.
        """
        from eesti import cloze
        from eesti.practice import CORPUS_SHARE, items_for

        asked = []
        real = cloze.negation_clozes
        monkeypatch.setattr(cloze, "negation_clozes",
                            lambda *a, count, **kw: asked.append(count)
                            or real(*a, count=count, **kw))
        items_for("obj-case", count=9, seed=1)
        assert asked == [9 // CORPUS_SHARE]

    def test_no_corpus_still_gives_a_full_lesson(self, tmp_path, monkeypatch):
        """A deployment without `content.db` had this topic yesterday and must
        still have it. `sqlite3.connect` happily opens a path that is not a
        database yet, and the failure only arrives at the first SELECT."""
        from eesti import config
        from eesti.practice import items_for

        monkeypatch.setattr(config, "CONTENT_DB", tmp_path / "absent.db")
        assert len(items_for("obj-case", count=9, seed=1)) == 9

    def test_a_branch_never_tests_a_topic_its_generator_cannot_own(self):
        """The shape of the bug, asked of `items_for` as a whole.

        Derived from the curriculum rather than written out here: every
        `topic == "x"` inside an `if generator == "y"` block is a claim that
        `x` is generated by `y`, and `curriculum.py` is where that is decided.
        """
        import ast
        import inspect

        from eesti import practice
        from eesti.curriculum import by_id

        tree = ast.parse(inspect.getsource(practice.items_for).lstrip())

        def compared(node, name):
            out = []
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Compare)
                        and isinstance(sub.left, ast.Name) and sub.left.id == name
                        and len(sub.comparators) == 1
                        and isinstance(sub.comparators[0], ast.Constant)):
                    out.append(sub.comparators[0].value)
            return out

        checked = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            generators = compared(node.test, "generator")
            if len(generators) != 1:
                continue
            for topic in {t for stmt in node.body for t in compared(stmt, "topic")}:
                checked += 1
                assert by_id(topic).generator == generators[0], (
                    f"`{topic}` is dispatched inside the "
                    f"`{generators[0]}` branch, but its generator is "
                    f"`{by_id(topic).generator}` — that branch never runs")
        assert checked, "no topic branches found; the parse stopped working"
