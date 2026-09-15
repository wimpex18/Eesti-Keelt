"""The single-page app's source, for tests that read it as text.

Collected by glob, so a new module is always included:

* `markup_and_script()` — the page and every module: behaviour, wording, the
  page/API contract.
* `styles()` — the stylesheet.
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
    """The authored HTML alone: a `data-tab="${tab}"` in a module's selector string is
    not a destination.
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
    """The whole body of one JS function, found by brace matching (fixed-size slices
    stop reaching code as functions grow). Raises if the function is missing.
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
    """Everything inside one `@media` block, by the same brace matching."""
    return function_body(css, query)
