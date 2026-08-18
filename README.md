# Eesti-Keelt

A personal tool for learning Estonian and preparing for the **A2/B1 tasemeeksam**.
Single user. Runs locally for development; deploys to Cloudflare so it is
reachable from anywhere, on desktop and phone.

Built around one documented weakness: choosing **partitive (osastav)** where a
completed, whole object needs **genitive (omastav)** — the only tag past the "3+
occurrences" threshold in my error log.

## Dependency-free core

Not "offline" in the sense of your connection — in the sense of *theirs*. While
researching this, four separate research-hosted endpoints (TartuNLP's grammar API
`/v1` and `/v2`, ELLE's CEFR predictor and corrector) were all returning HTTP 500
while every dataset and static asset worked fine. That is the normal state of
grant-funded infrastructure, not an outage.

So vocabulary, morphology, drill generation and grading depend on **no third-party
service at all**. They read from data this project owns. Online services are
optional enrichment behind a provider chain with short timeouts and a circuit
breaker, and the UI always shows which engine answered.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m eesti.cli fetch-data   # ~2.8 MB word list, one time
.venv/bin/python -m eesti.cli build        # import + index (a few seconds)
.venv/bin/python -m eesti.cli serve        # http://127.0.0.1:8000
```

Terminal use, if you prefer:

```bash
.venv/bin/python -m eesti.cli placement         # find where to start, once
.venv/bin/python -m eesti.cli practice          # graded session, picks up where you left off
.venv/bin/python -m eesti.cli practice --topic lihtminevik --theme reisimine
.venv/bin/python -m eesti.cli review            # interleaved review of whatever is due
.venv/bin/python -m eesti.cli progress --todo   # what is left, in study order
.venv/bin/python -m eesti.cli check "Ma lugesin eile raamatut läbi."
```

For the free-text writing check (corrections explained in Russian), one API key
is needed — everything else works without it.

**The key belongs where the code that uses it runs.** For CI and the model eval
that is a **GitHub repository secret** (`OPENROUTER_API_KEY`); for the deployed
app it will be a Cloudflare Worker secret; only if you clone this locally does a
git-ignored `.env` apply. See [`docs/setup.md`](docs/setup.md) — it also says
where *not* to put it.

## What it does

**Kirjutamine** — paste Estonian, get corrections. Object-case errors are sorted
first and highlighted separately; explanations are in Russian but keep the Estonian
grammar terms (`osastav`, `omastav`) so the exam vocabulary sticks.

**Harjutused** — generated object-case drills, filterable by rule and CEFR level:

| Rule | Case | Example |
|---|---|---|
| `negation` | partitive, no exceptions | *Ma ei ostnud **piletit**.* |
| `completed` | genitive | *Ma leidsin **rahakoti** üles.* |
| `ongoing` | partitive | *Ta luges **aruannet** tund aega.* |
| `verb-form` | irregular stem | *Ma **lähen** kooli* — not *minen* |

Grading is deterministic — no model involved, so it is right every time and free.

Beyond the templates, drills are also generated **from real Estonian**: the 349
harvested texts give 2 073 usable sentences, and blanking one word in a sentence
a native wrote removes both the semantic pool to maintain and any doubt about
whether the answer is right.

```bash
.venv/bin/python -m eesti.cli cloze -n 5 --topics kohakaanded --answers
```

The catch is that an authentic sentence does not always *have* one right answer.
Blank the object in *"Ta luges raamatut"* and ask genitive-or-partitive and you
are asserting the genitive is wrong — which depends on telicity, and Estonian
often licenses both. So an item ships only where the form is forced: either the
prompt **names the case** (*"Ma elan ____ (Tallinn, seesütlev)"* — morphology
decides, and nothing is claimed about which case the sentence needed), or a
**trigger makes it obligatory**, which for the object is negation and nothing
else. 1 138 case items and 28 negation items, covering five curriculum topics.

The verb drills exploit a useful property: **the form a learner builds by naive
rule is the mistake they actually make.** Estonian cites verbs as `minema`, and
stripping `-ma` for "I go" gives `minen`; the real form is `lähen`. So the naive
form is not an invented distractor — it is the error, and it appears verbatim in
my own log. Only the 507 forms (across 129 A1–B1 verbs) where naive and actual
differ are drilled.

**Lugemine** — 349 simplified Estonian texts (~23 000 words, 100 % Estonian),
sorted into three difficulty bands. Click any word for its lemma, case and CEFR
level; words above your level are highlighted, and each text shows what share of
its vocabulary you already know — which is the number that decides whether a text
is worth your time.

**Kuulamine** — any text becomes Estonian audio via TartuNLP TTS (12 voices),
default 0.7× for learners. Cached on disk, so replay is instant and offline.
Plus 28 ERR radio episodes with audio.

## What the reading material actually is

Measured, not assumed. The ERR Raadio 4 archives were planned as reading
material; they turned out to be **12 % Estonian** — 3 214 Estonian words against
23 147 Russian. They are Russian-language *grammar lessons* with Estonian
examples, so they are filed as `grammatika`, not `lugemine`, and their 333
teacher-curated Estonian example sentences are extracted for drill use.

Actual reading practice comes from **Selges keeles** — 349 simplified Estonian
news posts, 100 % Estonian, fetched through WordPress.com's public API.

Difficulty is **relative, not CEFR**. An earlier version estimated an absolute
level from vocabulary coverage and rated 342 of 349 deliberately-simplified texts
as B2. The cause is structural: only 9 951 of 160 316 lemmas (6.2 %) carry a CEFR
tag, so coverage systematically undercounts — measured 0.25–0.87, median 0.53.
The bands rank texts against each other instead, which is all that is needed to
start with the easier ones.

## How the forms are trusted

Two sources, and the split matters:

- **CEFR levels + frequency** come from
  [Estonian-Wordlist-Enriched-Ekilex](https://github.com/KristjanPikhof/Estonian-Wordlist-Enriched-Ekilex)
  (CC-BY-SA-4.0, derived from Ekilex/EKI). Using it means **never scraping
  Sõnaveeb**, whose maintainers explicitly ask people not to batch-request it.
- **Inflected forms** come from **Vabamorf synthesis**, not from that dataset's
  79 MB forms file. That file's per-word lists are de-duplicated, so identical
  forms collapse and position can no longer be mapped to a case (`auto` has 13
  singular entries, not 14). Vabamorf returns *labelled* cases, round-trip
  validated: each candidate is re-analysed and kept only if it reads back as the
  requested lemma in the requested case.

Only nouns whose genitive and partitive genuinely **differ** are drilled. That is
the clear majority — **1,741 of 2,533 indexed A1–B1 nouns (69 %)**. The remaining
31 % where the two coincide (`kino`→kino/kino, `kets`→ketsi/ketsi) are excluded
because there is no wrong answer to give, so such an item would measure nothing.

## Is the foundation actually correct?

Every drill answer, every case label and the whole exported dataset inherit
Vabamorf's correctness, so that inheritance is checked against data this project
did not write — `TalTechNLP/inflection_et` from the **Estonian Native LLM
Benchmark** (LREC 2026), 1 400 noun phrases built from native Estonian sources
with their correct form per case.

```bash
.venv/bin/python -m eesti.cli fetch-bench
.venv/bin/python -m eesti.cli validate
```

**98.1 % agreement overall, 98 % on both genitive and partitive** — the two cases
the entire app rests on. The disagreements are a narrow, real class: invariant
adjectives. In `täis pudel` ("a full bottle") the modifier does not decline, so
the gold form is `täis pudeli` while Vabamorf offers `täie pudeli`.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q     # 260 passed
```

Four gates:

1. **Planted errors are caught** — the obj-case regression set.
2. **Correct sentences are left alone.** A checker that flagged every partitive
   would pass gate 1 while teaching exactly the wrong rule, so sentences with no
   object at all must produce no candidates.
3. **Owner-only material cannot leak.** A public query must never return an item
   from a source that is not redistributable.
4. **The syllabus graph stays sound.** No topic may be scheduled before a topic
   it depends on, and every declared topic must appear in the derived path
   exactly once — a dropped edge silently removes topics from the course.

## Deliberately not built

- **Pronunciation scoring** — forced alignment yields timings, not correctness,
  and EKI already publishes free
  [pronunciation exercises](https://sonaveeb.ee/pronunciation-exercises/).
- **A dictionary / flashcard app** — Sõnaveeb, Sõnastik and Anki do it better.
- **A notes system** — Notion stays the system of record.

## Licensing is a column, not a convention

The app draws on sources with very different terms, so `licence` and
`redistributable` are columns in the `sources` table rather than a note in a
README. Once the app is on a public URL, "may this be served to an anonymous
visitor?" is a question every item must be able to answer.

| Source | May be served publicly |
|---|---|
| Enriched Ekilex wordlist (CC-BY-SA-4.0) | yes |
| Generated drills, TartuNLP TTS, sonapi | yes |
| **HARNO exam material** | **owner only** |
| **EIS public tasks, ERR transcripts** | **owner only** |

**Yes, HARNO material can be used** — downloading the official sample tasks and
listening MP3s to study from is ordinary personal use, and it is the best exam
material that exists. Serving it from a public URL is redistribution of a state
agency's copyrighted work. The same file is fine in one place and not the other,
which is why access control is data-driven and why **Cloudflare Access is not
optional** — it is what keeps the private half private. `data/exam/` stays
git-ignored; fetch it yourself.

## Docs

**Start here:** [`docs/curriculum-plan.md`](docs/curriculum-plan.md) — the
A1→B1 grammar syllabus, what the research says about practice schedules, and the
sequenced plan for covering it.

Also: [`docs/app-structure.md`](docs/app-structure.md) — path vs library, and
how progress is measured · [`docs/roadmap.md`](docs/roadmap.md) — what is built, what is
next, and what the 2026 competitors do that is worth copying.

- [`docs/setup.md`](docs/setup.md) — which API key, how to get it, where it goes
- [`docs/content-sources.md`](docs/content-sources.md) — where grammar and
  vocabulary come from, and why neither is stored per-word
- [`docs/architecture.md`](docs/architecture.md) — how this deploys to Cloudflare
  when Vabamorf cannot run there, plus stack and practice decisions
- [`docs/source-audit.md`](docs/source-audit.md) — every source and technique
  from research, against what is actually built
- [`docs/source-gaps.md`](docs/source-gaps.md) — what was discovered but never
  wired up, including the learner corpus and the Estonian-adapted LLM
- [`docs/grammar-scope.md`](docs/grammar-scope.md) — what is drillable beyond
  nouns, and where Estonian grammar data actually comes from
- [`docs/ai-strategy.md`](docs/ai-strategy.md) — which jobs justify an LLM,
  model options, and the eval results

## Roadmap

Phase 2 (reading + listening) and phase 3 (speaking) are scoped but not built:
harvesting the ~170 ERR Raadio 4 episodes that pair transcripts with audio, the
weekly *Lihtsad uudised* feed, and a question bank shaped like the real — and
notably **paired** — B1 speaking exam.
