# Handoff

Programme: October 2026 review → Linear DEV-35..DEV-56 (`qa/architecture-review.md`,
next-session prompts in `qa/session-briefs.md`). Sessions run in parallel
worktrees: S1 correctness (DEV-35), S2 public material (DEV-54), S4 data safety
and dependencies (DEV-37, DEV-39). Each PR edits this file; on conflict keep the
newest present-state note. The A2/B1 sittings are 7–8 Nov 2026: low-risk changes.

S1 open PRs: DEV-49 EVS glosses (#114, claude/dev-49-evs-glosses);
DEV-50 writing object case (claude/dev-50-writing-checks).
- DEV-50: `grammar.nominative_objects` flags a nimetav object after a 1st/2nd-
  person or negated verb that EKI says takes an object (`evs_object_verb`,
  filled by `cli import-evs`; PSV mida/keda). Places (*poodi*) are object
  evidence only after such a verb; spelling suggestions keep the written form.
  Precision: 1 flag in 22,613 corpus sentences (a real learner error), 1 in
  60,000 EVS phrases (bracket notation).
Next for S1: DEV-51 items (located: `forms.py` AGREEING_CASES sg in label;
pohivormid nimetav self-answers; JS/lesson blank capitals; cloze naive
distractors; placement cues and per-item results; rection label), then DEV-53
exam screens, then DEV-52 ÕS 2025 audit. DEV-51 bumps `itemref.GENERATOR_VERSION`.

Uncommitted: none after this commit. Blockers: none. S2 also edits
`eesti/evs.py`, `eesti/morph.py`, `eesti/mock.py`; the later PR rebases.
