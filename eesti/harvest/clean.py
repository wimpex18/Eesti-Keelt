"""One way to turn fetched markup into readable Estonian.

Four harvesters each carried a private copy of `_TAG_RE = re.compile(r"<[^>]+>")`
and their own idea of what else to do with it. They had already drifted into
three different behaviours, and every one of the differences reached the
learner:

    input:  <p>Eesti &#8211; ilus maa. Vaata <a href="…">siit</a>.</p>

    err.py      'Eesti &#8211; ilus maa. Vaata siit .'   entities undecoded
    evkk.py     'Eesti – ilus maa. Vaata siit.'          joins across tags
    lihtsad.py  'Eesti – ilus maa. Vaata siit .'
    selges.py   'Eesti – ilus maa. Vaata siit .'

`err.py` never decoded entities at all, so its 27 000 words of transcript — the
richest text in the corpus, and reachable from the app since the listening
shelf was wired up — show `&#8211;` as literal characters. `evkk.py` replaces
tags with nothing rather than a space, so `<p>Esimene</p><p>Teine</p>` becomes
the single word `EsimeneTeine`. And all four leave a space in front of a full
stop whenever a tag sat there, which the punctuation drill then displays as
correct Estonian.

Three defects, one cause: the same job written four times. This is the module
that does it once.

**Entities are decoded twice.** WordPress double-encodes some of them
(`&amp;#8211;`), which is where the second pass came from. Unescaping to a
fixed point would be neater and is deliberately not done: it would turn a
legitimately-escaped `&amp;lt;` into `<` and there is no third layer in any
observed source.
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

    Tags become a **space**, never nothing: two block elements butted together
    are two words, and joining them invents a word that is in no dictionary —
    which then fails lookup, fails the known-word count, and can be served as a
    dictation answer.

    URLs go by default. The reader makes every word clickable, and the pieces
    of a link (`kultuur`, `err`, `ee`) are not Estonian words. Pass
    `drop_urls=False` where the address is the content.
    """
    out = _TAG.sub(" ", markup or "")
    out = _html.unescape(_html.unescape(out))
    if drop_urls:
        out = _URL.sub(" ", out)
    out = " ".join(out.split())
    out = _SPACE_BEFORE_MARK.sub(r"\1", out)
    return _SPACE_AFTER_OPEN.sub(r"\1", out)
