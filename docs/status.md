# Status

What the app does today, what it does not, and the known issues. Counts marked
as checked are asserted by `tests/test_docs_match_code.py`; update this file in
the same change that makes it untrue.

## What works

| Area | State |
|---|---|
| **Drills** | 26 of 36 curriculum topics generate items: object case, verb forms, conjugation, locative cases, comparison, numerals, question words, word order, punctuation, rection. |
| **Grading** | Drills: code. Free writing: model chain plus deterministic checks. Meaning and conversation scoring by a model: authorised, not built. |
| **Plan** | Rada's Täna: today's blocks in a time budget (reviews, the weakest rule with its last mistake, refresh, the least-practised exam part, the next topic, a text), each with its reason in Russian (`eesti/planning.py`). |
| **Path** | Prerequisite-ordered topics, mastery gate, end-of-level checkpoints (web and CLI), blocked → interleaved handoff. Test-out runs from `Kogu rada` or the CLI (five of five, graded server-side); the placement sweep is CLI-only (`cli assess`). |
| **Review** | FSRS-6 over items answered wrong, cards seeded on mastery, and words mined from reading. Grammar cards are answered and rated by code (again / hard when slow / good); vocabulary cards are self-rated. A correct drill answer on a due card counts as its review. |
| **Reading** | Selges keeles texts and the weekly ERR *Lihtsad uudised* feed; click-to-look-up; recommended by the share of running words within reach (known, or A1–A2 on the word list), at least 80 %, shorter first (`docs/curriculum.md`). |
| **Vocabulary** | `Sõnavara` lists the word list by CEFR level and part of speech, commonest first; the word card sets a status. |
| **Meaning** | **294 Russian glosses ship with the app** (`data/seed_glossary.tsv`). Russian order: seed → live dictionary → EKI EVS → EKI HAR (`eesti/meaning.py`). Definitions: EKI PSV → live → VSL → EKSS. |
| **Live dictionary** | EKI's Ekilex API when `EKILEX_API_KEY` is set, otherwise the Sõnaveeb mirror; answers stored once per word. |
| **Rules** | 25 of 26 drillable topics link to the handbook. `kusisonad` has none, deliberately: no EKK section covers question words. |
| **Question-word cues** | A `kusisonad` item shows the Russian for the question word its blank wants, from EKI EVS (`docs/curriculum.md`): 8 of 12 answer words. |
| **Conversation** | `Vestlus` in Rääkimine: a model plays the paired-exam partner over a task card, in Estonian, for at most 8 turns. It never corrects and never scores; forms Vabamorf does not know are named. Only that a conversation happened is recorded. |
| **Tutor** | `Selgita` on a missed item: one model call grounded in the attempt, Vabamorf's reading and the EKK section; the answer is dropped if it quotes a form Vabamorf does not know, and never decides anything (`eesti/tutor.py`). |
| **Writing** | Grammar check through the provider chain (`docs/ai-providers.md`), plus deterministic spelling, subject–verb agreement and rection checks; back-translation; corrections queue for the Notion `Vead` log. |
| **Listening** | Dictation from the corpus (graded), TartuNLP TTS on any text, ERR episode audio. |
| **Speaking** | Paired-exam question bank with TTS, read-aloud with comparison, open-answer feedback over the transcript, and `Vestlus` (a model plays the partner). Each answer is recorded with what code can measure — answered or not, words, pace, and the share of words Vabamorf does not know, which flags a transcript the recogniser struggled with. Readiness reports that practice and still refuses to judge the part. |
| **Exam** | HARNO's own shape as data (`eesti/exam.py`, checked 2026-09-19): A2 4×20, B1 4×25, pass at 60 % with no part at zero, and the published sittings. The learner picks a sitting in `Eksam`; it is learner state (a `goal-set` event), drives the countdown and exports as `.ics`. |
| **Mock** | `Proovieksam`: one exam part on the exam's own clock, or all four in the exam's order (`eesti/mock.py`). Reading is gap-fill in corpus sentences, listening is dictation, writing is HARNO's task shape graded on length plus the deterministic checks (spelling, agreement, rection), speaking is the question bank and is never scored. Each section says what it really is, and counts as evidence for its part. |
| **Readiness** | Four exam parts reported separately with reasons in Russian; a section sat on the clock counts as contact for its part. |
| **Offline** | Installable PWA; opens without a connection and says what it cannot do. The API is never cached. |
| **Evidence** | Every learner-state change is an event in an append-only log (`eesti/evidence.py`); the learner databases are rebuilt from it. Attempts carry the item, its signed ref (regenerable) and the answer time; reviews carry the FSRS rating and who chose it. `Minu andmed` downloads the log. |
| **Operations** | One JSON line per API call on stdout (`eesti/logs.py`), carrying route, status and duration and never what was written or said. Each provider lane has a daily allowance (`providers/budget.py`), reported by `/api/engines`. |
| **Deployment** | Cloud Run behind a Cloudflare Worker + Access; the evidence log is copied into the Worker's Durable Object after every request and pushed back into each new instance; all EKI reference data and the reading corpus present. |

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

- **`cli link-topics` is a manual step.** It fills `topic_items`, the join that
  puts reading texts beside a drill. Nothing on the deploy path runs it: after
  a re-harvest, run it before `deploy/push-content.sh`. `/api/health` reports
  `corpus.topic_links`; the harvest commands print the reminder, and
  `cli push-content` and smoke warn when it is zero.
- **Grammar providers are free tiers with limits.** TartuNLP GEC answers
  first (its explanations are Estonian, not Russian), then the LLM lanes:
  Workers AI (10 000 neurons/day); NVIDIA's GLM-5.3-Flash is accurate but takes
  20–60 s; Mistral mostly returns "no errors"; OpenRouter allows 50 requests
  a day and counts failures. When all fail the check degrades to Vabamorf
  offline evidence. See `docs/ai-providers.md`.
- **TartuNLP GEC, first in the grammar chain, does not answer.** Its front
  end is up, but the model behind it (on the University of Tartu cluster)
  answers `/grammar/` with a 500 after 60 s, so `cli eval --provider tartunlp`
  scores none of the 18 cases. The breaker skips it after two failures; the
  lane stays for when the backend returns. Neurotõlge est→est
  (`tartunlp-mt`) covers form errors without explanations meanwhile.
- **The weekly eval schedule scores only OpenRouter.** Other lanes are checked
  by manual dispatch of `eval.yml`.
- **Browser journeys are not in CI.** They protect a release only when run
  locally (`docs/testing.md`).
- **4 of 12 question words have no Russian cue.** `kelle`, `kellele`,
  `kellega` are forms of `kes` and `kui palju` is two words, so EVS has no
  headword for them. EKI's Russian–Estonian dictionary (VES, same licence
  page) might attest them from the Russian side (`с кем` → `kellega`); it is
  not downloaded or checked.
- **Nothing measures ASR quality** — there is no Estonian speech benchmark wired
  up.
