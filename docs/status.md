# Status

What the app does today, what it does not, and the known issues. Counts marked
as checked are asserted by `tests/test_docs_match_code.py`; update this file in
the same change that makes it untrue.

The Practice rhythm interface below is implemented in this checkout and visible
on the public app. The public health stamp has no Git revision, so it does not
establish exact parity with the checkout. Local QA findings and unverified
release gates are in `qa/results.md`.
The local fixes now bind dictation grading to a signed passage and its recipient.
Container builds serve one compressed JavaScript bundle and compressed CSS;
the requested start screen and skill glosses appear before module initialization.
These changes have not been deployed by the QA session.

## What works

| Area | State |
|---|---|
| **Identity** | Grove keeps its curved leaf and self-hosted Geologica; platform and social artwork use deep blue on pale blue. The app opens straight into learning with no cover (`docs/brand.md`). |
| **Drills** | 37 of 43 curriculum topics generate items for every learner. Outside the owner's scope, where the harvested corpus is hidden, the corpus-based topics draw on EKI EVS's example phrases, credited per item (`evs.phrases`; `docs/sources.md`): case gap-fill, the comma drill, and `sonajark` as EVS noun phrases rebuilt from tiles, only where EKK fixes the order (SÜ 98, 104). Topics: object case, verb forms, conjugation, locative cases, comparison, numerals, telling the time and dates (`eesti/timedate.py`), the ma- and des-forms (`eesti/verbforms.py`), pronouns from the EKI teatmik tables (`eesti/pronouns.py`), pre- and postpositions (`eesti/postpositions.py`), käima against minema (`eesti/motion.py`), -mine and -ja nouns (`eesti/wordbuilding.py`), the indirect mood (`eesti/moods.py`), *mul on* / *mulle meeldib* / *mul on vaja* (`eesti/possession.py`), conjunctions and adverbs of place (`eesti/particles.py`), question words, word order, punctuation, rection. |
| **Exercise guidance** | Practice states the action in Russian and explains common case/person labels (`alaleütlev`, `nemad`) beside the Estonian term. The A1 personal-pronoun exercise includes an editorial whole-sentence Russian translation and pronoun meaning for each known frame (`eesti/scaffolding.py`); new or unknown frames receive no guessed translation. Other online exercises offer **Tõlge**, requested only on a click and labelled with the translation engine. Reading support does not grade or record an answer; offline practice keeps available local support without requesting translation. |
| **Grading** | Drills: code. Free writing: model chain plus deterministic checks. Meaning and conversation scoring by a model: authorised, not built; conversation practice is available. |
| **Plan** | Home offers one next lesson or current session. The planning API remains available for existing clients, while the web removes the competing time-budget dashboard. Guided sessions use learn → five checked exercises → result; completed topics offer the next topic. |
| **Course** | Prerequisite-ordered topics, mastery gate, end-of-level checkpoints (web and CLI), and interleaved practice when the next topic needs preparation. Test-out runs from `Kursus` or the CLI (five of five, graded server-side); the separate placement sweep is CLI-only (`cli assess`). Reversible navigation skips leave assessed mastery unchanged. |
| **Review** | FSRS-6 over items answered wrong, cards seeded on mastery, and words mined from reading. Grammar cards are answered and rated by code (again / hard when slow / good); vocabulary cards are self-rated. A correct drill answer on a due card counts as its review. |
| **Reading** | Selges keeles texts, the weekly ERR *Lihtsad uudised* feed and the Raadio 4 language archives; click-to-look-up; recommended by the share of running words within reach (known, or A1–A2 on the word list), at least 80 %, shorter first (`docs/curriculum.md`). |
| **Vocabulary** | `Sõnavara` leads with five-word practice; the optional collection filters by CEFR level and part of speech, commonest first. The word card sets a status. *Sõnatrenn* checks the typed Estonian against the word list; a miss can be queued for Kordamine. Exercise skips and answers create no graded attempts or mastery. |
| **Meaning** | **315 Russian glosses ship with the app** (`data/seed_glossary.tsv`). Russian order: seed → live dictionary → EKI EVS → EKI HAR (`eesti/meaning.py`). EVS homographs are chosen by EKI's level list, part of speech and corpus frequency (*siin* «здесь», not the noun «шина»); a sense EVS restricts to negation is left out when the first sense is ordinary (*hästi*, not «не очень») (`eesti/evs.py`). Homographs of one part of speech still share the card, ordered by sense count. Definitions: EKI PSV → live → VSL → EKSS. |
| **Live dictionary** | EKI's Ekilex API when `EKILEX_API_KEY` is set, otherwise the Sõnaveeb mirror; answers stored once per word. |
| **Rules** | 36 of 37 drillable topics link to the handbook. `kusisonad` has no drill link, deliberately: no EKK section is written for its mistakes. Every topic has a **Reegel** page (`eesti/lessons.py`), opened from Kursus, a running set and free practice: the EKK summary, a one-line gist with the typical mistake, written points in Russian for every topic (`eesti/lessontext.py`, each citing EKK, the EKI teatmik or EKI's learner grammar tables); object-case points distinguish completion from tense, omastav from nimetav, and ordinary negation from contrastive negation, a form table built by Vabamorf with each case's question and ending, the topic's own drill sentences, the learner's recent mistakes and linked texts. |
| **Word readings** | The form index (`edge.db`) keeps only forms Vabamorf reads back to the same lemma and tag; a word with nothing to inflect (`kus`, `aga`) is listed once and named by its part of speech. A word tapped in a text is looked up with its sentence: Vabamorf's disambiguator marks the reading it uses (*selles lauses*), puts it first, and **Kordamisse** queues that word (`mulle` in *Anna mulle* is `mina`). TartuNLP's neural tagger (`est-roberta-vm-morph-tagging`, CC BY-SA 4.0) was measured on 2 000 genuinely ambiguous words in EVS phrases, where EKI's headword says which word is meant: Vabamorf 66% right, 24% left open, 10% wrong; the tagger 75% right, 5% left open, 16% wrong. Where Vabamorf leaves a word open, the tagger agrees with EKI about half the time even at 99% confidence, so it is not used: a confidently wrong reading on the card is worse than two honest ones, and it would put PyTorch in the image. |
| **Example phrases** | The word card's *Näited*: EKI EVS's example phrases, each with its Russian, offline — 137 316 phrases for 34 802 lemmas (`evs.examples`). Three show, the rest fold, each with a play button; the word's 1 912 EVS idioms fold under *Väljendid*. A word's meaning card in Järjekord shows one (a different one each review) and, from the second review, asks for it to be built from tiles (*Koosta fraas*); code compares the order with EKI's and says so neutrally, and the learner still rates the card. |
| **Question-word cues** | A `kusisonad` item shows the Russian for the question word its blank wants, from EKI EVS (`docs/curriculum.md`): 8 of 12 answer words. |
| **Conversation** | `Vestlus` in Rääkimine: a model plays the paired-exam partner over a task card, in Estonian, for at most 8 turns. The learner can speak a turn, review the tentative Cloudflare/local ASR text before sending, and hear the partner through TartuNLP TTS. It never corrects or scores; forms Vabamorf does not know are named. Only that a conversation happened is recorded. |
| **Tutor** | `Selgita` on a missed item: one model call grounded in the attempt, Vabamorf's reading and the EKK section; the answer is dropped if it quotes a form Vabamorf does not know, and never decides anything (`eesti/tutor.py`). |
| **Writing** | Grammar check through the provider chain (`docs/ai-providers.md`), plus deterministic spelling, subject–verb agreement and rection checks; back-translation; corrections queue for the Notion `Vead` log. |
| **Listening** | Dictation (graded) from sentences read by EKI's own readers where they exist, the corpus otherwise, and EKI EVS's example phrases outside the owner's scope; TartuNLP TTS on any text; ERR episode audio. |
| **Speaking** | Paired-exam question bank with TTS, read-aloud with comparison (corpus sentences, or EKI EVS's example phrases outside the owner's scope), open-answer feedback over the transcript, `Vestlus` (a model plays the partner), and — under `cli serve` only — optional saving from ordinary mic practice into `Hindamiskomplekt`. The learner can play a saved answer, correct tentative ASR text in the page and confirm what was actually said for the private speech eval set. Ordinary practice audio stays unsaved. Each answer is recorded with what code can measure — answered or not, words, pace, and the share of words Vabamorf does not know, which flags a transcript the recogniser struggled with. Readiness reports that practice and still refuses to judge the part. A drill answer can be spoken: the microphone beside the answer box fills it with what was heard, and the learner checks it before grading (`eesti/web/js/voice.js`). |
| **Exam** | HARNO's own shape as data (`eesti/exam.py`): A2 4×20, B1 4×25, pass at 60 % with no part at zero, and the published sittings. Writing has two tasks: 30 minutes at A2, 35 at B1. The learner picks a sitting in `Eksam`; it is learner state (a `goal-set` event), drives the countdown and exports as `.ics`. |
| **Official tasks** | Owner-imported HARNO PDFs, recordings and EIS tasks open inside `Eksam`. `cli prepare-exam` writes private page-aware PDF sidecars with individual figures and optional Estonian OCR. A visually checked A2 reading PDF supplies six native choices; a B1 reading PDF supplies nine situation-to-ad matches. Both use their printed keys and are practice only; these owner-only tasks are verified from the owner’s session. The other 27 task PDFs remain ungraded page text and figures, plus original pages. EIS scoring still opens on its own site. Absent downloads link out. Private study only; every task carries © Haridus- ja Noorteamet (`docs/exam-native.md`). |
| **Mock** | `Proovieksam`: one exam part on the exam's own clock, or all four in the exam's order (`eesti/mock.py`). Reading is gap-fill in corpus sentences, listening is dictation (both on EKI EVS's example phrases outside the owner's scope), writing practises only the longer task over the whole part's clock and checks length plus deterministic spelling, agreement and rection, speaking is the question bank and is never scored. Each section says what it really is, and counts as evidence for its part. |
| **Readiness** | Four exam parts remain separate with reasons in Russian and contact towards three (`contact`, `contact_target`). Readiness is an optional Exam fold; speech remains explicitly unmeasured. It grants no mastery or FSRS state. |
| **Interface** | Practice rhythm replaces the boardwalk/glass shell: pale blue/aqua ground, frosted navigation, solid tasks and blue actions (`DESIGN.md`). Four skills are permanent; Home, Course, Review, Exam and account are ordinary destinations. Onboarding has beginning, chosen start and bounded grammar assessment; topic skips are reversible and separate from checked mastery. Geologica and Phosphor remain self-hosted. Progress history and the 14-day review forecast remain available in folds. |
| **Milestones** | Four level-specific markers derive from recorded practice, topic mastery, a passed checkpoint and completion of all four mock parts. They award no points, streaks or mastery (`eesti/milestones.py`). |
| **Reading questions** | Under any text long enough to ask about (`Lugemine → Küsimused`): five questions in Estonian, written by a model and keyed by the text itself — an answer that is not the text's own words, verbatim and once, never becomes a question (ADR-0004). Answers are graded by code against the stored span and recorded as `comprehension`, the one event that counts as practice for the `lugemine` part. The questions are learner state (a `questions-made` event), not library data, so they survive a cold start and an attempt can still be replayed against the question it was asked about. |
| **Reminders** | Off until switched on in `Edenemine → Meeldetuletused`. Four facts, each decided by code from the evidence (`eesti/reminders.py`): a review queue past 10 cards, a day with nothing done after the hour the learner picked, registration closing in 14 and in 3 days, and a silence of 3 days — said once, not daily. Quiet hours by default 22:00–08:00, Europe/Tallinn. A notification carries a count and a fixed phrase, never anything the learner wrote; the Worker's hourly cron sends it (VAPID, encrypted per subscription). On iPhone it needs the app on the Home Screen (iOS 16.4+). |
| **Offline** | Installable PWA. A five-item pack can be fetched in Course → Offline. The page grades locally and queues answers in IndexedDB; the server re-grades signed tokens on reconnect, idempotently. APIs are never cached. If no cached shell is available, a readable light/dark fallback explains the missing copy and offers a retry that returns to the app when connectivity resumes. |
| **Review schedule** | FSRS-6 with the published parameters until there are about 1 000 reviews; `cli optimise-review` then fits this learner's own and records them as a `fsrs-parameters` event, so they travel with the log. The optimiser's dependencies (torch, pandas) stay off the deployment: it is run locally, once in a while. |
| **Evidence** | Every learner-state change is an event in an append-only log (`eesti/evidence.py`); the learner databases are rebuilt from it. Attempts carry the item, its signed ref (regenerable) and the answer time; reviews carry the FSRS rating and who chose it. `Minu andmed` downloads the log. |
| **Operations** | One JSON line per API call on stdout (`eesti/logs.py`), carrying route, status and duration and never what was written or said. Each provider lane has a daily allowance (`providers/budget.py`), reported by `/api/engines`. |
| **Deployment** | Cloud Run capped at one instance behind a public Cloudflare Worker; EKI recordings and HARNO exam files are mounted from Cloud Storage. A successful permanent-account API response waits until the evidence log is copied through its reported sequence for the same origin boot in the learner's Durable Object; failed confirmation is a retriable 503. The log is pushed back into each new instance; all EKI reference data and the reading corpus are present. |
| **Accounts** | Sign-up and sign-in run in the Worker; accounts keep separate files and Durable Objects. Signed-out use is an isolated guest sandbox with its own onboarding choices. Header Profile owns identity, starting point and recovery; recorded history has its own Progress page. Permanent accounts can reset/restore without changing their identity. |

## What is missing

### 6 curriculum topics have no generator

```
tahestik  lauseehitus  astmevaheldus  tulevik  uhendverbid  liitsonad
```

They appear in the syllabus as reference topics and do not gate the path. The
source of truth is `[t.id for t in TOPICS if not t.generator]`.

- `astmevaheldus` is intentionally reference-only; its contrast is drilled via
  `gen-stem`.
- `asesonad` is drilled from the EKI teatmik's pronoun tables, not Vabamorf,
  whose pronoun paradigms are wrong (`mina` → genitive `mina`).
- `uhendverbid` and `liitsonad` have too few marked examples in the corpus for
  the attested-corrections approach behind `word-order`.

### Instructional coverage

Explanations and word meanings currently support Russian speakers. English and
Ukrainian speakers do not have equivalent instructional support. The A0 starting
recommendation does not constitute a complete beginner course. Candidate courses
and dictionary exports still need rights and quality review
(`docs/source-integrations.md`).

The confirmed product direction in `PRODUCT.md` adds a complete beginner path,
onboarding through a chosen starting point or an assessment, revisitable skips
across lessons and skill activities, and English/Ukrainian instructional support.
The course API supports reversible topic skips and explicit starting-level
navigation, and guest onboarding preferences are scoped to the guest sandbox.
The web exposes all three onboarding routes, reversible topic skips and individual
exercise/word skips. Listening and read-aloud use EKI EVS's example phrases
when imported content is hidden or empty, then generated starter sentences. Complete beginner sequencing and
English/Ukrainian instructional coverage remain content gaps, tracked in DEV-5.
The grammar assessment never claims to measure all four skills or certify CEFR.

### Not built, by decision

- **Acoustic pronunciation scoring** — the app links to EKI's free
  pronunciation exercises instead.
- **The `tuttav` word status has no control** — it sits on the same side of
  "settled" as `õpin`; the stored status remains supported.

## Known issues

- **Learners other than the owner get no reading texts.** Every harvested
  source (Selges keeles, ERR, HARNO, EIS) is marked not redistributable in
  `eesti/licences.py`, and `eesti/sources.py` hides them outside the owner's
  scope, so `Lugemine` is empty for guests and signed-up learners. Their drills,
  dictation, read-aloud and mock reading and listening use EKI EVS's example
  phrases instead: dictionary phrases, often fragments in lower case. Their
  word-order practice is noun-phrase order only (attributes before the head);
  verb-second clause order has more than one correct answer in EVS's phrases,
  so it waits for attested or reviewed material. Licensable texts and
  permission requests are tracked in DEV-36.
- **Deterministic writing checks miss partitive objects.** They do not flag
  *loen raamat* or *jõin kohv*, can treat an illative such as *poodi* as an
  object, and can suggest a wrong spelling (*Tallinas* → *Tallina*; DEV-50).
- **Answer keys follow EKK, not ÕS 2025.** ÕS 2025 is the normative basis and
  accepts more parallel forms; rection drills and checks use the EKK handbook
  aligned to ÕS 2006 (DEV-52).
- **Every model call passes one process-wide 3.5 s throttle.** It was written
  for evaluation rate limits and also serialises learners' tutor calls
  (`eesti/providers/llm.py`; DEV-38).
- **Official interactive tasks are not solvable in the app.** Matching tasks
  render without their options and listening tasks without answer choices;
  a sitting whose registration has closed is offered without a warning (DEV-53).
- **Password recovery remains owner-managed.** There is no self-service reset
  screen. The owner can reset a password using the procedure in
  `docs/deploy.md`; account removal is available to the owner and clears that
  learner's origin files and Durable Object data before disabling the login.
- **Grammar is qualified, not provider-count driven.** Workers AI GPT-OSS-120B
  is the only automatic hosted grammar/tutor lane, with deterministic offline
  degradation. Other LLMs, public GEC and est→est normalization remain explicit
  evaluation candidates; see `docs/ai-providers.md`.
- **Public GEC is not a production dependency.** It is excluded from automatic
  traffic; run its diagnostic and quality eval before considering it again.
  TTS and translation remain separate services.
- **Allowances are not billing caps.** Workers AI speech and text share the
  account allocation; local counters do not measure all account usage. The
  weekly grammar eval checks the production lane.
- **Source refreshes preserve usable data.** Partial and pointer-only harvests
  merge by source URL and level, preserving issued ids, stored text, recordings
  and other levels. HARNO validates downloads before atomic replacement;
  content upload rejects empty or corrupt databases. Refresh metadata records
  checks and hashes, without claiming a publication date for unversioned files.
  Upload rebuilds topic links and requires a built word list.
- **Reminder delivery remains unverified.** VAPID bindings and hourly cron are
  deployed, and Chrome on the owner's Mac is subscribed; actual delivery has
  not been confirmed.
- **Browser journeys in CI run without the reading corpus.** The `journeys`
  job builds the word list; reading journeys still skip there (`docs/testing.md`).
- **4 of 12 question words have no Russian cue.** `kelle`, `kellele`,
  `kellega` are forms of `kes` and `kui palju` is two words, so EVS has no
  headword for them. EKI's Russian–Estonian dictionary (VES, same source
  page) might attest them from the Russian side (`с кем` → `kellega`); it is
  not downloaded or checked.
- **ASR on the learner's voice rests on 8 verified clips.** The home service's
  TalTech engine misheard 7% of the owner's words against Workers AI's 36%, on
  fewer than the 20-clip pilot floor (`docs/asr-evaluation.md`). `Kuidas mind
  kuuldakse` in Rääkimine keeps measuring the production recogniser
  (`eesti/asrcheck.py`).
- **Speech quality depends on the owner's Mac mini being awake.** When it is
  off, the Worker falls back to Workers AI after up to 25 s
  (`deploy/home-asr/README.md`).
- **A few EVS glosses follow the rarer homograph.** Where EKI's level list
  tags a word by its rarer reading, the card follows the list (*väär* is
  listed as a noun, so EVS's «хоры» shows rather than «неправильный»), and
  homographs of one part of speech are ordered by sense count (*kord* puts
  «раз» fourth). The live dictionary outranks EVS on the card when it answers.
- **Live replication is not an independent backup.** Permanent-account API
  responses wait for acknowledgement of the event sequence and origin boot,
  but a hosting-account loss can still remove the live copies. Scheduled
  independent backups and self-service erasure are deferred. Private exports
  can be replay-checked with `cli verify-backup`; see `docs/deploy.md` and
  ADR-0005.
