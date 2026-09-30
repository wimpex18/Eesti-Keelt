"""Rebuild Laudtee's icons and outlined social artwork from brand/mark.svg.

Run with the project's Python: python deploy/build-brand.py.
Requires Pillow, fontTools and Brotli (asset tooling only, not app dependencies).
No browser, external font, or image service is needed.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "eesti/web"
BRAND = WEB / "brand"
BLUE, WHITE, PAGE, INK, MUTED = "#0030de", "#ffffff", "#f8fafc", "#0f172a", "#566376"
PATHS = [p.attrib["d"] for p in ET.parse(BRAND / "mark.svg").iter()
         if p.tag.endswith("}path")]


def glyph(fill: str, scale: float = 1) -> str:
    return (f'<g fill="{fill}" transform="translate({32 * (1-scale):g} '
            f'{32 * (1-scale):g}) scale({scale:g})">'
            + "".join(f'<path d="{d}"/>' for d in PATHS) + "</g>")


def svg(body: str, width: int = 64, height: int = 64) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">{body}</svg>\n')


def png(image: Image.Image, path: Path) -> None:
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Source", "Original Laudtee vector artwork: eesti/web/brand/mark.svg; "
                  "Geologica (SIL OFL), rendered by deploy/build-brand.py")
    meta.add_text("impeccable:prompt", "Origin: original vector artwork in eesti/web/brand/mark.svg, "
                  "rasterized by deploy/build-brand.py. Social lettering uses self-hosted "
                  "Geologica by Monokrom, SIL OFL 1.1. No image generation service.")
    image.save(path, pnginfo=meta)


def icon(size: int, *, full_bleed: bool = False, mono: bool = False) -> Image.Image:
    """Supersample the three straight-edged planks; masks need their own inset."""
    factor = 4
    image = Image.new("RGBA", (size * factor, size * factor))
    draw = ImageDraw.Draw(image)
    if not mono:
        if full_bleed:
            draw.rectangle((0, 0, size * factor, size * factor), fill=BLUE)
        else:
            draw.rounded_rectangle((0, 0, size * factor - 1, size * factor - 1),
                                   radius=size * factor / 4, fill=BLUE)
    scale = .88 if full_bleed else 1
    for d in PATHS:
        # The master uses M, implicit L, V, L, Z only. Expand V to (last x, y).
        values = re.findall(r"[MVLZ]|-?\d+(?:\.\d+)?", d)
        points, i = [], 0
        while i < len(values):
            if values[i] in ("M", "L", "Z"):
                i += 1
            elif values[i] == "V":
                points.append((points[-1][0], float(values[i + 1])))
                i += 2
            else:
                points.append((float(values[i]), float(values[i + 1])))
                i += 2
        draw.polygon([((32 + (x - 32) * scale) * size * factor / 64,
                       (32 + (y - 32) * scale) * size * factor / 64)
                      for x, y in points], fill="#000000" if mono else WHITE)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def typeface(weight: int) -> TTFont:
    font = TTFont(WEB / "fonts/geologica-latin.woff2")
    return instantiateVariableFont(font, {"wght": weight, "SHRP": 0}, inplace=True)


def lettering(text: str, x: int, y: int, size: int, weight: int, color: str) -> str:
    font = typeface(weight)
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
    tile = f'<rect width="64" height="64" rx="16" fill="{BLUE}"/>' + glyph(WHITE)
    (BRAND / "tile.svg").write_text(svg(tile))
    (BRAND / "favicon.svg").write_text(svg(tile))
    (BRAND / "safari-pinned-tab.svg").write_text(svg(glyph("#000000")))
    (BRAND / "icon-maskable.svg").write_text(svg(
        f'<rect width="64" height="64" fill="{BLUE}"/>' + glyph(WHITE, .88)))
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
    for weight in (450, 650):
        font = typeface(weight)
        font.flavor = None
        buffer = io.BytesIO()
        font.save(buffer)
        font_bytes[weight] = buffer.getvalue()
    # A quiet, honest card: identity, subject, learning loop. No readiness claim.
    for name, width, height in (("og-default", 1200, 630), ("twitter-default", 1200, 600)):
        body = f'<rect width="{width}" height="{height}" fill="{PAGE}"/>'
        body += f'<g transform="translate(80 80) scale(1.5)">{tile}</g>'
        lines = [("Laudtee", 210, 153, 68, 650, INK),
                 ("Eesti keel", 80, 336, 88, 650, BLUE),
                 ("A2 / B1", 80, 401, 38, 450, INK),
                 ("Õpi. Harjuta. Kontrolli.", 80, height - 80, 30, 450, MUTED)]
        image = Image.new("RGB", (width, height), PAGE)
        image.paste(icon(96), (80, 80), icon(96))
        draw = ImageDraw.Draw(image)
        for text, x, baseline, size, weight, color in lines:
            body += lettering(text, x, baseline, size, weight, color)
            pilfont = ImageFont.truetype(io.BytesIO(font_bytes[weight]), size)
            draw.text((x, baseline), text, font=pilfont, fill=color, anchor="ls")
        (BRAND / f"{name}.svg").write_text(svg(body, width, height))
        png(image, BRAND / f"{name}.png")

    (BRAND / "wordmark.svg").write_text(svg(
        lettering("Laudtee", 0, 56, 64, 650, "currentColor"), 294, 72))
    # The page needs inline fills for theme and motion. Keep those small copies
    # mechanically tied to the same vector source.
    page = WEB / "index.html"
    markup = page.read_text(encoding="utf-8")
    for location, classname in (("header", "brand-mark"), ("splash", "brand-splash-mark")):
        inline = (f'<svg class="{classname}" viewBox="0 0 64 64" aria-hidden="true">'
                  + "".join(f'<path d="{d}"/>' for d in PATHS) + "</svg>")
        pattern = f'(<!-- brand:{location}:start -->).*?(<!-- brand:{location}:end -->)'
        markup, count = re.subn(pattern, lambda m: m[1] + "\n      " + inline + "\n      " + m[2],
                               markup, flags=re.S)
        if count != 1:
            raise RuntimeError(f"Expected one {location} mark in index.html")
    page.write_text(markup, encoding="utf-8")


if __name__ == "__main__":
    main()
