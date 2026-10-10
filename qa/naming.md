# Naming review: Klint's interface names

A research note for the owner, written on 11 October 2026 in the S8 worktree.
It proposes names and changes no code, test or design document. The owner's
concern: many of Klint's names read as generic Estonian made by a model, and
apps built with the same tools converge on the same words (the competitor
review, `qa/competitor-review.md`, records that an assistant once offered the
owner the competitor's own name, *Sõnarada*). The aim is to name each thing
with the word that Estonia's official materials and ordinary Estonian use, and
to gloss it with the established term in Russian, English and later Ukrainian.

All sources were read on 11 October 2026. Quotations are kept to a few words;
definitions are paraphrased. Where a source could not be reached it is listed
under **Sources not reached**, and nothing is claimed from it.

## Summary

- **96 table rows** in nine tables (a row may group closely related labels), each with
  its current Russian gloss.
- **26 rows propose a change**: 16 change the Estonian name, 10 only the gloss.
  **11 rows are left to the owner**; 59 stay as they are.
- Most of Klint's vocabulary is already the official one: the four skills, *Kordamine*,
  *Sõnastik*, *Sõnavara*, *Ülesanne*, *Etteütlus*, *Vestlus*, *Proovieksam*,
  *Kontrolltöö*, *Jätka*, *Edasi*, *Kontrolli*, *Jäta vahele*, *Proovi veel*.
- The generic or calqued names cluster in course structure and a few labels:
  *ühik*, *rada*, *Sõnatrenn*, *Võrguta*, *Töövihikud*, and three different labels
  for one explanation.

The five most important changes:

1. **ühik → peatükk** (RU *глава*, EN *chapter*), and **Ühiku kontroll → Peatüki test**.
   In Estonian *ühik* is a unit of measurement or one item among many; Keeleklikk and
   Keeletee, which Klint's units link to as companions, call the same thing
   *Глава / Chapter / Розділ*, and Estonian coursebooks say *peatükk*.
2. **Minu rada (and every *rada*) → Peatükid / Kursus.** *Rada* is the path metaphor
   of Duolingo's home screen and of the competitor's name *Sõnarada*.
3. **Session step Kontroll → Tunnikontroll.** EKI's own word for the short check at the
   end of a lesson; it stops one word (*kontroll/Kontrolli*) from naming a step, a phase,
   a button and the unit check at once.
4. **Töövihikud → Konsultatsioonivihikud** (RU *консультационные тетради*,
   EN *consultation workbooks*): HARNO's own name for these booklets in all three languages.
5. **One name for the model's explanation:** *Miks?*, *Selgita* and *Miks nii* become
   **Selgita** (button) and **Selgitus** (heading); RU *объясни / объяснение*.

## Principles

1. **A name says what the learner does or gets.** A verb for an action (*Kontrolli*,
   *Jätka*), a noun for a place or a thing (*Sõnastik*, *Kordamine*).
2. **Plain Estonian a learner meets in real courses and in Estonian life**: in
   Keeleklikk/Keeletee, HARNO's exam pages and handbooks, EKI's dictionaries and
   classroom phrasebook, and Estonian coursebooks. A word must appear in such a
   source with the meaning Klint gives it, or be an ordinary dictionary word whose
   sense Sõnaveeb records.
3. **Consistent across the app; one term per thing, one thing per term.** The same
   thing keeps its name and its gloss on every screen; two things never share a label.
4. **No invented compounds or short forms** (*Sõnatrenn*, *Võrguta*). A compound is
   used only when a source uses it.
5. **No product names of other apps** (Duolingo's *Explain My Answer*, *Practice tab*;
   Busuu's *Smart Review*; LingQ's *LingQ*; Speakly's *LIVE©*), and no metaphor that
   identifies a competitor (*rada*).
6. **The gloss is the established term in the gloss language**, not a translation of
   the Estonian: the Russian is what HARNO, Keeleklikk, Russian school terminology or
   EKI's Russian equivalents use; the English is what HARNO's and Keeleklikk's English
   pages use.
7. **Conservative where the current word is already official.** A change needs a
   source; where the evidence is even, the current word stays and the row is the
   owner's call.

## Sources

Each row of the tables cites these tags.

**Official Estonian materials**

- **[H-et] HARNO, *Eesti keele tasemeeksamid*** — <https://harno.ee/eesti-keele-tasemeeksamid>.
  The exam checks four *osaoskust*: *kirjutamine, kuulamine, lugemine ja rääkimine*;
  the parts are *Kirjutamistest*, *Kuulamistest*, *Lugemistest*, *Rääkimistest*, each
  of numbered *ülesanded*; the speaking test is a *vestlus* between examiner and
  candidates. Materials: *konsultatsioonivihik*, *sooritusnäidis*, *näidisülesanded*,
  under *Eksamiks valmistumine (materjalid)*; *Teabeleht tasemeeksami sooritajale*;
  a video *eksamikorrast*; *Toimumisajad ja toimumiskohad*. Level names:
  *Eesti keele A2-taseme eksam*, *B1-taseme eksam*. A2 topics include *igapäevaelu*.
- **[H-ru] HARNO, Russian page** — <https://harno.ee/ru/ekzameny-testy-i-issledovaniya/ekzameny-testy-i-dokumenty-ob-okonchanii/urovnevye-ekzameny-po>.
  *Уровневые экзамены по эстонскому языку*; *Экзамен по эстонскому языку на уровень B1*;
  four parts named *письменная часть, слушание, чтение и устная часть*;
  *Консультационные тетради*; *Образец задания*; information about the *форме и
  порядке проведения* and the *структуре экзамена*.
- **[H-en] HARNO, English page** — <https://harno.ee/en/examinations-tests-and-studies/examinations-tests-and-certificates/estonian-language-proficiency>.
  Four parts *writing, listening, reading, and speaking*; *Workbooks:* followed by
  *consultation workbook and listening test*; *sample tasks*; *structure of the
  examination*; *Information sheet for the Estonian language proficiency examinee*.
- **[H-B1k] HARNO, B1 consultation booklet 2021** — local `data/exam/B1/B1_konsultatsioon_2021.pdf`, p. 1:
  headings *KIRJUTAMINE*, *LUGEMINE*, *Esimene ülesanne*, *Variant A*.
- **[H-B1] *Iseseisev keelekasutaja. B1- ja B2-taseme eesti keele oskus*** (REKK 2008) —
  local `data/exam/B1/Iseseisev-keelekasutaja.pdf` (page numbers are PDF pages):
  p. 13 the four *osaoskused* by name; p. 24 a learner perceiving their own
  *edenemist*; p. 33 topics of *igapäevaelu või tööga*; p. 86 *kontrolltöö, eksam,
  hinne* as school vocabulary; p. 178 *etteütlused* among writing practice.
- **[H-A2] *Algaja keelekasutaja. A2-taseme eesti keele oskus*** (2008) — local
  `data/exam/A2/Algaja-keelekasutaja.-A2-tase.pdf`: p. 21 Mall Laur's beginner
  description *Esimene verstapost*; p. 66 *märkamine* of new words as the best way
  to learn them; p. 71 a learner who *oskab vastandada grammatilisi vorme*; p. 123
  *etteütlus* to train listening and writing together; pp. 137–179 *Lisa 2. Esmane
  sõnastik*, about 2,000 frequent words, which lists among others *täna* (157),
  *kursus* (148), *harjutus* and *harjutama* (144), *kordama*, *kontroll*,
  *kontrollima* (147), *ülesanne* (160), *teema* (156), *rada* (153), *märkama* (150),
  *jätkama* (145), *edasi*, *eesmärk* (143), *algus*, *areng* (142), *treening, trenn* (157).
  It does not list *ühik*, *sõnavara*, *eksam* or *vestlus*.
- **[CEFR-et] *Euroopa keeleõppe raamdokument*** (Estonian translation) — local
  `data/exam/B1/euroopa_keele6ppe_raamdokument.pdf`: p. 42 self-assessment grid with
  *KUULAMINE*, *LUGEMINE*; p. 164 learner texts include *etteütlused*, *harjutused*,
  *vaba vestlus*, *valjult ettelugemine*; pp. 10, 21 learners assessing their
  *edusamme* and the *edenemist* of their studies.
- **[KK] Keeleklikk (A0–A2) and Keeletee (B1)**, course maps and lesson pages fetched after
  choosing each language: <https://www.keeleklikk.ee/ru/A/coursemap/list/1>,
  `/ua/…`, `/en/…`, `/ru/B1/coursemap/list/1`, `/en/B1/…`, `/ru/A/lesson/1/1/0`.
  - Menu: RU *Курсы, Содержание, Словарь, Помощь, Вход*; UA *Курси, Зміст, Словник,
    Допомога*; EN *Courses, Contents, Dictionary, Help*; the Estonian `title`
    attributes are *avaleht, sisukord, sõnastik, abi*.
  - Structure: RU *Глава 1 … Глава 16*, a lesson page *ГЛАВА 1, УРОК 1*, *Курс
    содержит 54 урока*; UA *РОЗДІЛ 1, УРОК 1*; EN *Chapter 1*, *CHAPTER 1, LESSON 1*.
    Keeletee calls its sub-chapter *подглава* in Russian and *unit* in English.
    The Estonian login message speaks of an *õppetükk*.
  - Items: RU *Задание:*, UA *Завдання:*, EN *Exercise:*, Keeletee ET *Ülesanne:*;
    a *Тест / Test yourself / Тест* item closes each Keeleklikk chapter (the Russian course map has 16 for 16 chapters).
  - Section headings: RU *Учим грамматику, Учим выражения, Учим лексикон, Говорим
    по-эстонски, Напишите*; UA *Вчимо граматику, Вчимо лексику*; EN *Let's study
    vocabulary*; Keeletee uses Estonian headings *Grammatika, Sõnavara, Kuulamine,
    Lugemine, Rääkimine, Kirjutamine, Test*, and *TEEMA* for a topic.
  - Category filter (EN labels; RU/UA labels are empty in the HTML): *Writing, Listening,
    Reading, Speaking, Dictionary, My dictionary, Test*; its Estonian keys are
    `kirjutamine`, `kuulamine`, `lugemine`, `raakimine`, `sonavara`, `minusonad`, `test`.
- **[IS] Integration Foundation** — <https://integratsioon.ee/eesti-keele-oskuse-tasemed-ja-testimine>
  (and its `/ru/` and `/en/` versions): *tasemeeksam*; testing one's
  *valmisolekut eksamiks* (RU *готовность к сдаче экзамена*, EN *how well prepared you
  are*); *Eesti keele tasemetestid*; the quick placement test *Sõeltest*;
  *enesehindamisskaala*. <https://www.integratsioon.ee/eesti-keele-ope>: *Eesti keele
  kursused*, *Iseseisev keeleõpe*.
- **[Kitsnik] Mare Kitsnik, *Müüja erialane eesti keel. Õppematerjal*** (Integratsiooni ja
  Migratsiooni SA Meie Inimesed, 2010) —
  <https://drupal9.meis.ee/sites/default/files/206_Myyja_erialane_eesti_keel_Oppematerjal.pdf>:
  eight *peatükid*, each opening *Selles peatükis õpime*; a *test* after every two
  chapters (*Esimene test*) to assess one's *arengut*; 176 uses of *ülesanne*;
  *uued sõnad*, *sõnaloend*, *õpik-töövihik*.
- **[SV] EKI, Sõnaveeb — *EKI ühendsõnastik 2026*** entries, URL pattern
  `https://sonaveeb.ee/search/unif/dlall/dsall/<word>/1/est`. Consulted for: sõnastik,
  sõnaraamat, sõnavara, kordamine, kordus, kordamistund, harjutus, harjutamine,
  harjutama, ülesanne, tund, õppetund, õppetükk, ühik, üksus, peatükk, teema, rada,
  trenn, treening, märkama, tähele panema, vastandama, võrdlema, edenemine, areng,
  edasiminek, valmisolek, töövihik, vihik, kontrolltöö, tunnikontroll, proovieksam,
  tasemeeksam, eksam, test, kontroll, kontrollima, etteütlus, vestlus, jutuajamine,
  paus, peatama, jätkama, edasi, uuesti, vahele jätma, õige, selgitama, selgitus,
  reegel, proovima, kinnitama, oskus, osaoskus, lugemine, kuulamine, rääkimine,
  kirjutamine, kodutöö, kursus, sisukord, avaleht, profiil, konto, veel, offline,
  sessioon, eksamisessioon, ülesehitus, korraldus, kuju, verstapost, märk, rütm,
  algus, algtase, algaja, aste, tase, eesmärk, segamini, koostama, fraas, sõnakaart,
  vabaharjutus, teabeleht. No ühendsõnastik entry exists for *õppeühik*, *õppeüksus*,
  *sõnatrenn*, *võrguta*, *võrguühenduseta*, *eksamipäev*, *eksamikord*, *näidisülesanne*,
  *sooritusnäidis*.
- **[SV-UI] Sõnaveeb's own interface** in three languages (`https://sonaveeb.ee/?uilang=et|ru|en`):
  *EKI sõnastikud / Словари EKI / EKI dictionaries*; *Hääldusharjutused / Упражнения на
  произношение / Pronunciation exercises*; *Õpime eesti keelt / Изучаем эстонский язык /
  Learn Estonian*; *Piltsõnastik / Словарь в картинках / Picture Dictionary*;
  *Keelemängud / Игры / Language Games*; *Tagasiside / Обратная связь / Feedback*.
- **[EKI-F] EKI, *Õppetöö korraldamise fraasikogu*** (R. Pool, J. Kallas, M. Tiits 2022,
  updated 10 Jan 2025), <https://sonaveeb.ee/learn#v-pills-oppetoo>: the phrases a
  teacher uses in an Estonian-medium lesson. Sections used here: §1.3 *Täna me
  kordame*, *Tänane teema on…*; §2.3 *Kuidas sul tänane tund läks?*; §2.4 *Teeme
  pausi*; §3.1 *Lähme edasi*, *Teeme uuesti*; §3.4 *Mis oli reegel?*; §3.7 *Tunni
  lõpus teeme väikese tunnikontrolli*, *Meil tuleb kontrolltöö*; §4.9 *Õige vastus*;
  §4.10 heading *Tagasiside: proovi veel*, *Ei ole õige*; §5.4 *Otsi sõnastikust*;
  §6.4 *Loe ette…*, *Kas see on õige või vale?*; §6.5 *Kontrolli oma vastust*;
  §6.9 *Küsi minult*.
- **[UT] University of Tartu, *Sõnavaraharjutused kõrgtasemele*** —
  <https://keeleweb2.ut.ee/kursused/4-varia/307-18-suenonueuemid>: *Sõnavaraharjutus*,
  *Harjutus*, *Peatükid*, *Ava sisukord*, *Avaleht*, *Järgmine test*.

**Coursebooks**

- **[Argo] Heinike Heinsoo, *Eesti keel ja eesti meel*** (Argo 2022/2024, Estonian with
  Ukrainian), sample: <https://argokirjastus.ee/wp-content/uploads/2022/08/Eesti-keel-ja-eesti-meel.pdf> —
  *Sisukord / Зміст*, *Sõnastik / Словник*, *harjutused / вправи*.
- **[Routledge] *Colloquial Estonian*** (Routledge 2015), publisher's description via
  search: units, dialogues, exercises, grammar notes, vocabulary, answer key.
  <https://www.routledge.com/Colloquial-Estonian-The-Complete-Course-for-Beginners/Moseley/p/book/9781138950115>
- **[Sõnarada] the competitor**, `qa/competitor-review.md` (owner's material): top areas
  *Марафоны, Словарь, Грамматика, Заметки, Профиль*; trainer modes *Заучивание*,
  *Повторение*.

**Russian and Ukrainian school terminology**

- **[FIPI] ФИПИ, Методические рекомендации ЕГЭ 2026, английский язык** —
  <https://doc.fipi.ru/navigator-podgotovki/navigator-ege/MR_angl_yaz_ege_2026.pdf>:
  the written part has sections *Аудирование, Чтение, Грамматика и лексика, Письменная
  речь* (PDF p. 8); the oral part *Говорение* (p. 48).
- **[UA-mil] Ukrainian Ministry of Defence institute, English entrance programme 2026** —
  <https://kzmi.mil.gov.ua/images/stories/NOV/Programa%20vstupu%20angl%202026.pdf>,
  seen only as a search result: the four activities *аудіювання, говоріння, читання і письма*.

**Learning apps** (names to avoid copying; the generic English words *Review*, *Practice*,
*Vocabulary*, *Dictionary*, *Lessons*, *Progress* are shared by all of them)

- **[Duo] Duolingo blog** — <https://blog.duolingo.com/guide-to-duolingo-practice-hub/>:
  *Practice tab* with *Mistakes, Words, Speak, Listen*; *Stories*, *Radio*, *Adventures*;
  *Explain My Answer*; *Video Call*, *Roleplay*. Home screen redesign (via search):
  <https://blog.duolingo.com/new-duolingo-home-screen-design> — a *path*, *units*, a *guidebook*.
- **[Babbel]** support pages (via search; the site returned 403): *Review* or *Review
  manager*, also called a *vocab workout*; *Practice tab*; *Your vocabulary*.
- **[Busuu]** <https://help.busuu.com/hc/en-gb/articles/16941990776593> (via search):
  a *Review* tab, *Vocabulary*, words *Weak/Medium/Strong*; App Store: *Smart Review*,
  *Study Plan*.
- **[Memrise]** third-party reviews only: *Learn*, *Review*, *Speed Review*, *Difficult Words*.
- **[Anki] manual** — <https://docs.ankiweb.net/studying.html>: *Decks*, *Study Now*;
  answer buttons *Again, Hard, Good, Easy*; card states *New, Learning, To Review*.
- **[LingQ] support** (via search): *LingQs*, *Known Words*, *Learned*, *Ignore*,
  *Daily Goal*, *streak*, *Vocabulary* page.
- **[Drops]** third-party reviews only: *Travel Talk*, *Review Dojo*.
- **[Speakly]** (Estonian-made) — <https://www.speakly.me/>: *LIVE© language course*,
  *real-life situations*; App Store RU <https://apps.apple.com/ru/app/id1255478968>:
  *интервальное повторение*, *уроки*, *Ситуации из реальной жизни*. No Estonian interface
  and no help centre found.

None of Klint's current names copies one of these product names. Two of them share
the competitors' metaphors: *Minu rada* (Duolingo's path, Sõnarada) and *Sõnatrenn*
(Babbel's *vocab workout*). Klint's word statuses (*õpin, tean, eiran, teadsin ammu*)
resemble LingQ's (*Learned, Known, Ignore*); see the open questions.

### Sources not reached

- `keeleklikk.ee/info_en.html` (course description): HTTP 403.
- Babbel support (`support.babbel.com`): HTTP 403; terms taken from search results only.
- ECML self-assessment pages in Russian, Ukrainian and Estonian (`edl.ecml.at`): a
  Cloudflare check blocked them, so no Council of Europe Russian/Ukrainian skill names.
- TestEst (`web.meis.ee/testest`): redirects into an ILIAS login frameset; not read.
- Russian-medium coursebooks of Estonian (e.g. *Краткий учебник эстонского языка для
  русских*, DIGAR): access restricted; tables of contents for *E nagu Eesti* and
  *Tere taas* not found. No textbook's Russian rubric names are claimed.
- Duolingo's Russian help centre and Russian blog: not found (blog `/ru/` 404).
- Speakly's in-app labels, Memrise, LingQ and Drops official help: only third-party
  pages or search results.
- The official Russian translation of the CEFR self-assessment grid: not found online.

## How to read the tables

*Mark*: **keep** (name and gloss stay), **change** (Estonian, gloss or both change;
the row says which), **owner** (evidence is even or the choice is a product decision).
*UK*: the Ukrainian gloss where a source gives one, else *S4*.

## 1. Navigation

| Current ET | Current RU | Proposed ET | Proposed RU | Proposed EN | UK | Mark | Reason and source |
|---|---|---|---|---|---|---|---|
| Täna | сегодня | Täna | сегодня | Today | сьогодні [SV *tänane*] | keep | An A2 core word [H-A2 p. 157]; teachers open a lesson by saying what *täna* holds [EKI-F §1.3]. Keeleklikk and Sõnaveeb name a start page *avaleht* [KK, SV], which would describe a home page, not today's plan. |
| Kursus | темы курса | Kursus | курс | Course | курс [SV] | change (gloss) | [SV] *kursus*: material set as a series of lessons, RU *курс*; Keeleklikk's menu says *Курсы / Courses / Курси* [KK]. "темы курса" describes contents; one gloss everywhere (DESIGN.md already writes *курс*). |
| Kordamine | повторение | Kordamine | повторение | Review | повторення [SV] | keep | [SV] *kordamine* RU *повторение*; *Täna me kordame* [EKI-F §1.3]; *kordamistund* [SV]. EN *Review* is generic (Anki, Babbel, Busuu all use it) and not a product name. |
| Eksam | подготовка / подготовка A2/B1 | Eksam | экзамен | Exam | іспит [SV] | change (gloss) | HARNO RU *Экзамен … на уровень B1* [H-ru]; [SV] *eksam* RU *экзамен*. "Preparation" is HARNO's *Eksamiks valmistumine* [H-et], a different name. |
| Oskused | навыки | Oskused | навыки | Skills | S4 [SV *oskus*: уміння, навичка] | keep | HARNO's four *osaoskused* [H-et, H-B1 p. 13]; [SV] *osaoskus* (e.g. reading, listening…), *oskus* RU *навык*. |
| Veel | разделы | Veel | ещё | More | S4 | owner | [SV] *veel*: in addition, besides. The gloss "разделы" describes the sheet; "ещё" says the word. No platform localisation source was reached. |
| Profiil | профиль | Profiil | профиль | Profile | профіль [SV] | keep | [SV] *profiil*, sense of the information a person publishes about themselves; RU *профиль*. |
| Sõnavara | слова; слова и тренировка; словарь по частотности | Sõnavara | лексика (or слова) | Vocabulary | лексика [KK UA, SV] | change (gloss) | Keeletee's own heading *Sõnavara* and Keeleklikk's key `sonavara` [KK]; [SV] RU *лексика, запас слов*; FIPI *Грамматика и лексика* [FIPI]; Keeleklikk UA *Вчимо лексику*. Three glosses today; "словарь" on the progress card means dictionary in Russian and is wrong there. Owner may prefer the plainer *слова*; either way one gloss. |
| Sõnastik | словарь | Sõnastik | словарь | Dictionary | словник [KK UA, SV, Argo] | keep | Keeleklikk *sõnastik / Словарь / Dictionary / Словник* [KK]; EKI *EKI sõnastikud / Словари EKI* [SV-UI]; [SV] reference work about words, synonym *sõnaraamat*; *Otsi sõnastikust* [EKI-F §5.4]. |
| Töövihikud | официальные материалы; тетради | Konsultatsioonivihikud | консультационные тетради | Consultation workbooks | S4 | change (owner on length) | The page holds HARNO's booklets, which HARNO names *konsultatsioonivihik* [H-et], *консультационная тетрадь* [H-ru], *consultation workbook* [H-en]. [SV] *töövihik* is the workbook that belongs to a coursebook set, a different thing. If the length hurts the Veel sheet: *Vihikud / тетради* ([SV] *vihik* RU *тетрадь*). |
| Edenemine | прогресс; занятия и прогресс; посмотреть прогресс | Edenemine | прогресс | Progress | S4 [SV *areng*: розвиток] | keep (gloss unified) | HARNO's B1 handbook uses *edenemine* for a learner's own progress [H-B1 p. 24]; CEFR *keeleõpingute edenemist* [CEFR-et p. 21]; [SV] *edenemine* = moving forward, development. *Areng* is the commoner coursebook word [Kitsnik] if the owner wants it. One gloss. |

## 2. The four skills

HARNO's names are the app's names; nothing changes in Estonian or English.
The Russian stays the school terminology; HARNO's own Russian page differs and is
noted so the owner can choose knowingly.

| Current ET | Current RU | Proposed ET | Proposed RU | Proposed EN | UK | Mark | Reason and source |
|---|---|---|---|---|---|---|---|
| Lugemine | чтение | Lugemine | чтение | Reading | читання [SV] | keep | [H-et], [H-B1 p. 13], [H-en] *reading*; Keeletee heading and Keeleklikk key [KK]; FIPI *Чтение* [FIPI]; [SV] RU *чтение*. |
| Kuulamine | аудирование | Kuulamine | аудирование | Listening | аудіювання [UA-mil] | keep | [H-et]; [H-en] *listening*; [KK]; FIPI *Аудирование* [FIPI]. HARNO's Russian page says *слушание* [H-ru], as does [SV]; *аудирование* is the established teaching term. |
| Rääkimine | говорение | Rääkimine | говорение | Speaking | говоріння [SV, UA-mil] | keep | [H-et]; [H-en] *speaking*; [KK]; FIPI *Говорение*. HARNO RU calls the exam part *устная часть* [H-ru]. |
| Kirjutamine | письмо | Kirjutamine | письмо | Writing | письмо [UA-mil] | keep | [H-et], [H-B1k] heading *KIRJUTAMINE*; [H-en] *writing*; [KK]; FIPI *Письменная речь*; HARNO RU *письменная часть* [H-ru]. |

## 3. Kursus: its modes and the *rada* family

| Current ET | Current RU | Proposed ET | Proposed RU | Proposed EN | UK | Mark | Reason and source |
|---|---|---|---|---|---|---|---|
| Minu rada | по порядку | Peatükid | по главам | Chapters | розділи [KK UA] | change | The tab lists the course's chapters in order. Keeleklikk/Keeletee *Глава / Chapter / Розділ* [KK]; *Peatükid* [UT]; *peatükk* [Kitsnik]. [SV] *rada* is a narrow trodden path: the metaphor of Duolingo's home *path* [Duo] and of the competitor's name *Sõnarada* [Sõnarada]. |
| Mine Radale; Kogu rada; Rada (progress card); Raja tase (profile) | к упражнениям; путь; уровень пути | Kursus / Peatükid; Kõik peatükid; Kursus; Kursuse algus | к курсу; все главы; курс; начало курса | Course; All chapters; Course; Course start | S4 | change | Same reason; every *rada* goes, so the word for the course is one: *Kursus*, its parts *peatükid*. |
| Vaba harjutus | без записи | Vaba harjutus | без записи | Free practice | S4 | owner | Ordinary words ([SV] *harjutus*, [H-A2] *vaba*), and the gloss says what it does. But [SV] records one-word *vabaharjutus* as a gymnastics floor exercise, which a reader may hear. Alternative with ordinary words: *Harjuta vabalt*. |
| Võrguta | набор без интернета | Võrguühenduseta | офлайн | Offline | S4 | change | *võrguta* has no Sõnaveeb entry; [SV] defines *offline* as an autonomous mode *võrguühenduseta*, RU *офлайн*. The disclosure's content (a five-item pack) can stay in the gloss. |

## 4. The session: phases, steps and plan

| Current ET | Current RU | Proposed ET | Proposed RU | Proposed EN | UK | Mark | Reason and source |
|---|---|---|---|---|---|---|---|
| Õpi (phase; Kursus row action) | разбери; изучить | Õpi | изучи | Learn | S4 | change (gloss) | *õppima* is an A2 core word [H-A2 p. 160]; Keeleklikk RU *Учим…* [KK]. Two glosses for one word today; "разбери" is a different verb. |
| Harjuta (phase; rule page primary) | попробуй; упражняться | Harjuta | упражняйся | Practise | S4 | change (gloss) | [SV] *harjutama* RU *упражняться, тренироваться*. "попробуй" is *Proovi* ([SV] *proovima* RU *попробовать*), which the app also uses: the phase gloss names the wrong verb. |
| Kontrolli (phase) | проверь | Kontrolli | проверь | Check | S4 | owner | Correct word ([SV] *kontrollima*), but the same label is the primary button (check my answer). With the step renamed *Tunnikontroll* the clash shrinks; the owner may keep it. |
| Kordamine (step) | повторение | Kordamine | повторение | Review | повторення | keep | As in navigation. |
| Reegel (step; rule headings) | правило на практике; правило по источникам; правило | Reegel | правило | Rule | правило [SV] | change (gloss) | [SV] *reegel* RU *правило*; *Mis oli reegel?* [EKI-F §3.4]. Three glosses for one word; the step's description belongs in the instruction line, not the gloss. |
| Harjutamine | упражнения | Harjutamine | упражнения | Practice | S4 [SV тренування] | keep | [SV] *harjutamine* EN *practice*; *harjutused* [CEFR-et p. 164]. |
| Sõnad | слова | Sõnad | слова | Words | слова | keep | *uued sõnad* [Kitsnik]; the unit part is *Sõnad* (`docs/course-structure.md`). |
| Kuulamine / Lugemine / Rääkimine / Kirjutamine (steps) | as skills | as skills | as skills | as skills | as skills | keep | One name per skill, in the session too (section 2). |
| Kontroll (step) | проверка | Tunnikontroll | проверочная работа | Lesson check | S4 | change | [SV] *tunnikontroll*: a short written check of what the lesson taught, RU *проверочная работа на уроке*; *Tunni lõpus teeme väikese tunnikontrolli* [EKI-F §3.7]. Frees *kontroll* from naming a step, a phase, a button and the unit check at once. |
| Tänane tund | занятие на сегодня | Tänane tund | занятие на сегодня | Today's lesson | урок [SV] | keep | *Kuidas sul tänane tund läks?* [EKI-F §2.3]; [SV] *tund* (sense: lesson) RU *урок, занятие*. |
| Tund (session line) | занятие | Tund | занятие | Lesson | урок [KK UA] | keep | As above. |
| Samm 3/7 | (none) | Samm | шаг | Step | S4 | keep | *samm* is an A2 core word [H-A2]. |
| Ülesanne (bead, counts *8 ülesannet*) | задание | Ülesanne | задание | Exercise | завдання [KK UA] | keep | Keeletee *Ülesanne:*, RU *Задание:*, EN *Exercise:*, UA *Завдання:* [KK]; HARNO *Esimene ülesanne* [H-B1k]; [SV] RU *задание*. |
| Sõnad ja kuulamine; Lugemine ja kirjutamine (rotation) | слова и аудирование; чтение и письмо | unchanged | unchanged | Words and listening; Reading and writing | S4 | keep | Built from kept names. |
| Nüüd segamini | теперь вперемешку с другой темой | owner | теперь вперемешку | Now mixed | S4 | owner | [SV] *segamini* means in disorder, messy. The gloss carries the meaning; an alternative of ordinary words is *Nüüd koos teise teemaga*. |
| Ilma vihjeteta | без подсказок | Ilma vihjeteta | без подсказок | No hints | S4 | keep | [SV] *vihje* EN *hint*. |

## 5. Controls and states

| Current ET | Current RU | Proposed ET | Proposed RU | Proposed EN | UK | Mark | Reason and source |
|---|---|---|---|---|---|---|---|
| Peata | пауза; пауза, прогресс сохранится | Peata | пауза | Pause | пауза [SV *paus*] | owner | [SV] *peatama* includes suspending (RU *приостановить*). Teachers say *Teeme pausi* [EKI-F §2.4]; *Paus* ([SV], RU *пауза*) would name the state instead of the act. No authoritative platform localisation was reached. |
| Jätka | продолжить | Jätka | продолжить | Continue | продовжити [SV] | keep | [SV] *jätkama* RU *продолжать*; A2 core word [H-A2 p. 145]. |
| Edasi | дальше; к упражнениям | Edasi | дальше | Next | далі [SV] | keep | *Lähme edasi* [EKI-F §3.1]; [SV] RU *дальше*. Keep one gloss; where the next screen differs, say so in the instruction line. |
| Kontrolli (button) | проверить | Kontrolli | проверить | Check | перевірити [SV] | keep | *Kontrolli oma vastust* [EKI-F §6.5]; [SV] *kontrollima* RU *проверять*. |
| Jäta vahele (item, word, unit) | пропустить | Jäta vahele | пропустить | Skip | S4 | keep | [SV] *vahele jätma*: leave a gap in a sequence, RU *пропускать*. |
| Proovi veel | попробуй ещё раз | Proovi veel | попробуй ещё раз | Try again | S4 | keep | EKI's feedback section is titled *Tagasiside: proovi veel* [EKI-F §4.10]. |
| Proovi uuesti (reload, resend) | загрузить ещё раз; попробовать снова | Proovi uuesti | попробовать снова | Retry | S4 | keep | [SV] *uuesti* EN *again*; *Teeme uuesti* [EKI-F §3.1]. |
| Miks? (session) / Selgita (free practice) | объясни / объяснить | Selgita | объясни | Explain | пояснити [SV] | change | One action, two labels. [SV] *selgitama* RU *объяснять, пояснять*; the Russian gloss of *Miks?* already says *объясни*. *Explain* is a plain verb, not Duolingo's product name *Explain My Answer* [Duo]. |
| Küsi | спросить; спроси о правиле | Küsi | спросить | Ask | S4 | keep | *Küsi minult* [EKI-F §6.9]; *küsima* [H-A2 p. 148]. |
| Näita | показать ответ | Näita | показать ответ | Show | S4 | keep | Ordinary verb. |
| Kinnita | это мой ответ | Kinnita | подтвердить | Confirm | підтвердити [SV] | change (gloss) | [SV] *kinnitama*, sense: acknowledge something as true; EN *confirm*, RU *подтвердить*. The current gloss describes rather than glosses. |
| Valmis | сдать проверку; готово | Valmis | готово | Done | S4 | keep (gloss unified) | *Kas sul on valmis?* [EKI-F §6.5]. |
| Õige | верно | Õige | верно | Correct | S4 [SV: правильний] | keep | *Õige vastus* [EKI-F §4.9]; [SV] RU *верный*. |
| Pole õige | неверно | Pole õige | неверно | Incorrect | S4 | keep | EKI's teachers say *Ei ole õige* [EKI-F §4.10]; *pole* is its usual short form. Not *Vale*. |
| Vahele jäetud | пропущено, без оценки | Vahele jäetud | пропущено | Skipped | S4 | keep | From *vahele jätma* [SV]. |

## 6. Course structure

| Current ET | Current RU | Proposed ET | Proposed RU | Proposed EN | UK | Mark | Reason and source |
|---|---|---|---|---|---|---|---|
| ühik (*Ühik 3 · 2/5*, *Jätka: 1. ühik*) | блок | peatükk (*3. peatükk · 2/5*, *Jätka: 1. peatükk*) | глава | Chapter | розділ [KK UA, SV] | change | [SV] *ühik*: a unit of measurement, or one item among similar ones; no source uses it for a part of a course, and [H-A2]'s core list lacks it. Keeleklikk/Keeletee: *Глава / Chapter / Розділ* [KK]; coursebook *peatükk* with *Selles peatükis õpime* [Kitsnik], *Peatükid* [UT]; [SV] *peatükk* RU *глава*, and *õppetükk* = a coursebook chapter. *Unit* is Duolingo's word [Duo]. Klint's units link to Keeleklikk/Keeletee chapters as companions (`docs/course-structure.md`), so one word serves both. |
| Jäta ühik vahele; Too ühik tagasi; Alusta siit | пропустить блок; вернуть блок в маршрут | Jäta peatükk vahele; Too peatükk tagasi; Alusta siit | пропустить главу; вернуть главу; начать отсюда | Skip chapter; Bring chapter back; Start here | S4 | change | Follows the row above; *маршрут* goes with *rada*. |
| Ühiku kontroll | проверка блока | Peatüki test | тест по главе | Chapter test | тест [KK UA] | change | Keeleklikk ends each chapter with *Тест / Test yourself / Тест*, Keeletee with *Test* [KK]; a *test* after chapters [Kitsnik]; [SV] *test*: a standard set of tasks. Distinct from *Tunnikontroll* and *Kontrolltöö*. Alternative: *Peatüki kontroll*. |
| Ühik kontrollitud | (result line) | Peatüki test tehtud | тест по главе пройден | Chapter test passed | S4 | change | Follows. |
| Kontrolltöö (level checkpoint) | контрольная; контрольная уровня | Kontrolltöö | контрольная работа | Level test | контрольна робота [SV] | keep | [SV] *kontrolltöö*: written work that checks knowledge, RU *контрольная работа*; *Meil tuleb kontrolltöö* [EKI-F §3.7]; [H-B1 p. 86]. |
| Grammatika kontroll (Eksam fold holding Kontrolltöö) | проверка тем курса | Kontrolltöö | контрольная работа | Level test | S4 | owner | One thing, two names (fold and button). |
| Kontrolli teadmisi (topic test-out) | проверить знания | Kontrolli teadmisi | проверить знания | Check what I know | S4 | keep | Ordinary phrase; *kontrollima* [SV]. |
| Teema | тема | Teema | тема | Topic | тема [SV] | keep | Keeletee *TEEMA* [KK]; *Tänane teema on…* [EKI-F §1.3]. |
| Kordus (unit part: earlier rules revisited) | (Kordus: X) | Kordamistund | урок повторения | Revision lesson | S4 | owner | [SV] *kordus* RU *повтор*, close to *Kordamine* (FSRS review), a different thing. [SV] *kordamistund*: a lesson in which what was learned is repeated, RU *урок на повторение*. |
| Kodutöö | (домашнее задание) | Kodutöö | домашнее задание | Homework | S4 | keep | [SV] *kodutöö* RU *домашняя работа*; *kodune töö* [EKI-F §2.2]. |
| Algus, A1, A2, B1 (stage headings) | (none) | Algus, A1, A2, B1 | начало, A1, A2, B1 | Beginning, A1, A2, B1 | S4 | keep | [SV] *algus* EN *starting point*; *algtase* ([SV]: the first, lowest level) contains *tase* and could read as a CEFR claim. *Algus* also names the starting-point question in onboarding; see section 8. |
| Esimesed sõnad | первые слова | Esimesed sõnad | первые слова | First words | S4 | keep | Plain. |

## 7. Exercise types and the exam

| Current ET | Current RU | Proposed ET | Proposed RU | Proposed EN | UK | Mark | Reason and source |
|---|---|---|---|---|---|---|---|
| Märka | заметь разницу | Märka | заметь | Notice | S4 | keep | [SV] *märkama* EN *notice* RU *замечать*; HARNO's A2 handbook names *märkamine* of words as the best way to learn them [H-A2 p. 66]. The usual textbook rubric *Pane tähele* ([SV] *tähele panema* = *märkama*) was found only as a warning-sign example [H-A2], so it is not proposed. |
| Proovi (rule walk) | выбери форму сам | Proovi | попробуй | Try | S4 | keep | [SV] *proovima*; *Proovi palun ise teha* [EKI-F §4.5]. |
| Miks nii (heading) | почему так | Selgitus | объяснение | Explanation | пояснення [SV] | change | One name with *Selgita* (section 5); [SV] *selgitus* RU *объяснение*. |
| Vastanda | неверно и верно | Õige ja vale | верно и неверно | Right and wrong | S4 | owner | *Vastandama* is right in meaning ([SV]; *oskab vastandada grammatilisi vorme* [H-A2 p. 71]), but the section shows a wrong and a right sentence, which EKI's teachers ask about as *õige või vale* [EKI-F §6.4], and the current gloss already says so. |
| Muuda tingimust | выбери условие — форма изменится | Muuda tingimust | выбери условие | Change the condition | S4 | keep | Ordinary words; no established rubric for this exercise was found. |
| Sõnatrenn; Trenn tehtud | тренировка слов; тренировка пройдена | Sõnavaraharjutus; Harjutus tehtud | упражнение на лексику; упражнение выполнено | Vocabulary practice; Practice done | S4 | change | *sõnatrenn* has no Sõnaveeb entry; *trenn* is a sports word ([SV], listed with *treening* [H-A2 p. 157]) and repeats Babbel's *vocab workout* [Babbel]. University of Tartu names its course items *Sõnavaraharjutus* [UT]; EKI uses the same pattern in *Hääldusharjutused* [SV-UI]. |
| Koosta fraas | собери фразу | Koosta fraas | собери фразу | Build the phrase | S4 | keep | [SV] *koostama* RU *составлять*; *fraas*; EKI's own phrase lists are a *fraasikogu* [EKI-F]. |
| Etteütlus | диктант | Etteütlus | диктант | Dictation | диктант [SV] | keep | [H-A2 p. 123], [CEFR-et p. 164], [H-B1 p. 178]; [SV] RU *диктант*. |
| Loe ette (read aloud) | вслух; озвучить | Loe ette | читать вслух | Read aloud | S4 | keep | *valjult ettelugemine* [CEFR-et p. 164]; *Loe ette … tekst* [EKI-F §6.4]. |
| Vestlus | разговор с собеседником | Vestlus | разговор | Conversation | розмова [SV] | keep | HARNO's speaking test is a *vestlus* [H-et]; *vaba vestlus* [CEFR-et p. 164]; [SV] RU *разговор, беседа*. |
| Proovieksam | пробный экзамен (на время) | Proovieksam | пробный экзамен | Mock exam | S4 | keep | [SV] *proovieksam*: work like the exam, done before it; RU *пробный экзамен*. |
| Terve eksam | все четыре части подряд | Terve eksam | весь экзамен | Full exam | S4 | keep | Plain. |
| Eksamipäev | (exam-day rules) | Eksamikord | порядок проведения экзамена | Exam rules | S4 | owner | The content restates HARNO's information sheet; HARNO calls these rules *eksamikord* (*video eksamikorrast*) [H-et] and *порядок проведения* [H-ru]. Neither compound has a Sõnaveeb entry; *Eksamipäev* is transparent too. |
| Eksami korraldus | формат и дата | Eksami korraldus | формат и дата | Format and dates | S4 | keep | [SV] *korraldus*, sense: the order or system prevailing in something. |
| Eksami kuju | как устроен экзамен | Eksami ülesehitus | структура экзамена | Exam structure | S4 | change | Integration Foundation: *tasemeeksamite ülesehitus* [IS]; HARNO *структура экзамена* [H-ru], *structure of the examination* [H-en]; [SV] *kuju* is outward shape, *ülesehitus* structure. |
| Minu valmisolek | моя готовность | Minu valmisolek | моя готовность | My readiness | готовність [SV] | keep | *valmisolekut eksamiks*, RU *готовность к сдаче экзамена* [IS]; [SV]. |
| Sessioon (exam.js) / Eksami aeg (session end) | когда сдаю / дата экзамена | Eksami aeg | дата экзамена | Exam date | S4 | change | One thing, two names. [SV] *sessioon* is a congress session or a university exam period, not a HARNO sitting; HARNO lists *Toimumisajad* [H-et]. |

## 8. Onboarding

| Current ET | Current RU | Proposed ET | Proposed RU | Proposed EN | UK | Mark | Reason and source |
|---|---|---|---|---|---|---|---|
| Kust alustame? | с чего начнём? | Kust alustame? | с чего начнём? | Where shall we start? | S4 | keep | Plain question. |
| Selgituste keel | язык объяснений | Selgituste keel | язык объяснений | Explanation language | S4 | keep | [SV] *selgitus*. |
| Vaata esmalt ringi | сначала осмотреться | Vaata esmalt ringi | сначала осмотреться | Look around first | S4 | keep | Plain. |
| Milleks õpid? / Eesmärk | для чего учишься? / цель | unchanged | unchanged | What for? / Goal | мета [SV] | keep | *eesmärk* [H-A2 p. 143]; [SV] RU *цель*. |
| Igapäevaelu | для жизни | Igapäevaelu | повседневная жизнь | Everyday life | S4 | change (gloss) | HARNO's A2 topic *igapäevaelu* [H-et]; B1 *igapäevaelu või tööga* topics [H-B1 p. 33]. The gloss should name the domain, as the next row does. |
| Töö | для работы | Töö | работа | Work | S4 | change (gloss) | Keeletee chapter *Töö* [KK]; [H-B1 p. 33]. |
| A2 eksam; B1 eksam | экзамен A2; подготовка к экзамену A2 | A2-taseme eksam; B1-taseme eksam | экзамен на уровень A2; на уровень B1 | A2 level exam; B1 level exam | S4 | change | HARNO's names: *Eesti keele A2-taseme eksam* [H-et], *Экзамен … на уровень A2* [H-ru], *level A2 exam* [H-en]. |
| Kust alustad? / Algus (legend) | с чего начнёшь? / точка старта | Kust alustad? / owner | с чего начнёшь? | Where do you start? | S4 | owner | *Algus* names both the first stage and this question's legend (and *Algus — старт* in Profiil): one word, two things. The question can stand without a legend. |
| Alustan algusest | с первого блока: звуки, приветствия, числа | Alustan algusest | с первой главы: … | From the beginning | S4 | change (gloss) | *блок → глава* (section 6). |
| Valin alguse | что-то уже знаю — выберу ступень сам | Valin alguse | (unchanged) | I'll choose | S4 | keep | Plain. |
| Proovin ennast | короткая проверка | Proovin ennast | короткая проверка | Test myself | S4 | keep | Plain. The Integration Foundation's quick placement test is called *Sõeltest* [IS], a product name of theirs; not copied. |
| Vali oma algus / Aste | выбери ступень / ступень | unchanged | unchanged | Choose your stage / Stage | S4 | keep | [SV] *aste* RU *ступень*. |
| Mitu korda nädalas? | сколько занятий в неделю? | unchanged | unchanged | How many times a week? | S4 | keep | Plain. |
| Alusta; Tagasi; Lõpeta siin; Sinu algus | начать; назад; закончить здесь; твоя точка старта | unchanged | unchanged | Start; Back; Stop here; Your start | S4 | keep | [SV] *alustama*; plain words. |

## 9. Other names noticed

| Current ET | Current RU | Proposed ET | Proposed RU | Proposed EN | UK | Mark | Reason and source |
|---|---|---|---|---|---|---|---|
| Märgid (milestones) | вехи; этапы обучения | Verstapostid | вехи | Milestones | S4 | change | [SV] *märk* is a sign or mark; *verstapost*, figuratively a turning point, EN *milestone*, RU *веха*. Estonia's first beginner-level description was titled *Esimene verstapost* [H-A2 p. 21]. |
| Rütm | история занятий; занятия по дням | Rütm | ритм занятий | Rhythm | S4 | owner | [SV] *rütm*: regular alternation; a figurative name for the sessions-by-day grid. |
| Kaart / kaarti (review counts) | карточка | Kaart | карточка | Card | S4 | keep | [SV] *sõnakaart*: the flashcard of language learning; *kaart* alone is its short form in context. |

## Open questions for the owner

1. **Peatükk or ühik.** *Peatükk* follows Keeleklikk and Estonian coursebooks; the
   Russian becomes *глава* (Keeleklikk) rather than *блок*; the English *Chapter*
   (Keeleklikk) rather than *Unit* (Keeletee's sub-chapter, Duolingo). Accept?
2. **Unit check:** *Peatüki test* (Keeleklikk's *Тест* at the end of each chapter) or
   *Peatüki kontroll*?
3. **Konsultatsioonivihikud** is HARNO's exact name but long in the Veel sheet.
   Accept it, or use the shorter *Vihikud / тетради*?
4. **The phase *Kontrolli*** shares its word with the primary button. Keep it once the
   step is *Tunnikontroll*, or rename the phase?
5. **Sõnavara's Russian gloss:** *лексика* (Keeleklikk UA, FIPI, Sõnaveeb) or the plainer *слова*?
6. **Peata or Paus** for the session's pause control?
7. **Vastanda or Õige ja vale** for the wrong/right pairs?
8. **Eksamipäev or Eksamikord** (HARNO's word) for the exam-day rules?
9. **Kordus or Kordamistund** for a unit's revisit of earlier rules, given *Kordamine*
   is the review queue?
10. **Russian skill names:** keep the teaching terms (*аудирование, говорение*) or follow
    HARNO's Russian page (*слушание, устная часть*)? The proposal keeps the teaching terms
    for the skills everywhere, including the exam.
11. **Veel's gloss** *ещё* (the word) instead of *разделы* (a description)?
12. **Vaba harjutus** stays, or *Harjuta vabalt* to avoid the gymnastics sense?
13. **Nüüd segamini:** Sõnaveeb gives *segamini* the sense of untidy; keep it or use
    *Nüüd koos teise teemaga*?
14. **Word statuses** *õpin, tean, eiran, teadsin ammu, tuttav* resemble LingQ's
    *Learned / Known / Ignore*. Review them in S11 with the exercise redesign?
15. **Ukrainian** (S4): sources found so far are Keeleklikk's Ukrainian interface
    (*Курси, Зміст, Словник, Розділ, Урок, Завдання, Тест, лексика*), Sõnaveeb's
    Ukrainian equivalents and the Argo coursebook (*Словник, Вправи*). The four skill
    names (*аудіювання, говоріння, читання, письмо*) come from a search result only and
    need a primary Ukrainian source.

## Applying the changes later

These are proposals. A session that applies them changes, together: the strings in
`eesti/web/index.html`, `eesti/web/js/*.js` and `eesti/session.py` (`NAMES`, `ROTATION`,
`PHASES`, `GOAL_NAMES`, `next_task`); `DESIGN.md` (screens, dock, session line),
`docs/app-structure.md` and `docs/course-structure.md`; the language checks in
`tests/test_ui_language.py` and the browser journeys in `tests/test_e2e_journeys.py`,
which find screens by these names. The S4 catalogue should take the Russian, English
and Ukrainian columns as its starting entries.
