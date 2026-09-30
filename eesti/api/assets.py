"""The page and the static files around it.

Served locally, not from a CDN, so a lesson never depends on someone else's
uptime. File names come from the URL, so every resolved path is checked against
its directory.
"""

from __future__ import annotations

import json
import os
from html import escape
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from .deps import WEB

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> str:
    origin = str(request.base_url).rstrip("/")
    # The guarded origin accepts only the Worker's header. Local development
    # uses its own request URL and ignores a forged proxy header.
    forwarded = request.headers.get("x-brand-origin", "")
    if os.environ.get("PROXY_TOKEN") and forwarded:
        parsed = urlsplit(forwarded)
        if (parsed.scheme == "https" and parsed.hostname and not parsed.username
                and not parsed.password and not parsed.path and not parsed.query
                and not parsed.fragment):
            origin = forwarded
    return ((WEB / "index.html").read_text(encoding="utf-8")
            .replace("__BRAND_ORIGIN__", escape(origin, quote=True))
            .replace("__BRAND_REVEAL__", (WEB / "brand-reveal.js").read_text(encoding="utf-8")))


# --------------------------------------------------------------------------
# Installable on a phone: manifest and icons
# --------------------------------------------------------------------------

#: Compatibility endpoint for existing bookmarks. The vector master and all
#: install variants live together under brand/; deploy/build-brand.py builds them.
ICON_SVG = (WEB / "brand/favicon.svg").read_text(encoding="utf-8")
BRAND_TYPES = {".svg": "image/svg+xml", ".png": "image/png",
               ".ico": "image/x-icon"}


@router.get("/brand/{name}")
def brand_asset(name: str) -> FileResponse:
    path = (WEB / "brand" / name).resolve()
    if (path.parent != (WEB / "brand").resolve() or not path.is_file()
            or path.suffix not in BRAND_TYPES):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, media_type=BRAND_TYPES[path.suffix],
                        headers={"Cache-Control": "no-cache"})


@router.get("/favicon.ico")
def favicon() -> FileResponse:
    return brand_asset("favicon.ico")


@router.get("/apple-touch-icon.png")
def apple_touch_icon() -> FileResponse:
    return brand_asset("apple-touch-icon.png")


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


@router.get("/fonts/{name}")
def font(name: str) -> FileResponse:
    """The typeface (Geologica, SIL OFL 1.1, its licence beside it), served from this
    origin so the installed app keeps its type offline and the page makes no
    request to a font host. A week's cache; the service worker keeps its own copy.
    """
    path = (WEB / "fonts" / name).resolve()
    # Path traversal: `name` comes from the URL.
    if (path.parent != (WEB / "fonts").resolve() or not path.is_file()
            or path.suffix != ".woff2"):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, media_type="font/woff2",
                        headers={"Cache-Control": "public, max-age=604800"})


@router.get("/icon.svg")
def icon_svg() -> Response:
    return Response((WEB / "brand/favicon.svg").read_text(encoding="utf-8"),
                    media_type="image/svg+xml", headers={"Cache-Control": "no-cache"})


@router.get("/icon.png")
def icon_png() -> FileResponse:
    """Compatibility raster for installed copies using the original URL."""
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
            "name": "Laudtee · Eesti keel",
            "short_name": "Laudtee",
            "description": "Eesti keele õppimine ja A2/B1 tasemeeksami ettevalmistus",
            "id": "/",
            "scope": "/",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f8fafc",
            "theme_color": "#f8fafc",
            # Russian: the install prompt and the page it opens are written
            # in the language the learner reads, not the one being learned.
            "lang": "ru",
            # Separate regular and maskable artwork: platform masks must not
            # clip the glyph or leave transparent corners in the crop.
            "icons": [
                {"src": "/brand/favicon.svg", "sizes": "any", "type": "image/svg+xml",
                 "purpose": "any"},
                {"src": "/brand/icon-192.png", "sizes": "192x192", "type": "image/png",
                 "purpose": "any"},
                {"src": "/brand/icon-512.png", "sizes": "512x512", "type": "image/png",
                 "purpose": "any"},
                {"src": "/brand/icon-maskable.png", "sizes": "512x512", "type": "image/png",
                 "purpose": "maskable"},
                {"src": "/brand/icon-mono.png", "sizes": "512x512", "type": "image/png",
                 "purpose": "monochrome"},
            ],
        }),
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache"},
    )
