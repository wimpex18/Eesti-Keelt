# S3: Interactive rules (Reegel) — `claude/s3-rule-walk`

**Task.** The Reegel page teaches by doing (ADR-0009 step 2; DESIGN.md Migration
step 4): notice, ask, explain, contrast and the form switch on `#rule/obj-case`
and `#rule/osaalus`; other topics get the rebuilt page without the walk.

**State.** PR #136; fast suite and browser journeys (both engines) green.
Logic `eesti/rulewalk.py`, data `lessontext.WALKS`, page `eesti/web/js/lesson.js`,
tests `tests/test_rulewalk.py` and `TestTheRuleWalk`.

**Next step.** The owner merges #136 (S9's PR then syncs with main: its
status row sits beside S3's in `qa/opus-sessions.md`).

**Outside S3's list.** `eesti/lessons.py` (the lesson response gains `gist_ru`
and `walk`); granted: `eesti/web/app.css` (Reegel block), rule-page journeys in
`tests/test_e2e_journeys.py`, rule-page lines of `docs/status.md`.

**Follow-ups.**
- S8: `path.js`'s learn step shows `tip.gist_ru`, an unsourced tip; use the
  response's `gist_ru`, then drop `tip` from `/api/lesson`. The session's rule
  step can reuse `rulewalk.walk(topic)`, answering with `record: true`.
- S8/S10: `interlinear()`'s form line can run off a narrow screen; the rule page
  moves or wraps it (`keepLinesInside`); `fitInterlinear` could do it everywhere.
- S4: the walk's Russian (`Explanation.text_ru` by stable id, condition glosses,
  `rulewalk.CASE_RU`, the notice question) joins the catalogue.
- R2: DESIGN.md's contrast table could list `good`/`bad` on `ground` (values in
  the Reegel section). More walks are data only (`lessontext.WALKS`).

**Uncommitted.** None. **Blockers.** None.
