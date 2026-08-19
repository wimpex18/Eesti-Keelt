# Eesti-Keelt — working notes for a new session

Estonian A2/B1 exam preparation, built for one learner. Read `docs/` for the
reasoning; this file is what a fresh session needs in the first minute.

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

**Done so far:** the readiness verdict and its reasons, the pronunciation
caveat, `library.SECTIONS` descriptions, the source notes on official material,
and the published integration map.

**Still Estonian or English** (audit 2026-08-19): the web UI's own body copy in
`eesti/web/index.html` and `docs/*.md`. Nothing in `data/` needs translating —
it is the study material.

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
- **Sõnaveeb must never be batch-scraped.** `sonapi` is single-lookup only and
  deliberately has no bulk helper. The enriched word list removes any need.
- `data/*.db` and `data/exam/` are git-ignored. Runtime databases are never
  committed.

## Commands worth knowing

```bash
python -m eesti.cli serve            # local app on :8000
python -m eesti.cli harvest          # ERR language archives
python -m eesti.cli harvest-reading  # Selges keeles
python -m eesti.cli harvest-news     # ERR Lihtsad uudised — the live feed
python -m eesti.cli harvest-exam     # official EIS tasks (pointers)
python -m eesti.cli link-topics      # which texts demonstrate which topic
python -m eesti.cli notion           # queued errors; --push writes to Notion
pytest tests/ -q                     # 503 tests
```

`deploy/setup.sh`, `deploy/push-content.sh`, `deploy/reset-progress.sh` all run
in Cloud Shell and discover the project, service and region themselves.

## Habits this codebase has earned the hard way

- **Presence of a database is not presence of data.** Two separate bugs came
  from checking that a file existed: the first request creates it *with its
  schema*, so an empty deployment looked full. Count rows.
- **Resolve paths at call time, not at import.** A module-level constant cannot
  be pointed anywhere else, and three bugs in a row came from that.
- **A third party being down must never fail the build.** EKI, HuggingFace and
  EIS are all optional at build and test time, loudly.
- **Check production by asking it.** Three bugs were found that way after the
  full suite was green.
