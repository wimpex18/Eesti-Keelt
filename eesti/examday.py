"""*Eksamipäev*: what the day of the exam asks, from HARNO's own sheet.

Every line restates a rule from HARNO's information sheet for examinees
(`SOURCE`, read 9 Oct 2026); nothing is added. The learner reads it in the
explanation language, with the sheet linked. The timing line is per level.
"""

from __future__ import annotations

SOURCE = ("https://harno.ee/sites/default/files/documents/2025-01/"
          "Information%20sheet%20for%20the%20Estonian%20language%20proficiency%20examinee.pdf")

EXAM_DAY: tuple[str, ...] = (
    "Экзамен начинается ровно в 10.00; опоздавших не допускают. Приходи за "
    "15–20 минут.",
    "Документ: действующая ID-карта, паспорт или вид на жительство. "
    "Водительские права документом не считаются.",
    "Часы снимают, телефон выключают и кладут в отведённое место до конца "
    "части экзамена.",
    "Пиши разборчиво: неразборчивое из-за почерка считается ошибкой. В "
    "письменной части — письменными буквами (kirjatähed).",
    "Только чёрная или синяя ручка. Карандаш, стираемые ручки и корректор "
    "нельзя; исправление — зачеркнуть слово целиком.",
    "Ответы с выбором — заглавными печатными буквами (A, B, C); I и J, C и G "
    "должны отличаться. Два отмеченных ответа — ответ неверный.",
    "Нельзя: словари, учебники, наушники, чужая помощь, телефон и смарт-часы.",
    "Порядок: письмо, затем аудирование, затем чтение. Устная часть — через "
    "15–20 минут после письменной; её записывают.",
    "Экзамен сдан при 60% от суммы баллов, если ни одна часть не на нуле.",
    "Результаты — не позже чем через 40 дней.",
    "Ниже 45% или неявка без уважительной причины — пересдача не раньше чем "
    "через шесть месяцев (если не отменить регистрацию за 4 рабочих дня).",
)

#: The written part's length per level, from the same sheet.
TIMING: dict[str, str] = {
    "A2": "Письменная часть A2 — 1 ч 50 мин: письмо 30 мин, аудирование около "
          "30 мин, чтение 50 мин.",
    "B1": "Письменная часть B1 — 2 часа: письмо 35 мин, аудирование около "
          "35 мин, чтение 50 мин. Претенденты на гражданство от 65 лет "
          "освобождены от письма на B1.",
}


def for_level(level: str) -> dict:
    """The day's rules for one level, with where they come from."""
    return {"rules": [*EXAM_DAY, TIMING[level]] if level in TIMING else list(EXAM_DAY),
            "source": SOURCE,
            "source_name": "Haridus- ja Noorteamet: teabeleht eesti keele "
                           "tasemeeksami sooritajale"}
