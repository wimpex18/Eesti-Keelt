# Grove identity

Grove is a familiar English word for a small wood. Its connection to Estonia is
quiet: forests and room to grow. The name stays the same across explanation
languages. **Eesti keel · A2/B1** identifies the subject in metadata and the
phone opening; the browser and installed full name are **Grove · Eesti keel**.
The header pairs a 48px leaf with the name in self-hosted Geologica.

## Artwork

`eesti/web/brand/mark.svg` is the original 64×64 vector master: a curved leaf
with a short stem. The app uses the current theme accent. Platform tiles pair
a white leaf with Estonian blue. The cornflower remains the separate exam-part
illustration, and the boardwalk remains the learning-path metaphor.

Run `.venv/bin/python deploy/build-brand.py` to rebuild all assets. Tooling
requires CairoSVG, Pillow, fontTools and Brotli; these are asset tools rather
than application dependencies. The generator uses the local Geologica font,
outlines social lettering, refreshes inline header/launch marks, and records
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

## Opening motion

A leaf unfolds from its stem for 560ms, starting at 40ms. The name rises 6px
and fades in over 360ms from 160ms. The cover fades at 720ms and is gone by
900ms; CSS and JavaScript dismiss it independently. The motion appears on a
fresh phone visit with a coarse pointer and no hover (≤719px, or ≤1023px with
height ≤559px). Desktop and tablet open directly.

Reduced motion, same-origin navigation, prerendering and history restoration
skip the cover. Tap or key dismisses it immediately. It is `aria-hidden`,
`inert`, pointer-transparent and never waits for network, modules or fonts.
Theme and saved transparency preferences are restored before paint. Offline
shells retain the cached brand; APIs remain uncached and require the server.
