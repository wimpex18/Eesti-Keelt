/* The entry point, and the only file that runs anything on load.

   Every import above the bootstrap, and the bootstrap last. That position is
   the fix for a real bug rather than tidiness: opening a tab runs its loader,
   a loader may touch anything declared anywhere, and from the middle of a file
   everything below it is in the temporal dead zone. Bootstrapping after every
   module has evaluated means there is nothing left to be too early for. */

import {glossChrome, paintIcons} from "./chrome.js";
import {goToPlace, selectTab} from "./router.js";

/* Imported for their wiring, not for a name.

   `reading.js` and `write.js` export nothing anybody calls: they attach the
   handlers for the reader and the writing check when they evaluate, which in
   one file happened by being in the file. In a module graph a file nobody
   imports is a file that never runs -- and the failure is silent, because the
   panel still opens and every button on it is simply dead. That is what
   happened to `Kirjutamine` for the length of one commit: the check button,
   the drill button and the error queue, all present and all inert, with no
   console error to say so. It is the "endpoint with no caller" bug in a third
   costume, and `tests/test_ui_contract.py` now fails on a module the entry
   point cannot reach. */
import "./reading.js";
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
