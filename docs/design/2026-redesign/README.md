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
| `canvas.json` | where each artboard sits, on three pages |
| `gen_*.py` | the generator — **edit these, not the `.dc.html` files** |

The `.dc.html` files are generated. Change `gen_a.py` (tokens, shell, icons),
`gen_b.py` / `gen_c.py` (desktop screens), `gen_d.py` (mobile), then:

```bash
python3 gen_e.py     # rewrites every .dc.html and canvas.json
```

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
