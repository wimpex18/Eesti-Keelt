"""HARNO's reading and listening task types, generated here and keyed by code.

The exam's tasks are HARNO's and stay in `Eksam` as HARNO printed them. What
this module makes is the *task type*: the same instruction, item shape, answer
format and question numbers, over material the app can key without inventing an
answer (ADR-0009, exam loops). Each type has a code, `<level>-<part><no>`:

| Code | HARNO's task | Here | Key |
|---|---|---|---|
| `B1-ku1`, `A2-ku1` | Kuulamine 1: a short exchange, tick A/B/C | two TTS voices say a time, price, date or number | the value the frame was filled with |
| `B1-ku3`, `A2-ku3` | Kuulamine 3: write a word or number in the gap | a heard text, the same sentences printed with one word out | the heard word, accepted as a Vabamorf lemma set |
| `B1-lu3`, `A2-lu5` | Lugemine 3 (A2: 5): a text with three-option gaps | the reading corpus or checked material | the text's own form; the two others are forms of the same lemma a rule rules out |
| `B1-lu4` | Lugemine 4: removed phrases from a larger bank | S1's checked texts | each phrase's place in the text |

Sources of each rule a gap is built on: agreement with a personal pronoun
(`morph.agreement_errors`, after GiellaLT), negation takes the partitive
(`cloze.negation_clozes`), a cardinal other than *üks* takes the singular
partitive (the `arvsonad` drill) as words of quantity take the partitive, a
postposition after `omastav` (EKK M 11).
The listening frames were written by a model (Claude Opus 5.5) in HARNO's
format, every word one Vabamorf knows; the values in them are code's.

Nothing here decides mastery or FSRS: a mock is exam evidence (`eesti/mock.py`).
"""

from __future__ import annotations

import random
import re
import sqlite3
from dataclasses import dataclass, field

from .item import BLANK, accepts

#: Who wrote the listening frames and instructions. Shown with every section.
FRAMES_BY = "Claude Opus 5.5 (модель); формат заданий — HARNO"

#: HARNO's answer letters. G and J are skipped, as on the paper: the exam-day
#: sheet asks for C/G and I/J to be told apart (`eesti/examday.py`).
LETTERS = "ABCDEFHIK"


@dataclass(frozen=True)
class TaskType:
    code: str
    level: str
    part: str
    no: int
    #: The question numbers HARNO prints for this task.
    first: int
    count: int
    #: `choice` (a letter) or `short` (a word or a number).
    answer: str
    et: str
    instruction_et: str
    instruction_ru: str
    #: What this is against HARNO's own task, in Russian.
    note_ru: str

    @property
    def last(self) -> int:
        return self.first + self.count - 1

    def minutes(self) -> int:
        """The part's minutes, shared by question count (`PART_QUESTIONS`), rounded up."""
        from .exam import SPECS

        whole = SPECS[self.level].part(self.part).minutes
        return -(-whole * self.count // PART_QUESTIONS[(self.level, self.part)])

    def to_dict(self) -> dict:
        return {"code": self.code, "level": self.level, "part": self.part,
                "no": self.no, "first": self.first, "last": self.last,
                "answer": self.answer, "et": self.et,
                "instruction_et": self.instruction_et,
                "instruction_ru": self.instruction_ru, "note": self.note_ru,
                "minutes": self.minutes()}


#: How many questions each part has on HARNO's paper, from its sample tasks
#: (the last question number of the part's last task).
PART_QUESTIONS = {("A2", "kuulamine"): 25, ("A2", "lugemine"): 30,
                  ("B1", "kuulamine"): 30, ("B1", "lugemine"): 33}

_KU1_ET = "Kuulake dialoogi ja valige õige vastus: A, B või C."
_KU1_RU = ("Послушай короткий диалог (два голоса) и выбери ответ. Запись "
           "можно прослушать два раза, как на экзамене.")
_KU1_NOTE = ("На экзамене ответы — картинки, числа или слова. Здесь — только "
             "числа: время, цены, даты и номера, в фразах, написанных моделью; "
             "ответ задаёт код. Голоса синтезированы (TartuNLP).")
_KU3_ET = "Kuulake teksti ja kirjutage lünka sobiv sõna või number."
_KU3_RU = ("Послушай текст и впиши в пропуск слово или число. Засчитывается "
           "любая форма нужного слова (по лемме Vabamorf); число можно цифрами.")
_KU3_NOTE = ("На экзамене напечатан пересказ услышанного. Здесь напечатаны те же "
             "предложения, что звучат, с одним словом пропущенным.")
_LU3_ET = "Lugege teksti. Valige lünka sobiv sõna ja kirjutage lünka tähe A, B või C."
_LU3_RU = ("Прочитай текст и впиши в каждый пропуск букву подходящего слова. "
           "Варианты — формы одного слова; правило, которое отсекает лишние, "
           "покажем после ответа.")
_LU3_NOTE = ("На экзамене варианты — разные слова. Здесь — формы одного слова: "
             "код может доказать, что подходит только одна.")
_LU4_ET = ("Lugege teksti. Valige lünka sobiv variant ja kirjutage lünka tähe. "
           "Üks variant jääb üle.")
_LU4_RU = ("Из текста убраны части предложений. Впиши в каждый пропуск букву "
           "подходящей части; одна часть лишняя.")
_LU4_NOTE = ("Текст написан моделью и проверен Vabamorf и автоматическими "
             "проверками (ADR-0009); ключ — место каждой части в этом тексте.")

TYPES: dict[str, TaskType] = {t.code: t for t in (
    TaskType("B1-ku1", "B1", "kuulamine", 1, 1, 7, "choice",
             "Arvud, kellaajad, hinnad ja kuupäevad", _KU1_ET, _KU1_RU, _KU1_NOTE),
    TaskType("B1-ku3", "B1", "kuulamine", 3, 14, 8, "short",
             "Lünkülesanne", _KU3_ET, _KU3_RU, _KU3_NOTE),
    TaskType("B1-lu3", "B1", "lugemine", 3, 16, 10, "choice",
             "Lüngad tekstis", _LU3_ET, _LU3_RU, _LU3_NOTE),
    TaskType("B1-lu4", "B1", "lugemine", 4, 26, 8, "choice",
             "Fraasid teksti", _LU4_ET, _LU4_RU, _LU4_NOTE),
    TaskType("A2-ku1", "A2", "kuulamine", 1, 1, 7, "choice",
             "Arvud, kellaajad, hinnad ja kuupäevad", _KU1_ET, _KU1_RU, _KU1_NOTE),
    TaskType("A2-ku3", "A2", "kuulamine", 3, 14, 6, "short",
             "Lünkülesanne", _KU3_ET, _KU3_RU, _KU3_NOTE),
    TaskType("A2-lu5", "A2", "lugemine", 5, 23, 8, "choice",
             "Lüngad tekstis", _LU3_ET, _LU3_RU, _LU3_NOTE),
)}


def for_part(level: str, part: str) -> list[TaskType]:
    """The task types built for one part, in HARNO's order."""
    return sorted((t for t in TYPES.values() if t.level == level and t.part == part),
                  key=lambda t: t.no)


def by_number(level: str, part: str, no: int) -> TaskType:
    for t in for_part(level, part):
        if t.no == no:
            return t
    raise KeyError(f"no task {no} in {level} {part}")


@dataclass(frozen=True)
class Question:
    """One question of a task. The fields `itemref.sign` reads are the key:

    - `answer` the key: the right option (choice) or the heard word (short);
    - `distractor` every option in the order shown, ` | `-joined (choice);
    - `lemma` the accepted lemmas, ` ~ `-joined (short);
    - `hint` the words that decide the answer, for the review's evidence;
    - `say` what was heard (listening), for the review's transcript.
    """

    code: str
    no: int
    prompt: str
    answer: str
    topic: str
    rule: str
    why_ru: str
    options: tuple[str, ...] = ()
    lemma: str = ""
    hint: str = ""
    say: str = ""
    source_id: str = ""
    #: Listening 1: the exchange, as (voice, text) turns.
    turns: tuple[tuple[str, str], ...] = ()

    @property
    def distractor(self) -> str:
        return " | ".join(self.options)

    def to_page(self) -> dict:
        """What the page shows before the answer: never the key or the rule."""
        out = {"code": self.code, "no": self.no, "prompt": self.prompt,
               "options": [{"letter": LETTERS[i], "text": o}
                           for i, o in enumerate(self.options)]}
        if self.turns:
            out["turns"] = [{"voice": v, "text": t} for v, t in self.turns]
        return out


@dataclass(frozen=True)
class Block:
    """One task of a section: its type, what is read or heard, its questions."""

    type: TaskType
    questions: list[Question]
    #: Reading: the text with numbered gaps. Listening 3: empty (it is heard).
    text: str = ""
    #: Listening 3: the text as (voice, sentence) turns, heard twice.
    audio: tuple[tuple[str, str], ...] = ()
    title: str = ""
    source_id: str = ""
    label: str = ""
    #: Reading 4: the bank, as shown (letters in `LETTERS` order).
    bank: tuple[str, ...] = ()

    def to_page(self, first_index: int) -> dict:
        from .licences import credit

        return self.type.to_dict() | {
            "title": self.title, "text": self.text,
            "audio": [{"voice": v, "text": t} for v, t in self.audio],
            "bank": [{"letter": LETTERS[i], "text": b} for i, b in enumerate(self.bank)],
            "label": self.label, "attribution": credit(self.source_id),
            "first_index": first_index, "count": len(self.questions)}


# --------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------

def chosen(issued: dict, given: str) -> str:
    """The option a choice answer names: its letter, or the option's own text."""
    options = [o for o in (issued.get("distractor") or "").split(" | ") if o]
    said = given.strip()
    if len(said) == 1 and said.upper() in LETTERS[:len(options)]:
        return options[LETTERS.index(said.upper())]
    return next((o for o in options if o.casefold() == said.casefold()), said)


def lemmas_of(word: str) -> set[str]:
    """Every lemma Vabamorf reads a written word as, without guessing."""
    from .morph import _readings

    return {lemma for lemma, _ in _readings(word) if lemma}


def check(issued: dict, given: str) -> bool:
    """Grade one answer against the issued question (`itemref.verify`'s item).

    A choice is right when it names the key. A short answer is right when it is
    the key, or when one of its words is a form of an accepted lemma: the task
    asks what was said, not which form (`18` for *kaheksateist* counts too).
    """
    if issued.get("distractor"):
        return chosen(issued, given) == issued["answer"]
    if accepts(issued["answer"], given):
        return True
    accepted = {lm for lm in (issued.get("lemma") or "").split(" ~ ") if lm}
    words = re.findall(r"[\wõäöüšž-]+", given.casefold())
    return any(lemmas_of(w) & accepted or w in accepted for w in words)


# --------------------------------------------------------------------------
# Listening 1: numbers, times, prices and dates, by two voices
# --------------------------------------------------------------------------

#: Two speakers per exchange, a woman and a man (`providers.tts.VOICES`).
WOMEN = ("mari", "liivika", "kylli", "vesta")
MEN = ("tambet", "kalev", "meelis", "albert", "indrek", "peeter")

#: (question turn, answer turn with `{}`, printed question). Written by a model
#: in HARNO's format; `tests/test_harnotasks.py` holds every word to Vabamorf.
TIME_FRAMES = (
    ("Vabandage, mis kell järgmine buss Tartusse läheb?",
     "Järgmine buss läheb kell {}.", "Mis kell läheb järgmine buss Tartusse?"),
    ("Mis kell film täna algab?", "Film algab kell {}, ära hiljaks jää!",
     "Mis kell algab film?"),
    ("Mis kell me homme kohtume?", "Kohtume kell {} kohviku ees.",
     "Mis kell nad homme kohtuvad?"),
    ("Mis kell on minu aeg arsti juures?", "Teie aeg on homme kell {}.",
     "Mis kell on aeg arsti juures?"),
)
PRICE_FRAMES = (
    ("Kui palju see jope maksab?", "Jope maksab {} eurot.", "Kui palju maksab jope?"),
    ("Palun üks pilet Pärnusse. Kui palju see maksab?",
     "Pilet Pärnusse maksab {} eurot.", "Kui palju maksab pilet Pärnusse?"),
    ("Kui palju ma kokku maksan?", "Kokku teeb {} eurot.",
     "Kui palju tuleb kokku maksta?"),
)
DATE_FRAMES = (
    ("Mis kuupäeval kontsert on?", "Kontsert on {}.", "Mis kuupäeval on kontsert?"),
    ("Millal su puhkus algab?", "Minu puhkus algab {}.", "Mis kuupäeval algab puhkus?"),
    ("Millal te koju tagasi tulete?", "Me tuleme tagasi {}.",
     "Mis kuupäeval nad tagasi tulevad?"),
)
NUMBER_FRAMES = (
    ("Mis bussiga ma kesklinna saan?", "Kesklinna sõidab buss number {}.",
     "Mis numbriga buss sõidab kesklinna?"),
    ("Mitu õpilast teie klassis on?", "Meie klassis on {} õpilast.",
     "Mitu õpilast on klassis?"),
    ("Mis number on teie korter?", "Meie korter on number {}.",
     "Mis number on korter?"),
)

#: Months with 31 days, so a confusable day (13 and 30) is always a real date.
LONG_MONTHS = ((1, "jaanuar"), (3, "märts"), (5, "mai"), (7, "juuli"), (8, "august"),
               (10, "oktoober"), (12, "detsember"))


def _clock(hour: int, minute: int) -> str:
    return f"{(hour - 1) % 12 + 1}.{minute:02d}"


def _time(rng: random.Random) -> tuple[str, str, list[str], str] | None:
    """(spoken, key, two distractors, why). The fraction counts towards the next
    hour (`timedate.FRACTIONS`, Opiq): *pool kaheksa* is 7.30, and 8.30 is the
    mistake it invites."""
    from .timedate import HOURS

    h = rng.randrange(1, 13)              # the hour the learner hears
    said = HOURS[h - 1]
    kind = rng.choice(("full", "pool", "veerand", "kolmveerand"))
    if kind == "full":
        return (f"{said}", _clock(h, 0), [_clock(h - 1, 30), _clock(h, 30)],
                f"*kell {said}* — ровно {_clock(h, 0)}.")
    minute = {"pool": 30, "veerand": 15, "kolmveerand": 45}[kind]
    other = {"pool": 0, "veerand": 45, "kolmveerand": 15}[kind]
    key = _clock(h - 1, minute)
    wrong = [_clock(h, minute), _clock(h - 1 if other else h, other)]
    share = {"pool": "половина", "veerand": "четверть", "kolmveerand": "три четверти"}[kind]
    return (f"{kind} {said}", key, wrong,
            f"*{kind} {said}* — {key}: {share} *к* часу {h} (дробь считается "
            f"к следующему часу), не {_clock(h, minute)}.")


def _confusable(n: int, rng: random.Random, low: int, high: int) -> list[int]:
    """Numbers a listener mishears `n` as: -teist against -kümmend, the tens
    against the units, one more or one less."""
    near = []
    if 11 <= n <= 19 and (n - 10) * 10 <= high:
        near.append((n - 10) * 10)                  # 13 heard as 30
    if n % 10 == 0 and 10 < n < 100 and n // 10 + 10 <= high:
        near.append(n // 10 + 10)                   # 30 heard as 13
    tens, units = divmod(n, 10)
    if 21 <= n <= 99 and units and units != tens and units * 10 + tens <= high:
        near.append(units * 10 + tens)              # 34 heard as 43
    near += [n + 10, n - 10, n + 1, n - 1]
    out = [m for m in dict.fromkeys(near) if low <= m <= high and m != n]
    first = out[:1] if out[:1] and out[0] in near[:3] else []
    rest = [m for m in out if m not in first]
    rng.shuffle(rest)
    return (first + rest)[:2]


def _number(rng: random.Random, low: int, high: int) -> tuple[str, str, list[str], str]:
    from .numbers import written

    n = rng.randrange(low, high + 1)
    spoken = written(n).split(" ~ ")[0]
    why = (f"*{spoken}* = {n}. Слушай окончание: **-teist** — от 11 до 19, "
           f"**-kümmend** — десятки (EKK O 42).")
    return spoken, str(n), [str(m) for m in _confusable(n, rng, low, high)], why


def _date(rng: random.Random) -> tuple[str, str, list[str], str] | None:
    from .morph import synthesize
    from .timedate import ordinal_form

    month_no, month = rng.choice(LONG_MONTHS)
    month_ad = (synthesize(month, "sg ad") or [None])[0]
    n = rng.randrange(1, 32)
    day = ordinal_form(n, "sg ad")
    if not day or not month_ad:
        return None
    wrong = [f"{m}.{month_no:02d}" for m in _confusable(n, rng, 1, 31)]
    key = f"{n}.{month_no:02d}"
    return (f"{day} {month_ad}", key, wrong,
            f"Дата — порядковое числительное в alalütlev: *{day} {month_ad}* = {key}.")


def _price(rng: random.Random) -> tuple[str, str, list[str], str]:
    spoken, key, wrong, why = _number(rng, 2, 99)
    return spoken, f"{key} €", [f"{w} €" for w in wrong], why


_MAKERS = (
    ("kellaaeg", TIME_FRAMES, lambda rng: _time(rng)),
    ("arvud", PRICE_FRAMES, _price),
    ("kuupaevad", DATE_FRAMES, lambda rng: _date(rng)),
    ("arvud", NUMBER_FRAMES, lambda rng: _number(rng, 2, 60)),
)


def listening_numbers(task: TaskType, seed: int) -> Block:
    """Listening 1: each question a two-voice exchange that says one value."""
    rng = random.Random(seed)
    out: list[Question] = []
    tries = 0
    while len(out) < task.count and tries < task.count * 10:
        tries += 1
        topic, frames, make = _MAKERS[len(out) % len(_MAKERS)]
        made = make(rng)
        if not made:
            continue
        spoken, key, wrong, why = made
        if len(set(wrong) | {key}) != 3:
            continue
        asked, answered, printed = rng.choice(frames)
        if any(q.prompt == printed and q.answer == key for q in out):
            continue
        options = [key, *wrong]
        rng.shuffle(options)
        a, b = rng.choice(WOMEN), rng.choice(MEN)
        if rng.random() < 0.5:
            a, b = b, a
        reply = answered.format(spoken)
        out.append(Question(
            code=task.code, no=task.first + len(out), prompt=printed, answer=key,
            topic=topic, rule=f"{task.code}/{topic}", why_ru=why,
            options=tuple(options), hint=spoken, say=f"{asked} — {reply}",
            turns=((a, asked), (b, reply))))
    return Block(task, out, label=FRAMES_BY)


# --------------------------------------------------------------------------
# Texts the reading and the listening 3 tasks are built on
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Text:
    title: str
    sentences: tuple[str, ...]
    source_id: str
    #: A voice per sentence (a dialogue's speakers), or empty for one reader.
    voices: tuple[str, ...] = ()
    label: str = ""


def _stage_fits(unit_id: str, level: str) -> bool:
    from .units import STAGES, by_id

    try:
        stage = by_id(unit_id).stage
    except KeyError:
        return False
    return STAGES.index(stage) <= STAGES.index(level) if level in STAGES else True


def material_texts(content: sqlite3.Connection | None, level: str,
                   kinds: tuple[str, ...] = ("dialoog", "tekst")) -> list[Text]:
    """S1's checked material (`eesti/material/store.py`), at or below `level`."""
    from .material import LABEL, SOURCE_ID
    from .material.schema import Material
    from .morph import split_sentences

    if content is None or not content.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='material'").fetchone():
        return []
    out: list[Text] = []
    marks = ",".join("?" * len(kinds))
    for row in content.execute(
            f"SELECT doc FROM material WHERE kind IN ({marks}) ORDER BY id",  # noqa: S608
            kinds):
        m = Material.model_validate_json(row[0])
        if not _stage_fits(m.unit, level):
            continue
        if m.kind == "dialoog":
            voices = _cast(m)
            out.append(Text(m.title, tuple(t.text for t in m.turns), SOURCE_ID,
                            tuple(voices[t.speaker] for t in m.turns), LABEL))
        else:
            out.append(Text(m.title, tuple(s for p in m.paragraphs
                                           for s in split_sentences(p)), SOURCE_ID,
                            label=LABEL))
    return out


def _cast(material) -> dict[str, str]:
    """A voice per speaker, alternating women and men, stable for the material."""
    pool = [v for pair in zip(WOMEN, MEN) for v in pair]
    return {s.id: pool[i % len(pool)] for i, s in enumerate(material.speakers)}


def corpus_texts(content: sqlite3.Connection | None, rng: random.Random,
                 words: sqlite3.Connection | None = None, level: str = "B1",
                 limit: int = 40, scan: int = 160) -> list[Text]:
    """Texts of the reading corpus the learner may see (the connection's scope).

    With a word list, only texts whose running words are at least 80 % on it at
    or below `level` (`difficulty.FLOOR`, the library's own threshold): a
    rule of thumb about vocabulary, not a CEFR level for the text."""
    from .cloze import _usable
    from .difficulty import FLOOR, reach_lemmas, within_reach
    from .mock import _up_to
    from .morph import split_sentences

    if content is None:
        return []
    rows = list(content.execute(
        "SELECT id, title, body, source_id FROM items"
        " WHERE source_id = 'selges-keeles' AND body <> '' ORDER BY id"))
    rng.shuffle(rows)
    reach = reach_lemmas(words, _up_to(level)) if words is not None else frozenset()
    out = []
    for row in rows[:scan]:
        if len(out) >= limit:
            break
        if reach and within_reach(row["body"], frozenset(), reach)["coverage"] < FLOOR:
            continue
        sentences = tuple(s for s in split_sentences(row["body"]) if _usable(s))
        if sentences:
            out.append(Text(row["title"] or "", sentences, row["source_id"]))
    return out


def _known(sentence: str) -> bool:
    """No lowercase word Vabamorf does not know: such a word is usually one broken
    by the source's layout, and the task would teach it."""
    from .morph import _readings, tokenize

    return all(not (w.isalpha() and w.islower()) or _readings(w) for w in tokenize(sentence))


# --------------------------------------------------------------------------
# Listening 3: a heard text, the gaps written, any form of the word
# --------------------------------------------------------------------------

#: Parts of speech a heard gap may be, the likelier first: HARNO's answers are
#: mostly numbers (which may be written in digits) and nouns.
_HEARD_POS = ("N", "S", "V", "A")


def _numeral_value(lemma: str) -> int | None:
    from .numbers import written

    for n in range(101):
        if lemma in written(n).split(" ~ "):
            return n
    return None


def _heard_gap(sentence: str, words: sqlite3.Connection | None,
               levels: tuple[str, ...]) -> tuple[int, int, str, set[str]] | None:
    """The word to write: a noun, numeral, verb or adjective on the word list at
    `levels` (a numeral always), one Vabamorf reads without guessing."""
    from .cloze import _level_of
    from .morph import analyze

    best = None
    for token in analyze(sentence):
        if token.pos not in _HEARD_POS or len(token.text) < 3:
            continue
        if not token.text.isalpha():
            continue
        accepted = lemmas_of(token.text)
        if token.lemma not in accepted:
            continue
        if token.pos != "N":
            level = _level_of(words, token.lemma)
            if words is not None and level not in levels:
                continue
        value = _numeral_value(token.lemma) if token.pos == "N" else None
        if value is not None:
            accepted |= {str(value)}
        rank = _HEARD_POS.index(token.pos)
        if best is None or rank < best[0]:
            best = (rank, (token.start, token.end, token.text, accepted | {token.lemma}))
    return best[1] if best else None


def listening_gaps(task: TaskType, seed: int, texts: list[Text],
                   words: sqlite3.Connection | None) -> Block | None:
    """Listening 3 over the first text that yields `count` gaps (at least 4)."""
    from .mock import _up_to

    levels = _up_to(task.level)
    rng = random.Random(seed)
    for text in texts:
        sentences = [s for s in text.sentences if 3 <= len(s.split()) <= 20]
        if len(sentences) < 4:
            continue
        start = rng.randrange(0, max(1, len(sentences) - task.count))
        window = text.sentences[text.sentences.index(sentences[start]):]
        heard: list[tuple[str, str]] = []
        out: list[Question] = []
        for i, sentence in enumerate(window):
            if len(out) >= task.count or len(heard) >= task.count + 4:
                break
            voice = (text.voices[text.sentences.index(sentence)] if text.voices
                     else WOMEN[seed % len(WOMEN)])
            heard.append((voice, sentence))
            if not (3 <= len(sentence.split()) <= 20) or not _known(sentence):
                continue
            gap = _heard_gap(sentence, words, levels)
            if gap is None:
                continue
            lo, hi, key, accepted = gap
            out.append(Question(
                code=task.code, no=task.first + len(out),
                prompt=sentence[:lo] + BLANK + sentence[hi:], answer=key,
                topic="", rule=f"{task.code}/heard",
                why_ru=f"В записи: «{sentence}». Засчитывается любая форма слова "
                       f"*{key}* (лемма по Vabamorf).",
                lemma=" ~ ".join(sorted(accepted)), hint=key, say=sentence,
                source_id=text.source_id))
        if len(out) >= min(4, task.count):
            return Block(task, out, audio=tuple(heard), title=text.title,
                         source_id=text.source_id, label=text.label)
    return None


# --------------------------------------------------------------------------
# Reading 3 (A2: 5): three forms of one lemma, one of which the text allows
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Gap:
    start: int
    end: int
    key: str
    lemma: str
    form: str
    options: tuple[str, ...]        # two distractors
    topic: str
    rule: str
    why_ru: str
    #: The words in the sentence that decide the gap.
    trigger: str


#: Postpositions that follow `omastav` and nothing else (EKK M 11): *laua all*,
#: *maja ees*. Words that are also prepositions or verb particles are left out.
GENITIVE_POSTPOSITIONS = frozenset({
    "all", "alla", "alt", "ees", "ette", "eest", "ääres", "äärde", "äärest",
    "juures", "juurde", "juurest", "kõrval", "kõrvale", "kõrvalt", "taga", "taha",
    "tagant", "kohta", "sees", "seest", "sisse", "peal", "pealt", "jaoks", "abil",
    "kaudu", "tõttu", "lähedal", "lähedale", "keskel", "vahel", "vahele",
})

#: Words of quantity that take the partitive: *mitu* the singular (*mitu
#: raamatut*), *palju* and *vähe* either number (*palju sõpru*, *vähe aega*).
QUANTITY = {"mitu": ("sg p",), "palju": ("sg p", "pl p"), "vähe": ("sg p", "pl p")}

#: Personal pronouns whose written form is only ever the nominative, so a verb
#: just before one (*Eile käisin ma*) has it as its subject.
SHORT_PRONOUNS = frozenset({"ma", "sa", "ta", "me", "te", "nad"})

_TENSE_TOPIC = {0: "olevik", 1: "lihtminevik", 2: "tingiv"}
_PERSON_RU = ("1-го лица ед. ч.", "2-го лица ед. ч.", "3-го лица ед. ч.",
              "1-го лица мн. ч.", "2-го лица мн. ч.", "3-го лица мн. ч.")


def _foreign(form: str, lemma: str, tag: str) -> bool:
    """Is `form` a form that cannot also be read as `lemma` in `tag`? A distractor
    that is a homograph of the key would be a second right answer."""
    from .morph import _readings

    readings = _readings(form)
    return bool(readings) and (lemma, tag) not in readings


def _case_distractors(lemma: str, tag: str, key: str, tags: tuple[str, ...],
                      rng: random.Random) -> tuple[str, ...] | None:
    from .morph import unique_form

    found: list[str] = []
    for other in tags:
        form = unique_form(lemma, other)
        if (form and form.casefold() != key.casefold()
                and form.casefold() not in {f.casefold() for f in found}
                and _foreign(form, lemma, tag)):
            found.append(form)
    if len(found) < 2:
        return None
    rng.shuffle(found)
    return tuple(found[:2])


def _agreement_gap(sentence: str, tokens, rng) -> Gap | None:
    from .morph import _FINITE, _FORM_PERSONS, _IMPERATIVE_PARTICLES, _PERSON
    from .morph import _readings, agreement_errors, synthesize

    words = [t for t in tokens if t.pos != "Z"]
    for i, pronoun in enumerate(words[:-1]):
        number, _, case = (pronoun.form or "").partition(" ")
        if pronoun.pos != "P" or case != "n":
            continue
        person = _PERSON.get((pronoun.lemma, number))
        verb = words[i + 1]
        if person is None or verb.pos != "V" or verb.form not in _FORM_PERSONS:
            continue
        if i and words[i - 1].text.casefold() in _IMPERATIVE_PARTICLES:
            continue
        if person not in _FORM_PERSONS[verb.form]:
            continue
        group_no = next(n for n, g in enumerate(_FINITE) if verb.form in g)
        group = _FINITE[group_no]
        wrong: list[str] = []
        for p, tag in enumerate(group):
            if p in _FORM_PERSONS[verb.form]:
                continue
            forms = synthesize(verb.lemma, tag, "V") or []
            if len(forms) != 1 or forms[0].casefold() in {verb.text.casefold(),
                                                          *map(str.casefold, wrong)}:
                continue
            form = forms[0]
            # Not a form of the right person under another reading, and one the
            # agreement check itself refuses after this pronoun.
            if any(lm == verb.lemma and t in group and person in _FORM_PERSONS.get(t, ())
                   for lm, t in _readings(form)):
                continue
            swapped = sentence[:verb.start] + form + sentence[verb.end:]
            if not agreement_errors(swapped):
                continue
            wrong.append(form)
        if len(wrong) < 2 or agreement_errors(sentence):
            continue
        rng.shuffle(wrong)
        return Gap(verb.start, verb.end, verb.text, verb.lemma, verb.form,
                   tuple(wrong[:2]), _TENSE_TOPIC[group_no], "agreement",
                   f"Подлежащее — *{pronoun.text}*, поэтому глагол {_PERSON_RU[person]}: "
                   f"*{verb.text}*. Согласование (ühildumine) подлежащего и сказуемого.",
                   pronoun.text)
    return _inverted_gap(words, rng) or _noun_subject_gap(tokens, rng)


#: Words that join two subjects (*Mari ja Jüri läksid*): a noun next to one is
#: not the whole subject, so no gap is built on it.
_JOINERS = frozenset({"ja", "ning", "või", "ega", "kui", "nagu", "ehk"})

#: Nouns that stand in the nominative as a time or a measure (*iga päev käin*):
#: before a verb they need not be its subject.
_ADVERBIAL_NOUNS = frozenset({
    "päev", "nädal", "kuu", "aasta", "hommik", "õhtu", "öö", "kord", "tund",
    "minut", "aeg", "talv", "suvi", "kevad", "sügis", "nädalavahetus"})


def _opens_clause(tokens, at: int) -> bool:
    """Does the noun at `tokens[at]` open its clause, with only names, adjectives
    and genitive attributes before it (*Uus seadus*, *Eesti valitsus*)?"""
    for t in reversed(tokens[:at]):
        if t.pos == "Z" or t.text.casefold() in _JOINERS:
            return t.text.casefold() not in _JOINERS
        if t.pos == "H" or (t.pos == "A" and t.form == "sg n") or (
                t.pos == "S" and t.form == "sg g"):
            continue
        return False
    return True


def _noun_subject_gap(tokens, rng) -> Gap | None:
    """A singular noun opening its clause, right before a finite verb in the 3rd
    person singular (*Kohtunik selgitas*). The options are 1st and 2nd person
    forms. Built only where the noun can be nothing but the subject: it has no
    reading in another case (*auto* is also the genitive object of *ostsin*),
    it is no time word (*iga päev käin*), it is not plural (a plural total
    object is nominative: *Väravad lõime*), and the verb is not *olema*."""
    from .morph import _FINITE, _FORM_PERSONS, _readings, synthesize

    for i, (noun, verb) in enumerate(zip(tokens, tokens[1:])):
        if noun.pos not in ("S", "H") or noun.form != "sg n":
            continue
        if noun.lemma in _ADVERBIAL_NOUNS or verb.lemma == "olema":
            continue
        # Another case reading could be an object (`auto` is also `sg g`); a verb
        # reading (*seadus* is also *seaduma*) is no case and leaves it a subject.
        if any(" " in form and form != "sg n" for _, form in _readings(noun.text)):
            continue
        if verb.pos != "V" or 2 not in _FORM_PERSONS.get(verb.form, ()):
            continue
        if not _opens_clause(tokens, i):
            continue
        after = tokens[i + 2:i + 3]
        if after and after[0].text.casefold() in _JOINERS:
            continue
        group_no = next(n for n, g in enumerate(_FINITE) if verb.form in g)
        wrong: list[str] = []
        for tag in (_FINITE[group_no][p] for p in (0, 3, 4)):
            forms = synthesize(verb.lemma, tag, "V") or []
            if len(forms) != 1 or forms[0].casefold() in {verb.text.casefold(),
                                                          *map(str.casefold, wrong)}:
                continue
            if any(lm == verb.lemma and _FORM_PERSONS.get(t, set()) & {2, 5}
                   for lm, t in _readings(forms[0])):
                continue
            wrong.append(forms[0])
        if len(wrong) < 2:
            continue
        rng.shuffle(wrong)
        return Gap(verb.start, verb.end, verb.text, verb.lemma, verb.form,
                   tuple(wrong[:2]), _TENSE_TOPIC[group_no], "agreement",
                   f"Подлежащее — существительное *{noun.text}*, поэтому глагол "
                   f"3-го лица ед. ч.: *{verb.text}*, не 1-го или 2-го. "
                   f"Согласование (ühildumine) подлежащего и сказуемого.", noun.text)
    return None


def _inverted_gap(words, rng) -> Gap | None:
    """A verb just before its subject (*Eile käisin ma poes*): the pronoun is one of
    the short forms, which are nominative only, so it is the verb's subject."""
    from .morph import _FINITE, _FORM_PERSONS, _PERSON, _readings, synthesize

    for verb, pronoun in zip(words, words[1:]):
        if pronoun.text.casefold() not in SHORT_PRONOUNS or pronoun.pos != "P":
            continue
        number, _, case = (pronoun.form or "").partition(" ")
        person = _PERSON.get((pronoun.lemma, number))
        if (case != "n" or person is None or verb.pos != "V"
                or person not in _FORM_PERSONS.get(verb.form, ())):
            continue
        group_no = next(n for n, g in enumerate(_FINITE) if verb.form in g)
        group = _FINITE[group_no]
        wrong: list[str] = []
        for p, tag in enumerate(group):
            forms = synthesize(verb.lemma, tag, "V") or []
            if p in _FORM_PERSONS[verb.form] or len(forms) != 1:
                continue
            form = forms[0]
            if form.casefold() in {verb.text.casefold(), *map(str.casefold, wrong)}:
                continue
            if any(lm == verb.lemma and person in _FORM_PERSONS.get(t, ())
                   for lm, t in _readings(form)):
                continue
            wrong.append(form)
        if len(wrong) < 2:
            continue
        rng.shuffle(wrong)
        return Gap(verb.start, verb.end, verb.text, verb.lemma, verb.form,
                   tuple(wrong[:2]), _TENSE_TOPIC[group_no], "agreement",
                   f"Подлежащее — *{pronoun.text}* (стоит после глагола), поэтому глагол "
                   f"{_PERSON_RU[person]}: *{verb.text}*. Согласование (ühildumine) "
                   f"подлежащего и сказуемого.", pronoun.text)
    return None


def _negation_gap(sentence: str, tokens, rng, words) -> Gap | None:
    from .cloze import negation_clozes

    found = negation_clozes([sentence], words, count=1, seed=0)
    if not found:
        return None
    item = found[0]
    start = item.prompt.index(BLANK)
    end = start + len(item.answer)
    if sentence[start:end] != item.answer:
        return None
    options = _case_distractors(item.lemma, "sg p", item.answer,
                                ("sg g", "sg n", "pl n"), rng)
    if not options:
        return None
    negator = next((t.text for t in tokens if t.end <= start
                    and (t.lemma in ("ei", "ega", "ära") or t.text.lower() in
                         ("pole", "polnud", "poleks"))), "ei")
    return Gap(start, end, item.answer, item.lemma, "sg p", options, "obj-case",
               "negation",
               f"Отрицание (*{negator}*) всегда требует **osastav**: *{item.answer}*.",
               negator)


def _numeral_gap(sentence: str, tokens, rng) -> Gap | None:
    words = [t for t in tokens if t.pos != "Z"]
    for numeral, noun in zip(words, words[1:]):
        if (numeral.pos != "N" or numeral.form != "sg n" or numeral.lemma == "üks"
                or not numeral.text.isalpha()):
            continue
        if noun.pos != "S" or noun.form != "sg p" or not noun.text.isalpha():
            continue
        options = _case_distractors(noun.lemma, "sg p", noun.text, ("sg n", "pl n", "pl p"), rng)
        if not options:
            continue
        return Gap(noun.start, noun.end, noun.text, noun.lemma, "sg p", options,
                   "arvsonad", "numeral",
                   f"После количественного числительного *{numeral.text}* (кроме *üks*) "
                   f"существительное стоит в **osastav ainsuses**: *{numeral.text} "
                   f"{noun.text}*.", numeral.text)
    return None


def _quantity_gap(sentence: str, tokens, rng) -> Gap | None:
    words = [t for t in tokens if t.pos != "Z"]
    for word, noun in zip(words, words[1:]):
        allowed = QUANTITY.get(word.text.casefold())
        if not allowed or noun.pos != "S" or noun.form not in allowed:
            continue
        if not noun.text.isalpha():
            continue
        # The other partitive may fit too (*palju sõpru* and *palju sõpra*): only
        # non-partitive forms are offered.
        tags = tuple(t for t in ("sg n", "pl n", "sg g", "pl g", "pl p") if t not in allowed)
        options = _case_distractors(noun.lemma, noun.form, noun.text, tags, rng)
        if not options or any(_has(o, noun.lemma, allowed) for o in options):
            continue
        return Gap(noun.start, noun.end, noun.text, noun.lemma, noun.form, options,
                   "osastav", "quantity",
                   f"После слова количества *{word.text}* существительное стоит в "
                   f"**osastav**: *{word.text} {noun.text}*.", word.text)
    return None


def _has(form: str, lemma: str, tags) -> bool:
    from .morph import _readings

    return any(lm == lemma and t in tags for lm, t in _readings(form))


def _postposition_gap(sentence: str, tokens, rng) -> Gap | None:
    words = [t for t in tokens if t.pos != "Z"]
    for noun, post in zip(words, words[1:]):
        if noun.pos != "S" or noun.form not in ("sg g", "pl g") or not noun.text.isalpha():
            continue
        if post.pos != "K" or post.text.casefold() not in GENITIVE_POSTPOSITIONS:
            continue
        # The other number's genitive fits as well (*laua all*, *laudade all*).
        tags = ("sg n", "sg p", "pl n") if noun.form == "sg g" else ("pl n", "pl p", "sg n")
        options = _case_distractors(noun.lemma, noun.form, noun.text, tags, rng)
        if not options or any(_has(o, noun.lemma, ("sg g", "pl g")) for o in options):
            continue
        return Gap(noun.start, noun.end, noun.text, noun.lemma, noun.form, options,
                   "kaassonad", "postposition",
                   f"Послелог *{post.text}* — после **omastav** (EKK M 11): "
                   f"*{noun.text} {post.text}*.", post.text)
    return None


def find_gap(sentence: str, words: sqlite3.Connection | None,
             levels: tuple[str, ...], rng: random.Random) -> Gap | None:
    """The one gap a sentence gives, if a rule decides it."""
    from .cloze import _above_level, _level_of
    from .morph import analyze

    if not _known(sentence):
        return None
    tokens = analyze(sentence)
    makers = [lambda: _negation_gap(sentence, tokens, rng, words),
              lambda: _numeral_gap(sentence, tokens, rng),
              lambda: _quantity_gap(sentence, tokens, rng),
              lambda: _postposition_gap(sentence, tokens, rng)]
    rng.shuffle(makers)
    # Agreement last: nearly every sentence has a subject, and a task of verb
    # endings alone would test one rule.
    for make in [*makers, lambda: _agreement_gap(sentence, tokens, rng)]:
        gap = make()
        if gap and not _above_level(_level_of(words, gap.lemma), levels):
            return gap
    return None


def _numbered(sentence: str, gap: Gap | None, no: int | None) -> str:
    if gap is None:
        return sentence
    return f"{sentence[:gap.start]}({no}) ____{sentence[gap.end:]}"


#: At most this share of a reading task's gaps is subject–verb agreement.
AGREEMENT_SHARE = 0.5


def reading_gaps(task: TaskType, seed: int, texts: list[Text],
                 words: sqlite3.Connection | None) -> Block | None:
    """Reading 3 over the first text that yields enough gaps (at least 4)."""
    from .mock import _up_to

    levels = _up_to(task.level)
    rng = random.Random(seed)
    for text in texts:
        found: list[tuple[int, Gap]] = []
        for n, sentence in enumerate(text.sentences):
            if len(found) >= task.count:
                break
            if not 3 <= len(sentence.split()) <= 30:
                continue
            gap = find_gap(sentence, words, levels, rng)
            agreed = sum(g.rule == "agreement" for _, g in found)
            if gap and (gap.rule != "agreement" or agreed < AGREEMENT_SHARE * task.count):
                found.append((n, gap))
        if len(found) < min(4, task.count):
            continue
        last = found[-1][0]
        gaps = dict(found)
        shown, questions = [], []
        for n, sentence in enumerate(text.sentences[:last + 2]):
            gap = gaps.get(n)
            no = task.first + len(questions) if gap else None
            shown.append(_numbered(sentence, gap, no))
            if gap:
                options = [gap.key, *gap.options]
                rng.shuffle(options)
                questions.append(Question(
                    code=task.code, no=no,
                    prompt=sentence[:gap.start] + BLANK + sentence[gap.end:],
                    answer=gap.key, topic=gap.topic, rule=f"{task.code}/{gap.rule}",
                    why_ru=gap.why_ru, options=tuple(options), lemma=gap.lemma,
                    hint=gap.trigger, source_id=text.source_id))
        return Block(task, questions, text=" ".join(shown), title=text.title,
                     source_id=text.source_id, label=text.label)
    return None


# --------------------------------------------------------------------------
# Reading 4: phrases taken out of the text, one more in the bank than gaps
# --------------------------------------------------------------------------

#: Words a removable part may open with: conjunctions and relative words.
OPENERS = {
    "kui": "sidesonad", "et": "sidesonad", "sest": "sidesonad", "aga": "sidesonad",
    "kuid": "sidesonad", "ja": "sidesonad", "ning": "sidesonad", "ega": "sidesonad",
    "nagu": "sidesonad", "kuna": "sidesonad", "mis": "asesonad", "mida": "asesonad",
    "mille": "asesonad", "millega": "asesonad", "kes": "asesonad", "keda": "asesonad",
    "kus": "kusisonad", "kuhu": "kusisonad", "kust": "kusisonad",
}


def _removable(sentence: str) -> tuple[int, int, str] | None:
    """The part after a comma that opens with a conjunction or relative word, up to
    the sentence's end: 2–9 words."""
    end = len(sentence.rstrip(".!?"))
    for match in re.finditer(r",\s+(\w+)\b", sentence):
        opener = match.group(1).casefold()
        span = sentence[match.start(1):end]
        if opener in OPENERS and 2 <= len(span.split()) <= 9 and "," not in span:
            return match.start(1), end, opener
    return None


def phrase_bank(task: TaskType, seed: int, texts: list[Text]) -> Block | None:
    """Reading 4 over a checked text with at least 4 removable parts. The extra
    phrase in the bank comes from another checked text, so it is no part of this
    one."""
    rng = random.Random(seed)
    order = list(texts)
    rng.shuffle(order)
    for text in order:
        spans = []
        for n, sentence in enumerate(text.sentences):
            found = _removable(sentence)
            if found:
                spans.append((n, *found))
        spans = spans[:task.count]
        if len(spans) < 4:
            continue
        body = " ".join(text.sentences)
        removed = [text.sentences[n][a:b] for n, a, b, _ in spans]
        if any(body.count(r) != 1 for r in removed):
            continue
        if len({r.casefold() for r in removed}) != len(removed):
            continue
        extra = None
        for other in order:
            if other is text:
                continue
            for sentence in other.sentences:
                got = _removable(sentence)
                if got and sentence[got[0]:got[1]].casefold() not in {
                        r.casefold() for r in removed}:
                    extra = sentence[got[0]:got[1]]
                    break
            if extra:
                break
        if extra is None:
            continue
        bank = [*removed, extra]
        rng.shuffle(bank)
        by_sentence = {n: (a, b, o) for n, a, b, o in spans}
        shown, questions = [], []
        for n, sentence in enumerate(text.sentences):
            if n not in by_sentence:
                shown.append(sentence)
                continue
            a, b, opener = by_sentence[n]
            no = task.first + len(questions)
            shown.append(f"{sentence[:a]}({no}) ____{sentence[b:]}")
            key = sentence[a:b]
            questions.append(Question(
                code=task.code, no=no, prompt=sentence[:a] + BLANK + sentence[b:],
                answer=key, topic=OPENERS[opener], rule=f"{task.code}/phrase",
                why_ru=f"В тексте: «{sentence}»", options=tuple(bank),
                hint=key, source_id=text.source_id))
        return Block(task, questions, text=" ".join(shown), title=text.title,
                     source_id=text.source_id, label=text.label, bank=tuple(bank))
    return None


# --------------------------------------------------------------------------
# A part's blocks
# --------------------------------------------------------------------------

def _evs_texts(words: sqlite3.Connection | None, level: str, seed: int) -> list[Text]:
    """EKI EVS's example phrases as one heard text, where nothing else may be heard."""
    from .evs import SOURCE_ID, phrases
    from .mock import _up_to

    if words is None:
        return []
    pool = [p.estonian for p in phrases(words, 4, 12, _up_to(level))]
    if not pool:
        return []
    rng = random.Random(seed)
    rng.shuffle(pool)
    return [Text("", tuple(p[:1].upper() + p[1:] for p in pool[:24]), SOURCE_ID)]


def build(task: TaskType, *, seed: int, content: sqlite3.Connection | None,
          words: sqlite3.Connection | None) -> Block | None:
    """One task, or None when there is nothing to build it on."""
    rng = random.Random(seed)
    if task.code.endswith("ku1"):
        return listening_numbers(task, seed)
    if task.part == "kuulamine":
        texts = (material_texts(content, task.level, ("dialoog",))
                 + corpus_texts(content, rng, words, task.level))
        rng.shuffle(texts)
        return (listening_gaps(task, seed, texts, words)
                or listening_gaps(task, seed, _evs_texts(words, task.level, seed), words))
    if task.no == 4 and task.level == "B1":
        return phrase_bank(task, seed, material_texts(content, task.level, ("tekst",)))
    texts = material_texts(content, task.level) + corpus_texts(content, rng, words, task.level)
    rng.shuffle(texts)
    return reading_gaps(task, seed, texts, words)


@dataclass
class Section:
    """The HARNO-format part: its blocks, in HARNO's order, and what is left out."""

    level: str
    part: str
    blocks: list[Block] = field(default_factory=list)
    missing: list[TaskType] = field(default_factory=list)

    @property
    def questions(self) -> list[Question]:
        return [q for b in self.blocks for q in b.questions]

    @property
    def minutes(self) -> int:
        return sum(b.type.minutes() for b in self.blocks)


def section(level: str, part: str, *, seed: int, content, words,
            only: int | None = None) -> Section:
    """Every task type this part has, or the one numbered `only`."""
    types = for_part(level, part)
    if only is not None:
        types = [t for t in types if t.no == only]
    out = Section(level, part)
    for n, task in enumerate(types):
        block = build(task, seed=seed + n, content=content, words=words)
        if block and block.questions:
            out.blocks.append(block)
        else:
            out.missing.append(task)
    return out
