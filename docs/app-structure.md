# How the app is organised, and why

The question this answers: with a grammar syllabus, 349 reading texts, 72 radio
episodes, generated drills and a review queue, **what does the learner actually
see** — and how is progress shown?

## What the mainstream apps settled on

**Duolingo replaced its skill *tree* with a linear *path* in 2022**, and their
own whitepaper reports the path produces better proficiency outcomes. The
mechanism is not that the content improved — it is that **choice was removed**.
A tree lets a learner wander and stall; a path says "this next". Each unit opens
with a guidebook, and review is built into the path rather than parked in a
separate section a learner never visits.

**Speakly** (Estonian-founded, which is why it supports Estonian at all) orders
vocabulary by **statistical real-world frequency** — the 4 000 most useful words
in the order you will actually meet them — and moves each word through three
stages: recognise → produce → repeat.

The two ideas are complementary and both apply here:

- one **path** for the thing that has a correct order (grammar has real
  prerequisites — every case builds on the genitive stem);
- **frequency ordering** for the thing that does not (vocabulary has no
  prerequisites, only usefulness), and `freq_rank` is already in the word list.

## The structure, as built

Measured 2026-08-21 by reading `eesti/web/index.html` and `eesti/library.py`,
not from intention. **The version of this section that stood here until now
described a structure that was never built** — it had a top-level
`Raamatukogu`, put `Kordamine` inside `Õppimine`, and had no `Rääkimine`,
`Kirjutamine` or `Grammatika` at all. It was a plan being read as a map.

Three modes, from `library.MODES`. Every screen answers one of three questions,
and that is the only rule the top level obeys:

```
Õppimine — "what am I learning today?"
├── Rada          the path: 25 of 36 grammar topics, prerequisite-ordered, mastery-gated
├── Harjutused    the same generators, free choice of rule, nothing recorded
├── Lugemine      349 Estonian texts, ranked by how much of each you already know
├── Sõnavara      the wordlist by CEFR level and part of speech, commonest first
├── Kuulamine     dictation from the corpus (graded) + TTS on any text (exposure)
├── Rääkimine     the exam's paired question bank + read-aloud through ASR
└── Kirjutamine   grammar check through the provider chain + back-translation

Kordamine — "what am I forgetting?"
├── Järjekord     the FSRS queue: items you got wrong, and words mined from reading
└── Töövihikud    official HARNO consultation workbooks (pointers only)

Eksam — "am I ready?"
├── Ülevaade      readiness verdict, four parts reported separately
└── Edenemine     progress report
```

### What each screen actually is

The distinction that matters for planning is not skill but **whether the app
can tell you that you were wrong**. Three kinds:

| Screen | Kind | Graded by | Writes |
|---|---|---|---|
| Rada | generated exercise | code, deterministic | mastery, review queue |
| Sõnavara | generated list | — (browsing) | word status |
| Kuulamine · dictation | generated exercise | code, word-aligned | dictation history |
| Harjutused | generated exercise | code, deterministic | nothing |
| Järjekord | scheduled exercise | code, deterministic | FSRS card state |
| Lugemine | material + lookup | — | word encounters |
| Kirjutamine | free text | **a model**, or offline heuristics | Notion queue |
| Rääkimine | free speech | **a model** (ASR), never scored | nothing |
| Kuulamine · TTS | material | — | nothing |
| Ülevaade · Edenemine | report | — | nothing |
| Töövihikud | pointers to PDFs | — | nothing |

**Only two screens depend on a model at all**, and neither of them decides
whether an answer is right: the writing check explains a correction in prose,
and the speaking screen reports what a recogniser heard. Everything with a
right answer is graded by code. That is the property in `docs/ai-boundaries.md`,
stated here as a table because it is easiest to violate by accident.

### Where the modules overlap

Three genuine overlaps, and only one of them is a defect.

**`Harjutused` is a narrower duplicate of `Rada`, and that is now deliberate.**
Both generate object-case drills; `/api/drills` serves four hand-listed rules,
`/api/practice` serves 25 topics including all four. What justifies keeping both
is *guidance*: `Rada` decides what is next and records mastery, `Harjutused`
lets you pick a rule and drill it with nothing recorded — a path and a sandbox.

It was called `Grammatika` and lived under **Eksam** until 2026-08-21, which
put free grammar practice behind the question "am I ready?" — where a learner
looking for exercises has no reason to open it. Renamed and moved next to the
path it is the unguided version of. The exam mode is now only the three things
that answer whether you are ready, which is what the mode is for.

**`Sõnavara` and `Järjekord` both act on words, and that is correct.**
Sõnavara is where a word is *chosen*; Järjekord is where a chosen word *comes
back*. Every word card in either place offers the same two actions —
`+ Kordamisse` queues the grammar pattern behind the word, `Tean seda sõna`
settles it — because it is one card, `showWordCard()`, with two callers. The
split matches what LingQ settled on: a vocabulary page for picking, a review
session for returning.

**The exam taxonomy is expressed twice.** `library.SECTIONS` declares which
`kind` values belong to `naidised`, `eksam` and `eksamiinfo`; `exam_material`
groups the same five values again for the exam screen, which never reads
`SECTIONS`. They are not merged because they answer different questions —
`SECTIONS` drives browsing, `exam_material` returns one level's material in a
single request grouped by activity — but it is exactly the shape that produced
the `TABS` bug: a hand-kept list beside the thing it describes, where nothing
fails when they drift because both halves still return *something*. Checked in
both directions by `test_sections.py`; they agree today.

**Not every section has a tab, and that is deliberate.** Seven sections, eleven
tabs, and the mapping is not one to one. `lugemine` and `vihikud` have tabs of
their own; the rest of `oppimine` is rendered inside Kuulamine from
`/api/modes`, so adding a section surfaces it without anyone editing the page;
the three `eksam` sections are reached through `exam_material`. The rule is
that a section is reachable by *some* route, and `test_ui_contract.py` checks
that in both directions — one-way contract tests find typos, not things nobody
wired up.

**`Lugemine` and `Sõnavara` are two doors to the same store.** Reading records
an encounter for every word met; Sõnavara lists those words with their status.
This is the LingQ model and is the point, not a duplication — but it means the
vocabulary count moves when you read, which the reading screen does not
currently say.

### Why `Sõnavara` sits under Õppimine

It is not a skill. Reading, listening, speaking and writing are the four things
the exam scores; vocabulary is the resource all four spend, which is why the
research keeps putting it *next to* reading rather than beside the skills.

Both apps worth copying agree on the shape and disagree on the detail. **LingQ**
makes vocabulary a layer over reading: click an unknown word, it is saved, it
feeds spaced repetition, and the page recolours as you learn. **Speakly**
(Estonian-founded) orders vocabulary by real-world frequency and moves each word
through recognise → produce → repeat. This app does both — words are saved from
reading *and* the list is frequency-ordered — so `Sõnavara` belongs where
`Rada` is: in the mode about learning, next to the reading it draws from.

One caution from the same research, which applies to us directly: LingQ uses
four status levels and users report that as **already too granular to judge**.
This app has five — `õpin`, `tuttav`, `tean`, `eiran`, `teadsin ammu` — and only
one distinction is load-bearing, the three that count as *settled*. Worth
revisiting before adding a sixth.

## Progress, per section

Different sections deserve different measures, and forcing one number on all of
them is how progress bars start lying.

| Section | Measure | Why this one |
|---|---|---|
| **Rada** | topics mastered / total, plus current position | Mastery is binary per topic; a percentage of a syllabus is honest. |
| **Sõnavara** | words known within each frequency band | Speakly's insight: "1 200 of the top 2 000" means something; "12 % of Estonian" does not. |
| **Kordamine** | due today, and retention | The FSRS numbers already exist. |
| **Lugemine · Kuulamine** | texts read, dictations taken and words heard correctly | Exposure counts and should not pretend to be mastery — but dictation *is* scored, so it is reported separately from minutes played. |
| **Eksam** | per-part readiness | The exam scores four parts separately and fails you for a zero in any. |

**No single "overall progress" number.** Four skills scored separately, with a
zero in any one failing the exam, is precisely a case where one aggregate number
hides the thing that matters.

## Roadmap display

The path shows topics in prerequisite order with three states — **locked**
(prerequisites unmet), **available**, **mastered** — plus a *test out* affordance
on every available topic, so known material can be skipped without pretending to
study it.

Prerequisites come from the topic graph, not a hand-written order: `gen-stem`
genuinely precedes eleven other cases, so the path can be *derived* and stays
correct when topics are added.

## Built

Three things only became clear once it was — and the fourth is a correction to
the third, which stood here as fact for a fortnight after it stopped being one:

- **`public_only` currently returns 0 of 421 items.** ERR material is © ERR and
  Selges keeles carries no reuse grant, so every harvested item is owner-only.
  The filter is not decorative — it is the whole reason Cloudflare Access is a
  requirement rather than a nicety.
- **Frequency ranks are not dense.** The top-500 band holds 304 lemmas, not 500,
  so bands report their real size rather than the width of their range.
- **A topic with no generator cannot gate.** A real prerequisite with no
  practice behind it, required to be demonstrated, makes everything downstream
  unreachable. Such topics show as `reference` and do not block; see
  `curriculum-plan.md` step 3.
- **`pohivormid` is no longer one of them.** It was the standing example above,
  and on 2026-08-21 it got a generator — the three principal forms, built from
  `object_cases`. So it stopped being a free pass and became the gate it was
  always declared to be: `gen-stem` now waits for it. `lauseehitus` and ten
  others are still reference topics. **The set is derived from
  `progress.reference_topics()`, never listed** — a test that hand-kept
  `{"pohivormid", "lauseehitus"}` went stale the moment this landed, which is
  exactly the failure the derivation rule exists to prevent.

## Sources checked and set aside

Completing the sweep, so these are not rediscovered as if new:

- **`word_meanings_et`** — fetched and inspected. Word→definition pairs, but the
  vocabulary is C1 (`poolvääriskivi`, `karmikoeline`). Wrong level; not used.
- **`exam_et`** — gated on Hugging Face (401). Not accessible.
- **Keelekõdi transcripts** — do not exist; the pages carry a series blurb only.
- **ERR Lihtsad uudised** — body is client-rendered with no reachable API, and
  a headless browser cannot reach ERR hosts from this environment.
