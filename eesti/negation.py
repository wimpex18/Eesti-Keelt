"""Negation beyond the present and the simple past: the conditional, the plural
imperative, the impersonal and the perfect.

`forms.negation_drills` drills *ei* in the present (*ei lähe*) and the past
(*ei läinud*), the A1 half of `eitus`. The other negated forms belong to the
topic whose form they are, and each is keyed by the form EKK names in M 99
(*Eitav kõneliik*):

    tingiv         ei elaks                 not the indicative  ei ela
    käskiv, teie   ärge elage               not the singular's  ärge ela
    umbisikuline   elatakse : ei elata      not                 ei elatakse
    täisminevik    ei ole ~ pole elanud     not the past        ei ole elas

The sentence is one of EKI EVS's example phrases, credited, where the negation
word stands right before a word Vabamorf reads one way only (`conjugation.reading`);
a bleached frame otherwise. Both forms come from Vabamorf.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass

from .config import LEVELS
from .conjugation import (VerbDrill, _one, adjacent, answer_for, blank, forms,
                          phrase_pool, reading, verb_levels, words_in)


@dataclass(frozen=True)
class Negated:
    """One negated form: what follows the negation word, and the slip against it."""

    topic: str
    tag: str                     # Vabamorf's tag for the answer
    against: str                 # the distractor's tag; `neg` is the indicative's connegative
    name: str
    before: tuple[str, ...]      # the negation, as the words right before the gap
    frames: tuple[str, ...]
    why_ru: str


NEGATED: dict[str, Negated] = {
    "tingiv": Negated(
        "tingiv", "ks", "neg", "tingiv kõneviis, eitus", ("ei",),
        ("Ta ei ____, isegi kui saaks.", "Ilma sinuta ta ei ____."),
        "Отрицание (**eitus**) в условном наклонении: **ei** + форма на **-ks** "
        "(EKK M 99: *ei elaks*). *ei ela* — это уже изъявительное наклонение."),
    "kaskiv": Negated(
        "kaskiv", "ge", "o", "käskiv kõneviis, eitus, teie", ("ärge",),
        ("Palun ärge ____ praegu!", "Lapsed, ärge ____ täna!"),
        "Запрет для **teie** (вы): **ärge** + форма на **-ge/-ke**, как в "
        "утвердительном (EKK M 99: *ärge elage*). *ära* + чистая основа "
        "(*ära ela*) — только для **sina** (ты)."),
    "umbisikuline": Negated(
        "umbisikuline", "ta", "takse", "umbisikuline tegumood, eitus", ("ei",),
        ("Siin ei ____ pühapäeviti.", "Seal ei ____ enam."),
        "Безличный залог (**umbisikuline tegumood**) с отрицанием: **ei** + форма "
        "на **-ta/-da**, без *-kse* (EKK M 99: *elatakse*, но *ei elata*)."),
    "taisminevik": Negated(
        "taisminevik", "nud", "s", "täisminevik, eitus", ("pole", "ei ole"),
        ("Ta ei ole veel ____.", "Nad pole veel ____."),
        "Перфект (**täisminevik**) с отрицанием: **ei ole** или **pole** + "
        "причастие на **-nud**, как в утвердительном (EKK M 99: *ei ole elanud ~ "
        "pole elanud*). Не форма простого прошедшего."),
}

#: A first- or second-person subject would leave *ma ei läheksin* in doubt
#: beside *ma ei läheks*; EKK M 99 shows only the latter, so a conditional phrase
#: with one is not used.
_PERSONAL = frozenset({"ma", "mina", "sa", "sina", "me", "meie", "te", "teie"})


def _wrong(kind: Negated, lemma: str) -> str | None:
    if kind.against == "neg":
        from .forms import connegative

        return connegative(lemma)
    return _one(lemma, kind.against)


def _item(kind: Negated, prompt: str, lemma: str, attested: str, level: str | None,
          source_id: str = "") -> VerbDrill | None:
    answer = answer_for(lemma, kind.tag, attested)
    wrong = _wrong(kind, lemma)
    if not wrong or wrong.casefold() in answer.casefold().split(" ~ "):
        return None
    return VerbDrill(
        prompt=prompt, answer=answer, distractor=wrong, lemma=lemma, tag=kind.tag,
        form_et=kind.name, rule="eitus",
        why_ru=f"{kind.why_ru} *{lemma}* → **{attested}**, не *{wrong}*.",
        topic=kind.topic, level=level, source_id=source_id)


def _after_negation(text: str, spans, at: int, kind: Negated) -> bool:
    """Whether the negation stands right before the word at `at`."""
    for negation in kind.before:
        said = negation.split()
        if at < len(said):
            continue
        run = spans[at - len(said):at + 1]
        if [w.casefold() for w, _, _ in run[:-1]] == said and all(
                adjacent(text, a, b) for a, b in zip(run, run[1:])):
            return True
    return False


def from_phrases(conn: sqlite3.Connection, kind: Negated, verbs: dict[str, str],
                 count: int, seed: int | None) -> list[VerbDrill]:
    """Negated forms in EKI EVS's phrases, credited; one per phrase and verb."""
    from .evs import SOURCE_ID

    surfaces = {f.casefold(): lemma for lemma in verbs for f in forms(lemma, kind.tag)}
    markers = {n.split()[0] for n in kind.before}
    pool = [p for p in phrase_pool(conn)
            if markers & {w.casefold() for w, _, _ in words_in(p.estonian)}]
    random.Random(seed).shuffle(pool)
    out: list[VerbDrill] = []
    seen: set[str] = set()
    for phrase in pool:
        if len(out) >= count:
            break
        text = phrase.estonian
        spans = words_in(text)
        said = [w.casefold() for w, _, _ in spans]
        if kind.topic == "tingiv" and _PERSONAL & set(said):
            continue
        for at, (word, start, end) in enumerate(spans):
            lemma = surfaces.get(word.casefold())
            if (lemma is None or lemma in seen or said.count(word.casefold()) > 1
                    or reading(word) != (lemma, kind.tag)
                    or not _after_negation(text, spans, at, kind)):
                continue
            item = _item(kind, blank(text, start, end), lemma, word, verbs[lemma],
                         SOURCE_ID)
            if item:
                out.append(item)
                seen.add(lemma)
                break
    return out


def from_frames(kind: Negated, verbs: dict[str, str], count: int,
                seed: int | None, top: int = 150) -> list[VerbDrill]:
    """The same forms in bleached frames, over the commonest verbs."""
    rng = random.Random(seed)
    pairs = [(lemma, frame) for lemma in list(verbs)[:top] for frame in kind.frames]
    rng.shuffle(pairs)
    out: list[VerbDrill] = []
    used: set[str] = set()
    for lemma, frame in pairs:
        if len(out) >= count:
            break
        made = forms(lemma, kind.tag)
        if lemma in used or not made:
            continue
        item = _item(kind, frame, lemma, made[0], verbs[lemma])
        if item:
            out.append(item)
            used.add(lemma)
    return out


def drills(
    conn: sqlite3.Connection,
    topic: str,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    only: frozenset[str] | None = None,
) -> list[VerbDrill]:
    """Negated items for one of `NEGATED`'s topics: EVS's phrases first, frames
    for the rest. `[]` for any other topic."""
    kind = NEGATED.get(topic)
    if kind is None or count <= 0:
        return []
    verbs = verb_levels(conn, levels, only)
    out = from_phrases(conn, kind, verbs, count, seed)
    if len(out) < count:
        out += from_frames(kind, verbs, count - len(out), seed)
    return out
