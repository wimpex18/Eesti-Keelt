# S2 — `claude/s2-unit-dialogues`

Task: a dialogue and a reading text for each of units 2–10, drafted by Claude
Opus 5.5 through the Batches API and kept only when `cli material check` and
`cli material blind` pass them (ADR-0009).

State: done. 18 files in `content/material/checked/`, five questions each;
`cli material build` rebuilds all 18; B1 reading 4 builds from the texts.
`content/material/draft.py` is the drafting tool, `README.md` how a file was
made, `log.md` and `rejected/` what was refused and why.

Next step: the owner merges. Then, in files S2 does not own (PR description):
1. `eesti/comprehension.py`: digits are ignored when answers are compared
   (*6 eurot* matches *5 eurot*); count them or refuse such answers.
2. `Dockerfile`: copy `content/` and run `cli material build`, or production
   has no material and B1 reading 4 cannot build.
3. `eesti/licences.py` `grove-material`: credit EKI's *Kasulikke väljendeid*,
   whose exchanges the dialogues reuse word for word.
4. `eesti/cli/material.py`: `blind` should call `env.load()`.
5. R2: the status rows that say no material is checked in.

Uncommitted paths: none after the commit. Blockers: none. The Anthropic key
stays in the owner's git-ignored `.env` (linked into the worktree); never
printed.
