---
name: Grove
description: Practice rhythm — pale blue ground, frosted navigation and solid learning surfaces.
colors:
  bg: '#f0f6fd'
  bg-2: '#e7f1fb'
  panel: '#ffffff'
  raised: '#ffffff'
  ink: '#172f4b'
  ink-2: '#34506f'
  muted: '#506681'
  line: '#c8d8eb'
  line-soft: '#e0e9f4'
  tint: '#e6effb'
  nav: '#e5efff'
  on-nav: '#172f4b'
  nav-muted: '#435f80'
  nav-active: '#cfe0fa'
  btn: '#2359c4'
  on-btn: '#ffffff'
  accent: '#2359c4'
  accent-deep: '#17469e'
  accent-soft: '#e3edff'
  coral: '#bd6540'
  good: '#226647'
  good-soft: '#e5f3ea'
  bad: '#aa3247'
  bad-soft: '#fce9ee'
  warn: '#835100'
  warn-soft: '#fff1d8'
  gloss: '#176b76'
  skill-blue: '#2359a8'
  skill-blue-soft: '#a9cdfa'
  skill-teal: '#09646b'
  skill-teal-soft: '#9ddade'
  skill-violet: '#6946a3'
  skill-violet-soft: '#d1b9f5'
  skill-amber: '#865214'
  skill-amber-soft: '#f9d49b'
  dark-bg: '#152236'
  dark-bg-2: '#1a2b42'
  dark-panel: '#20334c'
  dark-raised: '#293e59'
  dark-ink: '#edf4ff'
  dark-ink-2: '#cfddf2'
  dark-muted: '#b3c5de'
  dark-line: '#496380'
  dark-line-soft: '#364f6e'
  dark-tint: '#2a4161'
  dark-nav: '#20344f'
  dark-on-nav: '#edf4ff'
  dark-nav-muted: '#c1d3ed'
  dark-nav-active: '#334f75'
  dark-btn: '#aac9ff'
  dark-on-btn: '#16345e'
  dark-accent: '#aac9ff'
  dark-accent-deep: '#d1e1ff'
  dark-accent-soft: '#304a70'
  dark-coral: '#ffbd9e'
  dark-good: '#b0e3c4'
  dark-good-soft: '#214934'
  dark-bad: '#ffb7c7'
  dark-bad-soft: '#543044'
  dark-warn: '#f4d28d'
  dark-warn-soft: '#493d26'
  dark-gloss: '#b0e4e7'
  dark-skill-blue: '#a9cdff'
  dark-skill-blue-soft: '#456daa'
  dark-skill-teal: '#a9e3e5'
  dark-skill-teal-soft: '#33757b'
  dark-skill-violet: '#d8c4ff'
  dark-skill-violet-soft: '#6b5299'
  dark-skill-amber: '#ffdb9e'
  dark-skill-amber-soft: '#906a34'
typography:
  display:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: clamp(28px, 3vw, 40px)
    lineHeight: 1.2
    letterSpacing: -0.025em
  headline:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.025em
  title:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 20px
    lineHeight: 1.2
    letterSpacing: -0.025em
  prompt:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 24px
    lineHeight: 1.5
    letterSpacing: -0.005em
    fontVariation: '"SHRP" 40'
  reading:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 19px
    lineHeight: 1.8
    fontVariation: '"SHRP" 40'
  answer:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 18px
    fontWeight: 500
    fontVariation: '"SHRP" 40'
  body:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
    fontVariation: '"SHRP" 0'
  label:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 15px
    fontWeight: 600
    lineHeight: 1.25
  note:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 14px
    lineHeight: 1.55
  metadata:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 12px
    fontWeight: 400
rounded:
  r-xs: 8px
  r-sm: 12px
  r: 16px
spacing:
  s1: 4px
  s2: 8px
  s3: 12px
  s4: 16px
  s5: 24px
  s6: 32px
  s7: 48px
components:
  button-primary:
    backgroundColor: '{colors.btn}'
    textColor: '{colors.on-btn}'
    typography: '{typography.label}'
    rounded: '{rounded.r-sm}'
    padding: 12px 24px
  button-primary-hover:
    backgroundColor: 'color-mix(in srgb, #2359c4 88%, #172f4b)'
  button-secondary:
    backgroundColor: '{colors.tint}'
    textColor: '{colors.ink}'
    typography: '{typography.label}'
    rounded: '{rounded.r-xs}'
    padding: 10px 20px
  button-quiet:
    backgroundColor: transparent
    textColor: '{colors.ink-2}'
    rounded: '{rounded.r-xs}'
    padding: 4px 8px
  segmented-control:
    backgroundColor: '{colors.tint}'
    textColor: '{colors.muted}'
    rounded: '{rounded.r-sm}'
    padding: 4px
  segmented-control-selected:
    backgroundColor: '{colors.panel}'
    textColor: '{colors.ink}'
    rounded: '{rounded.r-xs}'
  field:
    backgroundColor: '{colors.panel}'
    textColor: '{colors.ink}'
    typography: '{typography.body}'
    rounded: '{rounded.r-sm}'
    padding: 10px 16px
  skill-navigation:
    backgroundColor: '{colors.nav}'
    textColor: '{colors.on-nav}'
    rounded: '{rounded.r}'
  recommendation-chip:
    backgroundColor: '{colors.accent-soft}'
    textColor: '{colors.accent}'
    rounded: 999px
    padding: 2px 8px
  task-sheet:
    backgroundColor: '{colors.panel}'
    textColor: '{colors.ink}'
    rounded: '{rounded.r}'
    padding: 24px
  step-strip:
    textColor: '{colors.muted}'
    typography: '{typography.body}'
    padding: 0 0 12px
---

# Design System: Grove

## Overview

**Creative North Star: "Practice rhythm"**

Grove is a calm working place for learning Estonian. A pale blue/aqua wash opens
the working area, frosted blue navigation gives the app a stable edge, and solid
task sheets give sentences, answers and corrections a dependable reading surface.
Deep blue actions, comfortable humanist type and four colourful rounded skill
pictograms carry the current identity.

The signature is the labelled three-step strip: Õpi → Harjuta → Kontrolli. It
borrows the rhythm of Baltic colour bands while remaining an ordinary progress
indicator. Navigation, fields and disclosures use familiar web controls. Grove's
leaf and name remain the identity; the interface opens directly into the app.

This record comes from [the stylesheet](eesti/web/app.css),
[the shell](eesti/web/index.html), [icons](eesti/web/js/icons.js), current
modules and [the offline fallback](eesti/web/sw.js). The
[direction contract](.impeccable/decisions/practice-rhythm-contract.md)
retains Practice rhythm, seed `6ecca7d2`, round 1, code-first and Operate. The
approved blue material direction is informed by
[design research](docs/design-research.md), which records the references and their
limits. The chooser remains a critique reference; no comp image is a build
specification. The implementation is the authority for values and behaviour.

**Key Characteristics:**

- Pale blue/aqua ground, frosted navigation and solid learning surfaces.
- Deep blue actions, warm current-step marks and separately labelled result states.
- One humanist family, with a sharper cut for Estonian material.
- Four original coloured skill pictograms, visible labels and a stable answer → correction → next-action rhythm.
- Short responsive layouts, readable glosses and progressive disclosure.

## Colors

Cool blues establish place and action; aqua softens the page wash. Warm peach
marks current position, four named skill colours distinguish silhouettes, and
semantic colours support checked feedback. Frontmatter values are normative;
they come from the stylesheet's root roles. Gradient and blur recipes are in
the sidecar because they are materials rather than colour primitives.

### Primary

- **Action blue** (`btn`, `accent`, `accent-deep`, `accent-soft`): primary action,
  links, focus, the current lesson label and contextual recommendations. The
  dark theme uses a pale blue action with dark blue text.

### Secondary

- **Moss** (`good`, `good-soft`): a checked correct answer and its supportive fill.
- **Berry** (`bad`, `bad-soft`): an incorrect attempt or a recording alarm state.
- **Amber** (`warn`, `warn-soft`): caution and material needing attention.
- **Lake** (`gloss`): lexical meaning, rather than a language identity colour.
- **Warm peach** (`coral`): the thin current-step and selected-skill underline;
  its source token retains its historical name.

### Tertiary

- **Reading blue** (`skill-blue`, `skill-blue-soft`): book outline and fill.
- **Listening teal** (`skill-teal`, `skill-teal-soft`): headphones outline and fill.
- **Speaking violet** (`skill-violet`, `skill-violet-soft`): microphone outline and fill.
- **Writing amber** (`skill-amber`, `skill-amber-soft`): pencil outline and fill.

These are skill identities, not correctness or mastery states. Each has a
distinct silhouette, an Estonian label and a Russian gloss in the current MVP.

### Neutral

- **Blue ground** (`bg`, `bg-2`): page and deeper neutral interaction tone.
- **Task surface** (`panel`, `raised`): opaque reading and answer surfaces;
  the dark raised tone also identifies a focused field.
- **Blue ink** (`ink`, `ink-2`, `muted`): primary text, supporting text,
  instructional placeholders and metadata. Placeholders retain full opacity.
- **Rules and tracks** (`line`, `line-soft`, `tint`): list dividers, correction
  separators and neutral selected-control grounds.
- **Navigation tones** (`nav`, `on-nav`, `nav-muted`, `nav-active`): solid fallback,
  labels, glosses and selected or hovered navigation backgrounds.

Dark-prefixed entries are the observed dark replacements for matching roles,
including navigation and all four skill pairs. System preference applies unless
a saved light or dark choice is restored before paint. Browser theme colours
follow the page ground; the install manifest uses the light ground. Component
snippets use live root properties.

**The State Has Words Rule.** Colour supports a visible label, icon or explicit correction; it never carries the result alone. A skipped item is labelled as ungraded and uses a neutral progress mark.

## Typography

**Display Font:** Geologica, with ui-sans-serif, system-ui and sans-serif fallbacks.
**Body Font:** the same family; there is no separate display, serif or icon font.

Geologica is self-hosted in Latin, Latin extended and Cyrillic subsets under
[the font directory](eesti/web/fonts/), with [SIL OFL](eesti/web/fonts/OFL-Geologica.txt).
Available weights are 300–800. Interface and Russian text use the soft sharpness
setting (`SHRP` 0); Estonian sentences, answers, words and rule titles use the
sharper setting (`SHRP` 40). The bundled subsets were checked for Estonian,
Russian and Ukrainian special letters; glyph coverage does not imply completed
Ukrainian instructional content.

### Hierarchy

- **Display:** next-lesson title; its clamp becomes 28px on a phone and 24px on
  a short touch viewport.
- **Headline:** page titles, weight 600; 28px on phones and 24px on short touch
  viewports. A rule title uses weight 700, with its level below the title.
- **Title / lead:** section headings and lesson gist, with the gist at 1.5 line
  height. Phone gist text is 18px.
- **Prompt:** guided drill text, 22px on a phone. Grading retains the same size
  until the learner chooses Edasi.
- **Reading:** continuous Estonian prose, at most 66ch. Ordinary paragraphs are
  bounded at 72ch; lesson sheets are bounded at 76ch.
- **Answer:** Estonian answer fields, weight 500. General fields remain at least
  16px to prevent focus zoom on iOS.
- **Label / note / metadata:** control text, explanation and small glosses.
  Both Estonian and Russian bottom-skill labels are 12px. Segmented controls
  use 14px, weight 700. Primary `go` actions use weight 600; the `primary`
  button variant uses weight 500.
- **Review word:** separate observed clamp (32px to 52px), weight 500, line
  height 1.1, tracking −0.025em. It is recall material, not a page heading.
- Changing counts and times use tabular numerals.

**The Shared Face Rule.** Use the same family across languages; sharpness marks learning material. Estonian UI labels keep a Russian gloss where the MVP needs it, without colouring text merely because it is Russian.

## Layout

The desktop frame is bounded at 1440px: sticky navigation (236px), a flexible
working column bounded at 940px, a 48px gap and 24px × 32px outer padding.
There is no context rail. Navigation begins 24px from the top and occupies the
available viewport height; the working column owns the task.

At widths up to 1079px, navigation narrows to 200px, the gap becomes 24px and
frame padding becomes 16px. The next-lesson copy and action stack; topic actions
move below their name rather than compressing the text.

At widths up to 719px, or on a non-hover viewport up to 559px high, the frame
becomes one column with 16px side gutters. The header keeps the brand home
link, visible Kursus return, Veel disclosure, account and theme controls.
Four skills become a fixed frosted bottom tray in equal columns, inset 12px
from each side and 8px from the bottom. Its safe-area padding and reserved
page-bottom allowance keep content and controls clear. Phone task surfaces
use 16–24px padding. Short touch viewports reduce vertical spacing and restore
a compact side-by-side next-lesson layout.

Spacing follows the seven frontmatter steps. Main sheets use 24–48px padding
on desktop, lessons 32px; secondary lists use hairline rows. Text wraps within
its available width. Tables may scroll sideways; labelled tables pin row labels.

**The Stable Workspace Rule.** Keep one guided item in the task surface. Reserve the correction region (144px) and a separate next-action zone (at least 48px); completed answers move to an optional disclosure after the workspace.

## Elevation & Depth

A restrained blue/aqua page wash sits behind opaque content. The desktop
navigation and floating phone skill tray use a high-opacity gradient tint with
real CSS backdrop blur (22px) and saturation (125%). The light tint is 90–94%
opaque; the dark tint is 94–96%. This is the web app's frosted navigation
material, informed by Liquid Glass, rather than native optical rendering.
The phone header itself stays transparent without blur; the Veel menu is solid.

Task sheets and desktop navigation have no drop shadow. The floating phone
tray, opaque word cards and mobile Veel menu use the shared soft overlay shadow
(`0 12px 32px -18px rgba(28,59,105,.25)`). Thin rules organise lists, form tables
and corrections. Word cards remain opaque in both themes.

Ordinary keyboard focus uses a 3px accent outline with 3px offset. Fields use
an accent edge and a 3px halo at 14% accent. Selected skills and lesson steps
use a thin warm underline rather than added elevation.

Reduced transparency removes the page wash and replaces navigation material
with its solid navigation tone. Browsers without backdrop-filter support also
receive solid navigation. Forced colours uses system Canvas/CanvasText,
removes the wash, blur and tray shadow, and adds a selected-link outline.
Skill silhouettes and labels remain available. Reduced motion retains controls
and collapses animation, transitions and smooth scrolling.

**The Navigation Material Rule.** Frosted material belongs to the functional navigation layer. Keep its high-opacity tint and opaque accessibility fallbacks when extending it.

**The Opaque Reading Rule.** Reading passages, answer fields, corrections and word explanations sit on opaque content surfaces. A floating word explanation keeps the same solid task colour.

## Shapes

The shared corner family is modest: 8px for navigation items and quiet controls,
12px for primary controls and fields, 16px for task surfaces, desktop navigation
and the floating skill tray. The step strip is a flat line with equal flexible
sections. Topic lists align status, name and actions in rows. Compact
recommendation tags remain capsules; audio retains its established rounded
player shape. These component-specific shapes do not make all controls capsules.

The four skill pictograms share a 32-unit grid, rounded 2-unit strokes and a
secondary fill. Book, headphones, microphone and pencil remain distinguishable
by shape when colour is unavailable. Utility icons retain their own bundled
Phosphor geometry.

## Components

### Buttons

Primary actions are solid action blue, at least 48px high, with 12px corners and
12px × 24px padding. Pointer hover darkens the fill; pressing retains the
source's small scale response. Disabled primary and secondary buttons use 45%
opacity. Secondary buttons use a neutral tint; quiet actions use supporting ink
and a text treatment. Both retain at least 44px targets and 8px corners.
Icon controls have at least a 44px square target. The drill microphone matches
the 52px answer-field height; recording adds a berry state and inset rule.

### Chips

Recommendation tags are compact accent-tinted capsules, with 2px × 8px padding,
12px text and weight 700. Segmented choices have a neutral 12px-corner track
with 4px padding; the selected 8px-corner item uses opaque task colour.
Selection is immediate, with the existing keyboard tab pattern.

### Cards / Containers

Next lesson, rule page, guided stage, starter reader and exam entry share an
opaque task surface and 16px corners. Spacing and type establish priority.
The desktop next lesson divides copy and action; one recommended action leads.
Set completion uses neutral tint, score, result marks and continuation.
Optional tools use disclosures.

### Inputs / Fields

General fields have opaque task backgrounds, 1px neutral borders, 12px corners,
48px minimum height and 10px × 16px padding. Answer fields are 52px high with
16px corners, 12px × 18px padding and the answer type role. Labels sit above
with a Russian gloss; focus uses the depth treatment. Placeholders use the
muted text role at full opacity. Choice answers have a neutral border and
accent selected outline. Textareas resize vertically.

### Navigation

Desktop primary links and four skills live in the frosted blue column. Active
links use the solid navigation selected tone; selected skills also carry a warm
underline. The skill pictograms render at 32px on desktop and 26px on phones.
Both phone labels stay 12px. All four skills remain reachable on every page.
On phones, Kursus stays in the header and Veel opens a 220px-wide solid blue
menu; account and theme retain separate targets.

Four original skill pictograms are bundled in [icons.js](eesti/web/js/icons.js)
and selected by [chrome.js](eesti/web/js/chrome.js). They are inline SVG paths,
with separate outline/fill tones, hidden from assistive technology because each
control carries a label and accessible name. Existing Phosphor utility paths,
[with their MIT notice](eesti/web/vendor/phosphor-icons.LICENSE), retain duotone
marks and bold small-button symbols. No icon font, second icon dependency,
external icon request, copied competitor artwork or raster skill icon is used.

### Practice rhythm

The labelled strip in [the shell](eesti/web/index.html) updates its current
step through [path.js](eesti/web/js/path.js). One guided item holds its sentence,
disabled answer controls and correction until Edasi is pressed. Long feedback
scrolls inside the reserved region. Earlier answers appear in Minu vastused
after the workspace, without pushing the active item down a completed stack.
Topic rows distinguish skipped, open, in-progress, mastered and reference states
with labels and icons.

The full rule page in [lesson.js](eesti/web/js/lesson.js) leads with its title,
then level metadata, explanation, forms, examples and sources. Exam entry starts
with the open Proovieksam disclosure; readiness and supporting material follow.

### Identity and opening

The original [64×64 leaf master](eesti/web/brand/mark.svg) supplies the inline
brand and platform artwork. Desktop pairs a 40px mark with a 26px name; phone
pairs a 32px mark with a 24px name. The leaf identity is unchanged. Platform
tiles use action blue and white; social artwork uses pale blue and outlined
Geologica lettering. Rebuild derivatives with [the brand generator](deploy/build-brand.py);
roles are in [the brand record](docs/brand.md). Eleven shipping PNGs, including
the fallback app icon, carry embedded original vector/font provenance. This
identity set contains no generated raster illustrations. Browser bootstrap
colours and the PWA manifest match their page-ground roles.

[main.js](eesti/web/js/main.js) opens the requested route or home directly,
without a timed cover. State changes use 140ms response, 240ms feedback and
420ms arrival with `cubic-bezier(.16,1,.3,1)`. Set-end arrival uses a small
clip/opacity change. Reduced motion collapses animation, transition and smooth
scrolling while retaining the same controls.

### Offline recovery

If navigation fails and no cached shell exists, [the service worker](eesti/web/sw.js)
renders a self-contained recovery page. Its solid background, text and retry
action use the matching light or system-preferred dark roles; it requires no
stylesheet, font file, icon or module download. System text (16px, 1.6 line
height) and a compact heading (24px, 1.3 line height) are dependency fallbacks
for this surface, not a replacement for Geologica in the app.

The reason is explicit in Russian: the app has not yet been saved for offline
use. The native link is labelled Proovi uuesti with a Russian gloss and opens
the app root. The centred copy is bounded at 36ch with 24px page padding. The
retry has 12px corners, 12px × 16px padding and at least a 44px target. Keyboard
focus uses a 3px outline in the matching action colour, offset by 4px against
the page ground. This standalone page follows system theme preference because
the saved app-theme code is unavailable.

## Do's and Don'ts

### Do:

- Do reuse pale blue/aqua ground, deep blue actions, frosted navigation and solid learning surfaces through the root roles.
- Do preserve opaque navigation fallbacks for reduced transparency, unsupported blur and forced colours.
- Do keep all four skills reachable, with their original silhouettes and both bottom-skill labels at 12px.
- Do preserve the single guided item, reserved correction area and explicit Edasi action.
- Do pair colour with a readable state label, icon or correction.
- Do keep Estonian learning material in the sharper Geologica cut and Russian explanations in the soft cut.
- Do retain visible source attribution, readable limits, opaque placeholders, keyboard focus and at least 44px control targets.
- Do derive platform artwork from the original leaf and local font, with provenance on shipping rasters.

### Don't:

- Don't restore the retired boardwalk layout, competing mode dock or timed opening passage as house defaults.
- Don't put reading passages, answer fields, corrections or word explanations on transparent surfaces.
- Don't let completed-answer history grow inside the active guided workspace.
- Don't use colour alone for skill identity, mastery, correctness, skipping or recording state.
- Don't colour text merely because of its language or shrink a caveat until it is unreadable.
- Don't replace source-backed evidence with decorative scores, streaks or an overall exam-readiness percentage.
- Don't treat competitor references, a trend forecast or visual freshness as evidence of improved learning.

Not canonized or repaired: retired boardwalk/glass/serif/capsule descriptions
remain in source comments; the current cascade and explicit navigation material
rule govern extensions. System typography on the uncached-shell recovery page
is scoped to that dependency fallback. This source-based record does not certify
complete English/Ukrainian instructional support. Main-app review and fixes are
recorded in [.impeccable/review/blue-finish-review.md](.impeccable/review/blue-finish-review.md);
the exact-source offline recovery variants and computed keyboard focus are in
[the closeout matrix](.impeccable/review/closeout/matrix.json).
