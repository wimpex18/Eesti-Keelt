# S9 Dictionary (Sõnastik) — handoff

**Task.** S9 of `qa/opus-sessions.md`: Sõnastik and the word card on one entry
per lemma (`eesti/dictionary.py`, `eesti/api/dictionary.py`,
`eesti/web/js/dictionary.js`), model-drafted English and Ukrainian behind a
blind back-translation (`eesti/dictionary_glosses.py`, `cli dictionary`).

**State.** Built and committed on `claude/s9-dictionary`; fast suite and the
browser journeys green on both engines. 1 368 checked glosses (739 English,
629 Ukrainian, 748 words) in `content/dictionary/glosses.jsonl`, $0.43.

**Exact next step.** The orchestrator opens the PR "[S9] Dictionary (Sõnastik)"
from the draft in the final report and sets S9's status cell.

**Owner operations.** None required: the image imports the glosses
(`Dockerfile`). Optional: `cli dictionary glosses` drafts for more words (the
set is EKI's A1 list and the units' words; extend `dictionary_glosses.wanted`).

**Follow-ups.**
- R2: `official_levels` keeps the last line per word (*mina*, *hea* read B1);
  keeping the lower level needs S2's `minu-pere` re-checked (*vana*).
- S8: the session's items could open the word card on a tapped word.
- S4: the entry's meanings follow the explanation language (English or
  Ukrainian first; `LANG_RU` names languages in Russian today).
- Offline sourced English/Ukrainian: EKI's Estonian–English and
  Estonian–Ukrainian downloads (`docs/source-integrations.md`) need the owner's
  download and a sense review before they outrank the drafts.

**Uncommitted paths.** None. **Blockers.** None.
