# Handoff

Current task: Grove rebranding, public access and requested skill cleanup.
PR: https://github.com/wimpex18/Eesti-Keelt/pull/107
Branch: `codex/rebrand-public-access`; base: `main` (465943f).
Implemented: leaf mark, regenerated platform/social assets and leaf-unfurl opening.
Anonymous requests remain guests; public sign-up creates separate learner accounts.
Existing owner state is preserved; protected operator bootstrap provisions an owner.
Nonowner corpus reads and private recordings are restricted; audio caches are scoped.
Deployment waits for a public-safe origin, opens only this Worker hostname and verifies it.
Docs/source credits are current; obsolete closed-access follow-up and Impeccable files are removed.
QA/product and WanderAlt copies are on the user’s computer, inaccessible remotely.
Local cleanup: `python3 deploy/remove-local-skills.py` previews; `--apply` removes matches.
Python suite: 2,475 passed/34 skipped; added cleanup/public-access regressions also pass.
Typecheck and 24 Worker tests pass. Chromium: 171 passed/23 skipped, one dock-timing failure.
That fixture waits for the dock transition; rerun of all 7 drag journeys passes.
Deep-link/icon rerun: 12 passed; Profile rerun: 22 passed.
All 11 tabs inspected at desktop, phone portrait/landscape and tablet, both themes.
Next: user merges PR #107; deployment opens and verifies public access.
Uncommitted paths: none after this handoff commit.
Deployment limitation: no runtime credentials here; live URL still redirects until merge/deploy.
Cloudflare deployment token requires Account Access: Apps and Policies Write.
