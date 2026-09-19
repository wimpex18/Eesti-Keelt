---
name: Eesti keel
description: A calm, modern daily study tool on the path to the Estonian A2/B1 exam.
colors:
  estonian-forest: "#1c6b52"
  forest-deep: "#12503c"
  forest-mist: "#e6f2ec"
  on-forest: "#ffffff"
  gloss-slate: "#4c6382"
  amber-note: "#9a5b00"
  amber-wash: "#fdf3e3"
  correction-red: "#a32c2c"
  paper: "#faf9f6"
  sheet: "#ffffff"
  ink: "#1b1b19"
  ink-soft: "#4a4a45"
  pencil: "#6b6b66"
  rule-line: "#e3e3de"
  rule-faint: "#efeee9"
  tint: "#f4f3ee"
typography:
  display:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "clamp(28px, 8vw, 44px)"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "21px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.022em"
  title:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "15px"
    fontWeight: 650
    lineHeight: 1.4
  reading:
    fontFamily: "Iowan Old Style, Palatino Linotype, Palatino, Georgia, serif"
    fontSize: "17.5px"
    fontWeight: 400
    lineHeight: 1.8
  prompt:
    fontFamily: "Iowan Old Style, Palatino Linotype, Palatino, Georgia, serif"
    fontSize: "18.5px"
    fontWeight: 400
    lineHeight: 1.6
  lead:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "19px"
    fontWeight: 650
    lineHeight: 1.2
  input:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.4
  ui:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  body:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  note:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.06em"
  gloss:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  tag: "5px"
  tile: "10px"
  control: "12px"
  card: "14px"
  panel: "18px"
  pill: "999px"
spacing:
  s1: "4px"
  s2: "8px"
  s3: "12px"
  s4: "16px"
  s5: "24px"
  s6: "32px"
components:
  button-primary:
    backgroundColor: "{colors.estonian-forest}"
    textColor: "{colors.on-forest}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "10px 18px"
    height: "44px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 18px"
    height: "44px"
  button-ghost-hover:
    backgroundColor: "{colors.forest-mist}"
    textColor: "{colors.estonian-forest}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
    height: "44px"
  skill-chip:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.pencil}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "44px"
  skill-chip-selected:
    backgroundColor: "{colors.forest-mist}"
    textColor: "{colors.estonian-forest}"
  panel:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "22px 24px"
  drill:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.card}"
    padding: "24px 16px"
  choice:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tile}"
    padding: "10px 13px"
  choice-picked:
    backgroundColor: "{colors.forest-mist}"
  tag:
    backgroundColor: "{colors.forest-mist}"
    textColor: "{colors.estonian-forest}"
    rounded: "{rounded.tag}"
    padding: "2px 7px"
  banner-warn:
    backgroundColor: "{colors.amber-wash}"
    textColor: "{colors.amber-note}"
    rounded: "{rounded.control}"
    padding: "12px 14px"
---

# Design System: Eesti keel

## Overview

**Creative North Star: "The Language Path"**

A simple, modern study tool for learning Estonian day to day. Three clear modes (Õppimine, Kordamine, Eksam) make it obvious where you are and easy to switch between practice, review and, later, A2/B1 exam preparation. Progress shows lightly: a ring, a count, a mastered badge. It should feel good to move along the path, but it is never a game and never a sterile exam booth.

The world is warm paper and one forest-green ink. The interface speaks in the system sans. The language itself (reading texts, drill prompts) is set in a book serif, so Estonian material always looks like material, not chrome. Density is moderate: one reading column of about 720px. On a phone it becomes a thumb-first stack with the three modes at the bottom. On a wide screen it becomes a three-column desk. Estonian labels carry a small Russian gloss beneath them. The gloss is part of the typography, not an afterthought.

Surfaces sit low and quiet. They answer the hand with small physical cues: a card lifts 1px, a primary button presses into its darker bottom edge. Depth exists only where it responds to touch; everything else is flat.

**Key Characteristics:**
- One accent hue (Estonian Forest), used for action, the correct form and success.
- Colour by role: slate means a word's meaning, amber is a caution or the object-case weakness, red is the struck-out wrong form.
- A serif for Estonian material, the system sans for the interface, and no webfonts.
- Estonian label first, Russian gloss beneath in small muted type.
- Clear, modern, lightly motivating: progress is visible but quiet.

## Colors

A warm off-white paper with near-black ink and a single deep forest green. Every other hue is a semantic role, never decoration. The dark theme mirrors each role one-for-one (values in `eesti/web/app.css` and `.impeccable/design.json`).

### Primary
- **Estonian Forest** (`--accent`): the only accent. It marks primary actions, the selected tab, the correct inserted form, the drill blank, mastered and in-progress path states, focus rings, caret, selection and the select chevron.
- **Forest Deep** (`--accent-deep`): the pressed bottom edge of primary buttons, and text in success banners.
- **Forest Mist** (`--accent-soft`): the selected-chip fill, hover fill, tag fill, picked choice and empty-state mark.
- **On Forest** (`--on-accent`): text on a filled forest button. It is white in light mode and dark in dark mode, because white on mint fails contrast.

### Secondary
- **Gloss Slate** (`--gloss`): what a word *means*, and only that: glosses, definitions, examples, the flashcard meaning, and reference topics on the path.

### Tertiary
- **Amber Note** (`--warn`) with **Amber Wash** (`--warn-soft`): warning banners, missed dictation words, "hard" words in reading, the `obj-case` correction stripe, and exam parts not yet ready.
- **Correction Red** (`--bad`): the struck-through wrong form, a wrong verdict, and the recording dot. It is kept rare on purpose.

### Neutral
- **Paper** (`--bg`): the page, and the recessed insets inside a panel (drills, choices, inputs, list rows).
- **Sheet** (`--panel`): panels, rail cards and chips: the raised surfaces.
- **Ink** (`--ink`): primary text. **Ink Soft** (`--ink-2`): subtitles that must be read. **Pencil** (`--muted`): hints, meta, glosses under labels, inactive tabs.
- **Rule Line** (`--line`): every 1px border. **Rule Faint** (`--line-soft`): dividers inside a card. **Tint** (`--tint`): skeletons, the info banner, segmented fills.

### Named Rules
**The One Forest Rule.** There is one accent hue. Depth is built within that hue, never with a second colour. Success is also forest (`--good` equals `--accent`), so green always means "right" or "go".

**The Colour-by-Role Rule.** A colour belongs to an information role, not to a language. Slate is meaning, amber is caution, red is wrong. Russian text is not coloured because it is Russian.

**The Never-Hue-Alone Rule.** Every state that has a colour also has an icon or a shape: path states, exam-part marks and external (dashed) rows.

## Typography

**Interface Font:** the system sans (`ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto`)
**Reading Font:** Iowan Old Style (with Palatino and Georgia as fallbacks)

**Character:** A neutral native sans for everything the app says, and a warm book serif for everything the language says. No webfont is requested.

### Hierarchy
Every size is a token in `eesti/web/app.css` (`--fs-*`). Ten roles, nothing under 11px, no half-pixel steps.
- **Display** (650, clamp 28→44px, 1.15): the flashcard word only.
- **Title** (`--fs-title` 21px, `--fs-title-wide` 23px at ≥1080px, 650, −0.022em): the app title and the rail's big figure.
- **Lead** (`--fs-lead` 19px, 600–650): the app title on a phone, the flashcard meaning, the rail's next topic, a set's score.
- **Prompt** (`--fs-prompt` 18.5px, serif 400/1.6): drill sentences, with the blank in bold forest.
- **Reading** (`--fs-read` 17.5px, serif 400/1.8): Lugemine prose and the reader's title.
- **Input** (`--fs-input` 16px): text fields and selects, so iOS never zooms on focus.
- **Body** (`--fs-body` 15px/1.55): the default, section titles and filled buttons.
- **UI** (`--fs-ui` 14px): controls, tabs, verdicts, explanations under a verdict.
- **Note** (`--fs-note` 13px/1.6, max 62ch, Pencil): explanatory paragraphs, meanings in lists, the task line.
- **Meta** (`--fs-meta` 12px, Pencil): hints, counts, rail-card labels (600, +0.06em, UPPERCASE).
- **Gloss** (`--fs-gloss` 11px, Pencil): the Russian line under an Estonian label, tags, level and count badges.

### Named Rules
**The Serif-Is-Estonian Rule.** The serif is reserved for Estonian material the learner reads or completes. Interface text never uses it.

**The Steady Digits Rule.** Every number that changes in place (scores, counts, the ring, badges, rail figures) uses `tabular-nums`.

**The 16px Field Rule.** Text inputs and selects are 16px, so iOS never zooms on focus.

## Layout

The spacing scale is 4px-based (`--s1`…`--s6`). Gaps between stacked items in a panel come from a single flow rule: `--s4` between siblings, with no top margin on the first child.

- **Phone (<720px):** a single column with 20px gutters. Panels bleed edge to edge with no radius and no shadow. The three **modes** are a fixed, translucent thumb bar at the bottom, with 54px targets showing an icon and label. The **skills** are a horizontally scrolling chip row at the top, with a fade at the trailing edge. Sticky word cards sit above the thumb bar.
- **Tablet (720–1079px, height ≥560px; iPad mini portrait):** a 168px rail of skills with their Estonian labels beside the column. The modes become a segmented control in the header.
- **Phone in landscape (touch, height ≤500px; iPhone 17 at 874×402):** the phone's chip row with the glosses dropped, side gutters that clear the Dynamic Island (`env(safe-area-inset-*)`), and Rada's topic line and button on one line.
- **Drill sets, every device:** one unanswered item at a time, with its position; Enter moves to the next. The next set is offered in the end card, not above the set.
- **Desktop (≥1080px):** a 1320px grid with a 248px sticky skills column (Estonian label plus Russian gloss), the reading column, and a 300px sticky context rail of cards.
- **Filter rows:** labels sit above their controls. Below 560px each filter takes the full width.
- **Touch:** on `hover:none` devices, every control inside a panel is at least 44px tall.

## Elevation & Depth

Depth is low and responsive. At rest, a panel carries a soft two-part shadow and a 1px rule line. Everything inside it is flat Paper insets. Depth changes in response to the hand: cards lift, buttons press. The only gradients are a faint accent wash in a panel's corner, in the first rail card and the top light of a primary button.

### Shadow Vocabulary
- **Rest** (`--shadow`): panels and the selected segmented tab.
- **Lift** (`--lift`): card hover, together with a 1px rise and a forest border.
- **Floating card** (`0 4px 18px rgba(0,0,0,.13)`): sticky word cards only.

### Named Rules
**The Depth-Answers-Touch Rule.** A surface gains elevation only in response to hover or press. On touch devices the hover lift is disabled so it never latches.

**The Flat Rule.** No other gradients, washes or shadow levels. Where depth is needed, use a border or a Paper/Sheet step.

## Shapes

Softly rounded, and more rounded as a surface gets bigger, on one scale: panels 18px, cards 14px, controls 12px, tiles 10px, tags and level badges 5px. Pills (999px) are reserved for things you switch between: mode buttons, skill chips, icon buttons and count badges. Borders are always 1px Rule Line. The exceptions are the 3px Forest Deep bottom edge of primary buttons, the 3px left stripe on correction cards, and dashed borders on rows that leave the app.

## Components

### Buttons
Pressable, calm, clear.
- **Shape:** gently rounded (12px), at least 44px tall, Body size (15px) at 600.
- **Primary (`.go`, `.primary`):** filled forest with On-Forest text and a 3px Forest Deep bottom edge. On press it drops 2px into that edge without reflowing. Hover brightens it slightly.
- **Ghost:** transparent with a 1px rule line. Hover fills Forest Mist with a forest border and text.
- **Icon button:** a round button with a Pencil icon, 36px with a mouse and 44px on touch. Hover turns it forest.
- **Ratings:** the three review ratings sit in one row of equal thirds, at least 48px tall.

### Chips and tabs
- **Mode switch:** a segmented pill on desktop, where the selected tab is Sheet with a rest shadow. On a phone it is the bottom thumb bar, where the selected tab is Forest Mist with forest text.
- **Skill chips (phone):** 44px pills on Sheet with a 1px line. The selected chip is Forest Mist with forest text at 600. On desktop they become outlined tags, and at ≥1080px a sidebar list with the gloss.
- **Tag / level badge:** 5px radius, small uppercase or tabular text. B1 and higher are tinted forest.

### Cards and containers
- **Panel:** Sheet, 18px, 1px line, rest shadow, 22–24px padding.
- **Drill:** a Paper inset, 14px, 24/16px padding, holding its position ("3 / 10"), the serif prompt and the task line (word · FORM · gloss · level). A set shows one unanswered drill at a time; for a choice topic (object case) the form is not printed before the answer.
- **Choice:** a full-width Paper tile, 10px. Picked is a forest border on Forest Mist. Choices are stacked, never side by side.
- **Library row / word tile:** a Paper or Sheet tile, 10–12px radius: a title with one meta line under it. It lifts on hover. A dashed border means the row is external.
- **Rail card:** Sheet, 14px, with an uppercase Label heading. The first card is the next topic with a Harjuta link; a card that repeats the open panel is hidden there.
- **Next step:** a Forest Mist strip that leads a report screen with the one action to take next.

### Inputs / Fields
- **Style:** a Paper fill, 1px line, 12px radius, 44px tall, 16px text. Selects use a custom forest chevron.
- **Focus:** a 2px forest outline with a 2px offset, applied everywhere through `:focus-visible`.
- **Disabled:** 50% opacity.

### Feedback
- **Banner:** amber for a warning, Tint for info, Forest Mist for success. Each has a 12px radius and 13px/1.6 text.
- **Correction card:** a Paper card with a 3px forest left stripe (amber for `obj-case`). The wrong form is red and struck through, and the right form is forest and bold.
- **Verdict:** a forest or red line, 14px. A wrong answer shows the learner's attempt struck in red, then the right form in forest, then the rule in Russian.
- **Set end card:** Forest Mist, 14px: "Komplekt tehtud", the score in Lead type, the missed sentences with the right form, "Korda vigu" and "Uued laused".

### Progress ring (signature)
A 44px conic ring that fills in forest and brightens along the arc, with a tabular percentage inside. It animates over 700ms. It is the one decorative flourish allowed to represent accumulated work.

### Flashcard
One word gets the whole card: Display type, a speak button, and a meaning in slate that appears with a 180ms, 4px drop (removed under reduced motion).

## Do's and Don'ts

### Do:
- **Do** use tokens for every colour and spacing (`var(--…)`, `--s1`…`--s6`). Never write a hex value in a rule.
- **Do** give each information role its own treatment, and pair every state colour with an icon or shape.
- **Do** keep Estonian material in the serif and the interface in the system sans.
- **Do** put the Russian gloss under an Estonian label as small Pencil text (11px).
- **Do** keep at least 44px targets on touch, and 54px in the phone thumb bar.
- **Do** honour `prefers-reduced-motion`: lifts, presses, reveal and pulse all switch off.
- **Do** check every screen at 1440×900, on iPhone (402×874 and 874×402) and on iPad mini (744×1133), in both themes.

### Don't:
- **Don't** make it a noisy game: no streaks, XP, confetti, loud badges or celebratory animation.
- **Don't** make it a sterile exam booth either: keep the light progress cues (ring, counts, mastered marks).
- **Don't** add a second accent hue, or colour text by its language.
- **Don't** add new gradients, washes or shadow levels (Flat Rule).
- **Don't** load a webfont or any third-party asset.
- **Don't** collapse readiness into one overall percentage or number.
