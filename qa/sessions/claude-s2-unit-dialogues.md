# S2 — `claude/s2-unit-dialogues`

Task: a dialogue and a reading text for each of units 2–10, drafted by Claude
Opus 5.5 and kept only when the gates and Haiku 5.5's blind check pass them
(ADR-0009); then, at the owner's request, the follow-ups. PR #133.

State: done. 18 files in `content/material/checked/`, five questions each.
The image builds them into `data/material.db` (Dockerfile), apart from the
owner's corpus in `content.db`; the unit routes, `mat:` library items and the
HARNO-format exam tasks read it, so B1 reading 4 builds. `comprehension` counts
digits as words. `draft.py` drafts, gates, revises and trims; `log.md` and
`rejected/` record what was refused.

Next step: the owner merges; Cloud Build then ships `material.db`. For local
`cli serve`, run `python -m eesti.cli material build` once in the main checkout.
Then run the `smoke` workflow with `deep: true`.

Deferred by the owner (10 Oct): crediting EKI's *Kasulikke väljendeid* in the
`grove-material` source entry; licences are settled before release.

Uncommitted paths: none after the commit. Blockers: none. The Anthropic key
stays in the owner's git-ignored `.env`; never printed.
