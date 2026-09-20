"""Does the recogniser hear *this* learner? The eval that must exist before any
provider is swapped.

WER on native Estonian says little about a Russian-speaking A2 learner reading
aloud, and the engines differ exactly there: a generic Whisper tends to
*correct* what it hears into fluent Estonian, which hides the learner's mistake
and inflates a read-aloud score. So this measures three things per engine:

| Measure | What it answers |
|---|---|
| WER / CER | how much of what was said comes back |
| **false accept** | of recordings with a planted wrong word, how often the word comes back *right* — the failure that flatters the learner |
| latency | whether it can sit in the page at all |

The set is the owner's own voice: `data/eval/asr/<name>.wav` beside
`<name>.txt`, the words as spoken (verbatim, including the planted error), and
optionally `<name>.said` naming the word that was deliberately said wrong.
Recordings are personal data and are **never committed** — `data/` is ignored,
and this module only reads what is there.

Run: `python -m eesti.cli eval --suite asr`. An engine with nothing to measure
is reported as such rather than scored.
"""

from __future__ import annotations

import json
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from ..config import DATA

#: Where the recordings live. Owner-only: personal voice, never in git.
SET = DATA / "eval" / "asr"

#: Enough to tell 10 % from 25 % WER; the plan's target is about 100.
ENOUGH = 20


def _norm(text: str) -> list[str]:
    """Words, lowercased, without punctuation: what both sides are compared as."""
    cleaned = "".join(
        " " if unicodedata.category(ch).startswith("P") else ch
        for ch in text.casefold())
    return cleaned.split()


def distance(a: list, b: list) -> int:
    """Levenshtein distance between two sequences (words or characters)."""
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def wer(said: str, heard: str) -> float:
    words = _norm(said)
    return distance(words, _norm(heard)) / len(words) if words else 0.0


def cer(said: str, heard: str) -> float:
    a = " ".join(_norm(said))
    return distance(list(a), list(" ".join(_norm(heard)))) / len(a) if a else 0.0


@dataclass(frozen=True)
class Clip:
    audio: Path
    said: str                 # what was actually said, verbatim
    planted: str = ""         # the word deliberately said wrong, if any

    @property
    def name(self) -> str:
        return self.audio.stem


def clips(folder: Path | str | None = None) -> list[Clip]:
    """The recordings that have a transcript beside them."""
    root = Path(folder or SET)
    if not root.is_dir():
        return []
    out = []
    for audio in sorted(root.glob("*.wav")) + sorted(root.glob("*.webm")):
        transcript = audio.with_suffix(".txt")
        if not transcript.exists():
            continue
        planted = audio.with_suffix(".said")
        out.append(Clip(audio, transcript.read_text(encoding="utf-8").strip(),
                        planted.read_text(encoding="utf-8").strip()
                        if planted.exists() else ""))
    return out


def run(engine: str = "chain", folder: Path | str | None = None,
        verbose: bool = True) -> dict:
    """Score one engine over the set. `chain` is whatever `asr.transcribe` picks."""
    from ..providers import asr

    recordings = clips(folder)
    if not recordings:
        score = {"engine": engine, "clips": 0, "measured": 0, "broken": 0,
                 "wer": None, "cer": None, "planted_errors": 0,
                 "false_accept": None, "latency_p50": None, "latency_max": None,
                 "valid": False,
                 "invalid_reason": (
                     f"no recordings in {Path(folder or SET)} — record a few "
                     "(see eesti/evals/asr.py) before trusting any number")}
        if verbose:
            print(json.dumps(score, indent=2, ensure_ascii=False))
        return score

    wers, cers, latencies = [], [], []
    planted = accepted = broken = 0
    rows = []
    for clip in recordings:
        audio = clip.audio.read_bytes()
        mime = "audio/wav" if clip.audio.suffix == ".wav" else "audio/webm"
        started = time.monotonic()
        try:
            got = asr.transcribe(audio, mime)
        except Exception:  # noqa: BLE001 - a dead engine is a reported state
            broken += 1
            continue
        latencies.append(time.monotonic() - started)
        if not got.text:
            broken += 1
            continue
        wers.append(wer(clip.said, got.text))
        cers.append(cer(clip.said, got.text))
        if clip.planted:
            planted += 1
            # The failure that matters: the learner said it wrong and the
            # recogniser handed back the right word.
            if clip.planted.casefold() not in _norm(got.text):
                accepted += 1
        rows.append((clip.name, round(wers[-1], 3), got.text[:60]))

    measured = len(wers)
    score = {
        "engine": engine,
        "clips": len(recordings),
        "measured": measured,
        "broken": broken,
        "wer": round(sum(wers) / measured, 3) if measured else None,
        "cer": round(sum(cers) / measured, 3) if measured else None,
        "planted_errors": planted,
        # Of the clips with a planted mistake, how often it was "corrected" away.
        "false_accept": round(accepted / planted, 3) if planted else None,
        "latency_p50": round(sorted(latencies)[len(latencies) // 2], 2) if latencies else None,
        "latency_max": round(max(latencies), 2) if latencies else None,
        "valid": measured >= min(ENOUGH, len(recordings)) and measured > 0,
        "note": ("Own voice, own recordings: a number here describes this "
                 "learner and this microphone, not Estonian speech in general."),
    }
    if not score["valid"]:
        score["invalid_reason"] = (
            f"only {measured} of {len(recordings)} clips were transcribed")
    if verbose:
        print(json.dumps(score, indent=2, ensure_ascii=False))
        for name, rate, heard in rows[:10]:
            print(f"  {name}: WER {rate}  «{heard}»")
    return score
