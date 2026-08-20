# Where version 1.0 stands

Written 2026-08-20 at the close of the first build, and revised the same day
after the deployment was actually asked how it was doing. This is the honest
inventory: what works, what was never built, what is knowingly broken, and what
the original research plan promised and did not deliver.

Read `roadmap.md` for *why* things were chosen and `CLAUDE.md` for the habits
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
| **Drills** | 23 of 36 curriculum topics generate items. Object case, verb forms, conjugation, locative cases, comparison, numerals, question words, word order, punctuation, rection. |
| **Grading** | Deterministic everywhere. No model decides whether an answer is right. |
| **Reading** | 349 Selges keeles texts, click-to-look-up, known-word tracking, comprehensibility ordering. |
| **Listening** | Dictation from the corpus, TTS on any text at 0.7×, ERR episode audio. |
| **Writing** | Grammar check through the provider chain, corrections queued for the Notion error log with an explicit send step. |
| **Speaking** | Question bank in the exam's paired shape, TTS voicing the other side, links out to EKI's own pronunciation exercises. |
| **Review** | FSRS-6 over items you actually got wrong, plus words mined from reading. |
| **Meaning** | Russian glosses from Sõnaveeb, stored per word, shown on drills, review cards and the word card. Sentence-level translation from TartuNLP, on request only. |
| **Back-translation** | The writing check reads your Estonian back in Russian, so a sentence that is well formed but says the wrong thing is visible. |
| **Verdict** | Four exam parts reported separately, never as one total, with the reasons named in Russian. |
| **Deployment** | Cloudflare Worker + Access in front of Cloud Run, both free tiers, state snapshotted across cold starts. |

42 API routes, every one with a caller. 1 141 tests.

## What was never built

### 13 curriculum topics have no generator

`tahestik`, `lauseehitus`, `asesonad`, `pohivormid`, `astmevaheldus`, `eitus`,
`kaassonad`, `sidesonad`, `maarsonad`, `tulevik`, `uhildumine`, `uhendverbid`,
`liitsonad`.

They appear in the syllabus and in the path, and practising them opens nothing.
Some are deliberate — `astmevaheldus` is reference material whose contrast is
already drilled through `gen-stem`, where the stem is actually chosen. Most are
simply not done. `uhildumine`, `uhendverbid` and `liitsonad` were investigated
as candidates for the attested-corrections treatment that made `word-order`
work, and the corpus did not have enough marked examples.

### Local ASR

The plan called for `faster-whisper` with TalTech's verbatim fine-tune, run
locally so a voice never leaves the machine. What shipped is Cloudflare Workers
AI. That is a real deviation and the privacy note on the speaking screen says
so plainly rather than pretending otherwise. The local route still has the
better privacy story and nobody hosts the model.

### Pronunciation scoring

Deliberately never attempted — forced alignment gives timings, not correctness,
and EKI publishes free exercises. The app links them instead.

## Known bugs and rough edges

Nothing here is severe enough to block use. All of it is real.

| | |
|---|---|
| ~~**`_bind_breaker()` runs at import**~~ | **Fixed 2026-08-20.** `breaker.bind_later(progress_db)` registers an opener instead of a connection, and the breaker opens it the first time it has something to remember. Importing `eesti.app` now opens no database at all, which is asserted. The conftest workaround that dropped the binding is no longer load-bearing. |
| ~~**`wordlist.connect` invents an empty database**~~ | **Fixed 2026-08-20**, exactly as this entry proposed: `wordlist.available()` opens read-only and counts a row, and `cli.words_db()` is the twin of `cli.content_db()` — it declines with "run `cli fetch-data` and then `cli build`" instead of handing back a convincing empty database. `connect` still creates, because `cli build` must be able to. |
| **`sonapi`'s raw payload cache is ephemeral** — *and that is correct* | Re-examined 2026-08-20 and **downgraded from a bug**. Every path that can reach Sõnaveeb from the running app goes through `gloss.remember`, which is durable and in the snapshot; `sonapi.entry_url` builds a string and touches nothing. The only caller of the file cache is `cli rections`, which runs **in the Docker build**, where a cache that lives for one build is exactly right. Nothing re-requests anything on a cold start. Left alone deliberately rather than moved for tidiness. |
| **The local `content.db` is partial** | 349 Selges keeles items only. The ERR transcripts, news issues and exam pointers were lost to a container rollback and not re-harvested. The **deployed** database is the complete one; the last smoke run confirms `"library":true`. Re-run the harvesters before trusting local numbers about the corpus. |
| **The container rolls the checkout back** | Twice in one session, once taking a committed-but-unpushed commit, and once reverting a session that had already pushed — leaving `origin/main` pointing at `Initialise repository` while GitHub held the full history. Nothing was lost either time, but a local `git log` is **not** evidence about the repository. `git ls-remote origin` is. Recover with `git fetch origin --prune && git reset --hard origin/<branch>` — **and then rebuild the derived artefacts**. The rollback also restores a stale `data/edge.db`, which presents as two failing export-quality tests (`kool` still carrying `koola, koola`) that look exactly like a code regression and are not one: CI passes on the same commit because it builds the dataset fresh. `python -m eesti.cli export` fixes it. |
| **The grammar checker is in offline mode on the deployment** | Found 2026-08-20 by the deep smoke check, after the v1.0 image shipped. The chain reports `llm:openrouter: HTTPError` — the key *is* on the process and the call fails, which is a different problem from `unavailable`. Writing still flags object-case candidates and typos, but no correction carries an explanation, so no "log it" button renders and **nothing reaches the Notion log**. Same inert chain as the original key-on-the-Worker bug, from a different cause. PR #18 makes the note name the status code, which decides whether it is a 429 (self-healing) or a 401 (needs a new key on Cloud Run). |
| **`evkk` reaches the network** — now fails like a citizen | Still one live request, and still excluded from the suite: it fetches from `elle.tlu.ee`, and a suite that depends on a research host is a suite that goes red on somebody else's Tuesday. **Fixed 2026-08-20:** it no longer dies with a traceback when that host is down. It says what happened, names the cache path a saved copy can be dropped at, and returns 1. A parse that yields nothing is reported too, rather than writing an empty taxonomy over a good one. |

## Tech debt, stated as debt

- **The harvesters' fetch halves are untested**, by choice: a suite that
  re-crawls ERR on every run is a suite that hammers someone else's server.
  Their *parsers* are covered. The line is drawn at the network boundary and
  that is where it should stay.
- **`providers/llm.py` and `providers/asr.py` sit at 67 % and 72 %** for the
  same reason. Going further means mocking HTTP for its own sake.
- **`cli.py` is 52 %.** The uncovered half is the write and network commands —
  harvest, push-content, notion --push, eval, models, rections, serve. Every
  read-only command runs in the suite.
- **`Cloze` still overrides `hint` and `label`.** Legitimate — for rection the
  case *is* the question — but it is the last place an item class differs from
  the mixin, and worth re-checking if a fifth generator appears.
- ~~**Two `_state_paths()` writers use `write_bytes`** on paths read from module
  globals.~~ **Fixed 2026-08-20**, and it was not as harmless as this entry
  said. `app.py` kept its own copies of the four learner paths, bound at
  import, and both `_state_paths()` and the database helpers read them — so
  redirecting one name without the other pointed a restore at a file the app
  never opened. Everything resolves `config` at call time now, twelve test
  redirects were paired up to match, and two tests pin it: the snapshot and the
  helpers must both follow a redirect of `config` alone.

## Coverage, for what it is worth

**81 % overall**, 5 458 statements. Chased deliberately during this build and
stopped deliberately: it found nine real defects, and the number itself was
never the goal.

Sixteen modules are at 100 %, including every one touched by a defect this
round — `export.py`, `env.py`, `item.py`, `overview.py`, `progress.py`,
`review.py`, `harvest/clean.py`, `config.py`, `grammar.py`, `handoff.py`,
`mining.py`, `speaking.py`.

Everything below 90 %, and why:

| | | |
|---|---|---|
| `evals/fetch.py` | 0 % | downloads benchmark datasets; nothing else in the app calls it |
| `evals/external.py` | 47 % | eval tooling, exercised by CI's separate `eval` job |
| `cli.py` | 52 % | the uncovered half is the write and network commands; every read-only one runs in the suite |
| `harvest/selges.py`, `harvest/err.py` | 57 %, 59 % | parsers covered, fetchers deliberately not |
| `providers/llm.py`, `evals/gec.py`, `providers/asr.py` | 67–72 % | network clients |
| `rection.py`, `harvest/evkk.py`, `harvest/lihtsad.py`, `providers/tts.py` | 80–84 % | network at the edges |
| `providers/grammar.py`, `sources.py`, `wordorder.py`, `app.py`, `providers/sonapi.py`, `difficulty.py`, `readiness.py` | 86–89 % | error paths and degradation branches |

The rest sits at 90 % or above. `wordlist.py` finished at 94 %, `gloss.py` at
99 %.

## What to do first in the next sprint

**Done since this list was written:** the redeploy. It was item 1 — the running
image predated the export fixes, so the deployed word card still printed
`kool, koola, koola` and 319 other invented paradigms. PR #17 merged at 12:21
on 2026-08-20 and Cloud Build had the new image serving by 12:24, confirmed by
the build stamp on `/api/health` rather than assumed from a green workflow.

1. **Merge #18, then run the deep smoke check and read the status code.** The
   grammar checker is in offline mode on the deployment right now. A 429 means
   the free tier is spent and it recovers on its own; a 401 means the key is
   dead and every writing check stays unexplained until it is replaced. Until
   the code is known, neither waiting nor rotating the key is justified.
2. **Re-harvest locally** so `content.db` is whole again and local measurements
   mean something.
3. **Study.** The verdict's three numbers for A2 — no exam part touched, 0 of 7
   topics mastered, checkpoint unattempted — do not move on their own, and they
   are what decides A2-then-B1 against B1-alone next year. This is the item
   that has been at number three through two sprints while the code around it
   got better; the app now has more features than it has practice history.
4. Then, if a build is wanted: the 13 topics with no generator, largest gap
   first.
