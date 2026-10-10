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
| 4 | S9 | Dictionary (Sõnastik) | S10 | waits |
| 5 | R2 | Refresh after steps 1–4 | S2, S3, S9, S10 | waits |
| 6 | S8 | Session, Täna and Haiku in the app | S3, S9, R2 | waits |
| 7 | R3 | Refresh after step 6 | S8 | waits |
| 8 | S4 | Explanation languages (alone: no other session open) | R3 | waits |
| 9 | R4 | Refresh after step 8 | S4 | waits |
| 10 | S11 | Beyond the generic exercise: a discussion with the owner | R4 | waits |

Why this order: S10 builds the tokens and the shell every redesigned screen
stands on, so it follows the reviewed spec and precedes S3, S9 and S8; S8's
session uses S3's rule walk for its "rule by doing" step; S4 rewrites call
sites across the app, so it runs alone after the build sessions; S11 then
discusses the exercise and the screens with the owner on the finished app. S2
touches only `content/material/` and runs beside anything; start it early,
because the exam reading task 4 waits for its checked texts (sittings 7–8 Nov
2026).

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

S10, S3, S9 and S8 build screens to `DESIGN.md`. Its **Fixed and open**
section says what every screen must keep and what is a reviewed starting
point. Bring the best design judgment the session has: your own, and a
front-end design skill if one is available. Where you see a simpler, more
useful or more beautiful solution than the spec's values, wireframes or
component looks, build it; keep every fixed rule; check it as the spec was
checked (screenshots at 390 and 1280 px in both themes, contrast computed with
the WCAG formula, the focus journey); and in the same PR update the spec's
section for your screen, with the reason in `docs/design-research.md`. A change
to a `PRODUCT.md` commitment is proposed in the PR, not made. The briefs below
name outcomes; where they quote a value, it is the spec's proposal.

## File ownership

| ID | Owns | Shared, add only |
|---|---|---|
| S2 | `content/material/` | — |
| R<n> | `HANDOFF.md`, `qa/sessions/`, the status cells of "Progress and order" | `docs/status.md`, `qa/architecture-review.md` |
| S10 | `eesti/web/app.css`, `eesti/web/js/chrome.js`, `eesti/web/js/core.js` (the interlinear helper), `eesti/web/sw.js` (offline page), `eesti/api/assets.py` (manifest colours), `tests/test_shell.py`; in `DESIGN.md` the frontmatter and the sections for tokens and shell (Colors to Layout, Elevation and shape, The signature, Components, Motion, Focus and the dock, iOS, Migration) | `eesti/web/index.html`, `eesti/web/js/router.js`, `tests/test_e2e_journeys.py`, `docs/app-structure.md`, `docs/design-research.md` |
| S3 | `eesti/rulewalk.py`, `eesti/web/js/lesson.js`, `tests/test_rulewalk.py`; in `DESIGN.md` the Reegel section | `eesti/lessontext.py` (walk data), `docs/design-research.md` |
| S9 | `eesti/dictionary.py`, `eesti/api/dictionary.py`, `eesti/web/js/dictionary.js`, `eesti/web/js/words.js`, `tests/test_dictionary*.py`; in `DESIGN.md` the Word card section | `eesti/web/index.html`, `eesti/web/js/router.js`, `docs/identity.md`, `docs/design-research.md` |
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

## S2. Lessons: unit dialogues and texts (step 1)

```text
Klint S2: draft dialogues and reading texts for units 2–10 with the material
pipeline. Follow "Every session first" in qa/opus-sessions.md; you own
content/material/ only. Read docs/course-structure.md, eesti/units.py,
eesti/phrases.py (EKI's A1 exchanges), Sõnaveeb's A2/B1 phrase collections
(credited), ADR-0009. Per unit: one dialogue of 6–10 turns and one text of
80–150 words on its HARNO topic, built on EKI's exchanges for that situation,
lemmas within the A1 list, grammar only from topics introduced so far, five
questions each whose answers appear verbatim once. Use Opus 5.5 at effort high
through the Batch API with a cached system prompt; run `cli material check` and
`cli material blind` until they pass; keep a log of rejected drafts and why.
Label every file with engine and prompt version.
```

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

## S10. Redesign: tokens and shell (step 3)

```text
Klint S10: build steps 1 and 2 of DESIGN.md's Migration, the Interlinear
tokens and the app shell. Follow "Every session first" and "Redesign sessions"
in qa/opus-sessions.md; your files are listed there under S10. Read DESIGN.md in
full, docs/design-research.md, docs/brand.md, .claude/rules/web.md, PRODUCT.md,
and look at the current app at 390 and 1280 px, light and dark, before you
decide anything.
Outcomes. Tokens: the spec's roles in eesti/web/app.css for both themes, with
every old name a rule uses kept as an alias (Migration step 1 has the map), so
every unconverted screen still renders; type in rem; Estonian material and the
explanation language told apart by Geologica's two cuts; the decoration the
spec forbids gone (glass, washes, pill radii, uppercase labels, italics,
decorative motion); motion that answers the learner, with reduced-motion,
reduced-transparency, forced-colours and prefers-contrast fallbacks; the
manifest, theme-color and the offline page in sw.js on the new ground. Shell:
desktop navigation; a phone header with Veel; a phone bottom area that keeps
the four skills reachable, gives each screen one primary action in a place that
does not move, and never covers focus or the keyboard, in portrait and
landscape and inside the safe areas; the interlinear word as a CSS component
with a core.js helper whose form name comes only from the item's data. The
spec's dock states, sizes and wireframes are its proposal, reviewed by S7R;
improve on them where you can.
Tests: a focus-versus-dock journey at 390x844, 874x402 and 1280x800 on both
engines, with the keyboard cases through a visualViewport stub; the bottom
area's labels at 390 and 320 px in Russian, Ukrainian and English; the whole
journey suite on both engines. Every screen keeps working on the aliases; S3,
S8 and S9 rebuild their own screens.
```

## S3. Interactive rules (step 4)

```text
Klint S3: make the Reegel page teach by doing, starting with obj-case and
osaalus (ADR-0009 step 2). Follow "Every session first" in
qa/opus-sessions.md; your files are listed there under S3. Read
eesti/lessons.py, eesti/drills.py, eesti/existential.py, eesti/grammar.py,
EKK SÜ 35/38/40.
Shape: a walk of steps — notice (2–4 examples from Vabamorf or a quoted EKK
example), ask (a generator spec keyed by code at run time), explain (≤40 words in
the explanation language, citing its section), contrast (the wrong/right pair).
On #rule/obj-case the learner toggles completed/ongoing, negation, plural,
imperative, impersonal and watches the object form change, every form from
Vabamorf. Model-written prose is labelled; any Estonian string not from code or
the cited source is rejected (tutor._grounded as a second gate). Keyboard and
screen reader complete; a reduced-motion version. The page keeps DESIGN.md's
fixed rules: sources visible near the top, the gist from the topic's sourced
summary (never an entry of TIPS), one primary action (Harjuta). Its Reegel
section (a page with a back control, the form switch with the interlinear word)
is the reviewed proposal; improve on it where you can ("Redesign sessions").
```

## S9. Dictionary (step 4)

```text
Klint S9: build the learner's dictionary (Sõnastik) on the shared word card.
Follow "Every session first" in qa/opus-sessions.md; your files are listed
there under S9. Read eesti/lookup.py, eesti/evs.py, eesti/meaning.py,
eesti/wordlist.py, eesti/haaldus.py, eesti/licences.py, docs/sources.md.
An entry, found by any form (Vabamorf lemma): the headword with its EKI level
(the A1/A2/B1 list or an identified Ekilex estimate), part of speech, the forms
a learner needs from morph.case_forms (verbs: ma, da, b, s, nud, tud, takse),
EKI's PSV recording where there is one, EVS example phrases with their Russian,
and meanings in Russian, English and Ukrainian from EKI sources. Where no source
has a translation, a gloss drafted by a model is labelled as such and kept only
when a second model's blind back-translation agrees; never shown as a source's.
"Lisa kordamisse" uses the existing vocabulary and review path. Every entry
names its sources. Search, the entry and the card work at phone width. The
card keeps DESIGN.md's fixed rules; its Word card section (a sheet on phones,
the tapped form as an interlinear word) is the reviewed proposal; improve on it
where you can ("Redesign sessions").
```

## S8. The session, Täna and Haiku in the app (step 6)

```text
Klint S8: build the session and the next task of ADR-0009, with Haiku 5.5 as
the in-app helper. Follow "Every session first" in qa/opus-sessions.md; your
files are listed there under S8. Read ADR-0008, ADR-0009, eesti/planning.py,
eesti/units.py, eesti/unitcheck.py, eesti/tutor.py, eesti/providers/claude.py.
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
Profile, a saved choice always wins, location never used. The page's `lang`
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
```
