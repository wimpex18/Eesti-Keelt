# Klint identity

Klint is named after the Baltic Klint, the limestone escarpment along
Estonia's north coast: a step learners climb, from the beginning to B1. The
name is not an Estonian common word, reads the same in Russian, Ukrainian and
English, and stays the same in every explanation language. **Eesti keel**
identifies the subject; A2/B1 preparation is one learning goal. The browser and
installed full name are **Klint · Eesti keel**. The header pairs the mark with
the name in self-hosted Geologica, marked `lang="et"`.

## Artwork

`eesti/web/brand/mark.svg` is the 64×64 vector master: a K outlined from
Geologica at weight 650 in the sharp cut (`SHRP` 100), with the interlinear bar
under it — the same bar that marks a form in the app (`DESIGN.md`), and the
shore line under the cliff. The header draws it in the navigation ink. Platform
tiles put a birch (`#F1F4F1`) mark on a spruce (`#15201A`) tile; social artwork
has a birch ground with the mark, *Klint*, *Eesti keel*, *Algusest kuni B1-ni*
and the learning loop, all Estonian lettering in the sharp cut.

Run `deploy/build-brand.py` with Python to rebuild all assets. Tooling
requires CairoSVG, Pillow, fontTools and Brotli (and the Cairo library); these
are asset tools rather than application dependencies, so a throwaway virtual
environment is enough. The generator uses the local Geologica font, outlines
the lettering, refreshes the inline header mark, and records artwork
provenance in PNG metadata. Third-party asset notices remain beside their
original files.

| Assets in `eesti/web/brand/` | Use |
|---|---|
| `tile.svg`, `favicon.svg`, `favicon-*.png`, `favicon.ico` | Browser identity, including 16/32/48px ICO |
| `icon-192.png`, `icon-512.png` | PWA icons |
| `icon-maskable.svg`, `icon-maskable.png` | Full-bleed tile with an inset mark |
| `icon-mono.svg`, `icon-mono.png`, `safari-pinned-tab.svg` | Transparent monochrome silhouette |
| `apple-touch-icon.png` | 180px Apple icon |
| `wordmark.svg` | Outlined Klint lettering |
| `og-default.svg`, `og-default.png` | 1200×630 social artwork |
| `twitter-default.svg`, `twitter-default.png` | 1200×600 social artwork |

The generator also updates `eesti/web/icon.png`. `/brand/{name}`, `/icon.svg`,
`/icon.png`, `/favicon.ico` and `/apple-touch-icon.png` serve these assets.
Social URLs use the public front-door origin supplied by the trusted Worker.
The footer offers **Allikad** source credits. App metadata and the manifest use
Klint.

Identifiers that carry the earlier name Grove stay as they are, so stored state
and issued references keep working: the `grove-material` source id, the Worker
service name and its public URL.

## Opening and theme

The app opens directly into the learner's current task. Saved light/dark
appearance is restored before paint. There is no branded cover or timed delay.
The lesson's labelled three-step strip changes through learn → practise → check;
reduced motion keeps the same usable, already-visible controls. Until the
redesign's token step lands (`DESIGN.md`, Migration), platform chrome, the
manifest colours and the offline fallback keep the pale blue working ground and
navy dark theme of the shipped interface; the brand tiles already use spruce
and birch. The fallback uses system fonts without requesting assets and offers
an explicit retry when the shell is unavailable. APIs remain uncached.
