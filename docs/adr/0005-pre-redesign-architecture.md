# ADR-0005: Architecture before the UX redesign

**Status:** Accepted. **Scope:** one learner, one origin, no paid inference host.

## Decision

Keep the modular FastAPI application, SQLite event log and projections, the
Cloudflare Access/Worker front door and the singleton Durable Object. Keep
Workers AI Whisper in production and use TalTech verbatim Whisper as a **local
benchmark reference**, not a second production dependency. Preserve deterministic
planning, grading and FSRS. Use the measured Workers AI explaining lane; unavailable GEC and low-quality
normalization/LLM candidates are explicit evaluation tools only. No framework migration,
message broker, vector store, streaming service or new model host is needed for
the redesign.

This is a feasibility and evidence decision, **not a measured ASR quality win**.
There are no learner recordings in the local evaluation folder, hence no
verified learner transcripts and no comparative WER/false-accept result. Native
EKI recordings and cached TTS are present; neither is learner ground truth.
The current model stays until the workflow in `docs/asr-evaluation.md` supplies
paired evidence and a deployable improvement. Catalogue presence is insufficient. Actual native EKI controls establish that
local CT2 and Zipformer can run; they are not learner ground truth.

## Architectural contracts to preserve

| Area | Decision and evidence in the implementation |
|---|---|
| Evidence/projections | `eesti/evidence.py` owns immutable event envelopes and replay handlers. Signed issued fields in `eesti/itemref.py` preserve the presented item; generator references alone are not immutable content. Keep events as the source and the four learner databases as projections. Operational caches, budgets and breakers are snapshot state, not learning evidence. |
| Learner/planning | Keep `eesti/learner.py` recency-weighted rule evidence and FSRS retrievability, and the pure `eesti/planning.py` plan with its input digest. These explain decisions without model judgement; statistical learner models have no calibration set here. |
| Curriculum | Keep the prerequisite DAG, generator registry, representation links and explicit reference-only topics. Do not invent generators to make coverage look complete. Stable topic/rule IDs survive screen renaming. |
| FSRS | Keep code-rated grammar and self-rated vocabulary distinct. Fitting is implemented locally by `eesti/optimise.py`; collecting sufficient review history is pending, not building an optimiser. Fit events travel with the log. |
| Exam/readiness | `eesti/exam.py`, `eesti/mock.py`, `eesti/readiness.py` implement chosen goals, clocks, sections, `.ics` and per-part evidence. Contact and practice are not a calibrated pass probability. Speaking remains unscored; mocks state their approximation to HARNO tasks. |
| AI/provenance | `eesti/tutor.py` is the common boundary for model feedback. `deterministic`, `model+verified`, `model-only` and transcript `advisory` have different meanings. Form existence does not prove contextual correctness. Detect object-case swaps from morphology even if the model supplied the wrong tag; deterministic findings take precedence. No model output changes mastery or FSRS. |
| Providers | Workers AI is the sole hosted grammar/tutor lane; an explicitly configured local trial precedes it. GEC, normalization and other hosted candidates are evaluation-only. Offline deterministic evidence handles failure. Explicit model IDs remain operational choices; changing a model requires the grammar eval. Never equate an empty/malformed response with correctness. |
| Quotas/breakers | Keep persistent per-lane counters and exponential cooldown. Breaker connections open on each request thread; tutor failures share the breaker. Interactive calls make one attempt per lane. Counts are best-effort call allowances, not exact account/token/Neuron billing caps; snapshot lag and concurrency can lose counts. Worker ASR uses Cloudflare's quota and does not traverse Python's budget. No automatic paid upgrade or retry storm. |
| Speech | Cloudflare receives production audio; no app audio archive. Transcripts/practice signals enter evidence; feedback stays advisory. Recognition is not pronunciation assessment. Local CT2 reference dependencies stay outside the deployment image. |
| Offline/sync | Keep cached shell and explicit IndexedDB drill packs; never cache API responses. Re-grade signed items server-side and deduplicate queued event IDs. Preserve pending answers across UI upgrades. There is no general offline tutor, exam or multi-device conflict resolver. |
| Reminders | Keep opt-in, evidence-driven facts, quiet hours, deduplication and encrypted Web Push. Deployed VAPID bindings and cron are verified; browser delivery remains unmeasured. Cron restores state before deciding. No motivational scoring, email service or retained conversation transcript is needed. |
| Privacy/recovery | Exported events contain writing and speech transcripts. `cli verify-backup` replays an export twice into isolated stores and rejects unsupported events. Manual private off-account exports remain the independent backup; live replication is not a backup. See `docs/deploy.md`. |
| Deployment | Keep one Cloud Run instance and one process, no traffic splitting between independent writable revisions. Asynchronous Worker event copying is not a durable acknowledgement: a crash before copying may lose acknowledged work. Scale-out requires moving the write authority, not increasing the instance limit. |
| Testing | Offline domain tests and replay tests, separate live provider evals, local browser journeys for both viewports. Morphology gold validation remains the dependency-upgrade gate. The redesign must exercise journeys, offline replay and restored state. |

## Deferred items, decided individually

- **Per-identity Durable Objects:** deferred. The origin itself is single-tenant;
  changing only the object name would falsely imply isolation. Revisit only with
  a real second learner and end-to-end identity-scoped storage.
- **`DELETE /api/me`:** deferred as a self-service feature, not replaced with
  progress reset. Erasure must coordinate the DO log/snapshots/push subscriptions,
  origin, browser queue, exports and externally sent Notion rows. A partial
  endpoint would resurrect data on restore. The operator procedure in
  `docs/deploy.md` defines the scope; no deletion is performed by this work.
- **Nightly independent backup:** deferred for this owner-operated app. Use a
  private export before migrations/redesign and periodically during study,
  validate it, and keep it outside the hosting account. This accepts loss since
  the last manual export if the hosting account is lost. Add scheduled encrypted
  backup only when that recovery-point tradeoff is unacceptable; do not put
  learner JSONL in public CI artifacts.
- **FSRS optimiser:** implemented; running it is deferred until enough history
  exists. A forced small-data fit is an experiment, not evidence of improvement.
- **Recorded ASR corpus:** remains necessary. Start with 20 manually verified
  clips, at least five error probes; expand toward 80–150 across normal and
  difficult conditions. No claimed sample size guarantees statistical power.
- **Streaming/local production ASR:** deferred. Short record-and-submit answers
  do not need partial transcripts. CPU Zipformer is the first streaming option
  to revisit if live interaction becomes a requirement; GPU Voxtral adds no
  demonstrated learning benefit today.
- **Acoustic scoring, conversation scoring, generated listening tasks, web
  placement sweep and missing curriculum generators:** remain separate product
  work. Current practice/contact signals and CLI placement are usable; scoring
  needs validated criteria, and linguistic content needs cited answer keys.
- **Conversation retention:** keep only occurrence/length. Retaining turns adds
  personal data without a current reader in readiness or planning.
- **Browser journeys in CI:** retain the local release gate for now; a clean
  fixture-only browser job is useful redesign work, not a reason to add private
  corpora to CI. Current CI does not certify browser behaviour.

## Redesign constraints

The redesign may replace presentation without replacing domain functions. Keep
route contracts, stable IDs, provenance/advisory/degraded fields, signed tokens,
and offline queue IDs. `planning.Block.action` currently includes tab names;
map those at the UI boundary or migrate them together. DOM IDs and cross-module
imports are presentation coupling, not reasons to duplicate domain state in a
frontend store. Cached pages may use older API contracts during rollout.

Progress reset is not erasure. Replay skips unknown events on normal rollback;
strict backup verification refuses them. A malformed event must never be silently
reported as a fully verified backup. Do not introduce a second persistence source
for questions, goals, reminders or fitted parameters during redesign.

## Source of truth

Code and tests define behaviour; deployment smoke proves what is running.
`docs/status.md` describes features/known gaps, this ADR defines decisions,
`docs/asr-evaluation.md` defines measurement, and `HANDOFF.md` holds the current
operational step.
`AGENTS.md` carries repository-wide agent instructions.
