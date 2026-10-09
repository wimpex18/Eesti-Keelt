# Architecture review and roadmap

The plan that came out of the October 2026 review of architecture, content,
sources and market, kept current. Illustrated original (private to the owner):
<https://claude.ai/artifact/9x35tYbYJDvTy5sAqHf1hg>. Current facts and known
issues are in `docs/status.md`; work is tracked on the existing Linear issues
(team DEV, project Eesti-Keelt; no new issues).

## Owner decisions

- A complete, practice-first path from A0 to B1 that learners use alongside
  Keeleklikk (0–A2) and Keeletee (B1), plus B1 exam preparation. Grove makes no
  video lessons.
- Explanations in Russian, then Ukrainian, then English; Estonian material,
  keys and progress shared.
- Private sources (ERR, Selges keeles, HARNO, EIS) stay owner-only until written
  permission; drafts in `qa/source-permission-requests.md`.
- No embedding model: long-context grounding on the Claude lane replaces
  retrieval. EmbeddingGemma 2 is revisited only for cross-lingual phrase search.
- One implementation session at a time, one branch and one PR per session
  (`AGENTS.md`).

## Decisions and their state

| # | Decision | Linear | State |
|---|---|---|---|
| D0 | Licensable material for every learner | DEV-36 | Partly done: EKI EVS phrases feed every corpus topic, dictation, read-aloud and mock reading/listening for public learners (DEV-54), and EKI's credit now shows on every item built from them, offline packs, test-out and placement included, and on review cards queued from 9 Oct 2026. Open: reading texts (none public), Settle in Estonia A1/A2 import once confirmed (DEV-56), permissions (DEV-55), the material pipeline below |
| D1 | Correctness | DEV-35, DEV-49..53 | Done: EVS homographs and inflection types, nimetav-object writing check, item labels and capitals, exam screens, rection norms EKI now accepts, retired rection cards out of due counts, one-reading case labels on short phrases. Open limits are in `docs/status.md` (parallel forms beyond Vabamorf, templated frames, narrow object check) |
| D1b | Data safety | DEV-37 | Done in code: nightly off-Cloudflare backup, Durable Object fixes, `ITEM_SECRET`, durable guest allowances. Owner setup pending (below) |
| D2 | Litestream-replicated SQLite instead of Durable Object replication | DEV-43 | Open; after the 7–8 Nov 2026 sittings |
| D3 | Claude Haiku 5.5 tutor lane and eval | DEV-38 | Open; needs the owner's API key in `.env` |
| D4 | Long-context grounding in EKI rule text | DEV-44 | Open; after D3 |
| D5 | Ukrainian, then English explanations | DEV-42 | Open; after the D6 spec |
| D6 | A0→B1 course structure: units, topics, modes | DEV-40 | Spec (`docs/course-structure.md`) and ADR-0007 agreed with the owner on 9 Oct 2026; first slice built: thirty units in `eesti/units.py`, Kursus by unit, unit 1 (sounds in EKI's recordings, EKI's A1 phrases, numbers, first words), the nominative total object, `osaalus`. Open: unit check, homework, weekly plan, dialogues and texts, unit pages in the redesign |
| D7 | HARNO task formats in practice and mocks | DEV-41 | Open; after the D6 spec |
| D8 | Lemma search, passkeys, account recovery, ASR heartbeat | DEV-48 | Open; later |
| D9 | Practice patterns (edit-then-explain, hint-first, mistakes session) | DEV-45 | Open |
| D10 | Locked dependencies and current versions | DEV-39 | Done |
| — | Scheduled harvests, corrected source notes | DEV-46 | Open |
| — | Four-week pilot with Russian, Ukrainian and English learners | DEV-47 | Open; after the sittings |

## Owner actions outstanding

1. Verify a nightly backup copy with `cli verify-backup` (`docs/deploy.md`):
   the bucket and trigger are set up, but no object had appeared by 9 Oct 2026.
2. GitHub → Settings → Actions → General: allow GitHub Actions to create pull
   requests (the weekly `python-upgrade` workflow needs it).
3. Mac mini: unpack the new ZIP and run `zsh deploy/home-asr/install.sh`.
4. Send the permission requests from the project's own address; EKI's now also
   asks about the pronunciation exercises' audio and the etLex licence.
5. Put `ANTHROPIC_API_KEY` in `.env` before D3.
6. After 28 Oct 2026: Node 26 in the Dockerfile and workflows.

## What the next steps build

### Course structure (DEV-40)

Specified in `docs/course-structure.md`, decided in ADR-0007: thirty one-week
units in four stages (Algus, A1, A2, B1) over the 46 topics, mapped to HARNO's
A2 and B1 topics and EKI's etLex grammar profile (546 statements, 84 A1, 136 A2,
171 B1, cited by id). Built: the units, Kursus by unit, unit 1, the nominative
total object and the partitive subject. Next: the unit check (code-graded, five
items per core topic and revisit), homework and the weekly pace check, then
the grammar the units still lack (plural partitive and plural cases, modal
verbs with infinitives, indefinite pronouns, relative clauses, negation outside
present and past) and word sets for the HARNO topics `themes.py` lacks
(personal data, daily routine, free time, relationships, shopping and money,
services, directions).

### Material pipeline (DEV-36)

Model drafts → Vabamorf verifies every form → every lemma within the band's EKI
level → coverage by code → a person reviews → code keys: graded texts and
dialogues by HARNO topic (Batch API: about $0.25 per 1,500 drafts on Haiku 5.5),
HARNO item types keyed to text spans, multi-voice TTS listening from the same
scripts, at least 20 writing prompts and 30 speaking cards per level. Label it
"written with a model, checked by Vabamorf and a person".

### Exam fidelity (DEV-41)

HARNO A2 has 14 task types and B1 12; Grove reproduces 2 (owner-only),
approximates 10 and has nothing for 14, including every listening task. Build:
HARNO item types keyed by code, both writing tasks per level on the real clock,
HARNO criteria and rated samples beside the learner's text with a content-point
checklist (HARNO's passing B1 samples contain many errors), per-part results
with evidence volume, an *Eksamipäev* page (paper and pen, no dictionaries).
Speaking is never scored.

### Claude lane (DEV-38, DEV-44)

GPT-OSS-120B catches 8/10 planted errors (8/8 clean) but 2/40 attested learner
errors (16/20 clean). Claude Haiku 5.5: 1M context (100K is the price threshold),
$0.10/$0.50 per MTok up to 100K-token prompts, cache read $0.01, batch
$0.05/$0.25; about $0.0003 per tutor call. Switching needs: no `temperature: 0`
(rejected), explicit effort, JSON-schema outputs, refusal handling (no server
fallback), a native Messages API lane, a ≤100K prompt guard, the 3.5 s throttle
scoped to evals, an ADR replacing "no paid inference host" with a spend
ceiling, and the hand and external evals passing a margin agreed first.

### Explanation languages (DEV-42)

About 1,900–2,400 Cyrillic fragments in about 90 files, no catalogue; `why_ru`
is signed into item tokens and stored in events; the tutor grounding treats any
Latin word as Estonian (English explanations would be rejected);
`explanation_language` is stored in the profile but unread. Shape: canonical
layer with stable IDs; a catalogue per language with draft/reviewed status,
CLDR plurals and per-language contrast notes; items and new events carry
`rule_id` and parameters. Meanings: Ekilex/Sõnaveeb `ukr`/`eng` (already parsed
in `eesti/providers/sonapi.py`), EKI picture dictionary (uk 997, en 960), EKI
English–Estonian (public domain), EKI Estonian–Ukrainian (on request).

### State layer (DEV-43)

Today the origin writes SQLite on Cloud Run's ephemeral disk; Durable Objects copy
events after each write and push the whole log back on a new boot for a full
replay (about 2.5–3k events/s measured on 8 Oct 2026). Proposal: one SQLite
directory per learner replicated with Litestream (directory watching) to R2; lazy
restore on a learner's first request without replay; the corpus on the read-only
GCS mount; Durable Objects keep accounts, sessions and push. Trade: a ≤1 s loss
window on an unclean crash instead of per-response confirmation.

### Practice patterns (DEV-45)

Edit-then-explain (code extracts the exact difference, the model phrases it;
Song et al., NAACL 2024: 40.6% → 93.9% correct explanations), hint before the
answer, a mistakes session, format-weighted mastery with a mislearned state,
adaptive placement over the topic graph, conversation as a mission with
objectives, listening micro-drills, sentence mining from the reader.

## Sources worth adding

EKI etLex grammar profiles and word lists (public API, terms not stated: ask);
Ekilex Ukrainian/English translations and collocations (CC BY 4.0); Settle in
Estonia A1/A2 (CC BY-SA 3.0 in e-Koolikott metadata: confirm); ERR *Lihtsad
uudised* audio (permission); TestEst diagnostic and sample tests (link out); graded
exam writing (TLU, 720 HARNO scripts, MIT; `elle_et`, CC BY 4.0); Sõnaveeb *Õpime
eesti keelt* model letters (CC BY 4.0); EKI pronunciation exercises (CC BY 4.0,
confirm audio); TalTech EFAC accent corpus (evaluation only, never committed).
Risks: `api.sonapi.ee` has no identifiable operator (prefer the Ekilex key);
ERR allows a headline and five sentences without permission; TartuNLP GEC 8B is
a Llama 3.1 derivative.

## Market

No Estonian course on Duolingo, Babbel, Busuu or Rosetta Stone. Selgeks (A1–B1 to
the A2 exam, English only, EKI-verified), Konsta.app (Russian/Ukrainian, generated
content, unverified), Keeli (student project), Speakly and Lingvist (vocabulary),
state courses Keeleklikk, Keeletee and Keelelend (B2, Estonian only). B1 is the
largest and hardest cohort (2024: 3,615 candidates, 62.9% pass; A2: 2,387, 70.7%).
Grove's distinct offer: Russian, Ukrainian and English explanations, verified
grading, B1 practice, honest per-part readiness, free offline use.
