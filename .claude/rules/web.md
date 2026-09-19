---
paths:
  - "eesti/web/**"
---

# The page

- Open the page in a browser at desktop (1440×900), iPhone 17 (402×874 and 874×402, touch) and iPad mini 6 (744×1133, touch), every tab, and look at screenshots — geometry assertions miss what a picture shows.
- Visibility is `checkVisibility()`; reachability is `elementFromPoint` at the element's centre. A non-zero bounding box proves neither.
- Tabs live in the URL hash: `pushState` per change, `replaceState` for the landing tab, re-selecting the current tab does nothing.
- `main.js` bootstraps last; loaders may touch anything declared.
- Never set `textContent` on an element with decorated children (the Russian gloss); use `setLabel`.
- Every `var(--token)` must be defined (`tests/test_design_tokens.py`); spacing uses `--s1`…`--s6`; colours are tokens, never hex in rules.
- Give each information role its own treatment; colour by role, not by language.
- `.wrap` is a grid with rows placed by number: place anything added at its top level deliberately.
- Before making a container flex, check what its children relied on normal flow for.
- `.panel > :first-child` owns the top-margin reset; do not copy inline resets.
- A media query does not raise specificity: a rule inside `@media` loses to a later rule of equal depth. Measure in a browser; deliberate overrides sit at the end of `app.css`.
- After a fix, re-run the whole browser pass — fixes create the next bug.
- Estonian labels, Russian explanations (see AGENTS.md); `tests/test_ui_language.py` enforces it.
- The service worker cache version is stamped by the server (`api/assets.py`); never hand-edit `VERSION` in `sw.js`, and never cache the API.
