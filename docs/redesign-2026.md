# The 2026 redesign

What changed on the page, and why. The design was drawn first as artboards on
a canvas (<https://claude.ai/code/artifact/e795c3d8-51d5-4f3a-bc2f-c85571f308d5>);
those files are not in the repository, because the implementation is, and two
descriptions of one design drift apart the moment either is edited.

## What was kept

**The palette, unchanged.** Same `#faf9f6` paper, same `#1c6b52`, same
`--gloss` slate for what a word means. A redesign that also changes every
colour cannot tell you which of the two made the difference.

**The DOM the app is built on.** `router.js` binds `nav[data-mode-nav]
button[data-tab]`, `chrome.js` fills `.modes button[data-mode]`, and eleven
`section.panel[id^=tab-]` are the panels. None of that moved: the redesign is
CSS plus two behaviour fixes, so no journey had to be re-verified against a
new contract.

## What changed

### The skills became a column, not a row

Seven bilingual tabs never fitted a row. On a phone the gloss had to be
dropped from six of them, every label was 10.5px, and the last tab still
clipped off the right edge — invisible to a page-level overflow check, because
the bar itself is the thing being cut. On a desktop the same row left four
fifths of the width empty.

At ≥1080px the skills are a sticky column: three grid columns per entry —
mark, text, count — so the Estonian name and its Russian gloss stack instead of
competing, on **every** entry rather than only the open one.

### The phone's thumb bar carries the modes

The two rows swapped jobs. The fixed bar at the bottom now holds the three
**modes**, which is the question the learner answers first and which fits three
54px targets across a phone. The skills moved to a scrolling row of chips at
the top, where a horizontal overflow is a gesture rather than a clipped
destination. Nothing moved in the markup — both rows already existed.

### Everything else

Reading prose and drill prompts take a serif (system faces only: a webfont
host is a third-party request the learner never asked for). Controls share a
44px floor. `.row > label` puts the label above its control, so fields line up
on one left edge at every width. The path list is a four-column grid, because
the Russian state words run to `ОТКРОЕТСЯ ПОЗЖЕ` and a `min-width:74px` sized
for English left every row starting its name at a different x.

## The middle width

720-1079px was the last range still answering with the phone's layout: a row
of seven bilingual tabs that has to scroll, on a screen with 300px of empty
margin either side. It gets a rail of marks instead -- room for a 68px column
and the reading measure at once, which a row cannot do because a row spends
its width on labels and then runs out.

Two things guard it, and both were found by measuring rather than by reading:

- `min-height:560px` on the branch. A phone in landscape is 844x390 -- wide
  enough for a rail and 390px tall, where a seven-item column is 352px and a
  sticky element taller than the window can never show its bottom. Rääkimine
  and Kirjutamine would have been unreachable. A short viewport keeps the row.
- The label is `display:none` in the rail, which takes the text out of the
  accessibility tree with it. `chrome.js` now sets `title` and `aria-label`
  from the label and its gloss, at every width.

## Where the learner is, in a row that scrolls

The old bottom bar could not lose the selected tab: all seven were on screen
at once, squeezed to 10.5px. A scrolling row can, and did -- opening `#write`
from a link or a reload put Kirjutamine 512px right of the viewport with the
row at `scrollLeft` 0, so the panel was Kirjutamine and the navigation said
Rada. `selectTab` scrolls the row (never the page) to bring it back.

## Marks, and one hue with depth

The navigation had drawn icons from the start; everything else used a text
character where it wanted a mark — `✓ Tean seda sõna`, `⊘ Pole vaja`,
`▶ Kuula`, `● Salvesta vastus`, `← Nimekirja`, `· ♪`. A character is not an
icon: it is drawn by whichever font the platform picks, so it changes size,
weight and baseline between Android, iOS and a desktop browser; `⊘` and `♪`
are not in every system face and fall back to another one mid-sentence; and
it cannot take the stroke weight of the icons beside it.

`UI_ICON` in `chrome.js` draws the rest, in the same grammar as `NAV_ICON` —
a 24-unit box, one stroke weight, round caps and joins, which is also the
grammar every mainstream icon set (Lucide, Phosphor, Heroicons) converged on.
Drawn rather than installed: this app ships no third-party requests and caches
its own shell, so an icon font or a CDN sprite would be both.

Two maps, so two ways to drift, and `test_navigation_icons.py` checks both
directions: a `BUTTON_ICON` id the page no longer has paints nothing, and
`uiIcon("typo")` returns an empty string. Neither would raise anything.

**The marks go in the flow, never by making the button a flex container.**
`button.go` deliberately is not flex: making it one blockifies every inline
child and the Russian gloss stops sitting inside the label. The mode buttons
solved that years ago with an inline-block mark and a vertical nudge; every
other button now uses the same solution.

### Depth, without a second colour

Colour in this app carries meaning — accent is *action* and *correct*, warn is
*attention*, bad is *error*, gloss is *what a word means*. So the 2026 house
style for surfaces (a gradient you cannot quite see: analogous, a few points
of lightness) is applied strictly inside the accent, and nowhere that a
learner reads a verdict:

- the primary button lightens 12 % toward white at its top edge;
- the progress ring sweeps from a lighter accent to the accent as it fills —
  it is the one number that represents accumulated work;
- every panel and the first rail card carry a 6–7 % accent wash at one corner.

Measured, not eyeballed: the lightest painted pixel of the button gradient
gives 5.03:1 against its white label in the light theme and 8.79:1 in the
dark one.

## The trap this file exists to warn about

**A media query does not raise specificity.** Three of the defects found while
building this were the same bug: a rule written inside `@media` lost to a rule
written later in the file at the same depth.

- `nav[data-mode-nav] button:not([aria-selected])` gets an outline at ≥720px,
  which made the new column read as seven stacked boxes.
- `.modes button{min-height:34px}` is declared for the desktop segmented
  control *after* the phone block, so the thumb targets came out 46px instead
  of 54.
- `.row > label` in the ≤560px block re-centred the column layout, so a select
  shrank to its content and sat centred under a left-aligned label.

All three were found by measuring in a browser and none by reading the file.
The overrides that fix them sit at the end of the stylesheet on purpose.
