# Next session

Keep this file current: replace a prompt when its work is done.

## Wave 1, in parallel

After PR #125 is merged, start one session per brief in `qa/opus-sessions.md`:
S1 (material pipeline), S5 (generators the units lack), S6 (HARNO B1 task types;
the sittings are 7–8 Nov 2026) and S7 (design and motion documents). Paste only
the brief; it points the session at "Every session first", which puts it in its
own worktree on the files it owns.

## After a wave is merged

```text
Klint (Eesti-Keelt): fold the merged wave into the shared notes. Read AGENTS.md,
qa/opus-sessions.md and every qa/sessions/*.md. Rewrite HANDOFF.md as the
present state (≤30 lines), bring docs/status.md and qa/architecture-review.md up
to date with what merged, move each session's open follow-ups into HANDOFF.md
or the relevant doc, delete the merged qa/sessions/ notes, and mark the next
wave's briefs as ready in qa/opus-sessions.md. Fast suite green. One branch and
one PR; Linear is paused.
```

## Haiku in production

Haiku 5.5 leads the grammar and tutor chain once `ANTHROPIC_API_KEY` is on
Cloud Run: in Cloud Shell, `bash deploy/set-llm-key.sh ANTHROPIC_API_KEY`, then
the `smoke` workflow with `deep: true`. Re-run `eval.yml` (provider anthropic,
both tracks, effort high) after any change to `grammar.CLAUDE_PROMPT`.
