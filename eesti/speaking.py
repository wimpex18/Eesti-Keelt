"""A question bank shaped like the real speaking exam.

What the B1 exam actually does, from HARNO's own task PDFs: **task 1** gives the
examiner a topic sheet, the two candidates answer in turn, and then they talk to
*each other* to reach agreement from a situation description, with an idea card
of pictures. **Task 2** is a role-play — one candidate phones an institution,
the other is its employee.

Both halves are **paired**. That is the fact that decides what is worth
building. A solo record-and-score loop trains almost none of what is graded:
turn-taking, picking up the other person's point, negotiating agreement. And
scoring pronunciation from audio is a research problem, not a feature — EKI
already publishes free pronunciation exercises, which is a better use of the
learner's time than a number this app would have to invent.

So what is here is the part a phone can honestly do: **the questions, in the
exam's shape, with the other side voiced by TTS.** No score, no transcript, no
upload — the recording stays in the browser. The value is rehearsal and hearing
yourself, and the interface says exactly that rather than implying a grade.

Questions are written to the exam's topic areas (the everyday domains the
level descriptors name) and kept short, because the point is to start talking.
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
             "Расскажите о поездке — это прошедшее время, лихтминевик.",
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
