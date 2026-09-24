# Status

What the app does today, what it does not, and the known issues. Counts marked
as checked are asserted by `tests/test_docs_match_code.py`; update this file in
the same change that makes it untrue.

## What works

| Area | State |
|---|---|
| **Drills** | 26 of 36 curriculum topics generate items: object case, verb forms, conjugation, locative cases, comparison, numerals, question words, word order, punctuation, rection. |
| **Grading** | Drills: code. Free writing: model chain plus deterministic checks. Meaning and conversation scoring by a model: authorised, not built; conversation practice is available. |
| **Plan** | Rada's Täna: today's blocks in a time budget (reviews, the weakest rule with its last mistake, refresh, the least-practised exam part, the next topic, a text), each with its reason in Russian (`eesti/planning.py`). |
| **Path** | Prerequisite-ordered topics, mastery gate, end-of-level checkpoints (web and CLI), blocked → interleaved handoff. Test-out runs from `Kogu rada` or the CLI (five of five, graded server-side); the placement sweep is CLI-only (`cli assess`). |
| **Review** | FSRS-6 over items answered wrong, cards seeded on mastery, and words mined from reading. Grammar cards are answered and rated by code (again / hard when slow / good); vocabulary cards are self-rated. A correct drill answer on a due card counts as its review. |
| **Reading** | Selges keeles texts, the weekly ERR *Lihtsad uudised* feed and the Raadio 4 language archives; click-to-look-up; recommended by the share of running words within reach (known, or A1–A2 on the word list), at least 80 %, shorter first (`docs/curriculum.md`). |
| **Vocabulary** | `Sõnavara` lists the word list by CEFR level and part of speech, commonest first; the word card sets a status. |
| **Meaning** | **294 Russian glosses ship with the app** (`data/seed_glossary.tsv`). Russian order: seed → live dictionary → EKI EVS → EKI HAR (`eesti/meaning.py`). Definitions: EKI PSV → live → VSL → EKSS. |
| **Live dictionary** | EKI's Ekilex API when `EKILEX_API_KEY` is set, otherwise the Sõnaveeb mirror; answers stored once per word. |
| **Rules** | 25 of 26 drillable topics link to the handbook. `kusisonad` has none, deliberately: no EKK section covers question words. |
| **Question-word cues** | A `kusisonad` item shows the Russian for the question word its blank wants, from EKI EVS (`docs/curriculum.md`): 8 of 12 answer words. |
| **Conversation** | `Vestlus` in Rääkimine: a model plays the paired-exam partner over a task card, in Estonian, for at most 8 turns. The learner can speak a turn, review the tentative Cloudflare/local ASR text before sending, and hear the partner through TartuNLP TTS. It never corrects or scores; forms Vabamorf does not know are named. Only that a conversation happened is recorded. |
| **Tutor** | `Selgita` on a missed item: one model call grounded in the attempt, Vabamorf's reading and the EKK section; the answer is dropped if it quotes a form Vabamorf does not know, and never decides anything (`eesti/tutor.py`). |
| **Writing** | Grammar check through the provider chain (`docs/ai-providers.md`), plus deterministic spelling, subject–verb agreement and rection checks; back-translation; corrections queue for the Notion `Vead` log. |
| **Listening** | Dictation (graded) from sentences read by EKI's own readers where they exist, the corpus otherwise; TartuNLP TTS on any text; ERR episode audio. |
| **Speaking** | Paired-exam question bank with TTS, read-aloud with comparison, open-answer feedback over the transcript, `Vestlus` (a model plays the partner), and — under `cli serve` only — optional saving from ordinary mic practice into `Hindamiskomplekt`. The learner can play a saved answer, correct tentative ASR text in the page and confirm what was actually said for the private speech eval set. Ordinary practice audio stays unsaved. Each answer is recorded with what code can measure — answered or not, words, pace, and the share of words Vabamorf does not know, which flags a transcript the recogniser struggled with. Readiness reports that practice and still refuses to judge the part. |
| **Exam** | HARNO's own shape as data (`eesti/exam.py`, checked 2026-09-19): A2 4×20, B1 4×25, pass at 60 % with no part at zero, and the published sittings. The learner picks a sitting in `Eksam`; it is learner state (a `goal-set` event), drives the countdown and exports as `.ics`. |
| **Official tasks** | HARNO's own past tasks and listening recordings, plus EIS's interactive practice tasks — their instruction, questions and every recording — downloaded with `cli harvest-exam --download` and opened inside `Eksam`: extracted PDF text, original PDF pages rendered on demand, and audio play on the page (`/api/exam/file`, `/api/exam/page`, `/api/exam/text`). A task that was not downloaded still links out. EIS answers exist only on their server, so official scoring opens there. Private study only; every task carries © Haridus- ja Noorteamet. |
| **Mock** | `Proovieksam`: one exam part on the exam's own clock, or all four in the exam's order (`eesti/mock.py`). Reading is gap-fill in corpus sentences, listening is dictation, writing is HARNO's task shape graded on length plus the deterministic checks (spelling, agreement, rection), speaking is the question bank and is never scored. Each section says what it really is, and counts as evidence for its part. |
| **Readiness** | Four exam parts reported separately with reasons in Russian; a section sat on the clock counts as contact for its part. |
| **Reading questions** | Under any text long enough to ask about (`Lugemine → Küsimused`): five questions in Estonian, written by a model and keyed by the text itself — an answer that is not the text's own words, verbatim and once, never becomes a question (ADR-0004). Answers are graded by code against the stored span and recorded as `comprehension`, the one event that counts as practice for the `lugemine` part. The questions are learner state (a `questions-made` event), not library data, so they survive a cold start and an attempt can still be replayed against the question it was asked about. |
| **Reminders** | Off until switched on in `Edenemine → Meeldetuletused`. Four facts, each decided by code from the evidence (`eesti/reminders.py`): a review queue past 10 cards, a day with nothing done after the hour the learner picked, registration closing in 14 and in 3 days, and a silence of 3 days — said once, not daily. Quiet hours by default 22:00–08:00, Europe/Tallinn. A notification carries a count and a fixed phrase, never anything the learner wrote; the Worker's hourly cron sends it (VAPID, encrypted per subscription). On iPhone it needs the app on the Home Screen (iOS 16.4+). |
| **Offline** | Installable PWA. A pack of drills can be fetched in advance (`Rada → Offline`): the page grades it by the same rule and queues the answers in IndexedDB, and the server re-grades each one from its signed token when the connection returns — the queue is idempotent, so sending it twice records once. The API itself is never cached. |
| **Review schedule** | FSRS-6 with the published parameters until there are about 1 000 reviews; `cli optimise-review` then fits this learner's own and records them as a `fsrs-parameters` event, so they travel with the log. The optimiser's dependencies (torch, pandas) stay off the deployment: it is run locally, once in a while. |
| **Evidence** | Every learner-state change is an event in an append-only log (`eesti/evidence.py`); the learner databases are rebuilt from it. Attempts carry the item, its signed ref (regenerable) and the answer time; reviews carry the FSRS rating and who chose it. `Minu andmed` downloads the log. |
| **Operations** | One JSON line per API call on stdout (`eesti/logs.py`), carrying route, status and duration and never what was written or said. Each provider lane has a daily allowance (`providers/budget.py`), reported by `/api/engines`. |
| **Deployment** | Cloud Run capped at one instance behind a Cloudflare Worker + Access; EKI recordings and HARNO exam files are mounted from Cloud Storage. The evidence log is copied into the Worker's Durable Object after every request and pushed back into each new instance; all EKI reference data and the reading corpus are present. |

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
- `uhendverbid` and `liitsonad` have too few marked examples in the corpus for
  the attested-corrections approach behind `word-order`.

### Not built, by decision

- **Acoustic pronunciation scoring** — the app links to EKI's free
  pronunciation exercises instead.
- **Local ASR in production** — recognition runs on Cloudflare Workers AI; the
  speaking panel says the recording leaves the device. Local whisper.cpp works
  only under `cli serve`.
- **The `tuttav` word status has no control** — it sits on the same side of
  "settled" as `õpin`; kept in the model to avoid a migration.

## Known issues

- **Grammar is qualified, not provider-count driven.** Workers AI GPT-OSS-120B
  is the only automatic hosted grammar/tutor lane, with deterministic offline
  degradation. Other LLMs and public GEC/est→est normalization remain explicit
  evaluation candidates. Fresh Mistral/newer-model comparisons are recorded in
  `docs/evaluations/providers.json` and explained in `docs/ai-providers.md`.
- **Public GEC remains unavailable.** Both endpoints timed out on all three
  12-second probes on 2026-09-23; longer probes on 2026-09-22 returned HTTP 500
  near 60 seconds. It is removed from automatic traffic. TTS and translation
  independently pass actual POST checks and remain in use.
- **Allowances are not billing caps.** Workers AI speech and text share the
  account allocation; local counters do not measure all account usage. The
  weekly grammar eval now checks the actual production lane.
- **Source refreshes preserve usable data.** Empty Selges responses keep the
  existing corpus; EIS failure does not stop HARNO. Deleting source content
  clears its links. Content upload rebuilds topic links before publishing and
  refuses without the publishing machine's built word list.
- **Reminder delivery remains unverified.** VAPID bindings and hourly cron are
  deployed. Chrome on the owner's Mac subscribed with permission granted on
  2026-09-23; an actual notification has not arrived yet.
- **Exam files are mounted but production still links out.** The deployed
  catalogue was published before the files were downloaded and lacks file
  pointers. The pending app change derives HARNO paths from official URLs;
  runtime access must be checked after deployment.
- **Browser journeys are not in CI.** They protect a release only when run
  locally (`docs/testing.md`).
- **4 of 12 question words have no Russian cue.** `kelle`, `kellele`,
  `kellega` are forms of `kes` and `kui palju` is two words, so EVS has no
  headword for them. EKI's Russian–Estonian dictionary (VES, same licence
  page) might attest them from the Russian side (`с кем` → `kellega`); it is
  not downloaded or checked.
- **ASR learner quality is unmeasured.** The existing harness compares named
  engines on manually verified audio, including false acceptance and morphology;
  this checkout has no learner eval clips. Native EKI controls ran on Cloudflare,
  TalTech CT2 and Zipformer, establishing runtime feasibility, not learner accuracy.
  Recording prompts are not ground truth.
  Production remains Cloudflare with a local TalTech reference; see
  `docs/asr-evaluation.md`.
- **State replication is asynchronous.** Event copying follows the response;
  an origin crash before copying can lose acknowledged work. There is no
  independent nightly backup or self-service erasure. Private exports can be
  replay-checked with `cli verify-backup`; see `docs/deploy.md` and ADR-0005.
