# S9 Dictionary (Sõnastik) — handoff

**Task.** S9 of `qa/opus-sessions.md`: Sõnastik and the word card on one entry
per lemma (`eesti/dictionary.py`, `eesti/api/dictionary.py`,
`eesti/web/js/dictionary.js`), model-drafted English and Ukrainian behind a
blind back-translation (`eesti/dictionary_glosses.py`, `cli dictionary`).

**State.** PR #137; fast suite and the browser journeys green on both
engines; checked on the iOS 27 simulator. 1 462 checked glosses (739 English,
723 Ukrainian, 749 words) in `content/dictionary/glosses.jsonl`, $0.45 in all.
Ukrainian re-checked after review: no copy-of-the-Russian filter; the checker
(`s9-back-2`) flags non-standard Ukrainian, code drops it and refuses a draft
that loses its main sense.

**Exact next step.** The owner merges #137 (after #136, sync with main: the
status rows sit side by side in `qa/opus-sessions.md`).

**Owner operations.** None (the image imports the glosses); optional: more words
with `cli dictionary glosses` (extend `dictionary_glosses.wanted`).

**Follow-ups.**
- R2: `official_levels` keeps the last line per word (*mina*, *hea* read B1);
  keeping the lower level needs S2's `minu-pere` re-checked (*vana*).
- S8: the session's items could open the word card on a tapped word.
- S4: meanings follow the explanation language (`LANG_RU` is Russian today).
- Offline English/Ukrainian: EKI's downloads (`docs/source-integrations.md`)
  need the owner's download and a sense review before they outrank the drafts.
- S10/R2: iOS Safari, keyboard up: the dock band leaves one result row.

**Uncommitted paths.** None. **Blockers.** None.
