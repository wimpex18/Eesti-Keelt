# Eesti-Keelt

An Estonian learning app for Russian speakers preparing for the
**A2/B1 tasemeeksam**.

Drills are generated from an Estonian word list with the Vabamorf morphological
analyser and graded by code. Models explain corrections, support open writing
and conversation, and transcribe speech. Model feedback is labelled and does
not set mastery or FSRS ratings.

## Features

- **Rada** — the A1→B1 grammar path: prerequisite-ordered, mastery-gated, with
  placement, test-out and checkpoints; **Vaba harjutus** runs the same drills on
  any topic, unrecorded.
- **Lugemine** — simplified Estonian texts ranked by how many of their words
  you know; click any word for its forms, meaning and level.
- **Kuulamine** — graded dictation, TTS on any text, radio episodes.
- **Rääkimine** — paired-exam questions, read-aloud comparison, spoken answers,
  conversation practice, and a private in-app speech review set during local use.
- **Kirjutamine** — grammar check with explanations in Russian, back-translation,
  and a queue to the Notion error log.
- **Kordamine** — FSRS review of mistakes and mined words, with EKI's
  Estonian–Russian example phrases built from tiles; **Sõnavara** lists words by
  CEFR level and frequency.
- **Eksam** — readiness per exam part, timed practice, HARNO material in-app,
  and two reviewed native reading exercises.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
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

Google Cloud Run (the app) behind a Cloudflare Worker with Access (login,
state snapshots, speech). Speech is transcribed on the owner's Mac mini when it
is on ([`deploy/home-asr/README.md`](deploy/home-asr/README.md)), else by
Workers AI. See [`docs/deploy.md`](docs/deploy.md) for setup and cost limits.

## Documentation

- [`docs/status.md`](docs/status.md) — what works, what is missing, known issues
- [`docs/architecture.md`](docs/architecture.md) · [`docs/app-structure.md`](docs/app-structure.md)
- [`docs/curriculum.md`](docs/curriculum.md) · [`docs/sources.md`](docs/sources.md)
- [`docs/ai-boundaries.md`](docs/ai-boundaries.md) · [`docs/ai-providers.md`](docs/ai-providers.md) · [`docs/speaking.md`](docs/speaking.md)
- [`docs/testing.md`](docs/testing.md) · [`docs/setup.md`](docs/setup.md) · [`docs/deploy.md`](docs/deploy.md)
- [`docs/exam-native.md`](docs/exam-native.md) · [`docs/asr-evaluation.md`](docs/asr-evaluation.md)

## Licences

The word list is CC-BY-SA-4.0; EKI dictionaries are CC-BY-4.0 with attribution.
Keep source attribution for every dataset. Details in
[`docs/sources.md`](docs/sources.md).

Agent instructions: [`AGENTS.md`](AGENTS.md).
