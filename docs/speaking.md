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

## Where the voice goes

In production the recording is sent to Cloudflare Workers AI (Whisper, language
`et`) through the Worker, used for one request and not stored anywhere. The
learner is told this in the panel before recording. Running `cli serve` with
local whisper.cpp keeps the voice on the machine.

## Not built

Acoustic pronunciation scoring: forced alignment gives timings, not
correctness, and EKI already publishes free exercises.

## Running ASR locally

`providers/asr.py` looks for whisper.cpp with TalTech's Estonian verbatim model,
then Voxtral, after the hosted engines. `/api/asr` reports which engines this
process can use.


## Before swapping a recogniser

`cli eval --suite asr` scores the engines on **the owner's own voice**
(ADR-0003, `docs/adr/0003-speech-eval-data.md`). The set is recorded in the app:
`Rääkimine → Hindamiskomplekt` shows a sentence, records it, and writes
`data/eval/asr/<n>.webm` beside `<n>.txt` (what was read) and, for a planted
prompt, `<n>.said` (the word deliberately said wrong). That block exists only
under `cli serve`: the routes are absent where `PROXY_TOKEN` is set, so nothing
is recorded on the deployment. Recordings are personal data and stay out of git.

Aim for 80–150 sentences, a quarter of them planted — the size at which a
10 % versus 20 % difference is distinguishable (Liu et al., Interspeech 2023),
given that words inside one utterance are not independent.

It reports WER with its substitution/deletion/insertion split (insertions are
the recogniser inventing words in a pause), CER, latency, and the measure that
decides this choice: the **false-accept rate** — how often a planted mistake
comes back corrected. A generic Whisper tends to tidy learner Estonian into
fluent Estonian, which hides the mistake and flatters a read-aloud score.
TalTech's verbatim model exists for exactly this, and is the candidate to beat.

`evals.asr.compare(a, b)` puts two runs side by side on the same clips and
resamples by clip, because word errors inside one utterance are correlated; it
reports the difference with a 95 % interval and whether it is decisive.

No number here is a gate: one voice and one microphone describe this learner.


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
