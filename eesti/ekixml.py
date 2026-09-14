"""Reading EKI's dictionary downloads as they actually are, not as their schemas say.

All `*_EKI_CCBY40.xml` files (psv, evs, vsl, har, ekss) have **no root element
and undeclared namespace prefixes**, one article per line —

    <c:A c:KF="psv1"><c:P><c:mg><c:m c:O="aabits">aabits</c:m>…</c:A>

— with `c:`, `x:`, `h:` or `s:` on every tag. The reader streams articles, drops
the prefixes and parses each on its own. `xml:lang` is kept (EVS marks Russian
with it).

EKI entity codes arrive as literal `&ba;` etc.:

    &ba; … &bl;    &ema; … &eml;    &la; … &ll;    &supa; … &supl;    markup
    &v;                                            "or" between alternatives

Markup pairs are removed, content kept; `&v;` becomes ` / `. `russian()` strips
EVS stress marks (`б"уква`) and the perfective mark (`возвест"и*`);
`[по]жениться` keeps its brackets (an optional prefix is meaning).
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

    Reads `.gz` directly (the repo stores these gzipped). Line-buffered, since the
    files are tens of MB. An article that will not parse is skipped.
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
    """All text under a node (`itertext`), entity codes resolved, whitespace collapsed."""
    if node is None:
        return ""
    raw = "".join(node.itertext())
    raw = _ENTITY.sub(lambda m: " / " if m.group(1) == "v" else
                      "&" if m.group(1) == "amp" else "", raw)
    return _SPACE.sub(" ", raw).strip()


def russian(node: ET.Element | None) -> str:
    """`text()` without EVS's stress and aspect marks or its `<xr>` question hints
    (`<x><xr>какой</xr>телеф"он</x>` → `телефон`).
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


#: Compound-boundary marks per dictionary: `+` in EVS (`aabitsa+`), `|` and `\\…\\`
#: in EKSS (`tehase|märk`, `\\sae\\pakk`).
_BOUNDARY = str.maketrans("", "", "+|\\_")


def headwords(article: ET.Element, tag: str = "m") -> list[str]:
    """Every lemma an article answers for, markers removed.

    * a combining form or affix (`akord+`, `ab-`, `-keelne`) answers for none;
    * a phrase entry with a placeholder (EKSS) answers for none;
    * an optional bracketed part (`ainuke[ne]`, `[struktuuri]üksus`) answers for
      both forms;
    * a trailing `_` (homograph marker) is removed; capitalisation still separates
      `Vähk` from `vähk`.
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
    """Add a TEXT column a table from an older build lacks (a local checkout keeps its
    file).
    """
    have = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in have:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")


XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
