"""The syllabus as data: topics, what they need first, and what drills them.

Declares what there is to learn, in the order the language permits, and which
generator practises it; no UI, no execution.

**A graph, not a list.** Every case except nominative and partitive is built on
the genitive stem, so prerequisites are real; `order()` derives the path.

**Levels.** A1 and B1 topic sets follow Estonian course curricula
(`docs/curriculum.md`). A2 placement (conditional, perfect, comparison,
ordinals) is a judgement call; the mastery gate absorbs a slightly early topic.

**`generator=None`** marks a topic with no drill yet, so `coverage()` can report
the gap.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import LEVELS, TAGS
from .grammar import REFERENCES, TOPIC_REFERENCES

# EVKK annotation share per error tag: a recorded snapshot used only to break ties
# the graph leaves free (`python -m eesti.cli evkk` recomputes it). Annotation
# shares, not error rates.
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
        """The EKK handbook entry: the tagged rule's if there is one (written for
        a mistake), else the topic's own. Same order as `grammar.reference_for`.
        """
        by_tag = REFERENCES.get(self.tag) if self.tag else None
        return by_tag or TOPIC_REFERENCES.get(self.id)

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
          note="nimetav, omastav, osastav — the three forms a dictionary gives.",
          generator="forms"),
    Topic("gen-stem", "A1", "omastava tüvi", "основа генитива",
          requires=("pohivormid",), tag="gen-stem", generator="corpus_cloze",
          note="The keystone: eleven further cases are built from this stem."),
    Topic("osastav", "A1", "osastav kääne", "партитив",
          requires=("pohivormid",), generator="corpus_cloze"),
    Topic("astmevaheldus", "A1", "astmevaheldus", "чередование ступеней",
          requires=("gen-stem",), tag="gradation"),
    Topic("mitmus", "A1", "ainsus ja mitmus", "единственное и множественное",
          requires=("gen-stem",), generator="corpus_cloze"),
    Topic("eitus", "A1", "eitus", "отрицание", requires=("osastav",),
          generator="forms"),
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
          requires=("mitmus", "kohakaanded"), generator="forms"),
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
               "tags cover — second only to vocabulary either way. Items are attested "
               "learner corrections, never generated: see eesti/wordorder.py "
               "for the measurement that ruled generation out. Corroborated "
               "by EstGEC-L2, a second L2 corpus annotated "
               "independently of EVKK: `R:WO` is its second-largest error tag, "
               "872 edits in 2 029 sentences. Two corpora, two methods, both "
               "putting word order at the top."),
    Topic("uhendverbid", "B1", "ühendverbid", "фразовые глаголы",
          requires=("verb-form", "obj-case")),
    Topic("liitsonad", "B1", "liitsõnad", "сложные слова",
          requires=("gen-stem",)),
    Topic("kirjavahemargid", "B1", "kirjavahemärgid", "знаки препинания",
          requires=("lauseehitus",), generator="punctuation",
          note="Only the comma before a subordinate clause is drilled, and "
               "only before `et` and `sest`. Measured across 1 349 native "
               "texts: those two are preceded by a comma 99 % and 96 % of the "
               "time, while `kui` is 38 % and `nagu` 64 % — those are not "
               "rules and drilling them would teach a learner to insert "
               "commas into correct Estonian."),
)

TOPICS: tuple[Topic, ...] = _A1 + _A2 + _B1

_BY_ID: dict[str, Topic] = {t.id: t for t in TOPICS}


def by_id(topic_id: str) -> Topic:
    return _BY_ID[topic_id]


def at_level(level: str) -> tuple[Topic, ...]:
    return tuple(t for t in TOPICS if t.level == level)


def validate() -> None:
    """Fail loudly on a malformed graph: a dangling prerequisite or a cycle would make
    `order()` drop topics silently.
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

    Kahn's algorithm with a sorted ready set — level first, then declaration order
    (the textbook sequence in the tables above). Error frequency answers a
    different question, in `practice_order()`. The graph stays the hard constraint.
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
    """Topics whose prerequisites are satisfied and which are not yet known; skipping a
    topic is adding it to `known`.
    """
    return [
        t for t in order(topics)
        if t.id not in known and set(t.requires) <= known
    ]


def practice_order(topics: list[Topic] | tuple[Topic, ...] = TOPICS) -> list[Topic]:
    """The same topics ranked by corpus error weight (`CORPUS_WEIGHT`), for "what to
    practise hardest"; untagged topics fall back to path order.
    """
    return sorted(order(tuple(topics)), key=lambda t: (-t.weight, _DECLARED[t.id]))


def blocked_by(topic_id: str, known: set[str]) -> list[str]:
    """Which prerequisites are still missing — the reason a topic is not offered."""
    return sorted(set(by_id(topic_id).requires) - known)


def unlocks(topic_id: str) -> list[str]:
    """Everything that depends on this topic, transitively."""
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


# --------------------------------------------------------------------------
# How each topic is represented in the app
# --------------------------------------------------------------------------
#
# A topic is learnt through whatever the app has for it, not only a generator:
#
# | Kind | Meaning |
# |---|---|
# | `generator:<name>` | drills generated and graded by code |
# | `reference` | an EKK handbook section to read |
# | `contextual` | reading texts linked to it (`topiclinks.py`) |
# | `cross:<topic>` | practised inside another topic's drills |
# | `assessment:checkpoint` | asked in the end-of-level checkpoint |
#
# Every topic has at least one, or a stated reason in `REPRESENTATION_GAPS`.

#: Topics practised inside another topic's drills. Only where the other drill
#: really exercises this one.
CROSS: dict[str, str] = {
    # Its contrast is drilled as the genitive stem (`docs/status.md`).
    "astmevaheldus": "gen-stem",
    # Word-order items are whole sentences corrected by learners (EVKK, EstGEC-L2).
    "lauseehitus": "sonajark",
}

#: Topics with nothing yet, and why. Filling one removes its line; a test holds
#: this list and the derived one together.
REPRESENTATION_GAPS: dict[str, str] = {
    "tahestik": "alphabet and sounds: needs audio exercises; EKI publishes them",
    "asesonad": "Vabamorf's pronoun paradigms are wrong; needs a cited table",
    "kaassonad": "no EKK section linked yet; attested corpus clozes not built",
    "sidesonad": "no EKK section linked yet; attested corpus clozes not built",
    "maarsonad": "no EKK section linked yet",
    "tulevik": "no EKK section linked yet; a generator is possible (Vabamorf)",
    "uhendverbid": "too few marked corpus examples; needs EKI usage examples",
    "liitsonad": "too few marked corpus examples",
}


def representations(topic: Topic) -> list[str]:
    """What the app offers for a topic, derived from what exists."""
    from .topiclinks import LABEL_TOPICS, LINKABLE

    out = []
    if topic.generator:
        out += [f"generator:{topic.generator}", "assessment:checkpoint"]
    if topic.reference is not None:
        out.append("reference")
    if topic.id in LINKABLE or topic.id in LABEL_TOPICS:
        out.append("contextual")
    if topic.id in CROSS:
        out.append(f"cross:{CROSS[topic.id]}")
    return out
