"""The page and the static files around it.

Served locally, not from a CDN, so a lesson never depends on someone else's
uptime. File names come from the URL, so every resolved path is checked against
its directory.
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

#: The app mark as SVG strokes (no font dependency), with a two-step accent
#: gradient.
ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#2a8064"/>'
    '<stop offset="1" stop-color="#155440"/></linearGradient></defs>'
    '<rect width="64" height="64" rx="15" fill="url(#g)"/>'
    '<g fill="none" stroke="#ffffff" stroke-width="5.4" stroke-linecap="round">'
    '<circle cx="28" cy="40.5" r="9.6"/>'
    '<path d="M39.5 30.5v20.4"/>'
    '<path d="M23.4 20.6h.01"/><path d="M34.2 20.6h.01"/>'
    "</g></svg>"
)


#: What the page loads besides itself, by extension. Anything not here is not
#: served, so a stray file in `eesti/web/` cannot be fetched by guessing.
STATIC_TYPES = {".css": "text/css", ".js": "text/javascript"}


def _asset_headers() -> dict:
    """Under `cli serve` the files on disk are the source being edited, and the
    service worker's cache name is the literal `dev`, so nothing retires a stale
    module: the page keeps running the version from an hour ago. A build stamps
    a real version and its own cache, so there this stays out of the way.
    """
    return {"Cache-Control": "no-cache"} if build_version() == "dev" else {}


@router.get("/app.css")
def stylesheet() -> FileResponse:
    """The stylesheet."""
    return FileResponse(WEB / "app.css", media_type="text/css",
                        headers=_asset_headers())


@router.get("/js/{name}")
def script(name: str) -> FileResponse:
    """One ES module of the app; the resolved path is checked against its directory."""
    path = (WEB / "js" / name).resolve()
    if (path.parent != (WEB / "js").resolve() or not path.is_file()
            or path.suffix not in STATIC_TYPES):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, media_type=STATIC_TYPES[path.suffix],
                        headers=_asset_headers())


@router.get("/vendor/{name}")
def vendor(name: str) -> FileResponse:
    """Third-party browser libraries (hls.js: Chrome and Firefox cannot play the HLS
    audio streams natively), served locally.
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
def icon_png() -> FileResponse:
    """The home-screen icon as a committed 512×512 raster: iOS ignores SVG for
    `apple-touch-icon`. Full bleed with the glyph at 74 % so a maskable crop keeps
    the dots.
    """
    return FileResponse(WEB / "icon.png", media_type="image/png")


#: The line `sw.js` declares its cache version on; replaced when served, and
#: asserted so a no-op cannot bring back stale shells.
_VERSION_LINE = 'const VERSION = "dev";'


def build_version() -> str:
    """This build's cache name: the commit, else the build timestamp, else `dev` (a
    source checkout).
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
    """The service worker, served from the root so its scope covers the whole app.

    `no-cache` so a new worker always replaces the old one. The cache name is
    stamped from the build: `activate` deletes other caches, so every new image
    retires the previous shell automatically.
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
            "background_color": "#faf9f6",
            "theme_color": "#1c6b52",
            # Russian: the install prompt and the page it opens are written
            # in the language the learner reads, not the one being learned.
            "lang": "ru",
            # SVG where accepted, the raster for installers that need one; `maskable` makes
            # Android crop the full-bleed artwork instead of framing it.
            "icons": [
                {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml",
                 "purpose": "any"},
                {"src": "/icon.png", "sizes": "512x512", "type": "image/png",
                 "purpose": "any maskable"},
            ],
        }),
        media_type="application/manifest+json",
    )
