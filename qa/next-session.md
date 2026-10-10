# Next session

Keep this file current: replace a prompt when its work is done.

## Opus sessions

The order, the progress and every brief live in `qa/opus-sessions.md`. Start a
session by writing one line, with the ID from its "Progress and order" table:

```text
Run <ID> from qa/opus-sessions.md.
```

The refresh after each step is the brief `R` in the same file (R1–R4).

## Haiku in production

Haiku 5.5 leads the grammar and tutor chain once `ANTHROPIC_API_KEY` is on
Cloud Run: in Cloud Shell, `bash deploy/set-llm-key.sh ANTHROPIC_API_KEY`, then
the `smoke` workflow with `deep: true`. Re-run `eval.yml` (provider anthropic,
both tracks, effort high) after any change to `grammar.CLAUDE_PROMPT`.
