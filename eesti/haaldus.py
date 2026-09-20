"""EKI's spoken word forms: a human voice for the forms the drills teach.

*Eesti keele põhisõnavara sõnastik 2014* ships recordings of about 6 000 base
words read by Eva Klemets and Marju Avamere, with an index that names the form
each clip holds. Two packs, two shapes:

    soundpack.txt      psv_00001.wav   SgN   aabits          (form tag, then the form)
    soundpack_alg.txt  psvalg_1000.mp3 `aasta aasta          (the form, then its lemma)

The tags are the forms this app already drills — `SgN`, `SgG`, `SgP` are
nimetav, omastav and osastav — so a drill can play a real speaker instead of
synthesis. The forms carry EKI's morphophonological marks (`` ` `` third
quantity, `'` palatalisation, `+` compound boundary, `[` and `/` form
separators); those distinctions are **not** in the spelling, which is why
synthesis gets them wrong and why the marks are kept in `spoken` while the
lookup key is the plain form.

Audio lands in `data/audio.db` as blobs, so one file carries it the way
`content.db` carries the corpus. Import keeps only what the app teaches, or the
whole 960 MB pack lands on a phone.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

#: EKI's form tags, mapped to the tags this app uses (`morph.case_forms`).
TAGS = {
    "SgN": "sg n", "SgG": "sg g", "SgP": "sg p",
    "PlN": "pl n", "PlG": "pl g", "PlP": "pl p",
    "IndPrSg3": "b", "Sup": "ma", "Inf": "da",
}

#: The marks EKI writes into a form. They carry real distinctions (third
#: quantity, palatalisation) that the spelling does not, so they are kept
#: alongside the plain form rather than thrown away.
MARKS = re.compile(r"[`'+\[/]")

SCHEMA = """
CREATE TABLE IF NOT EXISTS pronunciation (
    form   TEXT NOT NULL,      -- the plain form, as the app spells it
    tag    TEXT NOT NULL,      -- this app's form tag, or '' when unknown
    spoken TEXT NOT NULL,      -- EKI's own form, marks included
    lemma  TEXT NOT NULL DEFAULT '',
    mime   TEXT NOT NULL,
    audio  BLOB NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (form, tag)
);
CREATE INDEX IF NOT EXISTS idx_pron_form ON pronunciation(form);

CREATE TABLE IF NOT EXISTS sentence_audio (
    text   TEXT PRIMARY KEY,   -- the sentence, exactly as it is spoken
    words  INTEGER NOT NULL,
    mime   TEXT NOT NULL,
    audio  BLOB NOT NULL,
    source TEXT NOT NULL
);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    from . import config

    target = Path(path or config.AUDIO_DB)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def plain(form: str) -> str:
    """The form as the app spells it: EKI's marks removed, case kept.

    Case matters — `lõvi` is the animal and `Lõvi` the constellation — so it is
    left alone; the lookup lowercases at the edge instead.
    """
    return MARKS.sub("", form).strip()


@dataclass(frozen=True)
class Entry:
    audio: str          # the file name inside the pack
    spoken: str         # EKI's form, marks included
    tag: str            # this app's tag, or "" when the pack gives a lemma instead
    lemma: str

    @property
    def form(self) -> str:
        return plain(self.spoken)


def index(path: Path | str) -> list[Entry]:
    """Read either pack's index. The shape is told apart by the middle column."""
    out: list[Entry] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3 or not parts[0]:
            continue
        audio, middle, last = parts[0], parts[1].strip(), parts[2].strip()
        if middle in TAGS:
            # `psv_00001.wav  SgN  aabits`: the tag, then the form.
            out.append(Entry(audio, last, TAGS[middle], ""))
        else:
            # `psvalg_1000.mp3  `aasta  aasta`: the form, then its lemma.
            out.append(Entry(audio, middle, "", last))
    return out


def _mime(name: str) -> str:
    return "audio/mpeg" if name.lower().endswith(".mp3") else "audio/wav"


#: What a word is stored at. 48 kHz studio WAV is 150 KB for one word; speech
#: lives below 8 kHz, so 16 kHz keeps every consonant that distinguishes a form
#: and costs a third. No transcoder is assumed — this is plain `wave`.
RATE = 16_000

#: Below this share of the loudest sample, a frame is silence worth trimming.
#: EKI's clips are studio recordings with a second of room tone at each end.
QUIET = 0.02


def compress(data: bytes, rate: int = RATE) -> bytes:
    """Downsample a mono 16-bit WAV and trim the silence around the word."""
    import array
    import io
    import wave

    try:
        with wave.open(io.BytesIO(data)) as clip:
            if clip.getnchannels() != 1 or clip.getsampwidth() != 2:
                return data
            source = clip.getframerate()
            samples = array.array("h", clip.readframes(clip.getnframes()))
    except (wave.Error, EOFError, ValueError):
        return data
    if source <= rate or not samples:
        return data

    step = source / rate
    kept = array.array("h")
    position = 0.0
    while position < len(samples):
        # Mean over the window this sample stands for: plain decimation would
        # alias the fricatives, which are exactly what tells the forms apart.
        start, end = int(position), min(int(position + step), len(samples))
        window = samples[start:end] or samples[start:start + 1]
        kept.append(int(sum(window) / len(window)))
        position += step

    loudest = max((abs(v) for v in kept), default=0)
    if loudest:
        floor = loudest * QUIET
        first = next((i for i, v in enumerate(kept) if abs(v) > floor), 0)
        last = len(kept) - next((i for i, v in enumerate(reversed(kept))
                                 if abs(v) > floor), 0)
        pad = rate // 20                      # 50 ms, so nothing is clipped off
        kept = kept[max(0, first - pad):min(len(kept), last + pad)]

    out = io.BytesIO()
    with wave.open(out, "wb") as written:
        written.setnchannels(1)
        written.setsampwidth(2)
        written.setframerate(rate)
        written.writeframes(kept.tobytes())
    return out.getvalue()


def build(audio_dir: Path | str, index_path: Path | str,
          conn: sqlite3.Connection, *, keep: set[str] | None = None,
          source: str = "psv-haaldused") -> dict:
    """Import a pack. `keep` limits it to words the app teaches (lowercased)."""
    folder = Path(audio_dir)
    added = skipped = missing = 0
    for entry in index(index_path):
        if keep is not None and entry.form.casefold() not in keep:
            skipped += 1
            continue
        clip = folder / entry.audio
        if not clip.exists():
            missing += 1
            continue
        audio = clip.read_bytes()
        if _mime(entry.audio) == "audio/wav":
            audio = compress(audio)
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO pronunciation"
                " (form, tag, spoken, lemma, mime, audio, source)"
                " VALUES (?,?,?,?,?,?,?)",
                (entry.form, entry.tag, entry.spoken, entry.lemma,
                 _mime(entry.audio), audio, source))
        added += 1
    return {"added": added, "skipped": skipped, "missing": missing,
            "forms": conn.execute(
                "SELECT COUNT(*) FROM pronunciation").fetchone()[0]}


def taught(words: sqlite3.Connection,
           levels: tuple[str, ...] = ("A1", "A2", "B1")) -> set[str]:
    """Every form the app might ask for: the levels' words and their case forms.

    Synthesising the forms here rather than importing everything is what keeps
    `audio.db` to the size of a phone download.
    """
    from .morph import case_forms
    from .wordlist import declines

    keep: set[str] = set()
    marks = ",".join("?" * len(levels))
    rows = words.execute(
        f"SELECT word, pos FROM words WHERE proficiency IN ({marks})",  # noqa: S608
        levels).fetchall()
    for row in rows:
        word = row["word"]
        keep.add(word.casefold())
        if not declines(row["pos"]):
            continue
        try:
            keep.update(form.casefold() for form in case_forms(word).values())
        except Exception:  # noqa: BLE001 - a word Vabamorf refuses is simply not added
            continue
    return keep


def spoken(conn: sqlite3.Connection, form: str,
           tag: str | None = None) -> sqlite3.Row | None:
    """The clip for a form, preferring the asked-for tag."""
    rows = conn.execute(
        "SELECT * FROM pronunciation WHERE form = ? COLLATE NOCASE", (form,)
    ).fetchall()
    if not rows:
        return None
    if tag:
        for row in rows:
            if row["tag"] == tag:
                return row
    return rows[0]


def counts(conn: sqlite3.Connection) -> dict:
    return {
        "forms": conn.execute("SELECT COUNT(*) FROM pronunciation").fetchone()[0],
        "bytes": conn.execute(
            "SELECT COALESCE(SUM(LENGTH(audio)), 0) FROM pronunciation").fetchone()[0],
    }


# --------------------------------------------------------------------------
# Whole sentences: EKI's speech corpora (Kersti, Külli, Lee, Liivika, Meelis)
# --------------------------------------------------------------------------
#
# Each sentence is a `lauseNNNNN.wav` beside a `.txt` holding exactly what was
# read. Dictation has been synthesised until now; a real reader is the thing the
# exam plays, and the difference is audible at the end of a word.

def sentences(folder: Path | str) -> list[tuple[str, Path]]:
    """`(text, audio)` for every sentence in a corpus folder."""
    root = Path(folder)
    out = []
    for audio in sorted(root.glob("*.wav")):
        said = audio.with_suffix(".txt")
        if not said.exists():
            continue
        text = said.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            out.append((text, audio))
    return out


def build_sentences(folder: Path | str, conn: sqlite3.Connection, *,
                    max_words: int = 12, limit: int | None = None,
                    source: str = "eki-konekorpus") -> dict:
    """Import the sentences short enough to dictate.

    `max_words` keeps this to what a learner can hold in their head — the same
    bound `dictation.py` uses — and keeps the file to a size a phone can carry.
    """
    added = skipped = 0
    for text, audio in sentences(folder):
        if len(text.split()) > max_words:
            skipped += 1
            continue
        if limit is not None and added >= limit:
            break
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO sentence_audio"
                " (text, words, mime, audio, source) VALUES (?,?,?,?,?)",
                (text, len(text.split()), "audio/wav",
                 compress(audio.read_bytes()), source))
        added += 1
    return {"added": added, "skipped": skipped,
            "sentences": conn.execute(
                "SELECT COUNT(*) FROM sentence_audio").fetchone()[0]}


def said(conn: sqlite3.Connection, text: str) -> sqlite3.Row | None:
    """A human recording of exactly this sentence, or None."""
    return conn.execute(
        "SELECT * FROM sentence_audio WHERE text = ?", (text.strip(),)).fetchone()


def spoken_sentences(conn: sqlite3.Connection, max_words: int = 12,
                     limit: int = 200) -> list[str]:
    """Sentences there is a recording for, shortest first."""
    return [r[0] for r in conn.execute(
        "SELECT text FROM sentence_audio WHERE words <= ? ORDER BY words LIMIT ?",
        (max_words, limit))]
