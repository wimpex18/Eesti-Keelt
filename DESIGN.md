---
name: Grove
description: Practice rhythm — spruce navigation, mint working ground and a clear next action for learning Estonian.
colors:
  bg: '#edf5f0'
  bg-2: '#e2ede5'
  panel: '#ffffff'
  ink: '#17382c'
  ink-2: '#355548'
  muted: '#53685b'
  line: '#cbdcd0'
  line-soft: '#dde8df'
  tint: '#e4eee7'
  nav: '#173e2f'
  on-nav: '#f5faf6'
  nav-muted: '#c3d5c8'
  nav-active: '#2e5943'
  btn: '#244e3d'
  on-btn: '#ffffff'
  accent: '#a63424'
  accent-deep: '#85291c'
  accent-soft: '#fbe9e3'
  coral: '#c54834'
  good: '#256747'
  good-soft: '#e5f3e9'
  bad: '#a52f3d'
  bad-soft: '#fae7eb'
  warn: '#805000'
  warn-soft: '#fcf0d9'
  gloss: '#16606a'
  dark-bg: '#13251f'
  dark-bg-2: '#1d342a'
  dark-panel: '#213c30'
  dark-raised: '#294736'
  dark-ink: '#f1f7f1'
  dark-ink-2: '#d2e3d5'
  dark-muted: '#aec6b5'
  dark-line: '#486554'
  dark-line-soft: '#365443'
  dark-tint: '#2c4939'
  dark-btn: '#cce8d1'
  dark-on-btn: '#183629'
  dark-accent: '#ffbaaa'
  dark-accent-deep: '#ffd2c6'
  dark-accent-soft: '#563329'
  dark-coral: '#ff9a82'
  dark-good: '#b9dfc4'
  dark-good-soft: '#204933'
  dark-bad: '#ffb2c0'
  dark-bad-soft: '#522d38'
  dark-warn: '#f0ce8b'
  dark-warn-soft: '#493d23'
  dark-gloss: '#b1dedb'
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
    backgroundColor: 'color-mix(in srgb, #244e3d 88%, #17382c)'
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
  field:
    backgroundColor: '{colors.panel}'
    textColor: '{colors.ink}'
    typography: '{typography.body}'
    rounded: '{rounded.r-sm}'
    padding: 10px 16px
  skill-navigation:
    backgroundColor: '{colors.nav}'
    textColor: '{colors.on-nav}'
    rounded: '{rounded.r-xs}'
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

Grove is a calm working place for learning Estonian. Spruce navigation gives the
app a stable edge, mint opens the working area, and opaque task sheets give text,
answers and corrections a dependable reading surface. Comfortable humanist type
and a restrained coral current-step mark carry the identity.

The signature is the labelled three-step strip: Õpi → Harjuta → Kontrolli. It
borrows the rhythm of Baltic colour bands while remaining an ordinary progress
indicator. Navigation, fields and disclosures use familiar web controls. Grove's
leaf and name remain the identity; the interface opens directly into the app.

This record comes from [the stylesheet](eesti/web/app.css),
[the shell](eesti/web/index.html) and current modules. The authorised
[direction contract](.impeccable/decisions/practice-rhythm-contract.md) replaces
the previous visual world. Its chooser is a critique reference; no comp image
was approved. [Original roll evidence](.impeccable/review/roll-evidence.md)
records seed `6ecca7d2`, re-roll round 1, grounded candidate 6. The implementation
is the authority for exact values and behaviour.

**Key Characteristics:**

- Spruce navigation, mint ground, opaque task surfaces.
- Coral current-step marks and separately labelled result states.
- One humanist family, with a sharper cut for Estonian material.
- Four persistent skills and a stable answer → correction → next-action rhythm.
- Short responsive layouts, readable glosses and progressive disclosure.

## Colors

Forest greens establish place and action, coral marks current position, and
semantic colours support checked feedback. Frontmatter values are normative;
they come from root properties in the stylesheet.

### Primary

- **Spruce** (`nav`, `btn`): navigation and primary action. The primary action
  becomes light green with dark text in the dark theme.
- **Coral** (`accent`, `coral`): links, focus, the current lesson step and the
  selected skill's underline. The darker accent carries text; coral carries
  the thin state mark. Both become lighter in the dark theme.

### Secondary

- **Moss** (`good`, `good-soft`): a checked correct answer and its supportive fill.
- **Berry** (`bad`, `bad-soft`): an incorrect attempt or a recording alarm state.
- **Amber** (`warn`, `warn-soft`): caution and material needing attention.
- **Lake** (`gloss`): lexical meaning, rather than a language identity colour.

### Neutral

- **Mint ground** (`bg`, `bg-2`): page and deeper neutral interaction tone.
- **Task surface** (`panel`, `dark-panel`, `dark-raised`): opaque reading and
  answer surfaces; the dark raised tone also identifies a focused field.
- **Forest ink** (`ink`, `ink-2`, `muted`): primary text, supporting text and metadata.
- **Rules and tracks** (`line`, `line-soft`, `tint`): list dividers, correction
  separators and neutral selected-control grounds.
- **Navigation foregrounds** (`on-nav`, `nav-muted`, `nav-active`): labels,
  Russian glosses and selected or hovered navigation backgrounds. These
  spruce navigation colours remain fixed across themes.

Dark-prefixed frontmatter entries are the observed dark replacements for the
matching root role. System preference applies unless a saved light or dark
choice is restored before paint. Component snippets use live root properties.

**The State Has Words Rule.** Colour supports a visible label, icon or explicit correction; it never carries the result alone. A skipped item is labelled as ungraded and uses a neutral progress mark.

## Typography

**Display Font:** Geologica, with ui-sans-serif, system-ui and sans-serif fallbacks.
**Body Font:** the same family; there is no separate display, serif or icon font.

Geologica is self-hosted in Latin, Latin extended and Cyrillic subsets under
[the font directory](eesti/web/fonts/), with [SIL OFL](eesti/web/fonts/OFL-Geologica.txt).
Available weights are 300–800. Interface and Russian text use the soft sharpness
setting (`SHRP` 0); Estonian sentences, answers, words and rule titles use the
sharper setting (`SHRP` 40).

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
  use 14px, weight 700.
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
Four skills become a fixed, solid spruce bottom bar in equal columns, with
safe-area padding and a reserved page-bottom allowance. Phone task surfaces
use 16–24px padding. Short touch viewports reduce vertical spacing and restore
a compact side-by-side next-lesson layout.

Spacing follows the seven frontmatter steps. Main sheets use 24–48px padding
on desktop, lessons 32px; secondary lists use hairline rows. Text wraps within
its available width. Tables may scroll sideways; labelled tables pin row labels.

**The Stable Workspace Rule.** Keep one guided item in the task surface. Reserve the correction region (144px) and a separate next-action zone (at least 48px); completed answers move to an optional disclosure after the workspace.

## Elevation & Depth

Tonal separation carries hierarchy: mint page, opaque task sheets and spruce
navigation. The sidebar, bottom bar and task sheets have no drop shadow.
Word cards and the mobile Veel menu use the existing soft overlay shadow
(`0 8px 24px -12px rgba(23,56,44,.22)`). Word cards remain opaque in both themes.
Thin rules organise lists, form tables and corrections.

Ordinary keyboard focus uses a 3px accent outline with 3px offset. Fields use
an accent edge and a 3px halo at 14% accent. Selected skills and lesson steps
use a thin coral underline rather than added elevation.

**The Opaque Reading Rule.** Text, answers and their explanations sit on opaque surfaces. A floating word explanation keeps the same solid task colour.

## Shapes

The shared corner family is modest: 8px for navigation and quiet controls,
12px for primary controls and fields, 16px for task surfaces and sidebar.
The step strip is a flat line with equal flexible sections. Topic lists align
status, name and actions in rows. Compact recommendation tags remain capsules;
audio retains its established rounded player shape. These component-specific
shapes do not make all controls capsules.

## Components

### Buttons

Primary actions are solid spruce, at least 48px high, with 12px corners and
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
with a Russian gloss; focus uses the depth treatment. Choice answers have a
neutral border and accent selected outline. Textareas resize vertically.

### Navigation

Desktop primary links and four skills live in the spruce column. Active links
use a spruce tint; selected skills also carry a coral underline. Skills use
24px icons on desktop and 22px on phones. All four remain reachable on every
page. On phones, Kursus stays in the header and Veel opens a 220px-wide spruce
menu; account and theme retain separate targets.

Icons are bundled Phosphor path data in [icons.js](eesti/web/js/icons.js), with
[its MIT notice](eesti/web/vendor/phosphor-icons.LICENSE). Navigation and marks
use the bundled default set; small button icons use its bold set. SVG paths
inherit text colour and require no external icon request.

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
pairs a 32px mark with a 24px name. Platform tiles use spruce and white; social
artwork uses mint and outlined Geologica lettering. Rebuild derivatives with
[the brand generator](deploy/build-brand.py); roles are in [the brand record](docs/brand.md).
Eleven shipping PNGs, including the fallback app icon, carry embedded original
vector/font provenance. This identity set contains no generated raster illustrations.

[main.js](eesti/web/js/main.js) opens the requested route or home directly,
without a timed cover. State changes use 140ms response, 240ms feedback and
420ms arrival with `cubic-bezier(.16,1,.3,1)`. Set-end arrival uses a small
clip/opacity change. Reduced motion collapses animation, transition and smooth
scrolling while retaining the same controls.

## Do's and Don'ts

### Do:

- Do reuse spruce navigation, mint ground and opaque task surfaces through the root tokens.
- Do keep all four skills reachable and both bottom-skill labels at 12px.
- Do preserve the single guided item, reserved correction area and explicit Edasi action.
- Do pair colour with a readable state label, icon or correction.
- Do keep Estonian learning material in the sharper Geologica cut and Russian explanations in the soft cut.
- Do retain visible source attribution, readable limits, keyboard focus and at least 44px control targets.
- Do derive platform artwork from the original leaf and local font, with provenance on shipping rasters.

### Don't:

- Don't restore the discarded glass shell, boardwalk layout or timed opening passage as house defaults.
- Don't put reading, answer fields, corrections or word explanations on transparent surfaces.
- Don't let completed-answer history grow inside the active guided workspace.
- Don't use colour alone for mastery, correctness, skipping or recording state.
- Don't colour text merely because of its language or shrink a caveat until it is unreadable.
- Don't replace source-backed evidence with decorative scores, streaks or an overall exam-readiness percentage.

Not canonized or repaired: retired glass/boardwalk names and old descriptive
comments remain in styles and modules; their presence does not define the
replacement world. This source-based record does not assert fresh rendered
contrast, viewport coverage or complete English/Ukrainian instructional support.
