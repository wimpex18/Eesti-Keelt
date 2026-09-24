# Handoff

## Current state
The production deep smoke passes for the current image,
Cloudflare Access and origin guard, Workers AI grammar, Ekilex, EKI audio, HARNO
PDF rendering, and reading content. The smoke does not test native exam sidecars,
microphone recognition, or browser notification delivery.

Cloud Run has one instance and mounted EKI audio and HARNO exam storage. Workers
AI GPT-OSS-120B remains the automatic hosted grammar/tutor lane, with
deterministic fallback; Cloudflare Workers AI is production ASR. Local EstLLM is
an evaluation-only Ollama model stored outside Git. Native A2 and B1 reading
controls require private sidecars under `data/exam/`; other PDFs remain
ungraded. The owner has a verified private off-account event export.

## Current task

Review and merge the documentation cleanup PR. It removes stale release notes
and keeps active documentation aligned with the shipped code. No active runtime
code changes are included. Uncommitted paths after commit: none.

## Remaining checks

Verify the two native reading controls in production, actual Chrome reminder
delivery, and ASR on learner recordings reviewed inside `Hindamiskomplekt`.
