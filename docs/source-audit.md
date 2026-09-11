# Source audit

Every source, API and technique surfaced in research, against what is actually
built. Kept honest: "verified" means called and observed, not read about.

## Second pass, 2026-09-11: five things chased to the bottom

The first pass of the day (below) checked whether sources still answer. This
one went after five specific complaints, and four of them turned out to be real
defects on **this** side rather than upstream.

### 1. TartuNLP grammar — the client was already right; their worker is not

Their OpenAPI spec is public at `https://api.tartunlp.ai/grammar/openapi.json` and was
read today. It publishes two endpoints, `POST /grammar/v2` and `POST /grammar/`,
both taking `{"language": "et", "text": …}` — which is byte-for-byte the
request this app has always sent. The spec declares **no authentication**, so
there is no key to add.

Both endpoints answer **HTTP 500 after ~61 seconds**, reproduced with the
example string printed in their own spec, `{"text": "Aitähh!"}`. A `GET` to the
same URL returns 405. That 405 is the trap worth naming: the route exists and
the host is up, so any liveness check built on `GET` reports a healthy service
that has never once returned a correction.

There is no connection to fix. What *was* fixable, and is now fixed, is
everything that happens the moment their worker comes back:

| Was | Now |
|---|---|
| only `/v2` tried | `/v2` for the explanation, then `POST /grammar/` — a different code path on their side that skips the explanation step and returns character spans outright |
| `original`/`corrected` are whole **sentences**, handed straight to the highlighter | narrowed to the words that actually changed, so a correction points at `autot → auto` rather than at the sentence containing it |
| every correction tagged `vocab` | a pure re-ordering is tagged `word-order`, using the same multiset test `wordorder.py` already owns. Everything else stays `vocab`, which is still a guess and is left labelled as one |
| the contract lived in nobody's head | `tests/test_tartunlp_contract.py` replays both published response shapes offline |

### 2. EKI's A1/A2/B1 level vocabulary — imported

`cli import-levels FILE` is new. It reads *Eesti keele tasemete sõnavara*
(2018, CC BY 4.0) — `LEMMA POS SAGEDUS TASE`, tab separated — into a table of
its own and lets EKI's levels win in `words.proficiency`, stamping
`words.level_source = 'eki'`.

This replaces a derived estimate with the exam board institute's own answer.
The enriched Ekilex list tags **6.2 %** of its lemmas with a CEFR level; EKI
publishes the levels outright.

Two traps were designed around rather than discovered later:

- **EKI's `SAGEDUS` is a corpus count; `words.freq_rank` is a rank.** `aasta`
  is 5 006 831 occurrences and `ma` is rank 2. Writing one into the other would
  have ordered every frequency-ranked drill backwards and put the commonest
  words last. The count stays in `official_levels.freq`, under its own name.
- **`build()` deletes every row in `words`.** So the import lives in its own
  table and `build()` re-applies it, and a rebuild does not send the learner
  back to EKI's download form.

**It does not download.** EKI serves the file behind a page asking who you are
and what the material will be used in — a request worth answering rather than
stepping around — so the command takes a path and says where to get the file
when the path is wrong. EKI's licence terms are kept: attribution in
`sources.REGISTRY`, and the changes described there (rows filtered to A1–B1,
one-letter POS codes mapped to this project's tags, frequency kept under its
own name).

### 3. EVKK and ERR Lihtsad uudised

Three defects, two of them ours and one of them a claim nobody could check:

- **The registry said Lihtsad uudised is "audio + text". It is text only.** The
  pages were read today: an issue carries no per-issue audio, only ERR's
  site-wide radio-app banner. `harvest/lihtsad.py` had it right the whole time
  — it writes `audio: False` into every item — so the wrong claim lived in the
  ledger and nowhere else, which is the worst place for it, because nothing
  reads a note and so nothing could contradict it.
- **The EVKK failure message named the wrong host.** It told whoever hit it to
  retry when `elle.tlu.ee` answers. ELLE is a different TLU service, and it is
  up; the corpus is `evkk.tlu.ee`. An error message that names a working host
  sends its reader to check the wrong thing.
- **`LEAF_ONLY` was empty while being described as an active guard.** The
  comment said it "exists because two of these names sit above children that
  belong to a different tag of ours". Checked against the live taxonomy: none
  of the sixteen mapped nodes is an ancestor of another carrying a different
  tag, so nothing is double-counted and there was nothing to exclude. The
  mechanism stays, because the hazard returns the moment `TAG_MAP` grows — but
  it is now checked by `tests/test_evkk_mapping.py` rather than asserted in a
  comment. The same file checks that every `TAG_MAP` name really is on the
  page, because a typo there does not raise: it makes a tag weigh zero and
  quietly moves the topic order.

EVKK's retries went from 3 to 5. Measured, not guessed: it answered 500 twice
and succeeded on the third attempt today, and its successful response took 21
seconds, against a retry budget of about three.

### 4. HARNO — verified, mapped, and 20 items were invisible

**The headline defect: `statistika` (11) and `vorm` (9) were indexed into
`content.db` and claimed by no section.** Twenty official materials present in
the database and absent from the app — which is precisely the failure the
orphan check in `tests/test_sections.py` exists to prevent, and it got past it
because that test's fixture was a **hand-written list of kinds** somebody had
to remember to extend.

| Kind | Count | Where it goes now |
|---|---|---|
| `ulesanne` | 72 | `eksam` — official tasks, split by exam part |
| `konsultatsioon` | 9 | `vihikud` — the one official material that is homework |
| `kirjeldus` | 9 | `eksamiinfo` |
| `vorm` | 9 | **`eksamiinfo`** — newly reachable |
| `sooritusnaidis` | 4 | `naidised` |
| `teave` | 4 | `eksamiinfo` |
| `video` | 4 | `eksamiinfo` |
| `statistika` | 11 | **not indexed at all** |

`vorm` is the application and reimbursement forms, and this section's own
description gave the omission away: it promised *регистрация* while showing
none of them. They are level-less on purpose — registering is the same errand
at A2 as at C1 — so `exam_material` now matches level-less material for every
level rather than filing a form under a level HARNO did not give it.

`statistika` is eleven PDFs of national pass rates by year. It is not study
material, and putting a national pass rate beside a readiness verdict whose
whole job is to say "this is not a prediction" is worse than leaving it out.
`catalogue()` still reads it, so the catalogue stays a faithful account of the
page; `to_items` drops it.

The fix that keeps this from recurring is not the mapping, it is
`harno.KINDS` — one exported vocabulary, derived from the marker table, that
the section list and the tests both read. A new kind now fails a test instead
of disappearing.

**There is no A1.** The Estonian *tasemeeksam* starts at A2, and HARNO
publishes A2, B1, B2 and C1. At the two levels this app targets: **A2 has 25
materials and B1 has 26**, each covering all four exam parts, with 19 of them
listening audio (`mp3`/`wav`).

**HARNO and EIS complement rather than duplicate.** No URL overlaps. EIS's 14
A2/B1 items are interactive tasks with immediate feedback, done on their site;
HARNO's are downloadable per-task PDFs plus the listening audio. Keeping both
is right, and both stay **pointers** — `body` is empty and a test asserts it.

**Every pointer was fetched.** The page catalogues 122 materials, 111 of which
become items once the statistics are dropped. Four of those are embedded videos
and were not fetched; of the remaining **107, 86 answer 200** — every one of
them on `harno.ee`. The other **21 are on a different host entirely**,
`projektid.edu.ee`, a Confluence space for the consultation project, and today
that host answers **503 Service Unavailable** (confirmed by a second network
path; from inside a sandboxed session the relay closes the tunnel, which proves
nothing on its own).

Those 21 are the listening material — the `mp3` and `wav` files this project's
notes single out as "directly downloadable B1 listening MP3s". **Nothing was
changed about them.** A 503 is an outage, not a dead link, and deleting or
hiding a pointer because its host had a bad afternoon would lose the best
listening material the exam board publishes. It is written down here so that
the next person to find a broken listening link knows it is one host, it is not
`harno.ee`, and it is not this app.

One smaller bug found on the way: `format` was derived by splitting the URL on
its last dot, so a consultation entry pointing at a Confluence wiki page stored
`ee/spaces/tho/pages/343705183/konsultatsioonide+materjalid` as its file
format — a whole URL path in a field the app renders as a badge and `to_items`
reads to decide whether something is audio. Extensionless URLs are now `link`.

### 5. Sõnaveeb's learner dictionary — not refused, routed

The earlier verdict said this was out of reach because getting at *Keeleõppija
Sõnaveeb* meant building a second client against the site whose maintainers ask
not to be batch-requested. That was the right answer to the wrong question.
**EKI publishes the same material for download, under CC BY 4.0**, and their
own licence page says so in as many words: the material may be processed and
presented in any way needed, an app included, commercial use unrestricted, so
long as the attribution to EKI is kept and the changes described.

| Want | Sanctioned route | State |
|---|---|---|
| which words are at the learner's level | *Eesti keele tasemete sõnavara* (`D=A1A2B1`) | **wired today** — `cli import-levels` |
| simplified learner definitions, and recorded pronunciations of the principal forms | *Eesti keele põhisõnavara sõnastik 2014* (`D=psv`), XML + headword list, ~6 000 words | available, not wired — see below |
| the whole database | Ekilex API | still needs a free account's key; `ekilex.ee/api/*` answers 403 without one |

`psv` is not wired and is not registered, deliberately. Nothing in this project
has seen the file, and writing an XML parser for a format nobody here has read
is a code path that has never met its input — the same reason the level import
takes a path instead of guessing. It is the top open item.

So the posture is unchanged and the conclusion is not: Sõnaveeb is still never
batch-requested, `sonapi` is still single-lookup only, and the learner-level
vocabulary the app wanted from it now comes from EKI directly.

## Re-probe, 2026-09-11

Every third-party surface the code calls was called again today. **Nothing has
moved that the app depends on**, which is the useful half of this section — the
other half is three numbers of ours that had gone stale, and one dataset that
had been sitting on the benchmark server for two years unread.

| Surface | Today | Verdict |
|---|---|---|
| `api.sonapi.ee/v2/raamat` | 200 in 1.3 s; fields unchanged (`rection`, `inflectionType`, per-meaning `rus`) | **KEEP**. No `/v3` — `api.sonapi.ee/v3/raamat` is 404, so the pin is current, not merely old. |
| `api.tartunlp.ai/text-to-speech/v2`, `/translation/v2` | 200 | **KEEP** |
| `api.tartunlp.ai/grammar/v2` | `GET` 405, `POST` **hangs to a 30 s timeout** | **KEEP the rejection.** The 405 is worth writing down: the host answers, so a naive liveness check goes green on an endpoint that has never once returned a correction. Only a POST settles it. |
| `eis.harno.ee/publicitems` | `catalogue()` → **23 tasks**, 4+3 per level A2/B1/B2, 1+1 at C1 | **KEEP**. Matches the documented 23 exactly. |
| `harno.ee/eesti-keele-tasemeeksamid` | `catalogue()` → **122 materials** | **UPDATE the docs, not the code.** They said 39. See below. |
| `news.err.ee/k/lihtsad-uudised` | 74 issues listed | **KEEP** — still the one live feed. |
| EVKK taxonomy | 200 (21 s), **200 named categories, 51 467 errors** | **KEEP**. The error total is identical to the figure the curriculum weights use. |
| Ekilex wordlist (GitHub raw) | 200; repository still at its single commit of **2026-04-01** | **KEEP** — no newer snapshot to take. |
| `arhiiv.eki.ee/books/ekk09/` | 200 | **KEEP** |
| `estnltk` on PyPI | latest is **1.7.5**, the pinned version | **KEEP** |
| `tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125` | `inferenceProviderMapping` → `featherless-ai`, status `live` | **KEEP**. The 2026-09-01 finding held for ten more days. |
| `TalTechNLP/Voxtral-Mini-3B-2507-estonian` | mapping still `{}`; 66 downloads (was 48) | **KEEP the deferral** — nobody hosts it, and nobody is talking about it. |

### The three stale numbers

1. **HARNO is 122 materials, not 39.** `source-gaps.md` said 39 in two places.
   Whether HARNO published more or an improved parser now sees more, the number
   in the document was wrong today. The shape: 55 per-part exercises (10 B1
   listening, 9 C1, 8 A2, 8 B2, and so on), 8 consultation workbooks, 4 sample
   performances, 4 intro videos, 11 statistics PDFs and 9 application forms —
   the last two filed at no level on purpose, because they belong to the page
   rather than to a panel. Still pointers: `body` is empty and a test asserts it.
2. **EVKK is 200 named categories, not 202.** The parser drops nodes that
   render their own id instead of a label. The error count — the number the
   curriculum actually weights on — is unchanged at 51 467.
3. **The EKI level word lists are gated by a form, not by a certificate.** See
   `content-sources.md`; the conclusion (do not fetch them from code) does not
   change, but the stated reason was wrong.

### The one thing found: `TalTechNLP/grammar2_et` — **ADD**, done

446 more (learner wrote, native corrected) pairs, same two columns as
`grammar_et`, published 2024-11-18. Missed in every earlier pass because the
benchmark paper names seven datasets and this is an eighth beside them.

It matters for one reason only. `wordorder.py` refuses to *generate* word-order
items and takes them only from corrections that purely re-order, which is a
severe filter: 47 items from 1 000 pairs. `grammar2_et` yields **17 more**,
measured today — a third again on the whole pool, for the error class EVKK
ranks second-largest and this app could not practise at all until recently.

`evals/fetch.py` downloads it, and `cli wordorder` now ingests **every**
`grammar*_et.json` the fetch table knows rather than one hard-coded filename,
so the next file added to that table needs no second edit. Ingest is idempotent
— item ids are content hashes — so the two files merge rather than collide.
Licence posture is unchanged and unchanged deliberately: neither card states a
licence, so both are ungranted, git-ignored, pushed at runtime, never imaged.

It is deliberately **not** added to `evals/external.py`. That track's score is
compared across runs, and enlarging what it scores would make two different
measurements look like the same one.

### Candidates looked at and refused

| Candidate | Verdict | Why |
|---|---|---|
| **`tlu-dt-nlp/Estonian-CEFR-Assessment`** (TLU, MIT, paper Mar 2026) — 720 CEFR-labelled L2 exam writings, 154 features, ~0.9 accuracy | **REJECT for now, strongest open item** | The best new Estonian resource found, and it is genuinely open. Three things stop it: it ships no trained model, its feature pipeline needs Stanza plus a spell-checker plus an MT-based corrector, and its output is a CEFR verdict on the learner's own writing — which is the one claim `readiness.py` exists to refuse to make. Worth revisiting as a *corpus* rather than as a classifier. |
| **`TalTechNLP/EFAC`** — Estonian Foreign Accent Corpus (2026-06) | **REJECT** | Gated, licence "other", and it would serve a pronunciation score this app deliberately does not give. |
| **`tartuNLP/Llama-3.1-EstLLM-70B-Instruct-0826`**, **`Apertus-EstLLM-8B-Instruct-0326`** (Apache-2.0) | **REJECT** | Neither is hosted by any inference provider (`inferenceProviderMapping` is `{}`, checked today), and the 70B is ~40 GB at Q4. The Apertus licence is nicer than Llama 3.1's; nothing else about it is measured, and "newer" is not a reason. |
| **`TalTechNLP/err-video-news-transcribed`** — 40 K transcribed ERR stories, CC-BY-SA-4.0 | **REJECT for now** | Genuinely well-licensed and large, but it is transcripts without the audio, at native speed and native register. The listening library's constraint is level, not volume. |
| **Sõnaveeb's own search endpoint** (for *Keeleõppija Sõnaveeb*, ~7 000 words with A2/B1-simplified definitions) | **REJECT** | It is exactly the material this learner wants, and reaching it means building a second client against the site whose maintainers ask not to be batch-requested. `sonapi` is the single-lookup route and has no learner-dictionary parameter. The answer stays: link to Sõnaveeb. |
| **Ekilex API** | unchanged | `ekilex.ee/api-info` still redirects to `/login`. Needs an account only the learner can make. |

## Status of every lead

### Built and verified working

| Source | Use | Evidence |
|---|---|---|
| **Vabamorf / EstNLTK** | all forms, case detection, drill answers | **98.1 % agreement** with TalTech gold data; 98 % on genitive and partitive |
| **Enriched Ekilex wordlist** (CC-BY-SA-4.0) | CEFR level + frequency, 160 316 lemmas | counts match source exactly (A1 685 / A2 997 / B1 2 509) |
| **ERR Raadio 4** | transcript **+** audio, one artefact per episode | **28 episodes, 27 087 words, all 28 with audio**, harvested and stored owner-only |
| **TalTechNLP/inflection_et** | validates Vabamorf | 1 400 rows fetched; `cli validate` |
| **TalTechNLP/grammar_et** | GEC benchmark + word-order items | 1 000 error/correct pairs fetched; 47 pure re-orderings |
| **TalTechNLP/grammar2_et** | more word-order items | 446 pairs fetched 2026-09-11; 17 more re-orderings |
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
