# App structure

Three modes (`library.MODES`); every screen answers one of their questions.
Tabs live in `eesti/web/index.html`; `tests/test_docs_match_code.py` checks the
diagram below against the page in both directions.

## The structure, as built

```
Õppimine — "what am I learning today?"
├── Rada          the drills, two ways: Minu rada (prerequisite order, mastery-gated,
│                 opens on today's set, with Täna — today's plan) and Vaba harjutus
│                 (any topic, nothing recorded)
├── Lugemine      reading texts ranked by the share of words within the learner's reach
├── Kuulamine     dictation (graded), TTS on any text, radio episodes
├── Rääkimine     paired-exam question bank, read-aloud, open answers, and
│                 Vestlus — a model plays the exam partner, never scoring
└── Kirjutamine   grammar check through the provider chain, back-translation

Kordamine — "what am I forgetting?"
├── Järjekord     the FSRS queue: wrong answers and words mined from reading
├── Sõnavara      the word list by CEFR level and part of speech, commonest first
└── Töövihikud    official HARNO workbooks (PDF pages in-app when downloaded)

Eksam — "am I ready?"
├── Ülevaade      readiness verdict, four exam parts reported separately, the
│                 exam's own shape, the sitting being prepared for,
│                 Proovieksam (one part on the exam's clock), and HARNO's own
│                 past tasks, read and played in the app where downloaded
└── Edenemine     progress report
```

Õppimine is the path plus the exam's four skills, so the phone's skill row holds
five chips. Tabs are in the URL hash (`#write`); each change pushes history,
re-selecting the current tab pushes nothing. The retired `#drill` opens Rada in
Vaba harjutus. A drill set shows one unanswered item at a time on every device;
for `obj-case` the case to use appears only with the verdict, since choosing it
is the exercise.

## What grades each screen

| Screen | Kind | Graded by | Writes |
|---|---|---|---|
| Rada · Minu rada | generated exercise | code | mastery, review queue |
| Rada · Vaba harjutus | generated exercise | code (same endpoint, `record: false`) | nothing |
| Rada · Offline | a pack fetched in advance | the page shows a verdict; the server re-grades from the token when the answers arrive | attempts, with the time they happened |
| Järjekord | scheduled exercise | code | FSRS card state |
| Kuulamine · dictation | generated exercise | code, word-aligned | dictation history |
| Sõnavara | list | — | word status |
| Lugemine | material + lookup | — | word encounters |
| Kirjutamine | free text | **a model** (explains), plus deterministic checks | Notion queue |
| Rääkimine | speech | **ASR** (transcribes), never scored | speech evidence |
| Rääkimine · Vestlus | conversation | **a model** plays the partner; nothing is scored | that a conversation happened, and how long |
| Ülevaade · Proovieksam | timed section, or all four in order | code (reading, listening, writing: length + deterministic checks); speaking not scored | exam sections |
| Kuulamine · TTS, Ülevaade, Edenemine, Töövihikud | material / report | — | nothing |

Only Kirjutamine and Rääkimine involve a model, and neither decides whether an
answer is right (`docs/ai-boundaries.md`).

## Deliberate overlaps

- **Minu rada vs Vaba harjutus** — one tab, one generator path, one grader
  (`/api/practice`, `/api/practice/answer`). Minu rada decides what is next and
  records mastery; Vaba harjutus lets the learner pick any topic (and, for
  object case, one sub-rule) and records nothing.
- **Sõnavara vs Järjekord** — a word is chosen in Sõnavara and comes back in
  Järjekord. Both use one word card (`showWordCard()`) with `+ Kordamisse` and
  `Tean seda sõna`.
- **Lugemine vs Sõnavara** — reading records encounters; Sõnavara lists them.
- **Sections vs tabs** — seven library sections, ten tabs. Other `oppimine`
  sections render inside Kuulamine from `/api/modes`; `eksam` sections are
  reached through `exam_material`. `tests/test_ui_contract.py` checks both
  directions.

## Word statuses

`õpin` (set on first encounter), `tean` (word card), `eiran` (**Pole vaja**),
`teadsin ammu`, `tuttav` (no control; same side of "settled" as `õpin`).

## Progress measures

| Section | Measure |
|---|---|
| Rada | topics mastered / total, current position |
| Sõnavara | words known within each frequency band |
| Kordamine | due today, retention |
| Lugemine · Kuulamine | texts read, dictations taken, words heard correctly |
| Eksam | readiness per exam part |

No single overall percentage: the exam fails a zero in any one part.

## Path rules

Topics have three states — locked, available, mastered — plus test-out on any
available topic. Prerequisites come from the topic graph in `curriculum.py`. A
topic with no generator is a reference topic (`progress.reference_topics()`)
and does not block anything downstream.
