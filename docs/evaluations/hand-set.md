# Grammar eval labels

`eesti/evals/gec.py` contains ten deliberately altered sentences and eight
hand-written clean controls. They are **our examples**, not a native-speaker
gold corpus. A correct word form alone cannot establish a correct object case:
the construction decides it. This small set diagnoses a lane; promotion also
needs the separate [TalTech corrected-sentence track](../ai-providers.md#choosing-a-model-the-eval)
and review of its proposed edits.

The eight clean controls are grounded as follows:

| Sentence | Why the label is clean | Source |
|---|---|---|
| `Ma lugesin selle raamatu läbi.` | Completed, whole object: omastav. | [EKI: osasihitis/täissihitis](https://eki.ee/teatmik/osasihitis-ja-taissihitis/) |
| `Ma ei ostnud piletit.` | Negated object: osastav; EKI's rule includes a ticket example. | [EKI: osasihitis/täissihitis](https://eki.ee/teatmik/osasihitis-ja-taissihitis/) |
| `Ta luges raamatut terve õhtu.` | Duration does not establish completion; osastav is licensed. | [EKI: osasihitis/täissihitis](https://eki.ee/teatmik/osasihitis-ja-taissihitis/) |
| `Ma ostsin uue auto.` | Completed purchase of one whole car: omastav. | [EKI: osasihitis/täissihitis](https://eki.ee/teatmik/osasihitis-ja-taissihitis/) |
| `Ma sõin suppi.` | Unbounded quantity: osastav. | [EKI: osasihitis/täissihitis](https://eki.ee/teatmik/osasihitis-ja-taissihitis/) |
| `Homme ma lähen kooli ja tulen kell viis tagasi.` | `lähen` and `tulen` are ordinary first-person forms; no object is being tested. | [Sõnaveeb: minema](https://sonaveeb.ee/search/lite/dlall/minema/1/est?uilang=en), [tulema](https://sonaveeb.ee/search/unif/dlall/dsall/tulema/1/est?uilang=en) |
| `Mulle meeldib eesti keel, aga grammatika on raske.` | `mulle meeldib` takes the liked thing as subject; no object-case decision. | [Sõnaveeb: meeldima](https://sonaveeb.ee/search/unif/est%2Ceng%2Crus/eki/meeldima/1/est?uilang=en) |
| `Ta ei leidnud oma võtmeid.` | Plain negation takes osastav; `võtmeid` is a listed form of `võti`. The special `mitte … vaid` exception is absent. | [EKI: osasihitis/täissihitis](https://eki.ee/teatmik/osasihitis-ja-taissihitis/), [Sõnaveeb: võti](https://sonaveeb.ee/search/unif/dlall/dsall/v%C3%B5ti/1/est?uilang=en) |

As a separate source-anchored check, the 2026-09-23 local EstLLM trial also
used three short correct examples shown directly in the same EKI rule:
`Poiss sõi putru.`, `Poiss sõi pudru ära.`, and
`Poiss ei söönud putru ära.` It returned one no-op and two proposed edits,
including `pudru → putru` in the completed `ära` sentence. This corroborates
the concern independently of our hand-written labels; it is still too small
to estimate general error rates.

`left_alone` counts a clean response only when the model returns an empty
correction list. `no_op_flags` counts suggested replacements that do not change
the text; `changed_flags` counts proposed edits. A no-op is an unusable API
response, but it is not evidence that the model believes the sentence is
ungrammatical. Neither category alone proves a proposed edit is wrong: inspect
the words and cited rule. The app rejects no-op and unlocatable corrections.
