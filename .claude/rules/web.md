---
paths:
  - "eesti/web/**"
---

# The page

- Inspect every page at desktop 1440×900, phone 402×874 and 874×402 (touch),
  tablet 744×1133 (touch), and the user's reported viewport. Use screenshots as
  well as geometry; follow the active design skill's bounded review workflow.
- Visibility is `checkVisibility()`; reachability is `elementFromPoint` at the
  element's centre. A non-zero bounding box proves neither.
- Four skills stay reachable. Home, Course, Review, Exam and account use links.
  The phone More menu closes even on a link to the current page.
- Hash routes include session and rule topic IDs. Reload keeps the place,
  re-selecting adds no history, and malformed routes recover.
- `main.js` bootstraps last. Never set `textContent` on decorated label children;
  use `setLabel` so the explanation-language gloss survives.
- Define every CSS token. Use spacing `--s1`…`--s7` and semantic palette roles.
  A screen rebuilt from now on keeps every fixed rule of `DESIGN.md` and starts
  from its reviewed proposal, which the builder may improve and then records
  there (its "Fixed and open" section); screens not yet rebuilt keep the
  shipped Practice rhythm tokens until the token step of its Migration section
  lands.
- Use native links, buttons, details and labelled fields. View switches use
  `role="tablist"`, roving focus and `aria-selected`. Long references use a page;
  popovers are reserved for contextual word lookup.
- The wrap has navigation and content columns on desktop, one content column
  on phones. Check normal-flow assumptions before adding flex/grid.
- `.panel > :first-child` owns the top-margin reset. Media queries do not raise
  specificity; measure deliberate overrides in the browser.
- Estonian labels, Russian MVP explanations; preserve source/progress identities
  when preparing other explanation languages. The default explanation language
  comes from `navigator.languages` (first of uk, ru, en; else en) and a saved
  choice wins (`PRODUCT.md`). See AGENTS.md.
- After web changes run the whole browser journey suite and inspect both device
  classes. Keep skips distinct from checked mastery and FSRS.
- The server stamps the service worker version (`api/assets.py`). Never edit
  `VERSION` by hand, leave deleted modules out of precache, and cache no API.
