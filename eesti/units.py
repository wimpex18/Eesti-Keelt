"""The course as units: thirty one-week units from the first sound to B1.

A unit is a layer over topics, not a replacement (ADR-0007): it names the
topics it introduces (each topic has exactly one home unit), the sub-rules of
earlier topics its stage unlocks, the HARNO topics it serves, its word set and
its companion unit in Keeleklikk (0–A2) or Keeletee (B1). Topic ids, mastery and
FSRS are untouched. Specification: `docs/course-structure.md`.

**Stages are targets, not levels.** A stage is where EKI's grammar profile
(etLex, cited by statement id) and HARNO's topic lists put the unit's content.
Only official HARNO/EIS material has a CEFR `level` (AGENTS.md); the first
stage is *Algus*, because A0 is not a CEFR level.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Stages in course order.
STAGES = ("algus", "A1", "A2", "B1")

#: HARNO's A2 topics, from its exam page (https://harno.ee/eesti-keele-tasemeeksamid).
HARNO_A2 = (
    "isikuandmed", "maja ja kodu", "ümbruskond", "igapäevaelu",
    "vaba aeg ja meelelahutus", "reisimine", "suhted teiste inimestega",
    "tervis ja kehahooldus", "haridus", "sisseostude tegemine", "söök ja jook",
    "teenused", "kohad", "keel", "ilm",
)

#: HARNO's B1 topics: §4.2 of its handbook *Iseseisev keelekasutaja* (2021).
HARNO_B1 = (
    "endast ja teistest rääkimine", "haridus", "elukutse, amet ja töö",
    "teenindus", "igapäevaelu, kodu ja kodukoht", "enesetunne ja tervis",
    "vaba aeg ja meelelahutus", "sisseostud, hinnad", "söök ja jook",
    "inimeste suhted ühiskonnas", "keskkond, kohad, loodus, ilm",
    "kultuur ja keeled, keelte õppimine",
    "reisimine, transport, vaatamisväärsused",
)


@dataclass(frozen=True)
class Revisit:
    """Sub-rules of an earlier topic that this unit's stage unlocks."""

    topic: str
    rules: tuple[str, ...]
    #: EKI etLex statements placing the rule (cited, never copied).
    eki: tuple[int, ...] = ()
    #: Said when the profile puts the rule above the unit's stage.
    note_ru: str = ""


@dataclass(frozen=True)
class Unit:
    id: str
    n: int
    et: str
    stage: str
    goal_ru: str
    topics: tuple[str, ...] = ()
    revisits: tuple[Revisit, ...] = ()
    harno: tuple[str, ...] = ()
    #: ("KK", n) for Keeleklikk, ("KT", n) for Keeletee, None for none.
    course: tuple[str, int] | None = None
    #: A `themes.py` theme id, or "algus" for the first week's picture-dictionary
    #: words (`FIRST_WORDS`).
    words: str | None = None
    #: The stage checkpoint the unit's check carries, if any.
    checkpoint: str | None = None


def _u(n, id_, et, stage, goal_ru, topics=(), *, revisits=(), harno=(), course=None,
       words=None, checkpoint=None) -> Unit:
    return Unit(id_, n, et, stage, goal_ru, tuple(topics), tuple(revisits),
                tuple(harno), course, words, checkpoint)


UNITS: tuple[Unit, ...] = (
    _u(1, "tere", "Tere!", "algus",
       "Поздороваться, поблагодарить, извиниться и попрощаться; понимать и "
       "называть числа до ста; слышать, как долгота меняет слово.",
       ("tahestik", "fraasid", "arvud"), harno=("keel",), course=("KK", 1),
       words="algus"),
    _u(2, "tutvume", "Tutvume", "A1",
       "Представиться, спросить, кто это и где он живёт, рассказать о себе в "
       "настоящем времени.",
       ("asesonad", "kusisonad", "olevik", "lauseehitus"),
       harno=("isikuandmed", "keel"), course=("KK", 2)),
    _u(3, "pere", "Minu pere", "A1",
       "Рассказать о семье: кто есть, сколько их и сколько им лет.",
       ("pohivormid", "arvsonad"), harno=("suhted teiste inimestega",),
       course=("KK", 5), words="pere"),
    _u(4, "kohvik", "Kohvikus", "A1",
       "Заказать еду и напитки, сказать, чего не хочешь или чего нет.",
       ("osastav", "eitus"),
       revisits=(Revisit("fraasid", ("vastus",)),),
       harno=("söök ja jook",), course=("KK", 4), words="toit"),
    _u(5, "kodu", "Kus sa elad?", "A1",
       "Сказать, где ты живёшь и где что находится, куда идёшь и откуда.",
       ("gen-stem", "astmevaheldus", "kohakaanded"),
       harno=("maja ja kodu", "kohad"), course=("KK", 3), words="kodu"),
    _u(6, "paev", "Minu päev", "A1",
       "Рассказать о своём дне: что делаешь, когда и как часто.",
       ("verb-form", "kellaaeg", "maarsonad"), harno=("igapäevaelu",),
       course=("KK", 6), words="aeg"),
    _u(7, "linn", "Linnas", "A1",
       "Найти дорогу в городе: где что находится, рядом с чем и за чем.",
       ("kaassonad", "mitmus", "sidesonad"), harno=("ümbruskond", "kohad"),
       course=("KK", 15), words="linn"),
    _u(8, "meeldib", "Mulle meeldib", "A1",
       "Сказать, что нравится, что нужно и что хочется делать в свободное время.",
       ("ma-da-inf", "mul-on"), harno=("vaba aeg ja meelelahutus",),
       course=("KK", 7)),
    _u(9, "eile", "Eile", "A1",
       "Рассказать, что было вчера, куда ходил и какая была погода.",
       ("lihtminevik", "kaima-minema"), harno=("ilm", "reisimine"),
       course=("KK", 9), words="ilm"),
    _u(10, "poes", "Poes", "A1",
       "Купить в магазине: что купил целиком, чего нет в продаже.",
       ("obj-case", "osaalus"), harno=("sisseostude tegemine",),
       course=("KK", 8), words="toit", checkpoint="A1"),
    _u(11, "kodus", "Kodus", "A2",
       "Попросить и посоветовать: сделай, купи, принеси.",
       ("kaskiv",),
       revisits=(Revisit("obj-case", ("imperative", "plural"), (1288,)),),
       harno=("maja ja kodu",), course=("KK", 14), words="kodu"),
    _u(12, "tervis", "Tervis", "A2",
       "Объяснить врачу, что болит, и вежливо попросить.",
       ("tingiv",), harno=("tervis ja kehahooldus",), course=("KK", 11),
       words="tervis"),
    _u(13, "valimus", "Välimus ja iseloom", "A2",
       "Описать и сравнить людей: кто выше, моложе, веселее.",
       ("vordlusastmed",), harno=("suhted teiste inimestega",), course=("KK", 12),
       words="riided"),
    _u(14, "kogemused", "Kogemused", "A2",
       "Рассказать, что уже сделал и где бывал.",
       ("kesksonad", "taisminevik"), harno=("haridus",), course=("KK", 13),
       words="oppimine"),
    _u(15, "puhad", "Pühad ja kuupäevad", "A2",
       "Назвать дату, поздравить с праздником, договориться о дне.",
       ("jargarvud", "kuupaevad"), harno=("igapäevaelu",), course=("KK", 16),
       words="aeg"),
    _u(16, "too", "Töö ja amet", "A2",
       "Рассказать о работе и профессии: кто что делает.",
       ("tuletus", "ma-vormid"), harno=("haridus",), course=("KK", 13),
       words="too"),
    _u(17, "plaanid", "Plaanid", "A2",
       "Рассказать о планах на завтра и на выходные.",
       ("tulevik",), harno=("vaba aeg ja meelelahutus",), course=("KK", 7)),
    _u(18, "teenused", "Teenused", "A2",
       "Воспользоваться услугами: в парикмахерской, на почте, в банке.",
       ("harvad-kaanded",), harno=("teenused",), course=("KK", 8)),
    _u(19, "reis", "Reisimine ja ilm", "A2",
       "Повторение: поездка, погода, места; контрольная по уровню A2.",
       harno=("reisimine", "ilm", "kohad", "keel"), course=("KK", 9),
       words="reisimine", checkpoint="A2"),
    _u(20, "minu-paev", "Minu päev ja tunded", "B1",
       "Рассказать о себе и своих чувствах, связно и в нужном порядке слов.",
       ("rektsioon", "sonajark"), harno=("endast ja teistest rääkimine",),
       course=("KT", 1)),
    _u(21, "restoran", "Restoranis", "B1",
       "Заказать и описать блюда, согласуя определения.",
       ("uhildumine",), harno=("söök ja jook",), course=("KT", 3), words="toit"),
    _u(22, "perekond", "Perekond ja suhted", "B1",
       "Рассказать об отношениях в семье и обществе, объясняя причины.",
       ("kirjavahemargid",), harno=("inimeste suhted ühiskonnas",),
       course=("KT", 5), words="pere"),
    _u(23, "kodukoht", "Kodu ja kodukoht", "B1",
       "Рассказать о доме и родных местах: что построено и что делается.",
       ("umbisikuline",),
       revisits=(Revisit("obj-case", ("impersonal",), (1300,)),),
       harno=("igapäevaelu, kodu ja kodukoht",), course=("KT", 6), words="kodu"),
    _u(24, "ostud", "Ostud ja hinnad", "B1",
       "Покупки и цены: что нужно купить, сравнить, вернуть.",
       ("uhendverbid",),
       revisits=(Revisit(
           "obj-case", ("infinitive",), (879,),
           "В профиле EKI это уровень выше B1 (B2); правило — EKK SÜ 40 и "
           "teatmik EKI."),),
       harno=("sisseostud, hinnad",), course=("KT", 7), words="riided"),
    _u(25, "haridus", "Haridus ja keeled", "B1",
       "Рассказать об учёбе и языках и передать чужие слова.",
       ("kaudne",), harno=("haridus", "kultuur ja keeled, keelte õppimine"),
       course=("KT", 8), words="oppimine"),
    _u(26, "reisid", "Reisid", "B1",
       "Рассказать о поездке: что уже случилось до чего.",
       ("enneminevik",), harno=("reisimine, transport, vaatamisväärsused",),
       course=("KT", 9), words="reisimine"),
    _u(27, "enesetunne", "Enesetunne", "B1",
       "Повторение: самочувствие и здоровье.",
       harno=("enesetunne ja tervis",), course=("KT", 10), words="tervis"),
    _u(28, "too-elu", "Töö ja teenindus", "B1",
       "Работа и обслуживание: профессии, обязанности, сложные слова.",
       ("liitsonad",), harno=("elukutse, amet ja töö", "teenindus"),
       course=("KT", 11), words="too"),
    _u(29, "aastaring", "Aastaring ja loodus", "B1",
       "Природа, погода и времена года.",
       revisits=(Revisit(
           "osaalus", ("mitmus",), (1328,),
           "В профиле EKI это уровень выше B1 (B2); правило — EKK SÜ 35."),),
       harno=("keskkond, kohad, loodus, ilm",), course=("KT", 12), words="ilm"),
    _u(30, "uritused", "Üritused Eestis", "B1",
       "Повторение: события и места в Эстонии; контрольная по уровню B1.",
       harno=("vaba aeg ja meelelahutus",), course=("KT", 13), checkpoint="B1"),
)

_BY_ID = {u.id: u for u in UNITS}
_HOME = {t: u for u in UNITS for t in u.topics}

#: The first week's words: a selection of the words EKI's picture dictionary
#: marks A1–A2 in its themes *Värvid* and *Toit ja jook*, in its own order. Only
#: the selection is EKI's piltsõnastik; the Russian is the app's meaning chain
#: (seed, then EKI EVS), because the dictionary's Russian names the picture
#: (*kala* is captioned «окунь»). *Tee* and *või* are left out: each shares its
#: lemma with another word (road, "or"), so the meaning shown would be the other.
FIRST_WORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Värvid", ("must", "valge", "punane", "roheline", "kollane", "sinine",
                "pruun", "roosa", "oranž", "hall", "lilla")),
    ("Toit ja jook", ("leib", "vesi", "sai", "kook", "piim", "võileib", "kohv",
                      "mahl", "puder", "muna", "juust", "jäätis", "supp",
                      "kartul", "kala", "liha", "suhkur")),
)
PICTURES_URL = "https://sonaveeb.ee/wordgame"

#: Where each companion course's unit map is, by explanation language.
_COURSE = {"KK": ("A", {"ru": "ru", "uk": "ua", "en": "en"}),
           "KT": ("B1", {"ru": "ru", "uk": "en", "en": "en"})}


def by_id(unit_id: str) -> Unit:
    return _BY_ID[unit_id]


def home(topic: str) -> Unit:
    """The unit that introduces `topic`."""
    return _HOME[topic]


def stage_of(topic: str) -> str:
    return _HOME[topic].stage


def position(topic: str) -> tuple[int, int]:
    """Where a topic comes in the course: its unit, then its place in the unit."""
    unit = _HOME[topic]
    return (unit.n, unit.topics.index(topic))


def course_link(unit: Unit, language: str = "ru") -> str | None:
    """The companion unit's public course map, in the learner's language where
    the course has it."""
    if unit.course is None:
        return None
    kind, n = unit.course
    path, langs = _COURSE[kind]
    return f"https://www.keeleklikk.ee/{langs.get(language, 'en')}/{path}/coursemap/list/{n}"


def validate() -> None:
    """Fail on a map the course cannot follow: a topic with no home or two, a
    topic before its prerequisites, a revisit before its topic's home."""
    from .curriculum import TOPICS, by_id as topic

    if [u.n for u in UNITS] != list(range(1, len(UNITS) + 1)):
        raise ValueError("units must be numbered 1..N in order")
    if len(_BY_ID) != len(UNITS):
        raise ValueError("duplicate unit id")
    if [STAGES.index(u.stage) for u in UNITS] != sorted(STAGES.index(u.stage) for u in UNITS):
        raise ValueError("stages must not go backwards")
    homes = [t for u in UNITS for t in u.topics]
    if sorted(homes) != sorted({t.id for t in TOPICS}) or len(homes) != len(set(homes)):
        raise ValueError("every topic needs exactly one home unit")
    for u in UNITS:
        for t in u.topics:
            for need in topic(t).requires:
                if _HOME[need].n > u.n:
                    raise ValueError(f"{t} in unit {u.n} needs {need} from unit {_HOME[need].n}")
        for r in u.revisits:
            if _HOME[r.topic].n >= u.n:
                raise ValueError(f"unit {u.n} revisits {r.topic} before its home unit")


def words_for(unit: Unit) -> tuple[str, ...]:
    """The lemmas of a unit's word set."""
    if unit.words == "algus":
        return tuple(w for _theme, words in FIRST_WORDS for w in words)
    if unit.words:
        from .themes import THEMES

        theme = next((t for t in THEMES if t.id == unit.words), None)
        return theme.lemmas if theme else ()
    return ()
