# Design research and decisions

Source snapshot: **3 October 2026**. Official product pages, support guides,
publisher screenshots, releases and brand references inform the current design.
Native competitor apps and subscription accounts were not tested. Dated releases
and forecasts do not establish universal availability or learning effectiveness.
This record explains the choices; current capabilities and gaps live in
[status.md](status.md), structure in [app-structure.md](app-structure.md), and
implemented tokens/components in [DESIGN.md](../DESIGN.md).

## Applied to Grove

- One next lesson on Home, then learn → practise → check in a five-item session.
- Beginning, chosen starting point and a bounded grammar check are separate entry
  choices. Skips advance navigation without awarding mastery or review success.
- Reading, listening, speaking and writing remain visible. Course, Review, Exam
  and account own their supporting tools instead of duplicating dashboards.
- Contextual dictionary lookup supports the lesson or text and the same review
  queue. It does not become a second learning home or CEFR percentage.
- Pale blue/aqua grounds, deep blue actions and a navy dark theme match the
  selected Practice rhythm direction. Glass is limited to navigation; text,
  exercises, correction and word cards stay solid.
- Self-hosted Geologica distinguishes softer interface text from sharper
  Estonian material. Its bundled glyphs cover Estonian, Russian and Ukrainian;
  glyph coverage is distinct from complete translated instruction.
- Original book, headphones, microphone and pencil pictograms identify the
  skills by shape and colour. Phosphor supplies the small utility set; visible
  labels and keyboard access carry meaning independently of colour.

## Language-learning references

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
EVS examples and supports optional authenticated Ekilex lookups alongside Vabamorf forms;
see [sources.md](sources.md) and [source-integrations.md](source-integrations.md).
Fetch reference data from its upstream and preserve its attribution. EKI itself
[distinguishes current Sõnaveeb/Ekilex data from historical dictionary editions](https://arhiiv.eki.ee/dict/).
Sõnastik's private service, artwork and UI are not needed for that reuse.

Vocabulary tags and a brief word quiz are useful routing evidence; they do not
establish CEFR proficiency across four skills. Grove retains named word-level
sources, bounded grammar assessment and a separate exam-readiness view. The
vendor's word-percentage presentation is not adopted as a proficiency score.

## Colour, hierarchy and materials

| Source | Finding | Application |
|---|---|---|
| [Shopify: color psychology](https://www.shopify.com/blog/color-psychology) | Published 27 January 2023. Colour associations vary with context, culture and audience; the article recommends testing. Its ecommerce conversion percentages are not evidence for educational outcomes. | Blue is a visual preference, not a promise of trust or better learning. Contrast, consistent roles and learner feedback determine whether it works. |
| [Figma: colour combinations](https://www.figma.com/resource-library/color-combinations/) | Harmony, lightness and contrast matter alongside hue. Analogous and complementary relationships serve different hierarchies. | Blue/aqua carry the ground; deep blue identifies actions. Warm peach and distinct skill colours have limited named roles. Semantic success/error colours retain text and shape cues. |
| [Figma: pricing-page best practices](https://www.figma.com/resource-library/pricing-page-best-practices/) | Simple choices, benefit-oriented labels, clear hierarchy, progressive disclosure, obvious CTAs and mobile usability reduce decision friction. | Apply these principles to starting choices and exam entry. Grove stays free; pricing tiers, decoys, urgency and conversion tactics do not enter the learning flow. |
| [Figma: web-design trends for 2026](https://www.figma.com/resource-library/web-design-trends/) | A broad trend guide covers depth, vivid colour, variable type, motion, dark mode, accessibility and lean delivery, alongside experimental navigation and maximalism. The page still contains forecast wording. | Use controlled depth, colour and theme support. Keep familiar navigation and the settled density; decorative motion and complex navigation would conflict with the learner's task. |

## Product and brand references

**Dropbox.** Its live [colour guide](https://brand.dropbox.com/color) separates
core, accents and greys. Its [icon guide](https://brand.dropbox.com/iconography)
separates 24px UI icons, 64px pictograms and larger spot artwork, and relates
their geometry to the typeface. [Typography](https://brand.dropbox.com/typography)
uses a flexible custom variable family. Adopt consistent roles and a distinction
between small utility marks and expressive skill marks; retain Grove's own
lettering, logo, colours and artwork.

**Meetup.** The [2025 redesign account](https://www.meetup.com/blog/new-design-2025/)
describes stronger colour, new icons and type, clearer spacing and contrast,
with familiar core navigation. Its [2026 roadmap](https://www.meetup.com/blog/2026-meetup-roadmap/)
states that mobile launched in December 2025 and proposes a unified member and
organizer app. These are dated publisher accounts, not verification of every
roadmap item. Grove adopts coherence across skills and devices, with less
duplicated navigation, rather than collecting more separate tools.

**Airbnb and Bend.** Airbnb's [2025 release screens](https://news.airbnb.com/product-releases/airbnb-2025-summer-release)
use expressive object imagery to distinguish major destinations. [Bend's live
site](https://bend.com/) shows restrained illustrated routines, a clear current
step and short instructions. Borrow recognizable silhouettes, restrained
colour and a focused task. Grove's small navigation pictograms are original
vector geometry; they are not copied competitor artwork or photorealistic 3D.

**Apple.** Current [material guidance](https://developer.apple.com/design/human-interface-guidelines/materials)
places Liquid Glass in the functional navigation/control layer and advises
sparing use, distinct from ordinary content surfaces. Grove is a web app, so
its frosted effect uses CSS blur and transparency, not Apple's native optical
rendering. Navigation has a high-opacity tint, opaque fallbacks, reduced
transparency and forced-colour support; learning content remains solid.

## Design and icon references

- [Nielsen Norman Group](https://www.nngroup.com/articles/ten-usability-heuristics/):
  usability principles, status visibility, recognition, recovery and user control.
- [Mobbin](https://mobbin.com/): published real-app screens and flows for comparing
  onboarding and navigation; screenshots do not prove a pattern's effectiveness.
- [Awwwards](https://www.awwwards.com/): expressive brand, typography and motion
  inspiration; marketing-site experiments require judgment before use in lessons.
- [Figma Resource Library](https://www.figma.com/resource-library/): practical
  colour, hierarchy and design-system references.
- [Lucide](https://lucide.dev/), [Tabler](https://tabler.io/icons) and
  [Phosphor](https://phosphoricons.com/?size=64&weight=duotone): current scalable
  icon systems compared. Grove keeps its small cached Phosphor subset and adds
  four dedicated skill pictograms, avoiding a second full icon dependency.

## Acceptance and remaining release work

Readable copy in both themes, working keyboard/touch controls, clear recovery
and no horizontal overflow are the acceptance bar. Familiar navigation and one
obvious next action matter more than following every visual trend. A colour or
visual style is not evidence of improved learning.

The current app supports Russian explanations. Expanded beginner sequencing and
reviewed English/Ukrainian instruction remain release work; the onboarding
recommendation is not a certified CEFR result. Source access, attribution and
integration details belong in [sources.md](sources.md) and
[source-integrations.md](source-integrations.md). Verification is described in
[testing.md](testing.md); product commitments are in [PRODUCT.md](../PRODUCT.md).
