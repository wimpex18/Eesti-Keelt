# Eesti-Keelt

Estonian A2/B1 exam preparation for Russian speakers, growing into an
all-in-one Estonian learning "Super App". A **learn → practise → check** loop:
drills are generated from a word list and a morphological analyser (Vabamorf),
and answers are graded by code where code can decide and by an LLM where it
cannot (meaning, writing, conversation). The #1 documented weakness is
`obj-case` (genitive vs partitive for a completed object).

The sitting is planned for 2027 with no date: `readiness.TARGET` stays `None`,
no countdown.

## Non-negotiable

- **Code grades; models assess and explain.** Drills, review and FSRS are
  graded by code against Vabamorf/EKI forms, never by a model. A model may
  explain, tutor, and score open production (meaning, writing, conversation);
  such a score is labelled with its engine and is advisory evidence for
  readiness only, never mastery or FSRS. See `docs/ai-boundaries.md`.
- **Stay on the latest stable** Python, tools and dependencies; don't pin.
  Run the suite after an upgrade, and the eval before trusting a new `estnltk`.
- **Never put a credential** in chat, a commit or an environment box. Secrets
  live in GitHub Actions secrets, Cloudflare Worker secrets, Cloud Run env vars
  and a git-ignored `.env`.
- **Do not invent a linguistic fact.** Forms come from Vabamorf; rules from
  EKI's handbook (EKK); a model-supplied one is labelled as such.

## Which language a string is in

| Text | Language |
|---|---|
| UI labels (`Kirjutamine`, `Rada`) | Estonian — the interface is exposure |
| Grammar terms (`osastav`, `omastav`) | Estonian — they must be learned |
| Anything explaining, warning or justifying | **Russian** |
| Example sentences and drill content | Estonian |

When Russian names an Estonian concept, keep the Estonian word and gloss it
once: *"Говорение (rääkimine) оценить нельзя"*. Never transliterate a term
(`омастав` is wrong). `tests/test_ui_language.py` enforces it.

## Data and licences

- **`level` is CEFR** and only official HARNO/EIS material has one; **`band`**
  (`kergem`/`keskmine`/`raskem`) is relative difficulty. Never derive CEFR
  from vocabulary coverage. Word levels: EKI's A1/A2/B1 list, else the Ekilex
  estimate; `words.level_source` says which.
- Every library section belongs to exactly one mode in `library.MODES`
  (`oppimine`, `kordamine`, `eksam`); `tests/test_sections.py` finds orphans.
- Keep source attribution: `docs/sources.md`, `eesti/licences.py`,
  `/api/sources`. EKI downloads (`deploy/eki/`) are CC BY 4.0. Ekilex results
  are cached in `vocab.db`; link out with `sonapi.entry_url`.
- `data/*.db` and `data/exam/` are never committed.

## Where it runs
App (FastAPI + Vabamorf) on Google Cloud Run, rebuilt by Cloud Build on every
merge to `main`. Front door: Cloudflare Worker + Access (`deploy/worker.ts`,
speech via Workers AI), which snapshots learner state into a Durable Object.
Two locks: Access guards the Worker, `PROXY_TOKEN` the Cloud Run origin. A
session cannot read the deployed app; verify with the **`smoke`** workflow
(`deep: true` sends one sentence through the grammar chain). Operator actions
run in Google Cloud Shell via `deploy/*.sh`. See `docs/deploy.md`.

## Commands
```bash
python -m eesti.cli fetch-data && python -m eesti.cli build && python -m eesti.cli export
python -m eesti.cli serve                          # http://127.0.0.1:8000
python -m eesti.cli eval --provider workers-ai     # score a grammar model
python -m pytest tests/ -q -n auto                 # in-process + browser suites
```

Browser journeys (`tests/test_e2e_journeys.py`) need Playwright Chromium and
WebKit; CI runs only the in-process tests. After any change to `eesti/web/`,
run them and look at both viewports.

## Session lifecycle and hand-off

State lives in the repo, not in a chat. `HANDOFF.md` is the one file that
carries it between Claude Code and Codex.

- **Start:** read `HANDOFF.md`, then check `git status` and `git log -5`
  against it. Read `docs/status.md` before planning.
- **End, and before every commit:** overwrite `HANDOFF.md` with the current
  task, the exact next step, files changed but uncommitted, and blockers. It
  states the present, never a log: delete finished items, keep it to 30
  lines, and commit it with the work it describes.
- `AGENTS.md` and `CLAUDE.md` are identical. After editing one, run
  `cp AGENTS.md CLAUDE.md`.

## Working habits

- Stage named paths; never `git commit -a`. Open small PRs; the user merges.
- Docs state the current state only; derivable claims are tested
  (`tests/test_docs_match_code.py`). Path-scoped rules: `.claude/rules/`.

## Docs

Read `docs/status.md` (what works, what is missing) before planning. The rest
of `docs/`: `architecture`, `app-structure`, `ai-boundaries`, `ai-providers`,
`curriculum`, `sources`, `speaking`, `deploy`, `setup`, `testing`. Design
context: `PRODUCT.md`, `DESIGN.md`.
