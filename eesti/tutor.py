"""The bounded tutor: the one boundary a model speaks to the learner across.

Every model-facing job goes through here (ADR-0002), so the rules are written
once: the day's budget is checked and spent, the prompt is grounded in what code
knows, the answer names its engine, and nothing it says decides anything
(`docs/ai-boundaries.md`).

| Intent | Grounded in | Returns |
|---|---|---|
| `explain_attempt` | the attempt as it was shown (evidence log), Vabamorf's reading of both forms, the EKK section | why the expected form is the one |
| `explain_concept` | the topic's EKK reference and its Estonian term | the rule in a few sentences |
| `converse` | a task from the paired-exam bank, and the turns so far | the partner's next Estonian turn |
| `check_writing` | the provider chain plus the deterministic checks | corrections, each labelled with what code could verify |
| `speaking_feedback` | a transcript, read as advisory | the same corrections, never recorded |
| `translate` | TartuNLP's translation service | one sentence in Russian |

An explanation that quotes an Estonian word Vabamorf does not know is dropped
(`_grounded`) and the EKK reference stands on its own: a model that invents
`raamatud` as a partitive is worse than no explanation. A **conversation** is
allowed to speak freely — it is a dialogue, not a rule — but the words Vabamorf
does not know are named to the learner rather than passed off as Estonian.
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


def _lanes():
    """LLM lanes that are configured, not tripped, and still inside today's
    allowance — in the chain's own order."""
    from .providers import budget
    from .providers.breaker import is_open
    from .providers.grammar import LLM_PREFERENCE
    from .providers.llm import PROVIDERS

    for name in LLM_PREFERENCE:
        lane = PROVIDERS.get(name)
        if lane is None or not lane.available:
            continue
        if is_open(f"llm:{name}") or budget.exhausted(f"llm:{name}"):
            continue
        yield name


def _ask(prompt: str, allowed: set[str], intent: str, reference: dict | None,
         system: str = "", field: str = "explanation_ru") -> Answer:
    """One call through the chain's LLM lanes, then the grounding check."""
    from .providers import budget
    from .providers.llm import complete, parse_json

    for name in _lanes():
        try:
            budget.spend(f"llm:{name}")
            said = parse_json(complete(name, system or SYSTEM, prompt))
        except Exception:  # noqa: BLE001 - the next lane, then the reference alone
            continue
        text = (said.get(field) or "").strip()
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


# --------------------------------------------------------------------------
# Conversation: the exam is paired, so practice has to have two sides
# --------------------------------------------------------------------------

#: The exam's own length: three parts in fifteen minutes is a handful of turns
#: each, not an evening. A cap also bounds what one session can spend.
MAX_TURNS = 8

#: Estonian in, Estonian out. The partner never corrects and never scores —
#: that is the grammar chain's job, and it is advisory on a transcript anyway.
CONVERSE = """\
You are the learner's partner in an Estonian A2/B1 speaking exam (HARNO
tasemeeksam), which is taken in pairs.

Rules:
- Reply in Estonian, at A2/B1 level: one to three short sentences.
- Stay on the task card you are given, and end your turn with one question.
- Never correct the learner, never grade them, never say how they are doing.
- Do not switch to Russian in the reply.
- `hint_ru` is one short Russian nudge about *what to say next*, never about
  grammar being right or wrong. Leave it empty when nothing is needed.
Return JSON: {"reply_et": "...", "hint_ru": "..."}"""


@dataclass(frozen=True)
class Turn:
    """One exchange, as the page keeps it."""

    who: str      # learner | partner
    text: str


@dataclass(frozen=True)
class Reply:
    task: str
    reply_et: str
    hint_ru: str
    engine: str
    turns: int
    #: Words in the reply that Vabamorf does not know. Named, not hidden: a
    #: partner that invents a form must not pass it off as Estonian.
    unknown: tuple[str, ...] = ()
    degraded: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return {"task": self.task, "reply_et": self.reply_et,
                "hint_ru": self.hint_ru, "engine": self.engine,
                "turns": self.turns, "unknown": list(self.unknown),
                "degraded": self.degraded, "note": self.note,
                "source": "model", "graded": False}


def _unknown_words(text: str) -> tuple[str, ...]:
    """Estonian-looking words in a reply that Vabamorf does not know."""
    from .morph import _readings

    out = []
    for word in _WORD.findall(text):
        try:
            if not _readings(word) and not word[0].isupper():
                out.append(word)
        except Exception:  # noqa: BLE001 - no morphology is not a veto
            return ()
    return tuple(dict.fromkeys(out))


def converse(task: str, history: list[Turn], said: str = "") -> Reply:
    """The partner's next turn on a task from the speaking bank.

    Stateless: the page keeps the exchange and sends it back, capped at
    `MAX_TURNS` so a conversation stays the length of an exam part.
    """
    import json as _json

    from .providers import budget
    from .providers.llm import complete, parse_json
    from .speaking import bank

    question = next((q for q in bank() if q.question == task or q.topic == task), None)
    if question is None:
        raise KeyError(task)

    turns = [t for t in history][-2 * MAX_TURNS:]
    if said:
        turns = turns + [Turn("learner", said)]
    spoken = sum(1 for t in turns if t.who == "learner")
    if spoken > MAX_TURNS:
        return Reply(question.question, "", "", "none", spoken, degraded=True,
                     note=("Хватит на один раз: на экзамене эта часть длится "
                           "15 минут. Начни новый разговор, когда захочешь."))

    lines = "\n".join(f"{'Learner' if t.who == 'learner' else 'You'}: {t.text}"
                       for t in turns) or "(the learner has not spoken yet)"
    prompt = (f"Task card (Estonian): {question.question}\n"
              f"What the task is about, in Russian: {question.hint_ru}\n"
              f"Conversation so far:\n{lines}\n"
              "Give your next turn.")

    for name in _lanes():
        try:
            budget.spend(f"llm:{name}")
            answer = parse_json(complete(name, CONVERSE, prompt))
        except Exception:  # noqa: BLE001 - try the next lane
            continue
        reply = (answer.get("reply_et") or "").strip()
        if not reply:
            continue
        if CYRILLIC.search(reply):
            # The partner speaks Estonian; Russian belongs in the hint.
            continue
        return Reply(question.question, reply,
                     (answer.get("hint_ru") or "").strip(), f"llm:{name}",
                     spoken, unknown=_unknown_words(reply))
    return Reply(question.question, "", "", "none", spoken, degraded=True,
                 note=("Собеседник сейчас недоступен — ни один движок не "
                       "ответил. Вопросы для практики остаются во вкладке."))


#: Russian is Cyrillic; a reply that carries it is not the partner's turn.
CYRILLIC = re.compile(r"[\u0400-\u04ff]")


# --------------------------------------------------------------------------
# The other model-facing jobs, behind the same boundary (ADR-0002)
# --------------------------------------------------------------------------

def check_writing(text: str) -> dict:
    """The writing check: the provider chain, the deterministic checks merged in,
    every correction labelled with what code could verify, and a back-translation
    so the learner can see what the sentence actually says.
    """
    from .providers import grammar
    from .providers.translate import translate as translate_sentence

    result = grammar.check(text).to_dict()
    back = translate_sentence(text, target="rus")
    result["back_translation"] = back.text if back else None
    return result


def speaking_feedback(transcript: str) -> dict:
    """The same check over a transcript, read as advisory: a recogniser's mistake
    is not the learner's, so nothing here is ever recorded (`from_transcript`).
    """
    from .providers import grammar

    checked = grammar.from_transcript(grammar.check(transcript), transcript)
    return checked.to_dict()


def translate(text: str, target: str = "rus"):
    """One sentence, on request only. Not a grader: nothing about a translation
    feeds drills, review or readiness."""
    from .providers.translate import translate as translate_sentence

    return translate_sentence(text, target=target)
