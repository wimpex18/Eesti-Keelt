# Handoff

Current task: end-to-end product QA and landscape answer reachability.
Branch: `codex/product-qa-e2e`; base: `main`.

The initial landscape answer and check controls now fit above the mode dock.
A regression measures reachability and dock clearance in Chromium and WebKit.
It fails against the previous CSS and passes with the compact practice layout.

Verification: 2,491 Python tests passed (1 skip); typecheck and 7 Worker tests
passed; 204 browser journeys passed (4 skips). All 11 tabs inspected at desktop,
phone, landscape and tablet sizes in both themes; production inspected on phone
and desktop. The current origin passes a fresh deep smoke.

Next: owner reviews/merges the QA PR. Resolve PM-26: deployment credentials lack
VPC service access, leaving the production Worker stale. Its auth endpoint is
404 and its home ASR lane is unconfigured despite a healthy Mac mini tunnel.
Then redeploy and verify disposable account isolation, home transcription and
offline-home fallback. Deep smoke writes one sample writing event; the stale
Worker routes that service-token call to the legacy owner.

Uncommitted paths: none after this commit.
Blocker: VPC-authorized deployment credential; actual home ASR inference remains
unverified. No deployment or merge performed in this branch.
