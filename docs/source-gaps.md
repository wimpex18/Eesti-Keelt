# Source audit: what was found, what is wired, what was overlooked

A pass back through every source surfaced across all the research iterations,
checking each against what the code actually does. `source-audit.md` records the
research verdicts; **this file records the delivery gaps.**

Method: for each registered source, grep for whether any module besides the
registry references it. Registering a source is a licence decision, not an
integration.

## Wired and working

| Source | Where |
|---|---|
| Vabamorf / EstNLTK | `morph.py`, `export.py`, `verbs.py` — the spine |
| Enriched Ekilex wordlist | `wordlist.py` — 160 316 lemmas, CEFR + frequency |
| `TalTechNLP/inflection_et` | `evals/morphology.py` — 98.1 % gold validation |
| Selges keeles | `harvest/selges.py` — 349 texts, 100 % Estonian |
| ERR Raadio 4 | `harvest/err.py` — **but only 1 of 3 series** (see below) |
| TartuNLP TTS | `providers/tts.py` |
| OpenRouter / Groq / Workers AI / Anthropic | `providers/llm.py` |
| EKK handbook | `grammar.py` — 7 rules → sections |

## Overlooked — registered or fetched, never used

These are the real misses. Each was discovered, judged valuable, and then not
connected.

### 1. `grammar_et` — 1 000 error/correct pairs, fetched, unused

Downloaded in the same commit as `inflection_et` and referenced **only by a
well-formedness test**. It is a real Estonian GEC benchmark, twenty times the
size of the hand-written 18-case eval, and it has been sitting on disk unused
while I drew conclusions from the small set.

**Action:** add it as a second eval track. The hand-written set stays — it is
targeted at *our* error class and carries the precision half — but a 1 000-pair
external benchmark is stronger evidence about a model than 18 sentences.

### 2. ERR — fixed, and it corrected an earlier claim ✅

`SEEDS` had one of the three series. Adding the other two exposed two bugs and
one wrong assumption:

- **Only the 2010 series has transcripts.** The 2015 (`ekeel`) and 2019
  (`keelekodi`) series carry a series blurb and nothing more. My earlier
  "~170 episodes pairing transcript with audio" extrapolated from the one series
  I had looked at, and was wrong.
- **The later series serve HLS (`.m3u8`), not MP3.** The parser accepted only
  `.mp3`, so both series looked empty even once seeded.
- **Audio-only episodes were discarded** by a `word_count > 100` filter, and
  they all share the same blurb, so hashing the body collapsed ~44 of them into
  one. The content key now uses title + audio URL for those.

Result: **72 episodes — 28 with transcripts (filed `grammatika`) and 44
audio-only (filed `kuulamine`)**. Fewer than hoped for reading, considerably
more for listening.

### 3. `api.sonapi.ee` — verified, registered, never called

It returns **`rection`** (`lugema` → *"mida, kust, kellele"*), which is the
`rektsioon` error tag directly, plus `inflectionType` — the muuttüüp number the
Notion "Nomenid A–F" page already tracks. Both are things the curriculum plan
lists as missing, sitting behind an endpoint confirmed working weeks ago.

### 4. HARNO and EIS — registered owner-only, never fetched

The best exam material that exists: per-task PDFs for every skill and level, and
directly downloadable B1 listening MP3s. `eis.harno.ee/publicitems` serves
official A2–C1 reading and listening tasks with feedback, no login.

Neither has a fetch script. The licence work was done (owner-only, git-ignored);
the fetching was not.

### 5. The Estonian Native LLM Benchmark — 2 of 7 datasets used

Used: `inflection_et`, `grammar_et`. Unused and relevant:

- **`word_meanings_et`** — semantic knowledge; a vocabulary-quiz source that is
  native-authored rather than generated.
- **`exam_et`** (EstonianMME) — exam-style questions across subjects.
- `trivia_et_verified`, `ERRnews`, `paevakaja_speakers` — less relevant.

## Overlooked — never investigated at all

### 6. EVKK, the Estonian Interlanguage Corpus ⚠️ **highest value**

Tallinn University's corpus of texts **written by learners of Estonian**, with a
**linguistic error taxonomy** and error annotation — heading for 500 000 strings
of error-annotated learner text, licensed **CC-BY-4.0**.

This is the most valuable thing in this document, and it was mentioned early and
never followed up. Every drill in this app is generated from templates I wrote,
weighted by *one* learner's error log. EVKK is thousands of learners' actual
errors, annotated by linguists. It could tell us:

- whether object case really is the dominant error at A2–B1, or whether that is
  an artefact of one person's log;
- which errors cluster with which, giving a real difficulty ordering;
- authentic wrong sentences to drill against, instead of ones I invented.

**Status:** the corpus is browsable at `evkk.tlu.ee/vers1`, but the ELLE bulk
export endpoint (`/api/texts/tekstidfailina`) returns **500**, like the rest of
ELLE's API. So it needs either the web interface or an email to the maintainers.
Worth doing — this is a research-grade dataset for exactly our problem.

### 7. EstLLM — an Estonian-adapted Llama, open weights

`tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125`: Llama 3.1 8B with ~35B tokens of
continued Estonian pretraining plus instruction tuning. **Not gated**, Llama 3.1
licence, verified present on Hugging Face.

The paper reports it "consistently outperforms the original multilingual base
model" on Estonian. That speaks directly to the finding that a general free
model scored 0.50/0.50 on our eval: **the answer to "which model knows Estonian"
may be "an Estonian one".**

Earlier I dismissed `TartuNLP/gec-llm` as too heavy at 7B. That reasoning does
not transfer — EstLLM is general-purpose and instruction-tuned, and 8B is inside
what a modest GPU or a hosted inference provider handles. **Not on OpenRouter**,
so it needs HF Inference Providers or self-hosting.

### 8. Smaller items, correctly deferred

Noted here so they are not rediscovered as if new: ERR Jupiter subtitles,
`arhiiv.err.ee` (Keelesaade, Keelekõrv), Sõnaveeb teacher-tools CEFR lists,
`sonaveeb.ee/learn` phrase collections, `keeleweb2.ut.ee`, the MEIS level tests,
EKI Selgeks, EKIToolkit, wiktextract, Anki decks, tekstiks.ee and the TalTech
ASR models. All real; none blocking; each has a stated reason in
`source-audit.md`.

## What this changes in the plan

The curriculum plan (`curriculum-plan.md`) stands — but three items move earlier
because they are cheap and unblock other things:

| | Action | Why now |
|---|---|---|
| **A** | Seed the two missing ERR series | one line each; ×6 the listening corpus |
| **B** | Wire `sonapi` for rection + muuttüüp | supplies two curriculum topics outright |
| **C** | Add `grammar_et` as a second eval track | data already on disk |

And two become explicit investigations rather than footnotes:

| | Action | Why |
|---|---|---|
| **D** | Pursue EVKK access | real learner errors beat invented ones |
| **E** | Test EstLLM | the strongest candidate for the model problem |

None of these block **Step 1 (the topic model)**, which stays next.
