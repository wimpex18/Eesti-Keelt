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
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass

from estnltk.vabamorf.morf import synthesize

from .config import LEVELS
from .item import GradedItem


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
