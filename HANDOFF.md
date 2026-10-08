# Handoff

Programme: October 2026 review → Linear DEV-35..DEV-56 (`qa/architecture-review.md`,
`qa/session-briefs.md`). One open PR per session; no new Linear issues.
A2/B1 sittings 7–8 Nov 2026: low-risk changes.

S1 correctness (epic DEV-35): one branch, claude/dev-35-correctness, one PR,
merged with main after S2 (#115) and S4 (#122). It supersedes PRs #114, #117,
#120, #121 (closed). Contents:
- DEV-49: EVS homographs chosen by EKI's level list; negation-only senses
  dropped; glossed-word counter over all offline sources.
- DEV-50: nimetav-object writing check (`evs_object_verb` from `cli import-evs`);
  places not offered as objects; spelling suggestions keep the written form.
- DEV-51: item labels, no self-answering nimetav, sentence-initial capitals
  (`item.fill`, `blankForm`), no non-word choices, placement cues and review.
  `itemref.GENERATOR_VERSION` 4.
- DEV-53: closed registration shown; EIS tasks labelled; readable HARNO names;
  mock item review; Notion log owner-only.
- DEV-52: SÜ 65 contrasts EKI now records are not drilled, flagged or reviewed
  (`rection.EKI_ACCEPTS`); free-writing rection check covers verbs only; EKK
  credited as 2007, © Erelt, Erelt, Ross.
Follow-ups (comments on DEV-51, DEV-52): sentence-frame variety; EKI's parallel
inflected forms beyond Vabamorf (*rikkat*). DEV-57/DEV-58 were opened before
the no-new-issues rule: owner decides whether to cancel them.
After merge: Docker rebuild re-imports EVS; deploy; `smoke` with `deep: true`.
Uncommitted: none after this commit. Blockers: none.
