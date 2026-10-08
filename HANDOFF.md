# Handoff

Current task: architecture, content and market review → implementation programme.
Branch: claude/ek-review-plan (planning PR: review snapshot, permission drafts,
verified known issues). Base: main faa477d.
Review: `qa/architecture-review.md` (illustrated version: Claude artifact
https://claude.ai/artifact/9x35tYbYJDvTy5sAqHf1hg). Backlog: Linear DEV-35..DEV-56.

Start now, one fresh worktree session each, small PRs, branch names carry the ID:
- S1 correctness: DEV-35 (DEV-49 EVS glosses, DEV-50 writing object case,
  DEV-51 items, DEV-52 ÕS 2025 audit, DEV-53 exam screens).
- S2 public material: DEV-54 EVS phrase pools (DEV-36 epic).
- S3 Claude Haiku 5.5 lane and eval: DEV-38 (eval spends a little money: ask first).
- S4 data safety and dependencies: DEV-37, DEV-39.
Owner sends `qa/source-permission-requests.md` (DEV-55); answers go to
`eesti/licences.py` and `docs/sources.md` before any source is opened.

Next-session prompts: `qa/session-briefs.md` (A: DEV-40 spec, B: DEV-38 when
the key is in .env, C: DEV-41). Merge #111 first; S1/S2/S4 PRs rebase on it.
Order after that: DEV-40 course-structure spec (interview → SPEC.md → ADR) before
DEV-41 exam fidelity, DEV-42 languages and DEV-45 patterns; DEV-43 Litestream only
after the 7–8 Nov 2026 sittings; DEV-47 pilot after DEV-35/36; redesign last.
Owner decisions: full A0→B1 path alongside Keeleklikk; no embedding model;
private sources stay owner-only until written permission.

Uncommitted task paths before this commit: `HANDOFF.md`, `qa/session-briefs.md`,
`.claude/rules/docs.md`.
Preserve unrelated untracked agent/editor tooling. No learner data in the diff.
Blockers: none for S1–S4; ERR/HARNO/Selges keeles content waits for permission.
