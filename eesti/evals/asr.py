"""Does the recogniser hear *this* learner? The eval that must exist before any
provider is swapped.

WER on native Estonian says little about a Russian-speaking A2 learner reading
aloud, and a recogniser may normalise an incorrect form into fluent Estonian.
That risk needs measurement on verified learner recordings:

| Measure | What it answers |
|---|---|
| WER / CER | how much of what was said comes back |
| **false accept** | of recordings with a planted wrong word, how often the word comes back *right* — the failure that flatters the learner |
| latency | whether it can sit in the page at all |

The set is the owner's own voice: `data/eval/asr/<name>.wav` beside
`<name>.txt`, the words as spoken (verbatim, including the planted error), and
`<name>.verified.json` sealing a human-reviewed transcript and token annotations.
An unreviewed prompt (including legacy `.said` annotations) is never scored.
Recordings are personal data and are **never committed** — `data/` is ignored,
and this module only reads what is there.

Run: `python -m eesti.cli eval --suite asr`. An engine with nothing to measure
is reported as such rather than scored.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from ..config import DATA

#: Where the recordings live. Owner-only: personal voice, never in git.
SET = Path(os.environ.get("EESTI_ASR_EVAL_DIR", DATA / "eval" / "asr"))

#: Minimum pilot size, not a statistical power guarantee or a promotion gate.
ENOUGH = 20


def _norm(text: str) -> list[str]:
    """Words, lowercased, without punctuation — and with õ ä ö ü intact.

    Written here rather than taken from Whisper's own normaliser: that one was
    built alongside the model (so it flatters it) and strips Unicode marks,
    which in Estonian deletes the vowels that carry meaning.
    """
    cleaned = "".join(
        " " if unicodedata.category(ch).startswith("P") else ch
        for ch in unicodedata.normalize("NFC", text).casefold())
    return cleaned.split()


def alignment(said: str, heard: str) -> list[tuple[int | None, int | None]]:
    """Minimum-edit word alignment; indices keep repeated words distinct."""
    a, b = _norm(said), _norm(heard)
    grid = [[j if i == 0 else i if j == 0 else 0 for j in range(len(b) + 1)]
            for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            grid[i][j] = min(grid[i - 1][j - 1] + (a[i - 1] != b[j - 1]),
                             grid[i - 1][j] + 1, grid[i][j - 1] + 1)
    pairs = []
    i, j = len(a), len(b)
    while i or j:
        if i and j and grid[i][j] == grid[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i and grid[i][j] == grid[i - 1][j] + 1:
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    return list(reversed(pairs))


def errors(said: str, heard: str) -> dict:
    a, b = _norm(said), _norm(heard)
    counts = {"sub": 0, "del": 0, "ins": 0, "words": len(a)}
    for i, j in alignment(said, heard):
        if i is None:
            counts["ins"] += 1
        elif j is None:
            counts["del"] += 1
        elif a[i] != b[j]:
            counts["sub"] += 1
    return counts


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


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_clip(audio: Path, *, planted_index: int | None = None,
                accepted: str = "", focus: tuple[int, ...] = (),
                tags: tuple[str, ...] = (), question: str = "") -> dict:
    """Seal a transcript *after a human listened*. Changes invalidate the seal.

    `accepted` is the target form that would hide the planted error, not an
    automatically generated correction. `focus` names morphology-sensitive
    reference token indices; tags name slices such as numbers/names/hesitation.
    """
    saved_question = audio.with_suffix(".question")
    if saved_question.exists():
        recorded = saved_question.read_text(encoding="utf-8").strip()
        if question and question != recorded:
            raise ValueError("question differs from the recorded task")
        question = recorded
    if len(question) > 220:
        raise ValueError("question must fit the production 220-character context limit")
    transcript = audio.with_suffix(".txt")
    words = _norm(transcript.read_text(encoding="utf-8"))
    if not words:
        raise ValueError("a verified transcript cannot be empty")
    if any(i < 0 or i >= len(words) for i in focus):
        raise ValueError("focus indices must refer to transcript tokens")
    if planted_index is not None:
        if not 0 <= planted_index < len(words):
            raise ValueError("planted index must refer to a transcript token")
        if len(_norm(accepted)) != 1 or _norm(accepted)[0] == words[planted_index]:
            raise ValueError("accepted must be one different target word")
    elif accepted:
        raise ValueError("accepted needs a planted index")
    seal = {"v": 1, "audio_sha256": _digest(audio),
            "transcript_sha256": _digest(transcript),
            "planted_index": planted_index, "accepted": accepted,
            "focus": sorted(set(focus)), "tags": sorted(set(tags)), "question": question}
    audio.with_suffix(".verified.json").write_text(
        json.dumps(seal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return seal


@dataclass(frozen=True)
class Clip:
    audio: Path
    said: str
    annotation: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.audio.name

    @property
    def identity(self) -> str:
        # Pair only identical audio AND reviewed ground truth/annotations.
        body = json.dumps(self.annotation, sort_keys=True).encode()
        return hashlib.sha256(body).hexdigest()


def inventory(folder: Path | str | None = None) -> tuple[list[Clip], list[dict]]:
    root = Path(folder or SET)
    out, excluded = [], []
    for audio in sorted(p for p in root.glob("*")
                        if p.suffix.lower() in (".wav", ".webm", ".ogg", ".mp4", ".m4a")):
        try:
            transcript = audio.with_suffix(".txt")
            seal = json.loads(audio.with_suffix(".verified.json").read_text(encoding="utf-8"))
            if (seal.get("v") != 1 or seal.get("audio_sha256") != _digest(audio)
                    or seal.get("transcript_sha256") != _digest(transcript)):
                raise ValueError("recording or transcript changed; listen and verify again")
            said = transcript.read_text(encoding="utf-8").strip()
            words = _norm(said)
            focus = seal.get("focus", [])
            planted = seal.get("planted_index")
            question = seal.get("question", "")
            if (not isinstance(question, str) or len(question) > 220):
                raise ValueError("invalid question context")
            if (not words or not isinstance(focus, list)
                    or any(type(i) is not int or not 0 <= i < len(words) for i in focus)
                    or (planted is not None and (type(planted) is not int
                        or not 0 <= planted < len(words)
                        or len(_norm(seal.get("accepted", ""))) != 1
                        or _norm(seal["accepted"])[0] == words[planted]))):
                raise ValueError("invalid reviewed annotation")
            out.append(Clip(audio, said, seal))
        except (OSError, ValueError, TypeError, AttributeError):
            excluded.append({"clip": audio.name, "reason": "missing, stale or invalid human verification"})
    return out, excluded


def clips(folder: Path | str | None = None) -> list[Clip]:
    """Only unchanged, manually verified recordings; prompts are not truth."""
    return inventory(folder)[0]


def run(engine: str = "workers-ai", folder: Path | str | None = None,
        verbose: bool = True) -> dict:
    """Score one recogniser. Never substitute a fallback in a comparison."""
    from ..providers import asr

    recordings, excluded = inventory(folder)
    split = {"sub": 0, "del": 0, "ins": 0, "words": 0}
    chars = char_errors = planted = accepted = focus_n = focus_errors = 0
    latencies, per_clip, details = [], [], []
    broken = 0
    for clip in recordings:
        mime = {".wav": "audio/wav", ".webm": "audio/webm", ".ogg": "audio/ogg",
                ".mp4": "audio/mp4", ".m4a": "audio/mp4"}[clip.audio.suffix.lower()]
        started = time.monotonic()
        row = {"clip": clip.name, "identity": clip.identity, "tags": clip.annotation.get("tags", [])}
        options = {"context": clip.annotation["question"]} if clip.annotation.get("question") else {}
        row["question_context"] = bool(options)
        try:
            if engine == "chain":
                got = asr.transcribe(clip.audio.read_bytes(), mime, **options)
            else:
                got = asr.transcribe_with(engine, clip.audio.read_bytes(), mime, **options)
            row["seconds"] = round(time.monotonic() - started, 3)
            row["actual_engine"] = got.engine if got else None
            if got is None or not got.text or got.degraded:
                raise RuntimeError("unavailable or empty transcript")
        except Exception as exc:  # noqa: BLE001 - failed reference is reported, not scored
            broken += 1
            row.update(failure=type(exc).__name__, seconds=round(time.monotonic() - started, 3))
            details.append(row)
            continue
        latencies.append(row["seconds"])
        a, b = _norm(clip.said), _norm(got.text)
        edits = errors(clip.said, got.text)
        for key, value in edits.items():
            split[key] += value
        reference = " ".join(a)
        chars += len(reference)
        char_errors += distance(list(reference), list(" ".join(b)))
        aligned = {i: j for i, j in alignment(clip.said, got.text) if i is not None}
        focus = clip.annotation.get("focus", [])
        misses = sum(aligned[i] is None or a[i] != b[aligned[i]] for i in focus)
        focus_n += len(focus)
        focus_errors += misses
        false_accept = None
        index = clip.annotation.get("planted_index")
        if index is not None:
            planted += 1
            j = aligned[index]
            # A deletion or unrelated substitution is an ASR error, not proof
            # that the recogniser supplied the expected grammatical form.
            false_accept = j is not None and b[j] == _norm(clip.annotation["accepted"])[0]
            accepted += false_accept
        rate = wer(clip.said, got.text)
        per_clip.append((clip.identity, rate))
        row.update(wer=rate, cer=cer(clip.said, got.text), transcript=got.text,
                   errors=edits, false_accept=false_accept,
                   morphology_tokens=len(focus), morphology_errors=misses)
        details.append(row)
    measured = len(per_clip)
    valid = measured >= ENOUGH and measured == len(recordings) and engine != "chain"
    score = {
        "engine": engine, "clips": len(recordings), "excluded": excluded,
        "measured": measured, "broken": broken,
        "wer": round(sum(split[k] for k in ("sub", "del", "ins")) / split["words"], 4)
               if split["words"] else None,
        "cer": round(char_errors / chars, 4) if chars else None,
        "planted_errors": planted, "false_accept_count": accepted,
        "false_accept": accepted / planted if planted else None,
        "morphology_tokens": focus_n, "morphology_errors": focus_errors,
        "morphology_error_rate": focus_errors / focus_n if focus_n else None,
        "latency_p50": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "latency_max": max(latencies) if latencies else None,
        "latency_p95": sorted(latencies)[min(len(latencies)-1, int(len(latencies)*.95))]
                       if latencies else None,
        "errors": split, "per_clip": per_clip, "details": details, "valid": valid,
        "decision_ready": valid and planted >= 5 and focus_n >= 5,
        "note": "Corpus-weighted WER/CER; own voice and microphone only. "
                "20 complete clips is a pilot floor, not a statistical power guarantee. "
                "Latency includes local process/model startup; failures have separate timings.",
    }
    if not valid:
        score["invalid_reason"] = (
            f"{measured}/{len(recordings)} verified clips measured; need at least {ENOUGH}, "
            "complete coverage and one named engine. Record a few clips, listen, correct "
            "their transcripts and run asr-verify before trusting any number.")
    if verbose:
        print(json.dumps(score, indent=2, ensure_ascii=False))
    return score


# --------------------------------------------------------------------------
# Comparing two engines
# --------------------------------------------------------------------------

def compare(a: dict, b: dict, rounds: int = 2000, seed: int = 0) -> dict:
    """Is engine `b` really better than `a` on this set, or is it the clips?

    Paired on the same recordings, and resampled by clip (bootstrap): word
    errors inside one utterance are not independent, so a plain word-count test
    would report an interval far tighter than the evidence supports.
    """
    import random

    left = dict(a.get("per_clip") or [])
    right = dict(b.get("per_clip") or [])
    shared = sorted(set(left) & set(right))
    if not shared:
        return {"clips": 0, "difference": None,
                "note": "the two runs share no clips — nothing to compare"}

    deltas = [left[name] - right[name] for name in shared]
    observed = sum(deltas) / len(deltas)
    rng = random.Random(seed)
    means = []
    for _ in range(rounds):
        sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        means.append(sum(sample) / len(sample))
    means.sort()
    low = means[int(0.025 * rounds)]
    high = means[int(0.975 * rounds) - 1]
    return {
        "clips": len(shared),
        "a": a.get("engine"), "b": b.get("engine"),
        # Positive: `b` makes fewer errors than `a`.
        "difference": round(observed, 3),
        "ci95": [round(low, 3), round(high, 3)],
        "decisive": bool(a.get("decision_ready") and b.get("decision_ready")
                         and len(shared) == a.get("clips") == b.get("clips")
                         and (low > 0 or high < 0)),
        "note": ("Difference in mean per-clip WER (not corpus WER), paired by audio and "
                 "annotation hashes and resampled by clip. One voice and "
                 "one microphone: this says which engine hears *this* learner "
                 "better, not which is better at Estonian."),
    }
