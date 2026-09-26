"""A ready-made speech benchmark, so recognisers can be compared before any
learner recording exists.

Two kinds of clip, each with its truth known by construction rather than by
someone listening:

| Clip | Truth | Answers |
|---|---|---|
| EKI *kõnekorpus* sentence, read by a native speaker | EKI's own text of what was read | WER on clear native speech |
| TartuNLP synthesis of a sentence with a planted learner error (`Ma nägin suur koer`) | the text sent to the synthesiser | **false accept**: does the recogniser hand back the right form the speaker did not say? |

Neither is a learner's voice, and the synthetic sentences are a synthesiser's
accent, not a Russian speaker's. The set ranks engines on the two failures that
matter here (mishearing and silently correcting); the owner's own verified
clips in `data/eval/asr/` remain the only measure of *this* learner.

Built into `data/eval/asr-bench/` (git-ignored, beside the owner's set, never
mixed with it) by `cli asr-bench`; scored by
`cli eval --suite asr --folder data/eval/asr-bench --engine A --engine B`.
The seal carries `provenance` instead of a listening confirmation.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from ..config import DATA

FOLDER = DATA / "eval" / "asr-bench"

#: Sentences an A2 learner says, with one planted error each: (sentence,
#: index of the wrong word, the form that would hide it). Controls have no
#: error. Written for this test; the wrong forms are the error classes the
#: exam marks (object case, agreement, adjective agreement, partitive after a
#: numeral).
PLANTED = (
    ("Ma nägin suur koera pargis.", 2, "suurt"),
    ("Mina läheb homme tööle.", 1, "lähen"),
    ("Ta ostis kolm raamat.", 3, "raamatut"),
    ("Me elame väike korteris.", 2, "väikeses"),
    ("Ma söön iga päev puder.", 4, "putru"),
    ("Nad tuli eile koju.", 1, "tulid"),
    ("Ma ootan sinu vastus.", 3, "vastust"),
    ("Ma ostsin uus auto.", 2, "uue"),
    ("Tema elavad Tartus.", 1, "elab"),
    ("Ma lugesin raamat terve õhtu.", 2, "raamatut"),
    ("Mul on kaks vend.", 3, "venda"),
    ("Sina oskab hästi ujuda.", 1, "oskad"),
)
CONTROLS = (
    "Ma ei tea, kus ta elab.",
    "Minu vend töötab haiglas.",
    "Kas sa tahad minuga kino minna?",
    "Eile käisin poes ja ostsin leiba.",
)

#: Two voices, so one synthesiser's habits do not decide the ranking.
VOICES = ("mari", "albert")


def _seal(folder: Path, name: str, audio: bytes, text: str, provenance: str,
          tags: list[str], planted_index: int | None = None, accepted: str = "") -> None:
    wav = folder / f"{name}.wav"
    txt = folder / f"{name}.txt"
    wav.write_bytes(audio)
    txt.write_text(text + "\n", encoding="utf-8")
    seal = {"v": 1, "audio_sha256": hashlib.sha256(audio).hexdigest(),
            "transcript_sha256": hashlib.sha256(txt.read_bytes()).hexdigest(),
            "planted_index": planted_index, "accepted": accepted, "focus": [],
            "tags": sorted(tags), "question": "", "provenance": provenance}
    (folder / f"{name}.verified.json").write_text(
        json.dumps(seal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(folder: Path | str | None = None, native: int = 20, seed: int = 0) -> dict:
    """Write the set; idempotent for the same `seed`. Needs EKI's sentence
    recordings (`cli import-konekorpus`) for the native half and the TartuNLP
    speech API for the synthetic half.
    """
    from .. import haaldus
    from ..providers import tts

    root = Path(folder or FOLDER)
    root.mkdir(parents=True, exist_ok=True)
    counts = {"native": 0, "planted": 0, "controls": 0}

    conn = haaldus.connect()
    rows = conn.execute(
        "SELECT text, audio FROM sentence_audio WHERE words BETWEEN 4 AND 12 "
        "ORDER BY text").fetchall()
    for i, (text, audio) in enumerate(random.Random(seed).sample(rows, min(native, len(rows)))):
        _seal(root, f"native-{i:02d}", audio, text, "eki-konekorpus", ["native"])
        counts["native"] += 1

    for i, (text, index, accepted) in enumerate(PLANTED):
        audio = tts.synthesize(text, speaker=VOICES[i % len(VOICES)], speed=0.9).read_bytes()
        _seal(root, f"planted-{i:02d}", audio, text, "tartunlp-tts", ["synthetic", "planted"],
              planted_index=index, accepted=accepted)
        counts["planted"] += 1
    for i, text in enumerate(CONTROLS):
        audio = tts.synthesize(text, speaker=VOICES[i % len(VOICES)], speed=0.9).read_bytes()
        _seal(root, f"control-{i:02d}", audio, text, "tartunlp-tts", ["synthetic", "control"])
        counts["controls"] += 1
    return {"folder": str(root), **counts}
