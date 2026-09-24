/* Which panel is open, and keeping that in the URL.

   The tab lives in the URL so refresh keeps the place, `#status` links work, and
   Back stays in the app. `pushState` per change, `replaceState` for the landing
   tab, and re-selecting the current tab pushes nothing, so Back never lands
   somewhere the learner did not choose. */

import {$, once} from "./core.js";
import {loadExam, loadVihikud} from "./exam.js";
import {loadDictation, loadListenLibrary} from "./listen.js";
import {loadLibrary} from "./reading.js";
import {loadPath, loadStatus, setPathMode} from "./path.js";
import {refreshDueBadge} from "./review.js";
import {loadReadAloud, loadSpeakQuestions} from "./speak.js";
import {loadVocab} from "./vocab.js";

const TABS = [...document.querySelectorAll("section.panel[id^='tab-']")]
  .map(s => s.id.slice("tab-".length));

const ON_OPEN = {
  exam: () => loadExam(),
  vihikud: () => loadVihikud(),
  path: () => loadPath(),
  review: () => refreshDueBadge(),
  status: () => loadStatus(),
  sonad: once(() => loadVocab(false)),
  // Like Sõnavara: the list is there when the tab opens; `Näita` re-filters.
  read: once(() => loadLibrary(false)),
  listen: once(() => { loadDictation(); loadListenLibrary(); }),
  speak: once(() => loadSpeakQuestions().then(() => loadReadAloud("lause"))),
};

document.querySelectorAll("nav[data-mode-nav] button[data-tab]").forEach(b => {
  const panel = document.getElementById("tab-" + b.dataset.tab);
  if (!panel) return;
  b.id = b.id || "tabbtn-" + b.dataset.tab;
  b.setAttribute("aria-controls", panel.id);
  panel.setAttribute("role", "tabpanel");
  panel.setAttribute("aria-labelledby", b.id);
});

/* The other tab lists (the modes, Minu rada / Vaba harjutus, A2 / B1) follow the
   same keyboard pattern: arrows and Home/End move and select, and only the
   selected tab is in the Tab order. */
function rove(list) {
  list.querySelectorAll('[role="tab"]').forEach(t =>
    t.tabIndex = t.getAttribute("aria-selected") === "true" ? 0 : -1);
}

document.querySelectorAll('[role="tablist"]:not(nav)').forEach(list => {
  rove(list);
  /* Selection also changes without a click (a remembered exam level, the `#drill`
     route), so the Tab order follows `aria-selected` itself. */
  new MutationObserver(() => rove(list)).observe(list, {
    subtree: true, attributes: true, attributeFilter: ["aria-selected"]});
  list.addEventListener("keydown", e => {
    const keys = ["ArrowRight", "ArrowLeft", "ArrowDown", "ArrowUp", "Home", "End"];
    if (!keys.includes(e.key)) return;
    const tabs = [...list.querySelectorAll('[role="tab"]')];
    const here = tabs.indexOf(document.activeElement);
    if (here < 0) return;
    e.preventDefault();
    const back = e.key === "ArrowLeft" || e.key === "ArrowUp";
    const next = e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1
      : back ? (here - 1 + tabs.length) % tabs.length : (here + 1) % tabs.length;
    tabs[next].focus();
    tabs[next].click();
  });
});

document.querySelectorAll("nav[data-mode-nav]").forEach(nav => {
  nav.addEventListener("keydown", e => {
    const keys = ["ArrowRight", "ArrowLeft", "Home", "End"];
    if (!keys.includes(e.key)) return;
    const tabs = [...nav.querySelectorAll("button[data-tab]")];
    const here = tabs.indexOf(document.activeElement);
    if (here < 0) return;
    e.preventDefault();
    const next = e.key === "Home" ? 0
      : e.key === "End" ? tabs.length - 1
      : e.key === "ArrowRight" ? (here + 1) % tabs.length
      : (here - 1 + tabs.length) % tabs.length;
    tabs[next].focus();
    tabs[next].click();
  });
});


/* Keep the selected tab where the learner can see it.

   On a phone the skills are a scrolling row, and a tab opened from a link or a
   reload can be off screen. Only the row is scrolled, never the page:
   `scrollIntoView` would also drag the document. At widths where the row fits
   this does nothing. */
function keepVisible(button) {
  const nav = button.closest("nav");
  if (!nav || nav.scrollWidth <= nav.clientWidth + 1) return;
  const b = button.getBoundingClientRect(), n = nav.getBoundingClientRect();
  if (b.left >= n.left && b.right <= n.right) return;
  const centred = nav.scrollLeft + (b.left - n.left) - (n.width - b.width) / 2;
  nav.scrollLeft = Math.max(0, centred);
}


export function selectTab(button) {
  button.closest("nav").querySelectorAll("button").forEach(x => {
    x.setAttribute("aria-selected", x === button);
    // Roving tabindex: only the selected tab is in the Tab order.
    x.tabIndex = x === button ? 0 : -1;
  });
  keepVisible(button);
  const tab = button.dataset.tab;
  TABS.forEach(t => $("#tab-" + t).hidden = (t !== tab));
  // Fetched when opened rather than on page load: the exam view is two
  // requests and most sessions never go near it.
  ON_OPEN[tab]?.();
}


document.querySelectorAll("nav button").forEach(
  b => b.onclick = () => { selectTab(b); rememberPlace(); });


function selectMode(m, tab) {
  // Re-tapping the current mode stays put: jumping to the mode's first tab would
  // also push a history entry the learner never chose.
  if (m.getAttribute("aria-selected") === "true") return;
  document.querySelectorAll(".modes button").forEach(x =>
    x.setAttribute("aria-selected", x === m));
  document.querySelectorAll("nav[data-mode-nav]").forEach(nav => {
    nav.hidden = nav.dataset.modeNav !== m.dataset.mode;
  });
  // Land on the tab asked for, else the mode's first, so switching never shows a
  // blank panel and a deep link does not load a panel it is about to leave.
  selectTab(tab || document.querySelector(
    `nav[data-mode-nav="${m.dataset.mode}"] button`));
  document.querySelectorAll(".modes").forEach(rove);
}


document.querySelectorAll(".modes button").forEach(
  m => m.onclick = () => { selectMode(m); rememberPlace(); });

function rememberPlace() {
  const tab = [...document.querySelectorAll("section.panel")]
    .find(s => !s.hidden)?.id.replace("tab-", "");
  if (tab && location.hash !== "#" + tab) history.pushState(null, "", "#" + tab);
}


export function goToPlace(tab) {
  /* `#drill` was the free-practice tab; it is Rada's second mode now, so an old
     bookmark still lands on the same drills. */
  if (tab === "drill") {
    const ok = goToPlace("path");
    setPathMode("vaba");
    return ok;
  }
  // `#path` itself means the path: a link to it (the rail's Harjuta) lands on Rada,
  // not on whichever mode the panel was last left in.
  if (tab === "path") setPathMode("rada");
  const button = document.querySelector(`nav[data-mode-nav] button[data-tab="${tab}"]`);
  if (!button) return false;
  const mode = button.closest("nav").dataset.modeNav;
  const modeButton = document.querySelector(`.modes button[data-mode="${mode}"]`);
  if (modeButton.getAttribute("aria-selected") === "true") selectTab(button);
  else selectMode(modeButton, button);
  return true;
}
