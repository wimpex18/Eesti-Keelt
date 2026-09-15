/* Which panel is open, and keeping that in the URL.

   The tab lives in the URL so refresh keeps the place, `#status` links work, and
   Back stays in the app. `pushState` per change, `replaceState` for the landing
   tab, and re-selecting the current tab pushes nothing, so Back never lands
   somewhere the learner did not choose. */

import {$, once} from "./core.js";
import {loadExam, loadVihikud} from "./exam.js";
import {loadDictation, loadListenLibrary} from "./listen.js";
import {loadPath, loadStatus} from "./path.js";
import {loadReadAloud, loadSpeakQuestions} from "./speak.js";
import {loadVocab} from "./vocab.js";

const TABS = [...document.querySelectorAll("section.panel[id^='tab-']")]
  .map(s => s.id.slice("tab-".length));

const ON_OPEN = {
  exam: () => loadExam(),
  vihikud: () => loadVihikud(),
  path: () => loadPath(),
  status: () => loadStatus(),
  sonad: once(() => loadVocab(false)),
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


function selectMode(m) {
  // Re-tapping the current mode stays put: jumping to the mode's first tab would
  // also push a history entry the learner never chose.
  if (m.getAttribute("aria-selected") === "true") return;
  document.querySelectorAll(".modes button").forEach(x =>
    x.setAttribute("aria-selected", x === m));
  document.querySelectorAll("nav[data-mode-nav]").forEach(nav => {
    nav.hidden = nav.dataset.modeNav !== m.dataset.mode;
  });
  // Land on the mode's first tab, so switching never shows a blank panel.
  selectTab(document.querySelector(
    `nav[data-mode-nav="${m.dataset.mode}"] button`));
}


document.querySelectorAll(".modes button").forEach(
  m => m.onclick = () => { selectMode(m); rememberPlace(); });

function rememberPlace() {
  const tab = [...document.querySelectorAll("section.panel")]
    .find(s => !s.hidden)?.id.replace("tab-", "");
  if (tab && location.hash !== "#" + tab) history.pushState(null, "", "#" + tab);
}


export function goToPlace(tab) {
  const button = document.querySelector(`nav[data-mode-nav] button[data-tab="${tab}"]`);
  if (!button) return false;
  const mode = button.closest("nav").dataset.modeNav;
  selectMode(document.querySelector(`.modes button[data-mode="${mode}"]`));
  selectTab(button);
  return true;
}
