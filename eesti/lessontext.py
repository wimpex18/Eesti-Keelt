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
            "Упражнения здесь — на слух, в записях EKI: II или III долгота "
            "(*selle salli* — *seda salli*), одна буква (*kapp* — *käpp*), "
            "краткий или долгий звук (*kana* — *kanna*). Произносить вслух — в "
            "упражнениях EKI *e-hääldusharjutused* на Sõnaveeb.",
        ),
        sources=(Source("EKK O 1: kiri ja tähestik", f"{EKK}?p=2&p1=1"),
                 ekk("O 8"),
                 Source("EKI teatmik: häälduse sissejuhatus",
                        "https://teatmik.eki.ee/teatmik/haalduse-sissejuhatus/"),
                 Source("EKI e-hääldusharjutused (Sõnaveeb)",
                        "https://sonaveeb.ee/pronunciation-exercises/")),
    ),
    "fraasid": LessonText(
        points_ru=(
            "Фразы для первых встреч из сборника EKI: приветствие (*Tere!*, "
            "*Tere hommikust!*), знакомство (*Mina olen …*), прощание (*Head "
            "aega!*, *Nägemist!*), извинение (*Vabandust!*), благодарность "
            "(*Aitäh!*), пожелания (*Head isu!*).",
            "На некоторые фразы есть привычный ответ: *Aitäh! – Palun!*, "
            "*Vabandust! – Ei ole midagi.*, *Kuidas läheb? – Hästi! Aga sul?*",
            "Русский перевод фраз — из эстонско-русского словаря EKI (EVS), где "
            "он там есть; где нет, перевод не показывается.",
        ),
        sources=(Source("EKI: Kasulikke väljendeid A1-tasemel eesti keele õppijale",
                        "https://sonaveeb.ee/learn#v-pills-kasulikke-valjendeid-a1"),),
    ),
    "arvud": LessonText(
        points_ru=(
            "0–10: *null, üks, kaks, kolm, neli, viis, kuus, seitse, kaheksa, "
            "üheksa, kümme*.",
            "11–19 — с *-teist*: *üksteist, kaksteist … üheksateist*. Можно и "
            "полностью: *seitseteistkümmend*.",
            "Десятки — с *-kümmend*: *kakskümmend, kolmkümmend … "
            "üheksakümmend*; 100 — *sada*.",
            "*-teist(kümmend)* и *-kümmend* пишутся слитно, остальное — "
            "раздельно: *nelikümmend kolm*, *sada kaheksa*.",
        ),
        sources=(ekk("O 42"),
                 Source("EKI teatmik: arvukirjutus",
                        "https://teatmik.eki.ee/teatmik/arvukirjutus/")),
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
            "Таблица ниже — из EKI teatmik; Vabamorf склоняет местоимения с "
            "ошибками, поэтому формы взяты оттуда.",
        ),
        sources=(ekk("M 8"), Source("EKI teatmik: asesõnade käänamine",
                                    "https://teatmik.eki.ee/teatmik/asesonade-kaanamine/")),
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
            "*saama* + ma-инфинитив (*Elu saab seal olema raske*) — калька с "
            "немецкого; EKK советует его избегать, особенно для действий: не "
            "*saab hoolitsema*, а *hakkab hoolitsema* или *hoolitseb*.",
        ),
        sources=(Source("EKK, morfoloogilised kategooriad: aeg", f"{EKK}?p=3&p1=4"),
                 ekk("SÜ 37"), ekk("SÜ 28")),
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
    "kellaaeg": LessonText(
        points_ru=(
            "Полный час: **kell** + числительное: *Ma ärkan kell seitse*. "
            "Цифрами — *kell 19*, минуты при полном часе не пишут.",
            "Доли часа считаются к **следующему** часу, как «половина десятого»: "
            "*veerand kümme* = 9.15, *pool kümme* = 9.30, *kolmveerand kümme* = 9.45.",
            "Когда? — день недели в **alalütlev**: *Nad sõidavad neljapäeval maale*.",
            "К какому сроку? — **saav**: *Koosolek määrati reedeks*, *kell kuueks*.",
            "С какого времени — **seestütlev**, до какого — **rajav**: *hommikust "
            "õhtuni*, *pood on lahti kella 22-ni*.",
            "На письме: *10.30* или *10:30*; промежуток — через тире: *kauplus on "
            "lahti 9–18*.",
        ),
        sources=(Source("Opiq: Kellaaeg", "https://www.opiq.ee/kit/287/chapter/17412"),
                 ekk("M 57"), ekk("M 59"), ekk("M 61"),
                 Source("EKI teatmik: arvukirjutus",
                        "https://teatmik.eki.ee/teatmik/arvukirjutus/")),
    ),
    "mul-on": LessonText(
        points_ru=(
            "«У меня есть» — владелец в **alalütlev** (-l) + *on*: *Mul on kõht "
            "tühi*, *Maril on kaks last*. Глагола «иметь» здесь нет.",
            "Глагол при этом в ед. ч., даже если вещей много: *Neil oli kolm "
            "poega*.",
            "«У меня нет» — вещь в **osastav**: *Laual pole raamatut*, *Mul ei ole "
            "autot*.",
            "«Мне нравится» — кому в **alaleütlev** (-le): *See tüdruk meeldib mulle "
            "väga*; что делать — **da**-инфинитив: *Talle meeldib tantsida*.",
            "«Мне нужно» — *Mul on vaja* + osastav или da-инфинитив: *Mul on uut "
            "rahakotti vaja*, *Meil oli vaja maale sõita*.",
        ),
        sources=(ekk("M 59"), Source("EKK, süntaks: alus ja öeldis", f"{EKK}?p=5&p1=2"),
                 Source("EKI põhisõnavara sõnastik (PSV): meeldima, vaja",
                        "https://sonaveeb.ee/search/unif/dlall/dsall/meeldima/1/est")),
    ),
    "kaima-minema": LessonText(
        points_ru=(
            "**käima** отвечает на *kus?* и *mida tegemas?*: *Käisin eelmisel "
            "nädalal Riias* — был и вернулся.",
            "Регулярно ходить куда-то — тоже **käima** + *kus?*: *Suuremad lapsed "
            "käivad koolis*.",
            "**minema** отвечает на *kuhu?* и *mida tegema?*: *Naine läks poodi* — "
            "отправилась туда.",
            "Отсюда пары: *käisin ujumas* (плавал и вернулся) — *läksin ujuma* "
            "(пошёл плавать).",
            "Формы *minema* неправильные: *lähen, läksin, läks, minna*.",
        ),
        sources=(Source("EKI põhisõnavara sõnastik (PSV): käima, minema",
                        "https://sonaveeb.ee/search/unif/dlall/dsall/k%C3%A4ima/1/est"),
                 ekk("SÜ 65")),
    ),
    "tuletus": LessonText(
        points_ru=(
            "**-mine** делает из любого глагола название действия: *rääkima → "
            "rääkimine*, *kasvama → kasvamine*. Так же называют занятия: "
            "*laulmine, joonistamine, matkamine*.",
            "Суффикс присоединяется к основе ma-инфинитива: *jooksma → jooksmine*.",
            "Управление глагола сохраняется: *räägib tööst → tööst rääkimine*; "
            "подлежащее и дополнение становятся omastav: *sinu rääkimine*.",
            "**-ja** — тот, кто делает: *sööja, laulja, õpetaja*. У коротких "
            "e-основ с прошедшим на -i — *i*: *tegema → tegija*.",
            "С профессией или прибором — сложное слово: *muusikaõpetaja, "
            "tolmuimeja*.",
        ),
        sources=(ekk("SM 21"), ekk("SM 22")),
    ),
    "ma-vormid": LessonText(
        points_ru=(
            "**ma** — действие, которое последует: куда идут делать. *Läksime "
            "sööma*, *Mari hakkas laulma*.",
            "**mas** — действие в процессе, «где заняты»: *Olime marju korjamas*. "
            "С *olema* — длящееся изменение: *Kuritegevus on vähenemas*.",
            "**mast** — действие, которое было раньше, «откуда»: *Tulime söömast*. "
            "После *keelduma* и *lakkama*: *Mari keeldus söömast*, *Mari lakkas "
            "söömast*.",
            "**mata** — несделанное: *Jätsin toa koristamata*, *Tuba on "
            "koristamata*; отрицательная пара к des-vorm: *nõustus pikemalt "
            "mõtlemata*.",
            "**maks** — цель, как *selleks et*: *läks varakult kohale leidmaks "
            "endale paremat istekohta*. Звучит книжно.",
            "**des-vorm** — одновременное действие, которое описывает главное, "
            "как русское деепричастие: *Lauldes ja hõisates tormasid poisid majast "
            "välja*. Окончание как у da-инфинитива: *elada → elades*, *hüpata → "
            "hüpates*, *käia → käies*.",
        ),
        sources=(ekk("M 76"), ekk("M 80")),
    ),
    "kuupaevad": LessonText(
        points_ru=(
            "Дата — **порядковое** числительное и месяц, оба в **alalütlev**: "
            "*2. märtsil*, *5. ja 6. mail*.",
            "Порядковое числительное цифрами пишется **с точкой**: *30. kuupäev*.",
            "В составном числительном склоняется только последнее слово: "
            "*kahekümne esimene → kahekümne esimesel*.",
            "Срок — **saav**, и числительное согласуется: *30. kuupäevaks*.",
            "Промежуток дат: *5.–26. mail*, *5. kuni 26. maini*.",
            "Год: *2018. aastal*.",
        ),
        sources=(Source("EKI teatmik: arvukirjutus",
                        "https://teatmik.eki.ee/teatmik/arvukirjutus/"),
                 ekk("M 59"), ekk("M 61")),
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


#: EKI's learner grammar tables, published with its basic dictionary (PSV).
PSV = Source("EKI: eesti keele grammatika tabelid (PSV)",
             "https://arhiiv.eki.ee/dict/psv/grammatikatabelid.pdf")

LESSONS.update({
    "pohivormid": LessonText(
        points_ru=(
            "Словарь даёт **основные формы** (põhivormid). У существительного — "
            "nimetav, omastav и osastav ед. ч., короткий sisseütlev и omastav, "
            "osastav мн. ч.: *naaber, naabri, naabrit*.",
            "От **omastav ед. ч.** строятся все падежи от sisseütlev до kaasaütlev "
            "и nimetav мн. ч.: *naabri → naabrisse, naabris … naabriga, naabrid*.",
            "От **omastav мн. ч.** — все падежи мн. ч.: *naabrite → naabrites, "
            "naabritele*.",
            "Osastav не выводится по правилу — его запоминают: *naabrit*, *tuba*, "
            "*õnnelikku*.",
        ),
        sources=(ekk("M 20"), PSV),
    ),
    "gen-stem": LessonText(
        points_ru=(
            "**Omastav** (родительный) отвечает на *kelle? mille?*: *maja aknad*, "
            "*metsa taga*.",
            "Его основа часто не совпадает с начальной формой: *tuba → toa*, "
            "*sõber → sõbra*, *pood → poe*.",
            "От этой основы строятся почти все падежи: *toa → toas, toast, toale, "
            "toaga*. Поэтому слово учат сразу с omastav.",
            "Omastav нужен и для полного дополнения: *Viskasime prahi lõkkesse*.",
        ),
        sources=(ekk("M 52"), PSV),
    ),
    "osastav": LessonText(
        points_ru=(
            "**Osastav** (частичный) отвечает на *keda? mida?*. Окончание ед. ч. — "
            "*t, d, tt* или никакого: *naabrit, tuba, õnnelikku*.",
            "Нужен при **отрицании**: *Ma ei ostnud piletit*.",
            "Для **части** или неопределённого количества: *Klaasis on vett*.",
            "При **незавершённом** действии: *Ta luges raamatut terve õhtu*.",
            "После числительного больше одного: *kaks raamatut*.",
        ),
        sources=(ekk("M 53"), ekk("SÜ 37"), PSV),
    ),
    "astmevaheldus": LessonText(
        points_ru=(
            "В разных формах основа бывает в **сильной** или **слабой** ступени: "
            "*tõbi → tõve*, *haarama → haarata*, *tuba → toa*.",
            "Иногда разница только в долготе (välde) и на письме не видна: "
            "*palli* (omastav, II välde) — *palli* (osastav, III välde).",
            "Сильная ступень обычно в III välde, слабая — во II.",
            "Правило не выводится из буквы: слова чередуются по типам, поэтому "
            "основные формы берут из словаря.",
        ),
        sources=(ekk("M 22"), PSV),
    ),
    "mitmus": LessonText(
        points_ru=(
            "**Nimetav мн. ч.** = omastav ед. ч. + **d**: *naabri → naabrid*, "
            "*toa → toad*.",
            "**Omastav мн. ч.** оканчивается на **te, de** или **e**: *naabrite, "
            "tubade, õnnelike*. От него — все остальные падежи мн. ч.: *tubade → "
            "tubades, tubadele*.",
            "**Osastav мн. ч.** — *id* или *sid* (*naabreid*, *tubasid*) или короткая "
            "форма (*tube*).",
            "Короткая форма: последний звук osastav ед. ч. меняется: *u → e* "
            "(*toitu → toite*), *i → e* (*kivi → kive*), *e → i* (*lehte → "
            "lehti*), *a → u*, *i* или *e* по гласной первого слога (*sõna → sõnu*, "
            "*koera → koeri*, *tuba → tube*).",
        ),
        sources=(ekk("M 68"), PSV),
    ),
    "eitus": LessonText(
        points_ru=(
            "Отрицание настоящего: **ei** + форма без личного окончания, одна для "
            "всех лиц: *ma ei tule, nad ei tule*.",
            "Прошедшее: **ei** + форма на *-nud*: *ei tulnud*.",
            "Запрет: *ära tule!*, *ärge tulge!* (см. *käskiv kõneviis*).",
            "Дополнение при отрицании — **osastav**: *Ma ei ostnud piletit*.",
        ),
        sources=(ekk("SÜ 31"), PSV),
    ),
    "olevik": LessonText(
        points_ru=(
            "Окончания: *ma -n, sa -d, ta -b, me -me, te -te, nad -vad* — *luban, "
            "lubad, lubab, lubame, lubate, lubavad*.",
            "Все формы строятся от 3-го лица ед. ч.: *loeb → loen, loed, loeme*.",
            "Отрицание — *ei* + основа: *ei loe*.",
            "Настоящее время говорит и о будущем: *Jaan ehitab endale suvila*.",
        ),
        sources=(ekk("M 86"), PSV),
    ),
    "verb-form": LessonText(
        points_ru=(
            "Словарь даёт **четыре** основные формы глагола: *elama, elada, elab, "
            "elatud*.",
            "От **ma**-инфинитива — простое прошедшее, косвенное наклонение, "
            "причастие на -v и формы *mas, mast, maks, mata*.",
            "От **da**-инфинитива — причастие на -nud, повелительное (кроме *sina*) "
            "и des-форма.",
            "От **3-го лица** (*elab*) — остальные формы настоящего, условное "
            "наклонение и повелительное для *sina*.",
            "От формы на **-tud** — все безличные формы.",
        ),
        sources=(ekk("M 20"), PSV),
    ),
    "lihtminevik": LessonText(
        points_ru=(
            "Простое прошедшее строится от ma-инфинитива: *ma → sin* или *in*: "
            "*lugema → lugesin*, *tulema → tulin*.",
            "Формы: *lugesin, lugesid, luges, lugesime, lugesite, lugesid*.",
            "Иногда основа меняется: *tulema → tulin*, *sööma → sõin*.",
            "Отрицание: *ei* + форма на -nud: *ei lugenud*.",
        ),
        sources=(ekk("M 87"), PSV),
    ),
    "ma-da-inf": LessonText(
        points_ru=(
            "**ma**-инфинитив — действие, которое последует: после *hakkama, "
            "minema, õppima*: *Ma hakkan õppima*, *Läksime sööma*.",
            "**da**-инфинитив — действие вообще: после *tahtma, oskama, võima, "
            "meeldima, vaja*: *tahab magada*, *Mulle meeldib ujuda*.",
            "Окончание da-инфинитива: *da, ta* или *a*: *elada, hakata, käia*.",
            "Какой инфинитив нужен, решает глагол, а не смысл, — это управление "
            "(см. *rektsioon*).",
        ),
        sources=(ekk("M 74"), ekk("M 76"), PSV),
    ),
    "kohakaanded": LessonText(
        points_ru=(
            "Шесть местных падежей — две тройки *куда? где? откуда?*.",
            "**Внутренние**: *sisse* (-sse), *sees* (-s), *seest* (-st): *majasse, "
            "majas, majast*.",
            "**Внешние**: *peale* (-le), *peal* (-l), *pealt* (-lt): *lauale, laual, "
            "laualt*.",
            "Короткий sisseütlev есть у многих слов: *tuppa*, *kinno*, *kooli*.",
            "Внешние падежи ещё и про людей и время: *sõbrale*, *neljapäeval*, а "
            "*Mul on* — «у меня есть».",
        ),
        sources=(ekk("M 54"), PSV),
    ),
    "obj-case": LessonText(
        points_ru=(
            "**Täissihitis** (полное дополнение) обозначает целый объект и "
            "действие, которое достигло или достигнет результата: *Virve "
            "õmbles endale uue seeliku*. Завершённость может относиться и к "
            "будущему: *Õmble endale uus seelik!*.",
            "**Osasihitis** (частичное дополнение) — osastav (частичный падеж): "
            "часть, неопределённое количество или действие без указанного "
            "результата: *Virve õmbles endale uut seelikut*.",
            "Для одного целого объекта обычная форма täissihitis — omastav "
            "(родительный падеж): *Isa viis lapse lasteaeda*.",
            "Во множественном числе, при приказе и в безличном предложении "
            "täissihitis стоит в nimetav (именительный падеж): *Isa viis "
            "lapsed lasteaeda*; *Vii laps lasteaeda!*; *Laps viiakse lasteaeda*.",
            "Дополнение при da-инфинитиве тоже стоит в nimetav: *Isa "
            "ülesandeks jäi laps lasteaeda viia*; *Mul on vaja leib ära osta*. "
            "Исключение — когда сам инфинитив служит дополнением глагола: "
            "*pere otsustas kutsika võtta*, *Ma tahan leiva ära osta* (omastav).",
            "При обычном отрицании — osastav: *Ma ei ostnud leiba*. Даже "
            "указание результата не отменяет отрицания. Противопоставление "
            "*mitte … vaid* сохраняет полное дополнение: *Ta ei ostnud mitte "
            "maasturi, vaid paadi*.",
            "Некоторые глаголы допускают только osasihitis, независимо от "
            "того, целый ли объект: *Leena armastab lapsi*.",
        ),
        sources=(ekk("SÜ 38"), ekk("SÜ 40"),
                 Source("EKI teatmik: täissihitise kääne",
                        "https://teatmik.eki.ee/teatmik/taissihitise-kaane/")),
    ),
    "osaalus": LessonText(
        points_ru=(
            "Подлежащее (**alus**) в предложении о наличии чего-то где-то "
            "обычно стоит после места и глагола: *Laual on raamat*.",
            "При отрицании подлежащее всегда в **osastav** (частичный падеж): "
            "*Laual pole raamatut*, *Poes ei ole leiba*. Это частичное "
            "подлежащее, **osaalus**.",
            "Вещество или неопределённое количество может стоять в osastav и "
            "в утвердительном предложении: *Klaasis on vett*, *Poes on leiba*. "
            "Здесь возможны оба падежа: *Vaadis on bensiin/bensiini*.",
            "Частичное подлежащее не согласуется с глаголом: глагол остаётся в "
            "3-м лице ед. ч. — *Tänavanurgal seisis inimesi*. Полное "
            "подлежащее согласуется: *Külas elavad ukrainlased*, но *Külas elab "
            "ukrainlasi*.",
        ),
        sources=(ekk("SÜ 35"),),
    ),
    "arvsonad": LessonText(
        points_ru=(
            "После числительного больше одного существительное — **osastav ед. "
            "ч.**: *kaks raamatut*, *viis last*.",
            "После *üks* — nimetav: *üks raamat*.",
            "Числительное склоняется: *kahe, kolme, nelja*; в падежах 11–19: "
            "*ühe-teist-kümne*.",
        ),
        sources=(ekk("O 52"),),
    ),
    "kaskiv": LessonText(
        points_ru=(
            "*sina*: основа без окончания — *luba! tule! laula!*",
            "*tema, nemad*: **-gu / -ku** — *tulgu*, *hakaku*.",
            "*meie*: **-gem / -kem** — *tulgem*. *teie*: **-ge / -ke** — *tulge!*",
            "Запрет: *ära tule!*, *ärge tulge!*, *ärgu tulgu*, *ärgem tulgem*.",
            "g или k выбирается по da-инфинитиву: *lugeda → lugege*, *hakata → "
            "hakake*.",
        ),
        sources=(ekk("M 94"), PSV),
    ),
    "tingiv": LessonText(
        points_ru=(
            "Показатель **-ks-**: *ma teeksin, sa teeksid, ta teeks*. Строится от "
            "3-го лица: *loeb → loeksin*.",
            "Личное окончание можно опустить, если ясно, кто: *mina teeks*.",
            "Прошедшее: **oleks(in) + -nud** — *oleksin teinud* «я бы сделал».",
            "Отрицание: *ei teeks*, *ei oleks teinud*.",
            "Вежливая просьба и желание: *Kas te ulataksite mulle selle raamatu?*, "
            "*Tahaksin jäädagi nooreks!*",
        ),
        sources=(ekk("M 93"), PSV),
    ),
    "kesksonad": LessonText(
        points_ru=(
            "Четыре причастия: *lubav, lubatav, lubanud, lubatud*.",
            "На -v и -tav склоняются как прилагательные: *töötav masin*, *söödav "
            "taim*.",
            "На -nud — в сложных временах (*olen puhanud*) и как прилагательное "
            "(*puhanud lapsed*).",
            "На -tud — в безличных формах (*on müüdud*) и как прилагательное "
            "(*müüdud auto*).",
        ),
        sources=(ekk("M 77"), PSV),
    ),
    "taisminevik": LessonText(
        points_ru=(
            "**olema** в настоящем + **-nud**: *olen lubanud, oled lubanud, on "
            "lubanud…*",
            "Результат важен сейчас: *Näostki on näha, et oled kõvasti tööd "
            "teinud*.",
            "Отрицание: *ei ole lubanud*.",
            "Безлично: *on lubatud*.",
        ),
        sources=(ekk("M 88"), PSV),
    ),
    "enneminevik": LessonText(
        points_ru=(
            "**olema** в прошедшем + **-nud**: *olin lubanud, oli lubanud…*",
            "Действие закончилось к какому-то моменту в прошлом.",
            "Отрицание: *ei olnud lubanud*. Безлично: *oli lubatud*.",
        ),
        sources=(ekk("M 89"), PSV),
    ),
    "vordlusastmed": LessonText(
        points_ru=(
            "Сравнительная (**keskvõrre**): основа omastav + **m**: *ilusa → ilusam*, "
            "*suure → suurem*; иногда *a, u → e*: *vana → vanem*.",
            "Превосходная длинная: **kõige** + сравнительная: *kõige ilusam*.",
            "Короткая превосходная — **-im / -em**: *ilusaim, vanim, õnnelikem*; "
            "есть не у всех слов.",
            "Неправильные: *hea → parem, parim*; *pisike → pisem, pisim*.",
        ),
        sources=(ekk("M 100"), PSV),
    ),
    "jargarvud": LessonText(
        points_ru=(
            "Порядковые числительные: *esimene, teine, kolmas, neljas … kümnes*.",
            "Цифрами — **с точкой**: *3. koht*, *21. sajand*.",
            "Склоняются через основу omastav: *kolmas → kolmanda → kolmandal*.",
            "Дата — порядковое в alalütlev: *teisel märtsil* (см. *kuupäevad*).",
        ),
        sources=(ekk("O 52"),),
    ),
    "harvad-kaanded": LessonText(
        points_ru=(
            "**saav** (-ks) — во что превращается, срок: *muutus kurvaks*, *homseks*.",
            "**rajav** (-ni) — до какой границы: *metsani*, *õhtuni*.",
            "**olev** (-na) — в какой роли: *töötab õpetajana*.",
            "**ilmaütlev** (-ta) — без чего: *rahata*, *ilma emata*.",
            "**kaasaütlev** (-ga) — с кем, чем: *sõbraga*, *bussiga*.",
            "В последних четырёх определение остаётся в omastav: *suure majani*, "
            "*tubli õpilasega*.",
        ),
        sources=(ekk("M 61"), ekk("M 62"), ekk("M 63"), ekk("M 64"), ekk("M 65"),
                 PSV),
    ),
    "uhildumine": LessonText(
        points_ru=(
            "Прилагательное стоит в том же падеже и числе, что и существительное: "
            "*tublis õpilases*, *puhaste kätega*.",
            "**Кроме** rajav, olev, ilmaütlev и kaasaütlev: там прилагательное — в "
            "omastav: *tubli õpilasega*, *puhaste kätega*.",
            "Сказуемое согласуется с подлежащим в лице и числе: *mina loen, nemad "
            "loevad*.",
        ),
        sources=(ekk("SÜ 99"), PSV),
    ),
    "kaudne": LessonText(
        points_ru=(
            "**Kaudne kõneviis** — пересказ: говорящий передаёт чужие слова, не "
            "ручаясь за них: *Jüri olevat endale uue maja ostnud*.",
            "Настоящее — **-vat** от ma-инфинитива, одно для всех лиц: *lugema → "
            "lugevat*, *tulema → tulevat*.",
            "Прошедшее — **olevat + -nud**: *olevat tulnud*.",
            "Отрицание — *ei tulevat*, *ei olevat tulnud*.",
            "В разговоре пересказ передают и da-инфинитивом: *Mari olla väga "
            "jutukas*.",
        ),
        sources=(ekk("M 95"), ekk("M 74"), PSV),
    ),
    "umbisikuline": LessonText(
        points_ru=(
            "Безличная форма: действие есть, деятель не назван: *Siin räägitakse "
            "eesti keelt*.",
            "Строится от формы на -tud: *loetud → loetakse, loeti, ei loeta*.",
            "Окончание настоящего — *takse, dakse* или *akse*: *loetakse, lauldakse, "
            "tullakse*.",
            "Прошедшее: *loeti*; сложные: *on loetud, oli loetud*.",
        ),
        sources=(ekk("M 84"), PSV),
    ),
    "rektsioon": LessonText(
        points_ru=(
            "Глагол требует своего падежа или инфинитива — это **управление** "
            "(rektsioon).",
            "Эстонское управление часто не совпадает с русским: *kohanema millega?* "
            "(kaasaütlev), а не «к чему».",
            "EKK перечисляет управления, в которых чаще всего ошибаются; на них "
            "построены задания. Где EKI сегодня признаёт оба варианта (*põhinema "
            "millel ~ millele*), задания их не проверяют.",
            "Управление указано в словаре: в карточке слова (*kuhu? mida tegema?*).",
        ),
        sources=(ekk("SÜ 65"),),
    ),
    "sonajark": LessonText(
        points_ru=(
            "Спрягаемый глагол в утвердительном предложении обычно стоит **вторым**: "
            "*Ma sõidan täna maale*.",
            "Если первым стоит не подлежащее, подлежащее идёт после глагола: *Täna "
            "sõidan ma maale*.",
            "В начале — тема, в конце — самое важное и новое.",
            "В именной группе (**nimisõnafraas**) определение в omastav и "
            "согласованное прилагательное стоят перед главным словом: *kolme "
            "lapse isa*, *minu tulevane töö*. Указательное слово и число — "
            "дальше от главного слова, прилагательное — ближе: *need kaks "
            "väikest poissi*.",
        ),
        sources=(ekk("SÜ 91"), ekk("SÜ 92"), ekk("SÜ 98"), ekk("SÜ 104")),
    ),
    "kirjavahemargid": LessonText(
        points_ru=(
            "Запятая ставится по грамматике: каждое придаточное отделяется, в том "
            "числе перед *et, kui, sest, mis, kes*.",
            "Перед *ja, ning, ega, või* при однородных членах запятой нет: *linn "
            "ja maa*.",
            "Перед *aga, kuid, vaid* — запятая: *See on hea raamat, aga too teine "
            "on huvitavam*.",
            "Обращение выделяется запятыми.",
        ),
        sources=(ekk("O 57"),),
    ),
})


# ---------------------------------------------------------------------------
# Rule walks (ADR-0009 step 2): notice, ask, explain, contrast, and the form
# switch, resolved by `eesti/rulewalk.py`.
#
# A walk names no form. Its sentences are the generators' own frames
# (`drills.TEMPLATES`, `existential.FRAMES`) with a noun, or a sentence quoted
# in the topic's points above with the word it is about; Vabamorf supplies
# every form and code names it. The explanation is the one piece of prose here
# written by a model (Claude Opus 5.5, in session S3 on 10 October 2026): the
# page labels it, and `rulewalk` refuses it if it names an Estonian word that is
# neither code's nor the cited source's.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Sentence:
    """A generator frame (`____` for the gap) filled with `noun`, or a `quote`
    from the topic's sourced points with the word in it the walk is about."""

    frame: str = ""
    noun: str = ""
    rule: str = ""
    quote: str = ""
    form: str = ""
    tag: str = ""


@dataclass(frozen=True)
class Condition:
    """One segment of the form switch, or one wrong/right pair: a condition
    named in Estonian with its Russian gloss, and the sentence it governs."""

    id: str
    et: str
    ru: str
    sentence: Sentence


@dataclass(frozen=True)
class Explanation:
    """The walk's explain step: at most 40 words in the explanation language,
    from one cited section. `id` stays when other languages join (S4)."""

    id: str
    section: str
    text_ru: str
    engine: str
    written: str


@dataclass(frozen=True)
class Walk:
    notice: tuple[Sentence, ...]
    #: One item per entry, each from the topic's generator with these sub-rules.
    ask: tuple[tuple[str, ...], ...]
    explain: Explanation
    contrast: tuple[Condition, ...]
    switch: tuple[Condition, ...]


OPUS = "Claude Opus 5.5"

WALKS: dict[str, Walk] = {
    "obj-case": Walk(
        notice=(
            Sentence(frame="Ma sõin ____ ära.", noun="leib", rule="completed"),
            Sentence(frame="Ma ei söönud ____.", noun="leib", rule="negation"),
            Sentence(frame="Ma ostsin ____ iga nädal.", noun="leib", rule="ongoing"),
        ),
        ask=(("completed",), ("ongoing",), ("negation",)),
        explain=Explanation(
            id="obj-case.walk.explain", section="SÜ 38", engine=OPUS,
            written="2026-10-10",
            text_ru=(
                "Действие с результатом и целый объект — **täissihitis** "
                "(полное дополнение); в единственном числе это обычно omastav "
                "(родительный падеж): *Ma sõin leiva ära*. Действие без "
                "результата или с отрицанием — **osasihitis** (частичное "
                "дополнение), osastav (частичный падеж): *Ma ei söönud leiba*."
            ),
        ),
        contrast=(
            Condition("negation", "eitus", "отрицание",
                      Sentence(frame="Ma ei söönud ____.", noun="leib", rule="negation")),
            Condition("imperative", "käskiv", "приказ",
                      Sentence(frame="Söö ____ ära!", noun="leib", rule="imperative")),
        ),
        switch=(
            Condition("completed", "lõpetatud", "завершено",
                      Sentence(frame="Ma ostsin ____ ära.", noun="leib", rule="completed")),
            Condition("ongoing", "kestev", "длится, повторяется",
                      Sentence(frame="Ma ostsin ____ iga nädal.", noun="leib", rule="ongoing")),
            Condition("negation", "eitus", "отрицание",
                      Sentence(frame="Ma ei ostnud ____.", noun="leib", rule="negation")),
            Condition("plural", "mitmus", "мн. число",
                      Sentence(frame="Ma ostsin kõik ____ ära.", noun="leib", rule="plural")),
            Condition("imperative", "käskiv", "приказ",
                      Sentence(frame="Osta ____ ära!", noun="leib", rule="imperative")),
            Condition("impersonal", "umbisikuline", "безлично",
                      Sentence(frame="Eile osteti ____ ära.", noun="leib", rule="impersonal")),
        ),
    ),
    "osaalus": Walk(
        notice=(
            Sentence(quote="Laual on raamat", form="raamat", tag="sg n"),
            Sentence(quote="Laual pole raamatut", form="raamatut", tag="sg p"),
        ),
        ask=(("eitus",), ("mitmus",), ("mitmus",)),
        explain=Explanation(
            id="osaalus.walk.explain", section="SÜ 35", engine=OPUS,
            written="2026-10-10",
            text_ru=(
                "В предложении о наличии при отрицании подлежащее (**alus**) "
                "стоит в osastav (частичный падеж): *Laual pole raamatut*. Это "
                "**osaalus** (частичное подлежащее). С ним глагол остаётся в "
                "единственном числе: *Klassis istub õpilasi*, но *Klassis "
                "istuvad õpilased*."
            ),
        ),
        contrast=(
            Condition("eitus", "eitus", "отрицание",
                      Sentence(frame="Laual ei ole ____.", noun="raamat", rule="eitus")),
            Condition("ainsus", "verb ainsuses", "глагол в ед. ч.",
                      Sentence(frame="Klassis istub ____.", noun="õpilane", rule="mitmus")),
        ),
        switch=(
            Condition("jaatus", "jaatus", "утверждение",
                      Sentence(quote="Laual on raamat", form="raamat", tag="sg n")),
            Condition("eitus", "eitus", "отрицание",
                      Sentence(frame="Laual ei ole ____.", noun="raamat", rule="eitus")),
            Condition("mitmus", "verb mitmuses", "глагол во мн. ч.",
                      Sentence(frame="Klassis istuvad ____.", noun="õpilane", rule="mitmus")),
            Condition("ainsus", "verb ainsuses", "глагол в ед. ч.",
                      Sentence(frame="Klassis istub ____.", noun="õpilane", rule="mitmus")),
        ),
    ),
}


@dataclass(frozen=True)
class Tip:
    """The Reegel page's first card: the rule in one line, then the mistake a
    Russian speaker typically makes with it, wrong form first."""

    gist_ru: str
    wrong: str
    right: str


TIPS: dict[str, Tip] = {
    "tahestik": Tip("27 букв; *õ, ä, ö, ü* — отдельные звуки, долгота меняет смысл.",
                    "palli = palli", "selle palli (II) ≠ seda palli (III)"),
    "fraasid": Tip("Здороваются — *Tere!*, прощаются — *Head aega!* или *Nägemist!*",
                   "Tere! (прощаясь)", "Head aega! (прощаясь)"),
    "arvud": Tip("*-teist* — 11–19, *-kümmend* — десятки; составное — раздельно.",
                 "13 = kolmkümmend", "13 = kolmteist"),
    "lauseehitus": Tip("Глагол — вторым, и он согласуется с подлежащим.",
                       "Ma täna sõidan maale.", "Ma sõidan täna maale."),
    "asesonad": Tip("У местоимений две формы: длинная — с ударением, короткая — без.",
                    "Anna see mina.", "Anna see mulle."),
    "kusisonad": Tip("*kus?* — где, *kuhu?* — куда, *kust?* — откуда.",
                     "Kus sa lähed?", "Kuhu sa lähed?"),
    "pohivormid": Tip("Учи слово тремя формами: *raamat, raamatu, raamatut*.",
                      "tuba → tubat (osastav)", "tuba → tuba (osastav)"),
    "gen-stem": Tip("Почти все падежи — от основы omastav.",
                    "tubas", "toas"),
    "osastav": Tip("Отрицание, часть, процесс — osastav.",
                   "Ma ei ostnud pilet.", "Ma ei ostnud piletit."),
    "astmevaheldus": Tip("Основа меняется: сильная ↔ слабая ступень.",
                         "pood → poodi (omastav)", "pood → poe (omastav)"),
    "mitmus": Tip("Мн. ч. = omastav ед. ч. + d.",
                  "tubad", "toad"),
    "eitus": Tip("*ei* + основа, одна для всех лиц.",
                 "Ma ei tulen.", "Ma ei tule."),
    "olevik": Tip("*-n, -d, -b, -me, -te, -vad* — и это же будущее.",
                  "Ma lähe homme.", "Ma lähen homme."),
    "verb-form": Tip("Учи глагол четырьмя формами: *elama, elada, elab, elatud*.",
                     "minema → minen", "minema → lähen"),
    "lihtminevik": Tip("Прошедшее: *-sin* или *-in*.",
                       "Ma tulesin.", "Ma tulin."),
    "ma-da-inf": Tip("Куда/что начать — *ma*; хотеть, уметь, нравиться — *da*.",
                     "Ma tahan magama.", "Ma tahan magada."),
    "kohakaanded": Tip("Куда — *-sse / -le*, где — *-s / -l*, откуда — *-st / -lt*.",
                       "Ma elan Tallinnasse.", "Ma elan Tallinnas."),
    "obj-case": Tip("Täissihitis (полное дополнение) — omastav или nimetav; "
                    "при приказе — nimetav (именительный падеж).",
                    "Vii lapse lasteaeda!", "Vii laps lasteaeda!"),
    "osaalus": Tip("Чего нет — в osastav; частичное подлежащее не меняет глагол.",
                   "Poes ei ole leib.", "Poes ei ole leiba."),
    "arvsonad": Tip("После числа больше одного — osastav ед. ч.",
                    "kaks raamatud", "kaks raamatut"),
    "kellaaeg": Tip("Половина, четверть — к **следующему** часу, как «половина десятого».",
                    "9.30 = pool üheksa", "9.30 = pool kümme"),
    "kaassonad": Tip("Почти всё — послелоги после omastav.",
                     "all laud", "laua all"),
    "sidesonad": Tip("Союз не меняет формы слов; придаточное — через запятую.",
                     "Ma tean et ta tuleb.", "Ma tean, et ta tuleb."),
    "maarsonad": Tip("Наречия не склоняются, но места идут тройками: *alla, all, alt*.",
                     "Kass on alla.", "Kass on all."),
    "mul-on": Tip("Есть — *Mul on*, нравится — *Mulle meeldib*, нет — osastav.",
                  "Ma meeldib see film.", "Mulle meeldib see film."),
    "kaima-minema": Tip("*käima* — где был (и вернулся), *minema* — куда идёшь.",
                        "Eile ma läksin kinos.", "Eile ma käisin kinos."),
    "kaskiv": Tip("*sina* — основа (*tule!*), *teie* — *-ge* (*tulge!*), запрет — *ära*.",
                  "Ära tulge!", "Ärge tulge!"),
    "tingiv": Tip("«бы» — *-ks-*: *teeksin*; прошедшее — *oleksin teinud*.",
                  "Kui mul oleks aega, ma tulen.", "Kui mul oleks aega, ma tuleksin."),
    "kesksonad": Tip("*-v* — делающий, *-nud* — сделавший, *-tud* — сделанный.",
                     "müünud auto (проданная)", "müüdud auto"),
    "taisminevik": Tip("*olen* + *-nud*: результат виден сейчас.",
                       "Ma olen tegin.", "Ma olen teinud."),
    "vordlusastmed": Tip("omastav + *m*; «самый» — *kõige*.",
                         "kõige suur", "kõige suurem"),
    "jargarvud": Tip("Порядковое цифрой — с точкой: *3. koht*.",
                     "3 koht", "3. koht"),
    "harvad-kaanded": Tip("*-ks* во что, *-ni* до, *-na* как, *-ta* без, *-ga* с.",
                          "Ta tuli ilma autot.", "Ta tuli ilma autota."),
    "tulevik": Tip("Будущего времени нет: настоящее + слово времени.",
                   "Ma saan homme tulema.", "Ma tulen homme."),
    "ma-vormid": Tip("*ma* куда, *mas* где, *mast* откуда, *mata* без, *des* — деепричастие.",
                     "Ma tulin just ujuma.", "Ma tulin just ujumast."),
    "tuletus": Tip("*-mine* — действие, *-ja* — тот, кто делает.",
                   "Ta on hea laulmine.", "Ta on hea laulja."),
    "kuupaevad": Tip("Дата: порядковое + месяц, оба на *-l*.",
                     "kaks märtsil", "teisel märtsil"),
    "uhildumine": Tip("Прилагательное в том же падеже — кроме *-ni, -na, -ta, -ga*.",
                      "suures majaga", "suure majaga"),
    "kaudne": Tip("Пересказ «говорят, что…» — *-vat*, прошлое — *olevat + -nud*.",
                  "Ta on haige. (слышал от других)", "Ta olevat haige."),
    "enneminevik": Tip("*olin* + *-nud*: раньше другого прошлого.",
                       "Ma olen lõpetanud, kui ta tuli.", "Ma olin lõpetanud, kui ta tuli."),
    "umbisikuline": Tip("Деятель не назван: *-takse*, прошедшее *-ti*.",
                        "Siin räägivad eesti keelt.", "Siin räägitakse eesti keelt."),
    "rektsioon": Tip("Падеж задаёт глагол, а не русский перевод.",
                     "kohanen kliimale", "kohanen kliimaga"),
    "sonajark": Tip("Глагол — вторым, даже если первым стоит не подлежащее.",
                    "Täna ma sõidan maale.", "Täna sõidan ma maale."),
    "kirjavahemargid": Tip("Запятая — перед каждым придаточным и перед *aga, kuid, vaid*.",
                           "Ma arvan et see on hea.", "Ma arvan, et see on hea."),
    "uhendverbid": Tip("Частица меняет смысл глагола и часто стоит в конце.",
                       "Ma läbi loen raamatu.", "Ma loen raamatu läbi."),
    "liitsonad": Tip("Пишется слитно, изменяется только последняя часть.",
                     "kallistkivist", "kalliskivist"),
}
