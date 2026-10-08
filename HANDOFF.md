# Handoff

Current task: DEV-54 — EKI EVS example phrases as public practice pools (S2).
Branch: claude/dev-54-evs-public-pools, merged with origin/main 82dc9d1 (#111).
PR: https://github.com/wimpex18/Eesti-Keelt/pull/115 — owner reviews and merges.
No deployment performed.
State: outside the owner's scope, drills, dictation, read-aloud and mock
reading/listening draw on `evs.phrases`; the owner's corpus comes first.
`sonajark` tiles are EVS noun phrases whose order EKK fixes (SÜ 98, 104:
genitive chains, a determiner with one adjective); the lesson gained that
point. Clause (verb-second) tiles were rejected: EKK SÜ 92 allows inversion,
so grading against EKI's order would mark correct Estonian wrong.
`itemref.GENERATOR_VERSION` is 3.
Next: owner merges #115; deploy; run `smoke` with `deep: true`; confirm a
guest gets `gen-stem` and `sonajark` items on production.
Rebase notes: open #113 (DEV-37) touches `eesti/itemref.py`; open #114
(DEV-49) touches `eesti/evs.py`. DEV-51 (S1) may touch `eesti/cloze.py`;
this branch adds only the `listed` parameter there.
Gap for public learners: verb-second word-order practice and reading texts
(DEV-36: reviewed material pipeline, permissions DEV-55).
Repo note: two invalid refs `claude/ek-review-plan 2` (heads and
origin) blocked every fetch; moved to this session's scratchpad. Their commit
4654975 is on main.
Uncommitted task paths: none after this commit. Worktree `data/*.db` are
ignored copies used for browser journeys.
Blockers: none.
