# Testing

One learner uses this app. The suite exists to catch what would hurt that
learner (a wrong answer key, lost progress, a leaked secret, a broken screen),
not to guard the source's shape. A test that only checks source text, CSS or a
count in a doc is not added.

## Suites

| Suite | Command | Time | Runs in CI |
|---|---|---|---|
| **Fast** (default) | `python -m pytest tests/ -q -n auto` | ~15 s | yes — `tests.yml` |
| **Browser** | `python -m pytest tests/test_e2e_journeys.py -q -n auto --browser` | ~50 s | no — local only |
| **Browser, full matrix** | same, with `--all-browsers` | ~2 min | no |
| Model eval (grammar) | `cli eval --provider <lane>`, `eval.yml` | per lane | weekly (OpenRouter), manual |
| Speech eval | `cli eval --suite asr` | your own recordings | no — the set is personal and not in git |
| Production smoke | `smoke.yml` | — | after `deploy`, daily, manual |

- **Fast** is everything in process. Run it after every change. Run the
  browser file on its own: mixed into the fast run, the journeys' servers
  and the unit tests compete for the same workers and both slow down.
- **Browser** (`tests/test_e2e_journeys.py`) drives the page in Playwright at
  two pairings, the ones the owner uses: Chromium at desktop size, and WebKit
  at phone size (the installed PWA on an iPhone is WebKit). Run it after any
  change to `eesti/web/` and look at both sizes.
- **Full matrix** also runs Chromium at phone size and WebKit at desktop size.
  Use it before a release that restyles the page.

Browser tests skip (never fail) without Playwright, a browser or a built
dataset. To set them up:

```bash
python -m eesti.cli fetch-data && python -m eesti.cli build
python -m eesti.cli export            # word card forms
python -m eesti.cli harvest-reading   # reading journeys
playwright install chromium webkit
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

## Not covered

- Speaking end to end (microphone, Workers AI); only the panel is exercised.
- The Worker's behaviour: it is typechecked, not run. Anything behind
  Cloudflare Access is checked with `smoke`.
- Notion push with a real token; the LLM branch of `/api/check` locally.
- Audio actually heard, FSRS spacing over real time, Firefox, screen readers.
