# Handoff

Current task: PR [R2] folds steps 1–4 into the notes and waits for the owner's
merge. On `main`: S2 (checked dialogues and texts, units 2–10), S10 (tokens and
shell), S3 (Reegel's rule walk), S9 (Sõnastik and the word card).

Next step: S8 is ready: "Run S8 from qa/opus-sessions.md." in its own session.
For S8 (left by the finished sessions):
- Mark each screen's one `data-primary` and the awaiting item `data-dock-task`;
  *Peata* in the header; the desktop sticky action row; `interlinear()` for the
  revealed word; fit its form line on a narrow screen (`fitInterlinear`).
- `path.js`'s learn step shows `tip.gist_ru`, an unsourced tip: read the lesson
  response's `gist_ru`, then drop `tip` from `/api/lesson`. The rule step can
  reuse `rulewalk.walk(topic)` with `record: true`.
- Items could open the word card on a tapped word. No unit page shows units
  2–10's dialogues and texts yet. iOS Safari, keyboard up: Sõnastik's dock
  band leaves one result row.

Later: S4 folds the walk's Russian (`Explanation.text_ru`, `rulewalk.CASE_RU`)
and Sõnastik's `LANG_RU` into the catalogue; S11 can add `good`/`bad` on
`ground` to DESIGN.md's contrast table. `official_levels` keeps the last line
per word (*mina*, *hea* read B1) until `minu-pere` (*vana*) is re-checked.

Owner operations: re-run `deploy` once Cloud Build has shipped `main` (its run
after #131 failed the shell check), then `smoke` with `deep: true`; in local
checkouts run `cli material build` and `cli import-evs` once; then the list in
`qa/architecture-review.md` (Haiku key and spend limit, Klint trademark search
and `klint.ee`, permissions, backup verification). Re-subscribe to reminders
on each device. Licence tasks wait for launch. Linear is paused. Uncommitted:
none after the commit. No secrets revealed.
