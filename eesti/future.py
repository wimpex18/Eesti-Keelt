"""Talking about the future (`tulevik`): EKK SÜ 27.

Estonian has no future tense. The verb stays in the present, and a time
adverbial says that it is about the future (*Ma sõidan homme koju*); verbs such
as *hakkama* point there too (*Selles majas hakkavad elama välissaadikud*).
Two kinds of item, both keyed by Vabamorf:

- `olevik`: the present after a future adverbial, in one of EKI EVS's example
  phrases (credited) or a bleached frame. The distractor is the same person in
  the past, which the adverbial rules out.
- `hakkama`: *hakkama* in the present + its **ma**-infinitive, in EVS's phrases
  (`modals.pairs`) or a frame; the distractor is the da-infinitive.

The *saama*-future (*saab olema*, EKK SÜ 28) is never graded: no item blanks
it, and a phrase holding *saama* + a ma-infinitive is not used at all.

The adverbials are EVS's own future words, pinned with EKI's Russian
(`ADVERBS`, `ATTRIBUTES`); a phrase counts only when one stands in the clause
of the verb.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass

from .config import LEVELS
from .conjugation import (VerbDrill, _one, adjacent, answer_for, blank, forms,
                          phrase_pool, reading, verb_levels, words_in)

#: Adverbs that put a clause in the future, with EKI EVS's Russian for each.
#: Only words Vabamorf reads one way: *peagi* is also *pea* + *-gi*.
ADVERBS: dict[str, str] = {
    "homme": "завтра",
    "ülehomme": "послезавтра",
    "varsti": "скоро",
    "edaspidi": "в дальнейшем",
}

#: Attributes that do the same for a time noun in the adessive (*järgmisel
#: nädalal*, *tuleval aastal*), with EKI EVS's Russian for each.
ATTRIBUTES: dict[str, str] = {"järgmine": "следующий", "tulev": "будущий"}

#: The present's persons and the past form the adverbial rules out.
PRESENT: tuple[tuple[str, str, str], ...] = (
    ("n", "sin", "olevik, mina"), ("d", "sid", "olevik, sina"),
    ("b", "s", "olevik, tema"), ("me", "sime", "olevik, meie"),
    ("te", "site", "olevik, teie"), ("vad", "sid", "olevik, nemad"),
)
_PRESENT_TAGS = frozenset(tag for tag, _, _ in PRESENT)

RULES = ("olevik", "hakkama")

WHY_PRESENT = (
    "Отдельной формы будущего времени (**tulevik**) в эстонском нет: о будущем "
    "говорят настоящим временем (**olevik**), а на будущее указывает слово "
    "времени — здесь *{when}* (EKK SÜ 27).")
WHY_HAKKAMA = (
    "**hakkama** + ma-tegevusnimi (ma-инфинитив) — так тоже говорят о будущем "
    "(EKK SÜ 27). *saama* + ma-инфинитив для действия EKK не советует (SÜ 28): "
    "не *saab tegema*, а *hakkab tegema* или *teeb*.")


@dataclass(frozen=True)
class Frame:
    sentence: str
    tag: str
    when: str


#: Frames for when EVS has too few phrases (or none: before the import).
PRESENT_FRAMES = (Frame("Homme ma ____.", "n", "homme"),
                  Frame("Järgmisel nädalal ta ____.", "b", "järgmisel nädalal"),
                  Frame("Varsti nad ____.", "vad", "varsti"))
HAKKAMA_FRAMES = (Frame("Homme hakkan ma ____.", "ma", "homme"),
                  Frame("Järgmisel aastal hakkab ta ____.", "ma", "järgmisel aastal"))


def _when(text: str, spans, lo: int, hi: int) -> str | None:
    """The future adverbial between offsets `lo` and `hi`, as written, or None."""
    for i, (word, start, _end) in enumerate(spans):
        if not lo <= start < hi:
            continue
        said = word.casefold()
        if said in ADVERBS and reading(said) and reading(said)[0] == said:
            return word
        found = reading(said)
        if found and found[0] in ATTRIBUTES and found[1] == "sg ad" and i + 1 < len(spans):
            noun = spans[i + 1]
            after = reading(noun[0])
            if after and after[1] == "sg ad" and adjacent(text, spans[i], noun):
                return f"{word} {noun[0]}"
    return None


def _saama_future(spans) -> bool:
    """Whether the phrase may hold *saama* + a ma-infinitive anywhere after it
    (*saab olema*, *saab siin toimuma*). Erring towards dropping a phrase."""
    from .modals import _governor
    from .morph import _readings

    for at, (word, _, _) in enumerate(spans):
        if _governor(word, ("saama",)) and any(
                tag == "ma" for later, _, _ in spans[at + 1:]
                for _, tag in _readings(later.casefold())):
            return True
    return False


def present_from_phrases(conn: sqlite3.Connection, verbs: dict[str, str], count: int,
                         seed: int | None) -> list[VerbDrill]:
    """The present after a future adverbial, in EVS's phrases; one per phrase
    and per verb form."""
    from .cloze import _clause_span
    from .evs import SOURCE_ID

    against = {tag: (wrong, name) for tag, wrong, name in PRESENT}
    surfaces = {f.casefold(): (lemma, tag) for lemma in verbs for tag in _PRESENT_TAGS
                for f in forms(lemma, tag)}
    future = set(ADVERBS) | {"järgmisel", "tuleval"}
    pool = [p for p in phrase_pool(conn)
            if future & {w.casefold() for w, _, _ in words_in(p.estonian)}]
    random.Random(seed).shuffle(pool)
    out: list[VerbDrill] = []
    seen: set[tuple[str, str]] = set()
    for phrase in pool:
        if len(out) >= count:
            break
        text = phrase.estonian
        spans = words_in(text)
        said = [w.casefold() for w, _, _ in spans]
        if _saama_future(spans):
            continue
        for word, start, end in spans:
            found = surfaces.get(word.casefold())
            if (found is None or found in seen or said.count(word.casefold()) > 1
                    or reading(word) != found):
                continue
            lo, hi = _clause_span(text, start)
            when = _when(text, spans, lo, hi)
            lemma, tag = found
            wrong = _one(lemma, against[tag][0])
            answer = answer_for(lemma, tag, word)
            if not when or not wrong or wrong.casefold() in answer.casefold().split(" ~ "):
                continue
            out.append(VerbDrill(
                prompt=blank(text, start, end), answer=answer, distractor=wrong,
                lemma=lemma, tag=tag, form_et=against[tag][1], rule="olevik",
                why_ru=f"{WHY_PRESENT.format(when=when)} *{lemma}* → **{word}**, "
                       f"не *{wrong}*.",
                topic="tulevik", level=verbs[lemma], source_id=SOURCE_ID))
            seen.add(found)
            break
    return out


def hakkama_from_phrases(conn: sqlite3.Connection, verbs: dict[str, str], count: int,
                         seed: int | None) -> list[VerbDrill]:
    """*hakkama* in the present + its ma-infinitive, in EVS's phrases. None at
    all if EVS showed *hakkama* with a da-infinitive too (`modals.governed`)."""
    from .modals import governed, item, pairs

    if governed(conn, ("hakkama",)).get("hakkama") != "ma":
        return []
    pool = [p for p in pairs(conn, ("hakkama",))
            if p.tags <= _PRESENT_TAGS and p.lemma in verbs]
    random.Random(seed).shuffle(pool)
    out: list[VerbDrill] = []
    seen: set[str] = set()
    for pair in pool:
        if len(out) >= count:
            break
        if pair.lemma in seen or pair.phrase in seen:
            continue
        made = item(pair, verbs[pair.lemma], "tulevik", WHY_HAKKAMA)
        if made:
            out.append(made)
            seen |= {pair.lemma, pair.phrase}
    return out


def from_frames(rule: str, verbs: dict[str, str], count: int, seed: int | None,
                top: int = 150) -> list[VerbDrill]:
    """Either kind in a bleached frame, over the commonest verbs."""
    from .modals import other_infinitive

    frames = PRESENT_FRAMES if rule == "olevik" else HAKKAMA_FRAMES
    names = {tag: (wrong, name) for tag, wrong, name in PRESENT}
    pairs = [(lemma, frame) for lemma in list(verbs)[:top] for frame in frames
             if lemma not in ("hakkama", "saama")]
    random.Random(seed).shuffle(pairs)
    out: list[VerbDrill] = []
    used: set[str] = set()
    for lemma, frame in pairs:
        if len(out) >= count:
            break
        made = forms(lemma, frame.tag)
        if lemma in used or not made:
            continue
        answer = answer_for(lemma, frame.tag, made[0])
        if rule == "olevik":
            wrong = _one(lemma, names[frame.tag][0])
            name, why = names[frame.tag][1], WHY_PRESENT.format(when=frame.when)
        else:
            wrong = other_infinitive(lemma, frame.tag)
            name, why = "ma- või da-tegevusnimi", WHY_HAKKAMA
        if not wrong or wrong.casefold() in answer.casefold().split(" ~ "):
            continue
        out.append(VerbDrill(
            prompt=frame.sentence, answer=answer, distractor=wrong, lemma=lemma,
            tag=frame.tag, form_et=name, rule=rule,
            why_ru=f"{why} *{lemma}* → **{made[0]}**, не *{wrong}*.",
            topic="tulevik", level=verbs[lemma]))
        used.add(lemma)
    return out


def drills(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    only: frozenset[str] | None = None,
    rules: tuple[str, ...] | None = None,
) -> list[VerbDrill]:
    """A `tulevik` set: each kind in `rules` (both, by default) an equal share,
    EVS's phrases first and frames for the rest, interleaved reproducibly."""
    chosen = [r for r in RULES if not rules or r in rules] or list(RULES)
    verbs = verb_levels(conn, levels, only)
    out: list[VerbDrill] = []
    for n, rule in enumerate(chosen):
        want = count // len(chosen) + (n < count % len(chosen))
        make = present_from_phrases if rule == "olevik" else hakkama_from_phrases
        got = make(conn, verbs, want, seed)[:want]
        out += got + from_frames(rule, verbs, want - len(got), seed)
    random.Random(seed).shuffle(out)
    return out
