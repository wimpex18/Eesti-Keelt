# Stack and practices — August 2026

Recommendations for **this** app, not a generic survey. Where the modern default
does not fit a single-user local tool, that is said plainly.

## The constraint that decides most of it

**Vabamorf/EstNLTK is Python-only.** There is no JavaScript, Go or Rust port of
Estonian morphological analysis and synthesis. The core of this app — labelled
case forms, deterministic grading — cannot leave Python.

So the backend is Python. That is not a preference; it is the one hard
architectural fact, and it should be stated before any framework discussion.

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
