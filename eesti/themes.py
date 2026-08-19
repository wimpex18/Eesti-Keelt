"""Themes: the unit that carries grammar and vocabulary at the same time.

Step 6, and the idea is Keeleklikk's. Its sixteen chapters are *situations* —
greetings, food, family, shopping, health, work — and grammar arrives **in
service of one**: the chapter that needs the partitive teaches the partitive.
The learner is not doing a case exercise, they are ordering food, and the case
comes along with the words.

Everything else in this app is generated, so this can do something a fixed
course cannot: **theme and grammar rule are separate axes and recombine
freely.** `täissihitis × toit` drills the object case over food words;
`lihtminevik × reisimine` drills the past tense over travel words. Sixteen
chapters becomes eleven themes times twenty-one drillable topics, from the same
generators, without writing a single new lesson.

## The word lists are hand-picked, and that is the right call

Every other list in this project earns its place by being derived — corpus
frequency, Vabamorf synthesis, EKK's own tables. A theme is not derivable:
"which words belong to *food*" is a curatorial judgement, and Keeleklikk's
authors made it by hand too.

What is **not** left to judgement is whether the words are real. Every lemma
here is checked against the 160 316-word Ekilex list at load, and anything it
does not know is dropped and reported rather than silently drilled. That check
already earned itself: the first draft had `kindad`, `kingad`, `saapad`,
`sokid` — plural-only forms where the lexicon lists `kinnas`, `king`, `saabas`,
`sokk`, and a generator asked for the genitive of `kingad` would have produced
something no one says.

Untagged words are kept. Only 6.2 % of Ekilex lemmas carry a CEFR level, so a
missing tag is an absence of evidence, not evidence of difficulty — but a word
tagged *above* the learner's level is dropped, because that is evidence.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .config import LEVELS


@dataclass(frozen=True)
class Theme:
    id: str
    et: str            # what an Estonian course would call this chapter
    ru: str
    nouns: tuple[str, ...]
    verbs: tuple[str, ...]

    @property
    def lemmas(self) -> tuple[str, ...]:
        return self.nouns + self.verbs


def _t(id_, et, ru, nouns, verbs) -> Theme:
    return Theme(id_, et, ru, tuple(nouns.split()), tuple(verbs.split()))


THEMES: tuple[Theme, ...] = (
    _t("pere", "Pere ja sugulased", "семья",
       "ema isa vend õde laps poeg tütar vanaema vanaisa abikaasa naine mees "
       "sugulane perekond nimi",
       "elama tundma armastama aitama kohtuma"),
    _t("toit", "Toit ja söömine", "еда",
       "leib sai või juust piim kohv tee vesi mahl supp liha kala kana muna "
       "õun kartul riis sool suhkur kook jäätis hommikusöök lõunasöök "
       "õhtusöök restoran",
       "sööma jooma ostma valmistama küpsetama maitsma tellima"),
    _t("kodu", "Kodu ja elamine", "дом",
       "maja korter tuba köök vannituba magamistuba uks aken laud tool voodi "
       "kapp diivan põrand aed võti",
       "elama magama koristama ehitama avama sulgema"),
    _t("too", "Töö ja amet", "работа",
       "töö amet palk kontor koosolek kolleeg ülemus projekt arvuti dokument "
       "leping puhkus tööpäev ettevõte telefon",
       "töötama alustama lõpetama kirjutama helistama korraldama teenima"),
    _t("oppimine", "Õppimine ja kool", "учёба",
       "kool ülikool õpetaja õpilane tund eksam raamat sõnaraamat harjutus "
       "kodutöö klass loeng keel tudeng viga",
       "õppima lugema kirjutama küsima vastama kordama tõlkima seletama"),
    _t("linn", "Linnas", "город",
       "linn tänav pood turg apteek pank postkontor jaam park muuseum kohvik "
       "kino teater haigla kirik raamatukogu",
       "käima minema ostma kohtuma jalutama otsima leidma"),
    _t("reisimine", "Reisimine", "путешествия",
       "rong buss lennuk laev auto jalgratas pilet reis hotell kohver pass "
       "kaart sadam lennujaam tee",
       "sõitma lendama minema tulema jõudma ootama broneerima"),
    _t("tervis", "Tervis ja keha", "здоровье",
       "arst haigla apteek ravim valu palavik hammas käsi jalg pea silm süda "
       "tervis haigus nina",
       "ravima valutama tundma puhkama magama"),
    _t("riided", "Riided", "одежда",
       # Singulars, not the plural-only forms a learner sees on a label: the
       # lexicon lists `king`, and the genitive of `kingad` is not a thing.
       "särk kleit püksid seelik jope müts sall kinnas king saabas sokk pluus "
       "ülikond",
       "kandma ostma proovima pesema"),
    _t("aeg", "Aeg", "время",
       "päev nädal kuu aasta tund minut hommik õhtu öö kevad suvi sügis talv kell",
       "algama lõppema ootama jõudma kestma"),
    _t("ilm", "Ilm", "погода",
       "ilm päike vihm lumi tuul pilv temperatuur torm külm",
       "sadama puhuma paistma külmetama"),
)

# Substances and abstractions: real words, and not things you can have two of.
# The numeral drill produced *"Mul on kaks riisi"* — I have two rice — because a
# theme's nouns were treated as countable by construction. Countability is not
# derivable from the word list, and it is not guessable from the theme either:
# `toit` holds both `kook` (countable) and `suhkur` (not).
UNCOUNTABLE: frozenset[str] = frozenset({
    "piim", "vesi", "kohv", "tee", "mahl", "riis", "sool", "suhkur", "või",
    "liha", "leib", "sai", "juust", "töö", "tervis", "valu",
    "palavik", "ilm", "päike", "vihm", "lumi", "tuul", "temperatuur", "keel",
    "puhkus", "palk", "amet",
})

_BY_ID = {t.id: t for t in THEMES}


def by_id(theme_id: str) -> Theme:
    return _BY_ID[theme_id]


def validate(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Lemmas no lexicon knows, per theme. Empty dict means every word is real.

    Called by the tests, and cheap enough to call anywhere. This is the check
    that caught `kingad`.
    """
    known = {r[0] for r in conn.execute("SELECT word FROM words")}
    return {
        theme.id: [w for w in theme.lemmas if w not in known]
        for theme in THEMES
        if any(w not in known for w in theme.lemmas)
    }


def lemmas_for(
    conn: sqlite3.Connection,
    theme_id: str,
    levels: tuple[str, ...] = LEVELS,
    pos: str | None = None,
) -> list[str]:
    """The theme's words, filtered to what exists and is not above the level.

    An untagged word is kept: only 6.2 % of Ekilex lemmas carry a CEFR level, so
    a missing tag says nothing about difficulty. A word tagged *above* the
    target is dropped, because that does.
    """
    theme = by_id(theme_id)
    wanted = theme.nouns if pos == "s" else theme.verbs if pos == "v" else theme.lemmas
    if not wanted:
        return []

    rows = {
        r[0]: r[1]
        for r in conn.execute(
            f"SELECT word, proficiency FROM words WHERE word IN "
            f"({','.join('?' * len(wanted))})",
            tuple(wanted),
        )
    }
    return [
        word for word in wanted
        if word in rows and (rows[word] is None or rows[word] in levels)
    ]


def countable_nouns(
    conn: sqlite3.Connection,
    theme_id: str,
    levels: tuple[str, ...] = LEVELS,
) -> list[str]:
    """The theme's nouns you can have two of — what a numeral drill needs."""
    return [w for w in lemmas_for(conn, theme_id, levels, pos="s") if w not in UNCOUNTABLE]


def coverage(conn: sqlite3.Connection, levels: tuple[str, ...] = LEVELS) -> dict[str, dict]:
    """How much of each theme survives the level filter — the honest size of it."""
    return {
        theme.id: {
            "et": theme.et,
            "declared": len(theme.lemmas),
            "usable": len(lemmas_for(conn, theme.id, levels)),
            "nouns": len(lemmas_for(conn, theme.id, levels, pos="s")),
            "verbs": len(lemmas_for(conn, theme.id, levels, pos="v")),
        }
        for theme in THEMES
    }
