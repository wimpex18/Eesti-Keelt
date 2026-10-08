# Handoff

Programme: October 2026 review → Linear DEV-35..DEV-56 (`qa/architecture-review.md`,
next-session prompts in `qa/session-briefs.md`). Sessions run in parallel
worktrees: S1 correctness (DEV-35), S2 public material (DEV-54), S4 data safety
and dependencies (DEV-37, DEV-39). Each PR edits this file; on conflict keep the
newest present-state note. The A2/B1 sittings are 7–8 Nov 2026: low-risk changes.

S1 current task: DEV-49 EVS glosses, branch claude/dev-49-evs-glosses, PR #114.
- `eesti/evs.py`: homographs chosen by EKI's level list (POS + corpus count);
  negation-only senses dropped when the first sense is ordinary.
- `cli import-evs` reads `A1A2B1.txt` beside the EVS file (`--levels`); the
  Docker build re-imports on merge, nothing to run by hand.
- Progress counter: glossed ranked words from every offline source.
- Remaining limits in `docs/status.md` Known issues (väär, kord ordering).
Next for S1: DEV-50 writing object case (branch claude/dev-50-writing-checks),
then DEV-51 items, DEV-53 exam screens, DEV-52 ÕS 2025 audit.

Uncommitted: none after this commit. Blockers: none. S2 also edits
`eesti/evs.py`, `eesti/morph.py`, `eesti/mock.py`; the later PR rebases.
Owner sends `qa/source-permission-requests.md` (DEV-55); private sources stay
owner-only until written permission.
