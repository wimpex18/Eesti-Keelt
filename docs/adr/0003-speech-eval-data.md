# ADR-0003: What the speech eval is measured on

**Status:** Accepted
**Date:** 2026-09-20
**Deciders:** the owner (sole learner and maintainer)
**Follows:** P5 — no recogniser is swapped without an eval first.

## Context

The choice is between Cloudflare Workers AI (`whisper-large-v3-turbo`, running
today) and TalTech's `whisper-large-v3-turbo-et-verbatim-2604` (MIT, no WER
published). The learner is a Russian speaker at A2 reading Estonian aloud on one
microphone.

What decides it is not general Estonian accuracy. A generic Whisper **tidies**
learner Estonian into fluent Estonian: say *uus auto* where *uue auto* belongs
and it hands back the correct form. The mistake disappears, and the read-aloud
comparison calls it right. A verbatim model is trained not to do that. So the
measure that matters is the **false-accept rate on planted mistakes**, and it
can only be measured on speech that *contains* learner mistakes.

What exists (checked 2026-09-20):

| Source | What it is | Licence / access | Fit |
|---|---|---|---|
| **EKI Kõnekorpused** (Kersti, Külli, Lee, Liivika, Meelis) | native readers, novels, 1 000+ sentences each, 0.4–0.7 GB per archive | CC BY 4.0, but the download runs through `dl.cgi` behind **Estonian ID-card login** | native studio speech — measures a different thing |
| **EKI põhisõnavara hääldused** | ~6 000 isolated word forms read by two native speakers, 960 MB, index `soundpack.txt` (12 354 lines) | same | word-level, no sentences: no WER, no learner errors |
| **FLEURS `et_ee`** | 893 test utterances, native, clean | CC BY 4.0 | a regression baseline at best; the rows API cannot serve it in pieces (row-group limit), so it is an all-or-nothing download |
| **Common Voice Estonian** | 66 h, 1 067 speakers | CC0 | native/varied, gated behind a Hugging Face agreement |
| **TalTech Estonian Speech Dataset** | 1 334 h train, 23 h test | CC BY-SA 4.0 | **the candidate's own training data** — it cannot judge the candidate |
| **EFAC** (Estonian Foreign Accent Corpus) | ~80 h, 185 L2 speakers, 50 of them Russian-L1 | CLARIN ACA, academic, **interface only, not downloadable** | the only real L2 Estonian speech, and unusable here |

There is no publicly downloadable, transcribed corpus of learner Estonian.

Sizing, from the ASR literature: WER is a binomial over word tokens with
correlation inside an utterance, so a 10 % vs 20 % difference needs roughly
600–1 000 word tokens — **about 80–150 read utterances** — and a *paired*
comparison on identical audio is far stronger than two independent samples
(Liu et al., Interspeech 2023). Matched conditions (this voice, this
microphone, this room) predict production accuracy better than a larger set of
someone else's speech.

## Decision

**The deciding set is the owner's own voice, recorded in the app**, and the app
gains the flow that produces it.

1. `Rääkimine` gets a recording mode: the app shows a sentence, the learner
   reads it, and the clip is saved with its text. Some prompts ask for a
   deliberately wrong form (`planted`), which is what makes the false-accept
   rate measurable.
2. Clips are written by a **local-only** route: it refuses when `PROXY_TOKEN`
   is set, so it exists under `cli serve` and not on the deployment. The audio
   never leaves the machine and never enters git (`data/` is ignored).
3. `cli eval --suite asr` scores engines **paired** on the same clips, reports
   WER with its substitution/deletion/insertion split, CER, the false-accept
   rate, and a bootstrap interval for the difference between two engines.
4. **No public corpus is downloaded.** EKI's archives are excellent and
   irrelevant to this question; TalTech's test set is disqualified by
   contamination; FLEURS and Common Voice would cost a gigabyte to measure
   native speech this app never hears.

## Options considered

### Option A: download EKI's Kõnekorpused as the eval set

| Dimension | Assessment |
|---|---|
| Cost | 0.4–0.7 GB per speaker, ID-card login |
| Validity | Native professional readers — the opposite of the target |
| Effort | Low |

**Pros:** ready-made, CC BY 4.0, thousands of sentences with text.
**Cons:** answers "how well does it hear a professional Estonian reader", which
neither engine will fail and neither differs on. It cannot contain a learner's
mistakes, so the deciding measure is not even defined on it.

### Option B: FLEURS or Common Voice as the eval set

| Dimension | Assessment |
|---|---|
| Cost | Gigabyte download; Common Voice needs an account |
| Validity | Native, clean; same objection as A |
| Effort | Medium (gated formats, no partial fetch) |

### Option C: record the learner in the app (**chosen**)

| Dimension | Assessment |
|---|---|
| Cost | ~30 minutes of the learner's time, once |
| Validity | Exactly the voice, microphone and errors the app will meet |
| Effort | Medium: a recording mode and a local-only route |

**Pros:** measures the thing that decides; planted mistakes make the
false-accept rate real; nothing leaves the machine.
**Cons:** one speaker, so the numbers describe this learner — which is stated
wherever they are reported; and the set has to be recorded before any swap.

## Consequences

**Easier:** the swap question becomes answerable, and re-answerable after a
provider changes a pinned model.

**Harder:** the eval cannot run in CI — the data is personal and local. It stays
a local command, like the browser journeys.

**To revisit:** if the app ever has more than one learner, a shared eval set
would need consent and a licence of its own; and if EKI's word pronunciations
are ever wanted for the *word card* (real human audio instead of TTS), that is a
separate decision about 960 MB and an ID-card login, not this one.

## Action items

1. [x] Local-only clip route and the recording mode in Rääkimine.
2. [x] Paired scoring, WER split, CER, false accept, bootstrap interval.
3. [ ] Record 80–150 utterances, a quarter of them with a planted mistake.
4. [ ] Run both engines and commit the results table before any swap.
