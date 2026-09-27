---
target: "PR #91 Profiil page and progress reset"
total_score: 32
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 0
target_identity: "file:/Users/sergey/Documents/Projects/Eesti Keelt/eesti/web/js/profile.js"
target_fingerprint: "sha256:2d94f4f36fda757eedd78d105242a55a636a95038fb3fd05a650e6270322734f"
target_path: /Users/sergey/Documents/Projects/Eesti Keelt/eesti/web/js/profile.js
timestamp: 2026-09-27T13-25-26Z
slug: eesti-web-js-profile-js
---
# PR #91 — Profiil page and reset review

**Design specificity verdict:** The page is recognizably authored for Eesti-Keelt: Estonian A2/B1 exam concepts are paired with Russian guidance, and the profile groups milestones, practice rhythm, exam target, and vocabulary evidence in the app’s existing learning language. The familiar definition-list and section structure is conventional, but the restrained Estonian blue, Geologica type, ruled dividers, and existing liquid-glass navigation make it coherent with the rest of the product. New data sections stay flat instead of adding glass cards, which preserves the app’s hierarchy.

**Nielsen heuristic scores — Assessment A before fixes → integrated post-fix review:**

| # | Heuristic | Initial | Final | Key issue |
|---|-----------|---------|-------|-----------|
| 1 | Visibility of System Status | 3 | 3 | Reset now announces success; name-save feedback remains a small gap. |
| 2 | Match Between System and Real World | 3 | 4 | Russian scope descriptions and empty-email gloss now explain account terms. |
| 3 | User Control and Freedom | 3 | 3 | Reset confirmation has Cancel; completed reset still has no in-product undo. |
| 4 | Consistency and Standards | 4 | 4 | Profile controls use the existing type, spacing, button, and glass systems. |
| 5 | Error Prevention | 2 | 3 | Both permanent and guest resets now require an explicit second action. |
| 6 | Recognition Rather Than Recall | 3 | 4 | Milestone and rhythm meanings are visible, and individual days have spoken labels. |
| 7 | Flexibility and Efficiency | 2 | 2 | No profile shortcuts or power-user controls; reasonable for this learner surface. |
| 8 | Aesthetic and Minimalist Design | 3 | 3 | The page remains calm but is a long vertical read. |
| 9 | Error Recovery | 3 | 3 | API errors stay visible; permanent reset remains one-way in the profile UI. |
| 10 | Help and Documentation | 2 | 3 | Inline Russian guidance improved; there is no contextual path to fuller help. |
| **Total** | | **28/40** | **32/40** | **Good; the copy, prevention, and recognition gaps improved.** |

**Deterministic scan:** `impeccable detect --json eesti/web` completed with 67 advisory findings: 43 radius-token, 23 color-token, and 1 em-dash finding across `eesti/web/app.css`, `eesti/web/index.html`, `eesti/web/sw.js`, and computed page output. It reported no finding in `profile.js`. The radius/color notices are mostly false positives against this project’s documented pills, tints, and token-based surfaces; they do not identify a new profile inconsistency. The em-dash notice is outside the changed profile component. Assessment A caught interaction and language issues the scan cannot identify; the scan added no new component-specific defect.

**Visual overlay:** No user-visible overlay is available. The browser path rejected `javascript:` and page mutation, so the detector could not be injected. Fallback evidence came from fresh-browser screenshots and computed layout at the required viewport sizes.

## Overall Impression

The profile reads as part of the existing app rather than a new visual subsystem. The reset is easy to find at the end of the page and now has a clear confirmation boundary. The largest remaining opportunity is helping a learner with an empty profile move directly into their first useful exercise.

## What’s Working

- Geologica, Estonian blue, existing spacing tokens, ruled sections, and glass navigation remain consistent in light and dark themes.
- Reset copy states exactly what is removed and what remains; Cancel returns focus, the confirm buttons disable while the request runs, and success/error feedback is announced.
- Russian legends explain milestones and activity intensity without relying on hover. Each rhythm cell also exposes its date and exercise count to assistive technology.

## Priority Issues

1. **[P2] Account scope and missing email needed a Russian gloss — Fixed.** Guest, learner, and owner status are consequential, but the Estonian account labels alone did not explain whether progress persisted. **Fix:** Added short Russian scope descriptions and a gloss for an absent email. **Suggested command:** `$impeccable clarify`.
2. **[P2] Milestones and the activity chart depended too much on visual inference — Fixed.** A learner could see cells and seals without knowing what their states meant, especially on touch or with a screen reader. **Fix:** Added visible Russian legends and full date/count labels for rhythm cells. **Suggested command:** `$impeccable audit`.
3. **[P2] Sandbox reset could be triggered without a confirmation — Fixed.** Clearing a learner’s temporary work had no final check, and the new permanent reset needed the same protection. **Fix:** Both reset flows now expand an inline confirmation with Cancel; the permanent route preserves account identity and exposes the one-way/archive behavior before submission. **Suggested command:** `$impeccable harden`.

## Persona Red Flags

- **Jordan (first-timer):** The new account descriptions and visible chart legend remove two sources of ambiguity. A brand-new learner still reaches zero totals and milestones without a nearby “start your first practice” action; the exam-goal link is the only direct next step in the profile rows.
- **Sam (accessibility-dependent):** Reset confirmation, focus return, status announcements, and per-day labels are explicit. The 12-week rhythm exposes many individually labelled day images, so linear screen-reader browsing can be verbose; the visible 4-week summary helps but does not replace assistive-technology testing.
- **Casey (mobile):** The reset control sits after the profile sections and requires a scroll, which keeps a destructive action away from casual taps. Tested controls are 48px high in portrait and the confirmation stays above the floating dock in landscape.

## Minor Observations

- The profile is a long scroll on phones; the visual hierarchy stays clear and all four tested viewports have no horizontal overflow.
- The bilingual name-edit label now has breathing room. Empty “not yet” dates also carry the required Russian gloss.
- The reset preserves the append-only evidence log for export/recovery, but the profile offers no restore action. Keep the visible copy clear that preservation does not mean a one-click undo.
- No decision point presented more than four visible choices: level tabs have three options, auth tabs have two, and reset confirmation has two.
- The success message makes the reset’s endpoint reassuring, while the absence of a user-facing undo remains the emotional low point for someone who confirms accidentally.

## Questions to Consider

1. For a profile with no practice yet, should the next pass add a direct “start practice” action, or keep the profile informational? **Options:** Add a shortcut to practice · Keep the current exam-goal link only.
2. Should the permanent reset remain one-way in the UI, or should a later pass add a restore action backed by the retained event history? **Options:** Keep it one-way · Add an in-app restore flow.
