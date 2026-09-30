# Estep identity

Estep is the app's name, formed from **Estonian + step**.
**Eesti keel · A2/B1** is its subject descriptor in metadata and the phone launch
passage; the document title and installed full name are **Estep · Eesti keel**.
The header shows only Estep, alongside a 48px mark and a 28px name (26px in the
spine). The existing boardwalk learning-path metaphor remains separate from the
name, across the current Russian and planned English and Ukrainian explanation
languages.
It makes no exam outcome, CEFR assessment or mastery claim.

The mark is one stepped E with three chamfered treads and a longer foot. Its
canonical artwork is `eesti/web/brand/mark.svg`, an original project vector on
a 64×64 viewBox. The in-app mark uses the current theme's accent; platform
tiles use a white E on Estonian blue (`#0030de`). The existing cornflower
continues to illustrate contact with the four exam parts, separately from the
app identity. Learning evidence and source boundaries remain in
`ai-boundaries.md`, `sources.md` and `../DESIGN.md`.

## Artwork and type provenance

The geometric mark is original artwork made for this project. Its derived
rasters are generated from the vector, and PNG `Source` and
`impeccable:prompt` metadata record their origin and generator. The ICO is
assembled from those rendered sizes. The mark adds no third-party illustration
asset or font-service request.

The wordmark uses the app's self-hosted **Geologica**, soft `SHRP` 0 at weight
650. Geologica's SIL Open Font License 1.1 is retained at
`eesti/web/fonts/OFL-Geologica.txt`. The generator uses the local Latin WOFF2
to outline the SVG wordmark and social-card lettering. The UI retains real text,
the existing Latin, Latin Extended and Cyrillic subsets, and system fallbacks.
Phosphor icons and learning-material attribution are unchanged.

## Rebuilding

From the repository root, use the project virtual environment:

```bash
.venv/bin/python deploy/build-brand.py
```

Asset tooling requires **Pillow, fontTools and Brotli** in that environment.
These are generator tools, not added application runtime dependencies. Inputs
are `eesti/web/brand/mark.svg` and `eesti/web/fonts/geologica-latin.woff2`;
the generator also refreshes the inline header and launch copies between the
`brand:header` and `brand:splash` markers in `eesti/web/index.html`, including
the launch passage's point. The master silhouette is shared; only the launch
copy adds the animated circle.

| Output | Use |
|---|---|
| `tile.svg`, `favicon.svg` | Blue rounded tile, white mark |
| `favicon-16.png`, `favicon-32.png`, `favicon-48.png`, `favicon.ico` | Browser icons; ICO contains 16/32/48px |
| `icon-192.png`, `icon-512.png` | Regular PWA artwork |
| `icon-maskable.svg`, `icon-maskable.png` | Full-bleed blue, mark inset to 88%; 512px raster for platform masks |
| `icon-mono.svg`, `icon-mono.png` | Single-colour transparent silhouette; 512px raster |
| `safari-pinned-tab.svg` | Black silhouette, tinted by Safari's mask-icon colour |
| `apple-touch-icon.png` | Full-bleed blue Apple artwork, 180px |
| `wordmark.svg` | Outlined Estep lettering |
| `og-default.svg`, `og-default.png` | 1200×630 social card |
| `twitter-default.svg`, `twitter-default.png` | 1200×600 social card |

All outputs above live under `eesti/web/brand/`. The generator also refreshes
the legacy `eesti/web/icon.png` as a 512px full-bleed icon. Social cards say
**Estep**, **Eesti keel**, **A2 / B1** and **Õpi. Harjuta. Kontrolli.**

## Serving and metadata

`eesti/api/assets.py` serves existing SVG, PNG and ICO files at `/brand/{name}`
with `Cache-Control: no-cache` and directory traversal protection. Root
`/favicon.ico` and `/apple-touch-icon.png` use their brand counterparts.
Compatibility routes `/icon.svg` and `/icon.png` remain available.
`/manifest.webmanifest` names Estep, starts at `/`, and declares distinct
regular, maskable and monochrome icons. The page declares ICO, PNG and SVG
favicons, Apple artwork, Safari pinning, and Open Graph/Twitter metadata.

The origin replaces `__BRAND_ORIGIN__` in the social image URLs with the
request origin. In the guarded deployment, the Worker overwrites
`x-brand-origin` with the public front-door origin and supplies `PROXY_TOKEN`;
the origin accepts that header only when its proxy protection is configured
and the value is a valid HTTPS origin. Local development uses the request's
own origin. This keeps social artwork URLs on the public front door instead
of the private Cloud Run hostname. The Worker and origin changes must both
be deployed for that propagation to be active.

The root HTML also replaces `__BRAND_REVEAL__` with the canonical contents of
`eesti/web/brand-reveal.js` inside the head script. There is no separately
fetched reveal script or standalone reveal route. The server also replaces
`__BRAND_YEAR__` with the current UTC year in **© [year] Estep**. The footer
explains the name in Russian (**Estonian + step: эстонский шаг за шагом.**) and
keeps **Allikad ja litsentsid** with the existing source/licence disclosure.
The copyright line names the app, with no person or company claim.

## Header and phone navigation

The home link opens Rada. Profile/login replaces the header transparency
control; `eesti/web/js/profile.js` paints **Logi sisse** with a sign-in icon for
signed-out use and **Profiil** with a user-circle otherwise. Both open the
existing profile screen, where the established account flow runs. Theme cycling
remains beside it. Reduced transparency and higher contrast use the automatic
solid fallback; previously saved `glass=off` still works.

On coarse-pointer, non-hover phones, both the skill row and bottom mode dock
use a press/slide/release magnifying lens adapted from WanderAlt. A hold or
horizontal drag lifts an inert copy of the labels. Preview changes neither
panel nor history; release commits through the existing router. The row scrolls
at its edges to expose hidden skills. Cancellation restores the selected tab;
quick taps and keyboard navigation remain ordinary navigation. Desktop, tablet
and other segmented controls retain the quiet selection glide. The lens is
eligible at width ≤719px, or width ≤1079px with height ≤559px; reduced motion
removes its magnification. The detailed behavior is in `DESIGN.md` and
`eesti/web/js/glide.js`.

## Launch, accessibility and offline

The saved theme and any existing `glass=off` preference are restored in the head
before body paint, independently of launch eligibility. The optional cover uses the
current page surface and appears only for `pointer: coarse` and `hover: none`
at width ≤719px, or width ≤1023px and height ≤559px. Desktop and tablet open
directly; reduced motion, prerendering, back/forward restoration and
same-origin navigation skip the cover. An explicit reload may show it.

The stepped E exists in the first frame. A small point moves along its foot
and climbs one level inside the mark for 600ms after an 80ms delay; the cover
starts a 180ms fade at 720ms and finishes at 900ms. JavaScript removes it at that
deadline and CSS hides it independently.
It does not wait for fonts, modules, data or a network response. A tap or key
dismisses it immediately; page hiding and restored-page events clear it.
The cover is `aria-hidden`, `inert` and pointer-transparent. It traps no focus.
With JavaScript unavailable or eligibility failing, it stays hidden. Reduced
motion also hides it in CSS, including when the preference changes at runtime.

The service worker precaches the root HTML, platform icons, manifest, local
fonts, stylesheet and application modules. The reveal is already in that
cached root HTML. Root navigation and code are network-first with a cached
fallback; static artwork and the manifest are cache-first. The server stamps
the shell cache with the build version and activation retires older shells.
An offline launch can retain the identity and appearance from the cached
shell; drills still require the server and the API is never cached. Social
cards are not required for the offline shell.
