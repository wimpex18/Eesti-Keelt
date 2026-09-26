# Handoff

## Current state
PRs #72–#86 are merged. The production deep smoke passes for the current `main`
image. Cloud Run has one instance with mounted EKI audio and HARNO exam storage;
Workers AI GPT-OSS-120B is the grammar/tutor lane; Workers AI is production ASR.

## Current task
Branch `claude/home-asr-binding` (PR #87): binds the Mac mini home speech
service (`vpc_services` in `wrangler.jsonc`) and brings the docs to the current
state. The Mac mini runs `deploy/home-asr/install.sh` (Intel: TalTech Whisper
on the CPU); its tunnel is healthy and `HOME_ASR_TOKEN` is set on the Worker.

## Next step
User merges PR #87; the `deploy` workflow updates the Worker. Then the speaking
page should say "Сейчас тебя слушает твой Mac mini"; if it says Cloudflare,
check the deploy token's VPC permission. Run `smoke` with `deep: true`.
Uncommitted paths: none.

## Open questions
Whether to let EstLLM write comprehension questions in local `cli serve`
(Estonian-only work that code verifies), and whether to raise the grammar
lane's token budget: a long sentence returned `empty reply (length)`.

## Remaining checks
Chrome reminder delivery; 12 more owner clips to reach the ASR pilot floor.
