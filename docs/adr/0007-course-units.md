# ADR-0007: Units over topics

**Status:** Accepted (owner interview, 9 Oct 2026). **Scope:** the A0→B1
course (Linear DEV-40). Specification: `docs/course-structure.md`.

## Context

The course was a prerequisite graph of grammar topics (`eesti/curriculum.py`)
with a mastery gate. That orders grammar soundly, but it gives a beginner no
greetings, numbers or sounds. It also has no communicative goal, no words,
dialogue or skill work tied to the grammar, and no weekly rhythm towards an
exam sitting. Learners use Grove alongside Keeleklikk and Keeletee, whose
courses are organised in units, and HARNO examines by topic.

## Decision

1. **A unit is a data layer over topics, not a replacement for them.**
   `eesti/units.py` declares thirty one-week units in four stages (`algus`,
   `A1`, `A2`, `B1`). Each unit names its core topics, any revisited
   sub-rules of earlier topics, its HARNO topics and its companion
   Keeleklikk/Keeletee unit. Topic ids, rule pages, the mastery gate and FSRS
   stay as they are (ADR-0005).
2. **Every topic has exactly one home unit**, and the unit order respects the
   prerequisite graph. Both are tested. New topics are added, never renamed:
   `fraasid`, `arvud` and `osaalus` join the 43.
3. **Completion is checked.** A unit is complete when its core topics are
   mastered or tested out and its unit check (code-graded, five items per core
   topic and revisited rule) is passed. Reading, listening, speaking and writing
   tasks are offered and recorded, never block, and can be skipped. Skips are
   navigation, never mastery or readiness.
4. **Stages are sourced targets, not levels.** A stage is where EKI's grammar
   profile and HARNO's topic lists put the unit's content, shown as a target.
   `level` stays reserved for official HARNO/EIS material. The first stage is
   *Algus*, because A0 is not a CEFR level.
5. **Placement moves by unit.** A chosen start skips the units of earlier
   stages; the assessment places the learner at the first unit with a core
   topic it did not pass. Both are navigation, never mastery.
6. **One queue, one next action.** Unit words and misses join the single FSRS
   queue. Home shows the current unit's next session. Exam keeps mocks and
   readiness; from A2, units end with a HARNO-format task once DEV-41 builds
   the types.
7. **Homework and the weekly plan are pure functions of the evidence**, like
   `eesti/planning.py`: they say whether the pace fits a chosen sitting, and
   never estimate a pass.
8. **Companion courses are linked, never rehosted.** Keeleklikk and Keeletee
   course maps are public; their lessons need a free account.
9. **Dialogues and texts come from the material pipeline** (ADR-0004 shape):
   a model drafts, Vabamorf verifies, lemmas stay within the stage's EKI word
   level, a person reviews and code keys. The material is labelled.

## Consequences

- The course can grow by units without changing learner progress: progress
  remains per topic, and unit state is derived from it plus unit-check events.
- Adding topics at the start of the path must not pull existing learners
  back. Replaying the onboarding event re-applies a chosen start by stage, so
  the first week is skipped for learners who started at A1 or above; and the
  first week leads the next step only for a learner who has mastered nothing
  beyond it, without recording a skip (owner, 9 Oct 2026). The learner can
  also skip any unit, or every unit before a chosen one, and put them back.
- Two sub-rules sit above their stage in EKI's profile and are labelled so:
  the *da*-infinitive object (EKI B2; taught from EKK SÜ 40 and the Teatmik)
  and the plural partitive subject (EKI B2). Their units say so.
- Unit content that lacks licensable material is visible as such
  (`docs/course-structure.md`, "What each unit still needs"); no generator
  is invented to fill a unit (ADR-0005).
- EKI sources whose audio and images carry no stated licence (the
  *e-hääldusharjutused*, the picture dictionary) are used as credited text
  only; the audio played is EKI's CC BY 4.0 PSV recordings.

## Not decided here

The unit page layout, the weekly plan's screen and homework's surface belong
to the redesign. This ADR fixes the identities, states and grading boundaries
it inherits.
