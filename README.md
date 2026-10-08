# Grove

**Grove** (the Eesti-Keelt repository) is a free educational app for learning
Estonian. The MVP supports Russian-speaking learners and **A2/B1 tasemeeksam**
preparation. The product direction includes learning from the beginning,
flexible entry and skipping, and English and Ukrainian explanation languages;
the confirmed brief is in [`PRODUCT.md`](PRODUCT.md), and current coverage is
in [`docs/status.md`](docs/status.md). Open the app and practise as a guest, or create an
account in **Profiil** to keep your own progress between devices.

Drills are generated from an Estonian word list with the Vabamorf morphological
analyser and graded by code. Models explain corrections, support open writing
and conversation, and transcribe speech. Model feedback is labelled and does
not set mastery or FSRS ratings.

## Features

- **Kodu** — one next lesson or current session, with beginning, chosen-start
  and bounded grammar-check entry routes.
- **Kursus** — ordered grammar topics, source-backed rules, five-item guided
  sessions, checkpoints and checked test-out. Familiar topics can be skipped
  and restored without changing mastery; **Vaba harjutus** is unrecorded.
- **Lugemine** — simplified Estonian texts ranked by how many of their words
  you know; click any word for its forms, meaning and level.
- **Kuulamine** — graded dictation, TTS on any text, radio episodes.
- **Rääkimine** — paired-exam questions, read-aloud comparison, spoken answers,
  conversation practice, and a private in-app speech review set during local use.
- **Kirjutamine** — grammar check with explanations in Russian, back-translation,
  and a queue to the Notion error log.
- **Kordamine** — FSRS review of mistakes and mined words, with EKI's
  Estonian–Russian example phrases built from tiles. **Sõnavara** leads with
  five-word practice; the collection supports known/ignored choices and lookup.
- **Eksam** — optional timed practice, official materials and per-part readiness;
  the owner’s library supports HARNO tasks and reviewed native reading exercises.

Reading, listening, speaking and writing stay reachable throughout the app.
Russian instructional support is current; the A0 starting recommendation is not
yet a complete beginner course. Equivalent English/Ukrainian content remains
release work, as recorded in `docs/status.md`.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.lock
.venv/bin/python -m eesti.cli fetch-data && .venv/bin/python -m eesti.cli build
.venv/bin/python -m eesti.cli export
.venv/bin/python -m eesti.cli serve          # http://127.0.0.1:8000
.venv/bin/python -m pytest tests/ -q -n auto
```

No API key is needed for drills, reading and review. Keys and where they go:
[`docs/setup.md`](docs/setup.md).

Terminal practice is available too: `cli placement`, `cli practice`,
`cli review`, `cli checkpoint`, `cli status`, `cli check "…"` (see
`python -m eesti.cli --help`).

## Deployment

Google Cloud Run (the app) behind a public Cloudflare Worker (optional in-app accounts,
state snapshots, speech). Speech is transcribed on the owner's Mac mini when it
is on ([`deploy/home-asr/README.md`](deploy/home-asr/README.md)), else by
Workers AI. See [`docs/deploy.md`](docs/deploy.md) for setup and cost limits.

## Documentation

- [`PRODUCT.md`](PRODUCT.md) · [`DESIGN.md`](DESIGN.md) · [`docs/design-research.md`](docs/design-research.md)
- [`docs/status.md`](docs/status.md) — what works, what is missing, known issues
- [`docs/architecture.md`](docs/architecture.md) · [`docs/app-structure.md`](docs/app-structure.md)
- [`docs/curriculum.md`](docs/curriculum.md) · [`docs/sources.md`](docs/sources.md)
- [`docs/ai-boundaries.md`](docs/ai-boundaries.md) · [`docs/ai-providers.md`](docs/ai-providers.md) · [`docs/speaking.md`](docs/speaking.md)
- [`docs/testing.md`](docs/testing.md) · [`docs/setup.md`](docs/setup.md) · [`docs/deploy.md`](docs/deploy.md)
- [`docs/exam-native.md`](docs/exam-native.md) · [`docs/asr-evaluation.md`](docs/asr-evaluation.md)

Agent instructions: [`AGENTS.md`](AGENTS.md).
