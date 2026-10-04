# Grove QA and product review

## Verdict and scope

The two open implementation defects are fixed locally: dictation accepts only
server-issued passages, and the compressed build initializes faster on both
viewports. This is **not a production release sign-off**: these changes await
review/merge, deployment and deep smoke. Real account durability and live speech
quality remain unverified.

Audit: 2026-10-03; follow-up fixes: 2026-10-04; source base `eba54af` on
`codex/dev-17-dev-18-qa-fixes`, plus the changes listed below. Public app:
`https://eesti-keelt.wimpex18.workers.dev/`. Its observed health build is
`2026-10-03T19:10:09Z`, with no Git revision. The redesigned shell is visible;
exact deployed-source parity cannot be established from that stamp.

Local Chrome used scratch guest databases in `/tmp/eesti-qa`; provider keys
were blank. Local FastAPI is not a substitute for Worker authentication or home
ASR forwarding. No owner progress was reset; no personal recording was created.
Public browsing used a separate QA sandbox. Private HARNO/learner data are not
included in committed evidence.

See [test plan](test-plan.md) for research, case families and release gates;
[inventory](inventory.md) enumerates routes, modules, static controls and APIs.

## Verification

| Check | Result and limits |
|---|---|
| Initial Python suite | 2531 passed, 1 skipped |
| Initial four engine/viewport combinations | 346 passed, 46 skipped; source changed during this run, so it is broad coverage rather than final-revision certification |
| Recovery regressions | 22 passed; onboarding Back/focus, writing duplicate/timeout, conversation failed-send retention |
| Final focused journeys | 40 passed, 2 skipped; Chromium desktop/WebKit phone; includes speech availability; service workers blocked for request-interception cases |
| Final compiled journey run | 205 passed, 23 skipped in 7m08s; Chromium desktop/WebKit phone, including signed dictation retry and delayed-script start rendering |
| TypeScript | passed |
| Worker account/replication/security suite | 26 passed |
| Current Python suite | 2544 passed, 1 skipped in 22.72 s |
| Chrome responsive inventory | 15 routes × 5 viewport classes; no horizontal document overflow in the measured states |
| Accessibility | axe includes WCAG 2.2 AA tags; Lighthouse start page accessibility 100; manual focus/recovery reviewed, no full screen-reader certification |
| Impeccable detector | 0 counted anti-patterns, 38 palette/type/radius advisories; these are not 38 confirmed user defects |

Existing fixtures exercise lesson scoring, correct/wrong/empty answers,
test-out, skipped-versus-mastered topics, review scheduling, vocabulary,
reading popovers, listening, writing, conversation, exam/mock types and timers,
account isolation, offline signed-pack replay and recovery. Browser skips
include unavailable catalogue/native materials; they are not successful tests
of private documents or live services. No simulated recognition result is used
as evidence of real ASR quality.

## Findings and retained changes

Nine actionable findings: 0 P0, 2 P1 fixed locally, 7 P2 fixed locally. Severity describes
learner impact; a laboratory performance score does not itself prove a WCAG failure.

| Priority / status | Trigger, impact and action |
|---|---|
| **P1 fixed locally — dictation grading integrity** | The answer now requires a signed passage, validates its task kind/version and recipient, and grades the issued text. Caller target text is ignored. Issuance respects source redistribution rights. Evidence retains issuance/attribution; old events still replay. Tests cover missing/tampered/malformed/other-kind/other-session tokens, starter scoring, target substitution and retry retention. [DEV-17](https://linear.app/pm-career-transition/issue/DEV-17/ek-bind-dictation-grading-to-server-issued-signed-passages). |
| **P1 fixed locally — cold mobile start** | The container builds one minified, compressed script and compressed CSS; the service worker caches the bundle without downloading source modules again. Start content and skill glosses paint before initialization. Fonts use optional display to avoid late replacement. Repeated matched timings show first content about 0.8 s and initialization about 1.1 s on both viewports; final mobile Lighthouse CLS is 0.003. See [performance evidence](performance.md). [DEV-18](https://linear.app/pm-career-transition/issue/DEV-18/ek-reduce-cold-start-latency-and-investigate-mobile-layout-shift). |
| P2 fixed — onboarding Back and focus | Goal-choice Back returned to the first screen, losing the immediately preceding choice context. It now returns to starting-band choices, and replacement headings receive keyboard focus. `onboarding.js`. |
| P2 fixed — duplicate writing submission | Ctrl+Enter could submit during an active check. The disabled-state guard now prevents a second request. `write.js`; regression counts requests and checks draft retention. |
| P2 fixed — lost conversation draft | Sending cleared text before the tutor succeeded. Failed requests now retain it; repeated Enter is guarded and a stale response cannot overwrite a replaced conversation. `speak.js`. |
| P2 fixed — indefinite request wait | Fetches could leave controls waiting indefinitely for headers. Normal calls now abort at 30 s with a Russian retry message; transcription allows 60 s for the 25 s home-to-hosted fallback. `core.js`. This bounds waiting for response headers; a stalled body stream is not separately timed. |
| P2 fixed — irrelevant startup probes | Speech availability/report, private evaluation and writing queue requests ran when importing modules. They now load on the relevant screen/exercise; guest speech never probes the owner-only evaluation route. `router.js`, `speak.js`, `voice.js`, `write.js`. |
| P2 fixed — small navigation/word targets | Brand and home links were 32–43 px; the inline onboarding link did not honor its minimum height. These and starter word-lookup buttons now have 44 px targets. `app.css`. Inline source-attribution text remains inline and is assessed under the inline-link exception. |
| P2 fixed — misleading deployment documentation | Status/HANDOFF claimed the old interface was live despite the visible redesigned shell. Current docs distinguish observed deployment from unverifiable commit parity. |

No linguistic forms/rules, scoring engine, FSRS contract or provider lane was
changed. Model feedback remains advisory. A blanket module-preload experiment
was removed because repeated measurements did not demonstrate a useful result.
The production Mac mini lane is speech recognition; hosted grammar/tutor uses
Workers AI GPT-OSS-120B. A failed local grammar model is not treated as the
production grammar dependency.

## Chrome DevTools and performance evidence

Chrome 154 and Lighthouse 13.4.1 were used on the isolated local `#start`.
[Performance evidence](performance.md) contains the matched before/after timings,
compression/request counts, final layout-shift result and reproducible setup.
Earlier Lighthouse LCP values are not valid app timings: the final clean audit
identified the browser-control extension's cursor as its LCP element. We exclude
those values from the speed claim. Samples whose emulation/throttling reset were
also excluded. The new gains refer to local assets/rendering, not production
origin wake-up, real-device field percentiles or live model latency.

## UX, task effort and responsive review

The interface has a useful core: a next lesson, four permanently visible skills,
source-attributed rules, a bounded five-question session and a clear result.
Keep those. Self-selected starting points are explicitly distinct from CEFR and
checked mastery. Guest profile explains that progress is temporary.

Activation counts exclude typing and scrolling and describe the ordinary route.
The manual new-user journey finished five deliberately wrong choices, showed
0/5 without mastery, and offered retry/new-sentences/home actions. Correct-answer
and scoring boundaries are covered by the deterministic regression fixtures.

| Task | Desktop / phone effort | Product conclusion |
|---|---|---|
| Begin from scratch → lesson | 3 choices/activations to lesson: beginning, goal, start; 1 more to practise | Two choices have different purposes. Remove the unrelated network work first; do not collapse exam goal into a mastery claim. |
| Choose a starting band → lesson | 4 activations to lesson, 1 more to practise | Back now preserves the preceding step; no need to repeat the entire entry route. |
| Open reading/listening/speaking/writing | 1 permanent skill tab | Keep these direct destinations. |
| Finish five typed exercises | 5 checks + 5 continue actions | Continue allows correction to be read. Keyboard submission reduces pointer travel; do not auto-advance past feedback. |
| Open Exam / Review from mobile shell | More + destination: 2 activations | Acceptable supporting navigation; retain direct links in relevant empty states. |

Measured Chrome layouts: desktop 1440×900, phone 402×874, landscape 874×402,
tablet 744×1133, actual window 1512×406. All 15 routes were captured in each.
Light/dark reading were inspected on desktop and phone. Final word targets were
rechecked after stylesheet reload; inline attribution links are not enlarged
into separate buttons. Emulation and mouse/keyboard checks do not certify
physical-device swipes, long-press selection, audio output or thumb comfort.

Initial Impeccable audit health: **12/20, Acceptable — significant work needed**.
Its dictation-integrity and startup findings are now fixed locally; no new full
audit score is assigned here.
Accessibility 3/4 (automated coverage and improved focus, manual assistive-tech
gate remains); initial performance 1/4 (cold mobile delay/shift); responsive 3/4
(measured reflow, physical touch gate remains); theming 3/4 (light/dark captures,
not every expanded state); implementation integrity 2/4 (coherent Grove identity
passes; answer-key trust was subsequently fixed). Detector advisories include existing pill
radii/type steps and a dark background tone; they are documentary/token alignment
questions, not automatically accessibility violations. No new ignore rules added.

## Remaining release gates and evidence

1. Review/merge the DEV-17/DEV-18 fixes; deploy and run deep smoke.
2. Use a disposable real Worker account to verify signup/logout/expired session,
   cold-origin restoration and cross-device progress. Existing Worker tests cover
   protocol behavior; they do not prove this deployed-account journey.
3. Human-verified learner audio must exercise Mac mini ASR, its failed-service
   fallback, playback and recording permission on physical devices. Local blank
   provider configuration and fixtures prove recovery boundaries only.
4. Complete screen-reader traversal, zoom/text scaling, physical touch and
   downloaded official-material verification with the intended learner roles.
   Unloaded/private materials were inspected as unavailable states, not certified.

Remaining design verification concerns physical devices and assistive technology.
The local fixes do not certify those external release gates.

Local, git-ignored evidence is under `.impeccable/review/qa/`: Lighthouse JSONs,
75 route/viewport captures, native Chrome light/dark phone reading, offline-writing screenshot,
viewport geometry, detector output and test logs. Screenshots contain synthetic
guest material only. This report and test plan are the durable review artifacts;
raw captures remain on this computer and are not published.
