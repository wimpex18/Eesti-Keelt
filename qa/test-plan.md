# Grove QA test plan

## Scope and evidence rules

Test the local checkout and the deployed Worker separately. Record the Git
revision and deployed `/api/health` build stamp. A rendered redesigned shell
does not establish that every local change is deployed. Use isolated guest
sandboxes and scratch databases; never erase or grade against the owner's history.
Local FastAPI does not implement Worker authentication or speech forwarding.
Permanent-account and cross-device durability require a disposable account in
the actual Worker runtime. Distinguish pass, fail, skipped, blocked and not run.
Provider configuration, synthetic speech and mocked responses do not prove live
recognition quality, audio audibility or human learning outcomes.

## Research applied

- [Playwright best practices](https://playwright.dev/docs/best-practices):
  isolated state, visible outcomes, role/label locators, retrying assertions,
  controlled dependency failures, evidence on failure.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/): keyboard, reflow, contrast,
  labels, errors, status announcements and reduced motion. Check
  [unobscured focus](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html),
  [drag alternatives](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements),
  [accessible authentication](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum).
  AA [target minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
  is 24 CSS px with exceptions; Grove's requested product floor is 44×44 px.
- [Web Vitals](https://web.dev/articles/vitals): target LCP ≤2.5 s, INP ≤200 ms,
  CLS ≤0.1 at the 75th percentile. Single laboratory samples are diagnostic,
  not field percentiles. [Lighthouse](https://developer.chrome.com/docs/lighthouse/overview)
  complements manual accessibility and actual API readiness checks.
- [Duolingo learning research](https://research.duolingo.com/papers/settles.acl16.pdf)
  and [guided path rationale](https://blog.duolingo.com/new-duolingo-home-screen-design/):
  bounded sessions, readable correction, scheduled retrieval and a clear next
  activity are useful patterns. Applying them here is a product hypothesis;
  competitor claims are not evidence of Grove outcomes.

## Inventory and feature cases

Each row requires a normal completion, the specified negative case and recovery.
Inspect loading, empty, disabled, error and completed states in both themes.

| IDs / route / modules | Positive cases | Negative and edge cases / expected result |
|---|---|---|
| ON-01–08 `#start`, onboarding/profile | beginning, all four self-assessed starts, everyday/exam goal, grammar assessment, early stop, change start | back at each step, skip/explore, refresh and interrupt, rapid choice, failed save, empty/whitespace/oversized answers; retry reachable; no navigation choice creates mastery or FSRS |
| HM-01–05 `#path`, path | one next lesson, resume, next topic, change start, choose another topic | no mastery, all topics complete, unavailable curriculum, partial response, delayed response; truthful next action, recoverable error |
| CO-01–08 `#course`, path/curriculum | ordered chapters, prerequisites, every topic state, rule, start, test-out, skip/restore, checkpoint | locked/reference-only topic, 4/5 and 5/5 test-out, malformed topic, empty seed, duplicate submit; only server-checked pass sets mastery |
| SE-01–10 `#session/<topic>`, path/lesson | rule→five exercises→result; typed form, choice, word order, punctuation; correction, Edasi, history, repeat/next | blank, whitespace, wrong, Cyrillic, markup, long answer, fast double-click, skip, 5xx after submit, reload/back mid-set; errors keep answer editable, no duplicate evidence; reload semantics explicitly recorded |
| RU-01–04 `#rule/<topic>`, lesson | explanation, Vabamorf table, examples, attribution, return | missing/unknown/encoded topic, stale response, long text; no guessed rule or lost navigation |
| FR-01–06 `#drill` / free practice | every generator, topic/rule/difficulty/theme filters, translation on request, retry | empty set, invalid filter, failed check, repeated click; `record:false`, no mastery or FSRS; support does not submit answer |
| OF-01–07 offline pack, offline/sw | download five signed items, offline reopen/answer, reconnect/regrade/sync | no pack, unavailable shell, interrupted download, bad signature, expired item, duplicate replay, account change with queued pack; original timestamps retained; no API caching |
| RE-01–08 `#review`, review | due queue, grammar answer, vocabulary reveal/rate, phrase tiles, forecast, hard cards | empty/not-yet-due, blank, wrong, repeated rating, interrupted reveal, failed grade, identity switch; FSRS only changes on valid rating, retry preserves card |
| VO-01–07 `#sonad`, vocab/words | five-word workout, reveal/correct, queue miss, word statuses, level/POS/status filters, pagination | empty/wrong/oversized answer, skip, empty filter, repeated mining, failed lookup; skip is not known/mastered; EKI or identified estimate supplies word levels |
| RD-01–09 `#read`, reading/words | starter sentences, catalogue, filters, open/back, word popover, meaning/forms, mine, selected translation, comprehension | empty public corpus, inaccessible owner item, no selection, slow lookup then close, long card, failed page/translation, missing span; no owner-content leakage; source attached |
| LI-01–10 `#listen`, listen/media | dictation play/replay/answer/result/next, voices/speed, TTS, library filters/pages, radio/audio/video player, attribution | blank/wrong/long dictation, no recordings, refused TTS, failed HLS/audio, pause/navigation, offline playback, repeated submit; engine failure cannot grade as learner error |
| SP-01–12 `#speak`, speak/voice | read-aloud word/sentence, question topics, open response, record/stop/listen, transcript correction, feedback, recognition report | denied/no mic, insecure context, silence, oversized upload, stop twice, navigate during recording, ASR offline/timeout, Mac mini unavailable→fallback; disclose destinations, advisory scores only |
| CV-01–06 speaking conversation | start partner, typed turn, spoken turn review before send, audio reply | empty turn, double-send, failed tutor/TTS/ASR, navigation during response; retain unsent text, name engine, no mastery score |
| EV-01–05 private local speech review | save clip, play it, edit transcript, confirm listened, verify hash | guest denied, unreviewed draft, blank transcript, changed audio/text; prompt never counted as human-verified ground truth |
| WR-01–08 `#write`, write | daily prompt/custom text, grammar explanation, deterministic fallback, translation/back-translation, correction queue | empty/whitespace/oversized/malformed/HTML, slow/down hosted grammar, double-submit, refresh; input retained, engine labelled, no model mastery; owner-only Notion push tested without sending |
| EX-01–10 `#exam`, exam/mock | A2/B1 switch, format, four-part readiness, choose/change/unset sitting, calendar, checkpoints, timed part and whole exam | switch mid-run, refresh timer, zero/missing part, deadline, empty answer, partial submit, invalid sitting, unavailable tasks; no default sitting or combined pass prediction |
| MT-01–08 mock exercise types | gap, multiple choice, matching, listening, deterministic writing check, speaking continuation | false/blank/duplicate answers, forged key, timeout, retry; source-bound code scores, speaking unscored, readiness labels honest |
| WB-01–07 `#vihikud`, exam/media | HARNO list, downloaded PDF pages/image/text, native reviewed tasks, audio/video | not downloaded, corrupt/missing file, wrong level, unavailable official answers, owner-only ID; viewer in app when available; honest attribution link otherwise |
| PR-01–08 `#status`, path/remind/state | topic evidence, history, forecast, four exam parts, data export, reminder hour, permission/unsubscribe | no progress, unsupported/denied notifications, guest subscription, offline export, replication 503; no artificial streak/combined readiness; private export isolated |
| AC-01–12 `#profile`, profile/Worker | optional guest use, signup/login/logout, name, start settings, reset/restore | invalid email/password, whitespace/254+ email/1024+ password, duplicate signup, unknown/wrong login, delayed lockout, expired/forged cookie, cancellation; no exposed credential or identity bleed |
| SH-01–10 shell/router/chrome/sources | all primary links, four skill tabs, More, theme, source disclosure, deep links | same-route click, unknown/malformed route, browser back/forward, zoom, keyboard arrows/Home/End/Escape; meaningful names and focus, no menu overlay trapping controls |

## Common checks for every component

Apply to every rendered button, link, labelled input, textarea, dropdown,
checkbox, disclosure, tab, audio/video control, word popover and dynamically
generated exercise action. The source-derived control/API inventory is
`qa/inventory.md`; inspect dynamic templates in the listed modules too.

1. Click/tap, keyboard Tab/Shift+Tab/Enter/Space, meaningful screen-reader name,
   visible focus, selected/expanded/disabled state, logical focus after replace.
2. Scroll to first/last action; hit-test the centre (`elementFromPoint`), check
   `checkVisibility`, 44px product targets, sticky navigation occlusion, 200%
   zoom/320px reflow, text expansion, long feedback and dark-mode contrast.
3. Swipe native scroll; select text/long-press; where dragging exists, test
   tap and keyboard alternatives. Mark absent custom gestures N/A.
4. Repeat/rapid activation; navigate while request pending; late response
   cannot replace a newer task. Blank/whitespace/max+1/markup/Unicode input.
5. Slow/offline/timeout/400/401/403/404/422/429/500/503; explanation in Russian,
   named next action, restored controls, retained useful input/content.
6. Refresh/back/forward/new tab/reopen/logout/login/clear storage; separate
   session-only drafts from permanent evidence and document every reset.

## Execution matrix

- Chrome desktop 1440×900; Chrome touch phone 402×874, landscape 874×402;
  touch tablet 744×1133; user's actual viewport. WebKit phone in regression.
- Fresh named sandbox, returning guest, simulated permanent learner and owner
  in automated fixtures; deployed disposable-account verification separately.
- Cold no-cache/no-service-worker, warm service-worker, offline cached and
  uncached shell. Chrome DevTools Network, Console, Application/CDP inspection.
- Fast normal network and slow 150ms latency / 1.6Mbps down / 750Kbps up with
  4× CPU; record exact settings, cold vs warm and provider timings.
- Lighthouse mobile/desktop: performance, accessibility, best practices, SEO;
  save JSON/HTML. Do not equate an axe/Lighthouse pass with WCAG certification.
- Real audio heard, real microphone/permission, screen-reader traversal,
  physical touch and cross-device login remain explicit manual gates if absent.

## Commands and release gates

Run `.venv/bin/python -m pytest tests/ -q -n auto`, `npm run typecheck`,
`npm run test:worker`, and `.venv/bin/python -m pytest
tests/test_e2e_journeys.py --browser --all-browsers -q`. Meaningful new
regressions belong in the existing fixture-isolated journey/API suites.
Fail release on data leakage/loss, wrong deterministic grading, blocked core
journey, unhandled browser exception or a verified WCAG A/AA failure.
After the user merges and deployment completes, run deep production smoke.
Record current findings, tap counts, measured results and unexecuted gates in
`qa/results.md`; durable deferred product work belongs in Linear DEV/Eesti-Keelt.
