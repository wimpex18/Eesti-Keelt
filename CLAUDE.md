# Eesti-Keelt — working notes for a new session

Estonian A2/B1 exam preparation, built for one learner. Read `docs/` for the
reasoning; this file is what a fresh session needs in the first minute.

## Where the rest is written down

This file is the router. Each of these answers one question in full, and none
of it is repeated here.

| Read | For |
|---|---|
| `docs/status.md` | what works, what is missing, the known bugs and the tech debt — **read before planning a sprint** |
| `docs/lessons.md` | the habits this codebase paid for, grouped by what you are about to change |
| `docs/architecture.md` | how the modules fit together |
| `docs/app-structure.md` | the screens, the modes and the tabs, as built |
| `docs/ai-boundaries.md` | exactly what a model is and is not allowed to decide |
| `docs/deploy.md` | Cloud Run, the Worker, Access, and why it is neither a Worker nor a Container |
| `docs/curriculum-plan.md`, `docs/roadmap.md` | the syllabus, and why things were chosen |
| `docs/ui-language.md` | what has been audited against the language rule below, and the check that enforces it |
| `docs/redesign-2026.md` | the 2026 redesign: what changed on the page, and the specificity trap that cost three defects |
| `docs/qa-status.md` | what the browser suite covers and what it cannot see |

## Where things stand

**Version 1.0 closed 2026-08-20.** Read `docs/status.md` before planning a
sprint: it is the inventory of what works, the curriculum topics with no
generator, the known bugs and the tech debt.

**No exam is booked.** The 2026 A2 rehearsal was declined in favour of another
year of study; the sitting is planned for 2027, A2-then-B1 or B1-alone, and
`readiness.TARGET` is `None` until one is chosen. Do not reintroduce a
countdown to a date nobody has picked.

## What this is

A **learn → practise → check** loop, not a checker. Drills are *generated* from
a word list and a morphological analyser, not stored, so practice is unlimited
and every answer is gradeable without a network call.

The documented #1 weakness is `obj-case` — genitive vs partitive for completed
objects. Much of the design points at it.

## The one property that must not break

**Generation and grading are deterministic. No model decides whether an answer
is right or what to practise next.** A model is allowed to do exactly two
things: explain a correction in prose, and say what it heard in a recording.
Everything else — drills, grading, the study order, the mastery gate — is code.
See `docs/ai-boundaries.md`.

## Which language a string is written in

The learner is a **Russian speaker learning Estonian**. That single fact decides
every user-facing string, and getting it wrong is not cosmetic.

| Kind of text | Language | Why |
|---|---|---|
| UI labels — `Kirjutamine`, `Kuulamine`, `Rada` | **Estonian** | the interface is itself exposure, and these are the exam's own words |
| Grammar terms — `osastav`, `omastav`, `täisminevik` | **Estonian** | they must be learned; a translation would have to be unlearned |
| Everything explaining, warning, or justifying | **Russian** | this is where comprehension has to win |
| Estonian example sentences and drill content | **Estonian** | it is the material |

**The rule that makes it concrete: a caveat nobody can read is not a caveat.**
Two strings in this app exist to stop the learner drawing a wrong conclusion —
the pronunciation comparison ("a miss may be the recogniser, not your mouth")
and the readiness verdict ("this is not a prediction"). Both were written in
Estonian, and in Estonian they did the *opposite* of their job: the person they
protect could not read them, so a low score read as "my pronunciation is bad"
and a verdict read as a forecast.

When a Russian sentence names an Estonian concept, keep the Estonian word and
gloss it once: *"Говорение (rääkimine) оценить нельзя"*. That teaches the term
instead of hiding it.

A transliteration is not a gloss. `omastav` appeared as **омастав** in nine
explanation strings — a spelling that exists in no textbook, no dictionary and
no exam paper, so the learner can neither look it up nor recognise it when EKK
writes it. The tell was that the right Russian rendering, `основа генитива`,
was already sitting three lines above the prose that invented a second one.

## The three sections

Everything the learner does answers one of three questions, and every library
section belongs to exactly one (`library.MODES`):

| Mode | The question | What lives there |
|---|---|---|
| `oppimine` | "what am I learning today?" | generated drills, Selges keeles, the live ERR news feed, radio courses |
| `kordamine` | "what am I forgetting?" | the FSRS queue, failed items, official consultation workbooks |
| `eksam` | "am I ready?" | readiness verdict, annotated sample performances, official tasks, EIS, intro videos |

Sections filter on **skill and purpose** (`meta.kind`), not skill alone. Skill
alone held only while everything was reading or listening practice; the official
material broke it, because HARNO publishes samples, videos and workbooks that
carry the same skill as a task while being a completely different activity.
Twenty-five items ended up in no section at all — present in the database,
absent from the app, silently. `tests/test_sections.py` has the orphan check
that would have caught it.

## Two scales, never one

A text carries **two different claims** and they must not share a column:

| Field | Means | Who has it |
|---|---|---|
| `level` | CEFR — A2, B1, B2, C1 | only official HARNO / EIS material, where the exam board said so |
| `band` | difficulty relative to its own source — `kergem` / `keskmine` / `raskem` | all harvested prose |

They lived in one column, and a learner filtering `B1` got only exam material —
349 reading texts and 20 news issues invisible to the one filter anybody uses.

**Do not derive CEFR from vocabulary coverage.** It was tried: 342 of 349
deliberately-simplified news items came out as B2, because only 6.2 % of the
160 316 lemmas carry a CEFR tag at all. The scale is not calibrated and no
threshold on it can be.

What *is* computable is **comprehensibility for one learner** — the share of a
text's lemmas that learner has met (`difficulty.comprehensible`). That is the
mechanism the reading research actually names: input works when it is
understood, and understanding is gated by known vocabulary. `/api/reading/next`
ranks by it and puts the instructional band first, because that is where a text
teaches rather than bores or defeats.

It is vocabulary coverage, not comprehension, and the field names say so.

## Where it runs

| Half | Where | Why |
|---|---|---|
| the app | Google Cloud Run | needs Vabamorf, a compiled C++ Python extension |
| the front door | Cloudflare Worker + Access | one hostname, one login, Workers AI for speech |

Both on free tiers. `docs/deploy.md` has the whole picture, including why it is
not a Worker and not a Cloudflare Container.

**Two doors, two locks.** Access guards the Worker. `PROXY_TOKEN` guards the
Cloud Run origin, because Cloud Run must allow unauthenticated invocations to
be free and its `run.app` URL answers the whole internet. The Worker refuses
anything without an Access identity; the app refuses anything without the token.

## What a session can and cannot reach

Working through this repo, you **cannot read the deployed app**: Access blocks
the Worker and `PROXY_TOKEN` blocks the origin. That is correct and deliberate.

- To verify the deployment, run the **`smoke` workflow** (`.github/workflows/smoke.yml`).
  It authenticates with a Cloudflare Access service token held in Actions
  secrets, so the credential is never in a chat or an environment.
- To verify the UI, **run the app locally and drive it with Playwright**.
  Chromium is at `/opt/pw-browsers/chromium`. This is not optional polish: the
  overlapping-navigation bug in `tests/test_web_layout.py` was invisible to 500
  passing tests and obvious in a browser in one screenshot.
- Operator actions on the deployment run **in Google Cloud Shell**, via the
  scripts in `deploy/`, which read the tokens out of the running service so no
  person ever handles them.

**Never** put a credential in a chat message, a commit, or the Claude
environment-variables box. Secrets belong in GitHub Actions secrets (CI),
Cloudflare Worker secrets (production), Cloud Run environment variables (the
origin), and a git-ignored `.env` (local).

## Licence rules that are not negotiable

- **HARNO / EIS exam material** — © Haridus- ja Noorteamet. Indexed as
  *pointers only*; `body` is empty and a test asserts it. Never copied, never
  redistributed.
- **ERR transcripts** and **Selges keeles** — owner-only, `redistributable = 0`,
  behind Access. Roughly 421 items.
- **Sõnaveeb must never be batch-scraped.** `sonapi` is single-lookup only,
  throttled to one live request a second under a lock, and deliberately has no
  bulk helper. Where more than three fields are wanted, **link to Sõnaveeb**
  (`sonapi.entry_url`) rather than fetching more — the same posture as HARNO.
  Answers are kept in `vocab.db` (`eesti/gloss.py`) so a word is asked about
  **once, ever**, capped by `DAILY_BUDGET` per day; the store is one learner's,
  behind Access, never redistributed. Ekilex is CC-BY-4.0, so the copy is
  permitted — the restraint is about their server, not their licence.
- `data/*.db` and `data/exam/` are git-ignored. Runtime databases are never
  committed.

## Commands worth knowing

```bash
python -m eesti.cli serve            # local app on :8000
python -m eesti.cli harvest          # ERR language archives
python -m eesti.cli harvest-reading  # Selges keeles
python -m eesti.cli harvest-news     # ERR Lihtsad uudised — the live feed
python -m eesti.cli harvest-exam     # official EIS tasks (pointers)
python -m eesti.cli ingest FILE      # your own material: a text file, or JSON items
python -m eesti.cli link-topics      # which texts demonstrate which topic
python -m eesti.cli notion           # queued errors; --push writes to Notion
pytest tests/ -q                     # ~1 690 in-process; ~144 more need a browser
```

`deploy/setup.sh`, `deploy/push-content.sh`, `deploy/reset-progress.sh` all run
in Cloud Shell and discover the project, service and region themselves.

## Habits this codebase has earned the hard way

They are in **`docs/lessons.md`**, in eight groups, unchanged. They were in
this file until it reached 48 KB, which meant a session read every one of them
before doing anything and in practice read none of them.

Read the group that matches the change you are making:

- **Paths, connections and state that must survive a restart** — before binding
  anything at import, or storing anything in a module global.
- **Measurements with no writer, endpoints with no caller** — before adding a
  state, a status, a column or a route. This one has recurred five times in
  five different costumes.
- **Derived, never hand-maintained** — before writing a list of things that
  already exist somewhere else.
- **Tests and fixtures** — before trusting a green suite.
- **The page: layout, CSS, the browser, and what the learner reads** — before
  touching `eesti/web/`.
- **Content, third parties and the language itself** — before stating a
  grammatical rule, or fetching anything from someone else's server.
- **Providers, secrets and operating the deployment** — before believing a
  check that says OK.
- **Documents and decisions** — before writing a number into a document.
