# Course structure

The A0→B1 course as units: what a unit holds, how the units follow HARNO's
topics and EKI's grammar-competence profile, where every curriculum topic
lives, and how units reach Home, Course, Review, Exam and the four skills.
The units are data in `eesti/units.py`; the decision and its consequences are
ADR-0007 (`docs/adr/0007-course-units.md`). Topics, prerequisites and mastery
remain as described in `docs/curriculum.md`.

## Shape

- **A unit is one week**: about five sessions of 20–30 minutes. Thirty units
  run from the first sound to B1: Algus 1, A1 9, A2 9, B1 11.
- **Stages** group the units: `algus`, `A1`, `A2`, `B1`. A stage is the
  target the unit's content serves, as EKI's grammar profile (etLex, cited by
  statement id) and HARNO's topic lists place it, and is shown as a target
  (*sihttase A2*). It is never the learner's level and never a `level`:
  only official HARNO/EIS material has a CEFR level (AGENTS.md). A0 is not a
  CEFR level, so the first stage is *Algus*.
- **Topics stay the unit of grammar.** Every curriculum topic has exactly one
  home unit, where it is introduced and checked. A later unit may *revisit*
  a sub-rule of an earlier topic that its stage unlocks (the nominative total
  object at A2). Topic ids, rule pages, mastery and FSRS are unchanged
  (ADR-0005).
- **Units follow the prerequisite graph.** A unit introduces a topic only
  after every prerequisite's home unit; a test holds the map to the graph.

## What a unit contains

| Part | What it is | Graded by | Gates completion |
|---|---|---|---|
| *Eesmärk* | One communicative goal, with the HARNO topic and EKI profile statements it serves | — | — |
| *Sõnad* | A word set: a `themes.py` theme or EKI picture-dictionary categories (text only, credited) | self-rated review | no |
| *Dialoog* | A short dialogue on the unit's situation, from the material pipeline (`qa/architecture-review.md`): model draft → Vabamorf verifies every form → every lemma within the stage's EKI word level → a person reviews → code keys the questions; labelled as written with a model | code, against the stored key | no |
| *Grammatika* | The topics the unit introduces | code (mastery: 8 of the last 10 over 5 items) | yes |
| *Kordus* | Sub-rules of earlier topics this stage unlocks | code, in the unit check | yes, through the check |
| *Lugemine*, *Kuulamine*, *Rääkimine*, *Kirjutamine* | One task per skill where material exists | code where it can (text spans, dictation); model feedback labelled and advisory | no: recorded, skippable |
| *Kontroll* | Five checked items per core topic and per revisited rule, graded server-side | code | yes |
| *Kodutöö* | Set at the end of each session: the due review cards and one short skill task | as the task | no |
| *Keeleklikk* | The matching Keeleklikk (0–A2) or Keeletee (B1) unit, or an explicit none | — | — |

A unit is **complete** when each core topic is mastered (practice or test-out)
and the unit check is passed. A unit with no core topic (a revision week) is
complete when its check is passed. Any unit or part can be skipped and
revisited; a skip is navigation, never mastery or readiness (PRODUCT.md). In
Kursus a learner skips one unit (*Jäta ühik vahele*), puts it back (*Too ühik
tagasi*), or starts from a chosen unit (*Alusta siit*), which moves past every
earlier unit not yet complete — a run of units or whole stages in one step
(`/api/course/units/skip`). A topic mastered inside a skipped unit stays mastered.

## Where units appear

| Destination | With units |
|---|---|
| *Täna* | One action: the current unit's next session (*Ühik 3 · 2/5*), the due review count beside it, homework until it is done. Exam appears only after the learner picks a sitting. |
| *Kursus* | Stages → units → parts. Each topic keeps its rule page, test-out and free practice, reached from its unit or from an *All topics* fold. |
| *Kordamine* | One FSRS queue. Unit words and missed items join it; there is no per-unit queue. |
| *Eksam* | Mocks, readiness and sittings stay here. From the A2 stage on, a unit ends with one HARNO-format task on its HARNO topic once DEV-41 builds those task types; the answer counts as evidence for that exam part. |
| Four skills | Each skill page leads with the current unit's task for that skill, then the existing library and tools. |

## Placement

- **Algusest** starts at unit 1 (*Tere!*).
- **A chosen start** begins at the stage's first unit: A1 moves past Algus, A2
  past Algus and A1, A2–B1 past everything before B1. Earlier units are
  navigation skips, revisitable, never mastered (`course.apply_start`, which
  reads each topic's stage from `eesti/units.py`).
- **The assessment** places the learner at the first unit with a core topic
  the assessment did not pass; earlier units are skipped, not mastered.
  Passing a unit check early is checked evidence and completes the unit. The
  assessment starts at A1: it does not probe unit 1.

## Homework and the weekly plan

- **Homework** is set at the end of each session: the unit's due review cards
  and one short skill task (three sentences on the unit's topic, a 30-second
  spoken answer). Home shows it until it is done. Code checks what it can;
  model feedback stays labelled and advisory.
- **Without a sitting** the plan is one unit a week.
- **With a sitting** code compares the weeks left with the units left before
  the sitting's stage ends and says plainly whether the pace fits
  (*12 units in 8 weeks*). In the last four weeks it moves time to mocks and
  the weakest exam part. Like `eesti/planning.py`, it is a pure function of
  the evidence; it never estimates a pass.

## Keeleklikk and Keeletee

The state's free courses carry video lessons; Klint does not. A unit names its
companion unit and links to its course map, labelled as an external, free
course. Klint never rehosts it.

- Keeleklikk (0–A2, 16 units, Russian, Ukrainian and English instructions):
  `https://www.keeleklikk.ee/{ru|ua|en}/A/coursemap/list/{n}`.
- Keeletee (B1, 13 units, Russian and English): the same site, `/B1/` in
  place of `/A/`; `keeletee.ee` redirects there.
- Course maps are public; lessons after unit 1 ask for a free account.
- The link follows the explanation language where the course has it, else
  English.

## The units

HARNO A2 topics are from HARNO's exam page; B1 topics from §4.2 of HARNO's
*Iseseisev keelekasutaja* handbook. KK is Keeleklikk, KT Keeletee.

| # | Id | Unit | Stage | Core topics | Revisits | HARNO topic | Course |
|---|---|---|---|---|---|---|---|
| 1 | `tere` | Tere! | Algus | `tahestik`, `fraasid`, `arvud` | — | keel | KK 1 |
| 2 | `tutvume` | Tutvume | A1 | `asesonad`, `kusisonad`, `olevik`, `lauseehitus` | — | isikuandmed; keel | KK 2 |
| 3 | `pere` | Minu pere | A1 | `pohivormid`, `arvsonad` | — | suhted teiste inimestega | KK 5 |
| 4 | `kohvik` | Kohvikus | A1 | `osastav`, `eitus` | `fraasid`: situations | söök ja jook | KK 4 |
| 5 | `kodu` | Kus sa elad? | A1 | `gen-stem`, `astmevaheldus`, `kohakaanded` | — | maja ja kodu; kohad | KK 3 |
| 6 | `paev` | Minu päev | A1 | `verb-form`, `kellaaeg`, `maarsonad` | — | igapäevaelu | KK 6 |
| 7 | `linn` | Linnas | A1 | `kaassonad`, `mitmus`, `sidesonad` | — | ümbruskond; kohad | KK 15 |
| 8 | `meeldib` | Mulle meeldib | A1 | `ma-da-inf`, `mul-on` | — | vaba aeg ja meelelahutus | KK 7 |
| 9 | `eile` | Eile | A1 | `lihtminevik`, `kaima-minema` | — | ilm; reisimine | KK 9 |
| 10 | `poes` | Poes | A1 | `obj-case`, `osaalus` | — | sisseostude tegemine | KK 8 |
| 11 | `kodus` | Kodus | A2 | `kaskiv` | `obj-case`: imperative, plural | maja ja kodu | KK 14 |
| 12 | `tervis` | Tervis | A2 | `tingiv` | — | tervis ja kehahooldus | KK 11 |
| 13 | `valimus` | Välimus ja iseloom | A2 | `vordlusastmed` | — | suhted teiste inimestega | KK 12 |
| 14 | `kogemused` | Kogemused | A2 | `kesksonad`, `taisminevik` | — | haridus | KK 13 |
| 15 | `puhad` | Pühad ja kuupäevad | A2 | `jargarvud`, `kuupaevad` | — | igapäevaelu | KK 16 |
| 16 | `too` | Töö ja amet | A2 | `tuletus`, `ma-vormid` | — | haridus | KK 13 |
| 17 | `plaanid` | Plaanid | A2 | `tulevik` | — | vaba aeg ja meelelahutus | KK 7 |
| 18 | `teenused` | Teenused | A2 | `harvad-kaanded` | — | teenused | KK 8 |
| 19 | `reis` | Reisimine ja ilm | A2 | — | — | reisimine; ilm; kohad | KK 9 |
| 20 | `minu-paev` | Minu päev ja tunded | B1 | `rektsioon`, `sonajark` | — | endast ja teistest rääkimine | KT 1 |
| 21 | `restoran` | Restoranis | B1 | `uhildumine` | — | söök ja jook | KT 3 |
| 22 | `perekond` | Perekond ja suhted | B1 | `kirjavahemargid` | — | inimeste suhted ühiskonnas | KT 5 |
| 23 | `kodukoht` | Kodu ja kodukoht | B1 | `umbisikuline` | `obj-case`: impersonal | igapäevaelu, kodu ja kodukoht | KT 6 |
| 24 | `ostud` | Ostud ja hinnad | B1 | `uhendverbid` | `obj-case`: *da*-infinitive | sisseostud, hinnad | KT 7 |
| 25 | `haridus` | Haridus ja keeled | B1 | `kaudne` | — | haridus; kultuur ja keeled | KT 8 |
| 26 | `reisid` | Reisid | B1 | `enneminevik` | — | reisimine, transport | KT 9 |
| 27 | `enesetunne` | Enesetunne | B1 | — | — | enesetunne ja tervis | KT 10 |
| 28 | `too-elu` | Töö ja teenindus | B1 | `liitsonad` | — | elukutse, amet ja töö; teenindus | KT 11 |
| 29 | `aastaring` | Aastaring ja loodus | B1 | — | `osaalus`: plural | keskkond, kohad, loodus, ilm | KT 12 |
| 30 | `uritused` | Üritused Eestis | B1 | — | — | vaba aeg ja meelelahutus | KT 13 |

Every HARNO A2 topic and every B1 topic has a unit. Units 19, 27, 29 and 30
are revision weeks: their check draws on the stage's topics, and they carry the
stage checkpoint (19: A2, 30: B1) and, once built, HARNO-format tasks. Unit 10
carries the A1 checkpoint.

### Where EKI's profile puts the revisited rules

| Rule | EKI etLex statement | Unit |
|---|---|---|
| Nominative total object with imperative, plural object | 1288 (A2) | 11 |
| Nominative total object in the impersonal | 1300 (B1) | 23 |
| Nominative total object with a *da*-infinitive | 879 (B2) | 24: the profile places it above B1; the rule is EKK SÜ 40 and the Teatmik's |
| Partitive subject in a negated existential sentence | 913 (A1), 1336 (A2) | 10 |
| Affirmative existential with a nominative subject | 1336 (A2) | 10, on the rule page |
| Full or partial subject in an affirmative existential (*Termoses on tee/teed*) | 1328 (B2) | 29, as the plural-agreement rule only |

Statement ids are cited, not copied: the profile's licence is stated as
CC BY 4.0 in EKI's teacher tools and as restricted in META-SHARE
(`qa/source-permission-requests.md`).

## Unit 1: *Tere!*

**Goal.** Greet, thank, apologise and say goodbye; say and understand numbers
to a hundred; hear the difference long and short sounds make; know the first
words.

| Part | Content | Source and credit |
|---|---|---|
| Sounds | `tahestik`: listen to an EKI recording and choose what was said. Pairs that differ in quantity only (*selle salli*, II quantity, against *seda salli*, III), in one vowel (*kapp*/*käpp*, *koht*/*kõht*) or in a short against a long sound (*kana*/*kanna*). The key is EKI's own form and quantity mark for the recording. | Recordings: EKI *Eesti keele põhisõnavara sõnastik 2014*, CC BY 4.0. Contrasts follow EKI's *e-hääldusharjutused* on Sõnaveeb, which the rule page links to for pronouncing aloud. |
| Phrases | `fraasid`: choose the phrase for a situation (*Tänamine* → *Aitäh!*) and the reply in one of EKI's exchanges (*Aitäh! – Palun!*, *Vabandust! – Ei ole midagi.*). Russian from EKI EVS where EVS has the phrase; none otherwise. | Sõrmus, Pool, Kallas, Kiisla (2025), *Kasulikke väljendeid A1-tasemel eesti keele õppijale*, EKI, Sõnaveeb (CC BY 4.0). |
| Numbers | `arvud`: write the number you see in words, or the number you hear in digits (0–100, *sada*). Keyed by a table checked against Vabamorf, spelt as EKK O 42 spells numerals. | EKK O 42; EKI Teatmik *Arvukirjutus*; Vabamorf. |
| First words | Colours and food: a selection of the words EKI's picture dictionary marks A1–A2 in its themes *Värvid* and *Toit ja jook*. The meaning is the app's (seed, then EKI EVS), because the dictionary's Russian captions name the picture (*kala* «окунь»); homographs whose meaning would be another word's (*tee*, *või*) are left out. Pictures stay on Sõnaveeb behind a link. | Selection: EKI *piltsõnastik* (J. Kallas, K. Koppel), Sõnaveeb (CC BY 4.0, text). Meanings: EKI EVS. |
| Listening | The sounds part is listening; numbers can be heard. | EKI recordings; TartuNLP TTS for numbers. |
| Speaking | Read the phrases aloud (*Loe ette*); greet and introduce yourself. | — |
| Writing | Write a greeting and your name. | — |
| Check | Five checked items each from `tahestik`, `fraasid` and `arvud`. | code |
| Keeleklikk | Unit 1, *Tere!* | link |

## What each unit still needs

| Need | Units | Tracked in |
|---|---|---|
| Dialogues and reading texts every learner may see | all | DEV-36 (material pipeline) |
| HARNO-format reading and listening tasks, writing tasks on the real clock | 11–30 | DEV-41 |
| Explanations in Ukrainian and English | all | DEV-42 |
| Verb-second word order on licensable material (`lauseehitus` is drilled only through `sonajark`) | 2, 20 | DEV-36 |
| Material for `uhendverbid` and `liitsonad` (too few marked examples) | 24, 28 | DEV-40 |
| Word sets for HARNO topics `themes.py` lacks (personal data, daily routine, free time, relationships, shopping and money, services, directions) | 2, 6, 8, 18 | DEV-40 |
| Speaking and listening tasks per HARNO topic | all | DEV-41, DEV-45 |

`astmevaheldus` stays reference-only: its contrast is drilled as `gen-stem`.

## What the redesign inherits

- Unit ids, stage ids and the unit → topic map in `eesti/units.py`; topic and
  rule ids from `eesti/curriculum.py`. Renaming a screen renames none of them.
- Unit states: locked, ready, in progress, complete, skipped. Completion is
  core mastery plus the unit check; skips are navigation.
- One next action on Home; one review queue; exam evidence per part; four
  skills reachable everywhere.
- Every item names its source and engine. EKI material carries EKI's credit
  wherever it is shown, offline packs, test-out, placement and review cards
  included.

## Built today

- `eesti/units.py` holds the thirty units: stages, topics, revisits, HARNO
  topics, word sets and companion links. A test holds the map to the
  prerequisite graph and to HARNO's lists. `GET /api/curriculum` carries the
  units with each one's mastered count and the current unit.
- Kursus folds by unit: goal, topics, a *Kordus* button for each revisit (it
  practises only the unlocked rules), the first week's words with their meaning,
  and the companion link. The current unit is open.
- The next topic follows unit order; unit 1 leads only for a learner who has
  mastered nothing beyond it, so an existing learner is not sent back to
  greetings (nothing is skipped). A chosen start moves past the units of
  earlier stages; the assessment does not probe unit 1, and the A1 checkpoint
  leaves it out.
- Unit 1's three topics have generators. `obj-case` drills the nominative total
  object by rule name, and `osaalus` drills the partitive subject.
- EKI's credit shows on every item built from its material, offline packs,
  test-out and placement included, and on review cards queued from 9 Oct 2026.
- The unit check (`eesti/unitcheck.py`, `GET`/`POST /api/units/{id}/check`):
  five items per core topic and per revisited rule, every part at least 4 of 5;
  a part answered 5 of 5 counts its topic as mastered, as a test-out would.
  Revision units with a checkpoint (19, 30) run it; unit 27 checks its stage's
  recent topics, and so does unit 28, whose `liitsonad` has no drill yet; unit 17
  checks `tulevik` (EKK SÜ 27: the present after a future adverbial, *hakkama* +
  ma). A unit is *complete* when its check is passed and its core topics are
  mastered; Kursus says so.
- Not built yet: homework, the weekly plan, placement into a unit from the
  assessment, Home naming the session within a unit, skill pages led by the
  unit, dialogues and texts.
