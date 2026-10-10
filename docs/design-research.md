# Design research and decisions

Snapshot: **10 October 2026**. This record holds the audit of the current
screens, the references behind the redesign and the reasons for each choice.
The specification itself is [DESIGN.md](../DESIGN.md); current capabilities are
in [status.md](status.md), structure in [app-structure.md](app-structure.md).
Published sources inform the design; none of them establishes that a visual
style improves learning.

## Audit of the current screens

**Method.** `main` at `01fdce2`, served locally with reference data only, in a
guest sandbox after choosing *Alustan algusest*. Chromium through Playwright at
390×844 (touch) and 1280×800, light and dark: Kodu (`#path`), Kursus
(`#course`), `#session/obj-case` at its learn step, an item awaiting an answer
and a revealed miss, and `#rule/obj-case`; also `#start` as a new guest first
sees it. Screenshots are not committed (images are outside this record's
files); the routes reproduce them.

| Screen | Finding | Effect | Decision in DESIGN.md |
|---|---|---|---|
| Kodu | A generic title (*Õpime eesti keelt*), the date, a white card with the next topic, two tertiary links and a note restating that the skills exist. | No session shape; ADR-0009's one Jätka with two reasoned alternatives has nowhere to live. | Täna |
| Kodu, phone | The header holds the brand, a *Kursus* link wrapping to three lines, two icon buttons and *Veel*. | Five targets compete in 390px; the page title moves below. | Header |
| `#start` | The page heading draws the 3px focus ring after load (programmatic focus). | A large blue box around a non-interactive heading. | Focus and the dock, item 6 |
| Kursus | Thirty identical collapsed unit rows; metadata as middle-dot strings ("sihttase A1 · 0 из 4 пройдено") wrapping beside the title on phones; B1 unit numbers turn blue with no stated meaning. | A long list with no current position and no primary action. | Kursus |
| Kursus, phone | Topic rows spend 70px on a status-word column; *Õpi* and *Veel* are small buttons in each row. | Names truncate; actions are hard to hit. | Kursus |
| Session, learn | A readable sheet, but Estonian examples inside Russian are italic. The bundled Geologica has no slant axis (rendering `slnt` and `CRSV` changed nothing), so the browser synthesizes an oblique. | Faked italics, the "italic accent word" default. | Forbidden defaults; Typography |
| Session, practice | About 150px of blank space between the beads and the sentence; the lemma appears twice (in the instruction and the task line); "1 / 5" repeats the beads; *Tõlge* sits between the sentence and the field. | The answer field starts low; the eye travels sentence → button → field. | The session |
| Session, revealed | The disabled *Kontrolli* stays a pale primary beside the new *Edasi*; on 390px *Edasi* needs a scroll and the skill tray covers the bottom of the correction. | Two primary-looking buttons; the next action is hidden. | Practice rhythm; the dock |
| Session, revealed | The correction "✕ vale → rahakotti" is a separate line under the field; the sentence shows the key in colour but not its form. | The learner must connect three places to learn one form. | The signature: interlinear word |
| Session | Three equal labels *Õpi / Harjuta / Kontrolli* with a peach underline. | ADR-0009's session has seven steps. | Session line |
| Rule | A 720px sheet with a close cross although it is a page; gist, summary, seven points, a form table cut off at the sheet's edge, examples, mistakes, texts; sources and *Harjuta* at the end (about 2,000px down at 1280, 3,200px at 390). | A wall of text; attribution and the primary action are out of reach. | Reegel |
| Rule | The "Частая ошибка" card is the unsourced kind of tip ADR-0009 retires. | An unsourced claim on screen. | Reegel |
| All | Every label has a 12px Russian gloss on its own line; desktop navigation items are 74px tall. | Doubled vertical rhythm and visual noise. | Header (one baseline on desktop; phone tabs keep both lines) |
| All | Pale blue wash, frosted navigation, white cards. | Reads as a generic 2021–23 SaaS kit and has no relation to the name; the glass imitates material iOS draws natively. | Colors; Elevation and shape |
| All | Weights 500–600 and sizes 12–16px for most text; the Estonian cut at `SHRP` 40 is barely distinguishable from 0 at text sizes. | Weak hierarchy; the two voices do not read. | Typography |
| All | The current bead pulses forever; skeletons shimmer; a celebration overlay with petals; charts grow on load. | Motion without an action or a state change. | Motion (removed list) |

The audit found the learning rhythm sound — one item, a correction kept until
*Edasi*, skips distinct from mastery — and its presentation weak. The redesign
therefore keeps the rhythm and replaces the presentation.

## Decisions

**Interlinear as the signature.** Klint teaches which form a word takes. Code
already names that form for every keyed item (the form label, the rule's form,
Vabamorf's analysis), so showing it under the word costs no new linguistic data
and invents nothing. It moves the correction to where the learner is looking
and, shown only after an attempt, fits ADR-0009's evidence that corrective
prompts asking for self-correction outperform recasts. The convention is the
linguist's interlinear gloss ([Leipzig Glossing Rules](https://www.eva.mpg.de/lingua/resources/glossing-rules.php)),
adapted: Estonian term names in lower case instead of small-caps abbreviations,
which would be opaque to learners and are all-caps labels.

*Considered and set aside:* a "seam" marking the boundary between stem and
ending. Vabamorf reports a zero ending for the genitive singular and for many
partitives (*leiva*, *jäätise*) — exactly the forms of `obj-case`, the
documented weakness — so the seam would be missing where it matters most. It
can return as a refinement where Vabamorf separates a non-zero ending.

**Spruce ink on birch ground.** Cool, faintly green neutrals — the klint's pale
limestone and the spruce on its top — tie the screen to the name without a
picture and are clearly not the cream default.
The primary action takes the ink colour: the most legible fill on the page,
and it leaves every hue free for learning state. Lake blue stays for links,
focus and selection, the convention learners expect. *Considered:* keeping the
deep blue action; set aside because it then competes with links and focus and
keeps the generic look the owner calls outdated.

**No glass on the web.** Apple places Liquid Glass in the functional navigation
layer, drawn by the system ([materials](https://developer.apple.com/design/human-interface-guidelines/materials)).
On the web, CSS blur only imitates it and needs three fallbacks. The iOS app
will get the real material for free; the web uses opaque surfaces.

**A dock with three states.** The brief asks for one fixed primary action and
focus that the phone's skill tray never hides. iOS 26 answers the same problem
with a floating tab bar that minimises on scroll and a bottom accessory above
it that moves inline when the bar minimises ([WWDC25 session 284](https://developer.apple.com/videos/play/wwdc2025/284/)).
Klint's browse, act and task states follow that model, so the web and the
future app behave alike.

**The name: Klint.** The earlier name, Grove, collides with a company that
holds grove.ee. The owner ruled out Estonian common words and word mashups;
candidates were checked on 10 October 2026 against the `.ee` registry
(whois.tld.ee), the `.app` registry (Google's RDAP service) and a web search
for apps and companies. Klint — the Baltic Klint, the limestone escarpment of
north Estonia running through Ida-Virumaa, where many of the learners live —
had a free `klint.ee` (`klint.app` is registered) and no clashing app or
company; it reads the same in Russian, Ukrainian and English. A Business
Register and trademark search remain for the owner before the domain is bought.
The mark is the design's own signature: a K with the interlinear bar, which is
also the shore line under the cliff. Leaf and cliff silhouettes were drawn and
set aside: at 16px they read as a boot, a folder or a stock stairs icon.

**Default explanation language from the system.** Learners arrive with a
phone or browser already set to their language; asking before showing anything
costs the first minute ADR-0009 protects. The first preferred language that is
Ukrainian, Russian or English is preselected, English otherwise, and a saved
choice always wins. Location is not used: in Estonia it says nothing about
which of the three languages a person reads.

**Täna for Home.** ADR-0009 makes Home the session; *Täna* ("today") names
what the learner gets there.

**The answer typed in the sentence.** The gap becomes the field, so the
sentence, the answer and the correction share one line of sight. Automatic
sizing uses `field-sizing: content`, Baseline since Firefox 152 joined Safari
26.2 and Chromium ([web.dev, June 2026](https://web.dev/blog/web-platform-06-2026)),
with a `size` fallback.

**Seven steps under three phases.** ADR-0009's steps are the session's real
structure; *Õpi / Harjuta / Kontrolli* remain the labels learners already know.

**Sharper Estonian.** `SHRP` 100 at display and prompt sizes was rendered next
to 0 and 40: the cut shows at the terminals of *k*, *t* and the tail of *Щ*.
At 40 the difference disappears at text sizes, so running Estonian moves to 60.

**Bringhurst's scale and measure.** Sizes 12–48px from the classic typographic
scale and the 45–75 character line (66 ideal) from *The Elements of
Typographic Style*.

**Validation before writing.** A throwaway HTML mock of Täna, an item (awaiting
and revealed), the rule page and Kursus was rendered at 390 and 1280px in both
themes. It showed that a form line widening its word breaks the sentence's
spacing (now absolutely positioned), that a struck wrong answer inside the
sentence wraps at 390px (now in the correction region), and that repeating the
step name beside the phase labels was noise (now shown once per step). The mock
is not committed.

## Platform and standards references

| Source | Finding | Application |
|---|---|---|
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Contrast 4.5:1 text and 3:1 non-text (1.4.3, 1.4.11); focus not entirely hidden (2.4.11, AA) and not hidden at all (2.4.12, AAA); dragging alternatives (2.5.7); 24px minimum targets (2.5.8); consistent help (3.2.6); accessible authentication (3.3.8); the relative-luminance formula. | The contrast table, the focus rules for the dock, tap-only tile building, 44px targets, fixed places for *Miks?* and *Reegel*. |
| [Vispero: testing 2.4.11](https://vispero.com/resources/how-to-test-2-4-11-focus-not-obscured-minimum/), [TabNav: 2.4.11](https://tabnav.com/academy/wcag/success-criterion-2.4.11) | Sticky footers are the usual failure; `scroll-padding` and `scroll-margin` give focus room. | `scroll-padding-bottom` tied to the dock's measured height. |
| [Apple HIG: Motion](https://developer.apple.com/design/human-interface-guidelines/motion), [App Store reduced-motion criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/reduced-motion-evaluation-criteria) | Motion should communicate and never be the only carrier of information; scaling, spinning and peripheral motion need alternatives. | Motion inventory with reduced-motion fallbacks; no shake, spin or overlay. |
| [Material 3 easing and duration tokens](https://m3.material.io/styles/motion/easing-and-duration/tokens-specs) | Standard `cubic-bezier(.2,0,0,1)`, emphasized decelerate `(.05,.7,.1,1)` and accelerate `(.3,0,.8,.15)`; short durations for small changes. | Motion tokens, capped at 320ms. |
| [Chrome: view transitions in 2025](https://developer.chrome.com/blog/view-transitions-in-2025), [web.dev, October 2025](https://web.dev/blog/web-platform-10-2025) | Same-document View Transitions are Baseline since Firefox 144 (14 October 2025). | The next-item transition, with plain replacement as fallback. |
| [MDN: VirtualKeyboard API](https://developer.mozilla.org/en-US/docs/Web/API/VirtualKeyboard_API), [Chrome: VirtualKeyboard](https://developer.chrome.com/docs/web-platform/virtual-keyboard), [WebKit bug 230225](https://bugs.webkit.org/show_bug.cgi?id=230225) | Not Baseline; Safari keeps a full-height layout viewport; `interactive-widget=resizes-content` is Chromium's. | The dock follows `visualViewport` on Safari and the viewport meta on Chromium. |
| [Safari 26 release notes](https://developer.apple.com/documentation/safari-release-notes/safari-26-release-notes) | CSS anchor positioning and scroll-driven animations ship. | Desktop popovers may anchor to their control; scroll-driven animation is not used for decoration. |
| [SwiftUI tab bars on iOS 26](https://www.donnywals.com/exploring-tab-bars-on-ios-26-with-liquid-glass/), [Apple forums: bottom accessory collapse](https://developer.apple.com/forums/thread/809945) | `tabViewBottomAccessory` is app-wide and collapses only with long scroll content. | On iOS the session is a full-screen flow with its own bottom bar; other screens use a per-screen inset. |
| [Design Tokens specification 2025.10](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/) | First stable, vendor-neutral token format with theming. | One token source for CSS and the iOS asset catalog. |

## Language-learning references

Snapshot 3 October 2026, from official product pages, support guides and
publisher material; native apps and subscription accounts were not tested.

| Product | Verified public experience | Useful adaptation for Klint | Tradeoff to avoid |
|---|---|---|---|
| Duolingo | A guided course path plus on-demand speaking, listening, mistakes and word practice. | A strong next lesson, easy review of prior material, direct skill practice. | A long path or reward systems must not obscure the next action. [Practice guide](https://blog.duolingo.com/guide-to-duolingo-practice-hub/), [course navigation](https://blog.duolingo.com/how-to-review-lessons-on-duolingo/) |
| Babbel | A placement quiz recommends a course; review mixes flashcards, writing, speaking and listening. | Editable starting point; one practice system with several exercise types. | Do not expose every method as its own page. [Placement](https://support.babbel.com/hc/en-us/articles/20202703767442-Placement-quiz), [review](https://support.babbel.com/hc/en-gb/articles/205600228-Vocab-workout-Review) |
| Busuu | Placement suggests an entry level with the option to begin earlier. | Course position and completion stay separate. | Navigation choices do not award mastery. [Placement](https://help.busuu.com/hc/en-us/articles/16526383831569-What-is-a-Placement-Test) |
| Drops | Reversible hiding of words; Review Dojo explains when no review is needed. | Undoable word choices; useful empty states. | Skips advance navigation and stay distinct from completion. [Hide/unhide](https://support.languagedrops.com/hc/en-us/articles/19405567894419-How-do-I-hide-or-unhide-words), [Dojo](https://support.languagedrops.com/hc/en-us/articles/19334419328275-Dojo-Feature-What-is-it-and-How-to-Review-Words) |
| Speak | A learn–practise–apply sequence places speaking in situations; tutor lessons give hints and repetition. | A speaking goal, an example and a suggested reply before a beginner talks. | Open chat alone is not a beginner curriculum. [Method](https://www.speak.com/), [September release](https://www.speak.com/blog/live-tutor-lessons-powered-by-openais-gpt-live-1) |
| Praktika | A February 2026 redesign with system dark mode, improved VoiceOver and goal-based scenarios. | Clear scenario choices; accessible controls. | Animated tutors must not gate a useful session. [4.0 release](https://praktika.ai/blog/praktika-4-0) |
| Langua | A recommended Path beside an Explore route; recovery from stalled chats. | Guided by default, flexible by choice; preserve work when a provider fails. | Beta announcements are not universal availability. [Updates](https://support.languatalk.com/article/152-see-the-latest-updates-on-langua) |
| LingQ | A reader combining audio, word lookup, sentence view and review; Continue Studying. | Keep text, audio and vocabulary together; resume the actual material. | A large library is not a novice's first decision. [Reader](https://www.lingq.com/en/ios-app-support/) |
| Lingvist | Adaptive vocabulary in contextual sentences with scheduled repetition. | One compact exercise, then actionable feedback. | Vocabulary coverage is not a CEFR test. [Product](https://lingvist.com/) |

The strongest references remain Babbel and Busuu for entry, Duolingo for a
next lesson plus targeted practice, Drops for reversible choices,
Speak/Praktika/Langua for supported speaking and LingQ for real material across
skills. Usability research supports showing frequent tasks first and revealing
detail on request ([progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/)),
making differences between options explicit ([explicit differences](https://www.nngroup.com/articles/explicit-differences/))
and teaching controls in context rather than in a tour
([onboarding tutorials](https://www.nngroup.com/articles/onboarding-tutorials/)).

## Estonian-specific reference: Sõnastik

The [App Store listing](https://apps.apple.com/ee/app/s%C3%B5nastik-learn-estonian/id6764018075)
describes Ekilex-backed lookup, five translation languages, saved words,
flashcards, typed forms and EVS example phrases; the
[website](https://www.sonastik.app/en) shows meanings and declension views.
These are vendor claims, not verified outcomes.

**Klint's distinction is the learning journey:** an entry choice leads to a
lesson, checked practice, a correction the learner can understand and a next
action, across four skills, with optional exam preparation. Dictionary lookup
serves the current text or exercise. Adaptations that fit: meaning and a usage
example before a large form table; the learner's place preserved when a lookup
closes; tolerant matches resolved visibly so they never become a correct drill
answer; one review queue. Klint already imports EVS examples and supports
optional Ekilex lookups beside Vabamorf forms ([sources](sources.md),
[integrations](source-integrations.md)); Sõnastik's service and artwork are not
needed. A vendor's word-percentage presentation is not adopted as a
proficiency score.

## Acceptance

A separate reviewer session scores the redesign on design quality,
originality, craft and function before it is accepted. The bar it checks:
every forbidden default absent; one primary per screen in its fixed place;
every result carried by a word and a shape as well as colour; the contrast
table holding in both themes; focus never under the dock at phone sizes in
both orientations; reduced motion, forced colours and keyboard use complete;
no horizontal page scroll at 320px; source attribution visible near the top of
rules and texts. English and Ukrainian instructional support and the complete
beginner path remain content work; the design prepares for them and does not
establish them.
