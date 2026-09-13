"""Reading EKI's dictionary downloads as they actually are, not as their schemas say.

Every `*_EKI_CCBY40.xml` from arhiiv.eki.ee/litsents was measured on 2026-09-13
(psv, evs, vsl, har, ekss), and all five share a shape no schema-built fixture
would have: **there is no root element and the namespace prefixes are never
declared.** The file is one article per line —

    <c:A c:KF="psv1"><c:P><c:mg><c:m c:O="aabits">aabits</c:m>…</c:A>

— separated by blank lines, with `c:` (psv), `x:` (evs, vsl), `h:` (har) or `s:`
(ekss) on every tag and attribute. Handed to an XML parser whole, the first
byte is an error: `psv.py` failed on its first real run with "unbound prefix:
line 1, column 0", after a clean suite against a fixture built from the schema.

So the reader streams articles one at a time, drops the prefixes, and parses
each article on its own. `xml:lang` is kept — it is the one attribute XML
itself defines, and it is how EVS marks which text is Russian.

Text carries EKI's entity codes, escaped in the file as `&amp;ba;` and so read
back as literal `&ba;`:

    &ba; … &bl;    &ema; … &eml;    &la; … &ll;    &supa; … &supl;    markup
    &v;                                            "or" between alternatives

The markup pairs are removed and their content kept. `&v;` becomes ` / `.
Russian in EVS marks stress with `"` before the vowel (`б"уква`) and the
perfective of an aspect pair with `*` (`возвод"ить/возвест"и*`); `russian()`
strips both, because a learner copying the word into a search box needs the
spelling, and neither mark is part of it. `[по]жениться` keeps its brackets:
an optional prefix is meaning, not markup.
"""

from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

#: An article opens with `<p:A` or a bare `<A` — the bare form keeps a
#: hand-written, declared-namespace-free fixture readable by the same code.
_OPEN = re.compile(r"<(?:\w+:)?A[\s>]")
_CLOSE = re.compile(r"</(?:\w+:)?A>")
_TAG_PREFIX = re.compile(r"(</?)\w+:")
_ATTR_PREFIX = re.compile(r"(\s)(?!xml:)\w+:(\w+\s*=)")
_ENTITY = re.compile(r"&(\w+);")
_SPACE = re.compile(r"\s+")


def _unprefix(fragment: str) -> str:
    return _ATTR_PREFIX.sub(r"\1\2", _TAG_PREFIX.sub(r"\1", fragment))


def articles(path: Path | str) -> Iterator[ET.Element]:
    """Every `A` element in the file, one at a time, prefixes removed.

    A `.gz` path is read compressed: the repository carries these files
    gzipped, because `evs` raw is 87 MB against GitHub's 50 MB warning.

    Line-buffered rather than regex over the whole file: `evs` is 89 MB and
    `ekss` 70 MB, and nothing here needs two articles at once. An article that
    will not parse is skipped, not raised — EKI warn their XML does not validate
    against their own schema, and one bad entry is not a reason to lose 70 000.
    """
    buffer: list[str] = []
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not buffer:
                start = _OPEN.search(line)
                if not start:
                    continue
                line = line[start.start():]
            buffer.append(line)
            joined = "".join(buffer)
            end = _CLOSE.search(joined)
            if not end:
                continue
            buffer = []
            try:
                yield ET.fromstring(_unprefix(joined[: end.end()]))
            except ET.ParseError:
                continue


def text(node: ET.Element | None) -> str:
    """All text under a node: entity codes resolved, whitespace collapsed.

    `itertext`, not `.text`: markup inside a definition would otherwise cut it
    off at its first emphasised word.
    """
    if node is None:
        return ""
    raw = "".join(node.itertext())
    raw = _ENTITY.sub(lambda m: " / " if m.group(1) == "v" else
                      "&" if m.group(1) == "amp" else "", raw)
    return _SPACE.sub(" ", raw).strip()


def russian(node: ET.Element | None) -> str:
    """`text()`, without EVS's stress and aspect marks or its question hints.

    `<xr>` (198 in EVS) is the question a translation answers —
    `<x><xr>какой</xr>телеф"он</x>` for the attributive use of `telefon`. It is
    a hint, not part of the word, and joined into the text it read
    "какойтелефон" on a word card.
    """
    if node is None:
        return ""
    shell = ET.Element(node.tag)
    shell.text = node.text
    for child in node:
        if child.tag == "xr":
            shell.text = (shell.text or "") + " " + (child.tail or "")
        else:
            shell.append(child)
    return text(shell).replace('"', "").replace("*", "").replace("[]", "").strip()


#: Compound-boundary marks, per dictionary (measured 2026-09-13): `+` in EVS
#: (`aabitsa+`, 31 108), `|` and `\\…\\` in EKSS (`tehase|märk` 28 276,
#: `\\sae\\pakk` 58 814). Stripping only `+` stored every EKSS compound under
#: a key no lookup could ever match.
_BOUNDARY = str.maketrans("", "", "+|\\_")


def headwords(article: ET.Element, tag: str = "m") -> list[str]:
    """Every lemma an article answers for, markers removed.

    * a combining form or affix (`akord+`, `ab-`, `-keelne`) answers for none;
    * a phrase entry (`(kindel) kui ~ nagu aamen kirikus`, EKSS) answers for
      none — a learner clicks words, not idioms with a placeholder;
    * an optional part in brackets (`ainuke[ne]` in EVS, `[struktuuri]üksus`
      in HAR) answers for both forms;
    * trailing `_` tells homographs apart (`Vähk_` the sign): removed, and the
      capital keeps `Vähk` apart from `vähk`.
    """
    raw = text(article.find(f".//{tag}"))
    if not raw or "~" in raw or "(" in raw:
        return []
    ends = raw.replace("_", "").strip()
    if not ends or ends[0] in "+-" or ends[-1] in "+-":
        return []
    word = raw.translate(_BOUNDARY).strip()
    if "[" in word:
        full = word.replace("[", "").replace("]", "")
        short = re.sub(r"\[[^\]]*\]", "", word)
        return [w for w in dict.fromkeys((full, short)) if w]
    return [word]


def headword(article: ET.Element) -> str | None:
    """The first of `headwords()`, for the dictionaries that key one row per lemma."""
    found = headwords(article)
    return found[0] if found else None


def ensure_column(conn, table: str, column: str) -> None:
    """Add a TEXT column a table created by an older build lacks.

    `CREATE TABLE IF NOT EXISTS` does nothing to a table that already exists,
    so a words database built before a column was added would raise on the
    first query naming it. The words database is rebuilt with every image, but a
    local checkout keeps its file.
    """
    have = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in have:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")


XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
