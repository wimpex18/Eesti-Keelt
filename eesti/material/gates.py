"""The deterministic gates a model's draft passes before anything is kept (ADR-0009, step 2).

In order, each by code alone:

1. **schema** — the shape (`schema.py`); a draft that does not parse is nothing.
2. **vabamorf** — every word of the text, its questions and its gaps is a form
   Vabamorf knows without guessing (`guess=False`) and its spellchecker accepts.
   A declared name is exempt: Vabamorf need not know *Svetlana*.
3. **level** — every content lemma (noun, verb, adjective, adverb) is on EKI's
   A1/A2/B1 list at or below the unit's stage, or one of at most three
   off-list words the draft declares with a Russian gloss. Any reading
   Vabamorf allows counts here: its disambiguator reads *Ma joon* as the noun
   "line", which is not the word on the list.
4. **forms** — every form tag Vabamorf reads comes from a topic the course has
   introduced by this unit (`TAG_TOPICS`, `units.UNITS`). Lines of EKI's own A1
   phrase collection are exempt: *Mis su nimi on?* is taught as a phrase.
5. **answers** — each answer occurs in the text verbatim and exactly once, and
   the question does not give it away (`comprehension.verify`).
6. **gaps** — one right answer: the gap word is read in its sentence as the
   lemma and form it names, Vabamorf generates exactly that word for them, and
   no other form the gap's label could mean is a second right answer.
7. **duplicates** — no question or answer twice, no gap twice.

The text failing a gate fails the draft. A question or gap failing one is
dropped, with the gate that dropped it; a draft left with fewer than
`MIN_QUESTIONS` questions fails.

The forms gate judges Vabamorf's disambiguated reading, as the rest of the app
does: *Piima ma ei taha* is read as the short illative, so it is refused at
unit 4 and the draft is reworded (*Ma ei taha piima*). A strict gate costs a
redraft; a lenient one lets a form no unit has taught reach a learner.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from functools import lru_cache

from .schema import Gap, Material, Question

#: Bumped when a gate changes, so a stamp says which rules a file passed.
VERSION = 1

#: Fewer surviving questions than this and the draft fails.
MIN_QUESTIONS = 3

GATES = ("schema", "vabamorf", "level", "forms", "answers", "gaps", "duplicates")

#: Parts of speech whose lemma must be on EKI's list: noun, verb, adjective
#: (positive, comparative, superlative) and adverb. Pronouns, numerals,
#: conjunctions, adpositions, interjections and names are the grammar's, not
#: the word list's.
CONTENT_POS = frozenset({"S", "V", "A", "C", "U", "D"})

#: The EKI levels each stage may draw on.
STAGE_LEVELS = {"algus": ("A1",), "A1": ("A1",), "A2": ("A1", "A2"),
                "B1": ("A1", "A2", "B1")}

# ---------------------------------------------------------------------------
# Which topic introduces a form
# ---------------------------------------------------------------------------

#: Case → the topic that introduces it, for nouns, adjectives, numerals, names.
#: The nominative needs nothing; the plural adds `mitmus`.
CASE_TOPICS = {
    "n": None,
    "g": "pohivormid", "p": "pohivormid",
    "ill": "kohakaanded", "in": "kohakaanded", "el": "kohakaanded",
    "all": "kohakaanded", "ad": "kohakaanded", "abl": "kohakaanded",
    "tr": "harvad-kaanded", "ter": "harvad-kaanded", "es": "harvad-kaanded",
    "ab": "harvad-kaanded", "kom": "harvad-kaanded",
}

#: Verb form tag → the topic that introduces it. `o`, `neg o` and `nud` depend
#: on the word before them and are decided in `_verb_topic`.
VERB_TOPICS = {
    **dict.fromkeys(("n", "d", "b", "me", "te", "vad"), "olevik"),
    "neg": "eitus", "neg nud": "eitus",
    **dict.fromkeys(("s", "sin", "sid", "sime", "site"), "lihtminevik"),
    **dict.fromkeys(("ma", "da"), "verb-form"),
    **dict.fromkeys(("mas", "mast", "mata", "maks", "des"), "ma-vormid"),
    **dict.fromkeys(("ge", "gu", "gem", "neg ge", "neg gu", "neg gem", "neg me"),
                    "kaskiv"),
    **dict.fromkeys(("ks", "ksin", "ksid", "ksime", "ksite", "neg ks", "nuks"),
                    "tingiv"),
    **dict.fromkeys(("tud", "tav", "v"), "kesksonad"),
    **dict.fromkeys(("takse", "ti", "ta", "tagu", "taks", "neg ta", "tuks"),
                    "umbisikuline"),
    **dict.fromkeys(("vat", "tavat", "neg vat"), "kaudne"),
}

#: Words that make the next verb a connegative (*ei tule*, *ei tulnud*).
NEGATORS = frozenset({"ei", "ega"})

#: Conjunctions a first sentence needs before `sidesonad` teaches the rest.
BASIC_CONJUNCTIONS = frozenset({"ja", "aga", "või"})

#: Parts of speech a topic introduces whatever their form.
POS_TOPICS = {"C": "vordlusastmed", "U": "vordlusastmed", "O": "jargarvud",
              "K": "kaassonad", "P": "asesonad"}


def _verb_topic(lemma: str, form: str, after_negator: bool) -> str | None | bool:
    """The topic a verb form needs, None for none, False when no topic covers it."""
    if form == "o":
        # *ei tule* is negation (unit 4); *tule!* is the imperative (unit 11).
        return "eitus" if after_negator else "kaskiv"
    if form == "neg o":
        # *pole* is *ei ole*; *ära* is the negative imperative.
        return "eitus" if lemma == "olema" else "kaskiv"
    if form == "nud":
        # *ei tulnud* is the negated past; *on tulnud* the perfect.
        return "eitus" if after_negator else "taisminevik"
    return VERB_TOPICS.get(form, False)


def reading_topics(lemma: str, pos: str, form: str,
                   after_negator: bool = False) -> frozenset[str] | None:
    """The topics one reading needs, or None when no topic covers its form."""
    need: set[str] = set()
    if pos == "Z" or form in ("", "?"):
        if pos == "J" and lemma not in BASIC_CONJUNCTIONS:
            need.add("sidesonad")
        elif pos in POS_TOPICS and pos != "P":
            need.add(POS_TOPICS[pos])
        return frozenset(need)
    if pos == "V":
        topic = _verb_topic(lemma, form, after_negator)
        if topic is False:
            return None
        return frozenset({topic} if topic else ())
    if pos in POS_TOPICS:
        need.add(POS_TOPICS[pos])
        if pos == "P":
            # The EKI teatmik's pronoun tables are taught whole in `asesonad`.
            return frozenset(need)
    if form == "adt":
        return frozenset(need | {"kohakaanded"})
    parts = form.split()
    if len(parts) != 2 or parts[0] not in ("sg", "pl") or parts[1] not in CASE_TOPICS:
        return None
    number, case = parts
    if number == "pl":
        need.add("mitmus")
    if CASE_TOPICS[case]:
        need.add(CASE_TOPICS[case])
    return frozenset(need)


def introduced(unit_id: str) -> frozenset[str]:
    """Every topic the course has introduced by the end of this unit."""
    from ..units import UNITS, by_id

    n = by_id(unit_id).n
    return frozenset(t for u in UNITS if u.n <= n for t in u.topics)


# ---------------------------------------------------------------------------
# Labels for gap forms: what the learner is told to write
# ---------------------------------------------------------------------------

#: Vabamorf tag → the Estonian name a gap shows. A gap may only ask for a form
#: named here: an unnamed form cannot be asked for without guessing a label.
GAP_FORMS = {
    "sg g": "omastav", "sg p": "osastav", "sg ill": "sisseütlev",
    "sg in": "seesütlev", "sg el": "seestütlev", "sg all": "alaleütlev",
    "sg ad": "alalütlev", "sg abl": "alaltütlev", "sg tr": "saav",
    "sg ter": "rajav", "sg es": "olev", "sg ab": "ilmaütlev", "sg kom": "kaasaütlev",
    "pl n": "nimetav mitmuses", "pl g": "omastav mitmuses",
    "pl p": "osastav mitmuses", "pl in": "seesütlev mitmuses",
    "n": "olevik, mina", "d": "olevik, sina", "b": "olevik, tema",
    "me": "olevik, meie", "te": "olevik, teie", "vad": "olevik, nemad",
    "s": "lihtminevik, tema", "sin": "lihtminevik, mina",
    "sime": "lihtminevik, meie", "site": "lihtminevik, teie",
    "ma": "ma-tegevusnimi", "da": "da-tegevusnimi",
}

#: Tags that share a label with another form: a learner told *sisseütlev* may
#: write either. A gap is kept only when both give the same word.
SAME_LABEL = {"sg ill": ("adt",)}


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    gate: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.gate}] {self.where}: {self.message}"


@dataclass
class Report:
    material: Material
    failures: list[Finding] = field(default_factory=list)
    dropped: list[Finding] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def kept(self) -> Material:
        """The draft with only the items that passed: what may be stored."""
        return self.material.model_copy(update={"questions": list(self.questions),
                                                "gaps": list(self.gaps)})


# ---------------------------------------------------------------------------
# Morphology, once per word
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Word:
    text: str
    readings: tuple[tuple[str, str, str], ...]   # (lemma, pos, form), disambiguated


def _words(text: str) -> list[Word]:
    """Every token of `text` with its disambiguated readings, guessing nothing."""
    from ..morph import _vm, tokenize

    tokens = tokenize(text)
    if not tokens:
        return []
    out = []
    for item in _vm().analyze(tokens, disambiguate=True, guess=False, propername=True):
        readings = tuple(dict.fromkeys(
            (a.get("lemma", ""), a.get("partofspeech", ""), a.get("form", ""))
            for a in item.get("analysis") or []))
        out.append(Word(item["text"], readings))
    return out


@lru_cache(maxsize=8192)
def _all_readings(word: str) -> tuple[tuple[str, str, str], ...]:
    """Every reading of a word out of context, guessing nothing."""
    from ..morph import _vm

    return tuple(dict.fromkeys(
        (a.get("lemma", ""), a.get("partofspeech", ""), a.get("form", ""))
        for item in _vm().analyze([word], disambiguate=False, guess=False,
                                  propername=True)
        for a in item.get("analysis") or []))


def _is_word(token: str) -> bool:
    return any(ch.isalpha() for ch in token)


@lru_cache(maxsize=4096)
def _spelled(word: str) -> bool:
    from estnltk.vabamorf.morf import spellcheck

    return bool(spellcheck([word], suggestions=False)[0]["spelling"])


@lru_cache(maxsize=1024)
def _name_forms(word: str, names: frozenset[str]) -> tuple[tuple[str, str, str], ...]:
    """Readings of `word` as one of the declared names (*Svetlanale* → sg all)."""
    from ..morph import _vm

    if word.casefold() in names:
        return ((word, "H", "sg n"),)
    out = []
    for item in _vm().analyze([word], disambiguate=False, guess=True, propername=True):
        for a in item.get("analysis") or []:
            if a.get("lemma", "").casefold() in names and a.get("form"):
                out.append((a["lemma"], "H", a["form"]))
    return tuple(out)


def eki_levels(words: sqlite3.Connection | None) -> dict[str, str]:
    """EKI's own level for every lemma it lists, the lowest where it lists one twice.

    `official_levels` only: a level estimated from frequency is not EKI's
    (AGENTS.md), and a gate citing EKI must be EKI's.
    """
    if words is None:
        return {}
    order = {"A1": 0, "A2": 1, "B1": 2}
    out: dict[str, str] = {}
    try:
        rows = words.execute("SELECT word, level FROM official_levels").fetchall()
    except sqlite3.Error:
        return {}
    for word, level in rows:
        key = word.casefold()
        if level in order and (key not in out or order[level] < order[out[key]]):
            out[key] = level
    return out


# ---------------------------------------------------------------------------
# EKI's phrases, exempt from the forms gate
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _phrases() -> tuple[tuple[str, ...], ...]:
    from ..morph import tokenize
    from ..phrases import EXCHANGES, FUNCTIONS

    lines = {p for f in FUNCTIONS for p in f.phrases} | {x for pair in EXCHANGES for x in pair}
    seqs = {tuple(t.casefold() for t in tokenize(line) if _is_word(t)) for line in lines}
    return tuple(sorted((s for s in seqs if s), key=len, reverse=True))


def _phrase_covered(words: list[Word]) -> set[int]:
    """Indexes of tokens inside one of EKI's A1 phrases."""
    idx = [i for i, w in enumerate(words) if _is_word(w.text)]
    low = [words[i].text.casefold() for i in idx]
    covered: set[int] = set()
    for seq in _phrases():
        n = len(seq)
        for start in range(len(low) - n + 1):
            if tuple(low[start:start + n]) == seq:
                covered.update(idx[start:start + n])
    return covered


# ---------------------------------------------------------------------------
# The gates
# ---------------------------------------------------------------------------

class _Context:
    def __init__(self, material: Material, words: sqlite3.Connection | None):
        from ..units import by_id

        self.material = material
        try:
            self.unit = by_id(material.unit)
        except KeyError:
            self.unit = None
        # *Juhan Tamm* is two names, each read on its own.
        self.names = frozenset(part.casefold() for n in material.all_names()
                               for part in n.split())
        self.levels = eki_levels(words)
        self.stage_levels = STAGE_LEVELS.get(self.unit.stage, ()) if self.unit else ()
        self.topics = introduced(material.unit) if self.unit else frozenset()
        self.off_list = {o.lemma.casefold() for o in material.off_list}
        self.off_list_used: set[str] = set()

    def is_name(self, word: str) -> bool:
        return bool(_name_forms(word, self.names))


def _vabamorf(ctx: _Context, words: list[Word]) -> list[str]:
    problems = []
    for w in words:
        if not _is_word(w.text) or ctx.is_name(w.text):
            continue
        if not w.readings or not any(r[0] for r in w.readings):
            problems.append(f"Vabamorf does not know *{w.text}* (guess=False)")
        elif not _spelled(w.text):
            problems.append(f"the spellchecker refuses *{w.text}*")
    return problems


def _level(ctx: _Context, words: list[Word]) -> list[str]:
    problems = []
    for w in words:
        if not _is_word(w.text) or ctx.is_name(w.text):
            continue
        # Every reading, not only the disambiguated one: the disambiguator
        # reads *Ma joon* as the noun "line", and the verb is on the list.
        readings = _all_readings(w.text) or w.readings
        content = [r for r in readings if r[1] in CONTENT_POS]
        if not content or len(content) < len(readings):
            # A word with any grammatical reading (`mis`, `see`) is the grammar's.
            continue
        lemmas = {r[0].casefold() for r in content}
        if any(ctx.levels.get(lemma) in ctx.stage_levels for lemma in lemmas):
            continue
        declared = lemmas & ctx.off_list
        if declared:
            ctx.off_list_used |= declared
            continue
        listed = sorted({ctx.levels[lemma] for lemma in lemmas if lemma in ctx.levels})
        where = f"EKI lists it at {'/'.join(listed)}" if listed else "not on EKI's list"
        problems.append(f"*{w.text}* ({'/'.join(sorted(lemmas))}): {where}, beyond "
                        f"stage {ctx.unit.stage}, and not declared off-list")
    return problems


def _forms(ctx: _Context, words: list[Word]) -> list[str]:
    problems = []
    exempt = _phrase_covered(words)
    previous = ""
    for i, w in enumerate(words):
        if not _is_word(w.text):
            if w.text not in ("-", "–"):
                previous = ""
            continue
        after_negator = previous in NEGATORS
        previous = w.text.casefold()
        if i in exempt:
            continue
        readings = _name_forms(w.text, ctx.names) if ctx.is_name(w.text) else w.readings
        options = [reading_topics(lemma, pos, form, after_negator)
                   for lemma, pos, form in readings]
        if any(need is not None and need <= ctx.topics for need in options):
            continue
        tags = ", ".join(f"{pos} {form}".strip() for _, pos, form in readings)
        known = [need for need in options if need is not None]
        if not known:
            problems.append(f"*{w.text}* ({tags}): no topic covers this form")
        else:
            missing = sorted(set().union(*known) - ctx.topics)
            problems.append(f"*{w.text}* ({tags}): needs {', '.join(missing)}, "
                            f"not introduced by unit {ctx.unit.n}")
    return problems


def _gap(ctx: _Context, gap: Gap, segments: list[str]) -> str | None:
    """Why a gap has not exactly one right answer, or None when it has."""
    from ..comprehension import occurrences
    from ..morph import _readings, unique_form

    if gap.form not in GAP_FORMS:
        return f"form {gap.form!r} has no label a learner could be shown"
    line = segments[gap.at]
    if occurrences(line, gap.word) != 1:
        return f"*{gap.word}* is not in its line exactly once"
    words = _words(line)
    here = [w for w in words if w.text == gap.word]
    if not here or not any((r[0], r[2]) == (gap.lemma, gap.form) for r in here[0].readings):
        return f"*{gap.word}* is not read as {gap.lemma} {gap.form} in its sentence"
    if (gap.lemma, gap.form) not in _readings(gap.word):
        return f"*{gap.word}* does not read back as {gap.lemma} {gap.form}"
    form = unique_form(gap.lemma, gap.form)
    if form is None:
        return (f"Vabamorf gives {gap.lemma} {gap.form} no single form "
                "(a free variant or a homograph): two right answers")
    if form.casefold() != gap.word.casefold():
        return f"Vabamorf writes {gap.lemma} {gap.form} as *{form}*, not *{gap.word}*"
    for other in SAME_LABEL.get(gap.form, ()):
        variant = unique_form(gap.lemma, other)
        if variant and variant.casefold() != form.casefold():
            return (f"*{variant}* ({other}) answers the same label "
                    f"{GAP_FORMS[gap.form]!r}: two right answers")
    topics = reading_topics(gap.lemma, "V" if gap.form in VERB_TOPICS else "S", gap.form)
    if topics is not None and not topics <= ctx.topics:
        return f"asks for {gap.form}, not introduced by unit {ctx.unit.n}"
    return None


def check(material: Material, words: sqlite3.Connection | None) -> Report:
    """Run gates 2–7 over a parsed draft (gate 1, the schema, is `check_text`'s)."""
    from ..comprehension import normalise, verify

    ctx = _Context(material, words)
    report = Report(material)
    if ctx.unit is None:
        report.failures.append(Finding("schema", "unit", f"no unit {material.unit!r}"))
        return report
    if not ctx.levels:
        report.failures.append(Finding(
            "level", "word list", "EKI's level list is not imported "
            "(`cli import-levels`): the level gate cannot run"))
        return report
    lines = material.lines()

    # The text itself: any failure fails the draft.
    for gate, run in (("vabamorf", _vabamorf), ("level", _level), ("forms", _forms)):
        for n, line in enumerate(lines):
            for problem in run(ctx, _words(line)):
                report.failures.append(Finding(gate, f"line {n + 1}", problem))

    # Questions, each through the gates in order; the first to refuse drops it.
    body = material.body()
    seen_q: set[str] = set()
    seen_a: set[str] = set()
    for q in material.questions:
        where = f"question {q.id}"
        words_q = _words(q.question)
        reason = None
        for gate, run in (("vabamorf", _vabamorf), ("level", _level), ("forms", _forms)):
            problems = run(ctx, words_q)
            if problems:
                reason = Finding(gate, where, problems[0])
                break
        if reason is None and verify(body, q.question, q.answer) is None:
            reason = Finding("answers", where, f"*{q.answer}* is not the text's words "
                             "verbatim and once, or the question gives it away")
        if reason is None and (normalise(q.question) in seen_q
                               or normalise(q.answer) in seen_a):
            reason = Finding("duplicates", where, "asked or answered already")
        if reason is not None:
            report.dropped.append(reason)
            continue
        seen_q.add(normalise(q.question))
        seen_a.add(normalise(q.answer))
        report.questions.append(q)

    seen_g: set[tuple[int, str]] = set()
    for g in material.gaps:
        why = _gap(ctx, g, lines)
        if why is not None:
            report.dropped.append(Finding("gaps", f"gap {g.id}", why))
        elif (g.at, g.word.casefold()) in seen_g:
            report.dropped.append(Finding("duplicates", f"gap {g.id}", "the same gap twice"))
        else:
            seen_g.add((g.at, g.word.casefold()))
            report.gaps.append(g)

    unused = ctx.off_list - ctx.off_list_used
    for lemma in sorted(unused):
        why = ("on EKI's list at this stage" if ctx.levels.get(lemma) in ctx.stage_levels
               else "not used")
        report.failures.append(Finding("level", "off_list",
                                       f"{lemma} is declared off-list but {why}"))
    if len(report.questions) < MIN_QUESTIONS:
        report.failures.append(Finding(
            "answers", "questions",
            f"{len(report.questions)} questions survive, fewer than {MIN_QUESTIONS}"))
    return report


def check_text(raw: str, words: sqlite3.Connection | None) -> tuple[Material | None, Report | None, list[Finding]]:
    """Gate 1 then the rest: (material, report, schema failures)."""
    from pydantic import ValidationError

    try:
        material = Material.model_validate_json(raw)
    except (ValidationError, ValueError) as exc:
        errors = getattr(exc, "errors", None)
        found = ([Finding("schema", ".".join(str(p) for p in e.get("loc", ())) or "draft",
                          e.get("msg", "invalid")) for e in errors()]
                 if callable(errors) else [Finding("schema", "draft", str(exc))])
        return None, None, found
    if material.checks is not None and "blind" not in material.checks:
        return None, None, [Finding("schema", "checks", "written by the author, not the pipeline")]
    return material, check(material, words), []
