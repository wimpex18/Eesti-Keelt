"""Both writing tasks of the exam, in HARNO's format, with a checklist code keeps.

The format is HARNO's (https://harno.ee/eesti-keele-tasemeeksamid, read 9 Oct
2026):

- **B1**, 35 minutes: task 1 (8 raw points) a questionnaire of 10 questions or a
  note — a message, an invitation or a card — of about 50 words; task 2 (12 raw
  points) a story or a personal letter of about 100 words.
- **A2**, 30 minutes: task 1 a text from a business card, at least 25 words;
  task 2 a note, message or invitation, or a creative text, at least 30 words.

HARNO publishes the format, not its prompts, so **these prompts are written by a
model** (Claude Opus 5.5) in that format, every word one Vabamorf knows, and the
page says so. Nothing here is a score: code checks what it can — the length
against HARNO's figure, whether each point the prompt asks for shows up (by the
words and forms that carry it), a letter's greeting and closing, and the
deterministic grammar checks — and says it is a checklist, not a mark. A model's
reading of the text, when there is one, is labelled advisory (ADR-0009).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

PROMPTS_BY = "Claude Opus 5.5 (модель); формат заданий — HARNO"

#: What each kind is called, as the exam calls it.
KIND_ET = {"teade": "Teade", "kusimustik": "Küsimustik", "jutt": "Jutt",
           "kiri": "Isiklik kiri", "visiitkaart": "Visiitkaart", "loovtekst": "Loovtekst"}

#: Raw points per task, HARNO's (B1 only: A2's split is not published).
POINTS = {("B1", 1): 8, ("B1", 2): 12}


@dataclass(frozen=True)
class Point:
    """One thing the prompt asks for, and the evidence that it was written."""

    et: str
    ru: str
    test: str                       # a detector in `_DETECT`
    lemmas: tuple[str, ...] = ()


@dataclass(frozen=True)
class Task:
    id: str
    level: str
    task_no: int
    kind: str
    prompt_et: str
    prompt_ru: str
    target_words: int               # B1: "about"; A2: "at least"
    points: tuple[Point, ...] = ()
    questions: tuple[str, ...] = ()
    card: tuple[str, ...] | None = None
    letter: bool = False

    @property
    def at_least(self) -> bool:
        return self.level == "A2"

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "kind_et": KIND_ET[self.kind],
                "prompt_et": self.prompt_et, "prompt_ru": self.prompt_ru,
                "target_words": self.target_words, "at_least": self.at_least,
                "questions": list(self.questions), "card": list(self.card or ()),
                "letter": self.letter,
                "points": [{"et": p.et, "ru": p.ru} for p in self.points]}


_REASON = Point("miks", "почему", "lemmas",
                ("sest", "kuna", "sellepärast", "seetõttu", "põhjus"))
_WHEN = Point("millal", "когда", "time")
_WHERE_TO = Point("kuhu", "куда", "place_to")
_WHERE_AT = Point("kus", "где", "place_at")
_WITH = Point("kellega", "с кем", "with")
_WHAT_HAPPENED = Point("mis juhtus", "что случилось (прошедшее время)", "past")

BANK: dict[str, tuple[Task, ...]] = {
    "B1": (
        Task("b1-teade-kino", "B1", 1, "teade",
             "Sa ei saa homme sõbraga kinno minna. Kirjuta sõbrale teade (umbes 50 "
             "sõna): miks sa ei saa tulla, millal te võiksite kokku saada ja kuhu "
             "võiksite minna.",
             "Ты не можешь завтра пойти с другом в кино. Напиши ему сообщение "
             "(около 50 слов): почему, когда встретиться и куда пойти.",
             50, (_REASON, _WHEN, _WHERE_TO)),
        Task("b1-teade-kutse", "B1", 1, "teade",
             "Sul on laupäeval sünnipäev. Kirjuta kolleegile kutse (umbes 50 sõna): "
             "kus ja millal pidu on, mida kaasa võtta ja kuidas sinna saada.",
             "В субботу у тебя день рождения. Напиши коллеге приглашение (около "
             "50 слов): где и когда праздник, что взять с собой и как добраться.",
             50, (_WHERE_AT, _WHEN,
                  Point("mida kaasa võtta", "что взять с собой", "lemmas",
                        ("kaasa", "võtma", "tooma")),
                  Point("kuidas sinna saada", "как добраться", "lemmas",
                        ("buss", "tramm", "troll", "rong", "auto", "takso", "jala",
                         "sõitma", "peatus", "sõit")))),
        Task("b1-teade-naaber", "B1", 1, "teade",
             "Sa sõidad nädalaks ära. Kirjuta naabrile teade (umbes 50 sõna): kuhu "
             "ja kui kauaks sa sõidad ja millega naaber võiks sind aidata.",
             "Ты уезжаешь на неделю. Напиши соседу записку (около 50 слов): куда "
             "и надолго ли едешь и чем сосед мог бы помочь.",
             50, (_WHERE_TO,
                  Point("kui kauaks", "надолго ли", "time"),
                  Point("abi", "чем помочь", "lemmas",
                        ("aitama", "abi", "kastma", "lill", "post", "toitma", "kass",
                         "koer", "võti", "vaatama")))),
        Task("b1-kusimustik-kursus", "B1", 1, "kusimustik",
             "Sa tahad minna eesti keele kursusele. Vasta ankeedi küsimustele "
             "täislausetega.",
             "Ты хочешь записаться на курсы эстонского. Ответь на вопросы анкеты "
             "полными предложениями.",
             50, questions=(
                 "Mis on teie nimi ja kust te pärit olete?",
                 "Kus te praegu elate?",
                 "Millega te tegelete?",
                 "Kui kaua te olete eesti keelt õppinud?",
                 "Miks te tahate eesti keelt õppida?",
                 "Mis on teie jaoks eesti keeles kõige raskem?",
                 "Millal teil on aega kursusel käia?",
                 "Kas te eelistate õppida rühmas või üksi? Miks?",
                 "Milliseid teisi keeli te oskate?",
                 "Mida te vabal ajal teha armastate?",
             )),
        Task("b1-jutt-reis", "B1", 2, "jutt",
             "Kirjuta jutt (umbes 100 sõna) teemal „Minu kõige toredam reis“. "
             "Kirjuta, kuhu ja kellega sa sõitsid, mida sa seal tegid ja miks see "
             "reis sulle meelde jäi.",
             "Напиши рассказ (около 100 слов) «Моя самая приятная поездка»: куда "
             "и с кем ездил, что там делал и почему запомнилось.",
             100, (_WHERE_TO, _WITH, _WHAT_HAPPENED, _REASON)),
        Task("b1-jutt-paev", "B1", 2, "jutt",
             "Kirjuta jutt (umbes 100 sõna) teemal „Üks eriline päev“. Kirjuta, "
             "millal see oli, mis juhtus ja kuidas sa end tundsid.",
             "Напиши рассказ (около 100 слов) «Один особенный день»: когда это "
             "было, что случилось и что ты чувствовал.",
             100, (_WHEN, _WHAT_HAPPENED,
                   Point("tunded", "чувства", "lemmas",
                         ("tundma", "rõõm", "rõõmus", "õnnelik", "kurb", "väsinud",
                          "üllatus", "üllatunud", "hirm", "põnev", "uhke")))),
        Task("b1-kiri-kodu", "B1", 2, "kiri",
             "Sa kolisid hiljuti uude kohta. Kirjuta sõbrale kiri (umbes 100 sõna): "
             "kus sa nüüd elad, milline on su uus kodu ja mida sa seal teed. Kutsu "
             "sõber külla.",
             "Ты недавно переехал. Напиши другу письмо (около 100 слов): где "
             "теперь живёшь, какой у тебя дом и чем занимаешься. Пригласи в гости.",
             100, (_WHERE_AT,
                   Point("milline kodu", "какой дом", "lemmas",
                         ("korter", "maja", "tuba", "köök", "rõdu", "aed", "suur",
                          "väike", "uus", "hele", "mugav")),
                   Point("kutse", "приглашение", "lemmas",
                         ("kutsuma", "külla", "külastama", "ootama", "tulema"))),
             letter=True),
        Task("b1-kiri-haige", "B1", 2, "kiri",
             "Sinu sõber on haige. Kirjuta talle kiri (umbes 100 sõna): kuidas sa "
             "sellest kuulsid, mida sa soovitad tal teha ja millal sa saad teda "
             "vaatama tulla.",
             "Твой друг болеет. Напиши ему письмо (около 100 слов): как ты узнал, "
             "что советуешь делать и когда сможешь навестить.",
             100, (Point("kuidas kuulsid", "как узнал", "lemmas",
                         ("kuulma", "rääkima", "ütlema", "helistama", "kirjutama",
                          "teada", "teadma")),
                   Point("soovitus", "совет", "lemmas",
                         ("soovitama", "pidama", "puhkama", "arst", "ravim", "rohi",
                          "magama", "jooma", "tee")),
                   _WHEN),
             letter=True),
    ),
    "A2": (
        Task("a2-kaart-raamatupidaja", "A2", 1, "visiitkaart",
             "Vaata visiitkaarti. Kirjuta selle inimese kohta tekst (vähemalt 25 "
             "sõna): kes ta on, kus ta töötab ja kuidas temaga ühendust võtta.",
             "Посмотри на визитку. Напиши об этом человеке текст (не меньше 25 "
             "слов): кто он, где работает и как с ним связаться.",
             25, (Point("amet", "профессия", "lemmas", ("raamatupidaja",)),
                  Point("töökoht", "место работы", "words", ("Puit",)),
                  Point("ühendus", "как связаться", "contact")),
             card=("Kati Mägi", "raamatupidaja", "OÜ Puit", "Tartu mnt 12, Tallinn",
                   "tel 5123 4567", "kati.magi@puit.ee")),
        Task("a2-kaart-autojuht", "A2", 1, "visiitkaart",
             "Vaata visiitkaarti. Kirjuta selle inimese kohta tekst (vähemalt 25 "
             "sõna): kes ta on, kus ta töötab ja kuidas temaga ühendust võtta.",
             "Посмотри на визитку. Напиши об этом человеке текст (не меньше 25 "
             "слов): кто он, где работает и как с ним связаться.",
             25, (Point("amet", "профессия", "lemmas", ("autojuht",)),
                  Point("töökoht", "место работы", "words", ("Linnabuss",)),
                  Point("ühendus", "как связаться", "contact")),
             card=("Jaan Tamm", "autojuht", "AS Linnabuss", "Riia 5, Pärnu",
                   "tel 5876 5432", "jaan.tamm@linnabuss.ee")),
        Task("a2-teade-too", "A2", 2, "teade",
             "Sa ei saa homme tööle tulla. Kirjuta ülemusele teade (vähemalt 30 "
             "sõna): miks sa ei tule ja millal sa oled jälle tööl.",
             "Ты не можешь завтра прийти на работу. Напиши начальнику записку (не "
             "меньше 30 слов): почему и когда снова будешь на работе.",
             30, (_REASON, _WHEN)),
        Task("a2-teade-kylla", "A2", 2, "teade",
             "Kutsu sõber laupäeval endale külla. Kirjuta talle teade (vähemalt 30 "
             "sõna): millal ja kuhu ta peab tulema ja mida te koos teete.",
             "Пригласи друга в субботу в гости. Напиши ему сообщение (не меньше "
             "30 слов): когда и куда прийти и что вы будете делать.",
             30, (_WHEN, _WHERE_TO,
                  Point("mida teete", "что будете делать", "lemmas",
                        ("sööma", "jooma", "vaatama", "mängima", "rääkima", "kook",
                         "film", "grillima", "jalutama")))),
        Task("a2-loov-pere", "A2", 2, "loovtekst",
             "Kirjuta tekst (vähemalt 30 sõna) teemal „Minu pere“: kes on sinu "
             "pere, kus nad elavad ja mida te koos teete.",
             "Напиши текст (не меньше 30 слов) «Моя семья»: кто в семье, где живут "
             "и что делаете вместе.",
             30, (Point("kes", "кто", "lemmas",
                        ("ema", "isa", "vend", "õde", "laps", "poeg", "tütar", "mees",
                         "naine", "vanaema", "vanaisa", "abikaasa")),
                  _WHERE_AT,
                  Point("mida koos", "что вместе", "lemmas", ("koos",)))),
        Task("a2-loov-vaba-aeg", "A2", 2, "loovtekst",
             "Kirjuta tekst (vähemalt 30 sõna) teemal „Minu vaba aeg“: mida sa "
             "vabal ajal teed, kellega ja kui tihti.",
             "Напиши текст (не меньше 30 слов) «Моё свободное время»: что делаешь, "
             "с кем и как часто.",
             30, (Point("mida", "что делаешь", "lemmas",
                        ("lugema", "ujuma", "jooksma", "vaatama", "mängima",
                         "jalutama", "laulma", "tantsima", "käima", "sport")),
                  _WITH,
                  Point("kui tihti", "как часто", "lemmas",
                        ("iga", "tihti", "harva", "alati", "mõnikord", "kord",
                         "vahel", "sageli")))),
    ),
}

_BY_ID = {t.id: t for bank in BANK.values() for t in bank}


def by_id(task_id: str) -> Task:
    return _BY_ID[task_id]


def for_section(level: str, seed: int) -> list[dict]:
    """The section's two tasks: one prompt per HARNO variant, chosen by seed."""
    rng = random.Random(seed)
    out = []
    for no in (1, 2):
        variants = []
        for kind in dict.fromkeys(t.kind for t in BANK[level] if t.task_no == no):
            choices = [t for t in BANK[level] if t.task_no == no and t.kind == kind]
            variants.append(rng.choice(choices).to_dict())
        out.append({"no": no, "points": POINTS.get((level, no)), "variants": variants})
    return out


# -------------------------------------------------------------------------
# What code can check
# -------------------------------------------------------------------------

_TIME_LEMMAS = frozenset({
    "homme", "ülehomme", "täna", "eile", "hommik", "õhtu", "öö", "päev", "nädal",
    "kuu", "aasta", "kell", "nädalavahetus", "esmaspäev", "teisipäev", "kolmapäev",
    "neljapäev", "reede", "laupäev", "pühapäev", "jaanuar", "veebruar", "märts",
    "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober",
    "november", "detsember", "pärast", "varsti", "kuni", "kauaks", "minut", "tund",
})
_TO = frozenset({"sg ill", "pl ill", "sg all", "pl all", "adt"})
_AT = frozenset({"sg in", "pl in", "sg ad", "pl ad"})
_WITH_FORMS = frozenset({"sg kom", "pl kom"})
_PAST = frozenset({"s", "sin", "sid", "sime", "site", "nud", "ti", "tud"})
_OPENINGS = ("tere", "hei", "kallis", "armas", "lugupeetud", "hea ", "head ")
_CLOSINGS = ("parimate soovidega", "tervitades", "tervitusega", "kallistan",
             "kallistades", "lugupidamisega", "kõike head", "ootan", "sinu ", "teie ",
             "musi", "näeme")


def _found(point: Point, tokens, text: str) -> bool:
    if point.test == "lemmas":
        return any(t.lemma in point.lemmas for t in tokens)
    if point.test == "words":
        return any(w in text for w in point.lemmas)
    if point.test == "time":
        return (any(t.lemma in _TIME_LEMMAS for t in tokens)
                or bool(re.search(r"\b\d{1,2}([.:]\d{2})?\b", text)))
    if point.test == "place_to":
        return any(t.form in _TO and t.pos in ("S", "H") for t in tokens)
    if point.test == "place_at":
        return any(t.form in _AT and t.pos in ("S", "H") for t in tokens)
    if point.test == "with":
        return any(t.form in _WITH_FORMS or t.lemma == "koos" for t in tokens)
    if point.test == "past":
        return any(t.pos == "V" and t.form in _PAST for t in tokens)
    if point.test == "contact":
        return bool(re.search(r"\d{3}|@", text)) or any(
            t.lemma in ("telefon", "number", "helistama", "kirjutama", "e-post")
            for t in tokens)
    raise ValueError(f"unknown point test {point.test!r}")


def _framed(text: str) -> tuple[bool, bool]:
    lines = [ln.strip().casefold() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return False, False
    opening = lines[0].startswith(_OPENINGS)
    tail = " ".join(lines[-2:]) + " "
    closing = any(c in tail for c in _CLOSINGS)
    return opening, closing


def check(task: Task, text: str, answers: list[str] | None = None) -> dict:
    """What code can say about one written task: a checklist, never a mark."""
    from .morph import analyze
    from .providers.grammar import agreement, nominative_objects, rection, spelling

    if task.kind == "kusimustik":
        given = [a.strip() for a in (answers or [])][:len(task.questions)]
        answered = sum(1 for a in given if len(a.split()) >= 2)
        text = "\n".join(a for a in given if a)
    else:
        answered = None
    words = len(text.split())
    tokens = analyze(text) if text.strip() else []
    if task.kind == "kusimustik":
        long_enough = answered == len(task.questions)
    elif task.at_least:
        long_enough = words >= task.target_words
    else:                   # "about": within a tenth below HARNO's figure
        long_enough = words >= round(task.target_words * 0.9)
    found = (spelling(text) + agreement(text) + rection(text) + nominative_objects(text)
             if text.strip() else [])
    opening, closing = _framed(text) if task.letter else (None, None)
    return {
        "id": task.id, "kind": task.kind, "kind_et": KIND_ET[task.kind],
        "words": words, "target_words": task.target_words, "at_least": task.at_least,
        "long_enough": long_enough, "answered": answered,
        "points": [{"et": p.et, "ru": p.ru, "found": _found(p, tokens, text)}
                   for p in task.points],
        "opening": opening, "closing": closing,
        "errors": len(found), "findings": [c.to_dict() for c in found[:12]],
        "checked_by": "vabamorf+ekk",
    }


def met(result: dict) -> bool:
    """The checklist is complete: long enough, every point found, a letter framed,
    and nothing the deterministic checks object to. Practice evidence only."""
    return (result["long_enough"] and all(p["found"] for p in result["points"])
            and result["opening"] is not False and result["closing"] is not False
            and result["errors"] == 0)
