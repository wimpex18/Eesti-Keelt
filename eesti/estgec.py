"""EstGEC-L2: word-order errors a linguist labelled, with the writer's CEFR level.

`tlu-dt-nlp/EstGEC-L2-Corpus` (Tallinn University): learner sentences from the
Estonian Interlanguage Corpus, error-tagged in M2 format by several annotators,
organised by CEFR level. `R:WO` is a label, not an inference.

Merged with the TalTech pool in `wordorder.py`, not replacing it: the corpora
share no sentences, and both pass the same `is_reordering` gate (pairs that also
change a case ending, `R:WO:NOM:FORM`, are rejected by it).

Licence: GPL-3.0, © Language Technology Research Group, Tallinn University. Not
conveyed: it rides `content.db` to one deployment behind Access and is never
served to third parties. (MultiGEC-2025's `EIC` copy is research-only; TLU's own
publication is used.)
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path

from .config import CACHE

SOURCE_ID = "estgec-l2"

RAW = "https://raw.githubusercontent.com/tlu-dt-nlp/EstGEC-L2-Corpus/main"

#: Which file carries which level. The test split is per level; the dev split is
#: one combined file, so those items have level `None`. Five requests, once.
SOURCES: tuple[tuple[str, str | None], ...] = (
    ("test/A2/A2_source_gold.txt", "A2"),
    ("test/B1/B1_source_gold.txt", "B1"),
    ("test/B2/B2_source_gold.txt", "B2"),
    ("test/C1/C1_source_gold.txt", "C1"),
    ("dev/source_gold_dev.txt", None),
)

TIMEOUT = 30.0
CACHE_DIR = CACHE / "estgec"

#: M2 edit line; the last field is the annotator. Only annotator 0 is read, so a
#: sentence is not offered several times with different answers.
_EDIT = re.compile(r"^A (\d+) (\d+)\|\|\|([^|]*)\|\|\|([^|]*)\|\|\|")


def parse(path: Path | str, level: str | None = None) -> list[tuple[str, str, str | None]]:
    """(learner wrote, native corrected, level) for the word-order-only sentences; an
    unfetched corpus yields no items.
    """
    path = Path(path)
    if not path.exists():
        return []

    out: list[tuple[str, str, str | None]] = []
    tokens: list[str] | None = None
    edits: list[tuple[int, int, str, str]] = []

    def flush() -> None:
        if tokens is None:
            return
        # `noop` is the annotator saying the sentence needed nothing.
        real = [e for e in edits if e[2] != "noop"]
        if not real or not all("WO" in e[2] for e in real):
            return
        fixed = _apply(tokens, real)
        if fixed is None:
            return
        wrong, right = _detokenize(tokens), _detokenize(fixed)
        if wrong != right:
            out.append((wrong, right, level))

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("S "):
            flush()
            tokens, edits = line[2:].split(), []
        elif line.startswith("A "):
            m = _EDIT.match(line)
            if m and line.rstrip().endswith("|||0"):
                edits.append((int(m.group(1)), int(m.group(2)),
                              m.group(3), m.group(4)))
    flush()
    return out


#: Closing punctuation, a quote and a bracket: everything that should not carry
#: the space M2 tokenisation puts in front of it.
_TIGHT_LEFT = frozenset('.,!?;:)»"\'')
_TIGHT_RIGHT = frozenset('(«')


def _detokenize(tokens: list[str]) -> str:
    """Detokenise (`See on Islandi pealinn .` → `…pealinn.`) so the two-way choice
    shows no spurious visible differences.
    """
    out = ""
    for token in tokens:
        if out and token[0] not in _TIGHT_LEFT and out[-1] not in _TIGHT_RIGHT:
            out += " "
        out += token
    return out


def _apply(tokens: list[str], edits: list[tuple[int, int, str, str]]) -> list[str] | None:
    """Rebuild the corrected sentence from the edit spans; None when edits overlap."""
    out: list[str] = []
    i = 0
    for start, end, _type, replacement in sorted(edits):
        if start < i:
            return None
        out += tokens[i:start]
        if replacement != "-NONE-":
            out += replacement.split()
        i = end
    return out + tokens[i:]


def fetch(cache_dir: Path | str | None = None) -> list[Path]:
    """Download the five files once, politely; a short result is allowed."""
    root = Path(cache_dir or CACHE_DIR)
    root.mkdir(parents=True, exist_ok=True)
    got: list[Path] = []
    for name, _level in SOURCES:
        target = root / name.replace("/", "_")
        if target.exists() and target.stat().st_size:
            got.append(target)
            continue
        try:
            with urllib.request.urlopen(f"{RAW}/{name}", timeout=TIMEOUT) as resp:
                target.write_bytes(resp.read())
        except (urllib.error.URLError, OSError, TimeoutError):
            continue
        got.append(target)
    return got


def pairs(cache_dir: Path | str | None = None) -> list[tuple[str, str, str | None]]:
    """Every word-order-only pair on disk, with its level where there is one."""
    root = Path(cache_dir or CACHE_DIR)
    out: list[tuple[str, str, str | None]] = []
    for name, level in SOURCES:
        out += parse(root / name.replace("/", "_"), level)
    return out
