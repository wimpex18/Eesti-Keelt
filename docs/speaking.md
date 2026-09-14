# Speaking

The B1 speaking exam is **paired**: candidates answer in turn, then negotiate
with each other, and a role-play follows. A solo app cannot grade interaction,
so `Rääkimine` does what a phone can do honestly.

## What the tab does

| Mode | Input | Check | Model? |
|---|---|---|---|
| Question bank (`speaking.py`) | exam-shaped questions voiced by TTS | none — practice | TTS only |
| **Loe ette** (read aloud, `pronunciation.py`) | a known sentence | word-by-word `difflib` against what the recogniser heard | ASR only |
| **Vasta küsimusele** (open answer) | free speech | transcript through the grammar chain, word count and pace | ASR + LLM, advisory |

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
