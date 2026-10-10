/* The frame around the panels: the shell (sidebar, phone header, dock and
   action bar, sheets), icons, the Russian glosses, the theme.

   `RU` is the one place a tab's gloss lives. It covers every state
   `progress.TopicProgress.state` can emit. */

import {$, esc, gloss, ruCount} from "./core.js";
import {BOLD, DUOTONE, icon, skillIcon} from "./icons.js";


// ── health ──────────────────────────────────────────────────────────
/* The health payload also counts words and drillable nouns; those describe the
   dataset, not the learner, and are not shown. */
fetch("/api/health").then(r => r.ok ? r.json() : Promise.reject())
  .then(h => {
    const voice = $("#voice");
    if (voice && Array.isArray(h.voices))
      voice.innerHTML = h.voices.map(v =>
        `<option${v === "mari" ? " selected" : ""}>${esc(v)}</option>`).join("");
  })
  /* TTS remains a usable text box when its capability probe is unavailable; a failed
     health request must not become an unhandled rejection during page startup. */
  .catch(() => {});

export const RU = {
  // modes and tabs — the exam's own words, so glossed rather than replaced
  "Õppimine": "обучение", "Kordamine": "повторение", "Eksam": "экзамен",
  "Rada": "путь", "Lugemine": "чтение",
  "Sõnavara": "словарь", "Kuulamine": "аудирование",
  "Rääkimine": "говорение", "Kirjutamine": "письмо",
  "Järjekord": "очередь", "Töövihikud": "тетради",
  "Ülevaade": "обзор", "Edenemine": "прогресс",
  /* Path states: exactly those `progress.TopicProgress.state` emits.
     `tests/test_path_states.py` checks the two lists against each other. */
  /* Each answers "can I do this now, and if not, why not?": what to press, or that
     the topic opens by itself once the named topics are done. */
  "reference": "теория", "ready": "открыто", "locked": "откроется позже",
  "in progress": "в работе", "mastered": "пройдено",
  "skipped": "пропущено",
};

const STATE_ICON = {
  "reference":   "book-open",
  "ready":       "play-circle",
  "in progress": "circle-half",
  "mastered":    "check-circle",
  "locked":      "lock-simple",
  "skipped":     "arrow-right",
};

function svgIcon(d) {
  return `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor"
    stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"
    aria-hidden="true">${d}</svg>`;
}

export const markIcon = svgIcon;


export function stateIcon(state) {
  return STATE_ICON[state] ? icon(STATE_ICON[state]) : "";
}

/* Tabs and modes, by what they are: the route, the four skills, the queue, the
   words, the workbooks, the flower of the exam parts and the progress line. */
const NAV_ICON = {
  path: "path", read: "book-open-text", listen: "headphones", speak: "microphone",
  write: "pencil-simple-line", review: "cards", sonad: "translate", vihikud: "notebook",
  exam: "flower", status: "chart-line-up", profile: "user-circle",
};

const MODE_ICON = {learn: "graduation-cap", revise: "arrows-clockwise", exam: "exam"};

export function navIcon(name) {
  return icon(name);
}

/* ── The interface's own marks ───────────────────────────────────────
   Drawn icons instead of text characters (`✓`, `⊘`, `▶`, `♪`): a character is
   drawn by whatever font the platform picks, changes size and baseline between
   platforms, may fall back to another face mid-sentence, and cannot take the
   stroke weight of the icons beside it.

   Same grammar as `NAV_ICON`: a 24-unit box, one stroke weight, round caps and
   joins. Drawn here rather than pulled from a library because the app makes no
   third-party requests and caches its own shell. */
const UI_ICON = {
  plus: "plus", check: "check", ban: "prohibit", play: "play", record: "record",
  back: "arrow-left", next: "arrow-right", volume: "speaker-high", skip: "skip-forward",
  note: "music-notes", send: "paper-plane-tilt", inbox: "tray", done: "check-circle",
  eye: "eye", paper: "file-text", out: "arrow-square-out",
};


/* A mark for a button, a heading or an empty view.

   `class="btn-ico"` is what `setLabel` looks for when it rewrites a button's
   text, so a control whose label changes ("Kuula" -> "Laen…") keeps its mark. */
export function uiIcon(name, cls = "btn-ico") {
  const n = UI_ICON[name];
  if (!n) return "";
  // Small glyphs inside buttons take the bold weight; marks and empty views the duotone.
  const small = cls === "btn-ico" || cls === "inline-ico";
  const weight = (small && BOLD[n]) || !DUOTONE[n] ? "bold" : "duotone";
  return icon(n, {cls, weight});
}


/* What a slot says while its content loads: one word, shown only once the wait
   passes 400ms (the stylesheet's `.loading-note`), so a quick answer never
   flashes it. Nothing shimmers (DESIGN.md, Loading and errors). */
export function skeleton() {
  return `<p class="loading-note" role="status" lang="et">Laadin… <span class="ru" lang="ru">загружаю</span></p>`;
}


/* A row that opens something, reachable by keyboard.

   Rows hold a heading and, once opened, a player, so they cannot be `<button>`s.
   A click anywhere on `el` opens it; `handle` (the row itself unless given)
   takes the button role, is focusable, and opens on Enter or Space. A row that
   grows its own controls passes its heading as the handle: a button's contents
   are hidden from a screen reader, and the player inside must not be. */
export function actsAsButton(el, open, handle = el) {
  handle.tabIndex = 0;
  handle.setAttribute("role", "button");
  el.addEventListener("click", open);
  handle.addEventListener("keydown", e => {
    if (e.target !== handle || (e.key !== "Enter" && e.key !== " ")) return;
    e.preventDefault();
    open(e);
  });
}


/* An empty view that says what will appear and how to make it appear: a
   statement and a next step, left-aligned, no illustration.

   Russian throughout, including the heading: an empty view explains, and the
   learner has to be able to read it. */
export function emptyState({title, note, action}) {
  return `<div class="empty-state">
    <h3>${title}</h3>
    ${note ? `<p>${note}</p>` : ""}
    ${action ? `<div class="row">${action}</div>` : ""}
  </div>`;
}


/* Failed requests remain a local interruption: the rest of the screen stays useful,
   the problem is announced, and retry repeats exactly the action that failed. */
export function retryableError(message, retry) {
  const box = document.createElement("div");
  box.className = "banner recoverable-error";
  box.setAttribute("role", "alert");
  box.innerHTML = `<strong>Не удалось загрузить данные.</strong> <span>${esc(message)}</span>`;
  if (retry) {
    const button = document.createElement("button");
    button.className = "ghost";
    button.type = "button";
    button.innerHTML = `<span lang="et">${uiIcon("next")}Proovi uuesti <span class="ru" lang="ru">попробовать ещё раз</span></span>`;
    button.addEventListener("click", retry);
    box.append(button);
  }
  return box;
}


/* Buttons that live in the markup rather than in a template string.

   The page cannot call `uiIcon`, and inlining the SVG into `index.html` would put
   the drawing in two places. The id names the mark; this file draws it. */
const BUTTON_ICON = {
  dictPlay: "play", dictNext: "skip", dictCheck: "check",
  recBtn: "record", speakPlay: "volume", speakNext: "skip",
  backToLib: "back", speakBtn: "volume", loadReview: "play",
  queueSend: "send", checkBtn: "check", practiceBtn: "play",
  freeBtn: "play", checkpointBtn: "paper", loadLib: "eye",
  vocBtn: "eye", vocMoreBtn: "plus", libMoreBtn: "plus",
};


/* The rail's marks for the main pages (on a wide desktop they show as words). */
const PAGE_ICON = {path: "house-simple", course: "path", review: "cards", exam: "exam"};

/* The skills key: the four skills' colours in one 2×2 mark, the way the sheet it
   opens holds them. */
const SKILLS_KEY = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
  <rect class="skill-read" x="3" y="3" width="8" height="8" rx="2"/><rect class="skill-listen" x="13" y="3" width="8" height="8" rx="2"/>
  <rect class="skill-speak" x="3" y="13" width="8" height="8" rx="2"/><rect class="skill-write" x="13" y="13" width="8" height="8" rx="2"/></svg>`;

export function paintIcons() {
  document.querySelectorAll(".primary-nav a[href^='#']").forEach(a => {
    const name = PAGE_ICON[a.hash.slice(1)];
    if (!name || a.querySelector(".ico")) return;
    a.insertAdjacentHTML("afterbegin", `<span class="ico" aria-hidden="true">${navIcon(name)}</span>`);
  });
  const home = $(".dock-home .ico");
  if (home && !home.firstChild) home.innerHTML = navIcon(PAGE_ICON.path);
  document.querySelectorAll(".sheet-nav a[data-skill]").forEach(a => {
    if (!a.querySelector("svg")) a.insertAdjacentHTML("afterbegin", skillIcon(a.dataset.skill));
  });
  document.querySelectorAll(".sheet-close").forEach(b => { if (!b.firstChild) b.innerHTML = icon("x", {weight: "bold"}); });
  const key = $("#skillsKey");
  if (key && !key.firstChild) key.innerHTML = SKILLS_KEY;
  for (const [id, name] of Object.entries(BUTTON_ICON)) {
    const b = document.getElementById(id);
    // `insertAdjacentHTML` rather than `innerHTML =`: these buttons carry a
    // Russian gloss already, and rewriting the contents would drop it.
    if (b && !b.querySelector(".btn-ico"))
      b.insertAdjacentHTML("afterbegin", uiIcon(name));
  }
  document.querySelectorAll("nav[data-mode-nav] button[data-tab]").forEach(b => {
    const d = NAV_ICON[b.dataset.tab];
    const slot = b.querySelector(".ico");
    if (d && slot) slot.innerHTML = skillIcon(b.dataset.tab) || navIcon(d);
    /* A name that does not depend on the label being painted.

       Between 720 and 1079px the skills are a rail of marks and `.lbl` is
       `display:none`, which removes the text from the accessibility tree. `title`
       serves a pointer, `aria-label` everything else; both are set at every width. */
    const label = b.querySelector(".lbl");
    const name = label && label.textContent.trim();
    if (name) {
      const ru = RU[name];
      const full = ru ? `${name} — ${ru}` : name;
      b.title = full;
      b.setAttribute("aria-label", full);
    }
  });
  document.querySelectorAll(".modes button[data-mode]").forEach(b => {
    // Named like the skill tabs: label, dash, gloss.
    const et = b.firstChild && b.firstChild.nodeType === 3 ? b.firstChild.textContent.trim() : "";
    if (et && RU[et]) b.setAttribute("aria-label", `${et} — ${RU[et]}`);
    if (b.querySelector(".ico")) return;
    const d = MODE_ICON[b.dataset.mode];
    if (!d) return;
    const span = document.createElement("span");
    span.className = "ico";
    span.setAttribute("aria-hidden", "true");
    span.innerHTML = navIcon(d);
    b.prepend(span);
  });
}

const THEMES = [
  ["system", "Süsteemi järgi — как в системе", "desktop"],
  ["light", "Hele teema — светлая тема", "sun"],
  ["dark", "Tume teema — тёмная тема", "moon"],
];


function currentTheme() {
  return document.documentElement.dataset.theme || "system";
}


function paintTheme() {
  document.querySelectorAll("[data-theme-choice]").forEach(b =>
    b.setAttribute("aria-pressed", String(b.dataset.themeChoice === currentTheme())));
  const btn = $("#themeBtn");
  if (!btn) return;
  const [, label, name] = THEMES.find(t => t[0] === currentTheme()) || THEMES[0];
  btn.innerHTML = icon(name);
  // The browser's own chrome follows the theme the learner chose, not only the
  // system's: one theme-color, set to the page's background.
  requestAnimationFrame(() => {
    const bg = getComputedStyle(document.body).backgroundColor;
    document.querySelectorAll('meta[name="theme-color"]').forEach(m => {
      m.dataset.system ??= m.content;
      m.content = currentTheme() === "system" ? m.dataset.system : bg;
    });
  });
  btn.title = label;
  btn.setAttribute("aria-label", label);
}


function setTheme(next) {
  if (next === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = next;
  try {
    if (next === "system") localStorage.removeItem("theme");
    else localStorage.setItem("theme", next);
  } catch (e) {}
  paintTheme();
}

/* The sidebar's one button steps through the three; Veel's switch names them. */
$("#themeBtn").onclick = () => setTheme(
  THEMES[(THEMES.findIndex(t => t[0] === currentTheme()) + 1) % THEMES.length][0]);
document.querySelectorAll("[data-theme-choice]").forEach(b =>
  b.addEventListener("click", () => setTheme(b.dataset.themeChoice)));

paintTheme();

/* ── The shell ───────────────────────────────────────────────────────
   One header serves both devices (the stylesheet places it): the sidebar on a
   desktop; on a phone the header, its tab row as the dock along the bottom, and
   the action bar above it. This keeps three facts current and publishes them:

   1. the open screen's primary: its first rendered `[data-primary]` button,
      marked `.dock-primary` and set in the action bar (`body.has-primary`);
   2. whether the dock is in its task state (`body.dock-task`): the screen holds
      a rendered `[data-dock-task]` (an item awaiting its answer), or the
      on-screen keyboard is up (`body.kb`, `--kb`) — a text field has focus and
      the visual viewport has given way to something below it. The tab row then
      steps aside, the skills wait behind the skills key, and the primary rides
      on the keyboard;
   3. how tall the dock is (`--tabs-h`, `--dock-h`), which the page's end and
      every focus scroll keep clear of.

   And it keeps focus in sight: a focused element is moved out from under the
   header, the dock, the action bar and the keyboard (WCAG 2.4.12). */
const PHONE = matchMedia("(max-width:719px), (hover:none) and (max-height:559px)");
const TEXT_FIELD = "input:not([type]),input[type=text],input[type=search],input[type=email]," +
  "input[type=password],input[type=number],input[type=tel],input[type=url],textarea,[contenteditable='true']";
const docEl = document.documentElement;

const rendered = el => el.checkVisibility ? el.checkVisibility() : el.getClientRects().length > 0;

const openPanel = () => document.querySelector("main > section.panel:not([hidden])");

function screenPrimary() {
  const panel = openPanel();
  return panel && [...panel.querySelectorAll("[data-primary]")].find(b => !b.hidden && rendered(b)) || null;
}

/* The keyboard, read off the visual viewport: Safari keeps a full-height layout
   viewport and shrinks the visual one. How much it shrank says whether a
   keyboard is up; how much of the layout viewport lies below it says where the
   keyboard starts (0 while Safari has panned to the bottom, which it does as the
   keyboard slides in). Pinch zoom also shrinks it, and is no keyboard. Read
   afresh each time, so a replaced `visualViewport` is honoured. */
function keyboardGap() {
  const v = window.visualViewport;
  if (!v || Math.abs((v.scale ?? 1) - 1) > .01) return {shrunk: 0, below: 0};
  return {shrunk: innerHeight - v.height, below: Math.max(0, Math.round(innerHeight - v.height - v.offsetTop))};
}

let frame = 0, watched = null, keyboardWas = false, settling = 0;
function soon() { if (!frame) frame = requestAnimationFrame(syncShell); }

function watchViewport() {
  const v = window.visualViewport;
  if (!v || v === watched) return;
  watched?.removeEventListener("resize", soon);
  watched?.removeEventListener("scroll", soon);
  watched = v;
  v.addEventListener("resize", soon);
  v.addEventListener("scroll", soon);
}

function syncShell() {
  frame = 0;
  watchViewport();
  const phone = PHONE.matches, body = document.body;
  const primary = phone ? screenPrimary() : null;
  document.querySelectorAll(".dock-primary").forEach(b => b !== primary && b.classList.remove("dock-primary"));
  primary?.classList.add("dock-primary");
  const typing = phone && document.activeElement?.matches?.(TEXT_FIELD);
  const gap = typing ? keyboardGap() : {shrunk: 0, below: 0};
  const keyboard = gap.shrunk > 120;
  const height = window.visualViewport?.height ?? innerHeight;
  const task = phone && [...(openPanel()?.querySelectorAll("[data-dock-task]") || [])].some(rendered);
  body.classList.toggle("has-primary", !!primary);
  body.classList.toggle("dock-task", keyboard || task);
  body.classList.toggle("kb", keyboard);
  body.classList.toggle("kb-compact", keyboard && height < 320);
  docEl.style.setProperty("--kb", `${keyboard ? gap.below : 0}px`);
  const tabs = phone && !(keyboard || task) ? Math.round($(".dock-tabs").getBoundingClientRect().height) : 0;
  const bar = primary ? Math.round($("#actbar").getBoundingClientRect().height) : 0;
  docEl.style.setProperty("--tabs-h", `${tabs}px`);
  docEl.style.setProperty("--dock-h", `${tabs + bar}px`);
  // What is left for the field being typed in, which a compact keyboard state
  // caps a multi-line field at.
  const header = getComputedStyle($(".spine")).position === "sticky" ? $(".spine").offsetHeight : 0;
  docEl.style.setProperty("--band", `${Math.max(0, Math.round(height - header - bar - 16))}px`);
  /* A phone raises its keyboard after the field takes focus, and then scrolls the
     page its own way while the keyboard slides in: the task row lands on the
     keyboard and can cover the field. For a moment after the keyboard arrives,
     each change of the visual viewport puts the field back in sight; after that
     the learner's own scrolling is left alone. */
  if (keyboard && !keyboardWas) settling = performance.now() + 1000;
  keyboardWas = keyboard;
  if (keyboard && performance.now() < settling) keepInSightWhenStill();
}

/* The band a focused element must sit in: below the visible top (the sticky
   header, or the top of the visual viewport) and above whatever is fixed at the
   bottom (tab row, action bar, primary) or the keyboard. */
function clearBand() {
  const v = window.visualViewport;
  let top = v ? v.offsetTop : 0, bottom = v ? v.offsetTop + v.height : innerHeight;
  const header = $(".spine");
  if (getComputedStyle(header).position === "sticky") top = Math.max(top, header.getBoundingClientRect().bottom);
  for (const el of [$(".dock-tabs"), $("#actbar"), $(".dock-primary")]) {
    if (!el || !rendered(el) || getComputedStyle(el).position !== "fixed") continue;
    bottom = Math.min(bottom, el.getBoundingClientRect().top);
  }
  return {top, bottom};
}

function keepInSight(el) {
  if (el !== document.activeElement || !PHONE.matches) return;
  // The chrome itself, and anything in an open sheet, is never under the chrome.
  if (el.closest(".spine, #actbar, dialog, .dock-primary")) return;
  const r = el.getBoundingClientRect(), {top, bottom} = clearBand(), gap = 8;
  if (!r.height) return;
  const below = r.bottom + gap - bottom, above = top + gap - r.top;
  // Too tall for the band: its start matters more than its end.
  const by = above > 0 ? -above : below > 0 ? Math.min(below, r.top - top - gap) : 0;
  if (by) window.scrollBy({top: by, behavior: "instant"});
}

/* Measured only once the page has stopped moving: a screen often focuses its
   field while its own smooth scroll is still travelling, and Safari scrolls to a
   field it focuses; a correction added to a scroll in flight overshoots it. The
   wait also lets the dock take its new state first. */
let stillRun = 0;
function keepInSightWhenStill() {
  const run = ++stillRun;
  let last = "", still = 0, frames = 0;
  const tick = () => {
    if (run !== stillRun) return;
    const v = window.visualViewport;
    const now = `${scrollY}|${v ? `${v.offsetTop}|${v.height}` : ""}`;
    still = now === last ? still + 1 : 0;
    last = now;
    if (still >= 3 || ++frames > 90) keepInSight(document.activeElement);
    else requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

addEventListener("focusin", () => {
  soon();
  keepInSightWhenStill();
});
addEventListener("focusout", soon);
addEventListener("resize", soon);
addEventListener("eesti:place", soon);
PHONE.addEventListener("change", soon);
new ResizeObserver(soon).observe($(".dock-tabs"));
new ResizeObserver(soon).observe($("#actbar"));
/* A screen shows, hides or replaces its primary as its state changes; and text
   arriving above a field the learner is typing in (a status line, a hint) moves
   the field, which goes back into sight. */
new MutationObserver(() => {
  soon();
  if (document.body.classList.contains("kb")) keepInSightWhenStill();
}).observe($("main"), {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["hidden"]});
soon();

/* Where the learner is, said by the dock's Täna and the skills sheet as well as
   the sidebar (the router marks the sidebar and Veel). */
addEventListener("eesti:place", e => {
  const here = e.detail;
  const home = $(".dock-home");
  if (here === "path") home.setAttribute("aria-current", "page");
  else home.removeAttribute("aria-current");
  document.querySelectorAll("#skillsSheet a[data-skill]").forEach(a => {
    if (a.dataset.skill === here) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
});


/* ── Sheets ──────────────────────────────────────────────────────────
   Veel and the skills open as modal sheets: focus is held inside, Escape, the
   close button or a tap on the scrim closes, and focus returns to the opener.
   Veel lives in a `<details>` so its summary is the opener the page already had;
   the details' open state and the sheet's follow each other. */
function openSheet(sheet, opener) {
  if (sheet.open) return;
  sheet.opener = opener;
  sheet.showModal();
  (sheet.querySelector(".sheet-nav a[aria-current]") || sheet.querySelector(".sheet-nav a:not(.in-sidebar)")
    || sheet.querySelector(".sheet-nav a"))?.focus({preventScroll: true});
}

document.querySelectorAll("dialog.sheet").forEach(sheet => {
  sheet.querySelector(".sheet-close")?.addEventListener("click", () => sheet.close());
  sheet.addEventListener("click", e => {
    if (e.target.closest(".sheet-nav a")) { sheet.close(); return; }
    if (e.target !== sheet) return;
    const r = sheet.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) sheet.close();
  });
  sheet.addEventListener("close", () => {
    const opener = sheet.opener;
    sheet.opener = null;
    if (opener && rendered(opener)) opener.focus({preventScroll: true});
  });
});

const veel = $(".more-nav"), veelSheet = $("#veelSheet");
veel.addEventListener("toggle", () => {
  if (veel.open) openSheet(veelSheet, veel.querySelector("summary"));
  else if (veelSheet.open) veelSheet.close();
});
veelSheet.addEventListener("close", () => { veel.open = false; });
$("#skillsKey").addEventListener("click", () => openSheet($("#skillsSheet"), $("#skillsKey")));


export function glossChrome() {
  document.querySelectorAll("nav[data-mode-nav] button[data-tab] .lbl")
    .forEach(el => gloss(el, RU[el.textContent.trim()]));
  document.querySelectorAll(".modes button[data-mode]")
    .forEach(el => gloss(el, RU[el.textContent.trim()]));
}


/* ── Rukkilill: the four exam parts as one flower ───────────────────
   Each petal is a part, in the exam's own order; its three segments light up one
   contact at a time towards `contact_target` (`eesti/readiness.py`). A part the
   app cannot measure (Rääkimine) is hatched, never empty: "cannot tell" is not
   "none". A flower missing a petal is visibly incomplete, which is the exam's own
   rule — no part may be zero — drawn rather than stated. */
const PETAL = "M0 -12C-18 -26 -26 -48 -20 -70L-14 -84-7 -74 0 -90 7 -74 14 -84 20 -70C26 -48 18 -26 0 -12Z";
const ANGLES = [-45, 45, 135, 225];
let flowerSeq = 0;

export function flowerSvg(parts, target = 3, {labels = true} = {}) {
  const n = ++flowerSeq, hatch = `hatch${n}`, clip = `petal${n}`;
  // Segments from the heart outwards; the petal's own outline clips them.
  const bands = [[-12, -36], [-36, -60], [-60, -92]];
  const petals = parts.slice(0, 4).map((p, i) => {
    const unmeasured = p.touched === null;
    const got = unmeasured ? 0 : Math.min(target, p.contact ?? (p.touched ? target : 0));
    const lit = Math.round(got / target * bands.length);
    const fill = bands.slice(0, lit).map(([y0, y1]) =>
      `<rect x="-30" y="${y1}" width="60" height="${y0 - y1}" class="petal-fill"/>`).join("");
    const seams = lit ? [-36, -60].map(y =>
      `<line x1="-30" x2="30" y1="${y}" y2="${y}" class="petal-seam"/>`).join("") : "";
    return `<g transform="rotate(${ANGLES[i]})"><g class="petal-group${unmeasured
        ? " unmeasured" : ""}">
      <path d="${PETAL}" class="petal-shape"${unmeasured ? ` fill="url(#${hatch})"` : ""}/>
      <g clip-path="url(#${clip})">${fill}${seams}</g></g></g>`;
  }).join("");
  // Labels sit outside the SVG as HTML text so they keep the app's type sizes
  // however small the flower is drawn; the grid places them at the four corners.
  const say = p => p.touched === null ? "не измеряется"
    : p.touched ? "есть контакт"
    : `${Math.min(target, p.contact || 0)} из ${target}, не начато`;
  const name = parts.map(p => `${p.et}: ${say(p)}`).join("; ");
  const svg = `<svg class="flower" viewBox="-96 -96 192 192"
      role="img" aria-label="${esc(name)}">
    <defs>
      <pattern id="${hatch}" width="6" height="6" patternUnits="userSpaceOnUse"
        patternTransform="rotate(45)"><path d="M0 0v6" class="hatch-line"/></pattern>
      <clipPath id="${clip}"><path d="${PETAL}"/></clipPath>
    </defs>
    <g>${petals}</g>
    <circle r="15" class="heart"/><circle r="6" class="heart-eye"/>
  </svg>`;
  if (!labels) return svg;
  const corner = ["tl", "tr", "br", "bl"];
  const text = parts.slice(0, 4).map((p, i) => `<div class="petal-note ${corner[i]}" aria-hidden="true">
      <span class="petal-label" lang="et">${esc(p.et)}</span>
      <span class="petal-sub${p.touched === false ? " warn" : ""}" lang="ru">${say(p)}</span></div>`).join("");
  return `<div class="flower-wrap">${svg}${text}</div>`;
}


/* ── Milestones as seals ─────────────────────────────────────────────
   Four level-specific markers (`eesti/milestones.py`). A seal fills its ring as
   the count grows and is struck in cornflower when complete. They award nothing;
   they mark what already happened. */
const SEAL_GLYPH = {
  "first-practice": '<path d="M23 38c-3-3-4-8-3-13s4-8 7-8 5 4 4 9-3 8-8 12z"/><circle cx="33" cy="17" r="1.6"/><circle cx="36.5" cy="21" r="1.4"/><circle cx="38" cy="25.5" r="1.2"/>',
  "first-topic":    '<path d="M16 32h24M16 26h24M16 20h24"/>',
  "checkpoint":     '<path d="M20 18h16v22H20z"/><path d="m23.5 29 3 3 6-6"/>',
  "four-parts":     '<path d="M28 28c-3-4-4-8-2-12 3 1 4 5 2 12zm0 0c4-3 8-4 12-2-1 3-5 4-12 2zm0 0c3 4 4 8 2 12-3-1-4-5-2-12zm0 0c-4 3-8 4-12 2 1-3 5-4 12-2z"/>',
};

export function sealsHtml(milestones) {
  const C = 2 * Math.PI * 25;
  return `<div class="seals">${milestones.map(m => {
    const share = Math.max(0, Math.min(1, m.target ? m.current / m.target : 0));
    return `<div class="seal${m.complete ? " done" : ""}" title="${esc(m.ru)}">
      <svg viewBox="0 0 56 56" aria-hidden="true">
        <circle cx="28" cy="28" r="25" class="disc"/>
        <circle cx="28" cy="28" r="25" class="ring-bg"/>
        ${m.complete ? "" : `<circle cx="28" cy="28" r="25" class="ring-fg"
          stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${(C * (1 - share)).toFixed(1)}"/>`}
        <g class="glyph">${SEAL_GLYPH[m.id] || '<circle cx="28" cy="28" r="4"/>'}</g>
      </svg>
      <b lang="et">${esc(m.et)}</b>
      <span lang="ru">${m.complete ? "есть" : `${m.current}/${m.target}`}</span>
    </div>`;
  }).join("")}</div>`;
}


/* ── The kinds of block in today's plan, each with its own mark ────── */
const KIND_ICON = {
  review: "arrows-clockwise", repair: "wrench", refresh: "sparkle",
  skill: "target", new: "path", read: "book-open-text",
};

export function kindIcon(kind) {
  return icon(KIND_ICON[kind] || KIND_ICON.new);
}


/* ── A topic laid into the path ──────────────────────────────────────
   Mastery, decided by code, is said once through the page's polite live region.
   Nothing is drawn over the page: no overlay, no petals (DESIGN.md, Motion). */
export function celebrate({title, name, note}) {
  const say = $("#announce");
  if (say) say.textContent = [title, name, note].filter(Boolean).join(". ");
}


/* ── Charts drawn from time ──────────────────────────────────────────
   Three small graphics, each answering one question at a glance. */

/* The gate: the resume topic's last answers against the rule that masters it
   (`progress.MASTERY_CORRECT` of `MASTERY_WINDOW`). Ten slots, filled oldest
   first; the count to go is said in words beside it. */
export function gateHtml(recent = [], gate = {correct: 8, window: 10}) {
  const slots = Array.from({length: gate.window}, (_, i) => {
    const r = recent[i];
    return `<span class="slot${r === true ? " ok" : r === false ? " no" : ""}"></span>`;
  }).join("");
  const right = recent.filter(Boolean).length;
  const say = !recent.length
    ? `тема засчитывается при ${gate.correct} верных из ${gate.window}`
    : `${right} из ${recent.length} верно; нужно ${gate.correct} из ${gate.window}`;
  return `<div class="gate" role="img" aria-label="${esc(say)}">
    <div class="slots" aria-hidden="true">${slots}</div>
    <span class="gate-say" aria-hidden="true">${esc(say)}</span></div>`;
}


/* The rhythm: practice per day over five weeks, Monday first. A day with nothing
   is simply light; nothing resets and nothing is lost. */
export function rhythmHtml(days = []) {
  if (!days.length) return "";
  const lead = (new Date(days[0].date + "T12:00:00").getDay() + 6) % 7;
  const cells = Array.from({length: lead}, () => `<span class="day pad"></span>`)
    .concat(days.map(d => {
      const lvl = d.n === 0 ? 0 : d.n < 5 ? 1 : d.n < 15 ? 2 : d.n < 40 ? 3 : 4;
      const date = new Date(d.date + "T12:00:00");
      const label = date.toLocaleDateString("ru", {day: "numeric", month: "short"});
      const accessibleDate = date.toLocaleDateString("ru", {
        weekday: "long", day: "numeric", month: "long",
      });
      const amount = ruCount(d.n, ["упражнение", "упражнения", "упражнений"]);
      return `<span class="day l${lvl}" role="img"
        aria-label="${esc(`${accessibleDate}: ${amount}`)}"
        title="${esc(label)}: ${d.n}"></span>`;
    })).join("");
  // The headline counts the last four weeks: long enough to be a rhythm, short
  // enough to move when the learner comes back.
  const recent = days.slice(-28).filter(d => d.n > 0).length;
  const heads = ["E", "T", "K", "N", "R", "L", "P"]
    .map(x => `<span lang="et">${x}</span>`).join("");
  return `<div class="rhythm">
    <div class="rhythm-heads" aria-hidden="true">${heads}</div>
    <div class="rhythm-grid" role="group"
      aria-label="${esc(`Дни занятий за 12 недель. Последние 4 недели: ${recent} из 28 дней с занятиями.`)}">${cells}</div>
    <div class="rhythm-say"><b>${recent}</b> из 28 дней с занятиями за 4 недели</div></div>`;
}


/* The forecast: cards coming due over the next seven days, today first. */
export function forecastHtml(counts = []) {
  if (!counts.length) return "";
  const top = Math.max(1, ...counts);
  const bars = counts.map((n, i) => {
    const day = new Date(Date.now() + i * 864e5);
    const when = i === 0 ? "сег." : String(day.getDate());
    const full = day.toLocaleDateString("ru", {weekday: "short", day: "numeric", month: "short"});
    return `<div class="fc-bar${i === 0 ? " now" : ""}" title="${esc(full)}: ${n}">
      <span class="fc-n">${n || ""}</span>
      <span class="fc-col" style="--h:${n ? Math.max(6, n / top * 100) : 0}%"></span>
      <span class="fc-day">${esc(when)}</span></div>`;
  }).join("");
  const total = counts.reduce((a, b) => a + b, 0);
  return `<div class="forecast" style="grid-template-columns:repeat(${counts.length},minmax(0,1fr))"
    role="img" aria-label="${esc(`К повторению за ${counts.length} дней: ${total}; сегодня ${counts[0]}`)}">${bars}</div>`;
}
