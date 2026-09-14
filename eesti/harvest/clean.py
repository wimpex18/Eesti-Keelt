"""One way to turn fetched markup into readable Estonian, shared by every
harvester.

    input:  <p>Eesti &#8211; ilus maa. Vaata <a href="…">siit</a>.</p>
    output: 'Eesti – ilus maa. Vaata siit.'

Entities are decoded, tags become spaces (never nothing, so adjacent blocks do
not merge into one word), and the space a tag leaves before punctuation is
removed.

**Entities are decoded twice**, because WordPress double-encodes some
(`&amp;#8211;`). Not to a fixed point: that would turn a legitimately escaped
`&amp;lt;` into `<`.
"""

from __future__ import annotations

import html as _html
import re

_TAG = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+")

#: A space before one of these is never Estonian typography, and it is what a
#: stripped inline tag leaves behind: `<a …>siit</a>.` -> `siit .`
_SPACE_BEFORE_MARK = re.compile(r"\s+([.,!?;:…»”)\]])")

#: The mirror case, rarer: `( siit` from a stripped tag after an opening mark.
_SPACE_AFTER_OPEN = re.compile(r"([(\[«„])\s+")


def text(markup: str, *, drop_urls: bool = True) -> str:
    """Markup in, one line of readable prose out.

    Tags become a space. URLs are dropped by default (link fragments are not
    Estonian words); pass `drop_urls=False` where the address is the content.
    """
    out = _TAG.sub(" ", markup or "")
    out = _html.unescape(_html.unescape(out))
    if drop_urls:
        out = _URL.sub(" ", out)
    out = " ".join(out.split())
    out = _SPACE_BEFORE_MARK.sub(r"\1", out)
    return _SPACE_AFTER_OPEN.sub(r"\1", out)
