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
