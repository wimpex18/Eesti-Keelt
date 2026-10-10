# App structure

The interface (Interlinear, `DESIGN.md`) leads with today's session. Four
skills stay in navigation on every page. Course, review, exam and account are
ordinary destinations rather than mutually exclusive mode bars.
`library.MODES` still classifies source material; it does not determine the
navigation shell.

## The structure, as built

```
Learning and practice
├── Täna          today's session (ADR-0009): its plan, one Jätka, two alternatives
├── Kursus        units and their topics, rules, checked test-out and reversible skips;
│                 Vaba harjutus and a five-item offline pack live here
├── Lugemine      source texts and word lookup; five source-backed starter
│                 sentences when the imported library is empty
├── Kuulamine     dictation first; the recording library and custom TTS fold below
├── Rääkimine     read-aloud, questions, open responses and partner conversation
└── Kirjutamine   a short daily writing prompt, grammar feedback and translation

Supporting destinations
├── Kordamine     FSRS queue, with vocabulary and progress links
├── Sõnavara      five-word practice; the full word collection is an optional fold
├── Sõnastik      the dictionary: any form or a Russian word finds its entry;
│                 the word card opened from a text is the same entry
├── Töövihikud    official HARNO materials and in-app downloaded PDF pages
├── Eksam         optional A2/B1 practice, mock exam and official tasks;
│                 readiness, format, sitting and grammar checks open on request
├── Edenemine     recorded progress, history, forecast, reminders and data export
└── Profiil       identity, starting point and reset/restore recovery
```

Context pages have no extra permanent navigation item: `#start` is onboarding,
`#session` is today's session and `#session/<topic>` a session on one topic
(its rule, practice and a short check; Kursus' test-out and unit check run
there too, at `#session/check/<unit|testout>/<id>/<seed>`, so a reload resumes
the same set), and `#rule/<topic>` is the full reference. Rules use a page rather than a modal. Word lookup opens the word card,
a sheet over the text (`#sonastik/<lemma>` is the same entry as a page). Source
text, audio, video and PDFs stay in their in-app viewers when available;
attribution links remain visible.

Onboarding asks four questions — the explanation language (preselected from
the browser's languages; Profiil changes it later), the goal, the starting point and sessions a week —
and then opens today's session. The starting point is the beginning, a chosen
stage, or a placement of at most twelve code-graded items (three a unit) that
places by unit. This is a course recommendation, not certified CEFR. Guests can
use it and revise their choice from Kursus or Profile. Russian explanations are
the MVP; choosing English or Ukrainian says, in that language, that the app's
own text is Russian for now and that the model's explanations answer in the
chosen language.

Routes live in the hash. Skill changes push history; re-selecting the same skill
adds no history. Deep lesson and rule links survive a reload, unknown routes
recover to Home, and `#drill` opens Course's free practice. Desktop uses a left
navigation column (a rail of marks on tablets); phones use a compact header
with Veel and Profiil, and a permanent bottom dock of Täna and the four skills,
which gives way to a task row when the keyboard is up.
Appearance is changed from the shared header; Profile links to Progress instead
of duplicating its evidence or data export.

The cached shell can open offline, and a previously downloaded five-item pack
can be answered there. When no shell copy exists, the service worker presents a
small Russian explanation and **Proovi uuesti** link. Retrying while offline
keeps that recovery screen; after connectivity returns it opens the app.

## What grades each activity

| Activity | Graded by | Writes |
|---|---|---|
| Today's session and a topic session | code against issued forms; the key stays on the server until the attempt | the first attempt only: attempts, mastery and review queue (a heard item makes no card); a retry after a hint is graded and not recorded |
| A unit word in the session | code against the form in EKI's phrase | the first correct recall queues a meaning card |
| Placement in onboarding | code against each item's key, from its token | nothing but navigation: the units before the start are moved past |
| Writing and speaking in a session, the mock exam's writing and Rääkimine's open answers | code's checklist, then the model's comments against HARNO's descriptors | writing and speech practice; the comments are never recorded or scored |
| Unit 1 sound items | code against EKI's own form and quantity mark for the recording played | attempts and mastery; no card |
| Free practice | same code, `record: false` | nothing |
| Topic test-out / onboarding grammar check | server checks all five answers | checked mastery only on a pass |
| Unit check | server rebuilds the set from its seed and checks every answer | attempts; a passed unit check; mastery for a part answered 5 of 5 |
| Topic skip / selected start | navigation choice | `course_choices`, never attempts or mastery |
| Exercise or word skip | no grade | current session only; no mastery or FSRS |
| Offline pack | local verdict, then server re-grades the signed item; heard items are left out | attempts at the original answer time |
| Kordamine | code and FSRS | review card state |
| Sõnavara collection | no grade | explicit word status |
| Reading and word lookup | no grade | encounters and explicit mining choices |
| Reading questions | code against the text's stored span | comprehension evidence |
| Dictation | code, word-aligned | dictation history |
| Free writing | labelled model explanations plus deterministic checks | correction queue; advisory evidence |
| Speech | ASR and deterministic measurements | practice evidence, never mastery |
| Partner conversation | a labelled model plays the partner | contact and duration; no score |
| Mock exam | code for reading/listening and deterministic writing checks | exam sections; speaking remains unscored |
| TTS, material viewers and reports | no grade | no checked mastery |

Models never decide drill correctness, mastery or FSRS. Engine and source
attribution stay attached to feedback (`docs/ai-boundaries.md`).

## Consolidation and progression

Course owns guided and free grammar practice. Vocabulary chooses or mines words;
Review schedules them. Reading and vocabulary share one word card. Exam owns
timed practice and exam evidence; ordinary skills need no exam goal. Progress
owns history, so Profile and Home do not repeat readiness flowers, totals, rhythm
grids or competing time plans.

Kursus lists the course unit by unit (`docs/course-structure.md`): each unit
folds open to its goal in Russian, its topics, a *Kordus* button that practises
only the rules its stage unlocks in an earlier topic, the first week's words with
their meaning, and its companion Keeleklikk or Keeletee unit, marked as an
external course. The current unit is open. A unit shows how many of its topics
are mastered, and offers its check (*Ühiku kontroll*), which runs in the same
frame as a test-out; a unit is called complete once its check is passed and
its core topics are mastered.

Topic states are locked, ready, in progress, mastered, reference-only and skipped.
Every state has a textual label and icon. Prerequisites come from
`eesti/curriculum.py`. Reference topics do not block subsequent practice.

`POST /api/course/topics/{topic}/skip` stores a navigation skip; `skip: false`
restores it. Starting-point choices move past earlier chapters only when
onboarding explicitly requests `navigate`. These changes never create attempts,
FSRS cards or readiness. Learners can still open any topic's rule or practise it.
Known exercises and words can be passed over without being marked correct;
skips are named separately in the result and can be revisited in another set.

Word statuses remain `õpin`, `tean`, `eiran`, `teadsin ammu` and `tuttav`.
Checked topic mastery, vocabulary knowledge, review scheduling and the four exam
parts remain separate measures. There is no combined overall percentage.
