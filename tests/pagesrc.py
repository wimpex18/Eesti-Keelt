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


def function_body(source: str, name: str) -> str:
    """The whole body of one JS function, found by matching its braces.

    Written because three assertions in `test_ui_contract.py` took a fixed
    slice — `source.split("async function loadListenLibrary")[1][:2000]` — and
    the function outgrew the window. The behaviour they guard was still
    correct; the tests had simply stopped reaching it. A character count is a
    fuse, and widening it only resets the fuse.

    Raises rather than returning "" for a function that is not there: a
    renamed function must fail loudly, which is the one thing the slice
    version got right.
    """
    start = source.index(name)
    open_brace = source.index("{", start)
    depth = 0
    for i in range(open_brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace:i + 1]
    raise AssertionError(f"unbalanced braces after {name!r}")


def media_block(css: str, query: str) -> str:
    """Everything inside one `@media` block, by the same brace matching.

    `.rail`'s `display:flex` sits 2 278 characters into the 1080px block, and
    the test that checks the rail comes back on read the first 700.
    """
    return function_body(css, query)
