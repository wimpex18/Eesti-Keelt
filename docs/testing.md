# Testing

## Suites

| Suite | Where | Runs in CI |
|---|---|---|
| In-process tests (~2 000) | `tests/test_*.py` | yes — `tests.yml`, Python 3.14.7, on push to `main` and PRs |
| Browser journeys (Chromium + WebKit × desktop + phone) | `tests/test_e2e_journeys.py`, `test_web_layout.py` and other Playwright tests | no — local only |
| Model eval | `cli eval`, `eval.yml` | weekly (OpenRouter), manual per lane |
| Production smoke | `smoke.yml` | after `deploy`, daily, manual |

```bash
python -m pytest tests/ -q                            # everything available on this machine
python -m pytest tests/test_e2e_journeys.py -q        # browser journeys only
```

Browser tests **skip** (never fail) without Playwright, a browser or a built
dataset. They need:

```bash
python -m eesti.cli fetch-data && python -m eesti.cli build
python -m eesti.cli export            # word card forms
python -m eesti.cli harvest-reading   # reading journeys
playwright install chromium webkit
```

Run them after any change to `eesti/web/` and before a release, with WebKit
installed — Safari's engine reports errors Chromium does not. Each test class
gets a fresh browser (a long-lived WebKit browser stalls when the Mac's display
is off).

## What the suite guarantees

- **Offline:** `test_offline.py` blocks sockets and runs every generator.
- **Correctness:** planted object-case errors are caught; correct sentences
  produce no candidates.
- **Licences:** owner-only material never appears in a public query; HARNO
  bodies stay empty.
- **Syllabus:** no topic before its prerequisite; every topic in the path once.
- **Contracts both ways:** every page call has a route and every route has a
  caller (`test_route_inventory.py`, `test_ui_contract.py`); every library
  section is reachable (`test_sections.py`).
- **Language rule:** user-facing sentences contain Cyrillic; no Estonian term
  is transliterated; every Estonian label is marked `lang="et"` and every
  Russian gloss `lang="ru"`, so a screen reader uses the right voice
  (`test_ui_language.py`).
- **Docs:** derivable counts, the tab diagram and cited file paths match the
  code (`test_docs_match_code.py`).
- **Read-only commands write nothing:** checked in subprocesses, byte for byte
  (`test_read_only_is_read_only.py`); no command creates an empty word list
  (`test_phantom_wordlist.py`).
- **Deployment wiring:** secrets are read where they are set
  (`test_secret_placement.py`); the image imports only committed files
  (`test_reference_imports.py`).

Fixtures redirect every database (`conftest.py`) and build them with the app's
own openers. CI fetches `cli fetch-bench --required-only` first; a Hugging Face
outage skips those tests rather than failing.

## Not covered

- Speaking end to end (microphone, Workers AI) — only the panel is exercised.
- Anything behind Cloudflare Access — use `smoke`.
- Notion push with a real token; the LLM branch of `/api/check` locally.
- Audio actually heard, FSRS spacing over real time, Firefox, screen readers,
  two tabs on one learner state.
