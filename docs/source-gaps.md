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
| EstLLM (local / Hugging Face) / OpenRouter / Groq / Workers AI | `providers/llm.py` |
| EKK handbook | `grammar.py` — 7 rules → sections |

## Overlooked — registered or fetched, never used

These are the real misses. Each was discovered, judged valuable, and then not
connected.

### 1. `grammar_et` — 1 000 error/correct pairs, fetched, unused — fixed ✅

**Resolved.** It is the source of the `word-order` drill: 9 383
native-corrected pairs filtered to the corrections that only *re-order* — same
words, same punctuation, different sequence, which is the signature of a
word-order error and needs no annotation layer. Attested rather than generated,
and that was a measurement: see `docs/status.md` for why generating them was
refused.

9 383, not the 1 446 this section first said, because `grammar_et` has **two
splits and only the test one was ever fetched** — the fetch table named the
split `evals/external.py` scores, and every later pass read the fetch table.
The train split is 7 937 pairs and took the drill pool from 64 items to 322.

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

### 3. `api.sonapi.ee` — verified, registered, never called — fixed ✅

**Resolved.** `providers/sonapi.py` is called by `gloss.py`, `rection.py`,
`curriculum.py` and `app.py`. Single-lookup only, one live request a second
under a lock, and every answer kept in `vocab.db` so a word is asked about once,
ever — the restraint is about their server, not their licence.

It returns **`rection`** (`lugema` → *"mida, kust, kellele"*), which is the
`rektsioon` error tag directly, plus `inflectionType` — the muuttüüp number the
Notion "Nomenid A–F" page already tracks. Both are things the curriculum plan
lists as missing, sitting behind an endpoint confirmed working weeks ago.

### 4. HARNO and EIS — registered owner-only, never fetched — fixed ✅

**Resolved.** `harvest/harno.py` and `harvest/eis.py`, both via
`cli harvest-exam`: **122** HARNO materials and 23 EIS tasks, indexed as
**pointers only** — `body` is empty and a test asserts it. (This said 39 until
2026-09-11, when the catalogue was run again and counted.)

The best exam material that exists: per-task PDFs for every skill and level, and
directly downloadable B1 listening MP3s. `eis.harno.ee/publicitems` serves
official A2–C1 reading and listening tasks with feedback, no login.

Neither has a fetch script. The licence work was done (owner-only, git-ignored);
the fetching was not.

### 5. The Estonian Native LLM Benchmark — 3 datasets used

Used: `inflection_et`, `grammar_et`, and — since 2026-09-11 — **`grammar2_et`**.

`grammar2_et` is the one real find of the 2026-09-11 audit, and it is worth
being precise about why it was missed: it was not hard to reach, not gated and
not new. It was published 2024-11-18, it carries the same two columns as
`grammar_et`, and every earlier pass enumerated "the seven datasets of the
benchmark" — of which this is not one. A list read from a paper is still a
hand-maintained list.

446 pairs, of which **17 are pure re-orderings**, against the 47 `grammar_et`
yields. A third again on the entire word-order pool. `cli wordorder` now reads
every `grammar*_et.json` the fetch table knows, derived rather than named, so
the next one costs nothing.

Still unused and relevant:

- **`word_meanings_et`** — semantic knowledge; a vocabulary-quiz source that is
  native-authored rather than generated.
- **`exam_et`** (EstonianMME) — exam-style questions across subjects.
- `trivia_et_verified`, `ERRnews`, `paevakaja_speakers` — less relevant.

## Overlooked — never investigated at all

### 6. EVKK, the Estonian Interlanguage Corpus — fixed ✅

Tallinn University's corpus of texts **written by learners of Estonian**, with a
linguist-maintained error taxonomy. This was the most valuable item in this
document and the one filed as hardest to reach: ELLE's bulk export endpoint
500s, so the note said it needed "the web interface or an email to the
maintainers."

It needed neither. The corpus is **Plone-served HTML**, not a SPA, and the error
taxonomy with corpus-wide counts is a **public page** — 200 named categories,
**51 467 annotated errors**, one request. `eesti/harvest/evkk.py` reads it.
(Re-fetched 2026-09-11: the error total is identical, which is the number the
curriculum weights on. The category count reads 200 rather than the 202 first
written down, because the parser drops two nodes that render their own id
instead of a label.)

**The finding contradicts an assumption this app was built on.** Ranked by
annotation frequency, `obj-case` is 1.3 % of learner errors; the two largest
classes are **word order (5 889)** and **verb rection (5 170)**. See
`curriculum-plan.md` for the full table, the caveats, and what changes. In
short: the personal error log stays the first weight because it is evidence
about *this* learner, but it is no longer the only weight, and it was quietly
setting topic order.

**What is deliberately not taken.** The corpus search also works — POST to
`Search/search_results.html`, plain form encoding, no login — and returns
authentic learner sentences with their errors. Two reasons it stays untouched: a
single-word query returned **6 MB** from a research server with no rate limiting
to protect it, and the site publishes **no reuse licence**, so the texts are
other people's writing with no permission attached. Counts about a published
taxonomy are facts; the texts are not. Registered owner-only either way.

### 7. EstLLM — an Estonian-adapted Llama, open weights — lane built ✅

**Partly resolved.** Nobody hosts it: HuggingFace's router serves 132 models and
not one Estonian one, and every Estonian model has an empty
`inferenceProviderMapping`. So the `huggingface` lane became `local` — pointed
at `LOCAL_LLM_URL`, keyless, off unless set, first in the chain when on. GGUF
builds exist (`Q4_K_M` ≈ 4.9 GB). `docs/local-llm.md` has the setup. Open in the
sense that nothing runs there yet.

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

**A–D are done.** A–C landed with the ERR reseed, `providers/sonapi.py` and
`evals/external.py`; D is `harvest/evkk.py`.

**E was not.** This said "all five are done" and gave, as evidence for *Test
EstLLM*, "the `huggingface` provider entry pointing at
`tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125`". Adding a config entry is not
testing a model, and one real attempt would have failed immediately:

- the entry was in `PROVIDERS` and **not** in `LLM_PREFERENCE`, so the grammar
  chain never reached it;
- and it pointed at `router.huggingface.co`, which on 2026-08-20 served 132
  models and **not one Estonian one**. EstLLM, `gec-llm`, Llammas and TalTech's
  verbatim Whisper all have an empty `inferenceProviderMapping`. Nobody hosts
  any of them.

The project had already learned this for the Whisper model — `docs/speaking.md`
says "nobody hosts it" — and never ran the same check on the text model.

**E is now done properly, by a different route.** GGUF builds of EstLLM exist,
so the model runs on hardware you own rather than on an API nobody offers. The
lane points at `LOCAL_LLM_URL` and speaks OpenAI-compatible HTTP, which Ollama,
LM Studio and llama.cpp all serve. See `local-llm.md`. Whether it is *better*
than a hosted general model on Estonian object case is still unmeasured — that
is what the eval is for, and it is the honest state to leave this in.

Only D changed the plan, and it changed it in one place: **step 2's generator
order** now starts with `rektsioon` rather than noun declension, because the
corpus says rection is the second-largest real error class and `sonapi` already
supplies the data. **Step 1 (the topic model) stays next** — unchanged.

## Still open

| Item | State |
|---|---|
| HARNO / EIS fetch scripts | **built** — 122 HARNO materials and 23 EIS tasks, as pointers (re-counted 2026-09-11) |
| ERR *Lihtsad uudised* | **built** (`harvest/lihtsad.py`) |
| Notion write-back | **built** (`notion.py`), queue then confirm |
| Cloudflare deploy | **built** — Worker in front of Cloud Run, both free tier |
| `grammar2_et` | **wired 2026-09-11** — +17 attested word-order items (§5) |
| EKI A1/A2/B1 level vocabulary | **wired 2026-09-11** — `cli import-levels`, EKI's levels win in `words.proficiency` with `level_source` saying so |
| HARNO `statistika` / `vorm` | **fixed 2026-09-11** — 20 official materials were indexed and in no section; forms now reach `eksamiinfo`, statistics are no longer indexed |
| ERR Lihtsad uudised "audio" | **corrected 2026-09-11** — the ledger claimed audio, the pages have none, the harvester always said so |
| EKI *põhisõnavara sõnastik* (`psv`) | **open, and the top item** — the simplified learner definitions and ~6 000 pronunciation WAVs, CC BY 4.0, owner-fetchable. Not wired: nothing here has read the XML, and a parser written blind is a code path that has never met its input. |
| `word_meanings_et`, `exam_et` | still unused (§5) — the only row that has not moved |
| EKI A1/A2/B1 level word lists | **done** — the importer is `cli import-levels`; the file still comes from the learner, not from code. |
| `tlu-dt-nlp/Estonian-CEFR-Assessment` | **new, open, refused for now** — MIT, 720 CEFR-labelled L2 writings, no trained model, Stanza-scale dependencies, and a verdict `readiness.py` declines to make. See `source-audit.md`. |

`word_meanings_et` is a native-authored vocabulary quiz, and the reason it is
still unused is that vocabulary here is measured from **what the learner has
actually met while reading**, per lemma. A quiz over words nobody met would
report on a different population than every other number in the app. It stays
open rather than closed: it would be the right source if a placement-style
vocabulary check is ever wanted, which is a different question from progress.
