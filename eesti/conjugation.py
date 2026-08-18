"""Tenses, moods, infinitives and voice — the rest of the verb.

`verbs.py` drills **irregular stems**: verbs where stripping `-ma` and adding the
ending gives the wrong answer, so the distractor writes itself. That covers one
topic, `verb-form`, and it deliberately skips every regular verb, because a verb
whose naive form is already right teaches nothing about *stems*.

But it teaches plenty about everything else. A learner who can build `õpib` still
has to choose between `õpib` and `õppis`, between `õpiks` and `õpib`, between
`pean õppima` and `tahan õppida`. Those are nine separate curriculum topics, and
what they test is not the stem — it is **the marker**.

So the distractor here is not a naive form. It is **the same verb in the
neighbouring form the learner confuses it with**:

    tingiv kõneviis   õpiks    against the present   õpib
    lihtminevik       õppis    against the present   õpib
    täisminevik       õppinud  against the past      õppis
    umbisikuline      õpitakse against the personal  õpib
    ma-/da-infinitiiv õppima   against               õppida

Every one of those pairs is a real confusion with a real marker to learn, and
both halves come from Vabamorf rather than from a table I typed. Where a verb
happens to produce the same string for both, there is no contrast and the item is
dropped — the same rule that excludes `kino` from the object-case pool.

The `ma`/`da` pair is the one that is not a marker but a **list**: which
infinitive you use is decided by the governing verb, not by meaning. That is why
its frames come in pairs — *pean* takes `ma`, *tahan* takes `da` — and why the
explanation says so rather than pretending there is a rule to derive.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass

from estnltk.vabamorf.morf import synthesize

from .config import LEVELS


@dataclass(frozen=True)
class Frame:
    """One drillable verb form: how to elicit it, and what it is confused with."""

    tag: str            # Vabamorf synthesis tag for the answer
    against: str        # tag for the distractor — the neighbouring form
    name: str           # Estonian name, as a teacher would say it
    sentence: str       # frame with ____ where the form goes
    why_ru: str


# Keyed by curriculum topic id, so a generated item files itself against the
# syllabus. Frames use the pronoun that agrees with the form, so the sentence is
# grammatical whichever verb is dropped into it.
#
# They are also **object-free**, which is not cosmetic. The first version wrote
# the impersonal as *"Seda ____ iga päev"*, and `seda` is a partitive object —
# fine for `tegema`, wrong for `liikuma`, and there is no transitivity flag in
# the data to filter on. A locative frame (*"Siin ____ iga päev"*) reads
# correctly for transitive and intransitive verbs alike, which removes the need
# for the per-verb semantic pool that the object-case templates have to carry.
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
class VerbDrill:
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

    def to_dict(self) -> dict:
        from dataclasses import asdict

        return asdict(self) | {"hint": self.hint, "reference": self.reference}

    def check(self, given: str) -> bool:
        return given.strip().lower() == self.answer.lower()

    @property
    def hint(self) -> str:
        return f"{self.lemma}, {self.form_et}"

    @property
    def solution(self) -> str:
        answer = self.answer
        if self.prompt.startswith("____"):
            answer = answer[:1].upper() + answer[1:]
        return self.prompt.replace("____", answer)

    @property
    def reference(self) -> dict | None:
        from .curriculum import by_id
        from .grammar import describe

        tag = by_id(self.topic).tag
        return describe(tag) if tag else None


def verbs_at_levels(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    limit: int = 400,
) -> list[tuple[str, str]]:
    """Level-appropriate verbs, most frequent first.

    Frequency order matters more here than for nouns: a learner meets *saama*
    and *tegema* every day and *sarnanema* almost never, so drilling the
    conditional is worth far more on the first than the second.
    """
    marks = ",".join("?" * len(levels))
    return [
        (row[0], row[1])
        for row in conn.execute(
            f"""SELECT word, proficiency FROM words
                WHERE proficiency IN ({marks})
                  AND (','||COALESCE(pos,'')||',') LIKE '%,v,%'
                ORDER BY (freq_rank IS NULL OR freq_rank = 0), freq_rank
                LIMIT ?""",
            (*levels, limit),
        )
    ]


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
) -> list[VerbDrill]:
    """Drills for the tense, mood, infinitive and voice topics.

    An item ships only when the answer and the neighbouring form actually
    differ. For a few verbs they collide — the present and the imperative of some
    stems, for instance — and an item whose two options are the same string
    measures nothing.
    """
    wanted = tuple(topics) if topics else tuple(FRAMES)
    unknown = set(wanted) - set(FRAMES)
    if unknown:
        raise ValueError(f"no frames for topic(s): {sorted(unknown)}")

    rng = random.Random(seed)
    # Frequency-ordered, then shuffled *within the common band*. The frames are
    # deliberately bleached ("Eile ta ____"), which reads fine with a verb the
    # learner meets daily and oddly with one they never will — "Hirmutage palun
    # kohe!" is grammatical and useless. Restricting to the frequent end costs
    # nothing, since those are also the verbs worth conjugating correctly.
    pool = verbs_at_levels(conn, levels)[:top]
    if not pool:
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
