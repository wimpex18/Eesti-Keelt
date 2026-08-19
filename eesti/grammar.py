"""Grammar reference: link drills to the authority, don't reinvent it.

Where Estonian grammar actually comes from
------------------------------------------
Keeleklikk and Keeletee are courses, not references, and neither exposes an API.
But the authority does exist online and free: **Eesti keele käsiraamat** (EKK),
the Estonian Language Institute's handbook by Erelt, Erelt and Ross, hosted at
`arhiiv.eki.ee/books/ekk09/` with stable per-section URLs.

Its syntax chapter numbers the rules this app drills — SÜ 37–44 are the object,
täissihitis vs osasihitis, and the hard cases of choosing between them. So each
drill links to the section that defines it. Three reasons that beats writing our
own explanations:

  * it is authoritative, and a learner who doubts a drill can check the source;
  * it uses the terminology the exam uses;
  * it does not rot, because we are not maintaining a parallel grammar.

Terminology note: what the error log calls `obj-case` is **täissihitis**
(total object — genitive or nominative) versus **osasihitis** (partial object —
partitive). Using the real terms is better teaching than inventing our own, and
they are what an examiner will say.
"""

from __future__ import annotations

from dataclasses import dataclass

EKK_BASE = "https://arhiiv.eki.ee/books/ekk09/index.php"

# Chapter ids in EKK's URL scheme. `p1` selects a sub-page within the chapter,
# and there are no per-section anchors, so a link lands on the page that
# *contains* the section and `ekk_section` is the label to look for on it.
#
# Getting these right needs reading the handbook, not guessing: the morphology
# chapter numbers its sections **M**, not `MO`, and its sub-pages do not run in
# section order. An earlier version of this table had six of seven entries
# pointing at a real page with the wrong section on it — which is worse than no
# link, because it looks checked.
MORFOLOOGIA, SUNTAKS = 3, 5


@dataclass(frozen=True)
class Reference:
    """One rule, its Estonian name, and where the handbook defines it."""

    tag: str            # our error-log tag
    et_term: str        # the proper Estonian grammatical term
    ru_term: str        # how it is named in Russian, for the explanations
    ekk_section: str    # e.g. "SÜ 37"
    chapter: int
    subsection: int
    summary_ru: str

    @property
    def url(self) -> str:
        return f"{EKK_BASE}?p={self.chapter}&p1={self.subsection}"


REFERENCES: dict[str, Reference] = {
    "obj-case": Reference(
        tag="obj-case",
        et_term="täissihitis ja osasihitis",
        ru_term="полное и частичное дополнение",
        ekk_section="SÜ 37",
        chapter=SUNTAKS,
        subsection=2,
        summary_ru=(
            "**Täissihitis** (omastav või nimetav) — действие завершено и объект "
            "охвачен целиком. **Osasihitis** (osastav) — процесс, часть объекта "
            "или отрицание. Отрицание всегда требует osastav."
        ),
    ),
    "verb-form": Reference(
        tag="verb-form",
        et_term="verbi põhivormid",
        ru_term="основные формы глагола",
        ekk_section="M 19",
        chapter=MORFOLOOGIA,
        subsection=2,
        summary_ru=(
            "У эстонского глагола несколько основ, и они не выводятся из "
            "ma-инфинитива по одному правилу: *minema → lähen*, *tegema → teen*. "
            "Основные формы нужно запоминать вместе."
        ),
    ),
    "gen-stem": Reference(
        tag="gen-stem", et_term="omastava tüvi", ru_term="основа генитива",
        ekk_section="M 51", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Все падежи кроме nimetav и osastav строятся от **основы омастава**. "
            "Зная omastav, ты знаешь почти всё слово."
        ),
    ),
    "gradation": Reference(
        tag="gradation", et_term="astmevaheldus", ru_term="чередование ступеней",
        ekk_section="M 22", chapter=MORFOLOOGIA, subsection=3,
        summary_ru=(
            "Согласная в основе чередуется между сильной и слабой ступенью: "
            "*sõber → sõbra*, *pood → poe*. Это регулярно, но по типам."
        ),
    ),
    "loc-case": Reference(
        tag="loc-case", et_term="kohakäänded", ru_term="местные падежи",
        ekk_section="M 53", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Шесть местных падежей парами: внутренние (sisse/sees/seest) и "
            "внешние (peale/peal/pealt). Выбор зависит от того, мыслится ли "
            "место как объём или как поверхность."
        ),
    ),
    "rektsioon": Reference(
        tag="rektsioon", et_term="rektsioon", ru_term="управление глагола",
        ekk_section="SÜ 64", chapter=SUNTAKS, subsection=2,
        summary_ru=(
            "Глагол требует определённого падежа, и он часто не совпадает с "
            "русским: *mõtlema **millele*** (алалютлев), не «о чём»."
        ),
    ),
    "word-order": Reference(
        tag="word-order", et_term="lause sõnajärg", ru_term="порядок слов",
        ekk_section="SÜ 90", chapter=SUNTAKS, subsection=2,
        summary_ru=(
            "Эстонский порядок слов свободнее русского, но не произволен: "
            "**самое важное — в конце**, а спрягаемый глагол обычно вторым "
            "(*Eile **käisin** ma kinos*). Инверсия — не ошибка, а способ "
            "выделить."
        ),
    ),
    "ma-da-inf": Reference(
        tag="ma-da-inf", et_term="ma- ja da-infinitiiv",
        ru_term="ma- и da-инфинитив",
        ekk_section="M 73", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Какой инфинитив брать, решает управляющий глагол: *pean õppi**ma***, "
            "но *tahan õppi**da***. Это список, а не правило."
        ),
    ),
}


def reference_for(tag: str) -> Reference | None:
    """The handbook entry for an error tag, or None if we have no mapping."""
    return REFERENCES.get(tag)


def describe(tag: str) -> dict:
    """Reference as plain data, for the API and the UI."""
    ref = reference_for(tag)
    if ref is None:
        return {"tag": tag, "known": False}
    return {
        "tag": ref.tag,
        "known": True,
        "et_term": ref.et_term,
        "ru_term": ref.ru_term,
        "summary_ru": ref.summary_ru,
        "ekk_section": ref.ekk_section,
        "url": ref.url,
    }
