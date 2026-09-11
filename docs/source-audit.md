# Source audit

Every source, API and technique surfaced in research, against what is actually
built. Kept honest: "verified" means called and observed, not read about.

## GiellaLT: benefit without the duplication — 2026-09-11

The question put to it was the right one: **would it benefit us, and would it
create duplication?** Both answers are yes, and they apply to different halves.

`giellalt/lang-est-x-utee` was inspected rather than assumed. Its
`grammarchecker.cg3` is 35 KB, and the header is the Sámi template from UiT —
which is exactly the shape a stub would have. It is not a stub. The rules are
**genuinely Estonian**: `LIST Par` for the partitive, and 85 hand-written rules
whose comments are in Estonian and about Estonian (`# ta on is OK`,
`# ema ja tütar elasid|elaksid is OK`). The error tags it can emit include
`&err-agr` (agreement), `&err-gov` (**rection** — EVKK's second-largest learner
error class), `&err-no-conneg` and `&err-comma`.

### The duplication is real and structural

CG rules are written against a **specific tagset**. GiellaLT's rules speak
`PersPronSing1`, `Sg1`, `Nom`, `Par`; Vabamorf speaks `sg n`, `n`, `b`, `vad`.
There is no way to run their rules without running their morphology — so
adopting the toolchain means **a second morphological analyser beside
Vabamorf**, which is a second source of truth for the thing Vabamorf is the
answer key for. Plus HFST and VISL CG3 in a free-tier image, and a repository
its own maintainers file under `giellalt-experiment-langs` with a warning that
the builds are "not tested for language quality".

### So the linguistics was taken and the toolchain was not

`morph.agreement_errors` implements `&err-agr` over **Vabamorf's own tags**.
No new dependency, no second analyser, no build step, nothing of theirs copied
or shipped — and `sources.REGISTRY` records the debt with their LGPL-3.0.

This is the first thing in the app that **corrects** free writing with no model
in the loop. `object_case_candidates` reports which case a word is in and
refuses to judge it, because that needs telicity. `ma elab` needs nothing of
the kind: it is decidable from two adjacent words, and Vabamorf **synthesises**
the form that belongs there — `elan` — using the same call that generates every
drill answer.

**The exceptions were the valuable half, and they came straight from their rule
comments.** `sid` and `ksid` are 2sg *and* 3pl, so `sa elasid` and `nad elasid`
are both correct; a checker without that would flag the past tense with `sa`
every single time a learner used it. `eks`/`ega` flip a clause to the
imperative. Negation needs no special case, because a connegative carries no
person tag at all. All of it is pinned in `tests/test_agreement.py`, which also
regenerates the person/form table from Vabamorf so the two cannot drift.

`&err-gov` — rection — is the obvious next one, and is **not** attempted here:
it needs a verb-to-case table, which `sonapi` supplies per word and which this
project already stores. That is a real follow-up with a real source, not a
guess.

## Replacing ELLE: the sweep, and what it found — 2026-09-11

ELLE was closed as "no GEC endpoint, and every tool needs an account". The
follow-up question was whether anything else fills that hole. A sweep of
hosted APIs, open models, libraries, package indexes, community threads and
the Estonian language-technology bodies produced **three definitive negatives,
two documented candidates, and one thing that was already in the repository**.

### The negatives, so nobody re-checks them

| Checked | Result |
|---|---|
| **LanguageTool** — the obvious open grammar API | `api.languagetool.org/v2/languages` lists **62 languages and no Estonian**. Not a gap in their hosted tier; the language is not supported at all. |
| **Any hosted Estonian GEC model** | Every Estonian GEC model on Hugging Face — `tartuNLP/Llama-3.1-8B-est-gec-july-2025`, its `-highrec` sibling, `Llammas-…-GEC` — reports an empty `inferenceProviderMapping`. Nobody rents one. |
| **Consumer "Estonian grammar checker" sites** | Sapling, Rephrasely, paraphrasetool, hastewire and the rest are multilingual LLM wrappers with no Estonian case competence and no API worth binding to. This project already rejected that class once; nothing has changed. |

### The candidates, documented and not adopted

**`paulpall/GEC_Estonian_OPUS-MT`** — Apache-2.0, **73.9 M parameters**, Marian
seq2seq, fine-tuned from `Helsinki-NLP/opus-mt-fi-et`. Interesting because of
what it is *not*: every other Estonian GEC option is 7–8 B and needs a GPU,
and this is small enough to run on a CPU inside the app's own container. Two
things stop it being adopted on sight:

- it needs **torch and transformers in the image**, which is a serious change
  to a service that currently ships Vabamorf and FastAPI onto a free tier;
- it is trained on **textbook and legalese sentences**, not learner errors, so
  its error distribution is not this learner's. That is a measurement to make,
  not a guess to act on — `cli eval --track external` exists for exactly this.

**GiellaLT `lang-est-x-utee`** — LGPL-3.0, finite-state morphology plus
**Constraint Grammar** rules, 73 000 lemmas, from Heiki-Jaan Kaalep at the
University of Tartu. Architecturally this is the perfect answer: a
**deterministic, rule-based** Estonian grammar checker, no model deciding
anything. Two things hold it back: the repository is filed under
`giellalt-experiment-langs` and its own download page warns the nightly
packages are "not tested for language quality, and might contain regressions";
and building it needs HFST and VISL CG3, a non-Python toolchain, in the image.
**The strongest deterministic candidate found, and worth revisiting** when
either its maturity or this project's appetite for a build step changes.

### What was already here, and the bug that hid it

The sweep's real finding was in this repository, not on the internet.
**Vabamorf ships a spellchecker**, `estnltk.vabamorf.morf.spellcheck`, it is
already a dependency, it runs offline, it is deterministic, and `morph.py` has
wrapped it as `misspellings()` all along.

It was wired into `VabamorfFallback` — **the last provider in the chain**. And
`check()` returns the *first* provider that answers. So the moment an LLM lane
is configured, it answers, and Vabamorf's dictionary verdict is discarded. For
every request. For ever.

That inverts this project's central rule. A dictionary lookup is **code**, and
code does not lose to a model's opinion — but the chain was arranged so that it
always did. Worse, the model does not cover for it: the shipped prompt is aimed
at object case and says in as many words that most text is already correct and
to report a correction only where one of those rules is broken. `tanav` for
`tänav` breaks none of them.

So nothing in the app reported **the single commonest way a Russian speaker
mistypes Estonian** — a missing täpitäht — whenever the chain was working.

`_merge_spelling` fixes it: whatever answers, Vabamorf's verdict is merged into
the result. A word the provider already explained keeps the provider's
explanation, because that one has a reason attached and this one only has "not
in the dictionary". Nothing answering at all is still reported as nothing —
a spellcheck is never dressed up as a working grammar service.

**This is the honest replacement for ELLE.** Not a service, not a model: the
thing the app already had, moved to where it always applies.

## The three open threads, closed — 2026-09-11

The audit left three things open. Two are now wired and one is answered with
evidence rather than left hanging.

### 1. `cli import-levels` had never met the real file — hardened against what it holds

The importer could not be run against EKI's 51 015-row file from here, so
instead the **file was interrogated about its own contents**, and it turned out
to hold three things a fixture built from the schema would never have shown:

| What the real file holds | What the importer did | Now |
|---|---|---|
| ~200 lemmas on **more than one line** — the same word under two parts of speech (`all` as `D` and as `K`, `alaealine` as `A` and as `S`) | `official_levels.word` is a primary key, so `INSERT OR REPLACE` kept whichever line came last: a coin-toss between two of EKI's own rows, decided by file order | collapsed in the parser, **lowest level wins**. If EKI calls a word A1 in any of its uses the learner meets it at A1, and each level's pool is then a superset of the one below |
| **multi-word entries** — `aru saama`, `alla kirjutama`, `alles hoidma` | inserted into `words`, where `verbs_at_level` would hand `aru saama` to the conjugation drill and ask Vabamorf for its imperfect | kept in `official_levels`, which stays a faithful record of what EKI published, and out of `words`, which is the list of things this app generates exercises from |
| a few rows with a **blank level** | already dropped, by luck rather than by intent | dropped, with a test saying so |

Two things were added so the first real run is not the first look:

- **`cli import-levels --check`** reads the file and writes nothing, reporting
  the level counts, the multi-word entries and — the one that matters — any
  part-of-speech code `EKI_POS` does not know. This is the only command in the
  project that rewrites the CEFR level of every word the app drills, against a
  file that arrives from the learner rather than from here.
- **A stress test at the real scale**: 51 011 lemmas with the duplicates and
  phrases mixed through, asserting the collapse and the phrase guard hold at
  size. Not a benchmark — a check that nothing is quadratic on the one run that
  matters.

### 2. ELLE — answered, and the answer is no

The thread was "ELLE is alive at v26.9.1 and only `/api/status` was checked".
Its front end was read on 2026-09-11 and its whole API surface enumerated —
seventeen paths, and **not one of them is grammatical error correction**:

    /api/tools/masinoppe-ennustus      CEFR prediction
    /api/texts/keerukus-…              complexity, parts of speech, diversity
    /api/tools/wordanalyser            morphology
    /api/tools/wordlist  /collocates  /wordcontext  /minitorn-pikkus
    /api/texts/…                       the text library
    /api/auth  /api/status  /api/text-to-speech  /api/actuator/health

ELLE is a *text analysis* environment, not a corrector. Where its Tekstihindaja
shows corrections it is calling somebody else's GEC — most plausibly the same
TartuNLP service that has answered 500 since the first research round, which
would explain why ELLE's corrector was observed failing at exactly the same
time.

Two of the tools were probed anyway. Both answer **HTTP 500 in under a second**
— an instant refusal, not a timeout — and the bundle shows why: every tool call
carries `Authorization: Bearer …`. **They require an ELLE account.** This
repository must never hold a credential, so that is the end of it.

**There is no free, keyless, working Estonian GEC.** That is worth stating
plainly rather than leaving as a hopeful open item: the app's grammar chain is
correct against the one Estonian service that exists, that service is down, and
the LLM lane behind it is not a fallback but the thing that actually answers.

### 3. EKI *põhisõnavara sõnastik* — wired

`cli import-psv` imports EKI's learner dictionary: about 6 000 basic words
defined in language a learner can read, CC BY 4.0, from the same download page
as the level vocabulary.

**This is what *Keeleõppija Sõnaveeb* was wanted for**, and the earlier verdict
— out of reach without a second client against a site that asks not to be
batch-requested — was the right answer to the wrong question. EKI publishes it.

The format was read from **`schema_psv.xsd`, published beside the data**, not
guessed: `sr` → `A`, headword at `P/mg/m`, definition at `S/tp/tg/dg/d`,
example at `S/tp/tg/ng/n`. EKI warn on the same page that their XML does not
validate against that schema, so the parser reads by descendant tag rather than
rigid path and treats everything but the headword as optional.

Three decisions worth recording:

- **Two definitions, two databases.** It began as two columns of `word_gloss`
  in `vocab.db`, beside Sõnaveeb's answers, and that was wrong in a way that
  took a second look to see: `vocab.db` is in `STATE_DATABASES`, and a snapshot
  restore replaces the **file**, not the rows. Six thousand EKI definitions
  would have survived until the first restore and then gone, on a service that
  cold-starts constantly. They are reference data — identical for every
  learner, no more personal than the word list — so they live in `psv_gloss` in
  `data/eesti.db`, which is baked into the image. `/api/enrich` is the one
  place the two are read together, and it prefers EKI's, keeping Sõnaveeb's
  beside it as `full_definition`. Same rule that keeps `level` and `band`
  apart, applied to storage rather than to a column.
- **The baseline trap dissolved rather than handled.** While the two shared a
  row, a PSV import had the shape of the shipped seed glossary — a definition,
  no Russian, no rection, no muuttüüp — and `remember()` returns early for a
  row it considers complete, so the import would have filled the 6 000
  commonest words and denied every one of them a Russian translation for ever.
  That needed `_is_seed` to become `_is_baseline` and PSV to be listed in it.
  Separate tables mean an import writes nothing `remember()` looks at, and
  `BASELINES` went back to `("seed",)`. The fix that removes the trap beats the
  fix that survives it.
- **It filled a field that was hardcoded empty.** `/api/enrich` has always
  returned `"examples": []`, and `definition` was returned and never drawn. The
  card showed a muuttüüp number to someone who did not yet know the word. Both
  are rendered now.

The ~6 000 pronunciation recordings on the same page (`soundpack_alg.tgz`, MP3;
`soundpack.zip`, WAV) are **not** taken. They are about a gigabyte, the app
synthesises speech for any text already, and an audio store with no player is a
measurement with no writer.

## Review pass, 2026-09-11: what the five fixes broke

A code review of the two commits above found seven things. **Three were
regressions introduced by the fixes themselves**, and two of those defeated the
exact goal the fix was written for. Worth recording as its own section rather
than folding into the story above, because the pattern is the lesson.

### The HARNO fix made the forms invisible a second way

`exam_material` was taught to return `vorm` under its own key, which took the
forms **out of `muu`** — and `muu` is the one bucket the exam screen renders
for kinds it does not know by name. `exam.js`'s `groups` list had no `vorm`
entry, so the query got wider and the forms went from invisible in one way to
invisible in another. The whole point of the change was to make nine
application forms reachable; it made them unreachable by a different route.

A key returned by the API and read by nothing is the same defect as an item in
no section — which is the defect the change was fixing. Fixed: `exam.js` has an
`Avaldused` group, and `tests/test_sections.py` now checks every key
`exam_material` pops against the groups the page renders.

### The same fix put national pass rates on the readiness screen

Matching level-less material at every level is what lets the forms appear at
all. It also un-hid the eleven `statistika` PDFs, because `harno.NOT_INDEXED`
stops a **future** harvest writing them and does nothing about rows already in
a learner's `content.db` from an earlier one. Those rows are level-less, no
group claims them, and `muu` renders whatever no group claimed.

So anybody who had harvested before today would have got national pass rates
next to a verdict whose entire job is to say *"this is not a prediction"* —
the precise outcome `NOT_INDEXED` was added to prevent. A rule about what gets
written is not a rule about what gets read. `NOT_INDEXED` is now applied in the
query too.

### `KINDS` was defined twice in one module

The derived `KINDS` was added twelve lines below a hand-written `KINDS` that
had been there all along, and shadowed it. Two definitions of one name, the
second winning silently — which is the hand-maintained copy the new comment
says must not exist, written directly underneath the comment saying so. The
hand-written one is gone.

### Four smaller ones, all fixed

| | Was | Now |
|---|---|---|
| `wordlist.EKI_POS` | an EKI code the table does not know became `pos = NULL`, and `nouns_at_level` reads `COALESCE(pos,'s')` — so an unmapped code would have been treated as a **noun** and had a paradigm synthesised for it | unknown codes become `muu`, which is not in `DECLINABLE`. The twelve codes in the 2018 file are all mapped; this is for the thirteenth |
| `TartuNLPGrammar.check` | the new fallback spent `self.timeout` **again**, doubling the worst case on the chain's first and documented-dead provider from 5 s to 10 s | both attempts share one budget, with a test that fails if the worst case grows |
| `apply_official_levels` | a re-import from a corrected file left `level_source = 'eki'` on words EKI no longer claims — an attribution to an authority that had withdrawn it, on a function documented as idempotent | the stale attribution is cleared and counted. Only the attribution: the level underneath is not recoverable here, and `cli build` is the path that restores it |
| `library._filters` | `browse`/`count` still apply `i.level = ?`, so a section browsed *with* a level hides the same level-less forms `exam_material` now shows at every level | **not changed** — no caller passes a level to a section browse today. Written down rather than fixed, because changing the shared filter to satisfy a path nothing exercises risks the paths that are |

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
