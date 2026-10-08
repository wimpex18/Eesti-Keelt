# Handoff

Programme: October 2026 review → Linear DEV-35..DEV-57 (`qa/architecture-review.md`,
next-session prompts in `qa/session-briefs.md`). Sessions run in parallel
worktrees: S1 correctness (DEV-35), S2 public material (DEV-54), S4 data safety
and dependencies (DEV-37, DEV-39). Each PR edits this file; on conflict keep the
newest present-state note. The A2/B1 sittings are 7–8 Nov 2026: low-risk changes.

S1 open PRs (owner merges; the later ones rebase on the earlier):
- DEV-49 EVS glosses: #114, claude/dev-49-evs-glosses (CI green).
- DEV-50 writing object case: #117, claude/dev-50-writing-checks.
- DEV-51 practice items: claude/dev-51-practice-items. Agreement label and
  postposition nouns, no nimetav principal-forms item, sentence-initial
  capitals (`item.fill`, `blankForm`), non-word distractors become typed
  items, broken-word sentences skipped, rection label, placement cues and
  per-item review. `itemref.GENERATOR_VERSION` is 3 (S2 may bump it too).
  Frame variety split to DEV-57.
Next for S1: DEV-53 exam screens (closed-registration sitting in `exam.py`
SESSIONS/`exam.js` picker; interactive official tasks without options; raw
PDF names; mock item review; Notion queue owner-only; Home theory promise),
then DEV-52 ÕS 2025 audit.

Uncommitted: none after this commit. Blockers: none. S2 also edits
`eesti/evs.py`, `eesti/morph.py`, `eesti/mock.py`, `eesti/web/js/core.js`,
`eesti/web/js/path.js`, `eesti/itemref.py`; the later PR rebases.
Known flaky journeys: phone one-item drill (CI) and WebKit sign-up (local);
both pass on rerun.
