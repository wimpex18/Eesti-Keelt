"""Written explanations for the Reegel page, where a topic needs more than its
two-line summary (`grammar.REFERENCES`).

Every point restates a source named beside it: EKI's *Eesti keele käsiraamat*
(EKK) or the EKI teatmik. Examples are the sources' own, so no sentence here is
invented. Forms in tables are never written here: `eesti/lessons.py` asks
Vabamorf for them.
"""

from __future__ import annotations

from dataclasses import dataclass

EKK = "https://arhiiv.eki.ee/books/ekk09/index.php"


@dataclass(frozen=True)
class Source:
    label: str
    url: str


@dataclass(frozen=True)
class LessonText:
    points_ru: tuple[str, ...]
    sources: tuple[Source, ...]


def ekk(section: str) -> Source:
    """A numbered EKK section, by the handbook's own link scheme."""
    return Source(f"EKK {section}", f"{EKK}?link={section.replace(' ', '_')}")


LESSONS: dict[str, LessonText] = {
    "tahestik": LessonText(
        points_ru=(
            "В эстонском алфавите (**tähestik**) 27 букв: *a b d e f g h i j k l "
            "m n o p r s š z ž t u v õ ä ö ü*.",
            "Буквы *f, š, z, ž* встречаются только в заимствованных словах "
            "(**võõrsõnad**). *z* и *ž* по-эстонски звучат как слабые *s* и *š*: "
            "*zlott*, *žetoon*.",
            "*õ, ä, ö, ü* — отдельные буквы алфавита, а не варианты *o, a, u*.",
            "Долгота (**välde**) бывает смыслоразличительной, даже когда "
            "написание одинаковое: *selle palli* (II välde, omastav от *pall*) и "
            "*seda palli* (III välde, osastav).",
            "Произношение естественно варьирует; EKI не считает это ошибкой. "
            "Важно различать то, от чего зависит смысл или форма.",
        ),
        sources=(Source("EKK O 1: kiri ja tähestik", f"{EKK}?p=2&p1=1"),
                 Source("EKI teatmik: häälduse sissejuhatus",
                        "https://teatmik.eki.ee/teatmik/haalduse-sissejuhatus/")),
    ),
    "lauseehitus": LessonText(
        points_ru=(
            "Сказуемое (**öeldis**) согласуется с подлежащим (**alus**) в лице и "
            "числе: *mina loen, sina loed, tema loeb, meie loeme, teie loete, "
            "nemad loevad*.",
            "Вежливое *Teie* тоже требует множественного числа у глагола: "
            "*Te olete sümpaatne inimene*.",
            "Если полного подлежащего нет, глагол стоит в 3-м лице единственного "
            "числа: *Õues jookseb lapsi*.",
            "В утвердительном повествовательном предложении спрягаемый глагол "
            "обычно стоит **вторым** (V2): *Ma sõidan täna maale*, а не "
            "*Ma täna sõidan maale*.",
            "В начале — то, о чём говорят (**teema**), в конце — самое новое и "
            "важное (**reema**).",
            "В отрицательном или сомнительном предложении о наличии подлежащее "
            "стоит в **osastav**: *Laual pole raamatut*.",
        ),
        sources=(Source("EKK, süntaks: lauseliikmed ja sõnajärg", f"{EKK}?p=5&p1=2"),),
    ),
    "asesonad": LessonText(
        points_ru=(
            "Личных местоимений (**isikulised asesõnad**) шесть, у каждого есть "
            "короткий вариант: *mina (ma), sina (sa), tema (ta), meie (me), "
            "teie (te), nemad (nad)*.",
            "Короткая форма — в безударной позиции, длинная — когда на слове "
            "логическое ударение: *Tema sellega küll ei nõustu*.",
            "*ta* может обозначать и неодушевлённое; *tema* обычно — только "
            "человека.",
            "Возвратные (**enesekohased**): *ise, enda ~ enese, oma*. *oma* "
            "обычно не изменяется: *Sa võta oma asjad kaasa*.",
            "Указательные (**näitavad**): *see* нейтрально, *too* — то, что "
            "дальше: *Too seal on minu portfell*.",
            "Неопределённые (**umbmäärased**): *iga, igaüks, keegi, miski, mõni, "
            "kõik, mõlemad, kumbki*.",
            "Таблицы склонения местоимений здесь нет: Vabamorf склоняет их с "
            "ошибками, а проверенной таблицы с источником пока нет.",
        ),
        sources=(ekk("M 8"),),
    ),
    "kusisonad": LessonText(
        points_ru=(
            "Вопросительные местоимения (**küsivad asesõnad**): *kes, mis, kumb, "
            "missugune, milline, mitu, mitmes*.",
            "*kumb* — «который из двух»: *Kumb õde sulle rohkem meeldib?*",
            "*kumb, missugune, milline, mitmes* согласуются с существительным в "
            "числе: *Missugused inimesed nad tegelikult on?*",
            "*mis* в значении «какой» не изменяется: *Mis raamatu sa "
            "raamatukogust võtsid?*",
            "Вопросы о месте и времени — местоименные наречия (**asemäärsõnad**): "
            "*kuhu? kus? kust? millal? kuidas?* — *Kust sa tuled?*",
            "Вопрос «да или нет» начинается с частицы **kas**: *Kas Tallinnas eile "
            "vihma sadas?*",
        ),
        sources=(ekk("M 8"), ekk("M 9"), ekk("M 12")),
    ),
    "kaassonad": LessonText(
        points_ru=(
            "Послелоги и предлоги (**kaassõnad**) не изменяются и требуют от "
            "существительного определённого падежа.",
            "Большинство — **послелоги** (tagasõnad) с **omastav**: *katuse all, "
            "maja ees, aia ääres, söögi asemel*.",
            "**Предлогов** (eessõnad) мало, обычно с **osastav**: *enne koitu, "
            "keset teed, piki randa*.",
            "Исключения с другими падежами: *ilma emata* (ilmaütlev), *kuni "
            "metsani* (rajav), *tänu sõbrale* (alaleütlev).",
            "Некоторые стоят и до, и после: *mööda teed ~ teed mööda*. У других "
            "меняется смысл: *pärast tööd* (время) — *eksimuse pärast* (причина).",
            "Часто есть параллель с падежом: *Pani raamatu laua peale ~ Pani "
            "raamatu lauale*.",
        ),
        sources=(ekk("M 11"), ekk("M 11a")),
    ),
    "sidesonad": LessonText(
        points_ru=(
            "Союзы (**sidesõnad**) связывают части предложения и не меняют их "
            "форму. Их около двадцати: *ja, ning, ega, ehk, või, aga, kuid, ent, "
            "vaid, et, kui, kuna, sest, kuni, kuigi, ehkki, nagu*.",
            "**Сочинительные** (rinnastavad): *ja, ning, ega, või, aga, kuid, "
            "vaid* — *Tuleksin hea meelega, aga mul pole aega*.",
            "**Подчинительные** (alistavad): *et, kuna, sest, kuigi, nagu* — "
            "*Ma tean, et loota pole midagi*.",
            "*kui* бывает и сравнительным, и условным: *Jüri on noorem kui Mari* — "
            "*Söö, kui maitseb*.",
            "Многие союзы входят в составные: *nii et, selleks et, sellepärast et, "
            "kas … või, ei … ega*.",
            "Придаточное предложение всегда отделяется запятой (см. "
            "*kirjavahemärgid*).",
        ),
        sources=(ekk("M 13"),),
    ),
    "maarsonad": LessonText(
        points_ru=(
            "Наречия (**määrsõnad**) не изменяются и в предложении служат "
            "обстоятельством (**määrus**).",
            "Наречия места часто идут тройками, как местные падежи: *kuhu? — alla, "
            "kus? — all, kust? — alt*; *lähemale, lähemal, lähemalt*.",
            "Время: *homme, täna, eile, ammu, varsti, sageli, tihti, harva*.",
            "Образ действия: *hästi, halvasti, vaikselt, valjusti* — *Ära räägi "
            "nii valjusti*.",
            "Количество и степень: *palju, natuke, väga, üsna, võrdlemisi* — "
            "*Täna on üsna ilus ilm*.",
            "Некоторые наречия сравниваются: *ilusti, ilusamini, kõige "
            "ilusamini*.",
        ),
        sources=(ekk("M 7"), ekk("M 7a")),
    ),
    "tulevik": LessonText(
        points_ru=(
            "В изъявительном наклонении четыре времени: **olevik, lihtminevik, "
            "täisminevik, enneminevik**. Отдельного будущего времени нет.",
            "Будущее выражается **настоящим временем**: *Jaan ehitab endale "
            "suvila* — строит сейчас или построит.",
            "Что речь о будущем, показывают слова времени: *homme, varsti, "
            "järgmisel aastal* (см. *määrsõnad*).",
            "Завершённость в будущем передаёт täissihitis: *Ma loen raamatu "
            "läbi* — «прочитаю»; *Ma loen raamatut* — «читаю».",
        ),
        sources=(Source("EKK, morfoloogilised kategooriad: aeg", f"{EKK}?p=3&p1=4"),
                 ekk("SÜ 37")),
    ),
    "uhendverbid": LessonText(
        points_ru=(
            "Составной глагол (**ühendverb**) = глагол + наречие-приставка "
            "(**abimäärsõna**) с новым значением: *läbi lugema, vastu võtma, ära "
            "sõitma, kaasa võtma, valmis saama*.",
            "*ära, läbi, valmis* выражают завершённость: *ära minema, läbi "
            "lugema, valmis tegema*.",
            "Некоторые частицы никогда не отвечают на свой вопрос и живут только "
            "с глаголом: *kallale kippuma, jälile jõudma, kaasa tulema*.",
            "В предложении частица может стоять отдельно от глагола: *Loe see "
            "ankeet läbi*.",
            "Слитно такие глаголы пишутся только в отдельных формах, например в "
            "причастиях: *äravõetud õigused*.",
        ),
        sources=(ekk("M 10"), ekk("M 10a"), Source("EKK, sõnamoodustus: liitverbid",
                                                  f"{EKK}?p=4&p1=2")),
    ),
    "liitsonad": LessonText(
        points_ru=(
            "Сложное слово (**liitsõna**) пишется слитно и имеет одно главное "
            "ударение — на первой части: *vanaema*, но словосочетание *vana ema*.",
            "Изменяется только последняя часть: *kalliskivi → kalliskivist*, а "
            "словосочетание — *kallis kivi → kallist kivist*.",
            "Первая часть — в **nimetav** (*tornkraana, kipsplaat*) или в "
            "**omastav** (*aknaklaas, söögilaud, lapsehoidja*).",
            "Последняя часть определяет смысл: *muusikaõpetaja* — учитель, "
            "*tolmuimeja* — прибор.",
        ),
        sources=(Source("EKK, sõnamoodustus", f"{EKK}?p=4&p1=1"),
                 Source("EKI teatmik: liitsõnad",
                        "https://teatmik.eki.ee/teatmik/sona/sonamoodustus/liitsonad/")),
    ),
}
