---
name: Eesti keel
description: Laudtee — a boardwalk across the bog to the A2/B1 exam, in Estonian blue, black and white.
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
  title: "30px / 800"
  prompt: "24px, 28px from 720px"
  reading: "19px / 1.8"
  answer: "18px / 500"
  body: "16px"
  ui: "15px"
  note: "14px"
  meta: "13px"
  gloss: "12px"
rounded:
  control: "999px (buttons, switches, tabs)"
  field: "16px"
  sheet: "24px"
  hero: "32px"
  glass-dock: "30px"
spacing: "4px scale: --s1 4 · --s2 8 · --s3 12 · --s4 16 · --s5 24 · --s6 32 · --s7 48"
---

# Design System: Eesti keel

## Overview

**North star: "Laudtee" — the boardwalk across the bog.** Estonian bogs are
crossed on boardwalks, plank after plank, each laid before the next can be
walked. The path to the exam is built the same way: a topic is a plank, laid
only when code has checked the learner's answers. The metaphor draws the path,
the progress and the rewards, and keeps the product honest.

The ground is **near-white, cool and quiet** (`#f8fafc` page, white sheets),
never cream. The colour is **Estonian blue** from Brand Estonia (`#0030DE`),
with its partners Paldski, Liivi, Narva and Pärnu, black text (Mustkivi) and
white. One warm note, Haapsalu sand, is reserved for rest and reward. Colour
otherwise belongs to an information role, never to a language.

The interface follows **Apple's Liquid Glass rule of two layers**: navigation
and controls float on glass (the spine, the phone dock, switches, the word
card, the celebration); content sits on solid white sheets. Behind everything
is a faint sky of blue glows, so the glass has light to bend. Glass turns solid
with `prefers-reduced-transparency`, `prefers-contrast: more`, or the app's own
**Vähem läbipaistvust** switch (Safari does not report the system setting).

One typeface, **Geologica** (Monokrom, OFL), self-hosted under
`eesti/web/fonts/`. The interface is set soft; Estonian material is set in the
same face at a sharper cut (`--cut`, SHRP 55), so it reads as material without a
second family. Icons are **Phosphor** (MIT), inlined in `eesti/web/js/icons.js`:
duotone for navigation and marks, bold for the glyphs inside buttons.

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
| Evening | `--night-a/b/c` | #000a3d → #000087 → #0030de | darker | The hero: a Baltic evening gradient with Narva light |
| Glass | `--glass` + rim/edge/shadow | white 64% | slate 62% | The navigation layer |

**Colour by role.** Blue acts, moss is right, cranberry is wrong, cloudberry
cautions, lake means. Russian text is never coloured for being Russian.
**Never hue alone.** Every coloured state also has a shape: node icons,
filled, empty or hatched petals, a glyph per plan block, beads that stay.

## Typography

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
  mode is tinted blue). The dock hides while typing. Gutter 16px plus safe areas.
- **Spine (≥720px and ≥560px tall; iPad mini).** A **floating glass sidebar**
  inset 12px from the window, 32px radius: brand, the three modes with glosses,
  the open mode's tabs, and the two actions at its foot.
- **Desk (≥1080px).** Spine 264px, a working column up to 880px, and a 320px
  context rail: the readiness flower, the next topic, the review forecast and
  the milestone seals. A rail card hides while its own panel is open.
- **iPhone landscape (touch, ≤500px tall).** One line of chrome; the hero steps
  aside; a 44px dock.

## Controls

- **Buttons are capsules.** *Prominent* (`.go`, `.primary`): the blue fill with
  light running over it (a white top gradient and rim), never a flat block; it
  brightens under the pointer and settles to 97% when pressed. One per view.
  *Tinted* (`.ghost`): blue at 10%, deep-blue text, 17% on hover. *Plain*
  (`.linky`): an underlined link. Small (`.logbtn`, tutor offer, topic actions):
  tinted, 34–40px. Icon buttons: 42px circles (44px on touch), tinted on hover.
  Disabled: 45% opacity.
- **Fields are filled.** A soft Pahkla well, no border at rest; on focus it turns
  white with a blue edge and a 4px blue halo. Labels sit above with the Russian
  gloss on the same line. The drill's answer field is 56px, in the cut.
- **Switches** (`.levels`): a glass track, the chosen state a white capsule.
- **Tab lists** — modes, tabs, Minu rada / Vaba harjutus, A2 / B1 — take arrows,
  Home and End, with only the selected tab in the Tab order.

## Signature components

- **Hero (Praegu).** The evening gradient with Narva light, bog-map contour
  lines and a barn swallow (suitsupääsuke) gliding in the corner. It holds the
  resume topic, its Russian name and level, the **gate** (ten slots for the
  topic's last answers against 8 of 10), and the **boardwalk**.
- **Laudtee.** An SVG plank path through a window of the curriculum around the
  resume topic (5–13 nodes by width). Mastered nodes are moss with a tick; the
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
- **Plan strip.** The day as time, a segment per block as long as its minutes,
  coloured and glyphed by kind.
- **Celebration.** Mastery only: a flower blooms on an evening card, announced
  through the page's polite live region. Any key or tap dismisses it; under
  reduced motion only the announcement remains.

## Motion

140ms response, 240ms state change, 420ms arrival, `cubic-bezier(.22,1,.36,1)`.
Beads pop, petals grow in turn, the plan strip and the forecast rise, verdicts
drop into place, the resume node breathes, the swallow glides. Under
`prefers-reduced-motion` every animation, delay and transition collapses and
script scrolling stops being smooth.

## Do's and Don'ts

**Do:** use tokens for every colour and the `--s1`…`--s7` scale; keep glass on
the navigation layer and content on solid sheets; keep Estonian material in the
cut; keep 44px touch targets; check 1440×900, 402×874, 874×402 and 744×1133 in
both themes.

**Don't:** use cream or grey-beige grounds; put paragraph text or drill inputs on
glass; fill more than one or two buttons per view; add streaks, points or a single
readiness percentage; celebrate anything but code-decided mastery; colour text by
its language.
