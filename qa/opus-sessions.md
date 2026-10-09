# Opus 5.5 sessions

Ready-to-paste briefs for separate Claude Opus 5.5 sessions (ADR-0009). Paste
one brief into a new session; each brief tells the session to follow "Every
session first" below. Replace a brief when its work is merged.

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
   never in a checkout another session uses: the app's worktree, or
   `git fetch origin && git worktree add "../Eesti Keelt-<brief>" -b claude/<brief-slug> origin/main`.
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

## Waves and file ownership

Merge PR #125 before starting any session: every branch starts from `main`.

| Wave | Session | Owns | Shared, add only |
|---|---|---|---|
| 1 | S1 material pipeline | `eesti/material/`, `eesti/cli/material.py`, `eesti/api/reports.py`, `tests/test_material*.py`, `docs/material.md` | `eesti/cli/__init__.py`, `eesti/api/__init__.py`, `eesti/licences.py`, `docs/identity.md`, `docs/sources.md` |
| 1 | S5 generators the units lack | `eesti/modals.py`, `eesti/negation.py`, `eesti/future.py`, `eesti/conjugation.py`, `eesti/evs.py`, their tests | `eesti/curriculum.py`, `eesti/practice.py`, `eesti/grammar.py`, `eesti/unitcheck.py`, `eesti/itemref.py`, `docs/curriculum.md`, `docs/course-structure.md` |
| 1 | S6 HARNO B1 task types | `eesti/harnotasks.py`, `eesti/mock.py`, `eesti/web/js/mock.js`, `tests/test_harnotasks.py` | `eesti/api/exam.py` |
| 1 | S7 design and motion | `DESIGN.md`, `docs/design-research.md` | — |
| 2 | S2 unit dialogues and texts | `content/material/` | — |
| 2 | S3 interactive rules | `eesti/rulewalk.py`, `eesti/web/js/lesson.js`, `tests/test_rulewalk.py` | `eesti/lessontext.py` (walk data) |
| 2 | S9 dictionary | `eesti/dictionary.py`, `eesti/api/dictionary.py`, `eesti/web/js/dictionary.js`, `eesti/web/js/words.js`, `tests/test_dictionary*.py` | `eesti/web/index.html`, `eesti/web/js/router.js`, `docs/identity.md` |
| 3 | S8 session, Home and Haiku in the app | `eesti/session.py`, `eesti/api/session.py`, `eesti/web/js/path.js`, `eesti/web/js/review.js`, `eesti/web/js/onboarding.js`, `eesti/tutor.py`, tests | `eesti/web/index.html`, `eesti/web/js/router.js` |
| 4 | S4 explanation languages | `eesti/i18n/`, the call sites that read `why_ru`, `points_ru`, `summary_ru`, `tests/test_ui_language.py` | — (run it with no other session open) |

Every session may add its row to `docs/status.md` and its own
`qa/sessions/<branch>.md`. Wave 2 starts when S1 is merged (S2 needs its
checks); S4 touches many call sites, so it runs alone, last.

## Merging (owner)

1. Optional, once: in GitHub, Settings → Branches → `main` → require status
   checks to pass and branches to be up to date before merging. Every PR is
   then tested against the `main` it lands on, which catches two PRs that pass
   alone and break together.
2. Merge one PR at a time. The other open PRs then fall behind `main`: tell
   each session "sync with main", or let Auto-fix do it. A conflict can only be
   in a shared file, and its rule is to keep both sides.
3. After a wave, one short session refreshes `HANDOFF.md` and `docs/status.md`
   from the merged `qa/sessions/` notes and deletes them.

## S1. Material pipeline (wave 1, first)

```text
Grove S1: build the material pipeline of ADR-0009. Follow "Every session first"
in qa/opus-sessions.md; your files are listed there under S1.
Read ADR-0004, ADR-0009, eesti/comprehension.py, eesti/phrases.py,
eesti/units.py, docs/course-structure.md.
Build: a JSON schema for dialogues and reading texts (speakers, turns,
questions with answer spans, off-list words); `cli material check` running the
gates in order (Vabamorf on every token with guess=False and spellcheck; content
lemmas within the stage's EKI level, at most 3 glossed exceptions; form tags only
from topics the unit has introduced; answers verbatim once; one right answer for
any gap); `cli material blind` asking Haiku 5.5 (Batch API) to answer each
question without the key and without the text, dropping guessable or
disagreeing items; storage of passed drafts as committed
content/material/checked/<unit>/<slug>.json, built into content.db as a public
source with id `mat:<unit>:<slug>@<sha8>`, labelled "written with a model,
checked by Vabamorf and automatic checks"; a `Teata veast` report route and
item answer statistics that retire items. Never store an answer key a model
wrote without the gates.
```

## S2. Lessons: unit dialogues and texts (wave 2, after S1)

```text
Grove S2: draft dialogues and reading texts for units 2–10 with the material
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

## S3. Interactive rules (wave 2)

```text
Grove S3: make the Reegel page teach by doing, starting with obj-case and
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
screen reader complete; a reduced-motion version.
```

## S4. Explanation languages (wave 4, alone)

```text
Grove S4: make English and Ukrainian explanation languages beside Russian.
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
move into this shape or go.
```

## S5. Exercises: generators the units lack (wave 1)

```text
Grove S5: add the generators the course map names as missing. Follow "Every
session first" in qa/opus-sessions.md; your files are listed there under S5.
Read docs/course-structure.md ("What each unit still needs"), eesti/evs.py,
eesti/cloze.py.
Build, each keyed by Vabamorf or EKI and with one right answer: negation beyond
present and past (conditional, imperative 2pl, impersonal, perfect); modal verbs
with their infinitive from EVS phrases (võima/saama/tohtima + da, pidama + ma),
dropping verbs EVS shows with both; tulevik (present after a future adverbial;
hakkama + ma), never grading "saab olema"; conjugation and imperative frames
drawn from EVS phrases with a unique Vabamorf reading, credited; the four
missing question-word cues from EVS's own question phrases. Add TOPIC_REFERENCES
for tulevik, and give units 17 and 28 a check.
```

## S6. Exam: HARNO B1 task types (wave 1)

```text
Grove S6: generate HARNO B1 reading and listening task types keyed by code, A2
after; the sittings are 7–8 Nov 2026. Follow "Every session first" in
qa/opus-sessions.md; your files are listed there under S6. Read
docs/exam-native.md, ADR-0009 (exam loops), eesti/writingtasks.py,
eesti/examday.py, eesti/mock.py.
Start with what needs no new material: listening 1 (numbers, times, prices,
dates by TTS with two voices), listening 3 (short answers, accepted as a
Vabamorf lemma set) and reading 3 (three-option gaps on the existing reading
corpus, distractors other Vabamorf forms of the same lemma); reading 4 (removed
phrases from a larger bank) on S1's checked texts once merged. Each mock part
then has a review screen (answer, key, evidence span, the topic behind the miss)
and "Harjuta neid" practice re-tested 1–6 days later.
```

## S7. Design system and motion (wave 1, documents)

```text
Grove S7: write the design and motion spec for the redesign; documents only.
Follow "Every session first" in qa/opus-sessions.md; you own DESIGN.md and
docs/design-research.md. Read PRODUCT.md, eesti/web/app.css, ADR-0009.
Screenshot Kodu, Kursus, #session and #rule at 390 and 1280 px, light and dark.
Keep Practice rhythm unless a change is justified; list the forbidden defaults
by name (cream backgrounds, italic accent words, numbered section labels,
monospace labels, pill buttons); one fixed primary action per screen; motion for
feedback and state only, each with purpose, duration, easing and reduced-motion
and forced-colours fallbacks; WCAG 2.2 AA contrast table; focus never hidden by
the phone's skill tray; how the screens become an iOS app later. A separate
reviewer session scores the result on design quality, originality, craft and
function before it is accepted.
```

## S8. The session, Home and Haiku in the app (wave 3)

```text
Grove S8: build the session and the next task of ADR-0009, with Haiku 5.5 as
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
viewports.
```

## S9. Dictionary (wave 2)

```text
Grove S9: build the learner's dictionary (Sõnastik) on the shared word card.
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
names its sources. Search, the entry and the card work at phone width.
```
