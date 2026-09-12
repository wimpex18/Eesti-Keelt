"""EstGEC-L2: word-order errors a linguist labelled, at levels this learner sits.

`wordorder.py` refuses to generate items and *infers* which corrections are
re-orderings, because TalTech's pairs carry no error annotation: same words in
a different sequence is the only signature available without one. That
inference works — 322 items — and it has two costs it cannot pay off. It
cannot see a re-ordering that co-occurs with any other edit, and it cannot say
what level the sentence is, because nothing in the file says.

This corpus says both. `tlu-dt-nlp/EstGEC-L2-Corpus` is 258 texts and 3 721
sentences from the Estonian Interlanguage Corpus — the same corpus whose error
taxonomy already weights this app's curriculum — error-tagged in **M2 format**
by at least three annotators each, in directories named for the CEFR level of
the writer. `R:WO` is a label, not a guess.

Why this is merged with the TalTech pool rather than replacing it
-----------------------------------------------------------------
Measured before deciding, which is the only reason the answer is trustworthy:

* **Zero overlap.** Not one corrected sentence appears in both corpora. They
  are different learners writing different texts, collected by different
  universities. Replacing would throw 322 items away and buy nothing.
* **232 of 237 pass `is_reordering` unchanged.** The two sources are
  homogeneous under the filter the drill already applies, so merging does not
  mix two standards of item. The five that fail are `R:WO:NOM:FORM` — a
  re-ordering that also changes a word's case, like `pealinn Islandil` ->
  `Islandi pealinn` — and those are exactly the pairs a learner could answer
  from the case ending instead of the order. The filter keeps its job.

So: one gate, two feeders. `is_reordering` stays the arbiter for both, which
also means this module cannot lower the bar by arriving.

Licence
-------
GPL-3.0, © 2023 Language Technology Research Group, Tallinn University School
of Digital Technologies. GPL obligations attach to *conveying* the work, and
this app conveys nothing: the corpus rides `content.db` to one deployment
behind Access, the same road as every other ungranted thing here, and is never
served to a third party. Were that ever to change, the obligation would be to
carry the licence and point at the source — which `/api/sources` now does
structurally.

Note the door this came through. MultiGEC-2025 distributes the same 258 texts
as `EIC` under terms restricting use to "scientific or research purposes",
which exam self-study is not. TLU publish the identical material themselves
with no such clause. The corpus was not out of reach; one of its two
distributions was.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path

from .config import CACHE

SOURCE_ID = "estgec-l2"

RAW = "https://raw.githubusercontent.com/tlu-dt-nlp/EstGEC-L2-Corpus/main"

#: Which file carries which level, and the honest gap in the middle.
#:
#: The test split is published per CEFR level, so those sentences arrive with
#: the level the writer was sitting at. The dev split is published only as one
#: combined file -- its per-level directories hold individual documents, and
#: fetching 130-odd of them to recover a label is not worth doing to somebody
#: else's server. Those items get `None`, which is what this project does
#: instead of inventing a scale: a level it does not know is not a level it
#: guesses. Five requests in total, once.
SOURCES: tuple[tuple[str, str | None], ...] = (
    ("test/A2/A2_source_gold.txt", "A2"),
    ("test/B1/B1_source_gold.txt", "B1"),
    ("test/B2/B2_source_gold.txt", "B2"),
    ("test/C1/C1_source_gold.txt", "C1"),
    ("dev/source_gold_dev.txt", None),
)

TIMEOUT = 30.0
CACHE_DIR = CACHE / "estgec"

#: `A 3 4|||R:NOM:FORM|||sind|||REQUIRED|||-NONE-|||0` — the last field is the
#: annotator. Only annotator 0 is read: the corpus carries up to three parallel
#: annotations of the same sentence and taking all of them would offer the
#: learner the same item several times over, with different "right" answers.
_EDIT = re.compile(r"^A (\d+) (\d+)\|\|\|([^|]*)\|\|\|([^|]*)\|\|\|")


def parse(path: Path | str, level: str | None = None) -> list[tuple[str, str, str | None]]:
    """(learner wrote, native corrected, level) for the word-order-only sentences.

    Absence is a supported state, like every other harvested file here: a
    checkout that has not fetched the corpus reads as no items rather than as
    an error.
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
    """Put the sentence back the way a person writes it.

    M2 is tokenised -- `See on Islandi pealinn .` -- and the drill shows both
    sentences to the learner side by side. A space before the full stop is
    something they can see, and this project has just spent a commit on the
    principle that every visible difference in a two-way choice is one the
    learner can answer on. Here it would be worse than that: the difference is
    identical in both options, so it teaches nothing and simply looks wrong.
    """
    out = ""
    for token in tokens:
        if out and token[0] not in _TIGHT_LEFT and out[-1] not in _TIGHT_RIGHT:
            out += " "
        out += token
    return out


def _apply(tokens: list[str], edits: list[tuple[int, int, str, str]]) -> list[str] | None:
    """Rebuild the corrected sentence from the edit spans.

    None when two edits overlap. The corpus allows that deliberately — a
    spelling error *inside* a word-order error is annotated as both — and a
    sentence whose spans cannot be applied in sequence is one this module has
    no business guessing at.
    """
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
    """Download the five files, once. Politely, and allowed to come back short.

    A public repository under a free licence, so unlike EKI's downloads there
    is no gate to walk through and no reason for the learner to do this by
    hand. Unlike Sõnaveeb there is nothing to hammer: five files, once.
    """
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
