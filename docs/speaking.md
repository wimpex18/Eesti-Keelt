# Speaking

The B1 speaking exam is **paired**: candidates answer in turn, then negotiate
with each other, and a role-play follows. A solo app cannot grade interaction,
so `Rääkimine` does what a phone can do honestly.

## What the tab does

| Mode | Input | Check | Model? |
|---|---|---|---|
| Question bank (`speaking.py`) | exam-shaped questions voiced by TTS | none — practice | TTS only |
| **Loe ette** (read aloud, `pronunciation.py`) | a known sentence | word-by-word `difflib` against what the recogniser heard | ASR only |
| **Vasta küsimusele** (open answer) | free speech | transcript through the grammar chain, word count, pace, and how sure the transcript looks (`learner.speech_signals`) | ASR + LLM, advisory |
| **Vestlus** (conversation) | short push-to-talk turns or typed answers | tentative ASR text is editable before sending; model reply appears as text and TartuNLP TTS audio | ASR + tutor LLM + TTS, no score |

- Read-aloud sentences are corpus sentences of 3–8 words in which every word,
  names and numbers included, is known or at A1–A2 on the word list; when too
  few qualify the rest are the most within reach, shorter first
  (`pronunciation.sentences_to_say`, policy in `docs/curriculum.md`).
- Read-aloud reports which words were missed, never a percentage, and always
  carries the caveat (in Russian) that a miss may be the recogniser, not the
  learner.
- Open-answer feedback is advisory and never recorded (`docs/ai-boundaries.md`).
- The panel links to EKI's pronunciation exercises and the Sõnaveeb A1–B1
  phrase collections instead of scoring acoustics.
- With no ASR configured the tab still records and plays back.
- `Vestlus` keeps the learner in the page: speak a turn, inspect or edit the
  recognised text, send it, and hear or read the model partner's reply. It is
  turn-based, so it can reuse the production Cloudflare ASR and the current
  TTS service without a separate live audio connection. A TTS failure leaves
  the text reply usable.

## Where the voice goes

In production the recording goes to Cloudflare Workers AI (Whisper, language
`et`) through the Worker. The app does not archive that audio; the evidence log
**does retain transcripts and practice signals**, and exports contain them.
Provider handling follows [Cloudflare's data policy](https://developers.cloudflare.com/workers-ai/platform/data-usage/).
Local-only recognition keeps audio on the machine only when hosted lanes are
not configured. Eval recording intentionally saves audio locally. These are
three different privacy boundaries.

## Not built

Acoustic pronunciation scoring: forced alignment gives timings, not
correctness, and EKI already publishes free exercises.

## Running ASR locally

`providers/asr.py` looks for whisper.cpp with TalTech's Estonian verbatim model,
then Voxtral, after the hosted engines. `/api/asr` reports which engines this
process can use.


## Before swapping a recogniser

The production choice is Cloudflare plus a **local TalTech benchmark reference**,
not an additional production service. `docs/asr-evaluation.md` contains the
current model comparison and the complete recording/verification workflow.

`Hindamiskomplekt` under local `cli serve` records an answer in the app, either
from a dedicated read/question prompt or from an ordinary speaking exercise.
The proposed ASR transcript is editable in the same panel. Listen, correct it,
and confirm what was actually said; the prompt is never the transcript. The
private clip, draft and verified transcript stay under `data/eval/asr/` (or
`EESTI_ASR_EVAL_DIR`). `cli eval --suite asr` defaults to the production
recogniser. Only verified pairs are scored. The
harness reports WER, CER, latency, aligned false acceptance, morphology-sensitive
errors and per-clip coverage, with a paired comparison of named engines.
`faster-whisper` is an eval-only optional CPU backend for TalTech's official CT2
weights. The existing whisper.cpp reference needs WAV input. No learner clips
are present here, so comparative quality remains unmeasured.

## A human voice where EKI recorded one

Estonian quantity (`koera` against `k`oera`) is not written, so a synthesiser
guesses it. EKI's archive has both: about 6 000 word forms read by two speakers
(`cli import-haaldused`) and sentences read aloud (`cli import-konekorpus`),
imported into `data/audio.db` — downsampled to 16 kHz, and for word forms
limited to what the app teaches.

- `/api/pronounce?form=koera&tag=sg%20p` serves the recording and returns EKI's
  own marked form in `x-spoken-form`; a form nobody read is a 404 and the page
  falls back to synthesis.
- `/api/speak` plays the reader when the sentence is one of theirs.
- Dictation prefers sentences a person read.

On the deployment the same file is mounted from Cloud Storage
(`deploy/push-audio.sh`, `docs/deploy.md`), so the phone gets the human voice
too; the Worker caches each clip at the edge after the first play.

The archive is `arhiiv.eki.ee/litsents` (CC BY 4.0). The audio is not served to
anyone else — Access guards the app, and the novels behind the speech corpora
are still in copyright.
