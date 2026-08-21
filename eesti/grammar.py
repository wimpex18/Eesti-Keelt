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
ORTOGRAAFIA, MORFOLOOGIA, SUNTAKS = 2, 3, 5


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



# ---------------------------------------------------------------------------
# Topic references
#
# The nine entries above are keyed by *error tag* -- the fixed set the Notion
# log validates against (`config.TAGS`), which must not grow. These are keyed
# by **topic id** instead, so a curriculum topic can carry a handbook link
# without inventing a tenth error tag.
#
# Measured before this was written: of the 23 topics that generate exercises,
# only 5 carried a reference. A learner who got an item wrong received an
# explanation and no way to read the underlying rule.
#
# **Every section number below was read off the handbook, not inferred.** That
# matters more than it sounds: a summarising fetch of the same page returned
# numbers shifted by one, which would have made `M 51` point at the partitive
# instead of the genitive. Two of them were checked against entries that were
# already correct, and it was the summary that was wrong. `M 77` is another
# trap -- it is *Oleviku kesksõna*, the present participle, not the present
# tense, which is `M 85`.
# ---------------------------------------------------------------------------

TOPIC_REFERENCES: dict[str, Reference] = {
    "pohivormid": Reference(
        tag="pohivormid", et_term="nimisõna põhivormid",
        ru_term="основные формы имени",
        ekk_section="M 50", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Три формы, которые даёт словарь: **nimetav** (M 50), **omastav** "
            "(M 51) и **osastav** (M 52). Все остальные падежи строятся от "
            "основы омастава, поэтому эти три надо знать вместе."
        ),
    ),
    "osastav": Reference(
        tag="osastav", et_term="osastav kääne", ru_term="частичный падеж",
        ekk_section="M 52", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Osastav отвечает за неполный охват: часть количества, незавершённое "
            "действие и **любое отрицание**. Это тот падеж, который в русском "
            "чаще всего не имеет прямого соответствия."
        ),
    ),
    "mitmus": Reference(
        tag="mitmus", et_term="mitmus", ru_term="множественное число",
        ekk_section="M 67", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Множественное число строится от основы омастава: *raamat → "
            "raamatu → raamatud*. Отсюда же короткая форма множественного "
            "(vokaalmitmus, M 69)."
        ),
    ),
    "harvad-kaanded": Reference(
        tag="harvad-kaanded", et_term="saav, rajav, olev, ilmaütlev, kaasaütlev",
        ru_term="редкие падежи",
        ekk_section="M 60", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Пять падежей, идущих подряд в справочнике: **saav** (M 60), "
            "**rajav** (M 61), **olev** (M 62), **ilmaütlev** (M 63) и "
            "**kaasaütlev** (M 64). Все — от основы омастава."
        ),
    ),
    "olevik": Reference(
        tag="olevik", et_term="olevik", ru_term="настоящее время",
        ekk_section="M 85", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Настоящее время. Личные окончания добавляются к основе настоящего "
            "времени, а она не всегда выводится из ma-инфинитива: *minema → "
            "lähen*."
        ),
    ),
    "lihtminevik": Reference(
        tag="lihtminevik", et_term="lihtminevik", ru_term="простое прошедшее",
        ekk_section="M 86", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Простое прошедшее (имперфект) — основное повествовательное время. "
            "Показатель -si-/-s-, но у многих глаголов меняется основа."
        ),
    ),
    "taisminevik": Reference(
        tag="taisminevik", et_term="täisminevik", ru_term="перфект",
        ekk_section="M 87", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Перфект: **olema** в настоящем + причастие на -nud. Говорит о "
            "результате, который важен сейчас."
        ),
    ),
    "enneminevik": Reference(
        tag="enneminevik", et_term="enneminevik", ru_term="плюсквамперфект",
        ekk_section="M 88", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Предпрошедшее: **olema** в прошедшем + причастие на -nud. "
            "Действие, завершившееся раньше другого прошедшего."
        ),
    ),
    "tingiv": Reference(
        tag="tingiv", et_term="tingiv kõneviis", ru_term="условное наклонение",
        ekk_section="M 92", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Условное наклонение с показателем **-ksi-/-ks**: *ma teeksin* — "
            "«я бы сделал». Одна форма покрывает и вежливую просьбу."
        ),
    ),
    "kaskiv": Reference(
        tag="kaskiv", et_term="käskiv kõneviis", ru_term="повелительное наклонение",
        ekk_section="M 93", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Повелительное наклонение. Форма 2 л. ед. ч. — это основа без "
            "окончания (*tee!*), остальные лица берут -ge-/-gu-."
        ),
    ),
    "kesksonad": Reference(
        tag="kesksonad", et_term="kesksõnad", ru_term="причастия",
        ekk_section="M 76", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Четыре причастия: настоящего и прошедшего времени, личное и "
            "безличное — *tegev, teinud, tehtav, tehtud*. Причастие на -nud "
            "нужно для перфекта и для отрицания в прошедшем."
        ),
    ),
    "umbisikuline": Reference(
        tag="umbisikuline", et_term="umbisikuline tegumood",
        ru_term="безличный залог",
        ekk_section="M 83", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Безличная форма: действие есть, деятель не назван — *tehakse*, "
            "*tehti*. Ближе к русскому «делают», чем к пассиву."
        ),
    ),
    "vordlusastmed": Reference(
        tag="vordlusastmed", et_term="võrdlusastmed", ru_term="степени сравнения",
        ekk_section="M 100", chapter=MORFOLOOGIA, subsection=4,
        summary_ru=(
            "Три степени: **algvõrre** (M 100), **keskvõrre** (M 101) и "
            "**ülivõrre** (M 102). Сравнительная строится от основы омастава "
            "плюс -m: *suur → suure → suurem*."
        ),
    ),
    "eitus": Reference(
        tag="eitus", et_term="eitus", ru_term="отрицание",
        ekk_section="SÜ 30", chapter=SUNTAKS, subsection=2,
        summary_ru=(
            "Отрицание — это **kõneliik** сказуемого. После **ei** глагол "
            "теряет личное окончание (*ostan → ei osta*), а в прошедшем "
            "ставится форма на -nud. И отрицание всегда требует osastav у "
            "дополнения."
        ),
    ),
    "arvsonad": Reference(
        tag="arvsonad", et_term="põhiarvsõnad", ru_term="количественные числительные",
        ekk_section="O 51", chapter=ORTOGRAAFIA, subsection=10,
        summary_ru=(
            "Как числительные записываются и склоняются. Считаемое слово после "
            "числительного больше единицы стоит в **osastav**: *kaks raamatut*."
        ),
    ),
    "jargarvud": Reference(
        tag="jargarvud", et_term="järgarvsõnad", ru_term="порядковые числительные",
        ekk_section="O 51", chapter=ORTOGRAAFIA, subsection=10,
        summary_ru=(
            "Порядковое числительное цифрами пишется **с точкой**: *3. koht*, "
            "*21. sajand*. Точка и есть показатель порядка — без неё это "
            "количественное."
        ),
    ),
    "kirjavahemargid": Reference(
        tag="kirjavahemargid", et_term="koma", ru_term="запятая",
        ekk_section="O 56", chapter=ORTOGRAAFIA, subsection=11,
        summary_ru=(
            "Запятая в эстонском ставится по грамматике, а не по интонации: "
            "**каждое** придаточное отделяется запятой, в том числе после "
            "*et*, *kui*, *sest*. Это ближе к русскому правилу, чем к "
            "английскому."
        ),
    ),
    "uhildumine": Reference(
        tag="uhildumine", et_term="omadussõnaline täiend",
        ru_term="согласование определения",
        ekk_section="SÜ 98", chapter=SUNTAKS, subsection=3,
        summary_ru=(
            "Прилагательное принимает тот же падеж и число, что и "
            "существительное: *suures majas*, *ilusaid päevi*. "
            "**Исключение:** в rajav, olev, ilmaütlev и kaasaütlev определение "
            "остаётся в omastav — *suure majani*, *suure majaga*, а не "
            "*suureni majani*."
        ),
    ),
}


def reference_for(tag: str) -> Reference | None:
    """The handbook entry for an error tag or a topic id, or None.

    Error tags are looked up first, because that is the older and narrower set
    and the two do not collide -- `obj-case` is both a tag and a topic id, and
    the tag's entry is the one written for a learner who got it wrong.
    """
    return REFERENCES.get(tag) or TOPIC_REFERENCES.get(tag)


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
