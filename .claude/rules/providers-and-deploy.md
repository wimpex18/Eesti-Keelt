---
paths:
  - "eesti/providers/**"
  - "eesti/env.py"
  - "eesti/api/health.py"
  - "eesti/evals/**"
  - "deploy/**"
  - ".github/workflows/**"
  - "Dockerfile"
  - "wrangler.jsonc"
---

# Providers, secrets, deployment

- A third party being down never fails the build or the suite; optional steps are loud and skippable.
- Check production by asking it (`smoke`, `deep: true`), not by reading configuration. A configuration check must say "configured", not "OK".
- Name summary fields differently from per-item fields; read JSON with `jq`, not grep.
- A key must be set where the reading code runs (Cloud Run for the app). `env.load` strips `export ` and never reports a key it did not set.
- Do not retry a 429 blindly: failed attempts can count against a quota. Honour `Retry-After`.
- Before pinning a model, check the live catalogue (`cli models`) and run the eval; ids are withdrawn without notice (404/403/410).
- A router's error names what it could not route, which may be a requested capability (e.g. JSON mode), not the model.
- Eval and app prompts share their rules half (`tests/test_provider_chain.py`); keep prompt lines a real eval run justified.
- A check must run on every change to what it checks and report which version it looked at (smoke compares the image build stamp with `main`).
- In deploy scripts under `set -euo pipefail`, a failing command substitution exits before any guard; test scripts against stubbed failures — `bash -n` proves nothing.
- The local checkout is not evidence about the remote: use `git ls-remote origin`.
- Reference data goes into the image (`data/eesti.db`), never into a snapshotted learner database.
