"""Rebuild Klint's icons and outlined social artwork from brand/mark.svg.

Run with the project's Python: python deploy/build-brand.py.
Requires CairoSVG, Pillow, fontTools and Brotli (asset tooling only, not app dependencies).
No browser, external font, or image service is needed.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
import cairosvg
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "eesti/web"
BRAND = WEB / "brand"
# Spruce ink and birch ground (DESIGN.md): the tile is ink, the mark birch.
TILE, MARK, PAGE, INK, MUTED = "#15201A", "#F1F4F1", "#F1F4F1", "#15201A", "#56635B"
PATHS = [p.attrib["d"] for p in ET.parse(BRAND / "mark.svg").iter()
         if p.tag.endswith("}path")]


def glyph(fill: str, scale: float = 1) -> str:
    return (f'<g fill="{fill}" transform="translate({32 * (1-scale):g} '
            f'{32 * (1-scale):g}) scale({scale:g})">'
            + "".join(f'<path fill-rule="evenodd" d="{d}"/>' for d in PATHS) + "</g>")


def svg(body: str, width: int = 64, height: int = 64) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">{body}</svg>\n')


def png(image: Image.Image, path: Path) -> None:
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Source", "Original Klint vector artwork: eesti/web/brand/mark.svg, its K "
                  "outlined from Geologica (SIL OFL); rendered by deploy/build-brand.py")
    image.save(path, pnginfo=meta)


def icon(size: int, *, full_bleed: bool = False, mono: bool = False) -> Image.Image:
    """Rasterize the same underlined K used by every vector surface."""
    color = "#000000" if mono else MARK
    background = "" if mono else (
        f'<rect width="64" height="64" rx="{0 if full_bleed else 16}" fill="{TILE}"/>')
    artwork = svg(background + glyph(color, .88 if full_bleed else 1))
    data = cairosvg.svg2png(bytestring=artwork.encode(), output_width=size*4, output_height=size*4)
    return Image.open(io.BytesIO(data)).convert("RGBA").resize((size,size), Image.Resampling.LANCZOS)


def typeface(weight: int, sharp: int = 0) -> TTFont:
    """Estonian lettering takes the sharp cut (SHRP 100), as in the app."""
    font = TTFont(WEB / "fonts/geologica-latin.woff2")
    return instantiateVariableFont(font, {"wght": weight, "SHRP": sharp}, inplace=True)


def lettering(text: str, x: int, y: int, size: int, weight: int, color: str,
              sharp: int = 0) -> str:
    font = typeface(weight, sharp)
    glyphs = font.getGlyphSet()
    cmap, metrics = font.getBestCmap(), font["hmtx"].metrics
    pen, cursor = SVGPathPen(glyphs), 0
    for letter in text:
        name = cmap[ord(letter)]
        glyphs[name].draw(TransformPen(pen, (1, 0, 0, 1, cursor, 0)))
        cursor += metrics[name][0]
    scale = size / font["head"].unitsPerEm
    return (f'<path fill="{color}" transform="translate({x} {y}) scale({scale} {-scale})" '
            f'd="{pen.getCommands()}"/>')


def main() -> None:
    tile = f'<rect width="64" height="64" rx="16" fill="{TILE}"/>' + glyph(MARK)
    (BRAND / "tile.svg").write_text(svg(tile))
    (BRAND / "favicon.svg").write_text(svg(tile))
    (BRAND / "safari-pinned-tab.svg").write_text(svg(glyph("#000000")))
    (BRAND / "icon-maskable.svg").write_text(svg(
        f'<rect width="64" height="64" fill="{TILE}"/>' + glyph(MARK, .88)))
    (BRAND / "icon-mono.svg").write_text(svg(glyph("#000000")))
    for size in (16, 32, 48):
        png(icon(size), BRAND / f"favicon-{size}.png")
    icon(48).save(BRAND / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    for size in (192, 512):
        png(icon(size), BRAND / f"icon-{size}.png")
    png(icon(512, full_bleed=True), BRAND / "icon-maskable.png")
    png(icon(512, mono=True), BRAND / "icon-mono.png")
    png(icon(180, full_bleed=True), BRAND / "apple-touch-icon.png")
    # Keep the old raster endpoint usable for bookmarks and installed copies.
    png(icon(512, full_bleed=True), WEB / "icon.png")

    font_bytes = {}
    for weight, sharp in ((450, 100), (650, 100)):
        font = typeface(weight, sharp)
        font.flavor = None
        buffer = io.BytesIO()
        font.save(buffer)
        font_bytes[weight, sharp] = buffer.getvalue()
    # A quiet, honest card: identity, subject, course span, learning loop. No readiness claim.
    for name, width, height in (("og-default", 1200, 630), ("twitter-default", 1200, 600)):
        body = f'<rect width="{width}" height="{height}" fill="{PAGE}"/>'
        body += f'<g transform="translate(80 80) scale(1.5)">{tile}</g>'
        lines = [("Klint", 210, 153, 68, 650, INK, 100),
                 ("Eesti keel", 80, 336, 88, 650, INK, 100),
                 ("Algusest kuni B1-ni", 80, 401, 38, 450, INK, 100),
                 ("Õpi. Harjuta. Kontrolli.", 80, height - 80, 30, 450, MUTED, 100)]
        image = Image.new("RGB", (width, height), PAGE)
        image.paste(icon(96), (80, 80), icon(96))
        draw = ImageDraw.Draw(image)
        for text, x, baseline, size, weight, color, sharp in lines:
            body += lettering(text, x, baseline, size, weight, color, sharp)
            pilfont = ImageFont.truetype(io.BytesIO(font_bytes[weight, sharp]), size)
            draw.text((x, baseline), text, font=pilfont, fill=color, anchor="ls")
        (BRAND / f"{name}.svg").write_text(svg(body, width, height))
        png(image, BRAND / f"{name}.png")

    (BRAND / "wordmark.svg").write_text(svg(
        lettering("Klint", 0, 56, 64, 650, "currentColor", 100), 220, 72))
    # The page needs inline fills for theme and motion. Keep those small copies
    # mechanically tied to the same vector source.
    page = WEB / "index.html"
    markup = page.read_text(encoding="utf-8")
    for location, classname in (("header", "brand-mark"),):
        inline = (f'<svg class="{classname}" viewBox="0 0 64 64" aria-hidden="true">'
                  + "".join(f'<path class="brand-{role}" fill-rule="evenodd" d="{d}"/>' for role, d in zip(("k", "bar"), PATHS)) + "</svg>")
        pattern = f'(<!-- brand:{location}:start -->).*?(<!-- brand:{location}:end -->)'
        markup, count = re.subn(pattern, lambda m: m[1] + "\n      " + inline + "\n      " + m[2],
                               markup, flags=re.S)
        if count != 1:
            raise RuntimeError(f"Expected one {location} mark in index.html")
    page.write_text(markup, encoding="utf-8")


if __name__ == "__main__":
    main()
