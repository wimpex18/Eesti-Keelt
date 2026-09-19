# Eesti-Keelt

Estonian A2/B1 exam preparation for one learner, a Russian speaker. A
**learn → practise → check** loop: drills are generated from a word list and a
morphological analyser (Vabamorf), so practice is unlimited and every answer is
graded without a network call. The #1 documented weakness is `obj-case`
(genitive vs partitive for a completed object).

No exam is booked; the sitting is planned for 2027. `readiness.TARGET` stays
`None` until a date is chosen — do not add a countdown.

## Non-negotiable

- **Generation and grading are deterministic.** A model may only explain a
  correction in prose and transcribe speech. Drills, grading, study order and
  the mastery gate are code. See `docs/ai-boundaries.md`.
- **`estnltk==1.7.5` is the answer key** — do not bump it. Python is 3.14.7
  only (`.python-version`, Dockerfile, CI).
- **Never put a credential** in chat, a commit or an environment box. Secrets
  live in GitHub Actions secrets, Cloudflare Worker secrets, Cloud Run env vars
  and a git-ignored `.env`.
- **Do not invent a linguistic fact.** Forms come from Vabamorf; rules from
  EKI's handbook (EKK); a table without a cited source is not added
  (pronouns are blocked on exactly that).

## Which language a string is in

| Text | Language |
|---|---|
| UI labels (`Kirjutamine`, `Rada`) | Estonian — the interface is exposure |
| Grammar terms (`osastav`, `omastav`) | Estonian — they must be learned |
| Anything explaining, warning or justifying | **Russian** |
| Example sentences and drill content | Estonian |

A caveat the learner cannot read is not a caveat. When Russian names an
Estonian concept, keep the Estonian word and gloss it once:
*"Говорение (rääkimine) оценить нельзя"*. Never transliterate a term
(`омастав` is wrong; write `omastav`). `tests/test_ui_language.py` enforces it.

## Data rules

- **`level` is CEFR** and only official HARNO/EIS material has one; **`band`**
  (`kergem`/`keskmine`/`raskem`) is difficulty relative to its source. Never
  derive CEFR from vocabulary coverage.
- Word levels come from EKI's official A1/A2/B1 list where it has the word,
  otherwise the enriched Ekilex estimate; `words.level_source` says which.
- Every library section belongs to exactly one mode in `library.MODES`
  (`oppimine`, `kordamine`, `eksam`), filtered by `meta.kind`;
  `tests/test_sections.py` catches orphans.

## Licences

- **HARNO / EIS exam material** — pointers only; `body` stays empty.
- **ERR transcripts, Selges keeles** — owner-only (`redistributable = 0`),
  served only behind Access.
- **EKI downloads** (`deploy/eki/`) — CC BY 4.0, committed, imported at image
  build; keep attribution (`eesti/licences.py`, `/api/sources`).
- **Sõnaveeb / Ekilex** — single lookups only, one per second, stored once in
  `vocab.db`, capped by `DAILY_BUDGET`. Never batch; link out with
  `sonapi.entry_url` for more.
- `data/*.db` and `data/exam/` are never committed.

## Where it runs

| Part | Where |
|---|---|
| App (FastAPI + Vabamorf) | Google Cloud Run, rebuilt by Cloud Build on every merge to `main` |
| Front door | Cloudflare Worker + Access (`deploy/worker.ts`), speech via Workers AI binding |
| Learner state | snapshotted by the Worker into a Durable Object across cold starts |

Two locks: Access guards the Worker; `PROXY_TOKEN` guards the Cloud Run origin.
A session cannot read the deployed app — verify it with the **`smoke`**
workflow (`deep: true` sends one sentence through the grammar chain). Operator
actions run in Google Cloud Shell via `deploy/*.sh`. See `docs/deploy.md`.

## Commands

```bash
python -m eesti.cli fetch-data && python -m eesti.cli build   # word list + index
python -m eesti.cli export                                    # form index the word card reads
python -m eesti.cli serve                                     # http://127.0.0.1:8000
python -m eesti.cli keys                                      # which API keys are set
python -m eesti.cli eval --provider workers-ai                # score a grammar model
python -m pytest tests/ -q -n auto                            # in-process + browser suites, in parallel
```

Browser journeys (`tests/test_e2e_journeys.py`) need Playwright Chromium and
WebKit and a built dataset; CI runs only the in-process tests. After any change
to `eesti/web/`, run them and look at both viewports.

## Working habits

- Stage named paths; never `git commit -a`. Open small PRs; the user merges.
- A claim in a doc that can be derived is tested (`tests/test_docs_match_code.py`).
  Docs state the current state only — history is in git.
- Path-scoped rules in `.claude/rules/` load when you touch matching files.

## Docs

| File | Answers |
|---|---|
| `docs/status.md` | what works, what is missing, known issues — read before planning |
| `docs/architecture.md` | modules, data, request flow |
| `docs/app-structure.md` | modes, tabs, which screens a model touches |
| `docs/ai-boundaries.md` | what a model may and may not decide |
| `docs/ai-providers.md` | grammar and speech provider chains, models, eval |
| `docs/curriculum.md` | syllabus model, path, mastery, placement |
| `docs/sources.md` | every data source and its licence |
| `docs/speaking.md` | what the speaking tab checks and what it cannot |
| `docs/deploy.md` | Cloud Run, Worker, secrets, scripts, verification |
| `docs/setup.md` | local setup and API keys |
| `docs/testing.md` | test suites and how to run them |
| `PRODUCT.md` | who the learner is, product purpose and principles (design context) |
| `DESIGN.md` | the visual system: colour roles, type roles, layout, components |
