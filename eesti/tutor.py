"""The bounded tutor: one place a model is allowed to speak to the learner.

Every intent here is the same shape — grounded context assembled by code, one
model call through the existing chain, and an answer that names its engine. The
tutor explains; it never decides whether an answer was right, never supplies a
form, and never writes to mastery, FSRS or the error log (`docs/ai-boundaries.md`).

| Intent | Grounded in | Returns |
|---|---|---|
| `explain_attempt` | the attempt as it was shown (evidence log), Vabamorf's reading of both forms, the EKK section | why the expected form is the one |
| `explain_concept` | the topic's EKK reference and its Estonian term | the rule in a few sentences |

What comes back is checked before the learner sees it: every Estonian word the
model quotes must be one Vabamorf knows (`_grounded`), or the answer is dropped
and the EKK reference stands on its own. A model that invents `raamatud` as a
partitive is worse than no explanation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: One prompt, one job: explain, in Russian, using only what is given.
SYSTEM = """\
You explain Estonian grammar to a Russian-speaking learner (A2/B1).

Rules:
- Answer in Russian. Keep Estonian grammatical terms in Estonian (osastav,
  omastav, rektsioon), and gloss each once.
- Use only the forms and facts given to you. Never invent an Estonian form.
- Be short: at most four sentences.
- If the given facts do not explain it, say so plainly in Russian.
Return JSON: {"explanation_ru": "..."}"""

#: Estonian words in a model's answer, for the grounding check.
_WORD = re.compile(r"[A-Za-zÀ-ÿŠŽšžÕÄÖÜõäöü][A-Za-zÀ-ÿŠŽšžÕÄÖÜõäöü-]{2,}")


@dataclass(frozen=True)
class Answer:
    intent: str
    explanation_ru: str
    engine: str
    #: The EKK section the explanation had to work from, when there is one.
    reference: dict | None = None
    degraded: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return {"intent": self.intent, "explanation_ru": self.explanation_ru,
                "engine": self.engine, "reference": self.reference,
                "degraded": self.degraded, "note": self.note,
                # Always: an explanation is a model's, even when it is grounded.
                "source": "model"}


def _grounded(text: str, allowed: set[str]) -> bool:
    """True when every Estonian-looking word is one Vabamorf knows or was given."""
    from .morph import _readings

    for word in _WORD.findall(text):
        low = word.casefold()
        if low in allowed:
            continue
        # Russian is written in Cyrillic, so anything Latin here is Estonian.
        try:
            if not _readings(word):
                return False
        except Exception:  # noqa: BLE001 - no morphology is not a veto
            return True
    return True


def _ask(prompt: str, allowed: set[str], intent: str, reference: dict | None) -> Answer:
    """One call through the grammar chain's LLM lanes, then the grounding check."""
    from .providers.breaker import is_open
    from .providers.grammar import LLM_PREFERENCE
    from .providers.llm import PROVIDERS, complete, parse_json

    for name in LLM_PREFERENCE:
        lane = PROVIDERS.get(name)
        if lane is None or not lane.available or is_open(f"llm:{name}"):
            continue
        try:
            said = parse_json(complete(name, SYSTEM, prompt))
        except Exception:  # noqa: BLE001 - the next lane, then the reference alone
            continue
        text = (said.get("explanation_ru") or "").strip()
        if not text:
            continue
        if not _grounded(text, allowed):
            # An invented form is worse than silence: keep the handbook's own words.
            return Answer(intent, "", f"llm:{name}", reference, degraded=True,
                          note=("Объяснение отклонено: модель использовала форму, "
                                "которой Vabamorf не знает. Ниже — правило из EKK."))
        return Answer(intent, text, f"llm:{name}", reference)

    return Answer(intent, "", "none", reference, degraded=True,
                  note=("Объяснение сейчас недоступно — ни один движок не ответил. "
                        "Правило из EKK ниже."))


def explain_attempt(event_id: str) -> Answer:
    """Why the expected form was the right one, for one recorded attempt."""
    from . import evidence
    from .curriculum import by_id
    from .grammar import describe
    from .morph import analyze

    with evidence.connect() as log:
        found = [e for e in evidence.events(log) if e.id == event_id]
    if not found or found[0].type != "attempt":
        raise KeyError(event_id)
    p = found[0].payload
    topic = by_id(p["topic"])
    reference = describe(topic.tag or topic.id)
    reference = reference if reference.get("known") else None

    solution = p["prompt"].replace("____", p["expected"])
    readings = {t.text.casefold(): f"{t.lemma} · {t.form}" for t in analyze(solution)}
    given = " ".join([p["expected"], p.get("answer") or "", p.get("lemma") or ""])
    allowed = set(readings) | {w.casefold() for w in given.split()}
    facts = "\n".join(f"- {word}: {reading}" for word, reading in readings.items())
    prompt = (
        f"Sentence as shown: {p['prompt']}\n"
        f"Expected form: {p['expected']}\n"
        f"Learner wrote: {p.get('answer') or '(nothing)'}\n"
        f"Topic: {topic.et} ({topic.ru})\n"
        + (f"Rule (EKK {reference['ekk_section']}): {reference['summary_ru']}\n"
           if reference else "")
        + f"Vabamorf's reading of the correct sentence:\n{facts}\n"
        "Explain in Russian why the expected form is the one, and what the "
        "learner's form would mean instead."
    )
    return _ask(prompt, allowed, "explain_attempt", reference)


def explain_concept(topic_id: str) -> Answer:
    """The rule behind a topic, in a few sentences, from its EKK section."""
    from .curriculum import by_id
    from .grammar import describe

    topic = by_id(topic_id)
    reference = describe(topic.tag or topic.id)
    reference = reference if reference.get("known") else None
    if reference is None:
        return Answer("explain_concept", "", "none", None, degraded=True,
                      note=("Для этой темы в EKK нет раздела, поэтому объяснение "
                            "не на чём основывать."))
    prompt = (
        f"Topic: {topic.et} ({topic.ru})\n"
        f"EKK {reference['ekk_section']} says: {reference['summary_ru']}\n"
        f"Estonian term: {reference['et_term']}\n"
        "Explain this rule in Russian for an A2/B1 learner, in at most four "
        "sentences. Use only the facts above."
    )
    allowed = {w.casefold() for w in
               f"{topic.et} {reference['et_term']}".replace(",", " ").split()}
    return _ask(prompt, allowed, "explain_concept", reference)
