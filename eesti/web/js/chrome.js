/* The frame around the panels: icons, the Russian glosses, the theme.

   `RU` is the one place a tab's gloss lives. It covers every state
   `progress.TopicProgress.state` can emit. */

import {$, esc, gloss} from "./core.js";
import {BOLD, DUOTONE, icon} from "./icons.js";


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
  /* Path states: exactly the five `progress.TopicProgress.state` emits.
     `tests/test_path_states.py` checks the two lists against each other. */
  /* Each answers "can I do this now, and if not, why not?": what to press, or that
     the topic opens by itself once the named topics are done. */
  "reference": "теория", "ready": "открыто", "locked": "откроется позже",
  "in progress": "в работе", "mastered": "пройдено",
};

const STATE_ICON = {
  "reference":   "book-open",
  "ready":       "play-circle",
  "in progress": "circle-half",
  "mastered":    "check-circle",
  "locked":      "lock-simple",
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
  exam: "flower", status: "chart-line-up",
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
  ["system", "Süsteemi järgi — как в системе", "desktop"],
  ["light", "Hele teema — светлая тема", "sun"],
  ["dark", "Tume teema — тёмная тема", "moon"],
];


function currentTheme() {
  return document.documentElement.dataset.theme || "system";
}


function paintTheme() {
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

/* Less glass: the navigation layer turns solid. Safari does not report the
   system's "reduce transparency", so the switch is the app's own. */
function paintGlass() {
  const off = document.documentElement.dataset.glass === "off";
  const btn = $("#glassBtn");
  btn.innerHTML = icon("drop-half");
  btn.setAttribute("aria-pressed", String(off));
}

$("#glassBtn").onclick = () => {
  const off = document.documentElement.dataset.glass !== "off";
  if (off) document.documentElement.dataset.glass = "off";
  else delete document.documentElement.dataset.glass;
  try {
    if (off) localStorage.setItem("glass", "off");
    else localStorage.removeItem("glass");
  } catch (e) {}
  paintGlass();
};

paintGlass();

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
  review: "arrows-clockwise", repair: "wrench", refresh: "sparkle",
  skill: "target", new: "path", read: "book-open-text",
};

export function kindIcon(kind) {
  return icon(KIND_ICON[kind] || KIND_ICON.new);
}


/* ── A topic laid into the path ──────────────────────────────────────
   The one moment worth a ceremony: mastery, decided by code. A flower blooms,
   the topic is named, and the overlay leaves by itself. Announced politely, and
   instant under reduced motion (the stylesheet shortens every animation). */
export function celebrate({title, name, note}) {
  // Said through the page's one polite live region, which exists before the words
  // arrive, so a screen reader hears it; the card itself is decoration.
  const say = $("#announce");
  if (say) say.textContent = [title, name, note].filter(Boolean).join(". ");
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelector(".celebrate")?.remove();
  const box = document.createElement("div");
  box.className = "celebrate";
  box.setAttribute("aria-hidden", "true");
  box.innerHTML = `<div class="celebrate-card">
    <svg viewBox="-100 -100 200 200">
      ${ANGLES.map((a, i) => `<g transform="rotate(${a})"><path d="${PETAL}" class="petal"
        style="animation-delay:${i * 90}ms"/></g>`).join("")}
      <circle r="16" class="heart"/></svg>
    <h4 lang="et">${esc(title)}</h4>
    ${name ? `<div class="topic-name" lang="et">${esc(name)}</div>` : ""}
    ${note ? `<p>${esc(note)}</p>` : ""}
  </div>`;
  document.body.append(box);
  let gone = false;
  const leave = () => {
    if (gone) return;
    gone = true;
    removeEventListener("keydown", leave, true);
    removeEventListener("pointerdown", leave, true);
    box.classList.add("out");
    setTimeout(() => box.remove(), 260);
  };
  // Any key or touch dismisses it without being swallowed: typing goes on.
  addEventListener("keydown", leave, true);
  addEventListener("pointerdown", leave, true);
  setTimeout(leave, 3200);
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
    : `${right} из ${recent.length} верно · нужно ${gate.correct} из ${gate.window}`;
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
      const label = new Date(d.date + "T12:00:00").toLocaleDateString("ru", {day: "numeric", month: "short"});
      return `<span class="day l${lvl}" title="${esc(label)}: ${d.n}"></span>`;
    })).join("");
  // The headline counts the last four weeks: long enough to be a rhythm, short
  // enough to move when the learner comes back.
  const recent = days.slice(-28).filter(d => d.n > 0).length;
  const heads = ["E", "T", "K", "N", "R", "L", "P"]
    .map(x => `<span lang="et">${x}</span>`).join("");
  return `<div class="rhythm">
    <div class="rhythm-heads" aria-hidden="true">${heads}</div>
    <div class="rhythm-grid" role="img"
      aria-label="${esc(`Дней с занятиями за последние 4 недели: ${recent} из 28`)}">${cells}</div>
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



/* The dock steps back while reading. On a phone, scrolling down through a text or a
   list folds the three modes to their marks; scrolling up, or reaching the top,
   brings the words back — the way the system's own tab bars behave. */
{
  const phone = matchMedia("(max-width:719px), (hover:none) and (max-height:500px)");
  let last = scrollY, ticking = false;
  addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      const y = scrollY, down = y > last + 4, up = y < last - 4;
      if (!phone.matches || y < 80 || up) document.body.classList.remove("dock-min");
      else if (down) document.body.classList.add("dock-min");
      last = y;
      ticking = false;
    });
  }, {passive: true});
}
