---
name: Eesti keel
description: Laudtee — a boardwalk across the bog to the A2/B1 exam, one checked plank at a time.
colors:
  rukkilill: "#2b50c8"
  rukkilill-deep: "#1c3894"
  rukkilill-mist: "#e1e7fa"
  on-rukkilill: "#ffffff"
  must: "#15171b"
  must-soft: "#3d414a"
  pencil: "#5b606a"
  kask: "#f2f0ea"
  kask-deep: "#e8e5dc"
  leht: "#fbfaf6"
  valge: "#ffffff"
  rule-line: "#d8d4c9"
  rule-faint: "#e5e1d7"
  tint: "#ebe8df"
  sammal: "#2e7a4f"
  sammal-mist: "#e0efe5"
  johvikas: "#b3283c"
  johvikas-mist: "#f8e3e6"
  murakas: "#955400"
  murakas-mark: "#d98a1e"
  murakas-mist: "#f7ecd8"
  jarv: "#0f6873"
  oo: "#15171b"
  oo-accent: "#93a9ff"
typography:
  hero:
    fontFamily: "Literata, Iowan Old Style, Palatino, Georgia, serif"
    fontSize: "clamp(38px, 9vw, 64px)"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Onest, ui-sans-serif, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  prompt:
    fontFamily: "Literata, Iowan Old Style, Palatino, Georgia, serif"
    fontSize: "24px (28px from 720px)"
    fontWeight: 400
    lineHeight: 1.4
  reading:
    fontFamily: "Literata, Iowan Old Style, Palatino, Georgia, serif"
    fontSize: "19px"
    fontWeight: 400
    lineHeight: 1.8
  answer:
    fontFamily: "Literata, Iowan Old Style, Palatino, Georgia, serif"
    fontSize: "17px"
    fontWeight: 500
    lineHeight: 1.4
  lead:
    fontFamily: "Onest, ui-sans-serif, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 800
    lineHeight: 1.2
  body:
    fontFamily: "Onest, ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
  ui:
    fontFamily: "Onest, ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.25
  note:
    fontFamily: "Onest, ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
  meta:
    fontFamily: "Onest, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  gloss:
    fontFamily: "Onest, ui-sans-serif, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  xs: "6px"
  sm: "10px"
  control: "14px"
  stage: "20px"
  hero: "28px"
  switch: "999px"
spacing:
  s1: "4px"
  s2: "8px"
  s3: "12px"
  s4: "16px"
  s5: "24px"
  s6: "32px"
  s7: "48px"
components:
  button-primary:
    backgroundColor: "{colors.rukkilill}"
    textColor: "{colors.on-rukkilill}"
    rounded: "{rounded.control}"
    padding: "9px 20px"
    height: "46px"
  button-secondary:
    backgroundColor: "{colors.tint}"
    textColor: "{colors.must}"
    rounded: "{rounded.control}"
    padding: "9px 20px"
    height: "46px"
  button-check:
    backgroundColor: "{colors.must}"
    textColor: "{colors.kask}"
    rounded: "{rounded.control}"
    height: "54px"
  answer-field:
    backgroundColor: "{colors.valge}"
    textColor: "{colors.must}"
    rounded: "{rounded.control}"
    height: "54px"
  hero:
    backgroundColor: "{colors.oo}"
    textColor: "{colors.kask}"
    rounded: "{rounded.hero}"
    padding: "26px 22px 18px"
  stage:
    backgroundColor: "{colors.leht}"
    rounded: "{rounded.stage}"
    padding: "22px"
  switch:
    backgroundColor: "{colors.tint}"
    rounded: "{rounded.switch}"
    height: "38px"
  banner-caution:
    backgroundColor: "{colors.murakas-mist}"
    textColor: "{colors.murakas}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
---

# Design System: Eesti keel

## Overview

**Creative North Star: "Laudtee" — the boardwalk across the bog.**

Estonian bogs are crossed on boardwalks: plank after plank, each one laid
before the next can be walked on. The path to the A2/B1 exam is built the same
way. A topic is a plank, and it is laid only once code has checked the
learner's answers. That is the app's one metaphor. It draws the path, the
progress and the rewards, and it keeps the product honest, because a plank
is either laid or not.

The ground is **birch paper (kask) and black (must)** with **cornflower
(rukkilill)**, the national flower, as the single accent for action and
"now". Colour otherwise belongs to an information role, never to a language.
Surfaces are separated by **tone, not outline**. The page is the panel; sheets
(`leht`) sit on it for the things you work on; one dark surface (`öö`, night)
marks what to do now. There are no bordered cards everywhere, no pill clouds,
no gradients for their own sake.

The interface speaks **Onest**, a Cyrillic-native grotesk, so the Estonian
label and its Russian gloss are set in one family. The language itself is set
in **Literata**: every drill sentence, answer field, reading text, word and
topic name. Estonian material always looks like material, never like chrome.
Both faces are self-hosted (`eesti/web/fonts/`, SIL OFL 1.1) with system
fallbacks.

**Key characteristics**
- One dark hero per screen at most, answering "what do I do now?".
- Progress is drawn with three signature graphics: the **boardwalk** (Rada),
  the **cornflower** (exam readiness) and the **beads** (a set in progress).
- Rewards follow mastery, not attendance. There are no streaks that burn.
- Estonian label first, Russian gloss beside or beneath it, in the same face.
- Motion explains: a bead fills, a petal grows, a plank is laid. All motion
  collapses to instant under `prefers-reduced-motion`.

## Colors

Tokens live in `eesti/web/app.css` (`:root`) and are mirrored one-for-one for
dark (`@media (prefers-color-scheme: dark)` and `[data-theme="dark"]`).

| Role | Token | Light | Dark | Meaning |
|---|---|---|---|---|
| Rukkilill | `--accent` | #2b50c8 | #8ea6ff | Action, selection, focus, "now", readiness petals |
| Rukkilill deep | `--accent-deep` | #1c3894 | #6883e6 | The pressed edge of a primary button |
| Rukkilill mist | `--accent-soft` | #e1e7fa | #1f2745 | Selected fills, next-step strip, tutor offer |
| Sammal (moss) | `--good` | #2e7a4f | #6cc48e | Right answer, mastered plank, the filled blank |
| Jõhvikas (cranberry) | `--bad` | #b3283c | #ff8594 | The wrong form, a wrong bead. Kept rare. |
| Murakas (cloudberry) | `--warn` / `--warn-fill` | #955400 / #d98a1e | #f0ae4a | Caution, untouched exam part, the `obj-case` weakness |
| Järv (lake) | `--gloss` | #0f6873 | #5cc6cf | What a word means, and only that |
| Must (ink) | `--ink` | #15171b | #ececea | Text, the flower's heart, the check button |
| Kask (birch) | `--bg` | #f2f0ea | #101216 | The page |
| Leht (sheet) | `--panel` | #fbfaf6 | #181b21 | Stages, stat cards, word cards |
| Öö (night) | `--night` | #15171b | #1c2130 | The hero and the celebration, dark in both themes |

**The Colour-by-Role Rule.** Cornflower means "act / now", moss "right /
done", cranberry "wrong", cloudberry "caution", lake "meaning". Russian text is
never coloured for being Russian.

**The Never-Hue-Alone Rule.** Every coloured state also has a shape: topic
nodes carry icons (tick, clock, play, lock, book), petals are filled, empty or
hatched, plan blocks have their own glyph, and a wrong bead stays in the row.

## Typography

- **Hero** (Literata 500, clamp 38→64px): the current topic's name.
- **Title** (Onest 800, 30px): the page title, hidden on a phone where the
  tab row already names the place.
- **Prompt** (Literata 400, 24px, 28px from 720px): drill sentences. The blank
  is a cornflower rule that fills with the right form once graded.
- **Reading** (Literata, 19px/1.8, max 66ch): Lugemine prose; the reader's
  title is Literata 600 at up to 36px.
- **Answer** (Literata 500, 17px): the answer field. What the learner types is
  Estonian material.
- **Lead / body / ui / note / meta / gloss** (Onest 20 / 16 / 15 / 14 / 13 /
  12px). Nothing is smaller than 12px, except the band axis labels, which are
  also in the chart's accessible name.
- Every number that changes in place uses `tabular-nums`. Fields are at least
  16px so iOS never zooms on focus.

## Layout

Phone first, with three arrangements from one markup:

- **Phone (<720px, and any touch screen under 560px tall).** A top bar holds
  the mark, the name and two icon actions. The open mode's tabs sit in a row of
  words with a cornflower rule under the selected one; the row scrolls sideways
  with a fade. The three modes are a thumb dock at the bottom (56px targets;
  the open mode is inked black). The dock hides while typing. The gutter is
  16px plus safe areas.
- **Spine (≥720px and ≥560px tall; iPad mini portrait).** A full-height,
  sticky left spine (216px) on the recessed `kask-deep`. It holds the brand, the
  three modes stacked with their glosses, the open mode's tabs as a labelled
  column, and the actions at its foot.
- **Desk (≥1080px).** Spine 252px, a working column up to 880px, and a 320px
  context rail. The rail shows the cornflower, the next topic, the review queue
  and the milestone seals. A rail card is hidden while its own panel is open.
- **iPhone landscape (touch, ≤500px tall).** Chrome collapses to one line
  (mark, tabs, actions), the hero steps aside, and the dock shrinks to 44px.

## Signature components

### Hero (Praegu)
Night surface, 28px radius, drawn over contour lines of a bog map (a
repeating radial gradient, token-coloured and masked). It carries the resume
topic in the hero serif, its Russian name and level, the attempts so far, the
primary button while no set is on screen, and the boardwalk.

### Laudtee, the boardwalk
An SVG plank path through a window of the curriculum around the resume topic,
with as many nodes as the width holds (5–13). Mastered nodes are moss with a
tick; the resume node is cornflower with a slow halo; open nodes are outlined;
later nodes are grey; theory nodes are dashed. "Kogu rada" opens the full path:
one vertical boardwalk per level, each topic a node on a plank rail, with its
Russian name, prerequisites and accuracy, plus *harjuta* and *testi välja*
where available.

### Beads (Helmed)
One bead per item in the set: grey waiting, cornflower (pulsing) for the item
being answered, moss for right, cranberry for wrong. The end card repeats
them. A wrong bead is never hidden.

### The stage and the drill
A sheet (`leht`, 20px radius). Items are answered one at a time on every
device. The prompt is set in Literata; the blank is a cornflower rule. Once
graded, the blank fills with the right form (moss; with a cranberry rule when
the learner's answer was wrong), and the verdict shows the attempt struck
through, then the right form, then the rule in Russian. A recorded miss offers
*Selgita* (the model explains, labelled as such). On a phone, earlier answers
fold to their sentence and verdict. The check button is black (`must`), and
cornflower stays reserved for the next step.

### Set end
Score in 44px Onest 800, the beads again, the missed sentences with the right
form, *Korda vigu* and *Uued laused*. At 8/10 or better it takes the moss
wash.

### Rukkilill, the readiness flower
Four petals are the four exam parts, in the exam's order, so a flower missing
a petal is visibly incomplete, which is exactly the exam's own rule. Each petal
has three segments that light up one contact at a time toward
`contact_target` (`eesti/readiness.py`). This is contact, not competence, and
never a prediction. Rääkimine is hatched and dashed: "cannot tell" is not
"none". The flower appears on Ülevaade beside the verdict, and in the rail.

### Seals (Märgid)
The four level milestones (`eesti/milestones.py`) as circular seals, each
with its own glyph and a ring that fills with the count. They turn solid
cornflower when complete. They award nothing and only mark what happened.

### Plan strip (Täna)
The day as time: one segment per plan block, as wide as its minutes, coloured
and glyphed by kind (review, repair, refresh, skill, new, read). Up to three
blocks read left to right on a wide screen; more stack.

### Celebration
Mastery is the one ceremony. A cornflower blooms on a night card with the
topic's name. It is announced politely and leaves by itself after 3.6s; it is
instant under reduced motion.

### Supporting pieces
- **Buttons.** Primary is cornflower with a 3px pressed edge; secondary is a
  tinted surface without an outline. Both are 46px tall (54px for the drill's
  field and check).
- **Switch.** A segmented control on a tint, used for Minu rada / Vaba harjutus
  and A2 / B1. On a phone it spans the width with the gloss beneath.
- **Disclosures** (Plaan, Kogu rada, Offline, Proovieksam, Vestlus): a heading
  on a hairline with a chevron, not a box.
- **Library rows**: a Literata title and one meta line, divided by hairlines.
  A dashed divider means the row leaves the app.
- **Stat cards** (Edenemine): a big tabular number, a meter, and for
  vocabulary a frequency-band column chart.
- **Correction card**: a sheet with a 3px inset stripe, cornflower, or
  cloudberry for `obj-case`.
- **Empty states**: a tinted mark, a Russian sentence and one next step.

## Motion

Durations are 140ms (response), 240ms (state change) and 420ms (arrival),
with the ease `cubic-bezier(.22,1,.36,1)`, which has no overshoot. Beads pop
when graded, petals grow in sequence, the plan strip draws from the left, band
columns rise, the verdict drops 3px into place, and the resume node's halo
breathes. Under `prefers-reduced-motion` every animation and transition
collapses to 1ms and the halo is removed.

## Do's and Don'ts

**Do**
- Use tokens for every colour and the `--s1`…`--s7` scale for spacing.
- Keep Estonian material in Literata and the interface in Onest.
- Draw progress with the three signature graphics before adding any new chart.
- Keep 44px targets on touch (46px tabs, 56px dock).
- Check every screen at 1440×900, iPhone 17 (402×874 and 874×402), iPad
  mini 6 (744×1133), in both themes.

**Don't**
- Don't add a streak, an XP total or a single overall readiness percentage:
  the exam fails a zero in any part, and the flower says so.
- Don't outline a surface to separate it; use tone.
- Don't use cornflower for anything but action, "now" and readiness.
- Don't colour text by its language.
- Don't let a celebration follow anything except code-decided mastery.
