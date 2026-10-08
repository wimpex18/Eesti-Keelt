# Handoff

Programme: October 2026 review → Linear DEV-35..DEV-57 (`qa/architecture-review.md`,
next-session prompts in `qa/session-briefs.md`). Parallel worktree sessions:
S1 correctness (DEV-35), S2 public material (DEV-54, merged #115), S4 data
safety and dependencies (DEV-37, DEV-39). Each PR edits this file; on conflict
keep the newest present-state note. A2/B1 sittings 7–8 Nov 2026: low-risk changes.

S1 open PRs (owner merges; the later ones merge main in):
- DEV-49 EVS glosses #114 · DEV-50 writing object case #117 ·
  DEV-51 practice items #120 (`itemref.GENERATOR_VERSION` 4).
- DEV-53 exam screens: claude/dev-53-exam-screens. Closed registration shown
  in picker, banner and countdown; EIS tasks labelled as solved on EIS;
  HARNO file names get "Lugemine · ülesanne 2"; mock reading/listening list
  each item; the Notion queue and log button are owner-only; Home stops
  promising checked practice for reference topics. After #120 merges, swap the
  inline sentence fill in `eesti/api/exam.py` mock_result for `item.fill`.
Next for S1: DEV-52 ÕS 2025 audit. Found: EKI's ÕS-published recommendations
(Ekilex `wordEkiRecommendations`, `wwOs`) accept two rections for põhinema,
rajanema, baseeruma, tuginema and sarnanema, so EKK SÜ 65's starred frames for
them are not errors; rection drills and the writing check must stop marking
them wrong. Parallel case forms and spelling still to compare.

Uncommitted: none after this commit. Worktree `data/*.db` are ignored
reference copies. Blockers: none.
