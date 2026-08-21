# Source audit

Every source, API and technique surfaced in research, against what is actually
built. Kept honest: "verified" means called and observed, not read about.

## Status of every lead

### Built and verified working

| Source | Use | Evidence |
|---|---|---|
| **Vabamorf / EstNLTK** | all forms, case detection, drill answers | **98.1 % agreement** with TalTech gold data; 98 % on genitive and partitive |
| **Enriched Ekilex wordlist** (CC-BY-SA-4.0) | CEFR level + frequency, 160 316 lemmas | counts match source exactly (A1 685 / A2 997 / B1 2 509) |
| **ERR Raadio 4** | transcript **+** audio, one artefact per episode | **28 episodes, 27 087 words, all 28 with audio**, harvested and stored owner-only |
| **TalTechNLP/inflection_et** | validates Vabamorf | 1 400 rows fetched; `cli validate` |
| **TalTechNLP/grammar_et** | GEC benchmark | 1 000 error/correct pairs fetched |
| **TartuNLP TTS** | any text → listening practice | 310 KB WAV in 2.0 s, 14 voices, cached |
| **TartuNLP translation** | optional gloss | 200 in < 2 s |
| **OpenRouter** | LLM lane | catalogue probed live: 412 models, 15 `:free` |

### Verified available — all now wired

Every row in this table once read "pending". They are done; the table is kept
because *what* each one is for is still worth knowing.

| Source | Why it earns a place | Where it lives |
|---|---|---|
| **`api.sonapi.ee`** | muuttüüp (inflection type) + **`rection`** — the `rektsioon` tag directly — plus definitions and examples | `providers/sonapi.py`, read by `gloss.py`, `rection.py`, `curriculum.py` and `app.py`. Single-lookup only, one live request a second under a lock, answers kept forever in `vocab.db` so a word is asked about **once, ever**. |
| **HARNO exam material** | the best exam material that exists: per-task PDFs for every skill + listening MP3s, consultation workbooks re-uploaded 2026-01 | `harvest/harno.py`, via `cli harvest-exam`. Owner-only, **pointers only** — `body` is empty and a test asserts it. |
| **EIS `publicitems`** | official A2–C1 reading/listening tasks with feedback, no login | `harvest/eis.py`, via `cli harvest-exam`. Same pointer-only posture. |
| **ERR Lihtsad uudised** | simplified Estonian, audio + text, **weekly and ongoing** | `harvest/lihtsad.py`, via `cli harvest-news` — the one genuinely live feed in the app. |

### Rejected, with reasons

| Source | Why not |
|---|---|
| **TartuNLP grammar-api** | 500 on every call, 4 attempts over 25 min. Kept in the chain behind a 5 s timeout and a circuit breaker; never depended on. Its `/v2` explanations are Estonian-only with no language parameter. |
| **TartuNLP speech-to-text** | repo archived Oct 2024, `/docs` 404. Never was a hosted API. |
| **ELLE / Tekstihindaja** | API real and maintained (`/api/status` → v26.6.1) but both useful endpoints 500. Reviews report it calling random characters "Kõik on õige". Second opinion at best. |
| **`grammar-api` self-hosted** | defaults point at `artemis20.hpc.ut.ee` — internal UT hosts, not routable. |
| **`TartuNLP/gec-llm`** | only Estonian-tuned option, but 7B-class. Disproportionate to a few sentences a day. |
| **Sõnaveeb scraping** | maintainers explicitly ask people not to. The wordlist removes any need. |
| **Sõnastik app** | closed, no export. Already covered — keep using it for lookups. |
| **Pronunciation scoring** | forced alignment gives timings, not correctness. EKI already publishes free pronunciation exercises. |
| **Generic GEC sites** | multilingual engines with no Estonian case competence; will not catch `raamatut`/`raamatu`. |

## Techniques from the research, and where they landed

| Technique | Outcome |
|---|---|
| Provider chain + circuit breaker | built; breaker verified (3rd call instant vs 7.2 s) |
| Deterministic grading | built; string comparison, no model |
| Vabamorf as sensor not oracle | built; reports the case written, never judges telicity |
| Build-time synthesis → edge data | built; 411 349 forms, 98 % token coverage |
| Licence as an access-control column | built; tested that owner-only cannot leak |
| Probe models before pinning | built; `cli models` |
| Recall **and** precision in evals | built; half the eval set is correct Estonian |

## The four exam parts

Scoring is 25 points each, pass ≥ 60 % overall **and no part at zero** — so a tool
that perfects one part and ignores another can still fail you.

This table was written before version 1.0 and described the app as it stood
then — "no player UI yet", "no reader UI yet", "not built" — for three parts
that all shipped. Corrected 2026-08-21 against the running app. **`status.md`
is the live inventory**; this is kept only because the *ordering* argument
below still holds.

| Part | State |
|---|---|
| **Kirjutamine** | working — check + Russian explanations + obj-case priority, plus back-translation |
| **Harjutused** | working — generated drills over 4 rules; 1 672 nouns carry a distinct genitive/partitive |
| **Kuulamine** | working — dictation graded word-by-word, TTS on any text at 0.7×, 12 voices |
| **Lugemine** | working — 349 texts, click-to-look-up, ranked by known-word coverage |
| **Rääkimine** | working — the exam's paired question bank with TTS voicing the other side; deliberately not scored |

## Next, in order

1. **Reader / listener UI** — the material exists; the views do not.
2. **More harvesters** — Lihtsad uudised (weekly, ongoing), EIS task pages, and
   seeds for the other two ERR series (`ekeel`, `keelekodi`).
3. **HARNO fetch script** — owner-only, git-ignored, into `sources`.
4. **Notion write-back** to the existing `Vead` database.
5. **Verb-form drills** — machinery proven, template work.
6. **Cloudflare deploy** — Worker + D1 + Pages, behind Access.

## Harvesting note

ERR's archive index renders its episode list in JavaScript, and a headless
browser cannot reach the host from a sandboxed session (ERR_CONNECTION_RESET,
with or without the proxy, while plain curl succeeds). The harvester therefore
walks the series as a **graph**: every episode page carries an `ld+json` ItemList
of siblings, so a crawl seeded with one known episode reaches the rest using
ordinary requests. Episodes are deduplicated by transcript hash, because ERR
publishes the same episode under several content ids — one series returned
episode 21 three times at three different ids.

## Open questions

- **D1 import of 411 K rows** — may need batching, or ship as read-only SQLite in R2.
- **Auth** — Cloudflare Access is what makes the HARNO half legitimate. Not optional.
- **Mobile input** — õ/ä/ö/ü behind a keyboard layer would make drilling miserable.
- **Which model** — unanswerable without a key. `cli eval` is built and waiting.
