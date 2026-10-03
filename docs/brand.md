# Grove identity

Grove is a familiar English word for a small wood. Its connection to Estonia is
quiet: forests and room to grow. The name stays the same across explanation
languages. **Eesti keel** identifies the subject; A2/B1 preparation is one learning goal.
The browser and installed full name are **Grove · Eesti keel**. The header pairs
a 40px leaf with the name in self-hosted Geologica.

## Artwork

`eesti/web/brand/mark.svg` is the original 64×64 vector master: a curved leaf
with a short stem. The header uses its navigation foreground. Platform tiles pair a white leaf
with spruce; social artwork has a mint ground and the learning loop in Geologica.
Practice rhythm replaces the boardwalk and readiness-flower presentation.

Run `.venv/bin/python deploy/build-brand.py` to rebuild all assets. Tooling
requires CairoSVG, Pillow, fontTools and Brotli; these are asset tools rather
than application dependencies. The generator uses the local Geologica font,
outlines social lettering, refreshes the inline header mark, and records
artwork provenance in PNG metadata. Third-party asset notices remain beside
their original files.

| Assets in `eesti/web/brand/` | Use |
|---|---|
| `tile.svg`, `favicon.svg`, `favicon-*.png`, `favicon.ico` | Browser identity, including 16/32/48px ICO |
| `icon-192.png`, `icon-512.png` | PWA icons |
| `icon-maskable.svg`, `icon-maskable.png` | Full-bleed tile with an inset leaf |
| `icon-mono.svg`, `icon-mono.png`, `safari-pinned-tab.svg` | Transparent monochrome silhouette |
| `apple-touch-icon.png` | 180px Apple icon |
| `wordmark.svg` | Outlined Grove lettering |
| `og-default.svg`, `og-default.png` | 1200×630 social artwork |
| `twitter-default.svg`, `twitter-default.png` | 1200×600 social artwork |

The generator also updates `eesti/web/icon.png`. `/brand/{name}`, `/icon.svg`,
`/icon.png`, `/favicon.ico` and `/apple-touch-icon.png` serve these assets.
Social URLs use the public front-door origin supplied by the trusted Worker.
The footer explains Grove in Russian, shows the current UTC copyright year,
and offers **Allikad** source credits. App metadata and the manifest use Grove.
The Worker service name and public URL remain stable to preserve stored state.

## Opening and theme

The app opens directly into the learner's current task. Saved light/dark
appearance is restored before paint. There is no branded cover or timed delay.
The lesson's labelled three-step strip changes through learn → practise → check;
reduced motion keeps the same usable, already-visible controls. Platform chrome
and the offline fallback share the mint working ground. APIs remain uncached.
