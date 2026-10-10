/* Which panel is open, and keeping that in the URL.

   The tab lives in the URL so refresh keeps the place, `#status` links work, and
   Back stays in the app. `pushState` per change, `replaceState` for the landing
   tab, and re-selecting the current tab pushes nothing, so Back never lands
   somewhere the learner did not choose. */

import {$, once} from "./core.js";
import {ensureDictionary} from "./dictionary.js";
import {loadExam, loadVihikud} from "./exam.js";
import {loadDictation, loadListenLibrary} from "./listen.js";
import {loadLibrary} from "./reading.js";
import {loadPath, loadStatus, loadToday, setPathMode} from "./path.js";
import {ensureSession} from "./session.js";
import {ensureRule} from "./lesson.js";
import {refreshDueBadge} from "./review.js";
import {loadReadAloud, loadSpeakQuestions, loadSpeechCapabilities} from "./speak.js";
import {loadWriting} from "./write.js";
import {loadVocab} from "./vocab.js";
import {loadProfile} from "./profile.js";

const TABS = [...document.querySelectorAll("section.panel[id^='tab-']")]
  .map(s => s.id.slice("tab-".length));

const ON_OPEN = {
  exam: () => loadExam(),
  vihikud: () => loadVihikud(),
  path: () => loadToday(),
  course: () => loadPath(),
  review: () => refreshDueBadge(),
  status: () => loadStatus(),
  profile: () => loadProfile(),
  sonad: once(() => loadVocab(false)),
  // Like Sõnavara: the list is there when the tab opens; `Näita` re-filters.
  read: once(() => loadLibrary(false)),
  listen: once(() => { loadDictation(); loadListenLibrary(); }),
  speak: () => {
    loadSpeechCapabilities();
    openSpeaking();
  },
  write: () => loadWriting(),
};
const openSpeaking = once(() => loadSpeakQuestions().then(() => loadReadAloud("lause")));

document.querySelectorAll("nav[data-mode-nav] button[data-tab]").forEach(b => {
  const panel = document.getElementById("tab-" + b.dataset.tab);
  if (!panel) return;
  b.id = b.id || "tabbtn-" + b.dataset.tab;
  b.setAttribute("aria-controls", panel.id);
  panel.setAttribute("role", "tabpanel");
  panel.setAttribute("aria-labelledby", b.id);
});

/* The other tab lists (Minu rada / Vaba harjutus, A2 / B1) follow the
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
  goToPlace(button.dataset.tab);
  rememberPlace();
}


document.querySelectorAll("nav button[data-tab]").forEach(
  b => b.onclick = () => { selectTab(b); rememberPlace(); });

// A link to the page already open does not fire hashchange. Still dismiss the
// menu so its overlay cannot cover that page's controls on a phone.
document.querySelectorAll('.more-nav a').forEach(a => a.addEventListener('click', () => {
  document.querySelector('.more-nav').open = false;
}));


function rememberPlace() {
  const tab = [...document.querySelectorAll("section.panel")]
    .find(s => !s.hidden)?.id.replace("tab-", "");
  if (tab && location.hash !== "#" + tab) history.pushState(null, "", "#" + tab);
}


export function goToPlace(tab) {
  const [page, encodedTopic] = tab.split("/");
  let topic;
  try { topic = encodedTopic ? decodeURIComponent(encodedTopic) : null; }
  catch { return false; }
  tab = page;
  /* `#drill` was the free-practice tab; it is Rada's second mode now, so an old
     bookmark still lands on the same drills. */
  if (tab === "drill") {
    const ok = goToPlace("course");
    setPathMode("vaba");
    return ok;
  }
  // A Course link opens the guided syllabus; #drill still opens free practice.
  if (tab === "course") setPathMode("rada");
  if (tab === "rule" && !topic) return goToPlace("course");
  if (!TABS.includes(tab)) return false;
  const button = document.querySelector(`nav[data-mode-nav] button[data-tab="${tab}"]`);
  const changed = $("#tab-" + tab).hidden;
  document.querySelectorAll("nav[data-mode-nav] button[data-tab]").forEach(x => {
    x.setAttribute("aria-selected", String(x === button));
    x.tabIndex = x === button || !button && x.dataset.tab === "read" ? 0 : -1;
  });
  if (button) keepVisible(button);
  document.querySelectorAll('.primary-nav a, .more-nav a, #accountBtn').forEach(a => {
    if (a.hash === "#" + tab) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  TABS.forEach(t => $("#tab-" + t).hidden = (t !== tab));
  document.querySelector(".more-nav").open = false;
  if (changed) window.scrollTo({top: 0});
  ON_OPEN[tab]?.();
  if (tab === "session") ensureSession(topic);
  if (tab === "rule") ensureRule(topic);
  if (tab === "sonastik") ensureDictionary(topic);
  window.dispatchEvent(new CustomEvent("eesti:place", {detail: tab}));
  return true;
}
