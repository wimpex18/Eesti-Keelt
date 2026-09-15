"""A question bank shaped like the real speaking exam.

B1 speaking (from HARNO's task PDFs): **task 1** — the examiner asks from a
topic sheet, the candidates answer in turn, then reach agreement with each other
from a situation and an idea card; **task 2** — a role-play phone call to an
institution. Both are **paired**, so a solo app cannot grade them.

This supplies the questions in the exam's shape, with the other side voiced by
TTS, for rehearsal. Questions follow the level descriptors' everyday topics and
are short, because the point is to start talking. Read-aloud comparison and
open-answer feedback live in `pronunciation.py` and `api/speech.py`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    topic: str          # the topic sheet heading, as an examiner would say it
    question: str       # what gets asked, in Estonian
    hint_ru: str        # what is actually being asked for, in Russian
    kind: str           # vestlus (turn-taking) | kokkulepe (agree) | infovahetus


BANK: tuple[Question, ...] = (
    Question("Enda tutvustus", "Rääkige natuke endast ja oma perest.",
             "Расскажите о себе и семье: имя, возраст, откуда, кем работаете.",
             "vestlus"),
    Question("Töö ja amet", "Mis tööd te teete ja mis teile selle juures meeldib?",
             "Кем работаете, что нравится и что нет. Полные предложения.",
             "vestlus"),
    Question("Õppimine", "Miks te eesti keelt õpite ja kuidas te seda teete?",
             "Зачем учите эстонский и как именно — курсы, книги, приложения.",
             "vestlus"),
    Question("Vaba aeg", "Kuidas te tavaliselt nädalavahetust veedate?",
             "Как проводите выходные. Прошедшее и настоящее время.",
             "vestlus"),
    Question("Elukoht", "Kirjeldage oma kodu ja seda kohta, kus te elate.",
             "Опишите дом и район: где, какой, что рядом. Местные падежи.",
             "vestlus"),
    Question("Tervis", "Mida te teete selleks, et terve olla?",
             "Что делаете для здоровья: спорт, еда, сон.",
             "vestlus"),
    Question("Reisimine", "Rääkige ühest reisist, mis teile meelde on jäänud.",
             "Расскажите о поездке — это прошедшее время, **lihtminevik**.",
             "vestlus"),
    Question("Poes", "Te tahate sõbraga koos kingitust osta. Leppige kokku, "
                     "mida te ostate ja kui palju te kulutate.",
             "Задание на договорённость: предложите вариант, выслушайте, "
             "согласитесь или предложите другое.",
             "kokkulepe"),
    Question("Ühine üritus", "Te korraldate koos kolleegiga väikese peo. "
                             "Leppige kokku, millal ja kus see toimub.",
             "Договоритесь о времени и месте. Нужны условное наклонение и "
             "вежливые формы.",
             "kokkulepe"),
    Question("Helistamine", "Helistage kooli ja küsige eesti keele kursuste kohta: "
                            "millal need algavad ja kui palju need maksavad.",
             "Ролевая игра: вы звоните. Спросите время, цену, как записаться.",
             "infovahetus"),
    Question("Aja kokkuleppimine", "Helistage perearsti registratuuri ja leppige "
                                   "kokku vastuvõtuaeg.",
             "Ролевая игра: назовите причину, предложите время, уточните адрес.",
             "infovahetus"),
    Question("Probleem", "Te ostsite midagi, mis ei tööta. Helistage poodi ja "
                         "selgitage, mis juhtus.",
             "Ролевая игра: объясните проблему и спросите, что делать дальше.",
             "infovahetus"),
)

KINDS = {
    "vestlus": "Vestlus — küsimustele vastamine",
    "kokkulepe": "Kokkuleppele jõudmine (ülesanne 1)",
    "infovahetus": "Infovahetus telefonis (ülesanne 2)",
}


def bank(kind: str | None = None) -> list[Question]:
    return [q for q in BANK if kind is None or q.kind == kind]
