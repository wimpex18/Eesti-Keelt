# Source audit

Every source, API and technique surfaced in research, against what is actually
built. Kept honest: "verified" means called and observed, not read about.

## Status of every lead

### Built and verified working

| Source | Use | Evidence |
|---|---|---|
| **Vabamorf / EstNLTK** | all forms, case detection, drill answers | **98.1 % agreement** with TalTech gold data; 98 % on genitive and partitive |
| **Enriched Ekilex wordlist** (CC-BY-SA-4.0) | CEFR level + frequency, 160 316 lemmas | counts match source exactly (A1 685 / A2 997 / B1 2 509) |
| **TalTechNLP/inflection_et** | validates Vabamorf | 1 400 rows fetched; `cli validate` |
| **TalTechNLP/grammar_et** | GEC benchmark | 1 000 error/correct pairs fetched |
| **TartuNLP TTS** | any text → listening practice | 310 KB WAV in 2.0 s, 14 voices, cached |
| **TartuNLP translation** | optional gloss | 200 in < 2 s |
| **OpenRouter** | LLM lane | catalogue probed live: 412 models, 15 `:free` |

### Verified available, not yet wired

| Source | Why it earns a place | Status |
|---|---|---|
| **`api.sonapi.ee`** | muuttüüp (inflection type) + **`rection`** — the `rektsioon` tag directly — plus definitions and examples | verified 200; registered in `sources.py`; single-lookup only |
| **HARNO exam material** | the best exam material that exists: per-task PDFs for every skill + listening MP3s, consultation workbooks re-uploaded 2026-01 | registered **owner-only**; fetch script pending |
| **EIS `publicitems`** | official A2–C1 reading/listening tasks with feedback, no login | verified 200, plain HTML form, `aine=R`; harvester pending |
| **ERR Raadio 4** (~170 episodes) | transcript **+** audio in one page; two episodes cover exactly the obj-case contrast | episode 28 verified (~2 500-word transcript); harvester pending |
| **ERR Lihtsad uudised** | simplified Estonian, audio + text, **weekly and ongoing** | verified live (7 Aug 2026); harvester pending |

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

| Part | State |
|---|---|
| **Kirjutamine** | working — check + Russian explanations + obj-case priority |
| **Grammatika** | working — generated drills, 3 rules, 7 256 drillable lemmas |
| **Kuulamine** | partial — TTS on any text works; ERR/HARNO audio not yet harvested |
| **Lugemine** | not built — needs the ERR + EIS harvesters |
| **Rääkimine** | not built — and deliberately last (the real task is **paired**) |

## Next, in order

1. **Harvesters** — ERR (one-time, ~170 episodes), Lihtsad uudised (weekly), EIS
   task pages. This lights up Lugemine and most of Kuulamine from one build.
2. **HARNO fetch script** — owner-only, git-ignored, into `sources`.
3. **Notion write-back** to the existing `Vead` database.
4. **Verb-form drills** — machinery proven, template work.
5. **Cloudflare deploy** — Worker + D1 + Pages, behind Access.

## Open questions

- **D1 import of 411 K rows** — may need batching, or ship as read-only SQLite in R2.
- **Auth** — Cloudflare Access is what makes the HARNO half legitimate. Not optional.
- **Mobile input** — õ/ä/ö/ü behind a keyboard layer would make drilling miserable.
- **Which model** — unanswerable without a key. `cli eval` is built and waiting.
