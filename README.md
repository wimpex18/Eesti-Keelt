# Eesti-Keelt

A personal tool for learning Estonian and preparing for the **A2/B1 tasemeeksam**.
Single user, runs locally, no accounts, no cloud.

Built around one documented weakness: choosing **partitive (osastav)** where a
completed, whole object needs **genitive (omastav)** — the only tag past the "3+
occurrences" threshold in my error log.

## Offline-first, on purpose

While researching this, four separate research-hosted endpoints (TartuNLP's
grammar API `/v1` and `/v2`, ELLE's CEFR predictor and corrector) were all
returning HTTP 500, while every dataset and static asset worked fine. That is the
normal state of grant-funded infrastructure, not an outage.

So the core loop — vocabulary, morphology, drills, grading — **needs no network at
all**. Online services are optional enrichment behind a provider chain with short
timeouts and a circuit breaker, and the UI always shows which engine answered.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m eesti.cli fetch-data   # ~2.8 MB word list, one time
.venv/bin/python -m eesti.cli build        # import + index (a few seconds)
.venv/bin/python -m eesti.cli serve        # http://127.0.0.1:8000
```

Terminal use, if you prefer:

```bash
.venv/bin/python -m eesti.cli drill -n 10 --rules negation
.venv/bin/python -m eesti.cli check "Ma lugesin eile raamatut läbi."
```

For full grammar explanations in Russian, set an API key — everything else works
without it:

```bash
export ANTHROPIC_API_KEY=...
.venv/bin/pip install anthropic
```

## What it does

**Kirjutamine** — paste Estonian, get corrections. Object-case errors are sorted
first and highlighted separately; explanations are in Russian but keep the Estonian
grammar terms (`osastav`, `omastav`) so the exam vocabulary sticks.

**Harjutused** — generated object-case drills, filterable by rule and CEFR level:

| Rule | Case | Example |
|---|---|---|
| `negation` | partitive, no exceptions | *Ma ei ostnud **piletit**.* |
| `completed` | genitive | *Ma leidsin **rahakoti** üles.* |
| `ongoing` | partitive | *Ta luges **aruannet** tund aega.* |

Grading is deterministic — no model involved, so it is right every time and free.

**Kuulamine** — any text becomes Estonian audio via TartuNLP TTS (12 voices),
default 0.7× for learners. Cached on disk, so replay is instant and offline.

## How the forms are trusted

Two sources, and the split matters:

- **CEFR levels + frequency** come from
  [Estonian-Wordlist-Enriched-Ekilex](https://github.com/KristjanPikhof/Estonian-Wordlist-Enriched-Ekilex)
  (CC-BY-SA-4.0, derived from Ekilex/EKI). Using it means **never scraping
  Sõnaveeb**, whose maintainers explicitly ask people not to batch-request it.
- **Inflected forms** come from **Vabamorf synthesis**, not from that dataset's
  79 MB forms file. That file's per-word lists are de-duplicated, so identical
  forms collapse and position can no longer be mapped to a case (`auto` has 13
  singular entries, not 14). Vabamorf returns *labelled* cases, round-trip
  validated: each candidate is re-analysed and kept only if it reads back as the
  requested lemma in the requested case.

Only nouns whose genitive and partitive genuinely **differ** are drilled — 1,741
of them at A1–B1. For `maja`/`maja` there is no wrong answer, so such an item
would measure nothing.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

The suite is the regression gate for the one thing that matters: it checks planted
errors are caught **and** that sentences without objects produce no candidates.
A checker that flagged every partitive would pass the first half while teaching
exactly the wrong rule. Runs fully offline.

## Deliberately not built

- **Pronunciation scoring** — forced alignment yields timings, not correctness,
  and EKI already publishes free
  [pronunciation exercises](https://sonaveeb.ee/pronunciation-exercises/).
- **A dictionary / flashcard app** — Sõnaveeb, Sõnastik and Anki do it better.
- **A notes system** — Notion stays the system of record.

## Not in this repo

Exam material from [harno.ee](https://harno.ee/eesti-keele-tasemeeksamid) (task
PDFs and listening MP3s) is HARNO copyright. Fine for personal study, not for
redistribution — `data/exam/` is git-ignored. Fetch it yourself.

## Roadmap

Phase 2 (reading + listening) and phase 3 (speaking) are scoped but not built:
harvesting the ~170 ERR Raadio 4 episodes that pair transcripts with audio, the
weekly *Lihtsad uudised* feed, and a question bank shaped like the real — and
notably **paired** — B1 speaking exam.
