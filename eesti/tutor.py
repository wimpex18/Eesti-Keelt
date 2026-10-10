"""The bounded tutor: the one boundary a model speaks to the learner across.

Every model-facing job goes through here (ADR-0002), so the rules are written
once: the day's budget is checked and spent, the prompt is grounded in what code
knows, the answer names its engine, and nothing it says decides anything
(`docs/ai-boundaries.md`).

| Intent | Grounded in | Returns |
|---|---|---|
| `explain_attempt` | the attempt as it was shown (evidence log), Vabamorf's reading of both forms, the EKK section | why the expected form is the one |
| `explain_concept` | the topic's EKK reference and its Estonian term | the rule in a few sentences |
| `ask_rule` | a learner's question, the topic's EKK summary and sourced points | an answer from those alone |
| `descriptor_feedback` | a written or confirmed spoken text, HARNO's level descriptors | comments quoting the text, never a score |
| `converse` | a task from the paired-exam bank, and the turns so far | the partner's next Estonian turn |
| `check_writing` | the provider chain plus the deterministic checks | corrections, each labelled with what code could verify |
| `speaking_feedback` | a transcript, read as advisory | the same corrections, never recorded |
| `translate` | TartuNLP's translation service | one sentence in Russian |

An explanation that quotes an Estonian word Vabamorf does not know is dropped
(`_grounded`) and the EKK reference stands on its own: a model that invents
`raamatud` as a partitive is worse than no explanation. Explanations come in
the learner's explanation language (`LANGUAGES`); in Russian and Ukrainian a
Latin word is Estonian, and in English the model marks each Estonian word with
asterisks and every marked word is checked (`_grounded_in`). A **conversation** is
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
    #: The explanation, in `lang` (the field keeps its first language's name).
    explanation_ru: str
    engine: str
    #: The EKK section the explanation had to work from, when there is one.
    reference: dict | None = None
    degraded: bool = False
    note: str = ""
    lang: str = "ru"

    def to_dict(self) -> dict:
        return {"intent": self.intent, "explanation_ru": self.explanation_ru,
                "text": self.explanation_ru, "lang": self.lang,
                "engine": self.engine, "reference": self.reference,
                "degraded": self.degraded, "note": self.note,
                # Always: an explanation is a model's, even when it is grounded.
                "source": "model"}


#: Explanation languages (PRODUCT.md), as a model is asked to write them.
LANGUAGES = {"ru": "Russian", "uk": "Ukrainian", "en": "English"}

#: Said when no engine answered or an answer was refused, per language.
_UNAVAILABLE = {
    "ru": "Объяснение сейчас недоступно — ни один движок не ответил. Правило из EKK ниже.",
    "uk": "Пояснення зараз недоступне — жоден рушій не відповів. Правило з EKK нижче.",
    "en": "No explanation is available right now: no engine answered. The EKK rule is below.",
}
_REFUSED = {
    "ru": ("Объяснение отклонено: модель использовала форму, которой Vabamorf не "
           "знает. Ниже — правило из EKK."),
    "uk": ("Пояснення відхилено: модель ужила форму, якої Vabamorf не знає. Нижче — "
           "правило з EKK."),
    "en": ("The explanation was refused: the model used a form Vabamorf does not "
           "know. The EKK rule is below."),
}


def _system_for(lang: str) -> str:
    """The explain prompt in an explanation language; Russian keeps `SYSTEM`."""
    if lang == "ru":
        return SYSTEM
    name = LANGUAGES[lang]
    return f"""\
You explain Estonian grammar to a learner of Estonian (A1-B1) whose explanation
language is {name}.

Rules:
- Answer in {name}. Keep Estonian grammatical terms in Estonian (osastav,
  omastav, rektsioon), and gloss each once in {name}.
- Write every Estonian word or form between asterisks: *leiba*, *osastav*.
- Use only the forms and facts given to you. Never invent an Estonian form.
- Be short: at most four sentences.
- If the given facts do not explain it, say so plainly in {name}.
Return JSON: {{"explanation_ru": "..."}}  (the field takes the {name} text)"""


_MARKED = re.compile(r"\*([^*]+)\*")


def _grounded_in(text: str, allowed: set[str], lang: str) -> bool:
    """`_grounded` for an explanation language. In Cyrillic every Latin word is
    Estonian. In English only the marked words are: each must be one Vabamorf
    knows or was given, and no form given to the model may stand unmarked."""
    if lang != "en":
        return _grounded(text, allowed)
    marked = " ".join(_MARKED.findall(text))
    if not _grounded(marked, allowed):
        return False
    bare = _MARKED.sub(" ", text)
    return not any(w.casefold() in allowed and w.casefold() not in _ENGLISH
                   for w in _WORD.findall(bare))


#: English words that are also Estonian forms a sentence may contain: unmarked,
#: they are read as English.
_ENGLISH = frozenset({"see", "need", "all", "tee", "mis", "son", "pole", "kas", "her",
                      "art", "ere", "lane", "tall", "mail", "the"})


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


def _completion(name: str, system: str, prompt: str) -> dict:
    """One interactive request, with the same budget and breaker as grammar."""
    from .providers import breaker, budget
    from .providers.llm import complete, parse_json

    budget.spend(f"llm:{name}")
    try:
        reply = parse_json(complete(name, system, prompt, attempts=1))
        if (not isinstance(reply, dict)
                or any(reply.get(key) is not None and not isinstance(reply[key], str)
                       for key in ("explanation_ru", "reply_et", "hint_ru"))
                or ("questions" in reply and not isinstance(reply["questions"], list))):
            raise ValueError("invalid tutor response schema")
    except Exception as exc:
        from .providers.llm import is_fault

        if is_fault(exc):
            breaker.record_failure(f"llm:{name}")
        raise
    breaker.record_success(f"llm:{name}")
    return reply


def _ask(prompt: str, allowed: set[str], intent: str, reference: dict | None,
         system: str = "", field: str = "explanation_ru", lang: str = "ru") -> Answer:
    """One call through the chain's LLM lanes, then the grounding check."""

    for name in _lanes():
        try:
            said = _completion(name, system or _system_for(lang), prompt)
        except Exception:  # noqa: BLE001 - the next lane, then the reference alone
            continue
        text = (said.get(field) or "").strip()
        if not text:
            continue
        if not _grounded_in(text, allowed, lang):
            # An invented form is worse than silence: keep the handbook's own words.
            return Answer(intent, "", f"llm:{name}", reference, degraded=True,
                          note=_REFUSED[lang], lang=lang)
        return Answer(intent, text, f"llm:{name}", reference, lang=lang)

    return Answer(intent, "", "none", reference, degraded=True, note=_UNAVAILABLE[lang],
                  lang=lang)


def explain_attempt(event_id: str, lang: str = "ru") -> Answer:
    """Why the expected form was the right one, for one recorded attempt, in the
    learner's explanation language and from the item's EKK section."""
    from . import evidence
    from .curriculum import by_id
    from .grammar import describe
    from .morph import analyze

    with evidence.connect() as log:
        found = [e for e in evidence.events(log) if e.id == event_id]
    if not found or found[0].type != "attempt":
        raise KeyError(event_id)
    if lang not in LANGUAGES:
        raise ValueError(f"no such explanation language: {lang}")
    p = found[0].payload
    topic = by_id(p["topic"])
    reference = describe(topic.tag or topic.id)
    reference = reference if reference.get("known") else None

    from .item import fill

    solution = fill(p["prompt"], p["expected"])
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
        f"Explain in {LANGUAGES[lang]} why the expected form is the one, and what the "
        "learner's form would mean instead."
    )
    return _ask(prompt, allowed, "explain_attempt", reference, lang=lang)


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
# A question on the rule page: answered from the topic's sources alone
# --------------------------------------------------------------------------

#: The longest question a learner may ask, in characters.
QUESTION_MAX = 300


def _ask_system(lang: str) -> str:
    name = LANGUAGES[lang]
    return f"""\
You answer one question from a learner of Estonian (A1-B1) about one grammar
rule. The learner's explanation language is {name}.

Rules:
- Answer in {name}, in at most four short sentences.
- Use only the rule text and points you are given. If they do not answer the
  question, say so plainly and name the section to read; do not guess.
- Answer only about this rule. A question about anything else gets one
  sentence saying you can only explain this rule.
- Keep Estonian grammatical terms in Estonian and write every Estonian word or
  form between asterisks: *leiba*. Never invent an Estonian form.
- Never say whether something the learner wrote is right or wrong: you explain,
  code checks.
Return JSON: {{"explanation_ru": "..."}}  (the field takes the {name} text)"""


def ask_rule(topic_id: str, question: str, lang: str = "ru") -> Answer:
    """The learner's own question about a topic, answered from its EKK summary
    and sourced points (`lessontext.LESSONS`); an answer that writes an Estonian
    word the sources and Vabamorf do not have is refused."""
    from .curriculum import by_id
    from .grammar import describe
    from .lessontext import LESSONS

    if lang not in LANGUAGES:
        raise ValueError(f"no such explanation language: {lang}")
    question = " ".join((question or "").split())
    if not question:
        raise ValueError("empty question")
    if len(question) > QUESTION_MAX:
        raise ValueError(f"question longer than {QUESTION_MAX} characters")
    topic = by_id(topic_id)
    reference = describe(topic.tag or topic.id)
    reference = reference if reference.get("known") else None
    text = LESSONS.get(topic_id)
    points = list(text.points_ru) if text else []
    if reference is None and not points:
        return Answer("ask_rule", "", "none", None, degraded=True, lang=lang,
                      note=_NO_SOURCE[lang])
    sources = "\n".join(f"- {s.label}" for s in (text.sources if text else ()))
    facts = "\n".join(f"- {pt}" for pt in points)
    prompt = (
        f"Rule: {topic.et} ({topic.ru})\n"
        + (f"EKK {reference['ekk_section']} says: {reference['summary_ru']}\n" if reference else "")
        + (f"Points from the sources:\n{facts}\n" if facts else "")
        + (f"Sources:\n{sources}\n" if sources else "")
        + f"\nThe learner asks: {question}"
    )
    source_text = " ".join([topic.et, reference["summary_ru"] if reference else "",
                            reference["et_term"] if reference else "", *points])
    allowed = {w.casefold() for w in _WORD.findall(source_text)} | {"ekk"}
    answer = _ask(prompt, allowed, "ask_rule", reference, system=_ask_system(lang), lang=lang)
    if answer.degraded and answer.engine == "none":
        # On the rule page the sourced rule is above the question, not below.
        from dataclasses import replace

        answer = replace(answer, note=_ASK_UNAVAILABLE[lang])
    return answer


_ASK_UNAVAILABLE = {
    "ru": "Ответ сейчас недоступен: ни один движок не ответил. Правило по источникам — выше на этой странице.",
    "uk": "Відповідь зараз недоступна: жоден рушій не відповів. Правило за джерелами — вище на цій сторінці.",
    "en": "No answer is available right now: no engine answered. The sourced rule is above on this page.",
}

_NO_SOURCE = {
    "ru": "Для этой темы нет раздела в источниках, поэтому ответ не на чём основывать.",
    "uk": "Для цієї теми немає розділу в джерелах, тож відповідь нема на чому будувати.",
    "en": "This topic has no section in the sources, so there is nothing to base an answer on.",
}


# --------------------------------------------------------------------------
# Writing and speaking: comments against HARNO's descriptors, never a score
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Descriptors:
    """One level's descriptors for one skill, as HARNO's handbook gives them
    (summarised; the handbook is cited with its page)."""

    source: str
    url: str
    points: tuple[tuple[str, str, str], ...]     # (id, Estonian name, what it asks)


#: HARNO's level descriptions: *Iseseisev keelekasutaja* (B1, REKK 2008) and
#: Marju Ilves, *Algaja keelekasutaja* (A2, 2008), both on harno.ee. Each
#: criterion is the handbook's "üldjoontes" description, summarised in English
#: for the prompt; the page is the printed one.
DESCRIPTORS = {
    ("B1", "kirjutamine"): Descriptors(
        "Iseseisev keelekasutaja, lisa 4, lk 197",
        "https://harno.ee/sites/default/files/documents/2021-06/Iseseisev-keelekasutaja.pdf",
        (("seotus", "seotud tekst", "writes connected text on a familiar topic, joining "
          "short sentences into a simple sequence"),
         ("kirjeldus", "sündmused ja tunded", "describes events, reactions and feelings on "
          "familiar topics"),
         ("teave", "info ja mõtted", "passes on information and thoughts fairly "
          "precisely, asks for information and gives explanations"),
         ("kiri", "isiklik kiri", "keeps up regular personal correspondence"))),
    ("B1", "raakimine"): Descriptors(
        "Iseseisev keelekasutaja, lisa 2, lk 189",
        "https://harno.ee/sites/default/files/documents/2021-06/Iseseisev-keelekasutaja.pdf",
        (("ulatus", "väljendus", "speaks fairly fluently, if in general terms, on everyday "
          "topics and own interests; describes situations, events, plans and feelings "
          "in short sentences, explains the core of a problem, gives an opinion"),
         ("sonavara", "sõnavara", "uses core vocabulary and some common phrases; on an "
          "unfamiliar topic gaps in vocabulary make the wording indirect"),
         ("korrektsus", "korrektsus", "in a familiar situation the language is fairly "
          "correct and mistakes do not stop understanding"),
         ("suhtlus", "suhtlus", "can join a discussion on a familiar topic"))),
    ("A2", "kirjutamine"): Descriptors(
        "Algaja keelekasutaja, lisa 1, lk 135",
        "https://harno.ee/sites/default/files/documents/2021-06/Algaja-keelekasutaja.-A2-tase.pdf",
        (("laused", "lühikesed laused", "writes short sentences on everyday topics"),
         ("sidesonad", "sidesõnad", "joins simple phrases and sentences with simple "
          "conjunctions such as ja, ning, aga, sest, et"),
         ("endast", "endast", "writes in simple phrases and sentences about family, "
          "living conditions, education, present or past work"),
         ("teave", "teave", "can ask for simple factual information"))),
    ("A2", "raakimine"): Descriptors(
        "Algaja keelekasutaja, lisa 1, lk 131",
        "https://harno.ee/sites/default/files/documents/2021-06/Algaja-keelekasutaja.-A2-tase.pdf",
        (("ulatus", "väljendus", "speaks simply and in general terms about everyday "
          "topics and own interests"),
         ("sonavara", "sõnavara", "uses the most frequent words and set phrases"),
         ("seotus", "seotus", "tells or describes with unlinked sentences or links them "
          "with simple conjunctions such as ja, aga, sest, et"),
         ("suhtlus", "suhtlus", "takes part in simple everyday exchange of information "
          "on a familiar topic, in short turns"))),
}


def descriptors_for(level: str, kind: str) -> Descriptors:
    """The descriptors a text is read against: B1's for B1, A2's below it (the
    first stages work towards A2's)."""
    return DESCRIPTORS[("B1" if level == "B1" else "A2", kind)]


def _feedback_system(lang: str, kind: str) -> str:
    name = LANGUAGES[lang]
    what = "written text" if kind == "kirjutamine" else "spoken answer (a transcript the learner confirmed)"
    return f"""\
You comment on an Estonian learner's {what}, against level descriptors from
the Estonian exam board's handbook, in {name}.

Rules:
- For each descriptor you are given, write one or two sentences in {name} on
  how the text meets it, and quote the learner's own words that show it in
  "quote", copied character for character from the text.
- Never give a score, a grade, points, a percentage, a level verdict, or say
  pass or fail. You comment; you do not mark.
- Do not rewrite the text. You may suggest one Estonian word or form per
  descriptor; write every Estonian word between asterisks: *leiba*.
- {"A transcript can contain the recogniser's mistakes: never comment on spelling." if kind == "raakimine" else "Comment on what is written, not on what the task asked."}
Return JSON: {{"points": [{{"criterion": "<id>", "quote": "...", "comment": "..."}}]}}"""


#: A comment that marks: a number with %, a fraction, points or a grade word.
_MARK = re.compile(r"\d+\s*(%|/\s*\d|из\s+\d|з\s+\d|out of|points?|балл|бал|punkt)|"
                   r"\b(оценк|grade|score|балів|бали|оцінк)", re.IGNORECASE)


def descriptor_feedback(kind: str, text: str, *, level: str = "A2", task: str = "",
                        lang: str = "ru") -> dict:
    """Advisory comments on a learner's text against HARNO's descriptors, after
    code's checklist. Code keeps a comment only when its quote is the learner's
    own words, it marks nothing, and every Estonian word it suggests is one
    Vabamorf knows. Nothing here is recorded or graded."""
    if kind not in ("kirjutamine", "raakimine"):
        raise ValueError(f"no descriptors for {kind!r}")
    if lang not in LANGUAGES:
        raise ValueError(f"no such explanation language: {lang}")
    body = " ".join((text or "").split())
    if not body:
        raise ValueError("empty text")
    found = descriptors_for(level, kind)
    lines = "\n".join(f"- {pid} ({et}): {asks}" for pid, et, asks in found.points)
    prompt = (f"Level: {'B1' if level == 'B1' else 'A2'}. Descriptors ({found.source}):\n"
              f"{lines}\n" + (f"Task: {task}\n" if task else "")
              + f"\nThe learner's text:\n{text.strip()[:4000]}")
    known = {pid for pid, _et, _asks in found.points}
    names = {pid: et for pid, et, _asks in found.points}
    learner_words = {w.casefold() for w in _WORD.findall(text)}
    for name in _lanes():
        try:
            said = _completion(name, _feedback_system(lang, kind), prompt)
        except Exception:  # noqa: BLE001 - the next lane, then nothing
            continue
        points = said.get("points")
        if not isinstance(points, list):
            continue
        kept, dropped = [], 0
        for pt in points:
            if not isinstance(pt, dict) or pt.get("criterion") not in known:
                dropped += 1
                continue
            quote = " ".join(str(pt.get("quote") or "").split())
            comment = " ".join(str(pt.get("comment") or "").split())
            if not comment or (quote and quote.casefold() not in body.casefold()) \
                    or _MARK.search(comment) or not _grounded_in(comment, learner_words, lang):
                dropped += 1
                continue
            kept.append({"criterion": pt["criterion"], "et": names[pt["criterion"]],
                         "quote": quote, "comment": comment})
        if kept:
            return {"points": kept, "dropped": dropped, "engine": f"llm:{name}",
                    "source": {"label": found.source, "url": found.url},
                    "lang": lang, "degraded": False, "graded": False}
    return {"points": [], "dropped": 0, "engine": "none",
            "source": {"label": found.source, "url": found.url}, "lang": lang,
            "degraded": True, "graded": False, "note": _UNAVAILABLE_FEEDBACK[lang]}


_UNAVAILABLE_FEEDBACK = {
    "ru": "Комментарий модели сейчас недоступен. Проверка кодом выше остаётся в силе.",
    "uk": "Коментар моделі зараз недоступний. Перевірка кодом вище залишається чинною.",
    "en": "The model's comments are not available right now. Code's checklist above still stands.",
}


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
            answer = _completion(name, CONVERSE, prompt)
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


#: Questions about a text. The model writes the question; the *text* keys it,
#: and `comprehension.verify` throws away anything whose answer is not the
#: text's own words (ADR-0004).
QUESTIONS = """\
You write reading-comprehension questions for a Russian-speaking learner of
Estonian (A2/B1), about the Estonian text given to you.

Rules:
- Ask in Estonian, in simple language. Each question ends with "?".
- The answer to every question must be a span COPIED WORD FOR WORD from the
  text, at most 8 words long, appearing in the text exactly once.
- Never ask something the text does not answer. Never write the answer into
  the question.
- Ask about different parts of the text: who, where, when, how many, why.
Return JSON: {"questions": [{"q": "...", "a": "..."}]}"""


def propose_questions(text: str, want: int = 5) -> tuple[list[dict], str]:
    """Ask a lane for question/answer pairs. Returns the pairs and the engine.

    Nothing here is trusted: `comprehension.verify` decides which pairs are
    questions at all, and an empty list is a normal answer.
    """

    body = text.strip()[:6000]
    prompt = (f"Write {want} questions about this text.\n\nTEXT:\n{body}")
    for name in _lanes():
        try:
            said = _completion(name, QUESTIONS, prompt)
        except Exception:  # noqa: BLE001 - try the next lane, then give up
            continue
        pairs = [p for p in (said.get("questions") or [])
                 if isinstance(p, dict) and p.get("q") and p.get("a")]
        if pairs:
            return pairs, f"llm:{name}"
    return [], "none"


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
