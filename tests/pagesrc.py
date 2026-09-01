"""The single-page app's source, for the tests that read it as text.

Twenty test files opened `eesti/web/index.html` directly, which was right while
the page *was* the app: 3 506 lines of markup, 703 lines of stylesheet and
2 300 lines of script in one file. It is a page, a stylesheet and fourteen ES
modules now, and a check that still read only `index.html` would go quiet
rather than fail -- it would find no `const RU`, no `loadPath`, no `api(` call,
and pass by having nothing to object to.

So the sources are collected here, by glob, and the tests ask for the half they
mean:

* `markup_and_script()` -- the page and every module. This is what a check
  about behaviour, wording or the page/API contract wants.
* `styles()` -- the stylesheet. `test_design_tokens` and `test_web_layout` are
  about CSS and would be confused by 2 300 lines of JavaScript.

A glob rather than a list of filenames, deliberately: a hand-maintained list of
the things to scan is exactly how `test_ui_language` went blind to a module and
missed a real defect sitting in it.
"""

from __future__ import annotations

from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "eesti" / "web"

PAGE = WEB / "index.html"
CSS = WEB / "app.css"
JS = WEB / "js"


def scripts() -> list[Path]:
    """Every ES module the page loads, `main.js` first."""
    found = sorted(JS.glob("*.js"))
    assert found, f"no modules in {JS} -- every scan below would measure nothing"
    return sorted(found, key=lambda p: (p.name != "main.js", p.name))


def markup() -> str:
    """The authored HTML alone, for checks about what the page declares.

    Distinct from `markup_and_script`: a `data-tab="${tab}"` inside a selector
    string in a module is code looking for a destination, not a destination.
    """
    return PAGE.read_text(encoding="utf-8")


def markup_and_script() -> str:
    """The page and its modules, concatenated. No CSS."""
    return "\n".join(p.read_text(encoding="utf-8")
                     for p in [PAGE, *scripts()])


def styles() -> str:
    return CSS.read_text(encoding="utf-8")


def everything() -> str:
    return markup_and_script() + "\n" + styles()
