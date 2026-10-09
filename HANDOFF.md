# Handoff

Current task: DEV-40 course structure, branch `claude/dev-40-course-structure`, one PR.
Done: spec `docs/course-structure.md` and ADR-0007 agreed with the owner (interview
9 Oct 2026); thirty units in `eesti/units.py` (Kursus folds by unit, resume follows
units, a chosen start skips earlier stages); unit 1 topics `tahestik` (EKI PSV
recordings, now public), `fraasid` (EKI A1 phrases), `arvud`; `obj-case` nominative
total object by rule name; `osaalus`; EKI credit on packs, test-out, placement and
review cards. Fast suite and both browser engines green.
Next: owner reviews and merges the PR; merge rebuilds the origin (Cloud Build), then
run `smoke` with `deep: true`. The following session is in `qa/next-session.md`
(unit check, unit completion, homework, weekly pace check).
For the owner to confirm (a default taken in this session): unit 1 leads the next
step only for a learner who has mastered nothing beyond it; nothing is skipped.
Owner actions: send the EKI permission draft (adds pronunciation-exercise audio and
the etLex licence question); verify a nightly backup copy with `cli verify-backup`.
Production: sound items need `data/audio.db` on the GCS mount (already mounted);
without it `tahestik` reads as reference and resume passes it.
Uncommitted task paths: none after the commit.
Preserve unrelated package.json and untracked .agents/, .claude/agents/,
.claude/settings.local.json, .claude/skills/, .codex/, .github/agents/,
.github/hooks/, .github/skills/, .impeccable/decisions/learning-redesign.json,
.impeccable/live/. No secrets revealed.
