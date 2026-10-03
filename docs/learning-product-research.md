# Learning product research

Market snapshot: **2–3 October 2026**. This is research and the rationale for the
DEV-5 redesign under local verification, not evidence of production publication.

## Evidence and limits

The comparison uses current official product pages, support instructions,
published screenshots and release notes. The Grove guest interface was also
inspected in the owner's Chrome tab on desktop and at a 402 × 874 phone viewport.
Repository behaviour was checked against the checkout and GitHub's current
`docs/status.md`. Local preparation is not evidence of production publication.

Competitor subscription accounts and installed native apps were not tested.
Published release dates below establish current public evidence, not the latest
binary version in every country or an independently verified learning outcome.
Vendor claims about fluency, pronunciation accuracy and learning speed are not
used as proof. No sources dated after this snapshot are included.

## Relevant market patterns

Sõnastik was added on 3 October at the user's request. Its App Store listing,
release notes and the native screenshots on its public website were inspected;
the installed application was not tested.

| Product | Verified public experience | Useful adaptation for Grove | Tradeoff to avoid |
|---|---|---|---|
| Duolingo | A guided course path plus on-demand speaking, listening, mistakes and word practice; its current guide says skill practice is free on iOS and Android. | A strong next lesson, easy review of prior material, and direct skill practice. | A long path or extra reward systems must not obscure the next action. [Practice guide](https://blog.duolingo.com/guide-to-duolingo-practice-hub/), [course navigation](https://blog.duolingo.com/how-to-review-lessons-on-duolingo/) |
| Babbel | A placement quiz recommends a course; learners can change it. Review uses flashcards, writing, speaking and listening and can be recommended alongside the next lesson. | Editable starting point and one practice system with several exercise types. | Do not expose every practice method as a separate page. Placement availability varies by language. [Placement](https://support.babbel.com/hc/en-us/articles/20202703767442-Placement-quiz), [review](https://support.babbel.com/hc/en-gb/articles/205600228-Vocab-workout-Review) |
| Busuu | Placement suggests an entry level, with the option to begin earlier. The support page distinguishes placement from completed lessons, although it can suppress review of earlier words and grammar. | Let learners choose the beginning after assessment; make course position and completion separate. | Grove must not copy the automatic mastery implication: navigation choices do not award checked mastery. [Placement](https://help.busuu.com/hc/en-us/articles/16526383831569-What-is-a-Placement-Test) |
| Drops | Topics and word previews allow reversible hiding of words. Review Dojo schedules vocabulary review; its empty state explains when no review is needed. | Familiar-word controls, undo, and useful review-empty explanations. | Hiding words can prevent Drops topic progress; Grove skips should advance navigation and remain visibly distinct from completion. [Hide/unhide](https://support.languagedrops.com/hc/en-us/articles/19405567894419-How-do-I-hide-or-unhide-words), [Dojo](https://support.languagedrops.com/hc/en-us/articles/19334419328275-Dojo-Feature-What-is-it-and-How-to-Review-Words) |
| Speak | An expert-led learn–practise–apply sequence places speaking in situations. Tutor lessons offer hints, repetition and flexible pace; a September 2026 announcement describes help during an answer. | Give a speaking goal, example and suggested reply before asking a beginner to talk. | Open chat alone is not a beginner curriculum; advertised speech feedback is not evidence that Grove can grade pronunciation. [Method](https://www.speak.com/), [September release](https://www.speak.com/blog/live-tutor-lessons-powered-by-openais-gpt-live-1) |
| Praktika | Its February 2026 4.0 release describes a complete UI redesign, system dark mode, improved VoiceOver and goal-based scenario practice. Published practice screens use labelled topic rows. | Clear scenario choices, everyday goals and accessible controls. | Animated tutors and personalisation should not become prerequisites for a useful session. [4.0 release and screenshots](https://praktika.ai/blog/praktika-4-0) |
| Langua | July–September 2026 updates describe a recommended Path with a separate Explore route, content-to-conversation practice, suggested replies and recovery from stalled chats. Some new call features are a gradual beta rollout. | Guided by default, flexible by choice; preserve work and offer recovery when speech or a provider fails. | Do not infer universal availability from a beta announcement or copy its growing settings surface. [Current updates](https://support.languatalk.com/article/152-see-the-latest-updates-on-langua) |
| Memrise | The current public experience centres native-speaker video, understanding phrases and repeating them; it also describes private AI practice. | Connect listening, reading and speaking around one useful piece of language. | A video collection still needs a recommended next activity and suitable beginner material. [Current method](https://www.memrise.com/) |
| LingQ | A library, Continue Studying shelf, guided entry options and a reader combine audio, word lookup, sentence view and review. Its April 2026 notes describe reader, playback and offline reliability work. | Keep source text, audio and vocabulary together; resume the actual material. | A large import/library catalogue should not be the novice's first decision. [Reader and mobile flow](https://www.lingq.com/en/ios-app-support/), [2026 updates](https://forum.lingq.com/t/batch-importing-instagram-import-new-lesson-complete/2620919) |
| Lingvist | Adaptive vocabulary exercises use contextual sentences and scheduled repetition, with desktop and mobile access. | One compact exercise, then actionable feedback; vocabulary review can reuse the lesson context. | Vocabulary coverage is not a CEFR test or a complete four-skill course. [Current product](https://lingvist.com/) |
| Pimsleur | Core audio lessons lead to recall, reading and speaking activities, with mobile/offline use and a web app. Some features vary by language. | A simple audio session with replay, pace and a next step, plus supporting transcript/exercises. | Long audio alone does not meet every short-session or exam need. [Learning loop](https://www.pimsleur.com/), [app](https://www.pimsleur.com/pimsleur-app/) |
| ELSA Speak | Goal-based English speaking practice combines personalised lessons, role-play and feedback, with progress reporting. | Show a concrete speaking purpose and a small amount of actionable feedback. | Keep diagnostics out of the exercise; English speech-scoring claims do not transfer to Estonian. [Current product](https://elsaspeak.com/en) |

The strongest references for this project are Babbel/Busuu for course entry,
Duolingo for a next lesson plus targeted practice, Drops for reversible word
choices, Speak/Praktika/Langua for supported speaking, and LingQ/Memrise for
using real material across skills. This is a design judgement from the evidence,
not a ranking of learning effectiveness.

The synthesis also follows established usability research: show frequent tasks
first and reveal occasional detail on request; make distinctions between options
explicit; teach controls in context instead of through a long introductory tour.
[Progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/),
[clear option differences](https://www.nngroup.com/articles/explicit-differences/),
[contextual help](https://www.nngroup.com/articles/onboarding-tutorials/).

## Estonian-specific reference: Sõnastik

The [App Store listing](https://apps.apple.com/ee/app/s%C3%B5nastik-learn-estonian/id6764018075)
shows version 1.18.2 and describes Ekilex-backed lookup, five translation
languages, saved words, flashcards, vocabulary-level practice, typed forms and
EVS example phrases. These are vendor claims, not independently verified
outcomes. The [published website](https://www.sonastik.app/en) shows search
history, meanings and declension views; it describes spelling/diacritic/form
tolerance, cached recent entries and separate meaning/form information.

**Grove's distinction is the learning journey.** Its entry choice leads to a
lesson, checked practice, understandable correction and a next action. Reading,
listening, speaking and writing stay visible; optional exam preparation adds
real task formats and evidence. Dictionary lookup helps with the current text
or exercise rather than becoming the main product. A beginner curriculum and
complete English/Ukrainian instruction still require reviewed content; the
redesign does not establish that these are complete.

Useful adaptations fit that positioning:

- Put a concise meaning and relevant usage example ahead of a large form table.
  Keep detailed forms available within the same contextual card.
- Preserve the learner's text, query and course position when returning from a
  lookup. Save a useful word directly into the existing review queue.
- Resolve inflected forms and spelling alternatives visibly, so a tolerant
  dictionary match does not silently become a correct drill answer.
- Reuse cached source data and honest retry states. Keep one review system and
  learner-owned progress rather than adding separate vocabulary dashboards.
- Prepare instructional-language selection independently from the Estonian
  target word/topic identity; do not reset progress when language changes.

There is no new exclusive source to acquire from Sõnastik. Grove already imports
EVS examples and has authenticated Ekilex lookups alongside Vabamorf forms;
see [sources.md](sources.md) and [source-integrations.md](source-integrations.md).
Fetch reference data from its upstream and preserve its attribution. EKI itself
[distinguishes current Sõnaveeb/Ekilex data from historical dictionary editions](https://arhiiv.eki.ee/dict/).
Sõnastik's private service, artwork and UI are not needed for that reuse.

Vocabulary tags and a brief word quiz are useful routing evidence; they do not
establish CEFR proficiency across four skills. Grove retains named word-level
sources, bounded grammar assessment and a separate exam-readiness view. The
vendor's word-percentage presentation is not adopted as a proficiency score.

## Observed Grove problems

| Evidence in the live guest UI | Consequence | Proposed response |
|---|---|---|
| The home starts a pronoun drill before an entry choice and places topic position, mastery marks, today's checklist, a time plan and an exam rail around it. | A new learner must interpret the app before choosing how to learn. | Entry first; a calm home with one start/resume action; a separate session screen. |
| Switching modes replaces the skill navigation. At phone width speaking and writing sit outside the initial horizontal skill row. | The four main skills are not consistently visible. | Permanent four-skill navigation; a labelled home return; course, review, exam and account utilities in predictable places. |
| Reading reports zero texts, then explains a long recommendation policy and says the library will be added. | A prominent destination provides no learning action. | A source-labelled starter activity, then the library when available; one recovery/continue action. |
| Speaking selects read-aloud sentences when none are available and still displays playback/recording controls. | The default task is unusable even though other speaking modes exist. | Select a usable task; disable unavailable actions with a recovery option; support mic denial and ASR/provider failure. |
| Listening has an empty broadcast archive alongside dictation and a complete TTS utility form. | A learner must distinguish tools from lessons. | Lead with a usable listening session; put custom-text playback and archive browsing behind labelled choices. Audio playback/recognition itself was not tested in this inspection. |
| Writing opens an unprompted blank checker; the right rail discusses exam contact counts. | Beginners receive little help deciding what to write. | Prompt, example and optional hint first; keep open-text checking available as a secondary action. |
| The exam overview repeats readiness, part contacts and milestones and links its next step to general grammar. | Exam preparation and everyday learning compete for attention. | One exam workspace reached when wanted; task practice first, requirements and readiness detail on request. |
| Progress evidence appears in the rail, exam overview, progress page and profile. | Several views explain the same state with different visual emphasis. | One progress destination; a small relevant completion summary after a session. |

These are present-state observations, not claims about when defects were
introduced. Empty content can involve publication or access scope, not only UI
code. Confirm its upstream-to-production route during implementation. Guest
findings do not imply that owner-imported material is absent from owner accounts.

## Proposed product structure

The home answers **what should I do next?** It offers the saved session or next
lesson, a change-course control and a secondary review action only when useful.
It does not embed an active answer field or display an exam dashboard by default.

The four skills remain reachable throughout normal navigation. On phones they
fit as four labelled destinations; home and account/more live in the header.
On desktop one compact navigation area replaces the mode-switch-plus-tab shell.
An active exercise focuses on its task and retains an obvious return route.

Course browsing, review/vocabulary, exam preparation and account/progress are
secondary destinations. Fewer entry points must not require deep menu nesting:
each ordinary task should be reachable from home or the persistent skill links.

| Current feature | Proposed destination |
|---|---|
| Rada, today's plan, daily steps | Learning home and a separate guided session; one next-action decision |
| Kogu rada, level/start preferences, topic test-out | Course picker and onboarding; skip, restore or demonstrate knowledge |
| Vaba harjutus | Choose a topic from Course or Practice; retain the explicit unrecorded mode |
| Reading library, word lookup, comprehension | Reading lesson with vocabulary and questions in context |
| Dictation, radio, custom TTS | Listening; tools and media selected within that skill |
| Read-aloud, spoken questions, conversation | Speaking; labelled exercise choices with usable defaults |
| Text checker, back-translation | Writing; a guided prompt first, open text checking on request |
| Järjekord, Sõnavara, shared word cards | One Review/Vocabulary area; preserve scheduling and known/ignored states |
| Töövihikud, official tasks, mocks | Exam materials/practice, while general learning can surface relevant material |
| Rail, Edenemine, profile evidence, milestones | One progress view; small contextual summaries only where needed |
| Auth, explanation language, reminders, data export/reset | Account/settings, with progress and data identities preserved |

## Required flows and acceptance criteria

1. **First visit:** choose beginning, self-assessed starting point or a bounded
   assessment. Optional exam goal and account setup must not block a first lesson.
   Offer English/Ukrainian only when instructional coverage is reviewed; prepare
   the content model now without pretending those full courses have shipped.
2. **Lesson:** show a source-backed explanation or example, practise one task,
   give useful feedback, then continue. The controls distinguish skip this
   activity, skip this topic and checked test-out. Undo/revisit is easy. A skip
   never creates mastery, review success or exam readiness.
3. **Existing learner:** resume the correct topic/material and retain all stored
   progress. Changing course position or explanation language does not reset it.
4. **Four skills:** every default route has a working starter activity or a clear
   recovery path. Prompts and useful examples replace empty generic forms.
5. **Failures:** missing content, microphone denial, loading, offline, failed
   playback and delayed model responses each explain what happened and expose
   one useful next action. Avoid presenting unavailable controls as runnable.
6. **Hierarchy:** one primary action per task state; labels state what happens;
   progress is relevant to the current task. Remove duplicate summaries and
   ornamental data visualisations where they do not aid a decision.
7. **Devices:** check portrait/landscape phone, tablet and desktop. Preserve
   keyboard focus, browser back/deep links, touch targets, contrast, long Russian
   wording, future localisation space and reduced-motion support.
8. **Learning truth:** linguistic forms/rules and attribution retain their sources;
   model feedback stays labelled and advisory. Source rights and access facts,
   learner evidence, account isolation and offline replay remain accurate.

## Implementation sequence

Research and live review feed a fresh direction chooser. Once a direction is
selected, record its surface contract, consolidate navigation and entry flows,
connect existing skip/placement/starter APIs, then repair and simplify each skill
and utility flow. Verify real journeys and the viewport matrix, run the independent
Impeccable finish review, document the built system and prepare a reviewable PR.
The user merges; production checks follow publication. Code-first remains the
standing workflow. Current backend preparation and outstanding UI work are in
`HANDOFF.md` and `docs/status.md`.
