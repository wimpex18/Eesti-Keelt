"""The page and the static files around it.

Served from here rather than a CDN: the rest of this app refuses to depend on
someone else's uptime for a lesson, and a CDN is that dependency in a smaller
package. Every path is resolved and checked against its own directory, because
the name comes from the URL.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response

from .deps import WEB

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def index() -> str:
    return (WEB / "index.html").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Installable on a phone: manifest and icons
# --------------------------------------------------------------------------

ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#1c6b52"/>'
    '<text x="32" y="44" font-family="ui-sans-serif,system-ui,sans-serif" '
    'font-size="34" font-weight="700" fill="#fff" text-anchor="middle">ä</text>'
    "</svg>"
)


#: What the page loads besides itself, by extension. Anything not here is not
#: served, so a stray file in `eesti/web/` cannot be fetched by guessing.
STATIC_TYPES = {".css": "text/css", ".js": "text/javascript"}


@router.get("/app.css")
def stylesheet() -> FileResponse:
    """The stylesheet, which used to be 703 lines inside the page."""
    return FileResponse(WEB / "app.css", media_type="text/css")


@router.get("/js/{name}")
def script(name: str) -> FileResponse:
    """One ES module of the app.

    Same guard as `/vendor/{name}` and for the same reason: the name comes from
    the URL, so the resolved path is checked against the directory it must be
    in rather than trusted to stay inside it.
    """
    path = (WEB / "js" / name).resolve()
    if (path.parent != (WEB / "js").resolve() or not path.is_file()
            or path.suffix not in STATIC_TYPES):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, media_type=STATIC_TYPES[path.suffix])


@router.get("/vendor/{name}")
def vendor(name: str) -> FileResponse:
    """Third-party browser libraries, served from here rather than a CDN.

    One of them is load-bearing: 44 of the 91 audio items are HLS streams,
    which Safari plays natively and Chrome and Firefox do not. Without hls.js
    half the listening library is silently silent on a laptop.

    Served locally because the rest of this app already refuses to depend on
    someone else's uptime for a lesson, and a CDN is exactly that dependency in
    a smaller package.
    """
    path = (WEB / "vendor" / name).resolve()
    # Path traversal: `name` comes from the URL.
    if path.parent != (WEB / "vendor").resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, media_type="application/javascript")


@router.get("/icon.svg")
def icon_svg() -> Response:
    return Response(ICON_SVG, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/icon.png")
def icon_png() -> Response:
    """iOS ignores SVG for the home-screen icon, so serve the SVG's bytes under
    a .png name only if a real PNG exists; otherwise fall back to the SVG.

    Kept deliberately simple: adding a raster toolchain to draw one letter would
    be a dependency for a favicon.
    """
    png = WEB / "icon.png"
    if png.exists():
        return FileResponse(png, media_type="image/png")
    return Response(ICON_SVG, media_type="image/svg+xml")


#: The line `sw.js` declares its cache version on. Replaced when the worker is
#: served; asserted rather than assumed, because a silent no-op here brings
#: back the stale-shell bug it exists to prevent.
_VERSION_LINE = 'const VERSION = "dev";'


def build_version() -> str:
    """What to name this build's cache.

    The commit if the image build wrote one, else the build timestamp, else
    `dev` -- which is the honest answer from a source checkout, where the file
    on disk is the file being served and nothing needs retiring.
    """
    from .deps import BUILD

    revision = (BUILD.get("revision") or "").strip()
    built = (BUILD.get("built") or "").strip()
    return (revision or built or "dev")[:40]


def worker_source() -> str:
    """`sw.js` with the running build stamped into its cache name."""
    source = (WEB / "sw.js").read_text(encoding="utf-8")
    if _VERSION_LINE not in source:
        raise RuntimeError(
            f"sw.js no longer declares {_VERSION_LINE!r}; the cache version "
            f"would silently stop being stamped and old shells would never "
            f"be retired")
    version = build_version()
    return source.replace(_VERSION_LINE, f'const VERSION = "{version}";', 1)


@router.get("/sw.js")
def service_worker() -> Response:
    """Served from the root so its scope covers the whole app.

    A worker served from a subdirectory can only control that subdirectory,
    which for a single-page app means it controls nothing.

    `no-cache` on the worker itself: browsers re-check it on navigation, and a
    worker pinned by HTTP caching is one that cannot be replaced -- the failure
    mode where a bad worker outlives the deploy that fixed it.

    The cache name is stamped here rather than typed into the file. `activate`
    deletes every cache that is not the current one, so the version string is
    the only thing that retires a shell: left at a hand-edited literal, a
    redeploy that forgot to bump it kept serving the previous `index.html` from
    disk -- and that page names the modules it loads. Deriving it from the build
    means a new image is a new cache, always, with nothing to remember.
    """
    return Response(
        worker_source(), media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/manifest.webmanifest")
def manifest() -> Response:
    """Enough for "Add to Home Screen" to produce an app-like window."""
    return Response(
        json.dumps({
            "name": "Eesti keel",
            "short_name": "Eesti keel",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f7f7f5",
            "theme_color": "#1c6b52",
            # Russian: the install prompt and the page it opens are written
            # in the language the learner reads, not the one being learned.
            "lang": "ru",
            "icons": [
                {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml",
                 "purpose": "any"},
            ],
        }),
        media_type="application/manifest+json",
    )
