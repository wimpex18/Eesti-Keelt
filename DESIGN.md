---
name: Klint
description: Interlinear. Every Estonian form shows what it is; spruce ink on a birch and limestone ground; one fixed primary action per screen.
colors:
  ground: '#F1F4F1'
  sheet: '#FFFFFF'
  sunk: '#E4EAE5'
  ink: '#15201A'
  ink-2: '#3A4740'
  muted: '#56635B'
  line: '#D2DAD4'
  edge: '#76837B'
  act: '#15201A'
  act-hover: '#2B3A32'
  on-act: '#FFFFFF'
  jarv: '#2645B5'
  jarv-soft: '#E3E8F8'
  focus: '#2645B5'
  good: '#22663A'
  good-soft: '#E0EFE4'
  bad: '#A32F3B'
  bad-soft: '#F9E5E7'
  warn: '#7F4E00'
  warn-soft: '#FAEDD3'
  gloss: '#1A646E'
  scrim: 'rgba(21,32,26,.48)'
  skill-blue: '#2359a8'
  skill-blue-soft: '#a9cdfa'
  skill-teal: '#09646b'
  skill-teal-soft: '#9ddade'
  skill-violet: '#6946a3'
  skill-violet-soft: '#d1b9f5'
  skill-amber: '#865214'
  skill-amber-soft: '#f9d49b'
  dark-ground: '#141F19'
  dark-sheet: '#1B2A22'
  dark-sunk: '#24362C'
  dark-ink: '#E8EFEA'
  dark-ink-2: '#C2CDC6'
  dark-muted: '#A1AEA6'
  dark-line: '#30443A'
  dark-edge: '#7C9084'
  dark-act: '#E8EFEA'
  dark-act-hover: '#CFDAD3'
  dark-on-act: '#141F19'
  dark-jarv: '#A9BCFF'
  dark-jarv-soft: '#26345A'
  dark-focus: '#A9BCFF'
  dark-good: '#9CD6AC'
  dark-good-soft: '#1E3C29'
  dark-bad: '#FFB2BA'
  dark-bad-soft: '#4A2229'
  dark-warn: '#F1CA84'
  dark-warn-soft: '#3E3220'
  dark-gloss: '#93D4DB'
  dark-scrim: 'rgba(0,0,0,.56)'
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
    fontSize: 3rem
    fontWeight: 500
    lineHeight: 1.15
    letterSpacing: -0.02em
    fontVariation: '"SHRP" 100'
  display-phone:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 2.25rem
    fontWeight: 500
    lineHeight: 1.18
    letterSpacing: -0.02em
    fontVariation: '"SHRP" 100'
  title:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 2.25rem
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.02em
    fontVariation: '"SHRP" 100'
  prompt:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 2.25rem
    fontWeight: 500
    lineHeight: 2.5
    letterSpacing: -0.005em
    fontVariation: '"SHRP" 100'
  prompt-phone:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 1.5rem
    fontWeight: 500
    lineHeight: 2.6
    fontVariation: '"SHRP" 100'
  lead:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 1.3125rem
    fontWeight: 400
    lineHeight: 1.4
    fontVariation: '"SHRP" 0'
  reading:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 1.125rem
    fontWeight: 400
    lineHeight: 1.7
    fontVariation: '"SHRP" 60'
  body:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.5
    fontVariation: '"SHRP" 0'
  label:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 1rem
    fontWeight: 600
    lineHeight: 1.25
    fontVariation: '"SHRP" 60'
  action:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 1.125rem
    fontWeight: 600
    lineHeight: 1.2
    fontVariation: '"SHRP" 60'
  form-line:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.2
    fontVariation: '"SHRP" 0'
  note:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.45
    fontVariation: '"SHRP" 0'
  gloss:
    fontFamily: Geologica, ui-sans-serif, system-ui, sans-serif
    fontSize: 0.75rem
    fontWeight: 400
    lineHeight: 1.3
    fontVariation: '"SHRP" 0'
rounded:
  r-1: 6px
  r-2: 10px
  r-3: 14px
spacing:
  s1: 4px
  s2: 8px
  s3: 12px
  s4: 16px
  s5: 24px
  s6: 32px
  s7: 48px
motion:
  dur-1: 100ms
  dur-2: 160ms
  dur-3: 240ms
  dur-4: 320ms
  ease-standard: cubic-bezier(.2,0,0,1)
  ease-enter: cubic-bezier(.05,.7,.1,1)
  ease-exit: cubic-bezier(.3,0,.8,.15)
components:
  button-primary:
    backgroundColor: '{colors.act}'
    textColor: '{colors.on-act}'
    typography: '{typography.action}'
    rounded: '{rounded.r-3}'
    height: 52px
    padding: 0 24px
  button-primary-hover:
    backgroundColor: '{colors.act-hover}'
  button-secondary:
    backgroundColor: transparent
    textColor: '{colors.ink}'
    borderColor: '{colors.line}'
    typography: '{typography.label}'
    rounded: '{rounded.r-2}'
    height: 44px
    padding: 0 12px
  button-key:
    backgroundColor: transparent
    textColor: '{colors.ink}'
    borderColor: '{colors.edge}'
    rounded: '{rounded.r-3}'
    size: 52px
  field:
    backgroundColor: '{colors.sheet}'
    textColor: '{colors.ink}'
    borderColor: '{colors.edge}'
    typography: '{typography.body}'
    rounded: '{rounded.r-2}'
    height: 48px
    padding: 0 16px
  gap-field:
    backgroundColor: '{colors.sheet}'
    textColor: '{colors.ink}'
    borderColor: '{colors.edge}'
    typography: '{typography.prompt}'
    rounded: '{rounded.r-2}'
    padding: 2px 10px
  segmented-control:
    backgroundColor: '{colors.sunk}'
    textColor: '{colors.ink-2}'
    rounded: '{rounded.r-3}'
    padding: 4px
  segmented-control-selected:
    backgroundColor: '{colors.sheet}'
    textColor: '{colors.ink}'
    borderColor: '{colors.edge}'
    rounded: '{rounded.r-2}'
  bench:
    backgroundColor: '{colors.sheet}'
    textColor: '{colors.ink}'
    rounded: '{rounded.r-3}'
    padding: 32px 32px 0
  dock:
    backgroundColor: '{colors.sheet}'
    textColor: '{colors.ink-2}'
    borderColor: '{colors.line}'
    height: 67px
  action-bar:
    backgroundColor: '{colors.sheet}'
    height: 76px
    padding: 12px 8px
  session-line:
    backgroundColor: '{colors.sunk}'
    textColor: '{colors.muted}'
    height: 6px
    rounded: 3px
  interlinear-word:
    textColor: '{colors.ink}'
    borderColor: '{colors.ink}'
    typography: '{typography.prompt}'
  form-line:
    textColor: '{colors.gloss}'
    typography: '{typography.form-line}'
  sheet-modal:
    backgroundColor: '{colors.sheet}'
    rounded: '{rounded.r-3}'
    padding: 24px
---

# Design System: Klint

## Status of this record

This is the specification of the Klint redesign: the target for every screen
rebuilt from now on. The tokens and the shell ship: `eesti/web/app.css` defines
this record's roles for both themes and every rule reads them, and the header,
sidebar, dock, action bar and sheets are built (steps 1 and 2 of
**Migration**). The screens themselves keep their earlier layouts on the new
ground until their own step rebuilds them. The audit of the screens, the
references and the reasons behind each decision are in
[design research](docs/design-research.md).

Where a value here and the stylesheet disagree, a screen built to this record
uses this record; a screen not yet rebuilt keeps its layout. Learning rules
are unchanged: code grades, models are labelled, sources stay attributed
(`docs/adr/0009-learning-loop.md`, `PRODUCT.md`).

## Fixed and open

This record was written and independently reviewed on 10 October 2026. The
session that builds a screen may see further: a newer model, a front-end
design skill, or simply the real screen in front of it. So the record separates
what every screen must keep from what is a reviewed starting point.

**Fixed.** Whatever a screen looks like, it keeps:

- the learning rules: code grades answers and names every form (the data
  contract of the interlinear word); a model's words carry its engine and never
  a result colour; sources show near the top; a skip stays distinct from
  mastery; only the first attempt counts;
- the direction the owner committed to in `PRODUCT.md`: the name and mark, the
  interlinear word as the signature (a form named under the word, from code,
  after the learner has tried), Estonian labels with a gloss in the explanation
  language, and no score the app cannot stand behind;
- one primary action per screen, in a place that does not move between states;
- accessibility: WCAG 2.2 AA contrast with every ratio computed, no result
  carried by colour alone, focus never under the dock, header, action bar or
  keyboard, targets of 44px, complete keyboard and screen-reader use, and
  reduced motion, forced colours and `prefers-contrast` honoured;
- languages: Russian, Ukrainian and English without truncation, `lang` on
  every element, and the default-language rule;
- none of the forbidden defaults below.

**Open.** Colour values, type sizes, spacing, radii, wireframes, component
looks, motion timings, the dock's exact form and the iOS mapping are this
record's proposal. A builder who finds something simpler, more useful or more
beautiful builds it, provided every fixed rule holds and the result is checked
as this record was: screenshots at phone and desktop sizes in both themes,
contrast computed with the WCAG formula, and the focus journey. The same pull
request updates this record and gives the reason in
[design research](docs/design-research.md), so the record keeps describing the
target. A change to something `PRODUCT.md` commits to (spruce ink on a birch
ground, Geologica, the four pictograms) is proposed to the owner in the pull
request rather than made.

## Overview

**Creative North Star: "Interlinear"**

Linguists write a sentence with its analysis underneath, word by word: the
interlinear gloss. Klint's whole subject is that analysis — which form a word
takes and why — and the code already knows it, because Vabamorf and each item's
key name the form. So the interface sets the Estonian word large and sharp and,
when the learner needs it, writes its form under it in small soft type:
*rahakotti* over *osastav, частичный падеж*. The correction sits at the word,
not in a paragraph somewhere below.

That device is the one bold thing. Everything around it is quiet: a cool birch
ground, spruce ink, one family of type, hairline structure, no glass, no
gradients, no cards for their own sake. Colour is spent on learning state
(right, wrong, caution) and on the four skill pictograms; the primary action is
ink, the most legible colour the page has.

**Key characteristics**

- The interlinear word: Estonian form above, its form name and meaning below,
  supplied by code.
- One family, two voices: Geologica's sharp cut (`SHRP` 100) for Estonian
  material, its soft cut (`SHRP` 0) for the explanation language (Russian,
  Ukrainian or English) and interface text.
- One primary action per screen, always in the same place: the action bar
  above the phone dock, the sticky action row on desktop.
- Practice rhythm kept: one item, answer, correction at the word, Edasi.
- Solid surfaces only. Translucent material belongs to native iOS bars, later.

### What stays, what changes

| Area | Decision | Why |
|---|---|---|
| Practice rhythm (one item → check → correction → Edasi) | Kept | It works; the audit found the rhythm sound and its presentation weak. |
| Õpi → Harjuta → Kontrolli | Kept as the three phase labels of the session line | It is the app's loop; ADR-0009's seven steps group under it. |
| Reserved correction region | Kept, moved under the sentence | The answer no longer jumps; the correction now starts at the word. |
| Geologica, skill pictograms | Kept | Licensing is settled; the font's `SHRP` axis is used fully for the first time. |
| Name and mark | Grove becomes Klint; the leaf becomes an underlined K | Another company holds grove.ee. Klint, the limestone cliff of north Estonia, is a step learners climb; the mark is the signature component itself: a letter with its interlinear bar (`docs/brand.md`). |
| Both phone skill labels (Estonian and the explanation language) | Kept | The interface is language exposure (`PRODUCT.md`). |
| Pale blue wash, frosted navigation, deep blue buttons | Replaced | Generic 2021–23 SaaS material, unrelated to the name; glass imitates what iOS renders natively. |
| White cards on a tinted page | Replaced | Content chopped into identical cards; only the item bench and reading sheets keep a surface. |
| Primary action placement | Changed: fixed bar on phones, sticky row on desktop | Two primary-looking buttons and an off-screen Edasi were the commonest defects. |
| Phone skill tray | Becomes a dock with three states | The four skills are one tap away while browsing and acting, and behind the skills key during a task; focus and the keyboard are never covered. |
| Home | Becomes Täna, the session (ADR-0009) | One Jätka and two alternatives with reasons. |

## Principles

1. **Every form says what it is.** A form the learner must learn is shown with
   its name from code, at the word, the moment it matters — never before the
   learner has tried (rule by doing comes first).
2. **One primary, one place.** Each screen has at most one primary action. On a
   phone it lives in the action bar; on a desktop at the end of the sticky
   action row. Its label changes; its position does not.
3. **Colour is state.** Ink acts; moss means checked right; cranberry means checked
   wrong; amber means caution; lake blue means a link, a focus ring or a
   selection. Each also has a word, an icon or a shape.
4. **The page is the surface.** Lists, plans and headings sit on the ground. A
   surface appears only where opaque reading matters: the item bench, a rule or
   text being read, a sheet.
5. **Motion answers the learner.** Nothing moves unless the learner did
   something or the state changed; nothing loops except a recording clock.

## Forbidden defaults

These are defaults that appear whatever the subject. None of them may appear in
Klint, in either theme, on any screen.

- **Cream backgrounds.** No warm off-white ground (the `#F4F1EA` family) and no
  terracotta or clay accent beside it.
- **Italic accent words.** No italic at all: the bundled Geologica has no slant
  axis, so `em` and `i` render a synthesized oblique. Estonian inside a Russian
  sentence is marked by `lang="et"` and the sharp cut; emphasis is weight 600.
  An `i` element used for a gloss is restyled upright.
- **Numbered section labels.** No `01 / 02 / 03` markers on sections. Numbers
  appear only for real sequences that the learner counts: unit numbers, item
  progress, a mock exam's question numbers.
- **Monospace labels.** No monospace face anywhere, including counts, codes and
  metadata; counts use Geologica's tabular figures.
- **Pill buttons.** No control whose radius is half its height or more. Primary
  14px, secondary and fields 10px, chips 6px. The only circles are status dots
  and item beads, which are not controls.
- **Tracked all-caps labels.** No uppercase eyebrow or tag (today's `.task
  .form` and `.tag` are removed).
- **Middle-dot meta strings.** No `A · B · C`. Metadata is a short sentence or
  a second line: a unit is a heading, its progress a count beside it.
- **Spaced em-dash labels.** No "Tean juba — jäta vahele"; a control has one
  label and one gloss.
- **Arrows appended to links or buttons.** No "Edasi →". In grammar, a
  condition and its form are a table row or "eitus: osastav", not an arrow.
- **Frosted glass and gradient washes.** No `backdrop-filter`, no decorative
  gradient on any web surface.
- **The SaaS card kit.** No identical rounded cards with one soft grey shadow
  each.
- **Near-black with one acid accent; tinted `#111` standing in for black.**
  Spruce ink is a named colour with a role, not a substitute for black.
- **Decorative motion.** No load-in sequences, staggered reveals, shimmer
  skeletons, pulsing placeholders, confetti or celebration overlays.
- **Scores the app cannot stand behind.** No streaks, points or an overall
  readiness percentage (`PRODUCT.md`).

## Colors

The ground is birch bark and the pale limestone of the klint's face; the ink
is the spruce forest that grows along its top. Both are deliberately cool and
slightly green, tying the screen to the place the name comes from without a
picture of it. Lake blue
(järv) is the only blue: links, focus and selection. The frontmatter is the
single source of the token values; a change to one follows **Fixed and open**
and updates the contrast table.

### Roles

| Role | Light | Dark | Use |
|---|---|---|---|
| `ground` | `#F1F4F1` | `#141F19` | The page. Lists, plans, headings, phone screens. |
| `sheet` | `#FFFFFF` | `#1B2A22` | Opaque reading and answering: item bench, rule and text pages, sheets, dock, fields. |
| `sunk` | `#E4EAE5` | `#24362C` | Tracks: segmented control, session line, empty beads, disabled fill. |
| `ink` | `#15201A` | `#E8EFEA` | Text, the interlinear bar, the current segment. |
| `ink-2` | `#3A4740` | `#C2CDC6` | Supporting text, instructions. |
| `muted` | `#56635B` | `#A1AEA6` | Metadata, glosses under labels, placeholders (full opacity). |
| `line` | `#D2DAD4` | `#30443A` | Decorative hairlines between rows. Never the only boundary of a control. |
| `edge` | `#76837B` | `#7C9084` | Boundaries a learner must see: field borders, keys, selected segment outline. |
| `act`, `act-hover`, `on-act` | `#15201A`, `#2B3A32`, `#FFFFFF` | `#E8EFEA`, `#CFDAD3`, `#141F19` | The primary action. |
| `jarv`, `jarv-soft` | `#2645B5`, `#E3E8F8` | `#A9BCFF`, `#26345A` | Links, selected navigation, alternative actions on Täna. |
| `focus` | `#2645B5` | `#A9BCFF` | Keyboard focus ring. |
| `good`, `good-soft` | `#22663A`, `#E0EFE4` | `#9CD6AC`, `#1E3C29` | A checked right answer (Sammal, moss). |
| `bad`, `bad-soft` | `#A32F3B`, `#F9E5E7` | `#FFB2BA`, `#4A2229` | A checked wrong answer; recording (Jõhvikas, cranberry). |
| `warn`, `warn-soft` | `#7F4E00`, `#FAEDD3` | `#F1CA84`, `#3E3220` | Caution: an unchecked source, a provider fallback, a closing registration. |
| `gloss` | `#1A646E` | `#93D4DB` | The form line and word meanings (Meri, sea). |
| `scrim` | `rgba(21,32,26,.48)` | `rgba(0,0,0,.56)` | Behind a sheet. |
| `skill-*` | unchanged | unchanged | The four pictograms' strokes and fills only, never text. |

The previous `coral` current-step mark is retired: the current segment and the
current tab are ink. Skipped work uses `muted` and the word *vahele jäetud*,
never a result colour.

**The State Has Words Rule.** Colour supports a label, icon or shape; it never
carries a result alone. Right is a check mark, *Õige* and a filled bead; wrong
is a cross, *Pole õige*, the learner's answer struck through and a slashed
bead; skipped is a dash bead and *vahele jäetud*. Each bead's accessible text
names its result (see **Beads** under the session).

### Contrast (WCAG 2.2 AA)

Ratios are computed with the relative-luminance formula defined by
[WCAG 2.2](https://www.w3.org/TR/WCAG22/#dfn-relative-luminance) and rounded
down to two decimals. Requirements: text 4.5:1
([SC 1.4.3](https://www.w3.org/TR/WCAG22/#contrast-minimum)); user-interface
boundaries, focus indicators and meaningful graphics 3:1
([SC 1.4.11](https://www.w3.org/TR/WCAG22/#non-text-contrast)). Klint holds
every text pair to 4.5:1, including large text, which the standard would let
fall to 3:1.

| Foreground on background | Kind | Light | Dark | Needed |
|---|---|---|---|---|
| `ink` on `ground` | text | 15.11 | 14.49 | 4.5 |
| `ink` on `sheet` | text | 16.75 | 12.82 | 4.5 |
| `ink` on `sunk` | text | 13.72 | 10.96 | 4.5 |
| `ink-2` on `ground` | text | 8.79 | 10.35 | 4.5 |
| `ink-2` on `sheet` | text | 9.74 | 9.16 | 4.5 |
| `ink-2` on `sunk` | text | 7.98 | 7.83 | 4.5 |
| `muted` on `ground` | text | 5.68 | 7.35 | 4.5 |
| `muted` on `sheet` | text | 6.30 | 6.51 | 4.5 |
| `muted` on `sunk` | text | 5.16 | 5.56 | 4.5 |
| `on-act` on `act` | text | 16.75 | 14.49 | 4.5 |
| `on-act` on `act-hover` | text | 11.97 | 11.79 | 4.5 |
| Gloss in a primary button (`on-act` at 80 % over `act`) | text | 11.02 | 8.02 | 4.5 |
| `jarv` on `ground` | text | 7.28 | 9.13 | 4.5 |
| `jarv` on `sheet` | text | 8.07 | 8.08 | 4.5 |
| `jarv` on `jarv-soft` | text | 6.59 | 6.57 | 4.5 |
| `gloss` on `ground` | text | 6.12 | 10.22 | 4.5 |
| `gloss` on `sheet` | text | 6.79 | 9.05 | 4.5 |
| `good` on `sheet` | text | 6.93 | 9.01 | 4.5 |
| `good` on `good-soft` | text | 5.82 | 7.28 | 4.5 |
| `bad` on `sheet` | text | 6.93 | 8.80 | 4.5 |
| `bad` on `bad-soft` | text | 5.74 | 7.94 | 4.5 |
| `warn` on `sheet` | text | 7.01 | 9.65 | 4.5 |
| `warn` on `warn-soft` | text | 6.05 | 8.03 | 4.5 |
| `edge` on `sheet` (field, key border, selected tab outline) | UI | 3.96 | 4.41 | 3 |
| `edge` on `ground` | UI | 3.57 | 4.98 | 3 |
| `edge` on `sunk` (selected segment) | UI | 3.24 | 3.77 | 3 |
| `focus` on `ground` | UI | 7.28 | 9.13 | 3 |
| `focus` on `sheet` | UI | 8.07 | 8.08 | 3 |
| `act` on `ground` (button shape) | UI | 15.11 | 14.49 | 3 |
| Skill strokes on `ground` (lowest of four) | graphic | 5.86 | 10.37 | 3 |
| `line` on `sheet` | decorative | 1.42 | 1.43 | none: never the only boundary |

`line` is decorative by rule: wherever a boundary carries meaning (a field, a
key, a selected option, the end of the bench on a ground of nearly the same
lightness) it is drawn in `edge` or carried by a fill change of at least 3:1.

With `prefers-contrast: more`, `line` takes `edge`, `muted` takes `ink-2`, and
the form line takes weight 600.

### Forced colours

Under `forced-colors: active` the browser replaces the palette; Klint keeps
meaning by shape.

| Element | System colours |
|---|---|
| Ground, sheet, dock, sheets | `Canvas`, with a 1px `CanvasText` border on the bench, dock and sheets |
| Text, interlinear bar, segments | `CanvasText` (the bar is a border, so it survives) |
| Primary button | `ButtonFace` / `ButtonText`, 2px `ButtonText` border |
| Secondary buttons, keys | `ButtonFace` / `ButtonText`, 1px `ButtonText` border |
| Selected tab, segment, navigation item, choice | `Highlight` / `HighlightText` |
| Links | `LinkText` |
| Focus ring | 3px `Highlight` outline |
| Right / wrong / skipped | `CanvasText`, carried by the icon, the word, the strike-through and the bead's shape |
| Disabled | `GrayText` |
| Skill pictograms | `ButtonText` strokes, `Canvas` fills |

## Typography

**One family: Geologica**, self-hosted (Latin, Latin extended, Cyrillic; SIL
OFL, `eesti/web/fonts/`). Its variable axes in the bundled subsets are weight
(300–800) and sharpness (`SHRP` 0–100); there is no slant axis, hence no
italic. Sizes are set in `rem` so the browser's text size setting scales them.

**Two voices.** `SHRP` 100 for Estonian at display and prompt sizes, `SHRP` 60
for Estonian at running sizes (reading, labels, table cells), `SHRP` 0 for
the explanation language and every interface sentence. The difference shows at the terminals of
*k*, *t* and the tail of *Щ*; it is felt rather than read, and it marks
material without colour.

**Scale.** The sizes are the classic typographic scale Robert Bringhurst sets
out in *The Elements of Typographic Style* — 12, 14, 16, 18, 21, 24, 36, 48 px —
and nothing between them.

| Role | Size / line height | Weight | Cut | Use |
|---|---|---|---|---|
| Display | 48/1.15 desktop, 36/1.18 phone | 500 | 100 | Täna's sentence pair, the review word |
| Title | 36/1.15 | 600 | 100 | A rule title, a page heading on desktop |
| Prompt | 36/2.5 desktop, 24/2.6 phone | 500 | 100 | The item sentence; the tall line holds the form line |
| Lead | 21/1.4 | 400 | 0 | A rule's gist, Täna's question |
| Reading | 18/1.7 | 400 | 60 | Estonian prose, at most 66 characters a line |
| Body | 16/1.5 | 400 | 0 | Explanations and interface text, at most 66 characters |
| Label / action | 16/1.25, 18/1.2 in the action bar | 600 | 60 | Buttons and navigation |
| Form line, note | 14/1.2, 14/1.45 | 400 | 0 | The interlinear line, metadata |
| Gloss | 12/1.3 | 400 | 0 | The explanation-language gloss under an Estonian label; never smaller |

Rules: tabular figures for every count and time; `text-wrap: balance` on
headings, `pretty` on paragraphs; Estonian elements carry `lang="et"` so
hyphenation and screen-reader voices are right; glosses never take
the sharp cut. Fields stay at 16px or more so iOS Safari does not zoom.
The cut follows the markup: an element marked `lang="et"` takes the cut its
context sets (60, or 100 inside a display, title or prompt), and the
explanation languages and every gloss take 0, so no screen has to name its
Estonian elements one by one. `font-synthesis: none` stops the browser faking
an italic or a bold the face does not have; `em` is weight 600, and an
Estonian form cited inside an explanation (`*rahakotti*` in the explanations'
markup) is `lang="et"`, upright, weight 500.
Bringhurst's 45–75 character measure (66 ideal) is the longest a paragraph's
line may be; a phone column is narrower and sets its own.

## Layout

### Grid

- **Desktop (≥1024px):** a 248px sidebar on the ground, separated by one
  `line` rule; a content column with 32px side padding. Task and reading
  columns are 720px wide; browse lists (Kursus, Kordamine) 880px. Täna uses
  two columns: the session (minmax(0,1fr)) and its plan (300px), 48px apart.
- **Tablet (720–1023px):** the sidebar narrows to a 96px rail of marks with
  their label and gloss below; columns as desktop. 96px, not 88: *аудирование*
  is 78px at 12px and needs its tab's padding beside it.
- **Phone (<720px, or touch and under 560px high):** one column, 16px side
  gutters, a 56px header (sticky upright, scrolling with the page on its side)
  and the dock at the bottom.
- **Safe areas.** The page reaches under the iPhone's rounded corners and
  sensor housing (`viewport-fit=cover`), which in landscape covers about 60px
  at the left or right edge. Every side gutter is therefore the larger of its
  own width and the inset: `padding-inline: max(16px,
  env(safe-area-inset-left)) max(16px, env(safe-area-inset-right))` on the
  header, the content, the action bar and the dock (whose tab row uses 8px in
  place of 16px), and the bottom inset under the dock.
- Everything is left-aligned, including the end of a set. Nothing is centred
  except a pictogram inside its tab.
- Spacing uses `s1`–`s7` only. Between sections 48px; between a heading and its
  content 12px; between rows 0 with a hairline.

### The phone dock and the action bar

The bottom of a phone screen is one component with three states. It follows
the iOS 26 model of a tab bar with the current screen's action above it; on
iOS the act state is a per-screen inset and the task state a full-screen flow
with its own bar, not the app-wide bottom accessory (see **iOS**).

| State | When | Shows | Height |
|---|---|---|---|
| Browse | No primary action (a skill list, Veel pages) | Tab row: Täna and the four skills | 67px + safe area (49px on a phone's side, each tab one line) |
| Act | A screen with a primary action that is not a task (Täna, Kursus, a rule) | The action bar above the tab row | 76px + 67px + safe area |
| Task | An item awaits an answer or a correction is shown; or a text field is focused with the keyboard up | One row: a skills key (52px square), optional microphone key, the primary action filling the rest | 76px + safe area, on the keyboard when it is up |

```
Browse                         Act                            Task
┌──────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│                          │   │ [        Jätka         ] │   │ [⊞] [🎙] [  Kontrolli   ] │
│ Täna Lug. Kuul. Rääk. Kir│   │ Täna Lug. Kuul. Rääk. Kir│   └──────────────────────────┘
│ сег. чтен. ауд. гов. пис.│   │ сег. чтен. ауд. гов. пис.│
└──────────────────────────┘   └──────────────────────────┘
```

- Tabs show the pictogram (24px), the Estonian label (12px) and its gloss in
  the explanation language (12px; the owner's rule that both phone labels stay
  12px holds).
- Tab columns take the width of their content (`grid-template-columns:
  repeat(5, auto)`, spread with `justify-content: space-between`, never closer
  than 4px), not five equal fifths. Measured in Geologica at 12px on
  10 October 2026, *Kirjutamine* is 70px at weight 600 and *аудирование* 78px
  at 400, while an equal fifth of 390px leaves about 70px for text. A gloss
  wider than its column wraps to a second line with `hyphens: auto` in its own
  language (broken anywhere only where the browser has no dictionary), and the
  row grows by that line. Nothing is truncated or abbreviated. The tabs carry
  no `min-width`: a grid item's own minimum is then its content, which is what
  keeps a tab from running into the next.
- Under 360px the five Estonian labels need 281px of the row, so the gutters
  narrow to 2px, the tabs lose their side padding and the selection mark
  narrows to 40px before any word would. The row is checked at 390 and 320px
  in Russian, Ukrainian and English on both engines
  (`tests/test_e2e_journeys.py`).
- The selected tab keeps the label's weight (600, so its width does not
  change); its label turns `ink`, and a 44×28 `sunk` rectangle with a 1px
  `edge` outline sits behind its pictogram (radius 10px, not a capsule). The
  outline carries the state at 3.96:1 light and 4.41:1 dark; the fill alone
  would be 1.22:1 and 1.17:1, below the 3:1 a state indicator needs.
- The wireframes abbreviate tab labels to fit their character grid; the app
  never does.
- The skills key opens the four skills as a sheet. In the task state the four
  skills are therefore one tap further away, never unreachable. Its mark is
  four small squares in the four skills' colours.
- A screen names its primary by `data-primary` on the button, and the shell
  sets that button in the action bar (it keeps its place in the screen's
  markup and Tab order). Today Täna (*Alusta*), Kirjutamine and Kuulamine
  (*Kontrolli*) do. A screen enters the task state by holding a rendered
  `data-dock-task` element (S8's session item while it awaits an answer); a
  focused text field with the keyboard up does the same. With no primary, the
  task row holds the skills key alone, so the four skills stay one tap away.
- The dock is opaque `sheet` with a `line` top rule; no blur, no shadow.
- Kursus, Kordamine, Eksam, Sõnavara, Töövihikud, Edenemine, Profiil and the
  appearance switch (*Süsteem*, *Hele*, *Tume*) live in **Veel**, a sheet
  opened from the header. On a desktop the sheet opens beside the sidebar and
  lists only what the sidebar does not.
- With the on-screen keyboard open, the task row rides on top of the keyboard
  (see **Focus and the dock**).

### Desktop action row

The primary action sits at the right end of an action row at the bottom of the
content column: `position: sticky; bottom: 0` on the `sheet` (inside the bench)
or the `ground` (elsewhere). It rests directly after short content and sticks
to the viewport bottom when content is longer. The row is a direct child of
the bench or the content column, never wrapped in an element of its own: a
sticky element moves only within its containing block, so a wrapper as short
as the row would leave it below the fold on a long page. A secondary action
(Jäta vahele, the "checked by" line) sits at the left end. Enter in an answer
field triggers the primary.

### Header

- Phone: the mark (28px) with *Klint*, then **Veel** and the Profiil key at
  the right. The page title stays the first heading of the content: it is the
  page's own heading, which a screen reader and the screens' journeys find
  there, and repeating it in the header would either read it twice or hide
  the real one. During a session the left control is **Peata** ("пауза";
  progress is kept), which S8 places.
- Desktop: no header bar; the page title is the first element of the content
  column (Title role). The sidebar holds Klint, then Täna, Kursus, Kordamine
  (with its due count), Eksam; then *Oskused* and the four skills; then Veel,
  and the Profiil and appearance keys, at the bottom. Items are one line,
  44px: label and gloss on one baseline (a gloss too long for the column wraps
  whole to a second line). Selected: `sheet` fill and a 3px ink bar at the
  left. The sidebar is the viewport's height and scrolls inside itself when it
  is taller.
- A skip link, *Sisu juurde* "к содержанию", is the first thing Tab reaches.
  It moves focus to the open screen's heading and leaves the route as it is.

## Elevation and shape

- Flat by default. The only shadow belongs to sheets and the word card:
  light `0 -12px 32px -16px rgba(21,32,26,.28)` plus a `line` edge; dark
  theme uses `line` alone, because shadows vanish on dark grounds.
- Corners: 14px for the bench, sheets and the primary button; 10px for
  secondary buttons, fields, segments and keys; 6px for chips and navigation
  items. Tables and rows are square.
- Hairlines (`line`, 1px) separate rows. A row list never sits inside a card
  unless it is an opened group (the current unit on Kursus).
- No translucency: reduced-transparency needs no fallback because nothing is
  translucent except the scrim.

## The signature: interlinear word

The component that makes Klint recognisable. It is used wherever one Estonian
form is the point: the item gap, the correction, the rule page's contrast
example, the review card and the form switch.

```
   Ta ei leidnud rahakotti.
                 ‾‾‾‾‾‾‾‾‾        ← the bar: 0.09em, ink; moss or cranberry after a check
                 osastav  частичный падеж
                 └ form name (Estonian, ink-2, 600, cut 60)
                           └ its gloss (Russian, gloss colour, cut 0)
```

**Anatomy.** The word (prompt role) with a bar under it; the form line under
the bar: the Estonian form name, then its Russian gloss, or the lemma and its
meaning before a check.

**Placement.** The form line is absolutely positioned at the word's start
(`top: 100%`, `white-space: nowrap`). It never widens the word, so the sentence
keeps its spacing. The prompt's tall line height (2.5 desktop, 2.6 phone)
reserves the band it sits in, so revealing it moves nothing. If two words in
one sentence carry form lines that would collide, the sentence switches to
stacked layout: each glossed word becomes an inline column, as in a printed
interlinear text.

**States.**

| State | Word | Bar | Form line |
|---|---|---|---|
| Awaiting | The gap field | none (the field border) | Lemma and Russian meaning |
| Right | The learner's form | `good`, 3px | Form name and gloss |
| Wrong, first miss | The gap field, value kept | none | Lemma and meaning; the hint appears in the correction region |
| Wrong, revealed | The key | `bad`, 3px | Form name and gloss |
| Notice (Täna, rule walk) | The form | ink, 2px | none: the learner has not tried yet |
| Reference (rule page) | The form | ink, 2px | Form name and gloss |

**Data contract.** The form name comes from code only: the item's form label
(`label`), or the form its rule id names (the existing rule-to-form map behind
"eitus: osastav"), or Vabamorf's analysis of the key. A model never supplies
it. If code has no single form name for the key (an ambiguous analysis), the
form line shows the lemma and meaning and no form name. The Russian gloss of a
form name comes from the same fixed term list as every other gloss (one gloss
per Estonian term, `tests/test_ui_language.py`).

**Built.** `interlinear(form, item, {state})` in `eesti/web/js/core.js` writes
the word; its only source for the name is the item: `form_after` (a choice
topic's form, which the server withholds from `label` until the attempt) or
`label`. There is no parameter for a name, so nothing else can pass one in.
The gloss is the item's `form_ru` when the server gave one, else each term's
from the client's fixed list, the same one the instruction above an item uses.
`fitInterlinear(sentence)` stacks a sentence whose form lines would collide.
The word, the name and the gloss read as one unit ("rahakotti, osastav,
частичный падеж"). The stylesheet's `.il` sets the bar, places the line under
the word out of flow and gives a prompt that holds one the tall line height.

**Accessibility.** The word and its form line form one accessible unit:
"rahakotti, osastav, частичный падеж". The verdict region announces the result
once; the form line is not announced a second time.

## Practice rhythm

The item rhythm is unchanged in substance and is now one state machine shared
by guided practice, the rule walk's ask step, review and the exit check. ADR-0009
adds the retry: a first miss gets one retry with a hint; only the first attempt
counts for mastery and FSRS.

```
          type / choose                Kontrolli
 Awaiting ───────────────▶ Ready ─────────────────▶ Checking
    ▲                                                 │
    │ Proovi veel (first miss, guided practice only)  ├─ right ──────────▶ Right ─┐
    └──────────────────────── Hint ◀─ first miss ─────┤                           │
                                                      └─ second miss ───▶ Revealed┤
 Jäta vahele (any time before Checking) ─────────────────────────────▶ Skipped ───┤
                                                                     Edasi ◀──────┘
```

| State | Primary action | Correction region | Notes |
|---|---|---|---|
| Awaiting | **Kontrolli** "проверить", disabled until there is an answer | Empty, reserved | Disabled primary keeps the ink fill at 40 % opacity with its label; it never looks like a second button. |
| Checking | **Kontrollin…** after 300ms | Unchanged | Field and choices locked; no spinner. |
| Right | **Edasi** "дальше" | *Õige* "верно", the reason if the topic hides its form until now | The bead becomes a filled moss disc. |
| Hint (first miss) | **Kontrolli** | *Proovi veel* "попробуй ещё раз" and the hint from code | Field keeps the value, selected for editing. Exit check and review skip this state. |
| Revealed | **Edasi** | *Pole õige* "неверно", *Sinu vastus* with the learner's answer struck through, the reason, **Miks?** and **Reegel** | The sentence shows the key with its form line; the bead becomes a slashed cranberry ring. |
| Skipped | **Edasi** | *Vahele jäetud* "пропущено, без оценки" | A dash bead; no grade, no mastery. |

The correction region is reserved at 150px under the sentence (it scrolls
inside itself when longer) so the primary action and the sentence never move
between states. Under the reason, a muted line says what checked the answer:
*Kontrollis kood: Vabamorf ja ülesande võti* "проверено кодом". A model's
explanation (**Miks?**, Claude Haiku 5.5 per ADR-0008) appears below that in a
block with a dashed `edge` outline and the label *Selgitab mudel, ei hinda*
"объясняет модель, не оценивает", with the engine named. Nothing a model writes
uses `good` or `bad`.

## Screens

The four screens below are specified in full; every other screen inherits the
shell, the components and the rhythm. Example strings are the app's own
(generator items and the lesson for `obj-case`); counts in wireframes are
illustrative.

### Täna (Home, `#path`)

ADR-0009 makes Home the session: one **Jätka** with the session's shape, two
alternatives with one-line reasons, and nothing else competing.

```
Phone 390                                   Desktop 1280
┌──────────────────────────────────┐        ┌────────┬──────────────────────────────────────────────┐
│ ◆ Täna                      Veel │        │ Klint  │ Täna  сегодня                                 │
│   сегодня                        │        │        │ laupäev, 10. oktoober                         │
│ laupäev, 10. oktoober            │        │ Täna   │                                               │
│                                  │        │ Kursus │ Ma sõin jäätise ära.          │ Kordamine  6 │
│ Ma sõin jäätise ära.             │        │ Kordam.│         ‾‾‾‾‾‾‾               │ Reegel     8 │
│         ‾‾‾‾‾‾‾                  │        │ Eksam  │ Ma ei söönud suppi.           │ Harjutam. 10 │
│ Ma ei söönud suppi.              │        │        │              ‾‾‾‾‾            │ Sõnad      8 │
│              ‾‾‾‾‾               │        │ Oskused│ Почему jäätise, но suppi?     │ Kuulamine  1 │
│ Почему jäätise, но suppi?        │        │ Lugem. │ Сначала попробуешь сам,       │ Rääkimine  1 │
│ Сначала попробуешь сам, потом    │        │ Kuulam.│ потом прочитаешь правило.     │ Kontroll   5 │
│ прочитаешь правило.              │        │ Rääkim.│                               │              │
│                                  │        │ Kirjut.│ täissihitis ja osasihitis     │ Või          │
│ täissihitis ja osasihitis        │        │        │                               │ Kordamine    │
│ полное и частичное дополнение    │        │        │                    [ Jätka ]  │ 14 карточек… │
│ ──────────────────────────────── │        │        │                               │ Kuulamine    │
│ ● Kordamine            6 kaarti  │        │        │                               │ 6 дней без…  │
│   Reegel           8 ülesannet   │        └────────┴──────────────────────────────────────────────┘
│   … seven steps                  │
│ Või                              │
│ Kordamine  14 карточек ждут      │
│ Kuulamine  слух: 6 дней перерыва │
├──────────────────────────────────┤
│ [ Jätka  продолжить, 25 минут  ] │  action bar
│ Täna Lugem. Kuulam. Rääkim. Kirj.│  tab row
└──────────────────────────────────┘
```

- **Hero:** the first notice examples of today's rule step, display size, with
  the forms to notice underlined in ink and **no form names** (the learner
  chooses first; ADR-0009). A one-sentence Russian question built from a
  template names the two forms; it states no rule. If today's session has no
  rule step, the hero is the unit's title and goal.
- **Plan:** the seven steps in order with what each holds, the current one
  marked by an ink dot. A step done today is `muted` with a check.
- **Alternatives:** *Või* "или", then two links in `jarv`, each with its reason
  from code on the line below. They are links, not buttons: one primary.
- **Primary:** **Jätka** "продолжить", with the estimated minutes in the gloss.
  When today's session is done, the hero reports what was done and the primary
  becomes the next task code chose, with its reason as the gloss line under the
  hero.
- Removed from today's screen: the generic page title "Õpime eesti keelt", the
  starting-point link (moves to Profiil and Kursus), the note restating that
  skills exist.

### Kursus (`#course`)

```
Phone 390                                   Desktop 1280 (880px list)
┌──────────────────────────────────┐        ┌────────┬───────────────────────────────────────────────┐
│ ◆ Kursus                    Veel │        │        │ Kursus  курс                                  │
│   курс                           │        │        │ [Minu rada | Vaba harjutus]                   │
│ [ Minu rada | Vaba harjutus ]    │        │        │ Algus                                         │
│ Algus                            │        │        │  1  Tere!                         ■□□  1/3    │
│  1  Tere!                 ■□□    │        │        │     Поздороваться, поблагодарить…             │
│     Поздороваться, поблагодарить │        │        │   ┌───────────────────────────────────────┐   │
│  ┌────────────────────────────┐  │        │        │   │ ✓ tähestik ja hääldamine   пройдено   │   │
│  │ ✓ tähestik ja hääldamine   │  │        │        │   │ ◐ tervitused ja viisakus…  в работе   │   │
│  │   пройдено                 │  │        │        │   │ ○ arvud 0–100              открыто    │   │
│  │ ◐ tervitused ja viisakus…  │  │        │        │   │ Ühiku kontroll   Jäta ühik vahele     │   │
│  │ ○ arvud 0–100              │  │        │        │   └───────────────────────────────────────┘   │
│  │ Ühiku kontroll             │  │        │        │ A1                                            │
│  └────────────────────────────┘  │        │        │  2  Tutvume                       □□□□  0/4   │
│ A1                               │        │        │  3  Minu pere                     □□    0/2   │
│  2  Tutvume              □□□□    │        │        │ ───────────────────────────────────────────── │
│  3  Minu pere            □□      │        │        │                            [ Jätka: 1. ühik ] │
├──────────────────────────────────┤        └────────┴───────────────────────────────────────────────┘
│ [ Jätka: 1. ühik  продолжить   ] │
│ Täna Lugem. Kuulam. Rääkim. Kirj.│
└──────────────────────────────────┘
```

- Units grouped under their stage names as small `muted` headings (Algus, A1,
  A2, B1 — the course's own stages, not a CEFR claim about the learner).
- A unit row: number (tabular, `muted`), Estonian title (label role, 18px),
  Russian goal on the second line (one line, truncated with the full goal in
  the opened group), and a progress mark of one square per topic, moss when
  passed. The count "1/3" is text beside it on desktop and in the accessible
  name on phones.
- The current unit is open as a `sheet` group; others open on tap with the
  native `details` element (one open at a time is not enforced).
- Topic rows: status icon (the existing set: play, half, check, lock, arrow,
  book) and the Russian status word from the existing map; topic name in the
  sharp cut. Row actions (Õpi, Reegel, Kontrolli teadmisi, Jäta vahele) are a
  row menu, not four inline buttons.
- **Primary:** **Jätka** for the current unit. Free practice and the offline
  pack sit behind the segmented control and a disclosure, as now.

### The session (`#session/<topic>`)

```
Phone 390, awaiting                  Phone 390, revealed               Desktop 1280, revealed
┌────────────────────────────────┐   ┌────────────────────────────────┐ ┌────────┬────────────────────────────────────┐
│ ‹ Peata  täissihitis ja osas…  │   │ ‹ Peata  täissihitis ja osas…  │ │        │ ‹ Peata          täissihitis ja … │
│ Õpi  Harjuta          Kontrolli│   │ Õpi  Harjuta          Kontrolli│ │        │ ┌────────────────────────────────┐ │
│ ▂▂  ▬▭▭▭                ▭      │   │ ▂▂  ▬▭▭▭                ▭      │ │        │ │ Õpi Harjuta          Kontrolli │ │
│ ●●◎○○○○○○○                     │   │ ●●⊘○○○○○○○                     │ │        │ │ ▂▂ ▬▭▭▭                ▭       │ │
│ Впиши нужную форму.            │   │ Впиши нужную форму.            │ │        │ │ ●●⊘○○○○○○○                     │ │
│                                │   │                                │ │        │ │ Впиши нужную форму.            │ │
│ Ta ei leidnud [        ].      │   │ Ta ei leidnud rahakotti.       │ │        │ │ Ta ei leidnud rahakotti.       │ │
│               rahakott кошелёк │   │               ‾‾‾‾‾‾‾‾‾        │ │        │ │               ‾‾‾‾‾‾‾‾‾        │ │
│ ────────────────────────────── │   │               osastav частич…  │ │        │ │               osastav частич…  │ │
│                                │   │ ────────────────────────────── │ │        │ │ ────────────────────────────── │ │
│   (correction region, 150px,   │   │ ✕ Pole õige  неверно           │ │        │ │ ✕ Pole õige  неверно           │ │
│    reserved and empty)         │   │ Sinu vastus  ~~rahakott~~      │ │        │ │ Sinu vastus  ~~rahakott~~      │ │
│                                │   │ После «ei» объект всегда в     │ │        │ │ После «ei» объект всегда в     │ │
│                                │   │ osastav (частичный падеж)…     │ │        │ │ osastav (частичный падеж)…     │ │
│                                │   │ [Miks? объясни] [Reegel]       │ │        │ │ [Miks?] [Reegel]               │ │
│ Jäta vahele  пропустить        │   │ Kontrollis kood: Vabamorf…     │ │        │ │ ─────────────────────────────  │ │
├────────────────────────────────┤   ├────────────────────────────────┤ │        │ │ Kontrollis kood…     [ Edasi ] │ │
│ [⊞] [🎙] [   Kontrolli       ] │   │ [⊞] [        Edasi           ] │ │        │ └────────────────────────────────┘ │
└────────────────────────────────┘   └────────────────────────────────┘ └────────┴────────────────────────────────────┘
```

- **Session line:** seven segments for ADR-0009's steps, grouped under the
  three phase labels: **Õpi** (Kordamine, Reegel), **Harjuta** (Harjutamine,
  Sõnad, Kuulamine, Rääkimine), **Kontrolli** (Kontroll). Segments are 3px
  apart within a phase and 8px between phases. Done segments are `ink-2` and
  2px high on the line's baseline; the current segment is `ink` at the full
  6px; segments to come are `sunk` at 6px. The current step is the only tall
  dark segment, so shape tells it apart as well as tone (`ink` against `ink-2`
  alone is about 1.7:1). The current segment has `aria-current="step"` and the
  line's accessible name says "Samm 3/7: Harjutamine". When a step begins, its
  name appears once as the bench's heading; it is not repeated on every item.
- **Beads:** one bead per item of the current step, each in a 12px cell so a
  change of shape moves nothing. Every state has its own shape, which also
  survives forced colours:

  | Bead | Shape |
  |---|---|
  | Right | Filled 8px disc, `good` |
  | Wrong | 8px ring (2px) with a diagonal stroke, `bad` |
  | Skipped | 8×2px dash, `muted` |
  | Current | 10px ring (2px), `ink` |
  | To come | 8px ring (1px), `edge` |

  The beads are a list; each item's accessible text gives its position and
  result ("Ülesanne 2/10, pole õige"; "Ülesanne 4/10, vahele jäetud"), and the
  current one carries `aria-current="step"`.
- **Instruction:** one Russian sentence (body, `ink-2`). The lemma is not
  repeated in it: it is under the gap.
- **The gap is the field.** The answer is typed in the sentence: an inline
  input with `field-sizing: content` (Baseline since June 2026) and a minimum
  of 6ch, with the `size` attribute updated from the value as a fallback.
  Choice items show choices as full-width rows under the sentence (radio
  semantics; selecting fills the gap); tile items keep the line-and-bank
  construction with tap only (no drag requirement, WCAG 2.5.7).
- **Tõlge** (the on-demand translation) moves out of the way of the answer:
  a secondary button in the correction region before a check, labelled with
  its engine when shown.
- **Microphone:** a 52px key in the task row when speech input is available;
  recording turns the key `bad` with a static dot and an elapsed-time counter.
- **Jäta vahele** is a secondary button at the bottom-left of the bench
  (desktop) or at the end of the correction region (phone), never beside the
  primary.
- **Bench:** desktop only. On phones the screen is the surface.
- **Step intros** (Kuulamine, Rääkimine): the bench heading, one sentence of
  purpose, then the step's own content with the same primary location. The
  exit check states that it has no hints and counts once.
- **Session end:** a summary on the ground: what was done per step in plain
  counts, missed items as a short list of interlinear corrections, the next
  task code chose with its reason as the primary, two alternatives as links.
  No score theatre: the exit check result is "4/5", nothing larger.

### Reegel (`#rule/<topic>`)

The rule page is a page with a back control, not a modal with a close cross.
S3's rule walk (notice, ask, explain, contrast) leads when the topic has one.

```
Phone 390                                   Desktop 1280 (720px sheet)
┌──────────────────────────────────┐        ┌────────┬─────────────────────────────────────────────┐
│ ‹ Tagasi                         │        │        │ ‹ Tagasi                                    │
│ täissihitis ja                   │        │        │ ┌─────────────────────────────────────────┐ │
│ osasihitis                       │        │        │ │ täissihitis ja osasihitis               │ │
│ полное и частичное дополнение    │        │        │ │ полное и частичное дополнение           │ │
│ Allikas: EKK SÜ 38, SÜ 40,       │        │        │ │ Allikas: EKK SÜ 38, EKK SÜ 40, EKI …    │ │
│ EKI teatmik                      │        │        │ │                                         │ │
│                                  │        │        │ │ Täissihitis (полное дополнение) — целый │ │
│ Täissihitis (полное дополнение)  │        │        │ │ объект и действие, которое достигло или │ │
│ — целый объект и действие,       │        │        │ │ достигнет результата; форма — omastav…  │ │
│ которое достигло или достигнет…  │        │        │ │ [lõpetatud|kestev|eitus|mitmus|käskiv]  │ │
│ [lõpetatud|eitus|mitmus|käskiv]  │        │        │ │ Ma sõin jäätise ära.                    │ │
│ Ma sõin jäätise ära.             │        │        │ │         ‾‾‾‾‾‾‾                         │ │
│         ‾‾‾‾‾‾‾                  │        │        │ │         omastav родительный падеж       │ │
│         omastav родительный п.   │        │        │ │                                         │ │
│                                  │        │        │ │ Vormid (table, labelled rows sticky)    │ │
│ Vormid      (table)              │        │        │ │ Näited, Minu vead, Loe                  │ │
│ Näited                           │        │        │ │ Lisaks: 5 punkti  (disclosure)          │ │
│ Minu vead                        │        │        │ │ ───────────────────────────────────     │ │
│ Lisaks  ▾                        │        │        │ │                            [ Harjuta ]  │ │
├──────────────────────────────────┤        │        │ └─────────────────────────────────────────┘ │
│ [ Harjuta  упражняться         ] │        └────────┴─────────────────────────────────────────────┘
│ Täna Lugem. Kuulam. Rääkim. Kirj.│
└──────────────────────────────────┘
```

- **Head:** title (Title role, sharp cut), Russian name, and the sources line
  directly under it — attribution is visible before the content, not after
  2,000 pixels.
- **Gist:** one sentence, lead role: the first sentence of the topic's
  sourced summary (`summary_ru` in `eesti/grammar.py`, here EKK SÜ 38), which
  glosses each Estonian term once. It is never a tip from `TIPS` in
  `eesti/lessontext.py`, the unsourced kind retired below. Its measure is the
  sheet's, within the 45–75 characters of **Typography**.
- **Form switch** (S3): a segmented control of conditions; the example
  sentence changes and the object word's interlinear line shows the form that
  follows. Every form from Vabamorf; a condition with no Vabamorf form for the
  sentence is not offered.
- **Forms table:** full width of the sheet; row labels sticky when it scrolls
  sideways; the scroll edge marked by an `edge` rule, not a gradient.
- **Points:** the first three visible; the rest in a disclosure *Lisaks*
  "подробнее". Estonian examples inside Russian points are upright, sharp cut,
  weight 500 — not italic.
- **Unsourced tips go.** The gist-and-typical-mistake card is shown only as a
  sourced contrast note (ADR-0009); until then it is absent.
- **Primary:** **Harjuta** "упражняться". The page's other actions are links.

## Components

### Buttons

| Kind | Look | Use |
|---|---|---|
| Primary | `act` fill, `on-act` label (action role) with its gloss at 80 %, 52px high in the action bar, 48px inline, 14px corners | One per screen, in the action bar or row |
| Secondary | No fill, 1px `line` border (1px `edge` in high contrast), `ink` label, 44px, 10px corners | Miks?, Reegel, Tõlge, Jäta vahele |
| Text action | No box, `ink-2` label underlined in `edge`, 44px target | Row actions, "Vali teine teema" |
| Key | 52px square, 1px `edge` border, 24px pictogram | Skills key, microphone, play |
| Link | `jarv`, underlined, 44px target where it stands alone | Alternatives, sources, "back to" links |

Hover darkens the primary to `act-hover`; press scales it to .98. Disabled is
40 % opacity with the label kept and `aria-disabled`, so the reason can still
be announced. Every target is at least 44×44 (above WCAG 2.5.8's 24×24).
Links keep their underline in running text: colour alone would not tell them
apart (WCAG 1.4.1).

### Fields

Fields are `sheet`, 1px `edge` border, 10px corners, 48px. Focus: the `focus`
ring (below), border to `ink`. The gap field uses the prompt role and sits in
the sentence's line. Labels sit above fields with the gloss on the same line.
Placeholders are `muted` at full opacity and never the only label.

### Choices and segmented controls

Choice rows: `sheet`, 1px `edge`, 10px corners, at least 52px, Estonian in the
sharp cut; selected gets a 2px `ink` border and a check. Segmented control:
`sunk` track, 4px padding; the selected segment `sheet` with a 1px `edge`
outline. Both use roving focus and `aria-selected` or `aria-pressed`.

### Lists and rows

Rows are 56–64px with a `line` rule under each, content left, a single trailing
element right (count, status, chevron for a row that opens). No row is a card.

### Sheets

Veel, Oskused, the word card and confirmations are bottom sheets on phones
(native `dialog`, modal, focus trapped and returned) and anchored popovers or
centred dialogs on desktop. Detents: half and full on phones; the word card
opens at half. A sheet opens on the current entry (or its first), closes with
Escape, its close key or a tap on the scrim, and gives focus back to what
opened it. Veel keeps its `<details>` summary as the opener, so the sheet and
the summary's open state follow each other.

### Word card

Unchanged in content (meaning first, EVS examples, forms on request, sources);
its headword uses the interlinear treatment for the tapped form in context
(*mulle*, form line "mina, alaleütlev"). Owned by S9.

### Banners and empty states

A banner is a left 3px rule in its state colour, the state's mark (a circled
exclamation for caution, a circled cross for an error, a circled *i* for
information, a circled tick for good news; drawn as CSS masks, so they need no
markup) and text in `ink`; no tinted box. The mark, not the hue, says which
kind it is. An empty state is one sentence saying what will appear and one
action to make it appear, left-aligned, no illustration.

### Loading and errors

Content that takes longer than 400ms shows *Laadin…* "загружаю" in its slot
(`skeleton()` in `eesti/web/js/chrome.js`; the note is there at once but shown
only after 400ms); nothing shimmers. An error says what failed and keeps the learner's input on screen,
with a retry as the slot's action (not a second primary).

### Model output

Any text a model wrote (Miks?, writing feedback, conversation partner, a
model-drafted gloss) sits in a block with a dashed 1px `edge` outline and a
first line naming the engine. It never uses `good` or `bad` and never shows a
score.

## Motion

Motion exists only to answer an action or show a state change. Tokens follow
Material 3's standard and emphasized curves; durations stay at or under 320ms.

| Token | Value | Use |
|---|---|---|
| `dur-1` | 100ms | Press response |
| `dur-2` | 160ms | Selection, label swap, exit |
| `dur-3` | 240ms | Verdict, form line, scrim |
| `dur-4` | 320ms | Item change, sheet, step fill, dock change |
| `ease-standard` | `cubic-bezier(.2,0,0,1)` | State changes in place |
| `ease-enter` | `cubic-bezier(.05,.7,.1,1)` | Something arriving |
| `ease-exit` | `cubic-bezier(.3,0,.8,.15)` | Something leaving |

No springs, no overshoot, no oscillation.

### Inventory

| Motion | Trigger | Purpose | What changes | Duration, easing | Reduced motion | Forced colours |
|---|---|---|---|---|---|---|
| Press | Pointer or key down on a button | Confirms the press registered | Fill to hover tone; primary scales to .98 | `dur-1`, standard | Fill change only, no scale | No change; system button colours |
| Select | A choice, segment, tab or nav item chosen | Shows what is selected now | Fill and border | `dur-2`, standard | Instant | `Highlight` fill appears |
| Checking | Kontrolli pending over 300ms | Shows the answer is being checked | Label crossfades to *Kontrollin…* | `dur-2`, standard | Instant swap | Text only |
| Verdict | Result arrives | Puts the result where the learner is looking | Bar colour; form line fades in rising 4px; correction content fades in; bead fills | `dur-3`, enter | Opacity only, no rise | Icon, words and strike-through carry it |
| Relabel | Kontrolli becomes Edasi | Names the next action without moving it | Label crossfade; button fixed | `dur-2`, standard | Instant | None |
| Hint | First miss | Invites self-correction | Hint fades in; field value stays selected | `dur-3`, enter | Opacity only | Text |
| Next item | Edasi | Old item done, new one here | Same-document View Transition: old fades out, new fades in rising 8px; focus moves to the new gap | out `dur-2` exit, in `dur-4` enter | Crossfade `dur-2`, no translation | None |
| Step change | First item of a new step | Orients within the session | Segment fills from the left (`scaleX`); step heading fades in | `dur-4`, standard | Instant fill | Segment border fills with `CanvasText` |
| Form switch | A rule condition toggled | Shows which form follows from which condition | The word and its form line crossfade; nothing else moves | `dur-3`, standard | Instant | Bar is a border; stays |
| Sheet | Veel, Oskused, word card | Shows the sheet comes from the dock and the page waits behind it | Sheet slides up (beside the sidebar on a desktop, 16px); scrim fades | open `dur-4` enter; closes at once | Fade only, `dur-2` | Sheet border `CanvasText`; no scrim |
| Dock change | Task starts, field focused, task ends | Makes room for the primary and the keyboard | Tab row collapses, skills key appears | `dur-4`, standard | Instant | None |
| Disclosure | `details` toggled | Shows the content opened | Chevron rotates; content appears without height animation | `dur-2`, standard | Instant | Chevron in `CanvasText` |
| Recording | Microphone on | A state that must stay visible while it lasts | Static `bad` dot, elapsed seconds tick | No transition: a discrete tick each second, so no duration or easing | Same | Word *Salvestan* and border |
| Focus | Any focus | Shows where the keyboard is | Ring appears | Instant, never transitioned | Same | `Highlight` |

**Removed** from the app: the pulsing current bead, the shimmer skeleton, the
celebration overlay with petals (mastery is announced through the polite live
region only), grow-in animations on charts and meters, the readiness flower's
petal animation, the pulsing recording dot, the audio player's spinning
loader (a still dashed ring now) and the page-wide smooth scrolling.

Reduced motion is one switch in the tokens: `--rise` and `--press` go to none,
so every rise becomes a plain fade and a press changes colour only, and every
transition takes no time.

View Transitions are Baseline for same-document updates (Firefox 144, October
2025); where unsupported, the new item simply replaces the old.

## Focus and the dock

WCAG 2.2 requires that a focused component is not entirely hidden by
author-created content ([SC 2.4.11](https://www.w3.org/TR/WCAG22/#focus-not-obscured-minimum)).
Klint holds the stricter bar of
[SC 2.4.12](https://www.w3.org/TR/WCAG22/#focus-not-obscured-enhanced): no part
of a focused element is under the dock, the action bar, the header or the
keyboard.

1. The dock publishes its current height (`--dock-h`, measured after every
   change of state, size or screen) and the keyboard's (`--kb`). `html` has
   `scroll-padding-bottom: calc(var(--dock-h) + var(--kb) + 16px)` and
   `scroll-padding-top` equal to the sticky header, so the browser's own focus
   scrolling stops clear of both; the page's bottom padding is the same sum, so
   the last control can always be scrolled above them.
2. On `focusin`, once the page has stopped moving (three still frames, so a
   screen's own smooth scroll or Safari's scroll to the field has landed and
   the dock has taken its new state), an element that meets the header, the
   tab row, the action bar, the primary or the keyboard is scrolled instantly
   into the band between them. While the keyboard is up, the same happens after
   the screen changes (text arriving above the field moves it), and for a
   second after the keyboard arrives at every change of the visual viewport:
   iOS raises the keyboard after the field takes focus and pans the page while
   it slides in. Focus scrolling is never smooth: the page sets no
   `scroll-behavior`.
3. When a text field is focused and the keyboard is up, the dock enters the
   task state and sits on the keyboard. Both engines are read the same way:
   Safari keeps a full-height layout viewport, and Chromium has done the same
   by default since version 108, so the keyboard's height is
   `innerHeight − visualViewport.height − visualViewport.offsetTop`, read on
   the visual viewport's `resize` and `scroll` events and on focus. Whether a
   keyboard is up is read from how much the visual viewport shrank (over
   120px), not from where it sits: as the keyboard slides in, Safari pans the
   visual viewport to the bottom of the layout viewport, and the formula above
   is then 0. Pinch zoom (a scale other than 1) never counts, which is why no
   page may be wider than the screen: Safari zooms such a page out when a field
   takes focus. The viewport meta asks for no `interactive-widget`, which keeps
   one path and lets the journeys stub it.

   **Compact keyboard state.** When the visual viewport is under 320px high
   with a text field focused (a phone in landscape), the header stops being
   sticky and scrolls away with the content (`scroll-padding-top: 0`; on its
   side a phone's header always scrolls with the page), the task row drops to
   60px with 44px keys and a 44px primary, and a multi-line field is set to the
   band that remains (`--band`, scrolling inside).
   At 874×402 with a keyboard of about 200px (Apple does not publish its
   height), the band is then 402 − 200 − 60 − 16 = 126px, which holds the
   prompt line with its form line (24px at 2.6, about 62px). Without this
   state it would be 402 − 200 − 56 − 76 − 16 = 54px, less than one prompt
   line.
4. The tab row is part of the header in document order, because one element is
   both the desktop sidebar and the phone's dock; the four skills are a
   tablist, so they cost one Tab stop. A skip link, *Sisu juurde*, comes first.
   The primary keeps its place in its screen's markup, so Tab reaches the
   answer and then the primary; the skills key comes after the content. Enter
   in the gap submits.
5. Sheets opened from the dock trap focus and return it to their opener.
6. Focus ring: 3px `focus` outline, 2px offset, on every interactive element,
   on all grounds. A heading that receives programmatic focus after a route
   change (`tabindex="-1"`) shows no ring; interactive elements always do.

**Test.** A browser journey (`tests/test_e2e_journeys.py`) at 390×844 and
874×402 (touch) and 1280×800, on Chromium and WebKit, tabs through every
focusable element on Täna, Kursus, `#session` (awaiting and revealed) and
`#rule`, and for each asserts that `elementFromPoint` at the element's centre
(each line's, for a link that wraps) is the element or inside it and that its
rectangle meets neither the header, the tab row, the action bar nor the
primary. WebKit tabs with Option, since Safari's plain Tab skips links unless
the learner turns that on. Playwright opens no on-screen keyboard, so the
keyboard cases run through a stub: the journey replaces `visualViewport` with
one whose height is the viewport less an assumed keyboard (340px at 390×844,
200px at 874×402), fires its `resize` event, focuses each answer field (free
practice, Kirjutamine, Kuulamine) in both orders — the keyboard arriving
after focus, as on iOS, and focus moving with the keyboard already up — and
asserts the same conditions inside the stubbed band, that the tab row has
given way, that the primary sits above the keyboard, that the skills key opens
the skills and that no page is wider than the screen. The same three fields
were checked by hand with the software keyboard in Safari on the iOS 27
simulator (iPhone 18 Pro) on 10 October 2026.

## Accessibility checklist (WCAG 2.2 AA)

- 1.4.3 and 1.4.11: the contrast table above, both themes.
- 1.4.4, 1.4.10, 1.4.12: type in `rem`; one column at 320px with no horizontal
  page scroll (tables scroll inside themselves with sticky row labels); text
  spacing overrides do not clip the form line, whose band is relative.
- 2.4.7, 2.4.11: focus ring and the dock rules above.
- 2.5.7: tile building works by tapping; drag is optional.
- 2.5.8: targets 44×44 or larger.
- 3.2.6 Consistent Help: **Miks?** and **Reegel** stay in the same place in
  the correction region on every item.
- 3.3.7 and 3.3.8: sign-in accepts paste and password managers; nothing asks
  the learner to retype what the app already has.
- `lang` on every Estonian element, `lang="ru"` on glosses (checked by
  `tests/test_ui_language.py`).
- Reduced motion, reduced transparency (nothing translucent), forced colours
  and `prefers-contrast: more` as specified above.

## Explanation languages

Klint teaches Estonian in Russian, English and Ukrainian. Estonian material,
labels, keys and progress are shared; explanations, glosses, instructions,
warnings and accessible names follow the learner's explanation language.
Russian is the MVP and the language of this record's examples; every rule here
applies equally to Ukrainian and English.

**Default.** On first run the web app reads `navigator.languages` and the iOS
app its preferred languages (honouring a per-app language set in iOS
Settings), and takes the first whose primary subtag is `uk`, `ru` or `en`;
none matching gives English. A Russian speaker whose system is set to Estonian
first (`et-EE, ru`) therefore gets Russian. The result is preselected in
onboarding's first question, changeable in Profile at any time, and a saved
choice always wins over detection. Location is never used to guess a language.

**Markup.** The document's `lang` is the explanation language; Estonian
elements carry `lang="et"`; every gloss carries the explanation language's
code, so screen readers switch voices correctly in all three languages.

**Layout.** No component may depend on the length of one language's strings.
Russian and Ukrainian strings are often longer than English ones: primary
labels keep the gloss on one line and truncate nothing (the gloss wraps under
the label in the action bar before it is clipped); tab glosses use the shortest
established term per language from the term catalogue; the correction region
scrolls inside itself rather than growing. Every screen is checked in all three
languages at 390px, and the phone tab row also at 320px.

**Missing translations.** Where reviewed text is missing in the chosen
language, the slot says so in that language and offers the Russian text as an
explicit choice; it is never silently replaced (`PRODUCT.md`).

**Type.** The bundled Geologica Cyrillic subset covers Ukrainian letters (і, ї,
є, ґ) and the apostrophe; English needs only the Latin subset.

## iOS

The planned iPhone and iPad app is native SwiftUI on iOS 26, sharing the API,
the learning rules and these tokens. The web stays the PWA.

**Tokens.** The frontmatter above is the single source. A generator writes it
as a Design Tokens Community Group file (format 2025.10, the first stable
version), and from that the CSS custom properties for the web and an Asset
Catalog of colour sets (Any and Dark appearances, plus Increase Contrast
variants from the `prefers-contrast` rules) with Swift constants for spacing,
radii and durations for iOS.

**Type.** Geologica's variable font is bundled (the OFL permits embedding; its
licence text ships with it). The `SHRP` axis is set through a font descriptor's
variation attributes; each type role scales with Dynamic Type through
`UIFontMetrics` relative to the nearest text style (prompt to `.title`, body to
`.body`, gloss to `.caption1`).

| Web | iOS |
|---|---|
| Phone dock, browse state | `TabView` with five tabs: Täna and the four skills |
| Desktop sidebar | `TabView` with `.sidebarAdaptable` on iPad |
| Action bar (act state) | A per-screen `safeAreaInset(edge: .bottom)` above the tab bar |
| Task state | The session as a `fullScreenCover` with its own bottom bar and a toolbar button for the skills; system keyboard avoidance |
| Veel | A toolbar menu opening a sheet with medium and large detents |
| Täna | `ScrollView` root of the Täna tab |
| Kursus | `NavigationStack` with an inset-grouped `List`, sections per stage |
| `#session` | The full-screen flow; the step container switches views; same state machine |
| `#rule` | A pushed detail view; the form switch as `Picker` (segmented); the table as `Grid` |
| Word card | `.sheet` at the medium detent |
| Interlinear word | A lone word: `Text` with the form line overlaid on an alignment guide. A sentence with a gap field: a custom `Layout` (iOS 16+) that flows one view per word, so the field and each form line sit at their word and wrap with the line. A read-only sentence: `Text` with a custom `TextAttribute` on the glossed run and a `TextRenderer` (iOS 18+) that draws the bar and the form line under it. Each glossed word is one accessibility element ("rahakotti, osastav") |
| Motion tokens | `Animation.timingCurve(0.2, 0, 0, 1, duration: 0.16)` and peers; `accessibilityReduceMotion` swaps movement for opacity |
| Verdict feedback | `sensoryFeedback(.success)` on right; a light impact on a miss; nothing on skip |
| Materials | Liquid Glass only where the system draws it (tab bar, toolbars); content stays solid, as on the web |
| Explanation language | `uk`, `ru`, `en` localizations declared so iOS offers a per-app language; the default from `Bundle.main.preferredLocalizations` and preferred languages, as on the web; a saved choice wins |

Apple's own guidance places Liquid Glass in the navigation layer and asks that
motion communicate and never be the only carrier of information; the web
system follows the same split, so the two apps read as one product.

## Migration

The redesign lands screen by screen. Each step keeps the browser journeys
green on both engines and both viewports.

1. **Tokens.** Done (S10). This record's roles are the root custom
   properties in `eesti/web/app.css`, light and dark, with the
   `prefers-contrast`, reduced-motion and forced-colours rules above. Every
   rule reads the roles, with type in `rem` on the scale; the shipped
   interface's earlier token names are gone, so no alias is kept.
   The two cuts follow the markup's languages: `[lang="et"]` takes `--et-cut`
   (`SHRP` 60, or 100 inside a display or prompt), the explanation languages
   and every `.ru` gloss take `SHRP` 0.
2. **Shell.** Done (S10). Header, sidebar and rail, dock states, action bar,
   Veel and skills sheets, focus rules (`eesti/web/index.html`,
   `eesti/web/js/chrome.js`). The interlinear word is a component with its
   helper (`interlinear()` in `eesti/web/js/core.js`) for the screens that
   follow.
3. **Session and Täna** with S8's session (`eesti/web/js/path.js`), including
   the interlinear word and the state machine.
4. **Reegel** with S3's rule walk (`eesti/web/js/lesson.js`).
5. **Kursus**, then the skills, Kordamine, Eksam and Profiil.
6. **Brand.** Done with the rename: the underlined K, spruce tiles and birch
   social artwork ship, rebuilt by `deploy/build-brand.py` (`docs/brand.md`).
   The manifest, `theme-color` and the offline page stand on the ground
   (step 1); the manifest takes its colour from the page's `theme-color`.

When a step lands, the same change updates the documents that describe the
shipped interface: `docs/status.md` (Interface), `docs/brand.md`, the visual
system line in `PRODUCT.md` and the Practice rhythm sentence in
`.claude/rules/web.md`.

## Do's and Don'ts

### Do

- Do show a form's name under the word, from code, at the moment it helps.
- Do keep one primary action per screen in the action bar or the action row.
- Do pair every result colour with a shape and a word.
- Do set Estonian in the sharp cut with `lang="et"`, the explanation language
  in the soft cut with its own `lang`.
- Do keep sources visible near the top of any rule or text.
- Do label every model's words with the engine, outside the result colours.
- Do keep the four skills one tap away in the browse and act states, and
  behind the skills key (one tap more) during a task.
- Do test focus against the dock at phone sizes in both orientations.

### Don't

- Don't use any forbidden default listed above.
- Don't reveal a form name before the learner has tried (notice comes first).
- Don't show two primary-looking buttons at once, including a disabled one.
- Don't put a correction in a separate paragraph when it can sit at the word.
- Don't animate anything the learner did not cause, or loop anything but a
  recording clock.
- Don't use colour for a language: an explanation is not grey because it is
  Russian, Ukrainian or English; it is `muted` only where it is a gloss.
- Don't treat a trend, a competitor or visual freshness as evidence of better
  learning.
