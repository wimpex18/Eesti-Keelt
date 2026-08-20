# Architecture

Target: a Cloudflare-hosted app, reachable online, working on desktop and mobile.

## The constraint that shapes everything

**Vabamorf cannot run on Cloudflare.** Workers execute Python through
Pyodide/WebAssembly, which supports pure-Python and PyEmscripten wheels only —
and Vabamorf (via EstNLTK) is a compiled C++ extension. There is no port to
JavaScript, Rust or WASM either.

That looks fatal, because Vabamorf is the source of every linguistic fact in this
app. It is not, because **morphology is static**. The genitive of `raamat` does
not depend on the request.

## The resolution: move Vabamorf to build time

```
BUILD (local / CI, Python)                RUNTIME (Cloudflare, TypeScript)
─────────────────────────────             ────────────────────────────────
Ekilex wordlist ─┐
                 ├─► Vabamorf ─► edge.db ──► D1 ──► Worker ──► Pages (UI)
CEFR + freq ─────┘   synthesis                        │
                                                      └─► LLM (adjudication only)
```

`python -m eesti.cli export` runs Vabamorf over the vocabulary and writes a
portable SQLite. Measured:

| | |
|---|---|
| lemmas exported | 12 787 (all CEFR-tagged + frequency head to rank 25 000) |
| labelled forms | **411 349** |
| object-case pairs | 10 979, of which **7 256 have a distinct genitive/partitive** |
| size | 47 MB — against D1's 5 GB free tier |
| build time | ~11 s |

The edge therefore needs no morphology engine. It needs indexed lookups.

### The reverse index is the important part

`forms(form, lemma, tag)` replaces runtime analysis. Where Vabamorf answers "what
case is `raamatut`?", a `SELECT` answers the same question:

```sql
SELECT lemma, tag FROM forms WHERE form = 'raamatut';
-- raamat | sg p
```

Measured coverage on realistic learner sentences: **44/45 tokens (98 %)** — the
single miss was the string `b1`. Irregular verb stems resolve correctly
(`läksin`→minema/`sin`, `sõin`→sööma/`sin`), which is the `verb-form` gap.

Anything not in the index falls through to the LLM, so coverage degrades
gracefully instead of failing.

## What runs where

| Layer | Where | Why |
|---|---|---|
| UI | Cloudflare Pages | Static, free, global. Responsive desktop + mobile. |
| API | Workers | 100 K req/day free; 10 ms CPU is ample for indexed lookups. |
| Data | D1 | 5 GB, 5 M row reads/day. Holds `words`, `forms`, `object_cases`. |
| Progress | D1 | Attempts and drill history — single user, tiny. |
| Audio cache | R2 | 10 GB free. TTS output is immutable, keyed by content hash. |
| LLM | Workers AI, or OpenRouter/Groq | See below. |
| **Build** | **local / GitHub Actions** | **Python + Vabamorf. Never at the edge.** |

The Python package does not disappear — it becomes a **build tool and a local
dev server**, which is also how the offline-first property survives: everything
still works on `localhost` with the network unplugged.

## Free-tier headroom

For one learner, none of these bind:

- Workers 100 K req/day · D1 5 M reads/day · KV, R2, Durable Objects all free
- Workers AI **10 000 neurons/day**, shared across models
- OpenRouter **50 req/day** free, or **1 000/day** after a one-time $10 credit
  purchase — an account threshold, not consumption

## LLM lane

Providers are interchangeable behind one OpenAI-compatible client
(`eesti/providers/llm.py`), so the deployment target can change without touching
the grammar logic. Preference order, skipping any whose key is unset:

1. **OpenRouter** — one key, 412 models, 15 currently `:free`.
2. **Groq** — fastest inference, generous free tier.
3. **Workers AI** — runs *inside* Cloudflare: no egress, no third-party key.
4. **Anthropic** — paid backstop for quality.

**Probe before pinning.** Model ids are withdrawn silently, and a withdrawn
`:free` id is the worst case because the paid one with the same name keeps
working, so the name still looks right while every call 404s. Verified live in
August 2026: `openai/gpt-oss-120b:free` is **absent** from OpenRouter's catalogue
while `openai/gpt-oss-120b` still exists. The pinned default is
`google/gemma-4-31b-it:free`, re-verified present on 2026-08-20 and advertising
`response_format` — which is the capability the client actually sends, and a
*different* one from `structured_outputs`.

```bash
python -m eesti.cli models --provider openrouter   # re-probe the catalogue
```

## Choosing a model by measurement, not by reputation

The reasonable hypothesis — a model good at other languages should handle
Estonian — is testable, so `eesti/evals/gec.py` tests it. 18 Estonian sentences,
scored two ways:

- **recall** — of the 10 with planted errors, how many were caught
- **precision** — of the 8 that are **already correct**, how many were left alone

The second is what separates models. A checker that flags every partitive scores
perfect recall and is worse than useless, because it would teach the learner that
every partitive is wrong. Estonian is low-resource, and the specific judgement
here (genitive for a completed whole object, partitive for ongoing, partial or
negated) is exactly the language-specific semantics that thins out first.

```bash
python -m eesti.cli eval --provider openrouter --model <id>
```

Exits non-zero below 0.8 on either score, so it can gate a deploy.

## Invariants

1. **Linguistic facts come from Vabamorf, never from a model.** Models adjudicate
   free text and explain. Forms, paradigms and drill answers are generated.
2. **Grading is deterministic** — string comparison against a synthesized form.
   Free, instant, and incapable of being confidently wrong.
3. **Every network dependency is optional**, behind a chain with short timeouts
   and a circuit breaker; the UI always names the engine that answered.
4. **The build is reproducible and offline.** `export` needs no network.

## Open questions

- **Auth.** Currently single-user and unauthenticated, which is fine on
  `localhost` and *not* fine on a public URL. Cloudflare Access is the cheapest
  answer (free tier, no code) and keeps the app single-user by policy.
- **D1 import path.** 411 K rows: `wrangler d1 execute --file` may need batching,
  or the dataset can ship as a read-only SQLite in R2.
- **Mobile drill ergonomics.** The drill loop is a typing loop; on a phone,
  õ/ä/ö/ü need to be reachable without switching keyboard layers.

---

# Stack and practices

Merged from the former `stack-2026.md`. Recommendations are for *this*
project, not a generic survey; where the modern default does not fit a
single-user tool, that is said plainly.

## Backend

**FastAPI + Pydantic v2 — keep.** FastAPI is the default greenfield Python choice
in 2026: async-first, native Pydantic v2, OpenAPI for free. Pydantic v2 is 5–50×
faster than v1 on validation-heavy endpoints. Already in use here.

**Tooling — adopt.** Two changes are clearly worth making:

| Replace | With | Why |
|---|---|---|
| `pip` + `venv` | **`uv`** | Dramatically faster installs; one tool for envs, deps and lockfile. |
| flake8 + isort + black | **`ruff`** | One binary, fast enough to run on every keystroke. |

```bash
uv venv && uv pip install -r requirements.txt
uvx ruff check . && uvx ruff format .
```

**Database — keep plain `sqlite3`.** SQLModel/SQLAlchemy 2.0 is the production
standard, but this app has four tables, one writer, and no migrations. Adding an
ORM here buys abstraction nobody needs. Revisit only if the schema starts
changing often.

**Testing — pytest, already in place.** The suite is the regression gate; keep it
offline so it can run without keys or network.

## Frontend

The 2026 default is Next.js — and for this app it is **the wrong choice**.

Next.js earns its keep through SSR, image optimisation, file-based routing and
edge delivery. A single-user app on `localhost` with no SEO, no cold-start
audience and no auth benefits from none of it, while paying for a Node
toolchain alongside the Python one that must exist anyway.

**Recommended path, in order of when to escalate:**

1. **Now — vanilla HTML/CSS/JS in one file.** ~270 lines, zero build step, loads
   instantly, no `node_modules`. Correct for the current scope.
2. **If the UI outgrows one file — Vite + React 19 + TypeScript.** The consensus
   pick for dashboards and internal tools: instant HMR, fast builds, no framework
   opinions. Vite also wins the client-side metrics (bundle size, TTI) that
   actually apply to localhost.
3. **Next.js — only if this is ever deployed publicly** for other learners.

If step 2 happens, the 2026-standard companions: **Tailwind + shadcn/ui**
(components you own, not a dependency), **TanStack Query** (server state),
**Zod** (schema validation shared with Pydantic's contract), **Vitest +
Playwright**, **ESLint flat config**, strict TypeScript.

## Design

Principles the current UI already follows and should keep:

- **Theme-aware by default** — light/dark via `prefers-color-scheme`, all colours
  as CSS custom properties, never a hard-coded hex in a rule.
- **System font stack** — no webfont request, no layout shift, correct rendering
  of `õ ä ö ü` on every platform.
- **Semantic colour, sparingly.** Object-case errors get their own accent because
  they are the documented priority; everything else shares one neutral treatment.
  If every error type had a colour, none would signal anything.
- **Estonian UI labels** (`Kirjutamine`, `Harjutused`, `Kuulamine`) with Russian
  explanations. The interface is itself exposure; the explanation is where
  comprehension has to win.
- **Keyboard first** — Ctrl+Enter to check, Enter to submit an answer, autofocus
  on the first drill. Drilling is a typing loop; reaching for a mouse breaks it.

Accessibility floor: WCAG 2.2 AA contrast, visible focus rings, real `<label>`s,
`aria-selected` on tabs, and no meaning carried by colour alone (the ✓/✗ glyphs
carry it too).

## Practices worth keeping

- **Offline-first.** Four research APIs were down during development. The core
  loop must not depend on any network call.
- **Provider chain + circuit breaker.** Every external service behind one
  interface, short timeouts, automatic skip after repeated failure, and the UI
  always names the engine that answered.
- **Never let a model generate linguistic facts.** Forms come from Vabamorf.
  Models adjudicate and explain only. See `ai-strategy.md`.
- **Deterministic where possible.** Drill grading is string comparison — free,
  instant, and incapable of being confidently wrong.
- **Licence hygiene.** Wordlist CC-BY-SA-4.0, Ekilex CC-BY-4.0, Vabamorf/TalTech
  models permissive. HARNO exam material is copyright — git-ignored, never
  redistributed.

## Correction: the Cloudflare plan changed

This document's original deploy plan — export to D1, serve from a Worker — was
written when the app looked things up. It now *generates*: `cloze`,
`conjugation`, `patterns` and `verbs` all call Vabamorf at request time, and
Vabamorf is a compiled C++ extension that cannot run in a Worker.

The deploy is therefore **Cloudflare Containers**, with a Worker in front for
routing and for snapshotting the learner's state — container disk is ephemeral,
so without that a ten-minute idle period would reset all progress. See
[`deploy.md`](deploy.md).
