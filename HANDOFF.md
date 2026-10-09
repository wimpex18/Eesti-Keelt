# Handoff

Current task: operator maintenance PR on codex/operator-maintenance; owner review/merge pending.
Changes: Intel home-ASR installer pins PyAV 18.1.0; public-access checks use
Grove-deploy/1.0 for JSON and shell requests. Regression tests cover both
processor branches, package-install failure and credential-free public checks.
Docs describe the dependency constraint and remove the resolved Access issue.
Validation: 39 focused tests passed in both working and clean checkouts;
typecheck, zsh syntax and diff checks passed. Prior code fails both regressions.
Isolated faster-whisper 1.2.1 / PyAV 18.1.0 decoded a synthetic WAV successfully.
Next: owner reviews/merges the PR; merge runs the Worker deployment workflow.
Production: public access restored; deep smoke passed with repaired Intel ASR.
Backup bucket/configuration set up; nightly trigger ran, but no object was found.
Owner stopped backup checks; recovery verification remains pending.
Runtime SA retains project Editor permission, which permits backup deletion;
no IAM changes made. Mac mini was off overnight; home speech needs it awake.

Task changes committed: installer, public-access checker, regression tests and docs.
Uncommitted task paths: none.
Preserve unrelated package.json and untracked .agents/, .claude/agents/,
.claude/settings.local.json, .claude/skills/, .codex/, .github/agents/,
.github/hooks/, .github/skills/, .impeccable/decisions/learning-redesign.json,
.impeccable/live/. No secrets revealed. Mac mini already has the compatible PyAV version.
