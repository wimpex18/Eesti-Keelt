# 2026 redesign — the artboards

A visual redesign of every screen, drawn as static mock-ups. **Nothing here is
wired into `eesti/web/`**; it is a proposal to implement against, not code.

Published canvas: <https://claude.ai/code/artifact/e795c3d8-51d5-4f3a-bc2f-c85571f308d5>

## What is in here

| File | What it is |
|---|---|
| `Main.dc.html` … `Edenemine.dc.html` | the eleven screens at 1440 px |
| `Mobiil*.dc.html` | the same eleven at 390 × 844 |
| `Alused.dc.html` | palette, type scale, control sizes, the language rule |
| `Tume.dc.html`, `MobiilTume.dc.html` | the dark theme, desktop and mobile |
| `Tahvel.dc.html` | the middle width, 834 px |
| `Seisundid.dc.html` | press, focus, empty, loading, failure |
| `Komponendid.dc.html` | the parts the screens show in only one state |
| `canvas.json` | where each artboard sits, on five pages |
| `gen_*.py` | the generator — **edit these, not the `.dc.html` files** |

Twenty-eight artboards on five pages: Desktop, Mobiil, Alused, Tume ja tahvel,
Seisundid.

The `.dc.html` files are generated. Change `gen_a.py` (tokens, shell, icons),
`gen_b.py` / `gen_c.py` (desktop screens), `gen_d.py` (mobile), `gen_f.py`
(dark, tablet, states, components), then:

```bash
python3 gen_e.py     # rewrites every .dc.html and canvas.json
```

## The second pass

The first pass drew the eleven screens in their working state and nothing else.
Four things were missing, and all four are in the app today:

- **the dark theme** — `app.css` carries a full dark palette and a three-state
  toggle, and none of it had been drawn;
- **failure, empty and loading** — 11 `.banner` sites and 6 `.empty` sites in
  the JS, none of them drawn; the copy on `Seisundid.dc.html` is taken from the
  code, not invented;
- **the middle width** — `app.css` breaks at 720 px and again at 1080 px, so
  834 px is its own layout, not a wide phone;
- **components shown in one state only** — `.choices`, the flashcard's question
  side, a running checkpoint, the player's three states.

Rendering the dark board caught a real bug in this design system: elements that
set no colour of their own inherit `body`'s *computed* colour, which resolves
against the light tokens before `.dark` redefines them one level down — so every
heading and number came out dark-on-dark. The shells now re-resolve
`color: var(--ink)` at their root.

## What the redesign actually changes

The palette is **lifted unchanged** from `eesti/web/app.css` — same paper, same
`#1c6b52`, same `--gloss` slate for meanings. Three things are new:

- **Desktop navigation is a 248 px sidebar.** Mode is a group heading, section a
  row beneath it. Seven tabs no longer compete for one line, and the right rail
  keeps what used to sit behind a click.
- **Mobile carries the three modes in the bottom bar** (54 px targets) and the
  sections as a scrollable chip row. This is the fix for seven bilingual tabs at
  390 px, which `app.css` currently survives by hiding the Russian gloss.
- **Two type faces**: Manrope for the interface, Literata for reading passages
  and large numbers. Both cover Cyrillic and `õ ä ö ü`.

The language rule in `CLAUDE.md` is followed throughout, and `Alused.dc.html`
states it: Estonian for the interface and grammar terms, Russian for anything
that explains or warns — including the two caveats that exist to stop a wrong
conclusion being drawn.

## Verifying a change

Every artboard was rendered in Chromium and measured before publishing; that is
what caught bare inline SVGs defaulting to 300 × 150, and frame heights that
clipped their content. To repeat it after an edit:

```bash
python3 gen_e.py
/opt/pw-browsers/chromium-1194/chrome-linux/chrome --headless --disable-gpu \
  --no-sandbox --hide-scrollbars --window-size=1440,1290 \
  --screenshot=/tmp/shot.png file://$PWD/Main.dc.html
```

Note that a headless capture at *exactly* the viewport height drops the last
band — give the window ~200 px of slack when checking a mobile artboard's
bottom bar.
