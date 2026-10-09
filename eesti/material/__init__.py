"""Material written with a model and checked by code: dialogues and reading texts (ADR-0009).

A model may write material; only code may key it (ADR-0004). The pipeline, in
the order a draft meets it:

1. `schema` — the JSON shape a draft must have (`cli material schema`).
2. `gates` — the deterministic checks: Vabamorf, the stage's EKI level, the
   unit's grammar, answers verbatim once, one right answer per gap
   (`cli material check`).
3. `blind` — Claude Haiku 5.5, through the Message Batches API, answers each
   item without the key, and each question again without the text; an item it
   gets wrong, or gets right without the text, is dropped (`cli material blind`).
4. `store` — what passes is written to `content/material/checked/<unit>/<slug>.json`
   with the pipeline's stamp, and built into `content.db` as
   `mat:<unit>:<slug>@<sha8>` under the public source `grove-material`
   (`cli material build`), labelled `LABEL`.
5. `stats` — after release, *Teata veast* reports and answer statistics retire
   items whose answers split or never vary.

No answer key reaches `checked/` or `content.db` without passing 2 and 3, and
`build` re-runs 2 and verifies 3's stamp against the file's own hash.
Specification: `docs/material.md`.
"""

#: Shown with every piece of material beside the engine and prompt version
#: that wrote it. Provenance is explanation, so it is Russian, as the app's
#: other model labels are (`writingtasks.PROMPTS_BY`).
LABEL = "написано моделью, проверено Vabamorf и автоматическими проверками"

#: The same label in English, as ADR-0009 states it.
LABEL_EN = "written with a model, checked by Vabamorf and automatic checks"

#: The ledger's source id (`eesti/licences.py`).
SOURCE_ID = "grove-material"
