# Architecture

One Python package, `eesti/`, serving a FastAPI app and a CLI over SQLite
databases. Vabamorf (via EstNLTK, a compiled C++ extension) generates forms at
request time, which is why the app runs in a container and not in a Worker.

## Request path

```
browser ─► Cloudflare Worker (Access, PROXY_TOKEN, state snapshots, Workers AI speech)
              └─► Cloud Run: FastAPI (eesti.app) ─► eesti/api/* ─► domain modules ─► SQLite
```

- `eesti/app.py` builds the app: origin guard (`PROXY_TOKEN`), routers, static
  page. Every route lives in `eesti/api/`; `eesti.api.ROUTERS` is the list and
  `eesti.api.paths()` derives the inventory.
- `eesti/web/` is the page: `index.html`, `app.css`, ES modules in `web/js/`
  (one per screen plus `core`, `router`, `chrome`, `media`, `state`; `main.js`
  bootstraps last) and `sw.js`. No build step.
- `deploy/worker.ts` is the Worker; `wrangler.jsonc` configures it.

## API modules

| Module | Answers |
|---|---|
| `api/deps.py` | database handles and process facts, resolved at call time |
| `api/render.py` | ids, lemmas and topics rendered for the learner |
| `api/assets.py` | page, icons, manifest, service worker |
| `api/health.py` | word list, reference row counts, corpus counts, build stamp, origin guard |
| `api/practice.py`, `api/review.py`, `api/vocab.py` | drills and grading, FSRS queue, word statuses |
| `api/grammar.py` | sentence check, word lookup and word card |
| `api/library.py`, `api/speech.py`, `api/exam.py` | material, sound (TTS/ASR/dictation/speaking), readiness |
| `api/notion.py`, `api/state.py`, `api/sources.py` | error log, snapshot export/import, licence credits |

## Domain modules

| Concern | Modules |
|---|---|
| Morphology | `morph.py` (Vabamorf), `wordlist.py` (word list, `declines`), `export.py` + `lookup.py` (form index `edge.db`) |
| Generators | `drills.py`, `cloze.py`, `conjugation.py`, `patterns.py`, `forms.py`, `verbs.py`, `punctuation.py`, `rection.py`, `wordorder.py`, `dictation.py`, `speaking.py`, `pronunciation.py`; shared shape in `item.py` |
| Planning | `learner.py` (rule evidence, weak rules, refresh, skill balance, mistakes), `planning.py` (today's plan) |
| Exam | `exam.py` (HARNO's spec and sittings, the chosen goal, `.ics`), `readiness.py`, `checkpoint.py` |
| Curriculum | `curriculum.py` (topics, prerequisites, generators, representations), `practice.py` (dispatch), `progress.py`, `placement.py`, `checkpoint.py`, `handoff.py`, `themes.py`, `overview.py`, `readiness.py` |
| Evidence | `evidence.py` (event log, replay, backfill), `itemref.py` (signed, regenerable item refs) |
| Review and vocabulary | `review.py` (FSRS), `mining.py`, `vocab.py`, `gloss.py` (stored dictionary answers), `meaning.py` (which Russian a word gets) |
| EKI data | `ekixml.py` (file reader), `psv.py`, `evs.py`, `har.py`, `ekidefs.py` (VSL, EKSS) |
| Library | `library.py`, `sources.py`, `topiclinks.py`, `difficulty.py`, `harvest/` (ERR, Selges keeles, Lihtsad uudised, EIS, HARNO, EVKK) |
| Grammar reference | `grammar.py` (EKK links), `estgec.py` (EstGEC-L2 word-order corrections) |
| Providers | `providers/grammar.py` (check chain), `llm.py`, `asr.py`, `tts.py`, `translate.py`, `sonapi.py`, `ekilex.py`, `breaker.py` |
| Evals | `evals/gec.py` (18-case grammar eval), `external.py` (grammar_et), `morphology.py` (Vabamorf vs gold), `fetch.py` |
| Operations | `config.py`, `env.py` (`KNOWN_KEYS`), `net.py`, `notion.py`, `licences.py` |
| CLI | `cli/` — `build`, `harvest`, `study`, `assess`, `report`, `ops` |

## Databases

Paths resolve at call time from `eesti/config.py`; tests redirect them.

| File | Holds | Origin |
|---|---|---|
| `data/eesti.db` | words, object cases, EKI levels and dictionaries, rections | built into the image (`cli build`, imports) |
| `data/edge.db` | form index (`forms`, `object_cases`) | built into the image (`cli export`) |
| `data/content.db` | library items, sources, topic links | harvested locally, pushed with `push-content.sh` |
| `data/events.db` | the evidence log: every learner-state change as an append-only event (`eesti/evidence.py`) | created at runtime; copied event by event into the Worker's Durable Object |
| `data/progress.db`, `review.db`, `vocab.db`, `notion.db` | projections of the log (mastery, FSRS cards, word statuses, error queue), plus stored glosses and the provider breaker | created at runtime; rebuilt from the log on restore; snapshotted by the Worker for the caches |

`data/seed_glossary.tsv` is tracked and copied into the image.

## Invariants

1. Linguistic facts come from Vabamorf or EKI data, never from a model.
2. Drill grading is string comparison against a synthesised or attested form.
   Model scores of open production are advisory evidence only
   (`docs/ai-boundaries.md`).
3. Every network dependency is optional: provider chains with timeouts and a
   persistent circuit breaker (`providers/breaker.py`); responses name the
   engine that answered.
4. Tests run offline: `tests/test_offline.py` blocks sockets, and `conftest.py`
   fails any outbound HTTP outside the `TestAgainstTheLive…` classes.
