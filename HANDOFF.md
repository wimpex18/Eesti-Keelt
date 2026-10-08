# Handoff

Current task: review workstream S4 (data safety and dependencies), Linear
DEV-37 and DEV-39. Litestream (DEV-43) waits until after the 7–8 Nov sittings.
Branch: claude/dev-39-dependency-lock, from origin/main faa477d (DEV-39).
In this branch: `requirements.lock` (uv, universal, hashed) installed by the
image, CI and eval; base image python:3.14.8-slim; weekly `python-upgrade`
workflow opens a lock PR and dispatches `tests.yml`; wrangler 4.148.0,
workers-types 5.20261008.1, axe-core 4.14.0, `overrides` sharp 0.35.5
(npm audit 0); compatibility_date 2026-10-01; EstGEC-L2 pinned to c13d04a;
Phosphor recorded as @phosphor-icons/core 2.1.1.
Checks: Python 2533 passed/14 skipped (gold data fetched); morphology gate
98.1%, identical to the unlocked env; Worker 26 passed; typecheck clean;
`wrangler deploy --dry-run` builds; lock installs wheels-only for linux x86_64.
Next: owner enables Settings → Actions → General → "Allow GitHub Actions to
create and approve pull requests", merges, then deep smoke. Not done here:
local ASR (torch/transformers/av) bump needs the ASR bench on the Mac; Node 26
waits until after 28 Oct 2026; Python 3.15 waits for estnltk wheels.
Other S4 PRs: wimpex18/Eesti-Keelt#112, #113; nightly off-Cloudflare export
(DEV-37 item 1) awaits the owner's destination choice.
Uncommitted task paths: none after this commit.
