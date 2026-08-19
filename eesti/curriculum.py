"""The syllabus as data: topics, what they need first, and what drills them.

This is the spine of the learning path. It declares nothing about the UI and
runs nothing; it says **what there is to learn, in what order the language
itself permits, and which generator can produce practice for it.**

Why a graph rather than a list
------------------------------
Estonian makes prerequisite ordering unusually real. Every case except nominative
and partitive is built from the **genitive stem**, so a learner who cannot form
`raamatu` cannot form eleven other cases either. That is not a pedagogical
opinion to be argued about — it is how the morphology works. So the order comes
out of a dependency graph instead of being hand-sequenced, and `order()` derives
it. Where the language imposes no dependency, none is invented: topics with the
same prerequisites are free to be taken in any order, and the tie is broken by
how often learners actually get them wrong.

Where the levels come from
--------------------------
The A1 and B1 topic sets are the ones in `docs/curriculum-plan.md` Part 1, taken
from Estonian course curricula that agree because they track the same state
standard. **A2 is a judgement call**, and worth flagging as one: the sources
tabulate A1 and B1, so the topics conventionally taught in between — conditional,
perfect, comparison, ordinals — are placed at A2 here. If that split is wrong it
is wrong in the direction of seeing a topic slightly early, which the mastery
gate (step 3) absorbs.

`generator=None` is not an oversight
------------------------------------
Most topics have no generator yet — that is the honest state of the app, and
step 2 of the plan is precisely the work of filling them in. Declaring the topic
anyway is what lets `coverage()` report the gap instead of hiding it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import LEVELS, TAGS
from .grammar import REFERENCES

# How often each error tag is annotated in EVKK's learner corpus, as a share of
# the 51 467 marks it publishes. A recorded snapshot (2026-08), used only to
# break ties between topics the graph leaves unordered — never as a claim about
# this learner. `python -m eesti.cli evkk` recomputes it from the live page.
#
# It is a share of *annotations*, not of learner errors: parent categories
# absorb marks a finer child would have taken, and 40.7 % of marks fall outside
# these nine tags entirely. Good enough to order two topics; not good enough to
# quote.
CORPUS_WEIGHT: dict[str, float] = {
    "vocab": 24.2,
    "word-order": 11.4,
    "rektsioon": 10.0,
    "verb-form": 4.6,
    "gen-stem": 3.0,
    "ma-da-inf": 2.2,
    "loc-case": 1.6,
    "obj-case": 1.3,
    "gradation": 0.8,
}


@dataclass(frozen=True)
class Topic:
    """One thing to learn, and everything needed to schedule it."""

    id: str
    level: str                      # A1 | A2 | B1
    et: str                         # the Estonian name, which is what the exam uses
    ru: str                         # how a Russian-speaking learner will look for it
    requires: tuple[str, ...] = ()  # topic ids that must come first
    tag: str | None = None          # error-log tag, where one covers this topic
    generator: str | None = None    # drill generator; None = not built yet
    note: str = ""

    @property
    def reference(self):
        """The EKK handbook entry, when the topic maps onto a tagged rule."""
        return REFERENCES.get(self.tag) if self.tag else None

    @property
    def weight(self) -> float:
        return CORPUS_WEIGHT.get(self.tag or "", 0.0)


# --------------------------------------------------------------------------
# A1 — the foundation. Nothing here may depend on anything at a higher level.
# --------------------------------------------------------------------------
_A1: tuple[Topic, ...] = (
    Topic("tahestik", "A1", "tähestik ja hääldamine", "алфавит и произношение",
          note="Reference only — EKI publishes free pronunciation exercises."),
    Topic("lauseehitus", "A1", "lauseehitus", "строение предложения"),
    Topic("asesonad", "A1", "asesõnad", "местоимения"),
    Topic("kusisonad", "A1", "küsisõnad", "вопросительные слова",
          requires=("lauseehitus",), generator="patterns"),
    Topic("pohivormid", "A1", "nimisõna põhivormid", "основные формы имени",
          note="nimetav, omastav, osastav — the three forms a dictionary gives."),
    Topic("gen-stem", "A1", "omastava tüvi", "основа генитива",
          requires=("pohivormid",), tag="gen-stem", generator="corpus_cloze",
          note="The keystone: eleven further cases are built from this stem."),
    Topic("osastav", "A1", "osastav kääne", "партитив",
          requires=("pohivormid",), generator="corpus_cloze"),
    Topic("astmevaheldus", "A1", "astmevaheldus", "чередование ступеней",
          requires=("gen-stem",), tag="gradation"),
    Topic("mitmus", "A1", "ainsus ja mitmus", "единственное и множественное",
          requires=("gen-stem",), generator="corpus_cloze"),
    Topic("eitus", "A1", "eitus", "отрицание", requires=("osastav",)),
    Topic("olevik", "A1", "olevik", "настоящее время", generator="conjugation"),
    Topic("verb-form", "A1", "verbi põhivormid", "основные формы глагола",
          requires=("olevik",), tag="verb-form", generator="verb_stems"),
    Topic("lihtminevik", "A1", "lihtminevik", "простое прошедшее",
          requires=("verb-form",), generator="conjugation"),
    Topic("ma-da-inf", "A1", "ma- ja da-tegevusnimi", "ma- и da-инфинитив",
          requires=("verb-form",), tag="ma-da-inf", generator="conjugation"),
    Topic("kohakaanded", "A1", "kohakäänded", "местные падежи",
          requires=("gen-stem",), tag="loc-case", generator="corpus_cloze"),
    Topic("obj-case", "A1", "täissihitis ja osasihitis", "полное и частичное дополнение",
          requires=("gen-stem", "osastav", "eitus"), tag="obj-case",
          generator="object_case",
          note="The documented personal weakness. 1.3 % of corpus errors, "
               "first priority here anyway — the log outranks the average. "
               "Templates supply the aspect contrast; the corpus supplies the "
               "negation rule, which is the half it can settle on its own."),
    Topic("arvsonad", "A1", "põhiarvsõnad", "количественные числительные",
          requires=("pohivormid",), generator="patterns"),
    Topic("kaassonad", "A1", "kaassõnad", "пред- и послелоги",
          requires=("gen-stem",)),
    Topic("sidesonad", "A1", "sidesõnad", "союзы", requires=("lauseehitus",)),
    Topic("maarsonad", "A1", "määrsõnad", "наречия"),
)

# --------------------------------------------------------------------------
# A2 — the conventional middle. See the module docstring: this split is ours.
# --------------------------------------------------------------------------
_A2: tuple[Topic, ...] = (
    Topic("kaskiv", "A2", "käskiv kõneviis", "повелительное наклонение",
          requires=("verb-form",), generator="conjugation"),
    Topic("tingiv", "A2", "tingiv kõneviis", "условное наклонение",
          requires=("verb-form",), generator="conjugation"),
    Topic("kesksonad", "A2", "kesksõnad", "причастия", requires=("verb-form",),
          generator="conjugation"),
    Topic("taisminevik", "A2", "täisminevik", "перфект",
          requires=("kesksonad", "olevik"), generator="conjugation"),
    Topic("vordlusastmed", "A2", "võrdlusastmed", "степени сравнения",
          requires=("gen-stem",), generator="patterns"),
    Topic("jargarvud", "A2", "järgarvud", "порядковые числительные",
          requires=("arvsonad", "gen-stem"), generator="patterns"),
    Topic("harvad-kaanded", "A2", "saav, rajav, olev, ilmaütlev, kaasaütlev",
          "транслатив, терминатив, эссив, абессив, комитатив",
          requires=("gen-stem",), generator="corpus_cloze"),
    Topic("tulevik", "A2", "tuleviku väljendamine", "выражение будущего",
          requires=("olevik",),
          note="Estonian has no future tense; it is expressed by other means."),
)

# --------------------------------------------------------------------------
# B1 — what the exam adds.
# --------------------------------------------------------------------------
_B1: tuple[Topic, ...] = (
    Topic("uhildumine", "B1", "ühildumine", "согласование",
          requires=("mitmus", "kohakaanded")),
    Topic("enneminevik", "B1", "enneminevik", "плюсквамперфект",
          requires=("taisminevik", "lihtminevik"), generator="conjugation"),
    Topic("umbisikuline", "B1", "umbisikuline tegumood", "безличный залог",
          requires=("kesksonad",), generator="conjugation"),
    Topic("rektsioon", "B1", "rektsioon", "управление глагола",
          requires=("kohakaanded",), tag="rektsioon", generator="ekk_rection",
          note="Second-largest error class in the learner corpus (10.0 %), and "
               "sonapi already returns the rection of any verb."),
    Topic("sonajark", "B1", "sõnajärg", "порядок слов",
          requires=("lauseehitus",), tag="word-order",
          generator="wordorder",
          note="11.4 % of all EVKK marks and 19.3 % of the marks these nine "
               "tags cover — second only to vocabulary either way, and until "
               "now the largest tag with no drill at all. Items are attested "
               "learner corrections, never generated: see eesti/wordorder.py "
               "for the measurement that ruled generation out."),
    Topic("uhendverbid", "B1", "ühendverbid", "фразовые глаголы",
          requires=("verb-form", "obj-case")),
    Topic("liitsonad", "B1", "liitsõnad", "сложные слова",
          requires=("gen-stem",)),
    Topic("kirjavahemargid", "B1", "kirjavahemärgid", "пунктуация",
          requires=("lauseehitus",)),
)

TOPICS: tuple[Topic, ...] = _A1 + _A2 + _B1

_BY_ID: dict[str, Topic] = {t.id: t for t in TOPICS}


def by_id(topic_id: str) -> Topic:
    return _BY_ID[topic_id]


def at_level(level: str) -> tuple[Topic, ...]:
    return tuple(t for t in TOPICS if t.level == level)


def validate() -> None:
    """Fail loudly on a malformed graph. Called by the tests, cheap enough to call anywhere.

    A dangling prerequisite or a cycle would make `order()` silently drop topics,
    which is exactly the kind of quiet omission a syllabus must not have.
    """
    seen: set[str] = set()
    for topic in TOPICS:
        if topic.id in seen:
            raise ValueError(f"duplicate topic id: {topic.id}")
        seen.add(topic.id)
        if topic.level not in LEVELS:
            raise ValueError(f"{topic.id}: unknown level {topic.level!r}")
        if topic.tag is not None and topic.tag not in TAGS:
            raise ValueError(f"{topic.id}: unknown tag {topic.tag!r}")

    for topic in TOPICS:
        for need in topic.requires:
            if need not in _BY_ID:
                raise ValueError(f"{topic.id} requires unknown topic {need!r}")
            if LEVELS.index(_BY_ID[need].level) > LEVELS.index(topic.level):
                raise ValueError(
                    f"{topic.id} ({topic.level}) requires {need} "
                    f"({_BY_ID[need].level}) from a higher level"
                )
    order()  # raises on a cycle


_DECLARED: dict[str, int] = {t.id: i for i, t in enumerate(TOPICS)}


def order(topics: tuple[Topic, ...] = TOPICS) -> list[Topic]:
    """The study path: what the graph permits, sequenced the way a course would.

    Kahn's algorithm with a sorted ready set — level first, then **declaration
    order**, which is the authored textbook sequence in the tables above.

    Declaration order is the tie-break rather than corpus weight, because the two
    answer different questions and mixing them produced nonsense: weighting the
    path by error frequency put irregular verb stems before the genitive and left
    the alphabet until last. *What to learn next* is a sequencing question the
    course curricula already answer; *what to practise hardest* is what error
    frequency answers, and that is `practice_order()`.

    The graph stays the hard constraint. Declaration order only chooses among
    topics it has left genuinely free, so reordering the tables can never produce
    a sequence that teaches a case before the stem it is built from.
    """
    pending = {t.id: set(t.requires) & {x.id for x in topics} for t in topics}
    pool = {t.id: t for t in topics}
    done: list[Topic] = []

    def rank(tid: str) -> tuple[int, int]:
        t = pool[tid]
        return (LEVELS.index(t.level), _DECLARED[t.id])

    while pending:
        ready = sorted((tid for tid, need in pending.items() if not need), key=rank)
        if not ready:
            raise ValueError(f"prerequisite cycle among: {sorted(pending)}")
        first = ready[0]
        done.append(pool[first])
        del pending[first]
        for need in pending.values():
            need.discard(first)
    return done


def available(known: set[str], topics: tuple[Topic, ...] = TOPICS) -> list[Topic]:
    """Topics whose prerequisites are all satisfied and which are not yet known.

    This is what "where do I go next" resolves to, and what a skipped topic
    unlocks — skipping is just adding to `known` without doing the lesson.
    """
    return [
        t for t in order(topics)
        if t.id not in known and set(t.requires) <= known
    ]


def practice_order(topics: list[Topic] | tuple[Topic, ...] = TOPICS) -> list[Topic]:
    """The same topics ranked by how much trouble they cause, not by sequence.

    Answers "which of the things I could study now is worth the most practice"
    and "which generator should be built next" — the question `CORPUS_WEIGHT`
    is actually evidence for. Untagged topics carry weight 0 and fall to the
    back, in path order, so the ranking degrades to the sequence rather than to
    noise.
    """
    return sorted(order(tuple(topics)), key=lambda t: (-t.weight, _DECLARED[t.id]))


def blocked_by(topic_id: str, known: set[str]) -> list[str]:
    """Which prerequisites are still missing — the reason a topic is not offered."""
    return sorted(set(by_id(topic_id).requires) - known)


def unlocks(topic_id: str) -> list[str]:
    """Everything that depends on this topic, transitively.

    `gen-stem` unlocks most of the noun system, which is the argument for
    teaching it before anything that uses a stem.
    """
    found: set[str] = set()
    frontier = {topic_id}
    while frontier:
        frontier = {
            t.id for t in TOPICS
            if t.id not in found and frontier & set(t.requires)
        }
        found |= frontier
    return sorted(found)


def coverage(topics: tuple[Topic, ...] = TOPICS) -> dict[str, int]:
    """How much of the declared syllabus can actually be practised today."""
    return {
        "topics": len(topics),
        "with_generator": sum(1 for t in topics if t.generator),
        "with_reference": sum(1 for t in topics if t.reference is not None),
    }
