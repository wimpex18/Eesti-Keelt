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

## How the recogniser hears the learner

`Kuidas mind kuuldakse` works on the deployment and keeps no audio
(`eesti/asrcheck.py`). After each read-aloud sentence the learner taps
**Lugesin nii, nagu kirjas** or **Ütlesin teisiti**. Only sentences read as
written are scored, so their misses are the recogniser's. Every fourth sentence
carries one planted object-case error, the distractor an `obj-case` drill
offers; the report counts how often the recogniser handed it back and how often
it repaired it. Rates appear only after 20 sentences and 5 probes. The
learner's immediate word is a lighter tier than a clip listened to and
corrected in `Hindamiskomplekt`, and the two are reported separately
(ADR-0003).

In a drill, the microphone beside the answer box fills it with what was heard.
The recogniser gets no hint, and code grades what is in the box once the
learner presses Kontrolli.

## Where the voice goes

The deployed Worker sends the recording first to the owner's Mac mini (the home
service, `eesti/asrserver.py`: TalTech's Estonian recogniser, reached through a
Workers VPC Service on a Cloudflare Tunnel; the Mac is not on the public
Internet), and to Cloudflare Workers AI Whisper (language `et`) when the Mac
does not answer within 25 s. The speaking page says which one is listening
(`/api/asr/home`). Neither keeps the audio; the evidence log **does retain
transcripts and practice signals**, and exports contain them. Workers AI
follows [Cloudflare's data policy](https://developers.cloudflare.com/workers-ai/platform/data-usage/).
Under local `cli serve`, `providers/asr.py` asks Voxtral Realtime first when
`requirements-local-asr.txt` is installed and `VOXTRAL_RT_MODEL` is set, then
the hosted engines, then whisper.cpp and Voxtral via llama.cpp; `/api/asr`
reports which it can use. Eval recording intentionally saves audio locally.

Engine measurements and the recording/verification workflow are in
`docs/asr-evaluation.md`; setting up the home service is
`deploy/home-asr/README.md`.

## Not built

Acoustic pronunciation scoring: forced alignment gives timings, not
correctness, and EKI already publishes free exercises.

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
