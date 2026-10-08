# Testing

The app keeps permanent state separately for every signed-in account and gives
each guest a throwaway sandbox. The suite checks isolation, lost progress, a
leaked secret and broken screens. Narrow source-contract tests pin the Worker
and FastAPI's shared route and identity boundaries because they run in separate
runtimes; other tests exercise behavior instead of checking CSS or doc counts.

## Suites

| Suite | Command | Time | Runs in CI |
|---|---|---|---|
| **Fast** (default) | `python -m pytest tests/ -q -n auto` | ~10 s | yes — `test` job |
| **Worker** | `npm run test:worker` | ~2 s | yes — `worker` job |
| **Browser** | `python -m pytest tests/test_e2e_journeys.py -q --browser -n 4` | ~2 min | yes — one `journeys` job per engine, skipped when only Markdown under `qa/`, `docs/`, `.claude/` or the root changed; reading journeys skip without the corpus |
| **Browser, full matrix** | same, with `--all-browsers` | longer than the default pairings | no |
| Model eval (grammar) | `cli eval --provider <lane>`, `eval.yml` | per lane | weekly (Workers AI), manual |
| Speech eval | `cli eval --suite asr [--engine A --engine B]` | your own recordings | no — the set is personal and not in git |
| Production smoke | `smoke.yml` | — | after `deploy`, daily, manual |

- **Fast** is everything in process. Run it after every change. Run the
  browser file on its own: mixed into the fast run, the journeys' servers
  and the unit tests compete for the same workers and both slow down.
- **Browser** (`tests/test_e2e_journeys.py`) drives the page in Playwright at
  two pairings, the ones the owner uses: Chromium at desktop size, and WebKit
  at phone size (the installed PWA on an iPhone is WebKit). Run it after any
  change to `eesti/web/` and look at both sizes.
- **Full matrix** also runs Chromium at phone size and WebKit at desktop size.
  Use it before a release that restyles the page. `--engine chromium` or
  `--engine webkit` runs one engine's journeys; CI runs the two in parallel.
  More than four workers on one machine starves the journeys' servers and
  their waits time out; CI's runners have four.
- `pytest.ini` makes misspelt markers and ini keys errors and strict-xfails.
  CI installs with `uv` from `requirements.lock`, caches the Playwright
  browser and the built word list, and cancels a run a newer push supersedes.
- The journeys' server writes its log to a file in its own working directory
  so verbose API logging cannot block the browser run.
- CI builds the compressed web assets with `npm run build:web` and runs the
  journeys with `EESTI_WEB_BUILD=1`, matching the container's bundle. Locally,
  run `npm ci && npm run build:web` followed by
  `EESTI_WEB_BUILD=1 python -m pytest tests/test_e2e_journeys.py --browser -q`.
  Rebuild after web edits. Ordinary `cli serve` continues serving editable modules.

Every screen is also run through **axe** (WCAG 2.2 A and AA tags) at both
viewports, because the interface leans on markup to say which language a
string is in, and a screen reader is the one reader that cannot guess. It
skips when `axe-core` is not installed.

Browser tests skip (never fail) without Playwright, a browser or a built
dataset. To set them up:

```bash
python -m eesti.cli fetch-data && python -m eesti.cli build
python -m eesti.cli export            # word card forms
python -m eesti.cli harvest-reading   # reading journeys
playwright install chromium webkit
npm install                           # axe-core, for the accessibility check
```

## What the suite guarantees

- **Answer keys:** generated forms round-trip through Vabamorf. Planted
  object-case errors are caught, and correct sentences produce no candidates
  (`test_objcase.py` and the generator tests).
- **Grading:** the server grades from the signed item it issued
  (`test_evidence.py`, `test_api_path.py`).
- **Progress is not lost:**
  - replaying the evidence log reproduces every learner table;
  - a fresh instance rebuilds from an imported log;
  - importing twice changes nothing (`test_evidence.py`);
  - the snapshot never lets an empty export win (`test_api_path.py`,
    `test_state_coverage.py`).
- **Offline:** `test_offline.py` blocks sockets and runs every generator.
  Browser journeys verify signed-pack replay and the uncached-shell recovery
  screen: readable device width, retry while offline, and return to the app
  after connectivity resumes. The recovery test disconnects a dedicated proxy
  origin rather than using Playwright's offline switch, which currently rejects
  WebKit service-worker navigation ([upstream issue 42775](https://github.com/microsoft/playwright/issues/42775)).
- **Language rule:**
  - user-facing sentences are Russian;
  - no Estonian term is transliterated;
  - labels carry the right `lang` (`test_ui_language.py`).
- **Page ↔ API:** every endpoint the page calls exists and accepts that verb
  (`test_ui_contract.py`).
- **Secrets and deploy:**
  - secrets are read where they are set (`test_secret_placement.py`);
  - the Worker refuses the back channel (`test_origin_guard.py`).
- **Docs:** curriculum counts, the tab diagram and cited file paths match the
  code (`test_docs_match_code.py`).

Fixtures redirect every database (`conftest.py`) and build them with the app's
own openers. Outbound HTTP fails at once, except in the `TestAgainstTheLive…`
classes, which skip when their service is down.

## Live service, speech and recovery checks

`python -m eesti.cli provider-health --timeout 5` probes both GEC POST
contracts with canned text. Health is separate from correction quality, and an
outage exits 2 without failing the offline suite. The weekly eval checks Workers AI, the production lane. A green eval workflow
can still mean below threshold or unmeasured; read its report.

Speech compares named recognisers on the same manually verified recordings.
Follow `docs/asr-evaluation.md`: a recorder prompt is not ground truth; a changed
audio/text hash invalidates its review. Unit tests cover WER/CER, aligned false
acceptance, morphology tokens, incomplete coverage and reference isolation.
They do not establish real learner recognition quality or local model speed.

`python -m eesti.cli verify-backup /private/export.jsonl` validates replay in
temporary databases, twice. Tests cover unsupported events/versions, duplicates,
missing backfill marker and keeping live stores unchanged. This proves the
supplied export is replayable, not that every remote event reached the export.

`npm run test:worker` runs the Worker routes and Durable Object methods under
Node with isolated SQLite stores and a simulated origin. It verifies that a
replacement boot cannot acknowledge a lost event, cursor shortcuts use the
same boot, transient copying failures retry, and speech follows the same
acknowledgement. The Worker job runs these tests and typechecking in CI.

## Not covered

- Speaking end to end (microphone, Workers AI); only the panel is exercised.
- Production authentication: account helpers run under Node and browser
  journeys use a Worker-shaped response boundary. The actual Worker runtime is
  checked separately with `wrangler dev` and the deployed app with `smoke`;
  tests never create an account in production.
- Notion push with a real token; the LLM branch of `/api/check` locally.
- Audio actually heard, FSRS spacing over real time, Firefox, screen readers.
