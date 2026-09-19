# Status

What the app does today, what it does not, and the known issues. Counts marked
as checked are asserted by `tests/test_docs_match_code.py`; update this file in
the same change that makes it untrue.

## What works

| Area | State |
|---|---|
| **Drills** | 26 of 36 curriculum topics generate items: object case, verb forms, conjugation, locative cases, comparison, numerals, question words, word order, punctuation, rection. |
| **Grading** | Deterministic everywhere; no model decides correctness. |
| **Path** | Prerequisite-ordered topics, mastery gate, placement and test-out, end-of-level checkpoints, blocked → interleaved handoff. |
| **Review** | FSRS-6 over items answered wrong and words mined from reading. |
| **Reading** | Selges keeles texts and the weekly ERR *Lihtsad uudised* feed; click-to-look-up; recommended by the share of running words within reach (known, or A1–A2 on the word list), at least 80 %, shorter first (`docs/curriculum.md`). |
| **Vocabulary** | `Sõnavara` lists the word list by CEFR level and part of speech, commonest first; the word card sets a status. |
| **Meaning** | **294 Russian glosses ship with the app** (`data/seed_glossary.tsv`). Russian order: seed → live dictionary → EKI EVS → EKI HAR (`eesti/meaning.py`). Definitions: EKI PSV → live → VSL → EKSS. |
| **Live dictionary** | EKI's Ekilex API when `EKILEX_API_KEY` is set, otherwise the Sõnaveeb mirror; answers stored once per word. |
| **Rules** | 25 of 26 drillable topics link to the handbook. `kusisonad` has none, deliberately: no EKK section covers question words. |
| **Writing** | Grammar check through the provider chain (`docs/ai-providers.md`), plus deterministic spelling, subject–verb agreement and rection checks; back-translation; corrections queue for the Notion `Vead` log. |
| **Listening** | Dictation from the corpus (graded), TartuNLP TTS on any text, ERR episode audio. |
| **Speaking** | Paired-exam question bank with TTS, read-aloud of short sentences made of words within reach, with comparison, and open-answer feedback over the transcript (`docs/speaking.md`). |
| **Readiness** | Four exam parts reported separately with reasons in Russian; never one total. |
| **Offline** | Installable PWA; opens without a connection and says what it cannot do. The API is never cached. |
| **Deployment** | Cloud Run behind a Cloudflare Worker + Access; learner state snapshotted across cold starts; all EKI reference data and the reading corpus present. |

51 route handlers across `eesti/api/` serve 43 API endpoints; every endpoint
has a caller (`tests/test_route_inventory.py`).

## What is missing

### 10 curriculum topics have no generator

```
tahestik  lauseehitus  asesonad  astmevaheldus  kaassonad  sidesonad
maarsonad  tulevik  uhendverbid  liitsonad
```

They appear in the syllabus as reference topics and do not gate the path. The
source of truth is `[t.id for t in TOPICS if not t.generator]`.

- `astmevaheldus` is intentionally reference-only; its contrast is drilled via
  `gen-stem`.
- `asesonad` (pronouns) cannot be generated: Vabamorf's pronoun paradigms are
  wrong (`mina` → genitive `mina`). It needs a hand-written table **with a cited
  source**; none is in the repo, and TalTech's `inflection_et` has no pronouns.
- `uhendverbid` and `liitsonad` were checked for the attested-corrections
  approach behind `word-order`; the corpus lacks enough marked examples.

### Not built, by decision

- **Acoustic pronunciation scoring** — the app links to EKI's free
  pronunciation exercises instead.
- **Local ASR in production** — recognition runs on Cloudflare Workers AI; the
  speaking panel says the recording leaves the device. Local whisper.cpp works
  only under `cli serve`.
- **The `tuttav` word status has no control** — it sits on the same side of
  "settled" as `õpin`; kept in the model to avoid a migration.

## Known issues

- **`cli link-topics` is a manual step.** It fills `topic_items`, the join that
  puts reading texts beside a drill. Nothing on the deploy path runs it: after
  a re-harvest, run it before `deploy/push-content.sh`. `/api/health` reports
  `corpus.topic_links`; the harvest commands print the reminder, and
  `cli push-content` and smoke warn when it is zero.
- **Grammar providers are free tiers with limits.** Workers AI (10 000
  neurons/day) answers first; NVIDIA's GLM-5.3-Flash is accurate but takes
  20–60 s; Mistral mostly returns "no errors"; OpenRouter allows 50 requests
  a day and counts failures. When all fail the check degrades to Vabamorf
  offline evidence. See `docs/ai-providers.md`.
- **The weekly eval schedule scores only OpenRouter.** Other lanes are checked
  by manual dispatch of `eval.yml`.
- **Browser journeys are not in CI.** They protect a release only when run
  locally (`docs/testing.md`).
- **Nothing measures ASR quality** — there is no Estonian speech benchmark wired
  up.
