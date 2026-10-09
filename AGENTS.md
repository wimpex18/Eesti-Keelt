# Eesti-Keelt

Free Estonian learning and A2/B1 exam preparation; Russian is the MVP audience.
Beginner learning and English/Ukrainian support are release direction in PRODUCT.md.
The app uses learn → practise → check. Known weakness: `obj-case` (completed object, genitive vs partitive).

## Boundaries

- Code grades drills and FSRS reviews against Vabamorf/EKI forms. Models may
  explain and assess open writing or conversation, with the engine named; model
  scores are advisory readiness evidence, never mastery or FSRS. See
  `docs/ai-boundaries.md`.
- Claude Haiku 5.5 is the automatic hosted grammar/tutor lane (ADR-0008), then
  Workers AI GPT-OSS-120B, then deterministic offline evidence. Other grammar
  models are evaluation-only.
  Speech goes to the owner's Mac mini home service (`deploy/home-asr/`), with
  Workers AI Whisper as fallback. Change a lane only after its own
  task-specific evaluation; ASR needs human-verified learner audio, not prompts
  used as transcripts.
- Never invent a linguistic fact. Take forms from Vabamorf and rules from EKI's
  handbook or Teatmik; label a model-supplied claim as such. Preserve source
  attribution (`docs/sources.md`, `eesti.sources.REGISTRY`, `/api/sources`).
- Keep the learner in the app: present source-attributed text, PDFs, audio, video and
  exercises in its own UI. External links remain for attribution, undownloaded
  material and tasks whose official answers exist only on another site.
- Keep credentials out of chat, commits and environment boxes. Use the existing
  secret stores and git-ignored `.env`. Never commit learner databases,
  `data/exam/`, or `data/eval/` recordings/transcripts.

## Language and data

| Content | Language |
|---|---|
| UI labels and grammar terms | Estonian |
| Explanations, warnings and reasons | Russian |
| Examples and drills | Estonian |

This is the MVP contract; prepare Russian/English/Ukrainian instructional copy with stable topic/progress identities (PRODUCT.md).

In Russian explanations, retain an Estonian grammar term and gloss it once;
never transliterate it. `tests/test_ui_language.py` checks this.
For an explicit local EstLLM trial, English explanations are acceptable when
Russian is unreliable; label that trial clearly. Production UI stays Russian.

`level` means CEFR only for official HARNO/EIS material; `band` is relative
difficulty. Never infer CEFR from vocabulary coverage. Word levels come from
EKI's A1/A2/B1 list or an identified Ekilex estimate. Every library section
belongs to one `library.MODES` mode. The exam sitting is learner state, set by
the learner; no sitting is assumed.

## Runtime and verification

FastAPI/Vabamorf runs on one Cloud Run instance. public Cloudflare Worker is
the front door; `PROXY_TOKEN` protects the origin. Permanent-account API
success waits for the Durable Object to confirm the event sequence for that
response's origin boot. Cloud Build rebuilds the origin on merge to `main`;
the `deploy` workflow updates the Worker for Worker paths.
Use the `smoke` workflow with `deep: true` after deployment. Operator scripts
run in Google Cloud Shell; see `docs/deploy.md`. Learners and guests (each
person's own progress; sandboxes for agents and tests):
`docs/adr/0006-learners-and-guests.md`.

```bash
python -m eesti.cli serve                    # http://127.0.0.1:8000
python -m eesti.cli eval --provider workers-ai
python -m pytest tests/ -q -n auto
python -m pytest tests/test_e2e_journeys.py --browser -q -n 4
npm run typecheck
```

After a change to `eesti/web/`, run browser journeys and inspect both
viewports. Keep Python, tools and dependencies on current stable releases,
reached through `requirements.lock` upgrade PRs (`docs/deploy.md`); run the
suite after upgrades and the morphology eval before trusting a new `estnltk`.

## Working in this repository

- Start with `HANDOFF.md`, `git status` and recent commits. Read
  `docs/status.md` for feature or operational work; follow contextual links
  instead of loading every document for a small edit.
- Before each commit and at handoff, make `HANDOFF.md` (in a parallel session,
  `qa/sessions/<branch>.md`) a short present-state note: current task, exact
  next step, uncommitted paths and blockers; no completed history, ≤30 lines.
- Keep `AGENTS.md` concise and model-agnostic as the single repository-wide
  agent instruction file.
- Stage named paths, never `git commit -a`. One branch and one PR per session:
  add later work to it, even for another issue; never a PR per issue, and no
  sub-branches merged into each other. One implementation session at a time;
  parallel sessions only when the owner asks, each in its own worktree on the
  files its brief owns (`qa/opus-sessions.md`). If the owner says "no PR", commit to `main`. The user merges.
  Docs describe current behavior. Path rules are in `.claude/rules/`; design
  context is in `PRODUCT.md` and `DESIGN.md`. Architecture constraints are in
  `docs/adr/0005-architecture-contracts.md`.

## Linear tracking

Linear team **Development (DEV)**, project **Eesti-Keelt**, is paused by the
owner (9 Oct 2026). **Never create issues**; record follow-up, deferred work and
findings in the PR and the handoff note. Keep an issue ID in the branch or PR
when work starts from one; durable truth goes in repository docs.
