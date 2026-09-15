/* The entry point, and the only file that runs anything on load.

   Every import first, the bootstrap last: opening a tab runs its loader, which
   may touch anything in any module, so bootstrapping after every module has
   evaluated avoids the temporal dead zone. */

import {glossChrome, paintIcons} from "./chrome.js";
import {goToPlace, selectTab} from "./router.js";

/* Imported for their wiring, not for a name.

   `reading.js` and `write.js` export nothing; they attach their handlers when
   they evaluate. A module nobody imports never runs, and the panel would open
   with every button silently dead. `tests/test_ui_contract.py` fails on a module
   the entry point cannot reach. */
import "./reading.js";
import "./sources.js";
import "./write.js";

if ("serviceWorker" in navigator) {
  addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

addEventListener("hashchange", () => goToPlace(location.hash.slice(1)));


// The path is the default landing tab: it is the one screen that answers
// "what do I do now" without the learner having to decide. A hash naming a
// real tab wins over it; anything else falls back rather than showing nothing.
paintIcons();

glossChrome();

if (!goToPlace(location.hash.slice(1))) {
  selectTab(document.querySelector('nav[data-mode-nav="learn"] button'));
  // Replace, never push: the landing tab must not become an extra Back step
  // between the learner and the page they arrived from.
  history.replaceState(null, "", "#path");
}
