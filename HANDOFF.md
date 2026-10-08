# Handoff

Programme: October 2026 review → Linear DEV-35..DEV-57 (`qa/architecture-review.md`,
next-session prompts in `qa/session-briefs.md`). Parallel worktree sessions:
S1 correctness (DEV-35), S2 public material (DEV-54, merged #115), S4 data
safety and dependencies (DEV-37, DEV-39). Each PR edits this file; on conflict
keep the newest present-state note. A2/B1 sittings 7–8 Nov 2026: low-risk changes.

S1 open PRs (owner merges; the later ones merge main in):
- DEV-49 EVS glosses: #114, claude/dev-49-evs-glosses. Homographs chosen by
  EKI's level list; negation-only senses dropped. Limits in Known issues.
- DEV-50 writing object case: #117. DEV-51 practice items: #120.
Next for S1: DEV-53 exam screens, then DEV-52 ÕS 2025 audit.

After S2: guests draw drills, dictation and mock parts from `evs.phrases`;
`itemref.GENERATOR_VERSION` is 3 on main (DEV-51 takes it to 4). Deploy and
`smoke` with `deep: true` are the owner's next steps after merges.
Uncommitted: none after this commit. Worktree `data/*.db` are ignored
reference copies. Blockers: none.
