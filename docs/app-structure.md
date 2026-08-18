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

## The structure

```
Õppimine
├── Rada          the path — grammar topics in prerequisite order, mastery-gated
├── Sõnavara      vocabulary by frequency band, Speakly-style
└── Kordamine     FSRS review, cutting across everything above

Raamatukogu       the library — everything that is material, not curriculum
├── Lugemine      349 Estonian texts, by difficulty band
├── Kuulamine     44 audio-only episodes + TTS on any text
└── Saated        the radio courses: 28 lessons with transcripts

Eksam             timed, scored, real format
```

### Why a library rather than more path

**Keelekõdi is the case that forces the distinction.** Its episodes are ~30
minutes of mixed content — some grammar, some songs, some vocabulary — with no
transcript. That is genuinely useful *exposure*, and genuinely useless as a
*curriculum step*: it cannot be sequenced, gated on, or checked.

Putting it on the path would break the path's one promise, which is that
finishing a step means something. So the split is:

| | Path | Library |
|---|---|---|
| ordered | yes, by prerequisite | no, browse freely |
| gated | yes, on mastery | never |
| measurable | pass/fail per topic | exposure only |
| examples | täissihitis, past tenses | Keelekõdi, news texts, podcasts |

A learner who wants a plan follows the path. A learner who wants to *soak* opens
the library. Conflating them is what makes course apps feel either rigid or
aimless.

## Progress, per section

Different sections deserve different measures, and forcing one number on all of
them is how progress bars start lying.

| Section | Measure | Why this one |
|---|---|---|
| **Rada** | topics mastered / total, plus current position | Mastery is binary per topic; a percentage of a syllabus is honest. |
| **Sõnavara** | words known within each frequency band | Speakly's insight: "1 200 of the top 2 000" means something; "12 % of Estonian" does not. |
| **Kordamine** | due today, and retention | The FSRS numbers already exist. |
| **Raamatukogu** | texts read, minutes listened | Exposure counts, and should not pretend to be mastery. |
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

All of the above is implemented, and three things only became clear once it was:

- **`public_only` currently returns 0 of 421 items.** ERR material is © ERR and
  Selges keeles carries no reuse grant, so every harvested item is owner-only.
  The filter is not decorative — it is the whole reason Cloudflare Access is a
  requirement rather than a nicety.
- **Frequency ranks are not dense.** The top-500 band holds 304 lemmas, not 500,
  so bands report their real size rather than the width of their range.
- **A topic with no generator cannot gate.** `pohivormid` and `lauseehitus` are
  real prerequisites with no practice behind them, and requiring them to be
  demonstrated made everything downstream unreachable. They show as `reference`
  and do not block; see `curriculum-plan.md` step 3.

## Sources checked and set aside

Completing the sweep, so these are not rediscovered as if new:

- **`word_meanings_et`** — fetched and inspected. Word→definition pairs, but the
  vocabulary is C1 (`poolvääriskivi`, `karmikoeline`). Wrong level; not used.
- **`exam_et`** — gated on Hugging Face (401). Not accessible.
- **Keelekõdi transcripts** — do not exist; the pages carry a series blurb only.
- **ERR Lihtsad uudised** — body is client-rendered with no reachable API, and
  a headless browser cannot reach ERR hosts from this environment.
