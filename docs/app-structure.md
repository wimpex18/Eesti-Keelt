# App structure

Three modes (`library.MODES`); every screen answers one of their questions.
Tabs live in `eesti/web/index.html`; `tests/test_docs_match_code.py` checks the
diagram below against the page in both directions.

## The structure, as built

```
Õppimine — "what am I learning today?"
├── Rada          the path: grammar topics in prerequisite order, mastery-gated
├── Harjutused    the same generators, free choice of rule, nothing recorded
├── Lugemine      reading texts ranked by how much of each the learner knows
├── Sõnavara      the word list by CEFR level and part of speech, commonest first
├── Kuulamine     dictation (graded), TTS on any text, radio episodes
├── Rääkimine     paired-exam question bank, read-aloud, open answers
└── Kirjutamine   grammar check through the provider chain, back-translation

Kordamine — "what am I forgetting?"
├── Järjekord     the FSRS queue: wrong answers and words mined from reading
└── Töövihikud    official HARNO consultation workbooks (pointers only)

Eksam — "am I ready?"
├── Ülevaade      readiness verdict, four exam parts reported separately
└── Edenemine     progress report
```

Tabs are in the URL hash (`#write`); each change pushes history, re-selecting
the current tab pushes nothing.

## What grades each screen

| Screen | Kind | Graded by | Writes |
|---|---|---|---|
| Rada | generated exercise | code | mastery, review queue |
| Harjutused | generated exercise | code | nothing |
| Järjekord | scheduled exercise | code | FSRS card state |
| Kuulamine · dictation | generated exercise | code, word-aligned | dictation history |
| Sõnavara | list | — | word status |
| Lugemine | material + lookup | — | word encounters |
| Kirjutamine | free text | **a model** (explains), plus deterministic checks | Notion queue |
| Rääkimine | speech | **ASR** (transcribes), never scored | nothing |
| Kuulamine · TTS, Ülevaade, Edenemine, Töövihikud | material / report | — | nothing |

Only Kirjutamine and Rääkimine involve a model, and neither decides whether an
answer is right (`docs/ai-boundaries.md`).

## Deliberate overlaps

- **Harjutused vs Rada** — same generators; Rada decides what is next and
  records mastery, Harjutused is an unrecorded sandbox.
- **Sõnavara vs Järjekord** — a word is chosen in Sõnavara and comes back in
  Järjekord. Both use one word card (`showWordCard()`) with `+ Kordamisse` and
  `Tean seda sõna`.
- **Lugemine vs Sõnavara** — reading records encounters; Sõnavara lists them.
- **Sections vs tabs** — seven library sections, eleven tabs. Other `oppimine`
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
