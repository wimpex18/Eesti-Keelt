"""Tenses, moods, infinitives and voice — the rest of the verb.

`verbs.py` drills irregular stems. Here the distractor is the same verb in the
neighbouring form the learner confuses it with:

    tingiv kõneviis   õpiks    against the present   õpib
    lihtminevik       õppis    against the present   õpib
    täisminevik       õppinud  against the past      õppis
    umbisikuline      õpitakse against the personal  õpib
    ma-/da-infinitiiv õppima   against               õppida

Both forms come from Vabamorf; identical pairs are dropped. The `ma`/`da` choice
is decided by the governing verb, so its frames come in pairs (*pean* + ma,
*tahan* + da).

**Where the sentence comes from** (`RULES`, `drills`): `vorm` is the bleached
frames below (`generate`); `fraas` blanks a verb in one of EKI EVS's example
phrases (`phrase_drills`), credited per item, where Vabamorf has exactly one
reading for the word; `eitus` is the negated form (`negation.py`, EKK M 99);
`modaal` the infinitive a modal verb takes in EVS's phrases (`modals.py`).
"""

from __future__ import annotations

import random
import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache

from estnltk.vabamorf.morf import synthesize

from .config import LEVELS
from .item import BLANK, GradedItem


@dataclass(frozen=True)
class Frame:
    """One drillable verb form: how to elicit it, and what it is confused with."""

    tag: str            # Vabamorf synthesis tag for the answer
    against: str        # tag for the distractor — the neighbouring form
    name: str           # Estonian name, as a teacher would say it
    sentence: str       # frame with ____ where the form goes
    why_ru: str


# Frames per curriculum topic, with the pronoun agreeing with the form. Frames
# have no object (*"Siin ____ iga päev"*), so they suit transitive and
# intransitive verbs alike.
FRAMES: dict[str, tuple[Frame, ...]] = {
    "olevik": (
        Frame("n", "sin", "olevik, mina", "Ma ____ iga päev.",
              "**Olevik** — настоящее время. Сравни с прошедшим."),
        Frame("b", "s", "olevik, tema", "Ta ____ iga päev.",
              "**Olevik** — настоящее время. Сравни с прошедшим."),
        Frame("vad", "sid", "olevik, nemad", "Nad ____ iga päev.",
              "**Olevik** — настоящее время, 3-е лицо мн. ч."),
    ),
    "lihtminevik": (
        Frame("sin", "n", "lihtminevik, mina", "Eile ma ____.",
              "**Lihtminevik** — простое прошедшее, показатель *-si-/-s-*."),
        Frame("s", "b", "lihtminevik, tema", "Eile ta ____.",
              "**Lihtminevik** — простое прошедшее, показатель *-si-/-s-*."),
        Frame("sime", "me", "lihtminevik, meie", "Eile me ____.",
              "**Lihtminevik** — простое прошедшее, 1-е лицо мн. ч."),
    ),
    "taisminevik": (
        Frame("nud", "s", "täisminevik", "Ta on juba ____.",
              "**Täisminevik** = *olema* olevikus + **nud**-kesksõna. "
              "После *on* нужна причастная форма, а не простое прошедшее."),
    ),
    "enneminevik": (
        Frame("nud", "s", "enneminevik", "Ta oli juba ____, kui me tulime.",
              "**Enneminevik** = *olema* minevikus + **nud**-kesksõna."),
    ),
    "tingiv": (
        Frame("ks", "b", "tingiv kõneviis, tema", "Ta ____, kui saaks.",
              "**Tingiv kõneviis** — условное наклонение, показатель **-ks-**."),
        Frame("ksin", "n", "tingiv kõneviis, mina", "Ma ____, kui saaksin.",
              "**Tingiv kõneviis** — условное наклонение, показатель **-ks-**."),
    ),
    "kaskiv": (
        Frame("o", "d", "käskiv kõneviis, sina", "____ kohe!",
              "**Käskiv kõneviis** — повелительное наклонение. Форма 2 л. ед. ч. "
              "— это чистая основа, без *-d*."),
        Frame("ge", "te", "käskiv kõneviis, teie", "____ palun kohe!",
              "**Käskiv kõneviis** мн. ч. — показатель **-ge/-ke**."),
    ),
    "ma-da-inf": (
        Frame("ma", "da", "ma-tegevusnimi", "Ta peab ____.",
              "Какой инфинитив — решает управляющий глагол, а не смысл. "
              "*pean* требует **ma**-инфинитива."),
        Frame("da", "ma", "da-tegevusnimi", "Ta tahab ____.",
              "Какой инфинитив — решает управляющий глагол, а не смысл. "
              "*tahan* требует **da**-инфинитива."),
    ),
    "kesksonad": (
        Frame("nud", "s", "mineviku kesksõna (nud)", "Ta on ____.",
              "**nud**-kesksõna — причастие прошедшего времени, действительный залог."),
        Frame("tud", "nud", "mineviku kesksõna (tud)", "Siin on juba ____.",
              "**tud**-kesksõna — страдательное причастие: действие над предметом, "
              "деятель не назван."),
    ),
    "umbisikuline": (
        Frame("takse", "b", "umbisikuline olevik", "Siin ____ iga päev.",
              "**Umbisikuline tegumood** — безличный залог: деятель не назван. "
              "Показатель **-takse/-akse**."),
        Frame("ti", "s", "umbisikuline minevik", "Siin ____ eile.",
              "**Umbisikuline tegumood** в прошедшем — показатель **-ti/-di**."),
    ),
}


@dataclass(frozen=True)
class VerbDrill(GradedItem):
    prompt: str
    answer: str
    distractor: str
    lemma: str
    tag: str
    form_et: str
    rule: str
    why_ru: str
    topic: str
    level: str | None
    #: The registry id of the material the sentence is from (`evs.SOURCE_ID` for
    #: an EKI EVS phrase), credited on the page; empty for a frame.
    source_id: str = ""

    @property
    def label(self) -> str:
        return self.form_et


def verbs_at_levels(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    limit: int = 400,
) -> list[tuple[str, str]]:
    """Level-appropriate verbs, most frequent first (`wordlist.verbs_at_levels`)."""
    from .wordlist import verbs_at_level

    return verbs_at_level(conn, levels, limit)


def _one(lemma: str, tag: str) -> str | None:
    produced = synthesize(lemma, tag) or []
    return produced[0] if produced else None


def generate(
    conn: sqlite3.Connection,
    topics: tuple[str, ...] | None = None,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    top: int = 150,
    only: frozenset[str] | None = None,
) -> list[VerbDrill]:
    """Drills for the tense, mood, infinitive and voice topics; an item ships only when
    answer and neighbouring form differ.
    """
    wanted = tuple(topics) if topics else tuple(FRAMES)
    unknown = set(wanted) - set(FRAMES)
    if unknown:
        raise ValueError(f"no frames for topic(s): {sorted(unknown)}")

    rng = random.Random(seed)
    # Frequency-ordered, then shuffled within the common band: the bleached frames
    # read naturally only with common verbs.
    pool = verbs_at_levels(conn, levels)
    if only is not None:
        # A theme restriction skips the frequency cut, so the theme's words are kept.
        pool = [(lemma, level) for lemma, level in pool if lemma in only]
    else:
        pool = pool[:top]
    if not pool:
        if only is not None:
            return []  # the theme has no verbs at this level; not an error
        raise RuntimeError("no verbs indexed — run `cli build` first")

    # Every (verb, frame) pair is a candidate, not one item per verb. Drawing a
    # random frame per verb capped the run at len(pool) items and did it
    # silently — asking for 50 drills from 20 verbs returned 20.
    candidates = [
        (lemma, level, topic, frame)
        for lemma, level in pool
        for topic in wanted
        for frame in FRAMES[topic]
    ]
    rng.shuffle(candidates)

    out: list[VerbDrill] = []
    for lemma, level, topic, frame in candidates:
        if len(out) >= count:
            break
        answer = _one(lemma, frame.tag)
        wrong = _one(lemma, frame.against)
        if not answer or not wrong or answer.lower() == wrong.lower():
            continue

        out.append(
            VerbDrill(
                prompt=frame.sentence,
                answer=answer,
                distractor=wrong,
                lemma=lemma,
                tag=frame.tag,
                form_et=frame.name,
                rule="conjugation",
                why_ru=f"{frame.why_ru} *{lemma}* → **{answer}**, не *{wrong}*.",
                topic=topic,
                level=level,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Verbs in EKI EVS's phrases: shared by `negation`, `modals` and `future`
# ---------------------------------------------------------------------------

#: A word of a phrase; a hyphenated compound (`võib-olla`) is one word.
_WORD = re.compile(r"\w+(?:-\w+)*")

#: Phrase length for a verb gap: enough to place the form, short enough to
#: read at a glance.
PHRASE_WORDS = (3, 10)


def words_in(text: str) -> list[tuple[str, int, int]]:
    """`(word, start, end)` for every word of a phrase."""
    return [(m.group(), m.start(), m.end()) for m in _WORD.finditer(text)]


def adjacent(text: str, left: tuple[str, int, int], right: tuple[str, int, int]) -> bool:
    """Whether only spaces separate two words; a comma between them is a clause
    boundary."""
    return not text[left[2]:right[1]].strip()


def blank(text: str, start: int, end: int) -> str:
    return text[:start] + BLANK + text[end:]


@lru_cache(maxsize=16384)
def forms(lemma: str, tag: str) -> tuple[str, ...]:
    """Every form Vabamorf synthesises for `lemma` in `tag` that reads back as
    that lemma in that form, in Vabamorf's order."""
    from .morph import _readings

    out: list[str] = []
    for form in synthesize(lemma, tag) or []:
        if (lemma, tag) in _readings(form) and form not in out:
            out.append(form)
    return tuple(out)


@lru_cache(maxsize=65536)
def reading(word: str) -> tuple[str, str] | None:
    """The one `(lemma, form)` Vabamorf gives a word out of context, or None
    when it gives several or none: *tule* is *tulema* and *tuli*, so a phrase
    cannot say which one EKI meant, and no item is built on it."""
    from .morph import _readings

    found = _readings(word.casefold())
    return next(iter(found)) if len(found) == 1 else None


def answer_for(lemma: str, tag: str, attested: str) -> str:
    """The phrase's own form first, then the tag's other forms (`~`), so a
    parallel form the learner knows is not marked wrong."""
    seen = {attested.casefold()}
    out = [attested]
    for form in forms(lemma, tag):
        if form.casefold() not in seen:
            seen.add(form.casefold())
            out.append(form)
    return " ~ ".join(out)


def verb_levels(conn: sqlite3.Connection, levels: tuple[str, ...] = LEVELS,
                only: frozenset[str] | None = None) -> dict[str, str]:
    """`{verb: level}` for the word list's verbs at `levels` (a theme's, with
    `only`): EVS's phrases name rarer verbs than a learner at the level needs."""
    return {lemma: level for lemma, level in verbs_at_levels(conn, levels, limit=5000)
            if only is None or lemma in only}


def phrase_pool(conn: sqlite3.Connection) -> list:
    """EVS's example phrases of `PHRASE_WORDS` words, `[]` before the import."""
    from .evs import phrases

    return phrases(conn, *PHRASE_WORDS)


#: The forms a phrase gap asks, per topic: `(tag, against, name)`. The past's
#: `sid` is left out: *läksid* is both "you went" and "they went", so the label
#: could not name one person.
PHRASE_FORMS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "olevik": (("n", "sin", "olevik, mina"), ("d", "sid", "olevik, sina"),
               ("b", "s", "olevik, tema"), ("me", "sime", "olevik, meie"),
               ("te", "site", "olevik, teie"), ("vad", "sid", "olevik, nemad")),
    "lihtminevik": (("sin", "n", "lihtminevik, mina"), ("s", "b", "lihtminevik, tema"),
                    ("sime", "me", "lihtminevik, meie"),
                    ("site", "te", "lihtminevik, teie")),
    "kaskiv": (("o", "d", "käskiv kõneviis, sina"), ("ge", "te", "käskiv kõneviis, teie")),
}

#: Vabamorf reads the connegative as the imperative (`o`): *ma ei tea* has the
#: *tea* of *tea seda!*. A phrase with one of these is never asked for an `o`.
_NEGATORS = frozenset({"ei", "ega", "pole", "polnud", "poleks"})


def phrase_drills(
    conn: sqlite3.Connection,
    topics: tuple[str, ...],
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    only: frozenset[str] | None = None,
) -> list[VerbDrill]:
    """Conjugation and imperative gaps in EKI EVS's example phrases, credited.

    A word is blanked only when it occurs once in the phrase, Vabamorf reads it
    one way out of context (`reading`), that reading is a verb at `levels` in a
    form `PHRASE_FORMS` asks, and the neighbouring form differs. One item per
    phrase and per verb form.
    """
    from collections import Counter

    from .evs import SOURCE_ID

    wanted = {(topic, tag): (against, name) for topic in topics
              for tag, against, name in PHRASE_FORMS.get(topic, ())}
    if not wanted or count <= 0:
        return []
    verbs = verb_levels(conn, levels, only)
    surfaces: dict[str, list[tuple[str, str, str]]] = {}
    for lemma in verbs:
        for topic, tag in wanted:
            for form in forms(lemma, tag):
                surfaces.setdefault(form.casefold(), []).append((topic, lemma, tag))
    pool = [p for p in phrase_pool(conn)
            if any(w.casefold() in surfaces for w, _, _ in words_in(p.estonian))]
    rng = random.Random(seed)
    rng.shuffle(pool)

    out: list[VerbDrill] = []
    seen: set[tuple[str, str]] = set()
    for phrase in pool:
        if len(out) >= count:
            break
        text = phrase.estonian
        spans = words_in(text)
        times = Counter(w.casefold() for w, _, _ in spans)
        for word, start, end in spans:
            key = word.casefold()
            if key not in surfaces or times[key] > 1:
                continue
            found = reading(key)
            match = next(((t, l, g) for t, l, g in surfaces[key] if found == (l, g)), None)
            if match is None or match[1:] in seen:
                continue
            topic, lemma, tag = match
            if tag == "o" and _NEGATORS & set(times):
                continue
            against, name = wanted[(topic, tag)]
            answer = answer_for(lemma, tag, word)
            wrong = _one(lemma, against)
            if not wrong or wrong.casefold() in answer.casefold().split(" ~ "):
                continue
            why = next((f.why_ru for f in FRAMES[topic] if f.tag == tag),
                       FRAMES[topic][0].why_ru)
            out.append(VerbDrill(
                prompt=blank(text, start, end), answer=answer, distractor=wrong,
                lemma=lemma, tag=tag, form_et=name, rule="fraas",
                why_ru=f"{why} *{lemma}* → **{word}**, не *{wrong}*.",
                topic=topic, level=verbs[lemma], source_id=SOURCE_ID))
            seen.add((lemma, tag))
            break
    return out


#: Where a topic's items come from, by rule id (`drills`). `vorm` is the
#: bleached frames, and fills whatever the others could not.
RULES: dict[str, tuple[str, ...]] = {
    "olevik": ("vorm", "fraas"),
    "lihtminevik": ("vorm", "fraas"),
    "kaskiv": ("vorm", "fraas", "eitus"),
    "tingiv": ("vorm", "eitus"),
    "umbisikuline": ("vorm", "eitus"),
    "taisminevik": ("vorm", "eitus"),
    "ma-da-inf": ("vorm", "modaal"),
}


def _source(rule: str):
    if rule == "fraas":
        return lambda conn, topic, levels, count, seed, only: phrase_drills(
            conn, (topic,), levels, count, seed, only)
    if rule == "eitus":
        from .negation import drills as negated

        return negated
    if rule == "modaal":
        from .modals import drills as modal

        return lambda conn, topic, levels, count, seed, only: modal(
            conn, levels, count, seed, only)
    raise ValueError(f"unknown rule {rule!r}")


def drills(
    conn: sqlite3.Connection,
    topic: str,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    only: frozenset[str] | None = None,
    rules: tuple[str, ...] | None = None,
) -> list[VerbDrill]:
    """A practice set for one verb topic, from each of its sources (`RULES`).

    `rules` narrows the set to some of them; none it names leaves all. With the
    frames among them, each other source gives an equal share and the frames
    fill the rest (EVS absent, a theme with few verbs); without them, each
    source fills what the one before could not. Interleaved, reproducibly.
    """
    own = RULES.get(topic, ("vorm",))
    chosen = [r for r in own if not rules or r in rules] or list(own)
    out: list[VerbDrill] = []
    for rule in chosen:
        if rule == "vorm":
            continue
        want = count // len(chosen) if "vorm" in chosen else count - len(out)
        if want > 0:
            out += _source(rule)(conn, topic, levels, want, seed, only)[:want]
    if "vorm" in chosen and len(out) < count:
        out += generate(conn, topics=(topic,), levels=levels, count=count - len(out),
                        seed=seed, only=only)
    random.Random(seed).shuffle(out)
    return out
