# ADR-0009: The learning loop

**Status:** Accepted (owner, 9 Oct 2026). **Scope:** onboarding, the session, the
next task, exam preparation, speaking feedback, material written without a human
reviewer, and explanations in Russian, Ukrainian and English. Builds on ADR-0007
(units) and ADR-0008 (the Claude lane). Research behind it: Linear DEV-40 and
DEV-45 comments of 9 Oct 2026.

## Context

Klint has units, generators, checks and review, but a learner still picks tools
from menus. The owner wants one interactive path in which each completed step
leads to the next task — words, an exercise, a rule learned by doing, listening,
speaking — while every part stays reachable on its own, for learners with or
without Estonian and with different goals, explained in Russian, English or
Ukrainian. There is no teacher to review material: it must be built from
sources, models and checks that run on their own.

The evidence that shapes this: retrieval practice and spacing have the most
robust effects (Adesope et al. 2017, g≈0.5–0.6; Kim & Webb 2022); explicit rule
teaching beats implicit (Norris & Ortega 2000; Spada & Tomita 2010), and focused
grammar lessons beat grammar spread through themes (Duolingo in-house data);
corrective prompts that ask for self-correction beat recasts (Lyster & Saito
2010); dialogue practice with a system helps speaking (g≈0.6 across studies),
but LLM conversation without form-focused support does not improve accuracy;
interleaving helps confusable rules and hurts word learning (Brunmair & Richter
2019); exam familiarity is necessary but exam-only courses add little (Green
2007); AI writing feedback helps moderately and fades without follow-up.

## Decision

### Onboarding

The first task within a minute: explanation language → goal (everyday life,
work, A2 exam, B1 exam) → starting point (none: unit 1; some: choose a stage;
unsure: an adaptive check of at most 12 code-graded items that places by unit)
→ sessions a week. The exam sitting and notifications are asked after the first
session, never before. Skipped units stay navigation, never mastery.

### The session

About 20–30 minutes, built by code from the current unit and the evidence:

1. **Review** — due cards and yesterday's mistakes, mixed, at most 5 minutes.
2. **Rule by doing** — 6–10 items whose meaning depends on the form; the learner
   chooses first, then the rule appears (EKK-sourced, in the explanation
   language).
3. **Guided practice** — blocked, then mixed with the contrasting rule; a miss
   gets one retry with a hint, then the answer and *Miks?*. Only the first
   attempt counts for mastery and FSRS.
4. **Words** — the unit's words in sentences; a word enters review after its
   first correct recall.
5. **Listening** — a gap-fill or questions on a heard text, transcript after.
6. **Speaking** — shadowing, then a short task; the learner confirms the
   transcript; feedback is the model's, labelled, after the turn.
7. **Exit check** — 3–5 code-graded items.

Across a unit's five sessions the emphasis rotates: rules → words and listening
→ a speaking task → reading and writing → the unit check.

### The next task

Deterministic and explainable, like `eesti/planning.py`: review first when the
due queue is long (capped); remediation with fresh items after a failed check;
otherwise the next step of the path, preferring the skill practised least
recently; with a sitting chosen and near, a growing share of exam-format tasks.
Home shows one *Jätka* and two alternatives, each with a one-line reason. Every
step is reachable on its own (grammar, words, listening, speaking, exam), and
work done there counts in the same records.

### Exam preparation

Each part is a loop: **simulation** on the real clock and order (listening heard
twice, no dictionary, spellcheck off) → **review** of every item with the
learner's answer, the key and the evidence in the text or transcript → **practice**
of that task type and of the grammar behind each miss, re-tested one to six days
later. B1 first, then A2 reusing the generators. Writing gets a code checklist
(length, each content point, opening and closing, unknown words, deterministic
grammar checks) and then the model's labelled feedback against HARNO's published
descriptors, quoting the learner's text, never a score. Speaking is never scored.
Readiness shows task types covered and keyed evidence per part, and flags a part
with none; no pass probability. An *Eksamipäev* page states the day's rules from
HARNO's information sheet.

### Speaking

Recognition (the home service, then Workers AI) → the learner confirms the
transcript → Haiku's advisory feedback (ADR-0008). Morphology feedback is
withheld or labelled when the transcript came from the fallback recogniser,
which keeps few planted errors. No pronunciation or quantity score until
validated criteria exist (ADR-0005).

### Material without a human reviewer

ADR-0004 stands: a model may write material; only code may key it. Material is
built from sources first (EKI phrase collections, EVS examples, Vabamorf forms),
and model drafts pass, in order:

1. structured output against a schema;
2. deterministic gates — every token a form Vabamorf knows, every content lemma
   within the stage's EKI word level, every keyed form round-tripped, **one right
   answer** (every other form of the gap word is generated and must not fit),
   reading answers verbatim and once in the text, no duplicates;
3. independent blind checks — a second model answers each item without the key,
   and again without the text; disagreement or a guessable item drops it;
4. a label: *written with a model, checked by Vabamorf and automatic checks*,
   with the engine and prompt version;
5. after release, learners' *Teata veast* reports and answer statistics retire
   items whose answers split or never vary.

Explanations follow the same rule: grounded in a cited EKK or Teatmik section,
Estonian forms from code, labelled as model-written. An L1 contrast note ships
only when a published grammar or learner study backs it; an unsourced claim is
never shown.

### Explanation languages

Russian, English and Ukrainian, with Estonian material, keys and progress shared
(DEV-42). Contrast notes are per language and per rule — a Ukrainian note is
written for Ukrainian speakers, never translated from the Russian. Terminology is
fixed per language in the catalogue (one Russian gloss per Estonian term).

## Consequences

- Home becomes the session; Kursus, the skills and Eksam become the places to
  go back to. The redesign inherits the session's steps and states.
- Material can grow without a reviewer, at the cost of a narrower set of item
  types (those code can key and a blind check can confirm) and an honest label.
- `eesti/lessontext.py`'s tips that name "the mistake a Russian speaker
  typically makes" are unsourced; they move into sourced contrast notes.
- Exam work before the 7–8 Nov 2026 sittings comes before the session flow.
