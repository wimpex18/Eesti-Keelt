/* The frame around the panels: icons, the Russian glosses, the theme.

   `RU` is the one place a tab's gloss lives. It covers every state
   `progress.TopicProgress.state` can emit. */

import {$, esc, gloss} from "./core.js";


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
  // rail
  "Läbitud": "пройдено", "Järgmine": "следующая", "Kordamist ootab": "к повторению",
  /* Path states: exactly the five `progress.TopicProgress.state` emits.
     `tests/test_path_states.py` checks the two lists against each other. */
  /* Each answers "can I do this now, and if not, why not?": what to press, or that
     the topic opens by itself once the named topics are done. */
  "reference": "теория", "ready": "открыто", "locked": "откроется позже",
  "in progress": "в работе", "mastered": "пройдено",
};

const STATE_ICON = {
  "reference":   '<path d="M4 3h7a2 2 0 0 1 2 2v8H6a2 2 0 0 0-2 2z"/><path d="M4 15a2 2 0 0 1 2-2h7"/>',
  "ready":       '<circle cx="8" cy="8" r="6"/><path d="M6.5 5.5 11 8l-4.5 2.5z"/>',
  "in progress": '<circle cx="8" cy="8" r="6"/><path d="M8 4.5V8l2.5 1.5"/>',
  "mastered":    '<circle cx="8" cy="8" r="6"/><path d="m5.2 8.2 2 2 3.6-4"/>',
  "locked":      '<rect x="3.5" y="7" width="9" height="6.5" rx="1.5"/><path d="M5.75 7V5.25a2.25 2.25 0 0 1 4.5 0V7"/>',
};

function svgIcon(d) {
  return `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor"
    stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"
    aria-hidden="true">${d}</svg>`;
}

export const markIcon = svgIcon;


export function stateIcon(state) {
  const d = STATE_ICON[state];
  return d ? svgIcon(d) : "";
}

const NAV_ICON = {
  // the route
  path:    '<circle cx="6" cy="19" r="2.6"/><circle cx="18" cy="5" r="2.6"/><path d="M8.6 19h8.9a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7h8.9"/>',
  // skills -- what the exam grades
  read:    '<path d="M12 7.5v12.5"/><path d="M3 5h5a4 4 0 0 1 4 4v11a3 3 0 0 0-3-2.5H3z"/><path d="M21 5h-5a4 4 0 0 0-4 4v11a3 3 0 0 1 3-2.5h6z"/>',
  listen:  '<path d="M4 15.5V12a8 8 0 0 1 16 0v3.5"/><path d="M4 14.5h1.5a1.5 1.5 0 0 1 1.5 1.5v2.5a1.5 1.5 0 0 1-1.5 1.5H4z"/><path d="M20 14.5h-1.5a1.5 1.5 0 0 0-1.5 1.5v2.5a1.5 1.5 0 0 0 1.5 1.5H20z"/>',
  speak:   '<rect x="9.2" y="2.8" width="5.6" height="10.4" rx="2.8"/><path d="M5.6 11.2a6.4 6.4 0 0 0 12.8 0"/><path d="M12 17.6V21"/>',
  write:   '<path d="m14.8 4.6 4.6 4.6"/><path d="M17.2 2.4a2.2 2.2 0 0 1 3.1 3.1L7 19.2l-4.2 1.1L4 16.1z"/>',
  // revise
  sonad:   '<path d="m11 3 1.9 4.7L17.6 9.6l-4.7 1.9L11 16.2 9.1 11.5 4.4 9.6 9.1 7.7z"/><path d="m18.4 14.6.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z"/>',
  review:  '<path d="M20.6 11a8.6 8.6 0 1 0-2 6.4"/><path d="M21 3.6v5.2h-5.2"/>',
  vihikud: '<path d="M6.5 3H17a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6.5z"/><path d="M6.5 3v18"/><path d="M3.4 7.2h3.1M3.4 12h3.1M3.4 16.8h3.1"/><path d="M10.2 8.4h5M10.2 12.6h5"/>',
  // exam
  exam:    '<circle cx="12" cy="9" r="5.4"/><path d="m8.6 13.6-1 7.2 4.4-2.4 4.4 2.4-1-7.2"/>',
  status:  '<path d="M3.4 17.6 9.7 11.2l3.9 3.9L20.6 8"/><path d="M15.4 8h5.2v5.2"/>',
};

const MODE_ICON = {
  learn:  '<path d="M2.4 8.6 12 4.2l9.6 4.4-9.6 4.4z"/><path d="M6.2 10.8v4.1c0 1.4 2.6 2.5 5.8 2.5s5.8-1.1 5.8-2.5v-4.1"/><path d="M21.2 9.2v5.2"/>',
  revise: '<path d="M20.6 11a8.6 8.6 0 1 0-2 6.4"/><path d="M21 3.6v5.2h-5.2"/>',
  exam:   '<circle cx="12" cy="9" r="5.4"/><path d="m8.6 13.6-1 7.2 4.4-2.4 4.4 2.4-1-7.2"/>',
};

export function navIcon(d) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
    aria-hidden="true">${d}</svg>`;
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
  plus:    '<path d="M12 5.4v13.2M5.4 12h13.2"/>',
  check:   '<path d="m5 12.6 4.6 4.6L19 6.8"/>',
  ban:     '<circle cx="12" cy="12" r="8.6"/><path d="m6 6 12 12"/>',
  play:    '<path d="M8.4 5.6v12.8L18.4 12z"/>',
  record:  '<circle cx="12" cy="12" r="8.6"/><circle cx="12" cy="12" r="3.6" fill="currentColor" stroke="none"/>',
  back:    '<path d="M19 12H5.4"/><path d="m11.4 5.6-6 6.4 6 6.4"/>',
  next:    '<path d="M5 12h13.6"/><path d="m12.6 5.6 6 6.4-6 6.4"/>',
  volume:  '<path d="M4.8 9.2h3.4L13 5.2v13.6L8.2 14.8H4.8z"/><path d="M16.4 9.4a3.8 3.8 0 0 1 0 5.2"/>',
  skip:    '<path d="M6.4 5.6v12.8L15 12z"/><path d="M17.6 5.6v12.8"/>',
  note:    '<path d="M9.4 17.4V6.2l9-1.7v11.2"/><circle cx="7" cy="17.6" r="2.6"/><circle cx="16" cy="15.7" r="2.6"/>',
  send:    '<path d="M20.6 3.8 3.4 11.2l7 2.5 2.5 7z"/><path d="m10.4 13.7 10.2-9.9"/>',
  inbox:   '<path d="M5.4 5.4h13.2l2 8.2v5a1.6 1.6 0 0 1-1.6 1.6H5A1.6 1.6 0 0 1 3.4 18.6v-5z"/><path d="M3.4 13.6h4.2l1.2 2.4h6.4l1.2-2.4h4.2"/>',
  done:    '<circle cx="12" cy="12" r="8.6"/><path d="m8.4 12.3 2.6 2.6 4.7-5.4"/>',
  eye:     '<path d="M2.8 12S6.6 5.8 12 5.8 21.2 12 21.2 12 17.4 18.2 12 18.2 2.8 12 2.8 12z"/><circle cx="12" cy="12" r="3.1"/>',
  paper:   '<path d="M6.4 3.4h7.8l4 4v13.2H6.4z"/><path d="M14 3.4v4.2h4.2"/><path d="m9.2 14.4 1.9 1.9 4-4.4"/>',
};


/* A mark for a button, a heading or an empty view.

   `class="btn-ico"` is what `setLabel` looks for when it rewrites a button's
   text, so a control whose label changes ("Kuula" -> "Laen…") keeps its mark. */
export function uiIcon(name, cls = "btn-ico") {
  const d = UI_ICON[name];
  if (!d) return "";
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="1.75" stroke-linecap="round"
    stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
}


/* A skeleton while a list loads: the same layout drawn empty, so the arrival
   causes no layout shift. `rows` is what the request asked for. */
export function skeleton(rows = 6, kind = "row") {
  const one = kind === "tile"
    ? `<div class="skel-tile"><span class="skel" style="width:52%"></span>
         <span class="skel skel-sm" style="width:78%"></span></div>`
    : `<div class="skel-row"><span class="skel" style="width:62%"></span>
         <span class="skel skel-sm" style="width:34%"></span></div>`;
  return `<div class="skel-wrap${kind === "tile" ? " skel-grid" : ""}"
    aria-hidden="true">${one.repeat(rows)}</div>`;
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


/* An empty view that says what it is, why, and what to do about it: a mark, a
   statement and a next step.

   Russian throughout, including the heading: an empty view explains, and the
   learner has to be able to read it. */
export function emptyState({icon, title, note, action}) {
  return `<div class="empty-state">
    <div class="empty-mark">${uiIcon(icon, "")}</div>
    <h4>${title}</h4>
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


export function paintIcons() {
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
    if (d && slot) slot.innerHTML = navIcon(d);
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
  ["system", "Süsteemi järgi — как в системе",
   '<path d="M8.5 2.5h5a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-11a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2h2"/><path d="M6 15.5h6"/>'],
  ["light", "Hele teema — светлая тема",
   '<circle cx="9" cy="9" r="3.2"/><path d="M9 1.6v1.6M9 14.8v1.6M2.2 9H3.8M14.2 9h1.6M4.2 4.2l1.1 1.1M12.7 12.7l1.1 1.1M13.8 4.2l-1.1 1.1M5.3 12.7l-1.1 1.1"/>'],
  ["dark", "Tume teema — тёмная тема",
   '<path d="M14.2 10.6A5.8 5.8 0 0 1 7 3.5a5.9 5.9 0 1 0 7.2 7.1z"/>'],
];


function currentTheme() {
  return document.documentElement.dataset.theme || "system";
}


function paintTheme() {
  const btn = $("#themeBtn");
  if (!btn) return;
  const [, label, path] = THEMES.find(t => t[0] === currentTheme()) || THEMES[0];
  btn.innerHTML = `<svg viewBox="0 0 18 18" fill="none" stroke="currentColor"
    stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
    aria-hidden="true">${path}</svg>`;
  btn.title = label;
  btn.setAttribute("aria-label", label);
}


$("#themeBtn").onclick = () => {
  const next = THEMES[(THEMES.findIndex(t => t[0] === currentTheme()) + 1)
                      % THEMES.length][0];
  if (next === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = next;
  try {
    if (next === "system") localStorage.removeItem("theme");
    else localStorage.setItem("theme", next);
  } catch (e) {}
  paintTheme();
};

paintTheme();

$("#homeBtn").innerHTML = navIcon(
  '<path d="M3.6 10.4 12 3.8l8.4 6.6V19a1.6 1.6 0 0 1-1.6 1.6H5.2A1.6 1.6 0 0 1 3.6 19z"'
  + '/><path d="M9.4 20.6v-6.2h5.2v6.2"/>');

$("#homeBtn").onclick = () => {
  location.hash = "#path";
};

export function glossChrome() {
  document.querySelectorAll("nav[data-mode-nav] button[data-tab] .lbl")
    .forEach(el => gloss(el, RU[el.textContent.trim()]));
  document.querySelectorAll("#modes button[data-mode], .modes button[data-mode]")
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
    // The rotation sits on its own group: the petal's grow-in animation sets a CSS
    // transform, which would otherwise replace the SVG one.
    return `<g transform="rotate(${ANGLES[i]})"><g class="petal-group${unmeasured
        ? " unmeasured" : ""}" style="animation-delay:${i * 80}ms">
      <path d="${PETAL}" class="petal-shape"${unmeasured ? ` fill="url(#${hatch})"` : ""}/>
      <g clip-path="url(#${clip})">${fill}${seams}</g></g></g>`;
  }).join("");
  // Labels at the four corners, outside the petals, in the exam's order.
  const corner = [[-156, -100, "start"], [156, -100, "end"], [156, 100, "end"], [-156, 100, "start"]];
  const say = p => p.touched === null ? "не измеряется"
    : p.touched ? "есть контакт"
    : `${Math.min(target, p.contact || 0)} из ${target} · не начато`;
  const text = labels ? parts.slice(0, 4).map((p, i) => {
    const [x, y, anchor] = corner[i];
    return `<text x="${x}" y="${y}" text-anchor="${anchor}" class="petal-label" lang="et">${esc(p.et)}</text>
      <text x="${x}" y="${y + 17}" text-anchor="${anchor}" lang="ru"
        class="petal-sub${p.touched === false ? " warn" : ""}">${say(p)}</text>`;
  }).join("") : "";
  const name = parts.map(p => `${p.et}: ${say(p)}`).join("; ");
  return `<svg class="flower" viewBox="${labels ? "-160 -128 320 256" : "-96 -96 192 192"}"
      role="img" aria-label="${esc(name)}">
    <defs>
      <pattern id="${hatch}" width="6" height="6" patternUnits="userSpaceOnUse"
        patternTransform="rotate(45)"><path d="M0 0v6" class="hatch-line"/></pattern>
      <clipPath id="${clip}"><path d="${PETAL}"/></clipPath>
    </defs>
    <g>${petals}</g>
    <circle r="15" class="heart"/><circle r="6" class="heart-eye"/>
    ${text}
  </svg>`;
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
  review:  '<path d="M20.6 11a8.6 8.6 0 1 0-2 6.4"/><path d="M21 3.6v5.2h-5.2"/>',
  repair:  '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3.6 17.4a1.9 1.9 0 0 0 2.7 2.7l5.7-5.7a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.3-.3-2.4z"/>',
  refresh: '<path d="M12 3.5v4M12 16.5v4M3.5 12h4M16.5 12h4"/><circle cx="12" cy="12" r="3.2"/>',
  skill:   '<circle cx="12" cy="9" r="5.4"/><path d="m8.6 13.6-1 7.2 4.4-2.4 4.4 2.4-1-7.2"/>',
  new:     '<circle cx="6" cy="19" r="2.6"/><circle cx="18" cy="5" r="2.6"/><path d="M8.6 19h8.9a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7h8.9"/>',
  read:    '<path d="M12 7.5v12.5"/><path d="M3 5h5a4 4 0 0 1 4 4v11a3 3 0 0 0-3-2.5H3z"/><path d="M21 5h-5a4 4 0 0 0-4 4v11a3 3 0 0 1 3-2.5h6z"/>',
};

export function kindIcon(kind) {
  return navIcon(KIND_ICON[kind] || KIND_ICON.new);
}


/* ── A topic laid into the path ──────────────────────────────────────
   The one moment worth a ceremony: mastery, decided by code. A flower blooms,
   the topic is named, and the overlay leaves by itself. Announced politely, and
   instant under reduced motion (the stylesheet shortens every animation). */
export function celebrate({title, name, note}) {
  document.querySelector(".celebrate")?.remove();
  const box = document.createElement("div");
  box.className = "celebrate";
  box.setAttribute("role", "status");
  box.innerHTML = `<div class="celebrate-card">
    <svg viewBox="-100 -100 200 200" aria-hidden="true">
      ${ANGLES.map((a, i) => `<g transform="rotate(${a})"><path d="${PETAL}" class="petal"
        style="animation-delay:${i * 90}ms"/></g>`).join("")}
      <circle r="16" class="heart"/></svg>
    <h4 lang="et">${esc(title)}</h4>
    ${name ? `<div class="topic-name" lang="et">${esc(name)}</div>` : ""}
    ${note ? `<p>${esc(note)}</p>` : ""}
  </div>`;
  document.body.append(box);
  const leave = () => {
    box.classList.add("out");
    setTimeout(() => box.remove(), 260);
  };
  box.querySelector(".celebrate-card").addEventListener("click", leave);
  setTimeout(leave, 3600);
}
