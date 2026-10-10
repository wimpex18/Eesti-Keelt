# Opus 5.5 sessions

Briefs for separate Claude Opus 5.5 sessions (ADR-0009), in the order they run.
To start one, open a new session and write one line:

```text
Run <ID> from qa/opus-sessions.md.
```

with `<ID>` from "Progress and order" below (for example `S10`). Nothing else
needs pasting.

## How a session starts

A session told to run `<ID>` reads, in this order: "Who does what", "Every
session first", the `<ID>` row of "Progress and order" (and checks that
everything in its "Starts after" column is done: merged on `origin/main`; if
not, it stops and says so), its row in "File ownership", and the `<ID>` brief
at the end of this file. It does not need the other briefs. In its own PR it
sets its own row's status to "done in PR #<n>", touching no other row; the row
reads done on `main` once the owner merges.

## Progress and order

Steps run in order; sessions in one step may run at the same time, each in its
own worktree. A step starts when everything in "Starts after" is done.

| Step | ID | Session | Starts after | Status |
|---|---|---|---|---|
| 0 | S1 | Material pipeline | — | done in PR #128 |
| 0 | S5 | Generators the units lack | — | done in PR #129 |
| 0 | S6 | HARNO B1 task types | — | done in PR #130 |
| 0 | S7 | Design and motion spec, rename to Klint | — | done in PR #131 |
| 1 | S7R | Independent review of the design spec (read only) | S7 | done, review on PR #131 |
| 1 | S2 | Unit dialogues and texts | S1 | done in PR #133 |
| 1 | R1 | Refresh after step 0 | S7 | done in PR #132 |
| 2 | S7F | Apply the S7R review | S7R | done in PR #132 |
| 3 | S10 | Redesign: tokens and shell | S7F | done in PR #134 |
| 4 | S3 | Interactive rules (Reegel) | S10 | done in PR #136 |
| 4 | S9 | Dictionary (Sõnastik) | S10 | done in PR #137 |
| 5 | R2 | Refresh after steps 1–4 | S2, S3, S9, S10 | done in PR #138 |
| 6 | S8 | Session, Täna and Haiku in the app | S3, S9, R2 | done in PR #139 |
| 7 | R3 | Refresh after step 6 | S8 | waits |
| 8 | S4 | Explanation languages (alone: no other session open) | R3 | waits |
| 9 | R4 | Refresh after step 8 | S4 | waits |
| 10 | S11 | Beyond the generic exercise: a discussion with the owner | R4 | waits |

Why this order: the tokens and the shell (S10) came first because every
redesigned screen stands on them; S8's session uses S3's rule walk for its
"rule by doing" step; S4 rewrites call sites across the app, so it runs alone
after the build sessions; S11 then discusses the exercise and the screens with
the owner on the finished app.

## Who does what

- **Opus 5.5 builds, offline:** lessons (unit dialogues and texts), exercises
  (generators and checked material), the dictionary, interactive rules and
  explanations in Russian, English and Ukrainian. Its drafts pass the automatic
  checks of ADR-0009 and carry a label; an Estonian form comes from Vabamorf or
  a cited source, never from the model.
- **Haiku 5.5 helps in the app, at answer time** (ADR-0008): explains a miss or
  a rule in the learner's language, comments on writing and speaking against
  HARNO's descriptors, plays the conversation partner. Its words are labelled
  as a model's.
- **Code grades.** Whether a drill answer is right comes from Vabamorf and the
  item's key, never from a model: Haiku catches 10/10 planted errors but only
  11/40 real learner errors (9 Oct 2026), so a model verdict would sometimes
  mark a right answer wrong. Mastery and review follow code alone.

## Every session first

```text
Before anything else, in this order:
1. Work in your own git worktree on a new branch from the latest origin/main,
   never in a checkout another session uses: the app's worktree, or, from the
   main checkout,
   `git fetch origin && git worktree add ".claude/worktrees/<brief>" -b claude/<brief-slug> origin/main`.
   Every worktree lives inside the project in `.claude/worktrees/`, which git
   ignores; never create one beside the project folder, and never move or
   rename one by hand (git loses track of it; use `git worktree move`). The
   next refresh removes it once merged.
   In it run `python -m eesti.cli worktree-data "<path of the main checkout>"`
   (reference data only, never the owner's learning history or recordings).
2. Read AGENTS.md, docs/status.md, the ADRs your brief names, and
   qa/opus-sessions.md. Edit only the files your brief owns. In the shared
   files listed there, only add, in the sorted or natural place, never at the
   very end of a list, and never reorder or reformat. If you need any other
   file changed, stop and say so in your PR description.
3. Your handoff note is qa/sessions/<branch>.md (≤30 lines), not HANDOFF.md.
   Linear is paused: follow-ups go in the PR description and that note.
4. No new dependencies. No secrets in chat or commits.
5. Tests first. Before every push: `git fetch origin && git merge origin/main`
   (or the app's sync with the base branch); in a shared file keep both sides
   of a conflict; bump GENERATOR_VERSION to one above main's if both changed
   it. Then the fast suite, and the browser journeys on both engines after any
   change to eesti/web/.
6. One PR titled "[S<n>] <title>", listing the files you changed. The owner
   merges.
There is no human reviewer: material passes the automatic checks of ADR-0009
and is labelled; a contrast claim needs a published source.
```

## Redesign sessions

Sessions that build screens (S8; earlier S10, S3 and S9) work to `DESIGN.md`.
Its **Fixed and open** section says what every screen must keep and what is a
reviewed starting point. Bring the best design judgment the session has: your
own, and a front-end design skill if one is available. Where you see a simpler,
more useful or more beautiful solution than the spec's values, wireframes or
component looks, build it; keep every fixed rule; check it as the spec was
checked (screenshots at 390 and 1280 px in both themes, contrast computed with
the WCAG formula, the focus journey); and in the same PR update the spec's
section for your screen, with the reason in `docs/design-research.md`. A change
to a `PRODUCT.md` commitment is proposed in the PR, not made. The briefs name
outcomes; where they quote a value, it is the spec's proposal.

## File ownership

| ID | Owns | Shared, add only |
|---|---|---|
| R<n> | `HANDOFF.md`, `qa/sessions/`, the status cells of "Progress and order" | `docs/status.md`, `qa/architecture-review.md` |
| S8 | `eesti/session.py`, `eesti/api/session.py`, `eesti/web/js/path.js`, `eesti/web/js/review.js`, `eesti/web/js/onboarding.js`, `eesti/tutor.py`, tests; in `DESIGN.md` the Practice rhythm, Täna and session sections | `eesti/web/index.html`, `eesti/web/js/router.js`, `docs/design-research.md` |
| S4 | `eesti/i18n/`, the call sites that read `why_ru`, `points_ru`, `summary_ru`, `tests/test_ui_language.py` | — (no other session open) |
| S11 | `qa/competitor-review.md`; prototypes stay in its worktree until the owner picks one | `docs/design-research.md`; the `DESIGN.md` sections the owner agrees to change |

Every session may add its row to `docs/status.md`, set its own status cell
above, and write its own `qa/sessions/<branch>.md`.

## Merging (owner)

1. Optional, once: in GitHub, Settings → Branches → `main` → require status
   checks to pass and branches to be up to date before merging. Every PR is
   then tested against the `main` it lands on, which catches two PRs that pass
   alone and break together.
2. Merge one PR at a time, in the order of "Progress and order". The other open
   PRs then fall behind `main`: tell each session "sync with main", or let
   Auto-fix do it. A conflict can only be in a shared file, and its rule is to
   keep both sides.
3. After each refresh step (R1–R4) is merged, the next step's sessions start
   from an up-to-date `main`.
4. Session worktrees live in `.claude/worktrees/` inside the project (hidden in
   Finder; Cmd+Shift+. shows it). Leave them where they are: dragging one breaks
   git's link to it. The refresh removes merged ones; to remove one yourself,
   from the project folder: `git worktree remove ".claude/worktrees/<name>"`.

## R. Refresh after a step (R1–R4)

```text
Klint R<n>: fold the merged step into the shared notes. Read AGENTS.md,
qa/opus-sessions.md and every qa/sessions/*.md. Rewrite HANDOFF.md as the
present state (≤30 lines), bring docs/status.md and qa/architecture-review.md up
to date with what merged, move each session's open follow-ups (and any owner
operations they list, such as a one-off import) into HANDOFF.md or the relevant
doc, delete the merged qa/sessions/ notes, set the rows of merged sessions in
"Progress and order" to done with their PR numbers, remove the briefs of done
sessions from this file, remove the worktrees of merged sessions (each one in
`.claude/worktrees/` whose branch is merged into origin/main and whose `git -C
<worktree> status` is empty: `git worktree remove`, then `git branch -d` its
branch; if `git worktree list` marks one "prunable", find the folder and run
`git worktree repair <folder>` instead of pruning), and mark the next step
"ready". Fast suite green. One
branch and one PR titled "[R<n>] Refresh after step <n>"; Linear is paused.
```

## S8. The session, Täna and Haiku in the app (step 6)

```text
Klint S8: build the session and the next task of ADR-0009, with Haiku 5.5 as
the in-app helper. Follow "Every session first" in qa/opus-sessions.md; your
files are listed there under S8. Read HANDOFF.md's "For S8" list first: it
carries what S2, S3, S9 and S10 left for you. Read ADR-0008, ADR-0009,
eesti/planning.py, eesti/units.py, eesti/unitcheck.py, eesti/tutor.py,
eesti/providers/claude.py.
Build: the seven steps composed by code from the current unit and the evidence,
the weekly rotation, one Jätka with two alternatives and their reasons, the hint
and one retry with only the first attempt counting, words entering review after
their first correct recall, and the onboarding of ADR-0009 (first task within a
minute; sitting and notifications after the first session). Haiku in the app,
always labelled as a model and never deciding right or wrong: "Miks?" after a
miss explains it in the explanation language from the item's EKK section; a
question box on the rule page; advisory feedback on writing and speaking after
the code checklist, against HARNO's descriptors; the conversation partner.
Journeys for a new beginner, a chosen start and an assessed start, both
viewports. Onboarding's first question, the explanation language, is preselected
from the system or browser language (PRODUCT.md). Täna and the session keep
DESIGN.md's fixed rules: the item state machine, one primary action that does
not move between states, every result carried by a shape and a word as well as
colour, and the form named under the word only after an attempt. Its Täna and
session sections (the seven-step session line, beads, wireframes) are the
reviewed proposal; improve on them where you can ("Redesign sessions").
The owner finds the current exercise — a blank, a "?", a gap to fill — as
generic as a competitor's (docs/design-research.md, "Open: the exercise
itself"); its forms are redesigned after the S sessions. Build the state
machine and the rhythm on it, and keep the item's look easy to replace.
```

## S4. Explanation languages (step 8, alone)

```text
Klint S4: make English and Ukrainian explanation languages beside Russian.
Follow "Every session first" in qa/opus-sessions.md; run it with no other
session open. Read qa/architecture-review.md ("Explanation languages"),
ADR-0009, eesti/lessontext.py, eesti/drills.py.
Build: a catalogue (eesti/i18n/) keyed by stable rule/message ids with
per-language text and status; items and new events carry rule ids and
parameters, old events keep why_ru for replay; the profile's
explanation_language is read; grounding in tutor.py treats English as an
explanation language. Fix one gloss per Estonian term per language. Then
contrast notes per rule and language (id, rule_id, lang, effect, text,
examples, evidence, sources, status), shipping only notes with a published
source (Keelehärm 2003, Külmoja et al. 2003, Heinsoo for Ukrainian, Erelt's
Estonian Language for English) — a Ukrainian note written for Ukrainian
speakers, never translated from the Russian. Unsourced tips in lessontext.py
move into this shape or go. The default explanation language comes from the
system or browser (PRODUCT.md): the first of `navigator.languages` (iOS:
preferred languages) that is uk, ru or en, else en; preselected, changeable in
Profile, a saved choice always wins, location never used. (S8's onboarding
already preselects it and saves it; Profile has no switch yet.) Key every
interface label and gloss by a stable id, so the names S11 settles with the
owner (qa/naming.md) are a catalogue change. The page's `lang`
and every gloss's `lang` follow the chosen language; a missing reviewed
translation is shown as missing, never silently replaced by Russian.
```

## S11. Beyond the generic exercise (step 10, a discussion)

```text
Klint S11: a discussion with the owner first, then a build only of what the
owner picks. Klint's exercise (a sentence with a drawn blank and a "?") and
much of its look follow the same defaults as competitors built with the same
tools; the owner wants Klint clearly better in value, UX and UI, from the best
product design of the day. Follow "Every session first" in
qa/opus-sessions.md. Read qa/competitor-review.md and the screenshots and
recording it points to, docs/design-research.md ("Open: the exercise itself",
"Language-learning references"), DESIGN.md ("Fixed and open", Practice
rhythm, the session), PRODUCT.md, and use the app as it then is on a phone.
Bring to the owner: a short survey of the best learning and non-learning apps
of the time, seen first-hand where possible; your own view of the review's
directions, agreeing or not; three or four exercise concepts on real obj-case
items that make the learner produce a form without a drawn blank, each graded
by code with the first attempt counting; and the review's open questions.
Prototype only what the owner chooses, at 390 and 1280 px in both themes.
Record what is agreed in docs/design-research.md and the spec in DESIGN.md; a
change to a PRODUCT.md commitment is proposed, not made.

Since S8 the session (eesti/web/js/session.js) builds every item kind on one
state machine, and they all still look like the competitor's: a typed gap, a
choice between two forms, heard choices ("Kuula ja vali: ____"), a word
recalled into an EKI phrase, questions on a heard dialogue, dictation, tiles,
sentences to repeat, a spoken and a written task. On 11 October 2026 the
owner set a competitor's lesson (matching sentence halves, a paragraph of
drop-down gaps; qa/competitor-review.md) beside S8's screens and found the
same structure and approach. Cover each kind, not obj-case alone; keep the
state machine and the fixed rules, so a new look is a renderer in
session.js, not a new flow.

Names: the owner finds the app's names generic and close to competitors'
(sections, modes, steps, exercise types: Sõnastik, Vaba harjutus, Märka…).
qa/naming.md proposes names in Estonian, Russian and English from official
courses (Keeleklikk, Keeletee), HARNO, EKI, the CEFR's Estonian translation,
textbooks and learning apps. Bring it to the owner, record the chosen names
in DESIGN.md, and rename by stable id through S4's catalogue.
```
