# Architecture, content and market review

Point-in-time review of Grove, prepared 8 October 2026 from commit `faa477d`.
The illustrated version with diagrams is the Claude artifact
<https://claude.ai/artifact/9x35tYbYJDvTy5sAqHf1hg> (private to the owner).
Decisions are tracked in Linear project Eesti-Keelt (team DEV); this file is the
reference every implementation session can read. Current-state facts belong in
`docs/status.md`; accepted decisions become ADRs.

Method: documentation and code reading; a measured replay benchmark; a learner
walkthrough of an isolated local copy (model lanes off); a content audit by
sampling every generator; web research on sources, competitors, exam
preparation, EmbeddingGemma 2, versions and Claude pricing (checked on
platform.claude.com). No production access, no paid model calls.

## Decisions

| # | Decision | Linear | When |
|---|---|---|---|
| D0 | Give every learner licensable material: EKI EVS example phrases now, Settle in Estonia A1/A2 once confirmed, then a "model drafts → Vabamorf verifies → person reviews → code keys" pipeline; ask ERR, Selges keeles, HARNO, Integration Foundation and EKI for permission | DEV-36 (DEV-54, DEV-55, DEV-56) | now |
| D1 | Fix correctness defects: EVS glosses, writing checker, mislabelled items, ÕS 2025 audit, exam screens; protect learner data (off-Cloudflare backup, Durable Object defects) | DEV-35 (DEV-49–DEV-53), DEV-37 | now |
| D2 | Replace Durable Object replication with Litestream-replicated SQLite; Durable Objects keep accounts, sessions and push | DEV-43 | after 8 Nov 2026 |
| D3 | Native Claude lane; evaluate Haiku 5.5 on the hand and external tracks; promote only if it clearly beats GPT-OSS-120B's 2/40 | DEV-38 | now |
| D4 | Ground free-form grammar answers in cached EKI rule text (long context, ≤100K-token prompts); no embedding model | DEV-44 | after D3 |
| D5 | Ukrainian, then English, as first-class explanation languages | DEV-42 | after D6 spec |
| D6 | Practice-first A0→B1 path alongside Keeleklikk/Keeletee, plus B1 exam preparation; spec first | DEV-40 | after D1 |
| D7 | Exam fidelity: HARNO task formats, both writing tasks, criteria and samples | DEV-41 | after D6 spec |
| D8 | Lemma search (FTS5); passkeys and recovery; ASR heartbeat | DEV-48 | later |
| D9 | Proven practice patterns (edit-then-explain, hint-first, mistakes session) | DEV-45 | later |
| D10 | Lock dependencies; October updates | DEV-39 | now |
| — | Scheduled harvests, corrected source notes | DEV-46 | next |
| — | Four-week pilot with Russian, Ukrainian and English learners | DEV-47 | after the sittings |

Owner decisions on 8 Oct 2026: a full A0→B1 path (not only exam preparation);
no embedding model; permission requests rather than opening private sources.

## What to keep

- Grading authority: code keys drills, review and mastery; models explain (ADR-0001, ADR-0004).
- Event log with signed, regenerable items; strict replay verification.
- Evaluation before any lane change.
- Honest per-part readiness; no pass probability; no CEFR inference.
- Free offline packs re-graded server-side.
- No streak machinery.

## Content and features

### The public app has almost no material

All 506 corpus items come from sources marked not redistributable (Selges keeles 349,
ERR Raadio 4 72, HARNO 50, ERR Lihtsad uudised 21, EIS 14). Outside the owner's scope
`eesti/sources.py` `connect()` exposes an empty view. Measured under a guest scope:
0 reading texts; mock reading and listening empty; 30 of 43 topics produce items
(owner: 37); `gen-stem` (6th on the path, 9 dependants) dead-ends; dictation falls back
to ≈331 generated TTS sentences.

### By skill and level (lower-bound counts from sampling)

| Skill | A0 | A1 | A2 | B1 |
|---|---|---|---|---|
| Grammar | none | 23 topics, 20 generators (public 16); conjugation 1–3 frames per topic | 11 topics; imperative/conditional/participles 2 frames | 9 topics, 6 generators; indirect mood 7 items; rection 12 verbs |
| Vocabulary | none | 695 EKI lemmas: 97% Russian gloss, 94% example, 91% audio | 1,230 lemmas; practice tops up from A1 only | 2,415 lemmas; 63% audio |
| Reading | none | owner 116 posts; public 0 | owner 349 posts + 21 ERR; public 0 | owner 21 ERR + 8 exam tasks; public 0 |
| Listening | none | owner 405 EKI human-read sentences + TTS; public ≈331 TTS | 72 ERR radio items, ungraded; 0 graded comprehension | none |
| Speaking | none | read-aloud; advisory feedback | 12 prompts in total, unlevelled, no pictures | Vestlus over the same 12 cards |
| Writing | none | 1 prompt | 1 mock prompt (≥30 words) | 1 mock prompt (100 words), no rubric |

About 20 exercise types exist; every grammar item is a single sentence.

### The real exam, task by task

HARNO A2 has 14 task types, B1 12. Grove reproduces 2 faithfully (owner-only),
approximates 10, and has nothing for 14, including every listening task.

| Part | Types | Faithful | Approx. | None | Biggest gap |
|---|---|---|---|---|---|
| A2 reading (50 min) | 5 | 1* | 2 | 2 | matching; notices; 3-option text gap-fill |
| A2 listening (30 min) | 4 | 0 | 0 | 4 | all |
| A2 writing (30 min) | 2 | 0 | 1 | 1 | T1 business-card form |
| A2 speaking | 3 | 0 | 2 | 1 | picture description; asking as well as answering |
| B1 reading (50 min) | 4 | 1* | 2 | 1 | phrase bank |
| B1 listening (30–35 min) | 4 | 0 | 0 | 4 | all, played twice |
| B1 writing (35 min) | 2 | 0 | 1 | 1 | T1 form/≈50-word message; rubric |
| B1 speaking | 2 | 0 | 2 | 0 | picture idea cards; both roles |

\* owner-only, one paper. The mock fills a 50-minute reading clock with 8 sentences,
has no scaled points, and does not apply the no-part-at-zero rule. Readiness counts
contact, not competence. HARNO's written part is on paper with a pen, no
dictionaries; speaking is recorded and second-marked. HARNO's passing B1 writing
samples contain many errors: task coverage matters more than error count.

### Missing grammar and topics

Against EKI's grammar profiles (546 can-do statements: 84 A1, 136 A2, 171 B1):
nominative total object (A2; `obj-case` only contrasts genitive/partitive);
partitive subject and existential sentences (A1); plural partitive and plural cases;
modal verbs with infinitives, *hakkama* + *-ma*; indefinite and quantifier pronouns;
word formation and compounds; phrasal verbs; relative clauses; negation outside
present and past; adverb comparison; declined numerals; B1 postpositions. Level
mismatches with EKI: imperative and perfect (A1 in EKI), noun-phrase agreement (A1).

Against HARNO's 15 A2 topics, missing themes: personal data and forms, daily routine,
free time and culture, relationships, shopping and money, services, directions.
Missing functional language: greetings, asking the way, phone calls, agreeing and
disagreeing, opinions.

Learning loop missing: units with communicative goals and can-do checks; vocabulary
and dialogue input in lessons; productive tasks per unit; homework, a weekly plan to
the sitting, any teacher role; a scored exam-shaped mock.

### Learner walkthrough (≈230 steps, owner scope, model lanes off)

- Russian A0: blocked. "Start from the beginning" jumps to pronouns; the alphabet
  topic has three bullets and no audio; examples untranslated; first drill asks for
  three cases before any is taught; no greetings or phrases.
- Russian A2: thin. Placement covers 3 A1 topics with unhinted blanks and marks valid
  answers wrong; templated drills ("____ palun kohe!"); non-word distractors
  (*lehtl*); tap-to-look-up reading is excellent; recommendations favour 2017 news.
- B1 candidate: thin. Only sitting offered has closed registration with no warning;
  mocks not exam-shaped, no item review; official interactive tasks render without
  options.
- Ukrainian or English speaker: blocked; everything that explains is Russian.

Correctness bugs: EVS homograph glosses (*siin* "шина", *miks* "микс", *küll*
"обилие", *hästi* "не очень"); writing checks miss *loen raamat*, *jõin kohv*, flag
*poodi* as an object, suggest *Tallinas* → *Tallina*; "____ tütres" labelled
*sisseütlev*; principal-forms item shows its own answer; sentence-initial blanks in
lower case.

### Material pipeline

C1 EVS phrases as public pools (now). C2 graded texts and dialogues by HARNO topic
drafted with the Batch API (≈$0.25 per 1,500 with Haiku 5.5, ≈$5 with Sonnet 5.5),
every form through Vabamorf, every lemma within the band's EKI level, coverage by
code, human review. C3 HARNO item types keyed to text spans. C4 multi-voice TTS
listening from the same scripts. C5 ≥20 writing prompts and ≥30 speaking cards per
level. C6 permission requests (`qa/source-permission-requests.md`). The A0 unit:
alphabet and sounds (EKI pronunciation exercises), greetings, numbers, first words
(EKI picture dictionary).

## Three audiences

| | Russian | Ukrainian | English |
|---|---|---|---|
| Meanings | EVS (homograph bug), Ekilex, 315 hand glosses | EKI picture dictionary (997), Ekilex/Sõnaveeb `ukr` (already parsed in `eesti/providers/sonapi.py`, discarded), EKI Estonian–Ukrainian (11k, on request), TartuNLP est↔ukr for drafts | EKI English–Estonian (≈90k, public domain), Ekilex `eng`, picture dictionary (960), Wiktionary |
| Terminology | EKI tables, EKK, Teatmik | «Розмовляємо естонською» (ask authors) | Erelt (ed.), *Estonian Language* (CC0 per repository; confirm) |
| Blockers | `why_ru` signed into item tokens (`eesti/itemref.py`) and stored in events | same | same, plus grounding rejects Latin-script explanations (`eesti/tutor.py` `_grounded`) |

About 1,900–2,400 Cyrillic fragments in about 90 files; no catalogue;
`explanation_language` is stored in the profile but nothing reads it. Shape: a
canonical layer with stable IDs; an explanation catalogue per language with
`draft`/`reviewed` status, CLDR plurals and per-language contrast notes; items and
new events carry `rule_id` and parameters, never prose.

## Architecture

### State layer

The origin writes SQLite on Cloud Run's ephemeral disk; Durable Objects copy events
after every write, confirm the sequence before success, pull snapshots, and on each
new boot push the whole log back for a full replay (measured ≈2.5–3k events/s;
16,044 events took 13.8 s). The owner's restore, including the 4.7 MB corpus, runs
first on every learner's path. ≈550 Worker lines, ≈300 Python lines and ≈1,300 test
lines exist for this. No backup outside Cloudflare.

Defects (DEV-37): owner rebind with `email: ""` on every non-owner request
(`deploy/worker.ts` → `bindWho`); memory-only corpus revision likely re-archives the
corpus after eviction; hourly cron restores every subscribed account; liveness probe
counts the 270 MB `audio.db`; item tokens fall back to `PROXY_TOKEN`; one
process-wide 3.5 s LLM throttle (`eesti/providers/llm.py`).

Options: A harden in place (do the defect fixes regardless); **B Litestream on Cloud
Run (recommended)**: per-learner SQLite replicated to R2 with directory watching,
lazy restore on first request, corpus on the read-only GCS mount, Durable Objects for
accounts/sessions/push, nightly copy off Cloudflare; trade-off ≤1 s loss window on an
unclean crash instead of per-response confirmation; C persistent-disk VM (GCE
e2-micro is US-only and 1 GB; Oracle Always Free was halved to 2 OCPU/12 GB in 2026);
D Durable Object as writer (4–6k lines rewritten; rejected).

### Model lane

GPT-OSS-120B: hand set 8/10 caught, 8/8 clean; TalTech external track 2/40 caught,
16/20 clean. Claude Haiku 5.5: 1M context (100K is the price threshold, not the
context), 128K output, $0.10/$0.50 per MTok up to 100K-token prompts ($0.50/$2.50
above), cache read $0.01, batch $0.05/$0.25. ≈$0.0003 per tutor call; ≈$3/month at
the 300-call daily cap; Sonnet 5.5 ≈$54/month at the same cap.

Switching requires: removing `temperature: 0` (Haiku 5.5 rejects values ≠ 1); explicit
`output_config.effort` (thinking on by default, billed as output); JSON-schema
structured outputs; refusal handling (no server-side fallback on Haiku 5.5); native
Messages API via the `anthropic` SDK; a prompt-size guard ≤100K tokens (compaction is
a multi-turn feature and not used); scoping the throttle to evals; an ADR replacing
"no paid inference host" with a spend ceiling; the hand and external evals.

Grounding: the EKI rule text Grove cites fits a cached prefix (estimate tens of
thousands of tokens; measure). Free-form Q&A uses citations (not combinable with
structured outputs); grammar checks keep schemas.

### EmbeddingGemma 2

Released 6 Oct 2026 (Apache 2.0; 270M text to 740M multimodal; 8,192-token context;
Matryoshka 768→128). Multilingual MTEB 61.36 (v1 61.15; Qwen3-Embedding-0.6B 64.33);
no Estonian evaluation anywhere; float16 yields NaN. Runs free on the 2018 Mac mini
(estimate: overnight for 200k short items); Workers AI has only v1. Owner decision:
not used; revisit only for cross-lingual phrase search.

### Speech

Keep TalTech first (7% vs 36% WER on 8 clips). Replace the 25 s fallback wait with a
heartbeat. Workers VPC is free only in beta. Candidates only after a learner-audio
eval: Deepgram Nova-3, NVIDIA Parakeet/Canary, TalTech streaming Zipformer; evaluate
on TalTech EFAC (50 Russian-L1 speakers, evaluation only). No ready-made Estonian
pronunciation scoring exists (Azure supports Finnish, not Estonian).

## Sources

Norm change: ÕS 2025 is the normative basis since 1 Jan 2026 and accepts more
parallel forms; rection drills grade against EKK (2007, aligned to ÕS 2006).

Freshness: EKI bulk files unchanged (PSV 2014, A1A2B1 2018); Ekilex terms unchanged
(CC BY 4.0); Teatmik active; TartuNLP translation `/v1` deprecated, `/v2` offers
est↔rus/ukr/eng; TalTech ASR models current; HARNO formats unchanged, Q4 sittings
A2 7 Nov and B1 8 Nov 2026, 2027 registration opens 1 Jan; EIS public tasks show
per-question feedback since Jan 2026; ERR Lihtsad uudised weekly with read-aloud audio;
EstGEC-L2 read from `main` unpinned.

Most valuable unused resources: EKI etLex grammar profiles and word lists (public
API, terms not stated); Ekilex Ukrainian/English translations and collocations;
Settle in Estonia A1/A2 materials (CC BY-SA 3.0 in metadata; confirm); ERR Lihtsad
uudised audio (permission); TestEst diagnostic and sample tests; graded exam writing
(720 HARNO scripts, MIT; `elle_et` 1,697 texts, CC BY 4.0); Sõnaveeb *Õpime eesti
keelt* model letters (CC BY 4.0); EKI pronunciation exercises (37, CC BY 4.0, confirm
audio); EKI picture dictionary JSON (uk/en/ru, Estonian audio); TalTech EFAC; Corpus
of Estonian Web Sentences; UD Estonian EDT; EKI KORP corpora; EKI Combined Dictionary
2023.

Risks: `api.sonapi.ee` has no identifiable operator or terms; the enriched word list's
levels come from Ekilex and cover ≈6.2% of words (CC BY-SA share-alike); ERR allows a
headline plus five sentences without permission; HARNO samples are published
unchanged with authors' permission; TartuNLP GEC 8B is a Llama 3.1 derivative;
etLex, Teatmik, Keeleklikk and Selges keeles state no licence.

## Market

No Estonian course on Duolingo, Babbel, Busuu or Rosetta Stone. Keeleklikk (0–A2,
free, video), Keeletee (B1), Keelelend (B2, Estonian-only), Selgeks (A1–B1 → A2 exam,
English only, verified via EKI), Konsta.app (RU/UK + 5, Gemini-generated, unverified),
Keeli (student project, RU/UK), Speakly, Lingvist. B1 is the largest and hardest
cohort: 3,615 candidates in 2024 at 62.9% pass (A2: 2,387 at 70.7%). Grove's
combination (Russian/Ukrainian/English explanations, morphology-verified grading, B1
practice, honest readiness, free offline) is unoccupied.

Global patterns worth copying (DEV-45): edit-then-explain (Song et al., NAACL 2024:
40.6% → 93.9% correct explanations); hint before the answer; mistakes session;
format-weighted mastery with a mislearned state (Kwiziq); adaptive placement;
conversation as a mission with objectives (Duolingo Video Call, Rosetta Stone,
Babbel); listening micro-drills; sentence mining (Readlang, Migaku); generate → verify
→ select; per-language contrast notes (Babbel). Exam preparation (DEV-41): official
formats, both writing tasks, criteria and rated samples, per-part uncertainty, timed
speaking simulation, exam-day medium (paper), topic-grouped input (Yle YKI-treenit),
route to a human reviewer, checks with measured precision (Cambridge Write & Improve).
Traps: engagement as learning, unverified generated content at scale, chatbots
without curriculum, absolute pronunciation scores, outcome claims without controls.

## Versions (8 Oct 2026)

Current: estnltk 1.7.5, fsrs 6.3.2 (no FSRS-7 release), uvicorn 0.54.0, starlette
1.7.0, pypdf 6.19.0, Pillow 12.3.0, TypeScript 7.0.2, esbuild 0.28.2, hls.js 1.7.3.
Patch: Python 3.14.8, FastAPI 0.142.4, wrangler 4.148.0, workers-types 5.20261008.1,
pypdfium2 5.14.0, cryptography 50.0.2, axe-core 4.14.0. Blocked: Python 3.15 (no
estnltk/crfsuite/pyahocorasick/httptools wheels). Node 26 after 28 Oct. Advisories:
nltk GHSA-8mgp-746c-j5xp (no fix, unused APIs); sharp GHSA-wq5f-xc86-pv6w (dev-only;
npm override). Cloudflare Containers still paid-only; Python Workers GA but no
WebAssembly build of estnltk; Workers AI free allocation unchanged at 10,000
neurons/day.

## Revisit when

- One origin instance cannot keep up: move write authority to a database service.
- Model spend nears the ADR ceiling: lower effort, batch offline work, Workers AI for
  conversation turns.
- More than ≈100 active learners: per-account allowances; durable guest limits.
- 20+ verified learner clips: re-decide the ASR order (ADR-0003).
- HARNO's digital exam leaves its pilot: mirror digital task formats.
