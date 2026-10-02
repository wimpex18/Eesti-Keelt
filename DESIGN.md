---
name: Grove
description: Grove — a little room to grow your Estonian, in Estonian blue, black and white.
colors:
  estonian-blue: "#0030de"
  paldski: "#0062f5"
  liivi: "#000087"
  narva: "#00c3ff"
  parnu: "#cee2fd"
  haapsalu: "#fceec8"
  mustkivi: "#0f172a"
  majakivi: "#3d4b5e"
  kabelikivi: "#566376"
  pahkla: "#f1f5f9"
  page: "#f8fafc"
  sheet: "#ffffff"
  line: "#e2e8f0"
  sammal: "#17804f"
  johvikas: "#cc2f45"
  murakas: "#955400"
  murakas-mark: "#f0a020"
  jarv: "#0b7285"
typography:
  family: "Geologica (variable: weight 300–800, sharpness SHRP 0–100), system fallbacks"
  interface: "Geologica, SHRP 0 (soft)"
  material: "Geologica, SHRP 55 (cut) — every Estonian sentence, answer, word and title"
  hero: "clamp(38px, 9vw, 60px) / 600"
  title: "28px / 700"
  prompt: "24px, 28px from 720px"
  reading: "19px / 1.8"
  answer: "18px / 500"
  body: "16px"
  ui: "15px"
  note: "14px"
  meta: "12px"
  gloss: "12px"
rounded:
  control: "999px (buttons, switches, tabs)"
  field: "16px"
  sheet: "24px"
  hero: "32px"
  glass-dock: "30px"
spacing: "4px scale: --s1 4 · --s2 8 · --s3 12 · --s4 16 · --s5 24 · --s6 32 · --s7 48"
---

# Design System: Grove

## Overview

**North star: "Laudtee" — the existing boardwalk learning-path metaphor.**
Estonian bogs are crossed on boardwalks, plank after plank, each laid before the next can be
walked. The path to the exam is built the same way: a topic is a plank, laid
only when code has checked the learner's answers. The metaphor draws the path,
the progress and the rewards, and keeps the product honest.

**Grove is the app’s name: a small wood, with a quiet connection to Estonia’s forests.**
The original mark is a curved leaf with a short stem, from
`eesti/web/brand/mark.svg`. The subject descriptor **Eesti keel · A2/B1** appears
in metadata and the phone launch passage; the header shows only the name. The
identity stays the same across explanation languages. The cornflower remains
the readiness illustration for contact with the four exam parts; it is not the
app icon.

The ground is **near-white, cool and quiet** (`#f8fafc` page, white sheets),
never cream. The colour is **Estonian blue** from Brand Estonia (`#0030DE`),
with its partners Paldski, Liivi, Narva and Pärnu, black text (Mustkivi) and
white. One warm note, Haapsalu sand, is reserved for rest and reward. Colour
otherwise belongs to an information role, never to a language.

The interface follows **Apple's Liquid Glass rule of two layers**: navigation
and what floats over content sit on glass (the spine, the phone dock, the word
card, the celebration) and a selection glides between tabs on one capsule;
content sits on the plain page, separated by lines rather than cards. The
switches choose content, so their track is solid. Glass turns solid
with `prefers-reduced-transparency` or `prefers-contrast: more`. A previously
saved `glass=off` preference is still honoured; the header now exposes profile
and theme actions.

One typeface, **Geologica** (Monokrom, OFL), self-hosted under
`eesti/web/fonts/`. The interface is set soft; Estonian material is set in the
same face at a sharper cut (`--cut`, SHRP 55), so it reads as material without a
second family. Icons are **Phosphor** (MIT), inlined in `eesti/web/js/icons.js`:
one line style: Phosphor regular outlines (the duotone fill is hidden) for navigation and marks at 20–24px, and bold for the small glyphs inside buttons.

## Colors

Tokens live in `eesti/web/app.css` (`:root`), mirrored for dark under
`prefers-color-scheme: dark` and `[data-theme="dark"]`.

| Role | Token | Light | Dark | Meaning |
|---|---|---|---|---|
| Estonian blue | `--accent` | #0030de | #00c3ff (Narva) | Action text, selection, focus, "now", readiness petals |
| Button fill | `--btn` / `--btn-2` | #0030de → #0062f5 | #0062f5 → #2f7bff | Prominent buttons, with white text |
| Liivi | `--accent-deep` | #000087 | — | Tinted-button text, hover |
| Accent mist | `--accent-soft` | #e6eefd | #0c2544 | Selected fills, next-step strip |
| Narva | `--sky` | #00c3ff | #00c3ff | Light in the hero, chart glow |
| Haapsalu | `--sand` | #fceec8 | #e8d9ae | Rest and reward, sparingly |
| Sammal | `--good` | #17804f | #4fcb8c | Right answer, mastered |
| Jõhvikas | `--bad` | #cc2f45 | #ff7d8c | The wrong form; kept rare |
| Murakas | `--warn` / `--warn-fill` | #955400 / #f0a020 | #f5b451 | Caution, untouched exam part, `obj-case` |
| Järv | `--gloss` | #0b7285 | #52d0da | What a word means, and only that |
| Mustkivi | `--ink` | #0f172a | #eef2f8 | Text |
| Page / sheet | `--bg` / `--panel` | #f8fafc / #ffffff | #0b1120 / #131c2e | Page and content sheets |
| Daylight | `--hero-bg` + `--hero-rim` | #d9e8fc → #e8f1fc → #f6efdc | #1b2842 → #2a2d38 | The hero: a pale sky settling into sand, with a glass rim; ink text, a blue "now" |
| Evening | `--night-a/b` | #0b1433 → #142257 | #101a33 → #16224a | The celebration card: a Baltic evening with Narva light |
| Glass | `--glass` + `--glass-lift` | white 64% | slate 62% | The navigation layer: a white specular line on top, light caught again at the foot, a darker outer edge (iOS 27) and a soft shadow |

**Colour by role.** Blue acts, moss is right, cranberry is wrong, cloudberry
cautions, lake means. Russian text is never coloured for being Russian.
**Never hue alone.** Every coloured state also has a shape: node icons,
filled, empty or hatched petals, a glyph per plan block, beads that stay.

The inline brand mark uses `--accent`, so it follows both themes. Installed
icons and social artwork use the fixed Estonian-blue identity with a white
mark; the launch cover uses the current page's `--bg`, `--ink` and `--accent`.

## Typography

- **Brand name** (650, 28px; 26px in the spine; soft): Geologica with −0.03em
  tracking, alongside a 48px mark. The header has no subject subtitle. The phone
  launch name is 32px/1.2, with the descriptor at 14px. Keep the name as text
  in the UI; generated wordmark and social SVGs carry outlined lettering.
- **Hero** (600, clamp 38→60px, cut): the current topic's name.
- **Title** (800, 30px): the page title, hidden on a phone where the tab row
  already names the place.
- **Prompt** (24px, 28px from 720px, cut): drill sentences. The blank is a blue
  rule that fills with the right form once graded.
- **Reading** (19px/1.8, cut, max 66ch): Lugemine prose; the reader's title up to 36px.
- **Answer** (18px/500, cut): answer fields. What the learner types is Estonian.
- **Lead / body / ui / note / meta / gloss**: 20 / 16 / 15 / 14 / 13 / 12px.
- Numbers that change in place use `tabular-nums`. Fields are at least 16px, so
  iOS never zooms on focus.

## Layout

- **Phone (<720px, and touch screens under 560px tall).** A top row with the mark,
  the name and two icon buttons; the open mode's tabs as a scrolling row where the
  selected tab sits on a small glass capsule; the page; and a **floating glass
  dock** of the three modes, clear of the home indicator (56px targets; the open
  mode is tinted blue). Scrolling down folds the dock to its marks; scrolling up
  or reaching the top unfolds it. The dock hides while typing or while the inline
  profile name editor is open, keeping Save/Cancel clear on WebKit. Gutter 16px plus
  safe areas.
- **Spine (≥720px and ≥560px tall; iPad mini).** A **floating glass sidebar**
  inset 12px from the window, 32px radius, fixed so the brand never scrolls away:
  brand, the three modes with glosses, the open mode's tabs, and the two actions
  at its foot. Below 1080px there is no rail, so Rada carries the **pulse**:
  three tiles (Kordamine due today, the exam flower, the four-week rhythm), each
  opening its own screen. On Rada an active set compacts the hero and comes before
  the plan and pulse, so the first answer remains above the phone dock.
- **Desk (≥1080px).** Spine 264px, a working column up to 880px, and a 320px
  context rail: the readiness flower, the next topic, the review forecast and
  the milestone seals. A rail card hides while its own panel is open.
- **iPhone landscape (touch, ≤500px tall).** One line of chrome; the hero and the
  pulse step aside while a set is on screen; a 44px dock. The brand keeps its
  48px mark and hides the name to leave room for the tabs.

## Controls

- **Brand / home link.** The 48px inline leaf and the single-line Grove
  name share a 44px-minimum home target to Rada (`#path`), with a 10px gap. The
  name stays ink on hover; the normal blue keyboard focus ring identifies the
  link. Preserve its Russian accessible home label and the Estonian language
  tag on the visible name.
- **Account / theme actions.** The 44px account link opens the existing Profiil
  screen (`#profile`). `eesti/web/js/profile.js` keeps the user-circle glyph
  in every account state. Its accessible **Profiil** label explains that guests
  can sign in or create an account. The adjacent theme button retains system/light/dark
  cycling. There is no transparency setting in the header.
- **Buttons are flat capsules, in four ranks.** *Primary* (`.go`, `.primary`):
  solid Estonian blue, no gradient, rim or glow; darker under the pointer. One per
  view — a started Sõnatrenn demotes Alusta. *Secondary* (`.ghost`, `.logbtn`,
  tutor offer): a neutral grey fill (`--ctl`, ink at 6%) with ink text. *Ghost*
  (`.linky`, Vihje): text only; `.quiet` is its neutral form for a secondary
  link inside a list row (Reegel on Kogu rada and over a running set). *Icon*:
  44px neutral circles, Phosphor glyphs, never a text character. Heights 44px,
  52px for a drill's answer action and the mic beside it. Disabled: 45% opacity. Blue is kept for the primary
  action, focus, selection, progress and "now" — never as a tint on a control.
- **Fields are outlined.** White with a 1px line at rest; on focus a blue edge and a
  3px blue halo. Labels sit above with the Russian
  gloss on the same line. The drill's answer field is 52px, spans the column, in the cut.
- **Form tables** (Reegel): lines, not boxes. Column heads in meta grey over an
  ink rule; row labels (cases, persons) stay pinned while the forms scroll
  sideways on a phone, with a soft edge showing there is more. A table whose
  first column is data (numerals) has no pinned labels.
- **Switches** (`.levels`): a grey track, the chosen state a white capsule.
- **The gliding selection** (`js/glide.js`). Every `role="tablist"` (the modes,
  each mode's tabs, the switches) carries one capsule that slides, with a slight
  spring, to the chosen tab, instead of one capsule vanishing and another
  appearing. It wears that list's selected look (glass pill in the tabs, grey in
  the dock, white in a switch). It jumps, not slides, when a list first shows, and
  it is instant under reduced motion. Without the script each tab paints its own
  capsule, so the page reads the same.
- **Phone navigation lens** (`eesti/web/js/glide.js`). The skill row and bottom
  modes use a press → slide → release gesture. A 140ms hold or 6px
  horizontal movement lifts a glass lens with an inert, `aria-hidden` copy of
  the labels at 1.12×. It follows the finger and scrolls near the row's edges to
  reach hidden skills. Preview never opens a panel or writes history; release
  activates the destination through the existing click/router. Cancel, Escape,
  lost capture on the list, resize or page hiding restores the current
  selection. A quick tap and keyboard navigation keep their ordinary behavior;
  other segmented controls retain the quiet glide. The gesture requires coarse
  pointer and no hover, at width ≤719px, or width ≤1079px and height ≤559px.
  Reduced motion removes magnification; solid glass fallbacks still apply.
- **Tab lists** — modes, tabs, Minu rada / Vaba harjutus, A2 / B1 — take arrows,
  Home and End, with only the selected tab in the Tab order.

## Signature components

- **Platform identity.** A 64×64 master supplies the inline header/launch mark,
  blue rounded favicon tile, platform rasters and social cards. Use the regular
  icon for unmasked contexts, the separately inset full-bleed artwork for
  maskable installation and Apple, and the single-colour silhouette for Safari
  pinning and monochrome contexts. Rebuild derivatives with
  `deploy/build-brand.py`; do not redraw a derivative independently. Provenance,
  output sizes and routes are in `docs/brand.md`.
- **Hero (Praegu).** A quiet daylight surface: a pale sky fading into Haapsalu
  sand under a white glass rim, a soft slate dusk in dark (no glows or contour rings)
  with a faint barn swallow (suitsupääsuke) gliding in the corner. It holds the
  resume topic, its Russian name and level, the **gate** (ten slots for the
  topic's last answers against 8 of 10), and the **boardwalk**.
- **Boardwalk (Laudtee).** An SVG plank path through a window of the curriculum
  around the resume topic (5–13 nodes by width). Mastered nodes are moss with a tick; the
  resume node is white with a slow halo; open nodes are outlined in Narva; theory
  is dashed. *Kogu rada* opens one vertical boardwalk per level.
- **Beads.** One per item in a set: waiting, now (pulsing), right, wrong. The end
  card repeats them.
- **Stage and drill.** A white sheet; one item at a time; the blank fills with
  the right form; the verdict shows the attempt struck through, the right form
  and the rule in Russian; a recorded miss offers *Selgita*. On a phone, earlier
  answers fold to their sentence and verdict.
- **Rukkilill, the readiness flower.** Four petals for the four exam parts, three
  segments each lighting one contact toward `contact_target`; Rääkimine hatched as
  unmeasured. Contact, never a prediction. On Ülevaade beside the verdict, and in the rail.
- **Rütm.** Twelve weeks of days, Monday at the top, in four tints of blue; the
  headline counts active days in the last four. Rest is simply light — nothing
  resets.
- **Forecast.** Cards coming due over fourteen days; today solid, later days
  lighter. In Järjekord, Edenemine and the rail.
- **Seals (Märgid).** The level's milestones as seals whose ring fills with the
  count and turns solid blue when complete. They award nothing.
- **Word card.** Floats over the text or list it came from, and always has a
  close button.
- **Player (Mängija).** Every `<audio>` in the app is drawn as one capsule: a
  round blue play button (a spinner while a stream loads), the time, a seek track
  filled to the playhead, the length, *−5* seconds (hidden under 420px) and a
  speed chip cycling 1× → 0.75× → 1.25×, remembered per device. It stays on one
  line; a recording that cannot play says so in Russian. The native element stays
  in the page, hidden, so the media code is unchanged.
- **Sõnatrenn.** In Sõnavara: ten words the learner marked *õpin* (topped up with
  the commonest new A1 words) shown by their Russian meaning; the learner types
  the Estonian, compared with the word list's spelling. *Vihje*, a quiet text action under the answer, reveals a letter
  at a time. It is a practice space on the page, not a card: heading, a thin
  progress line, the Russian meaning as the largest text, then the answer row. A miss shows the right word, its omastav/osastav when the list has
  them, a *Kuula* button and *Kordamisse*; the end card lists the misses. It
  records nothing — Kordamine owns memory.
- **Identity / sources footer.** Grove's meaning is explained in Russian:
  **маленькая роща: место, где растёт твой эстонский.** A separate **© [year] Grove**
  line uses the current UTC year supplied by `eesti/api/assets.py`; it names no
  person or company. **Allikad** retains source credits and loads the source list on first opening.
- **Reader source.** One line above the title: *Allikas* and the source's name,
  linked to the original. Source credits remain in the sources footer.
- **Plan strip.** Inside **Täna**, the day as time: a segment per block as long as
  its minutes, coloured and glyphed by kind. Its summary also reports how many
  evidence-backed daily steps are complete.
- **Tänased sammud.** Three small boardwalk-shaped checks on Rada, computed from
  today's evidence: drill attempts, cards actually due, and one skill contact.
  They may be done in any order; an empty queue is complete and a missed day
  removes nothing. They live inside **Täna** with the generated time plan, so
  evidence and recommendations read as one system. No points, streak or mastery
  are attached.
- **Set completion.** The score, beads and missed sentences close the block. On
  Minu rada the primary action continues into the next incomplete block from
  today's plan; another set remains a secondary choice. Vaba harjutus stays
  self-contained and records nothing.
- **Starting recommendation.** Two optional, solid-sheet account screens: a
  self-assessed start band and one preferred first lane. A two-plank marker is
  the only progress decoration. Completion marks the recommended destination,
  selects a suitable word filter and opens real work; it never skips curriculum
  topics or presents the choice as confirmed CEFR evidence.
- **Celebration.** Mastery only: a flower blooms on an evening card, announced
  through the page's polite live region. Any key or tap dismisses it; under
  reduced motion only the announcement remains.

## Layout rhythm

One left edge per column. Exercises (drills, Sõnatrenn, Kordamine cards, the
checkpoint, dictation, the readiness bloom, progress stats) share one treatment:
on the page, ruled by a 1px line above, no card fill. The meta line (position,
form, level) sits above the answer; the answer spans the column. Section heads
open with a rule and 24px. Lists (words, library) are hairline rows, not tiles. A
filter row's apply button is secondary. Text: 12 gloss/meta · 14 note/hint ·
16 body · 20 section · 28 title and big numbers · 40 score.

## Depth

Content sheets are separated by a 1px line (`--shadow` is a hairline ring), not a
drop shadow. Only the floating glass layer (spine, dock, and the word card over
the text it glosses) casts a soft shadow. The page has no background
glows. The root (`html`) carries the page colour as well as `body`: Safari 26
ignores `theme-color` and tints its toolbars and the overscroll from it.

## Adding a page or section

Glass is not something a new screen chooses; it comes from where the thing sits.

- **Content** (a new panel, list, exercise, reader): on the plain page, in the
  shared treatment under Controls, never glass. No new shadow or card fill.
- **Navigation that floats over content** (a new bar, dock or sidebar): give it
  the `.glass` class. It then takes `--glass`, the blur and `--glass-lift`, turns
  solid under reduced transparency, higher contrast or the retained `glass=off`
  preference, and follows both themes. Never copy the recipe into a new rule.
- **A card that floats over the content it explains** (like the word card over
  its text): glass as well, by adding it to the `.glass` rule's selector list
  in `app.css`, as `#wordCard` is; the fallbacks come with it.
- **A choice between views** (tabs, a segmented switch): mark it up as
  `role="tablist"` with `role="tab"` children and `aria-selected`. It then gets
  the gliding capsule and the arrow-key pattern with no extra code, including
  when it is added to the page later. Give it a selected look of its own in
  `app.css` for the no-script case, and a `.glide` colour at the end of the file
  if that look is new.
- A new floating layer that must not follow this belongs in this document
  first.

## Motion

140ms response, 240ms state change, 420ms arrival, `cubic-bezier(.22,1,.36,1)`.
Beads pop, petals grow in turn, the plan strip and the forecast rise, verdicts
drop into place, the resume node breathes, the swallow glides. Under
`prefers-reduced-motion` every animation, delay and transition collapses and
script scrolling stops being smooth.

**Phone launch passage.** On eligible coarse-pointer, non-hover phones, the
leaf unfolds from its stem over 560ms after a 40ms delay. The name rises
6px and fades in over 360ms from 160ms. The cover fades for
180ms after 720ms, completing at 900ms with `--ease`; CSS supplies its own
deadline and the inline script removes it. It never waits for a font, app
module, data or network response. A tap or key dismisses it immediately.

Eligibility is width ≤719px, or width ≤1023px with height ≤559px, always with
`pointer: coarse` and `hover: none`. Desktop and tablet open directly. Reduced
motion, prerendering, history restoration and same-origin navigation skip
the passage (an explicit reload can show it). With JavaScript unavailable the
cover remains hidden. Saved theme and transparency are restored before body
paint independently of the passage; the cover is inert and hidden from
assistive technology, and never traps focus.

## Do's and Don'ts

**Do:** use tokens for every colour and the `--s1`…`--s7` scale; keep glass on
the navigation layer (`.glass`, `--glass-lift`) and content on solid sheets; build
every choice between views as a `role="tablist"` so it glides; keep Estonian material in the
cut; keep 44px touch targets; check 1440×900, 402×874, 874×402 and 744×1133 in
both themes; keep the leaf identity distinct from readiness evidence.

**Don't:** use cream or grey-beige grounds; put paragraph text or drill inputs on
glass; copy the glass recipe or hand-roll a selection capsule; add SVG refraction
or displacement filters to navigation; fill more than one or two buttons per
view; add streaks, points or a single readiness percentage; celebrate anything but code-decided mastery; colour text by
its language.
