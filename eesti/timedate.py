"""Telling the time (`kellaaeg`) and dates (`kuupaevad`).

Rules and their sources:

- `pool kümme` is 9.30, `veerand kümme` 9.15, `kolmveerand kümme` 9.45: the
  fraction counts towards the *next* hour (Opiq, *Kellaaeg*, the 4th-grade
  course on the national curriculum).
- A full hour is `kell` + the numeral: *Ma ärkan kell seitse* (Opiq), *kontsert
  algab kell 19* (EKI teatmik, *Arvukirjutus*).
- A time is in `alalütlev` (*Nad sõidavad neljapäeval maale*, EKK M 59); a
  deadline in `saav` (*Koosolek määrati reedeks*, EKK M 61; *30.
  kuupäevaks*, teatmik); a start in `seestütlev` and an end in `rajav`
  (*hommikust õhtuni*, EKK M 57; *pood on lahti kella 22-ni*, teatmik).
- A date is an ordinal in `alalütlev` with the month in `alalütlev`: *5. ja 6.
  mail*, *2. märtsil* (teatmik).

Every answer is synthesised by Vabamorf; the frames only place it.
"""

from __future__ import annotations

import random

from .item import BLANK
from .morph import synthesize
from .patterns import ORDINALS, PatternDrill

HOURS = ("üks", "kaks", "kolm", "neli", "viis", "kuus", "seitse", "kaheksa",
         "üheksa", "kümme", "üksteist", "kaksteist")

#: Each weekday with the Russian after в (when), к (by) and до (until).
WEEKDAYS = (
    ("esmaspäev", "в понедельник", "к понедельнику", "до понедельника"),
    ("teisipäev", "во вторник", "ко вторнику", "до вторника"),
    ("kolmapäev", "в среду", "к среде", "до среды"),
    ("neljapäev", "в четверг", "к четвергу", "до четверга"),
    ("reede", "в пятницу", "к пятнице", "до пятницы"),
    ("laupäev", "в субботу", "к субботе", "до субботы"),
    ("pühapäev", "в воскресенье", "к воскресенью", "до воскресенья"),
)

MONTHS = (("jaanuar", "январь"), ("veebruar", "февраль"), ("märts", "март"),
          ("aprill", "апрель"), ("mai", "май"), ("juuni", "июнь"), ("juuli", "июль"),
          ("august", "август"), ("september", "сентябрь"), ("oktoober", "октябрь"),
          ("november", "ноябрь"), ("detsember", "декабрь"))

#: Fraction of the hour, its word and the frame (Opiq's own sentences).
FRACTIONS = (
    (15, "veerand", "Tunnid algavad kell veerand {}."),
    (30, "pool", "Rong väljub kell pool {}."),
    (45, "kolmveerand", "Ma ärkan kell kolmveerand {}."),
)

#: Case frames for the hour and the weekday: tag, question, frame, and the
#: Russian for what it asks.
HOUR_CASES = (
    ("sg tr", "mis kellaks?", "Töö peab kell {} valmis olema.", "к {n} часам"),
    ("sg el", "mis kellast?", "Pood on lahti kella {} kella kümneni.", "с {n} часов"),
    ("sg ter", "mis kellani?", "Pood on lahti kella {}.", "до {n} часов"),
)
DAY_CASES = (
    ("sg ad", "millal?", "Me sõidame {} maale.", 1),
    ("sg tr", "mis päevaks?", "Koosolek määrati {}.", 2),
    ("sg ter", "mis päevani?", "Pood on avatud esmaspäevast {}.", 3),
)


def _one(lemma: str, tag: str) -> str | None:
    found = synthesize(lemma, tag) or []
    return found[0] if found else None


def ordinal(n: int) -> str | None:
    """The ordinal lemma for 1–31: `esimene`, `kaheksateistkümnes`, `kahekümne esimene`."""
    units = dict((i + 1, o) for i, (_, o) in enumerate(ORDINALS))
    cardinals = dict((i + 1, c) for i, (c, _) in enumerate(ORDINALS))
    if n <= 10:
        return units[n]
    if n < 20:
        stem = _one(cardinals[n - 10], "sg g")
        return f"{stem}teistkümnes" if stem else None
    tens = {2: "kahekümne", 3: "kolmekümne"}[n // 10]
    return f"{tens}s" if n % 10 == 0 else f"{tens} {units[n % 10]}"


def ordinal_form(n: int, tag: str) -> str | None:
    """An ordinal in one case. In `kahekümne esimesel` only the last word declines."""
    lemma = ordinal(n)
    if not lemma:
        return None
    head, _, last = lemma.rpartition(" ")
    form = _one(last, tag)
    if not form:
        return None
    return f"{head} {form}" if head else form


def time_drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    out: list[PatternDrill] = []
    makers = [_clock, _full_hour, _hour_case, _day_case]
    for i in range(count * 3):
        if len(out) >= count:
            break
        item = makers[i % len(makers)](rng)
        if item and all((item.prompt, item.answer_ru) != (o.prompt, o.answer_ru)
                        for o in out):
            out.append(item)
    rng.shuffle(out)
    return out


def _clock(rng) -> PatternDrill | None:
    hour = rng.randrange(1, 13)
    minutes, word, frame = rng.choice(FRACTIONS)
    nxt = HOURS[hour % 12]
    return PatternDrill(
        frame.format(BLANK), nxt, HOURS[hour - 1], "", "kellaaeg", "clock",
        f"*{word} {nxt}* = {hour}.{minutes:02d}: доля считается к **следующему** "
        f"часу, как в русском «половина десятого». Не *{word} {HOURS[hour - 1]}*.",
        "kellaaeg", "A1", answer_ru=(f"{hour}.{minutes:02d}",))


def _full_hour(rng) -> PatternDrill | None:
    hour = rng.randrange(1, 13)
    return PatternDrill(
        "Ma ärkan kell {}.".format(BLANK), HOURS[hour - 1],
        _one(HOURS[hour - 1], "sg g") or "", "", "kellaaeg", "clock",
        f"Полный час: **kell** + числительное в nimetav — *kell {HOURS[hour - 1]}*.",
        "kellaaeg", "A1", answer_ru=(f"{hour}.00",))


def _hour_case(rng) -> PatternDrill | None:
    tag, question, frame, ru = rng.choice(HOUR_CASES)
    # The opening hour sits before the closing ten.
    hour = rng.randrange(7, 10) if tag == "sg el" else rng.randrange(1, 13)
    answer = _one(HOURS[hour - 1], tag)
    if not answer:
        return None
    case = {"sg tr": "saav", "sg el": "seestütlev", "sg ter": "rajav"}[tag]
    return PatternDrill(
        frame.format(BLANK), answer, HOURS[hour - 1], "", question, "clock",
        f"{ru.format(n=hour).capitalize()} — **{case}**: *{answer}*.",
        "kellaaeg", "A1", answer_ru=(ru.format(n=hour),))


def _day_case(rng) -> PatternDrill | None:
    row = rng.choice(WEEKDAYS)
    day = row[0]
    tag, question, frame, which = rng.choice(DAY_CASES)
    if tag == "sg ter" and day == "esmaspäev":
        return None
    answer = _one(day, tag)
    if not answer:
        return None
    case = {"sg ad": "alalütlev", "sg tr": "saav", "sg ter": "rajav"}[tag]
    return PatternDrill(
        frame.format(BLANK), answer, day, "", question, "weekday",
        f"{row[which].capitalize()} — **{case}**: *{answer}*.",
        "kellaaeg", "A1", answer_ru=(row[which],))


def date_drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    out: list[PatternDrill] = []
    makers = [_birthday, _deadline, _month]
    for i in range(count * 3):
        if len(out) >= count:
            break
        item = makers[i % len(makers)](rng)
        if item and all((item.prompt, item.answer_ru) != (o.prompt, o.answer_ru)
                        for o in out):
            out.append(item)
    rng.shuffle(out)
    return out


def _birthday(rng) -> PatternDrill | None:
    n = rng.randrange(1, 32)
    month, _ = rng.choice(MONTHS)
    month_ad = _one(month, "sg ad")
    answer = ordinal_form(n, "sg ad")
    if not answer or not month_ad:
        return None
    return PatternDrill(
        f"Minu sünnipäev on {BLANK} {month_ad}.", answer, ordinal(n) or "", "",
        "mitmendal?", "date",
        f"Дата: **порядковое** числительное в alalütlev — *{answer} {month_ad}* "
        f"(пишется *{n}. {month_ad}*).",
        "kuupaevad", "A2", answer_ru=(f"{n}.",))


def _deadline(rng) -> PatternDrill | None:
    n = rng.randrange(1, 32)
    answer = ordinal_form(n, "sg tr")
    if not answer:
        return None
    return PatternDrill(
        f"Töö tuleb esitada {BLANK} kuupäevaks.", answer,
        ordinal_form(n, "sg ad") or "", "", "mitmendaks?", "date",
        f"Срок — **saav**, и числительное согласуется: *{answer} kuupäevaks* "
        f"(пишется *{n}. kuupäevaks*).",
        "kuupaevad", "A2", answer_ru=(f"{n}.",))


def _month(rng) -> PatternDrill | None:
    month, month_ru = rng.choice(MONTHS)
    answer = _one(month, "sg ad")
    if not answer:
        return None
    n = rng.randrange(1, 29)
    return PatternDrill(
        f"Puhkus algab {n}. {BLANK}.", answer, month, "", "millal?", "date",
        f"Месяц в дате — тоже **alalütlev**: *{n}. {answer}* ({month_ru}).",
        "kuupaevad", "A2", answer_ru=(month_ru,))
