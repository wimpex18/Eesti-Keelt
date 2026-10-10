# Product

## Platform

web

## Users

The MVP serves Russian-speaking learners of Estonian, including people with
no prior knowledge and people returning with some knowledge. A2/B1 exam
candidates are one audience within that broader learning purpose.

English- and Ukrainian-speaking learners are the next planned audiences.
New product work must prepare for all three explanation languages from the
start; equivalent English and Ukrainian instructional support is not shipped yet.

Each permanent account has separate progress; signed-out use is an isolated
guest sandbox. In-app sign-up and sign-in run at the Cloudflare Worker in
front of the deployed app.

The learner splits work by device: the installed PWA on a phone for short
drill and review sessions, a desktop for reading, writing and longer work.

The product should bring lessons and practice into one clear, minimal and
concise structure. Learners should see a useful next step without having to
understand the whole catalogue first.

## Product Purpose

A free, non-commercial educational app for learning Estonian from the very
beginning through practical language use and A2/B1 exam preparation.
The core loop is **learn → practise → check**, across grammar, vocabulary,
reading, writing, listening and speaking, with text, audio and video material.

Success means the learner can start at a suitable point, understand the next
lesson, practise it, check their understanding and continue. Starting from
the beginning remains a choice even for learners with prior knowledge.
For exam preparation, readiness is tracked for each of the four exam parts.

The #1 documented weakness is `obj-case` (genitive vs partitive for a
completed object).

## Positioning

One guided learning path with a flexible entry point and the ability to move
past familiar material, inspired by Duolingo's start-and-skip flexibility.
Exam practice builds on that learning path rather than defining the entire app.

Dictionary information supports a lesson, text or review card: meaning first,
source-attributed examples and forms when needed, then a clear return to practice.
Klint's primary value is guided learning across reading, listening, speaking and
writing, with grammar feedback and optional exam preparation. Vocabulary tools
must support that sequence without becoming another competing home or dashboard.

Drills are graded by code against Vabamorf and EKI forms. Models explain,
tutor, and support open writing and conversation as labelled, advisory
feedback. The app says plainly what was checked and by what.

## Operating Context

- Home offers the next lesson; Course owns topics and free practice; Review
  owns scheduled cards; Exam owns optional preparation. Reading, listening,
  speaking and writing stay reachable on every screen (`docs/app-structure.md`).
- Phone: guided practice, vocabulary and review in short sessions.
- Desktop: the same activities, with comfortable reading and writing space.
- Material comes from EKI dictionaries and handbook (EKK), Selges keeles, ERR
  *Lihtsad uudised*, and owner-imported HARNO tasks presented in the app.

## Confirmed Release Direction

- **Onboarding:** offer three clear entry routes: start from the beginning,
  choose a self-assessed starting point, or take an assessment to find a
  suitable starting point. The assessment reports what it tested and an
  estimated recommendation; it does not claim certified CEFR proficiency.
- **Flexible progression:** let learners skip familiar topics, rules and
  individual text, audio, video, reading, writing, listening or speaking
  activities, continue forward and return later. A navigation skip is distinct
  from demonstrated mastery or completion; topic test-out uses checked answers.
- **Beginner learning:** provide a coherent sequence for someone with no
  prior Estonian, with explanation, examples, guided practice and a check
  before moving on. The current A0 recommendation is not that complete course.
- **Languages:** prepare content and onboarding for Russian, English and
  Ukrainian. Keep Estonian learning material and grammar terms shared; put
  explanations, meanings, instructions, warnings and accessibility wording in
  the learner's selected supported language. Gloss an Estonian term once in
  that language rather than transliterating it.
- **Default explanation language:** the web app and the iOS app take it from
  the system or browser language: the first of the learner's preferred
  languages that is Ukrainian, Russian or English (browser `navigator.languages`,
  iOS preferred languages), English when none is. It is preselected, never
  imposed: the first onboarding question shows it, Profile changes it at any
  time, and a saved choice always wins over detection. Location is never used
  to guess a language.
- **Preparation for localisation:** separate language-dependent instructional
  copy from shared lessons and exercises; retain stable topic, material and
  progress identities when the explanation language changes. Missing reviewed
  translations should be explicit rather than silently shown as supported.
- **Structure:** keep onboarding short, expose the current lesson and next
  action first, and reveal detail when needed. Exam preparation remains an
  optional learner goal; no exam sitting is assumed.
- **Design authority:** simplify page structure, navigation, controls and
  interaction logic where that improves learning. The redesign, Interlinear, is
  specified in `DESIGN.md` and replaces the shipped Practice rhythm visuals
  screen by screen (its migration order is in the same file).
- **Market-informed learning:** use current guided-course, targeted-practice,
  authentic-media and supported-speaking patterns as references. Prefer one
  recommended session with freedom to explore, change entry point and revisit
  material. Resolve duplicated entry points and broken or empty default flows
  before adding new tools. The research and applied decisions are in
  `docs/design-research.md`; implemented local behaviour is described in `docs/app-structure.md`.

- **One learning loop (ADR-0009):** a 20–30-minute session from the current unit
  — review, a rule learned by doing, guided practice, words, listening, speaking,
  an exit check — then the next task chosen by code with its reason, one
  *Jätka* and two alternatives. Every part also stands alone.
- **Exam preparation as loops:** each part simulated on the real clock, every
  item reviewed with its evidence, then practice on that task type and the
  grammar behind each miss. B1 first. Model feedback on writing and speaking is
  labelled and advisory; nothing is scored by a model.
- **Model lane:** Claude Haiku 5.5 for explanations and feedback once its eval
  passes, Opus 5.5 for drafting material (ADR-0008).
- **No human reviewer:** material is built from sources and model drafts that
  pass deterministic and blind automatic checks, and says so (ADR-0009).

These are product requirements. Current gaps and implemented behaviour are
recorded in `docs/status.md`; the course is specified in `docs/course-structure.md`
and tracked in Linear DEV-40, the explanation languages in DEV-42.

## Current Capabilities

- Current state, gaps and known issues: `docs/status.md` (read before
  planning). Generator coverage and remaining reference topics are derived
  from `eesti/curriculum.py` and recorded there.
- **MVP language roles:** UI labels and grammar terms are Estonian; explanations,
  warnings and reasons are Russian; examples and drills are Estonian.
  `tests/test_ui_language.py` checks that current production contract.
- Readiness is shown per exam part; there is no overall progress score because a
  zero in one part fails the exam regardless of the others.
- A learner may save a self-assessed starting band for recommendations. It is
  not CEFR evidence, mastery or an exam result. Topic test-out is available
  from Course topic actions. The broader sweep is in the CLI; a bounded grammar entry
  assessment is also available through `/api/placement/next`, used by onboarding.
- `level` means CEFR and only official HARNO/EIS material has one; `band`
  (`kergem`/`keskmine`/`raskem`) is relative difficulty.
- No linguistic fact without a source: Vabamorf forms and EKI handbook,
  Teatmik or learner grammar rules. Model-supplied claims stay labelled.
  Code grades drills and review and decides mastery; model feedback is
  advisory and never moves mastery or FSRS (`docs/ai-boundaries.md`).
- Offline-capable PWA. Fonts and icons are self-hosted (the page asks no font
  or icon host for anything); media APIs are allowed; keep system fallbacks.
- Data access is open to caching, batching and API integration. Keep source
  attribution (`/api/sources`). Empty or failed refreshes must preserve usable
  content, issued references and each learner's progress.
- The repository targets the latest stable Python and dependencies.
- No countdown until the learner chooses an exam sitting.

## Educational Material

Use publicly available educational resources broadly and keep the learner in
the app with source-attributed text, PDFs, audio, video and exercises wherever
reuse is supported. A source's public availability and the app being free do
not by themselves establish permission to copy or redistribute it.

Source-specific licences, permissions and applicable exceptions determine
reuse. Attribution and source records belong in `docs/sources.md` and
`/api/sources`. Current owner-only access is an implementation and rights-review
state, not a permanent product requirement; broaden access when the source's
reuse basis is established. Official EIS scoring remains external where its
answers are only available there.

## Brand Commitments

- Name: **Klint**, after the Baltic Klint, the limestone escarpment along
  Estonia's north coast that learners climb step by step; the name is not an
  Estonian common word and reads the same in Russian, Ukrainian and English.
  **Eesti keel** identifies the subject; the artwork says *algusest kuni B1-ni*
  (from the beginning to B1). Stored identifiers that carry the earlier name
  Grove (the `grove-material` source id, the Worker service) stay unchanged.
  Russian is supported today; English and Ukrainian are planned explanation
  languages.
- Visual system: **Interlinear** (`DESIGN.md`): the Estonian form with its form
  name beneath it from code, spruce ink on a birch ground, solid surfaces,
  Geologica in two cuts, one fixed primary action per screen and the four
  original skill pictograms. The mark is an underlined K. Its tokens and
  shell ship; each screen keeps its earlier layout until it is rebuilt.
  Research and reasons are in `docs/design-research.md`.
- The interface is itself language exposure: Estonian labels with a gloss in
  the learner's supported explanation language where needed; Russian in the MVP.
- Honest about limits: a caveat the learner cannot read is not a caveat.

## Evidence on Hand

- Real content: word list, EKI dictionaries, handbook links, reading corpus,
  ERR episodes, the learner's own mastery and review history.
- Speech-recognition evidence includes a native/synthetic benchmark and a
  small set of human-verified learner clips, below the pilot floor
  (`docs/asr-evaluation.md`). The in-app **Kuidas mind kuuldakse** check measures
  the production recogniser; it is not a pronunciation or exam score.
- No public testimonials, customer counts or pass-rate claims are established;
  none may be invented. Limited engine evaluations do not establish learning
  outcomes or general recognition reliability.

## Product Principles

1. **Correct beats clever.** Code decides mastery and review; models provide
   labelled advisory feedback. Never show a verdict the app cannot stand behind.
2. **Start where the learner needs.** Beginning, self-assessment and an
   assessment are valid entry routes; familiar material can be skipped and revisited.
3. **Make the next step clear.** Keep the structure concise and distinguish
   skipped material, practice, checked mastery and exam readiness.
4. **Teach across languages.** Estonian stays the learning language;
   explanations follow the learner's supported language, with honest limits.
5. **Fit the session.** Support short phone practice and longer desktop work;
   prepare learners for practical use as well as each part of an optional exam.

## Accessibility & Inclusion

No specific needs beyond a baseline: WCAG AA contrast in light and dark
themes and full keyboard use.
