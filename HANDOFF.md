# Handoff

Current task: PR #132 (`claude/s7f-design-review`) applies the S7R review to
`DESIGN.md` (S7F) and adds its "Fixed and open" section, so redesign sessions
keep the rules and may improve the proposal. It also refreshes the notes after
step 0 (R1). It waits for the owner's merge.

On `main`: step 0 of `qa/opus-sessions.md` is merged: the material pipeline
(S1, `docs/material.md`), generators for negation, modals, the future and EVS
gaps (S5), HARNO reading and listening task types (S6), and the Interlinear spec
with the rename to Klint (S7). Haiku 5.5 leads the grammar and tutor chain once
its key is on Cloud Run (ADR-0008).

Next: after #132 merges, S2 (unit dialogues and texts) and S10 (tokens and
shell) are ready; start each with "Run <ID> from qa/opus-sessions.md." in its
own session. If only one runs, S2 first: exam reading task 4 waits for its
checked texts (sittings 7–8 Nov 2026).

Owner operations: re-run the `deploy` workflow (its run after #131 failed the
shell check, most likely before Cloud Build had replaced the origin;
`docs/status.md`); then the outstanding list in `qa/architecture-review.md`
(Haiku key on Cloud Run with a spend limit, `cli import-evs` in local serving
checkouts, the Klint trademark search and `klint.ee`, permission requests,
backup verification). Re-subscribe to reminders on each device.

Follow-ups from step 0 now sit in `qa/architecture-review.md` (material, course
structure, exam fidelity) and `docs/status.md`. Linear is paused (owner, 9 Oct):
follow-ups live here, in PRs and in `qa/sessions/`.
Uncommitted paths: none after the commit. No secrets revealed.
