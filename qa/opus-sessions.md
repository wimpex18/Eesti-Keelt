# Opus 5.5 sessions

Ready-to-paste briefs for separate Claude Opus 5.5 sessions (ADR-0009). Each
names the files it may change, so two sessions never edit the same file
(`AGENTS.md`: parallel sessions only when the owner asks, on files no other
session edits). Replace a brief when its work is done.

Every brief starts with: read `AGENTS.md`, `HANDOFF.md`, `git status`,
`docs/status.md` and the ADRs it names; one branch and one PR; no new Linear
issues (comment on the named one); update `HANDOFF.md` before each commit; the
fast suite green, and the browser journeys on both engines after any change to
`eesti/web/`. There is no human reviewer: material passes the automatic checks
in ADR-0009 and is labelled; an Estonian form comes from Vabamorf or a cited
source, never from the model; a contrast claim needs a published source.

## 1. Material pipeline (DEV-36) — do first

```text
Grove: build the material pipeline of ADR-0009 (Linear DEV-36). Files:
eesti/material/ (new), eesti/cli/ material commands, tests/test_material*.py,
docs/ (pipeline section). Read ADR-0004, ADR-0009, eesti/comprehension.py,
eesti/phrases.py, eesti/units.py, docs/course-structure.md.
Build: a JSON schema for dialogues and reading texts (speakers, turns,
questions with answer spans, off-list words); `cli material check` running the
gates in order (Vabamorf on every token with guess=False and spellcheck; content
lemmas within the stage's EKI level, at most 3 glossed exceptions; form tags only
from topics the unit has introduced; answers verbatim once; one-right-answer for
any gap); `cli material blind` asking Haiku 5.5 (Batch API) to answer each
question without the key and without the text, dropping guessable or
disagreeing items; storage of passed drafts as committed
content/material/checked/<unit>/<slug>.json, built into content.db as a public
source with id `mat:<unit>:<slug>@<sha8>`, labelled "written with a model,
checked by Vabamorf and automatic checks"; a `Teata veast` report route and
item answer statistics that retire items. Never store an answer key a model
wrote without the gates. Comment on DEV-36.
```

## 2. Unit dialogues and texts (after 1)

```text
Grove: draft dialogues and reading texts for units 2–10 with the material
pipeline (DEV-36). Files: content/material/ only. Read docs/course-structure.md,
eesti/units.py, eesti/phrases.py (EKI's A1 exchanges), Sõnaveeb's A2/B1 phrase
collections (credited), ADR-0009. Per unit: one dialogue of 6–10 turns and one
text of 80–150 words on its HARNO topic, built on EKI's exchanges for that
situation, lemmas within the A1 list, grammar only from topics introduced so far,
five questions each whose answers appear verbatim once. Use Opus 5.5 at effort
high through the Batch API with a cached system prompt; run `cli material check`
and `cli material blind` until they pass; keep a log of rejected drafts and why.
Label every file with engine and prompt version.
```

## 3. Interactive rules (rule by doing)

```text
Grove: make the Reegel page teach by doing, starting with obj-case and osaalus
(ADR-0009 step 2). Files: eesti/rulewalk.py (new), eesti/lessontext.py (walk
data only), eesti/web/js/lesson.js, tests/test_rulewalk.py. Read eesti/lessons.py,
eesti/drills.py, eesti/existential.py, eesti/grammar.py, EKK SÜ 35/38/40.
Shape: a walk of steps — notice (2–4 examples from Vabamorf or a quoted EKK
example), ask (a generator spec keyed by code at run time), explain (≤40 words in
the explanation language, citing its section), contrast (the wrong/right pair).
On #rule/obj-case the learner toggles completed/ongoing, negation, plural,
imperative, impersonal and watches the object form change, every form from
Vabamorf. Model-written prose is labelled; any Estonian string not from code or
the cited source is rejected (tutor._grounded as a second gate). Keyboard and
screen reader complete; a reduced-motion version.
```

## 4. Explanation languages (DEV-42)

```text
Grove: make English and Ukrainian explanation languages beside Russian (DEV-42).
Files: eesti/i18n/ (new catalogue), the call sites that read `why_ru`, `points_ru`,
`summary_ru`, tests/test_ui_language.py. Read qa/architecture-review.md
("Explanation languages"), ADR-0009, eesti/lessontext.py, eesti/drills.py.
Build: a catalogue keyed by stable rule/message ids with per-language text and
status; items and new events carry rule ids and parameters, old events keep
why_ru for replay; the profile's explanation_language is read; grounding in
tutor.py treats English as an explanation language. Fix one gloss per Estonian
term per language. Then contrast notes per rule and language in the shape the
DEV-42 comment gives (id, rule_id, lang, effect, text, examples, evidence,
sources, status), shipping only notes with a published source (Keelehärm 2003,
Külmoja et al. 2003, Heinsoo for Ukrainian, Erelt's Estonian Language for
English) — a Ukrainian note written for Ukrainian speakers, never translated
from the Russian. Unsourced tips in lessontext.py move into this shape or go.
```

## 5. Generators the units lack

```text
Grove: add generators the course map names as missing (DEV-40). Files:
eesti/modals.py, eesti/negation.py, eesti/future.py (new), eesti/conjugation.py
(attested frames), eesti/evs.py (question cues), tests for each. Read
docs/course-structure.md ("What each unit still needs"), eesti/evs.py,
eesti/cloze.py, the DEV-40 research comment.
Build, each keyed by Vabamorf or EKI and with one right answer: negation beyond
present and past (conditional, imperative 2pl, impersonal, perfect); modal verbs
with their infinitive from EVS phrases (võima/saama/tohtima + da, pidama + ma),
dropping verbs EVS shows with both; tulevik (present after a future adverbial;
hakkama + ma), never grading "saab olema"; conjugation and imperative frames
drawn from EVS phrases with a unique Vabamorf reading, credited; the four
missing question-word cues from EVS's own question phrases. Add TOPIC_REFERENCES
for tulevik, and give units 17 and 28 a check.
```

## 6. HARNO task types (DEV-41)

```text
Grove: generate HARNO B1 reading and listening task types keyed by code
(DEV-41), A2 after. Files: eesti/harnotasks.py (new), eesti/mock.py,
eesti/web/js/mock.js, tests. Read docs/exam-native.md, ADR-0009 (exam loops),
the DEV-41 research comment (task types per part).
Build on checked material (session 1): B1 reading 3 (three-option gaps,
distractors other Vabamorf forms of the same lemma), B1 reading 4 (removed
phrases from a larger bank), listening 1 (numbers, times, prices, dates by TTS
with two voices), listening 3 (short answers, accepted as a Vabamorf lemma set);
each mock part then has a review screen (answer, key, evidence span, the topic
behind the miss) and "Harjuta neid" practice re-tested 1–6 days later.
```

## 7. Design system and motion (documents)

```text
Grove: write the design and motion spec for the redesign; documents only.
Files: DESIGN.md, docs/design-research.md. Read DESIGN.md, PRODUCT.md,
docs/design-research.md, eesti/web/app.css, ADR-0009. Screenshot Kodu, Kursus,
#session and #rule at 390 and 1280 px, light and dark. Keep Practice rhythm unless
a change is justified; list the forbidden defaults by name (cream backgrounds,
italic accent words, numbered section labels, monospace labels, pill buttons);
one fixed primary action per screen; motion for feedback and state only, each
with purpose, duration, easing and reduced-motion and forced-colours fallbacks;
WCAG 2.2 AA contrast table; focus never hidden by the phone's skill tray. A
separate reviewer session scores the result on design quality, originality,
craft and function before it is accepted.
```

## 8. The session and Home (after the exam loop)

```text
Grove: build the session and the next task of ADR-0009. Files: eesti/session.py
(new), eesti/api/ session routes, eesti/web/js/path.js and review.js (Home),
tests. Read ADR-0009, eesti/planning.py, eesti/units.py, eesti/unitcheck.py.
Build: the seven steps composed by code from the current unit and the evidence,
the weekly rotation, one Jätka with two alternatives and their reasons, the hint
and one retry with only the first attempt counting, words entering review after
their first correct recall, and the onboarding of ADR-0009 (first task within a
minute; sitting and notifications after the first session). Journeys for a new
beginner, a chosen start and an assessed start, both viewports.
```
