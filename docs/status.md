# Where version 1.0 stands

Written 2026-08-20 at the close of the first build, and revised the same day
after the deployment was actually asked how it was doing. This is the honest
inventory: what works, what was never built, what is knowingly broken, and what
the original research plan promised and did not deliver.

Read `roadmap.md` for *why* things were chosen and `lessons.md` for the habits
that came out of getting them wrong.

## The decision this version closes on

**No exam in 2026.** The optional A2 rehearsal (register by 01.10.2026, sit
07.11.2026) was considered and declined on 2026-08-20. The plan is independent
study plus a tutor through the winter, and a sitting in 2027 — either A2 and
then B1, or B1 alone, whenever the evidence supports it.

The app reflects that: `readiness.TARGET` is `None`, the countdown reads
*"экзамен ещё не выбран"*, and `EXAMPLE_TARGET` keeps the calendar shape so
setting a 2027 date is one line. Both levels stay first-class, because *which*
of those two routes to take is precisely what the readiness verdict is for.

## What works

| | |
|---|---|
| **Drills** | 26 of 36 curriculum topics generate items — **24 on a checkout with no harvested corpus**, measured 2026-08-21 by asking `/api/practice` for every topic in `/api/curriculum` rather than by counting generators. Object case, verb forms, conjugation, locative cases, comparison, numerals, question words, word order, punctuation, rection. |
| **Grading** | Deterministic everywhere. No model decides whether an answer is right. |
| **Reading** | 349 Selges keeles texts, click-to-look-up, known-word tracking, comprehensibility ordering. |
| **Listening** | Dictation from the corpus, TTS on any text at 0.7×, ERR episode audio. |
| **Writing** | Grammar check through the provider chain, corrections queued for the Notion error log with an explicit send step. |
| **Speaking** | Question bank in the exam's paired shape, TTS voicing the other side, links out to EKI's own pronunciation exercises. |
| **Review** | FSRS-6 over items you actually got wrong, plus words mined from reading. Intervals expand as they should — measured 2026-08-21 at the due date: 10 min → 2 d → 11 d → 47 d → 171 d → 514 d. |
| **Vocabulary** | `Sõnavara` lists the wordlist by CEFR level, part of speech and what you have marked, commonest first. Same word card as the reader, so a word chosen here and a word met while reading are one thing. |
| **Meaning** | **294 Russian glosses ship with the app** (`data/seed_glossary.tsv`), covering 81 % of the words drills actually use — measured 0 % before. Written for this project, never scraped. Sõnaveeb enriches on demand with senses, rection and muuttüüp; the seed is a baseline, not a ceiling. Sentence-level translation from TartuNLP, on request only. |
| **Rules** | **25 of 26 drillable topics link to the handbook** (was 5). Every section number read off the EKK rather than inferred — a summarising fetch of the same page returned numbers shifted by one. `kusisonad` has none: no section covering question words was found, and a wrong link is worse than none. |
| **Back-translation** | The writing check reads your Estonian back in Russian, so a sentence that is well formed but says the wrong thing is visible. |
| **Verdict** | Four exam parts reported separately, never as one total, with the reasons named in Russian. |
| **Offline** | Installable, and an installed copy now opens without a connection and says why it can do no more. The API is never cached — every endpoint is either the learner's own state or freshly generated, and a drill quietly a day old is worse than one unavailable. |
| **Deployment** | Cloudflare Worker + Access in front of Cloud Run, both free tiers, state snapshotted across cold starts. |

52 route handlers across `eesti/api/`, serving **44 API endpoints** — every one with a caller, and `test_route_inventory.py` fails on one nothing can reach. The two numbers differ because `/api/review` answers both GET and POST, and because eight of the handlers serve the page itself (`/`, `/app.css`, the modules, the worker) rather than the API. Roughly 1 900 in-process tests, plus 72 browser journeys run once per engine (Chromium and WebKit, so 144 when both are installed).

The route count is checked against the code (`test_docs_match_code.py`), and so are the three numbers in the table above that can be: topics with a generator, topics that link to the handbook, and shipped glosses. The test count is deliberately **not** one of them and is deliberately vague: it changes on almost every commit, nothing can derive it from prose, and a number asserted here would make adding a test a two-file edit. Precision nobody can maintain is worse than a round figure that says the right thing.

## What a learner still cannot do

Measured 2026-08-22 against the code, not inferred from the last time this
section was written.

**This section listed three things on 2026-08-21 and all three were built
within the day** — the vocabulary browser, the empty-topic message, and the
service worker. It stayed as written for a further sprint, which means the one
section a fresh session reads to decide what to build was describing an app
three days out of date. Rebuilding `Sõnavara` from it would have been a
reasonable thing to do and a complete waste. Check this section against the
code before trusting it; better, delete an entry the moment it ships.

### The reading library is not joined to the practice

`library.related()` selects the texts that demonstrate a grammar topic, and
`/api/practice` returns them alongside the drill — "the join that makes
practice and the reading library one tool", as the comment there says. It
reads `topic_items`, and that table is **empty**: `cli link-topics` fills it
and has not been run since the corpus was last rebuilt. The reader returns
`[]`, the practice response carries an empty `reading` list, and nothing
anywhere says so.

**On the deployment it is not empty:** smoke run 34765657703 (2026-09-13) read
609 corpus items and 660 topic links, so `link-topics` was run on the copy that
was last pushed. What is still true is that nothing on the deploy path runs it —
it is a manual step between harvesting and `push-content.sh`, written out in
`docs/deploy.md`, and a re-harvest pushed without it empties the join again.
A local checkout with a fresh `content.db` starts empty.

No longer unknown on the deployment, as of 2026-09-11. `/api/health` reports
`corpus` as two row counts — `items` and `topic_links` — and the smoke check
warns when there are texts and no links, naming `cli link-topics`. The gap this
paragraph described (the check verified `/api/library` *answers* and counted
nothing) was the "presence of a database is not presence of data" mistake in a
new place, and it is closed. **The table can still be empty; what changed is
that asking now gets an answer.**

### EKI's dictionaries: committed, imported, not yet measured in production

Closed in code on 2026-09-13; open until a smoke run reads the counts.

Until then production had none of EKI's data (`eki_levels` 0, `eki_definitions`
0, smoke run 34765657703), because Cloud Build builds from git and the files
were git-ignored. They are now committed in `deploy/eki/` and the image imports
them. Measured locally on the real files the same day:

| `/api/health` `reference` | Local, from the committed files |
|---|---|
| `eki_levels` | 4 340 (4 102 words carry `level_source = 'eki'`) |
| `eki_definitions` | 4 849 |
| `eki_russian` | 60 610 |
| `eki_loanwords` | 30 095 |
| `eki_terms` | 5 873 |

The first real run found what the fixtures could not: the XML has no root
element and undeclared prefixes, so `psv.parse` failed on byte one. PSV also
has 58 lemmas with two articles, and an upsert in file order kept the rarer
meaning. Both are fixed and tested against the real shape.

Which answer a word card shows, each from its own table:
**definition** PSV → Sõnaveeb → VSL (→ EKSS, if imported); **Russian** EVS →
Sõnaveeb → HAR. EKSS (119 426 definitions) is optional and not in the image.

### Only one grammar provider is actually configured

The chain is built for redundancy and has had none: the deep smoke check on
2026-08-22 read `llm:openrouter: HTTPError 429` with every other lane
`unavailable` — no key. So the writing check falls to `vabamorf-offline`
whenever the one free tier is spent, which for a 50/day allowance is a normal
Tuesday rather than an incident.

**The `huggingface` lane does not answer.** `HF_TOKEN` is set in Actions, and
the eval was finally run with it: `eval.yml`, `provider=huggingface`, provider
default model, run 34765659556 on 2026-09-13. **Not a score — could not
measure.** 18 of 18 cases came back `HTTPError 400 (model_not_supported)`, and
the run finished green, which is exactly the green `eval.yml` warns about.

What that does settle: the token is accepted (a bad one is a 401 before
routing), and the router refuses the pinned
`tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125`. The 2026-09-01 metadata probe
that brought this lane back (`featherless-ai`, `live`) described a mapping, not
a completed request, and a request is what failed. The catalogue step of the
same run listed 140 routable models and marked the pin "not answerable here".
**Why, measured the same day:** the bare id asks for the default `:fastest`
policy, and that route does not offer this model. Naming the provider
explicitly — `…-1125:featherless-ai`, the router's documented suffix — does
route it, and the answer is money: run 34772172942 returned `403` for the first
ten cases and `402 Payment Required` for the rest. The model is live; it is not
served on this account's free allowance.

**Decided: not paid for, and nothing changed in code.** Both halves of the
deployment run on free tiers, and a model is only ever allowed to *explain* a
correction here, never to decide one — so EstLLM would improve the prose, not
the grading, which is not worth a subscription on its own. The lane stays
defined because it costs nothing while failing: the breaker in
`providers/breaker.py` skips a lane after two failures for 15 minutes, doubling up to six
days. If an HF plan with inference credits is ever bought, the check is
`cli eval --provider huggingface --model tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125:featherless-ai`.
It is deliberately not in `eval.yml`'s menu: `test_every_selectable_model_is_free`
keeps paid ids out, and it caught this one being added for the measurement.

The weekly `schedule` of `eval.yml` always scores `openrouter`, so nothing
re-checks this lane on its own; a re-run is a manual dispatch.

## What was never built

### 10 curriculum topics have no generator

```
tahestik  lauseehitus  asesonad  astmevaheldus  kaassonad  sidesonad
maarsonad  tulevik  uhendverbid  liitsonad
```

It was 13 that morning: `pohivormid`, `eitus` and `uhildumine` were built on 2026-08-21. **Do not
maintain this list by hand** — it is `[t.id for t in TOPICS if not t.generator]`,
and the version above is a snapshot for reading, not the source. A test that
kept its own copy of the same set went stale the moment those two landed.

They appear in the syllabus and in the path, and practising them opens a
message saying so rather than nothing. Some are deliberate — `astmevaheldus` is
reference material whose contrast is already drilled through `gen-stem`, where
the stem is actually chosen. Most are simply not done. `uhildumine`,
`uhendverbid` and `liitsonad` were investigated as candidates for the
attested-corrections treatment that made `word-order` work, and the corpus did
not have enough marked examples.

### Pronouns will not be generated from Vabamorf

`asesonad` is A1, closed-class and looks like the easiest remaining topic —
thirty-five words, decline them, done. Measured, and refused:

```
mina  → genitive "mina"    (correct: minu)
keegi → genitive "kee"     (correct: kellegi)
iga   → genitive "ea"      (that is `iga` meaning *age*, a different word)
```

The short forms `ma`, `sa`, `ta`, `me`, `te` synthesise to nothing at all.
Estonian pronouns are suppletive and Vabamorf's paradigms for them are not
usable as an answer key, so a generated pronoun drill would be confidently
wrong several times a page — the `kool, koola, koola` failure again, in a
place where every item is a word the learner uses constantly.

If it is built, it needs a hand-written table of about thirty words, which is
the same shape as `data/seed_glossary.tsv` and now a proven pattern. It is not
a generation problem.

**And it needs a cited source, which this repository does not have.** Nothing
in `eesti/`, `docs/` or `data/` gives a pronoun paradigm. TalTech's native gold
forms were the obvious candidate, and they have none. Measured 2026-09-13 on
`inflection_et` as `cli fetch-bench` downloads it: 1 400 rows, all adjective +
noun phrases, and **0** contain a personal, demonstrative, interrogative or
indefinite pronoun. So the table cannot be checked against that source, and
until one is cited the topic stays without a generator.

### Local ASR

The plan called for `faster-whisper` with TalTech's verbatim fine-tune, run
locally so a voice never leaves the machine. What shipped is Cloudflare Workers
AI. That is a real deviation and the privacy note on the speaking screen says
so plainly rather than pretending otherwise. The local route still has the
better privacy story and nobody hosts the model.

### Pronunciation scoring

Deliberately never attempted — forced alignment gives timings, not correctness,
and EKI publishes free exercises. The app links them instead.

### The documentation described a structure that was never built

`docs/app-structure.md` had a top-level `Raamatukogu`, put `Kordamine` inside
`Õppimine`, and listed no `Rääkimine`, `Kirjutamine` or free-practice tab. None
of that matched the app. It was a plan being read as a map, and it had been
that way long enough that its "Built" section asserted `pohivormid` could not
gate — true when written, false since the generator landed.

Rewritten 2026-08-21 from `index.html` and `library.py` rather than from
intent, and it now carries the three things this project keeps needing and not
having written down: **which screens are graded by code and which by a model**
(only two involve a model, and neither decides correctness), **where the modules
overlap**, and **why `Sõnavara` sits where it does**.

Worth knowing for its own sake: `Sõnavara` was *already specified* in that
document — "vocabulary by frequency band, Speakly-style" — before it was built.
It was built frequency-ordered by independent reasoning, which converged, but
the specification was sitting there unread.

### Three of the five word statuses had no writer

`vocab` models five: `õpin`, `tuttav`, `tean`, `eiran`, `teadsin ammu`. Two
were reachable — `õpin` set automatically on the first encounter while reading,
`tean` by the word card's button. The other three were modelled, stored and
counted by the overview, and there was nowhere a learner could click to set
them. Same shape as a measurement with no writer and an endpoint with no
caller, which this project has now met three times in three different costumes.

Fixed for `eiran` and `teadsin ammu` on 2026-08-21: the word card carries
**Pole vaja**, and `POST /api/vocab/known` takes an explicit `status`. `eiran`
is the one a vocabulary list needs and a reader does not — browsing B1 nouns
turns up `riigivisiit` and `seinamaaling`, real words that this learner is not
going to spend a morning on, and without a way to say so they return on every
page and the "still to learn" count never means anything.

`tuttav` is still unreachable, deliberately. It sits between met and known,
which is exactly the granularity LingQ's four levels are reported as being too
fine to judge; the boundary that carries weight here is *settled*, and `tuttav`
is on the same side of it as `õpin`. It stays in the model because removing a
stored value is a migration, and earns its place only if something ever needs
to distinguish "seen twice" from "seen once".

## How this got here

Everything above is what is true **now**. What happened to make it true — every
retrospective, every bug and what it cost, every dated re-probe of a third
party — is in **`changelog.md`**, newest first.

They were one file of 1 377 lines until 2026-09-12, and the log was nine tenths
of it. That is the wrong shape for the document a session reads to decide what
to build: the inventory is the part that must be re-checked against the code,
and it was buried under a thousand lines that are true forever by construction.

The split is not only tidying. `test_docs_match_code.py` scans the live
documents for claims and needs a `HISTORICAL` regex to skip sentences that
record a past state — a guess it makes from wording. With the log in its own
file that distinction is structural, and the guess has less to do.

