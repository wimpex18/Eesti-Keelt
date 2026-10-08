# Handoff

Current task: DEV-54 — EKI EVS example phrases as public practice pools.
Branch: claude/dev-54-evs-public-pools; base origin/main faa477d. PR open for
owner review; the owner merges. No deployment performed.
What changed: outside the owner's scope (corpus hidden) drills, dictation,
read-aloud and mock reading/listening draw on `evs.phrases`; owner keeps the
corpus first, EVS only tops up. `sonajark` gets EVS noun-phrase tiles (fixed
order only: nominative/genitive attributes before a nominative noun head).
Every EVS item shows "EKI eesti-vene sõnaraamat · CC BY 4.0".
`itemref.GENERATOR_VERSION` 2→3 (owner sets the corpus cannot fill now differ).
Measured on real data, guest scope: 37 of 37 generator topics yield items
(was 30); tile pool 690, comma items 157, cloze/dictation pool 17 383.
Checks: 2550 passed/14 skipped (real data present); browser journeys
205+2 passed; typecheck clean; preview checked desktop and phone.
Next: owner reviews; after merge, deploy and run `smoke` with `deep: true`,
then confirm a guest gets `gen-stem` items on production.
Rebase notes: S1/DEV-51 may touch `eesti/cloze.py` (this PR adds only the
`listed` parameter). Planning PR 111 adds a status.md Known issue on the same
problem; keep this PR's narrower wording (reading texts still owner-only).
Uncommitted paths: none after the commit. Worktree `data/*.db` are ignored
copies used for journeys.
Blockers: none. Reading texts for public learners remain DEV-36 (C2/C6).
