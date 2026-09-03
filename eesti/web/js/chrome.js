/* The frame around the panels: icons, the Russian glosses, the theme.

   `RU` is the one place a tab's gloss lives, so a tab added later gets one by
   being in the map rather than by somebody remembering. It covers every state
   `progress.TopicProgress.state` can emit, including the two that only appear
   after you finish something -- they reached the screen as raw English for
   months because the earlier fix glossed what was visible on a screenshot. */

import {$, gloss} from "./core.js";


// ── health ──────────────────────────────────────────────────────────
fetch("/api/health").then(r => r.json()).then(h => {
  $("#stats").textContent =
    `${h.words.toLocaleString("ru")} слов · ${h.drillable_nouns.toLocaleString("ru")} существительных для упражнений`;
  $("#voice").innerHTML = h.voices.map(v => `<option${v === "mari" ? " selected" : ""}>${v}</option>`).join("");
});

export const RU = {
  // modes and tabs — the exam's own words, so glossed rather than replaced
  "Õppimine": "обучение", "Kordamine": "повторение", "Eksam": "экзамен",
  "Rada": "путь", "Harjutused": "упражнения", "Lugemine": "чтение",
  "Sõnavara": "словарь", "Kuulamine": "аудирование",
  "Rääkimine": "говорение", "Kirjutamine": "письмо",
  "Järjekord": "очередь", "Töövihikud": "тетради",
  "Ülevaade": "обзор", "Edenemine": "прогресс",
  // rail
  "Eksamini": "до экзамена", "Puudutamata": "не начато",
  "Läbitud": "пройдено", "Järgmine": "следующая", "Kordamist ootab": "к повторению",
  /* Path states. These were English, and glossing them was a previous fix --
     which glossed the three that were on screen at the time and missed the
     two that only appear once the learner has actually done something.
     `progress.TopicProgress.state` emits exactly five, and `done` and
     `review` were never among them: a topic that had been mastered rendered
     the raw word `mastered`, and one in flight rendered `in progress`.
     `tests/test_path_states.py` now checks the two lists against each
     other in both directions. */
  /* Each answers "can I do this now, and if not, why not?". The first set
     answered a different question and two of them answered none: `можно` said
     permission where the learner wanted to know what to press, and `закрыто`
     said a door was shut without saying that it opens by itself once the
     topics it names are done. `справка` read as a help page rather than as a
     rule with no exercises behind it. */
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
  drill:   '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/>',
  read:    '<path d="M12 7.5v12.5"/><path d="M3 5h5a4 4 0 0 1 4 4v11a3 3 0 0 0-3-2.5H3z"/><path d="M21 5h-5a4 4 0 0 0-4 4v11a3 3 0 0 1 3-2.5h6z"/>',
  sonad:   '<path d="m11 3 1.9 4.7L17.6 9.6l-4.7 1.9L11 16.2 9.1 11.5 4.4 9.6 9.1 7.7z"/><path d="m18.4 14.6.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z"/>',
  listen:  '<path d="M4 15.5V12a8 8 0 0 1 16 0v3.5"/><path d="M4 14.5h1.5a1.5 1.5 0 0 1 1.5 1.5v2.5a1.5 1.5 0 0 1-1.5 1.5H4z"/><path d="M20 14.5h-1.5a1.5 1.5 0 0 0-1.5 1.5v2.5a1.5 1.5 0 0 0 1.5 1.5H20z"/>',
  speak:   '<rect x="9.2" y="2.8" width="5.6" height="10.4" rx="2.8"/><path d="M5.6 11.2a6.4 6.4 0 0 0 12.8 0"/><path d="M12 17.6V21"/>',
  write:   '<path d="m14.8 4.6 4.6 4.6"/><path d="M17.2 2.4a2.2 2.2 0 0 1 3.1 3.1L7 19.2l-4.2 1.1L4 16.1z"/>',
  // revise
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

const GROUP_ICON = {
  skills: '<circle cx="12" cy="12" r="8.6"/><path d="m15.6 8.4-2.1 5.1-5.1 2.1 2.1-5.1z"/>',
  modes:  '<path d="M3.6 7.2h9.2M17.6 7.2h2.8M3.6 16.8h3.4M11.8 16.8h8.6"/><circle cx="15.2" cy="7.2" r="2.2"/><circle cx="9.2" cy="16.8" r="2.2"/>',
};


export function navIcon(d) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
    aria-hidden="true">${d}</svg>`;
}

/* ── The interface's own marks ───────────────────────────────────────
   The navigation has had drawn icons since it was built; everything else in
   the app used a text character where it wanted a mark -- `✓ Tean seda sõna`,
   `⊘ Pole vaja`, `▶ Kuula`, `● Salvesta vastus`, `← Nimekirja`, `· ♪`.

   A character is not an icon. It is drawn by whichever font the platform
   picks, so it changes size, weight and baseline between Android, iOS and a
   desktop browser; `⊘` and `♪` are not in every system face at all and fall
   back to a different one mid-sentence. They cannot take the stroke weight of
   the icons beside them, and they cannot be sized in the stylesheet.

   Same grammar as `NAV_ICON`, which is also the grammar every mainstream
   icon set converged on: a 24-unit box, one stroke weight, round caps and
   joins. Drawn here rather than pulled from a library because this app ships
   no third-party requests and caches its own shell -- an icon font or a CDN
   sprite would be both. */
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
  download:'<path d="M12 3.6v10.8"/><path d="m7.6 10.4 4.4 4.4 4.4-4.4"/><path d="M4.6 17.4v1.4a1.6 1.6 0 0 0 1.6 1.6h11.6a1.6 1.6 0 0 0 1.6-1.6v-1.4"/>',
  paper:   '<path d="M6.4 3.4h7.8l4 4v13.2H6.4z"/><path d="M14 3.4v4.2h4.2"/><path d="m9.2 14.4 1.9 1.9 4-4.4"/>',
};


/* A mark for a button, a heading or an empty view.

   `class="btn-ico"` is what `setLabel` looks for when it rewrites a button's
   text, so a control whose label changes ("Kuula" -> "Laen…") keeps its mark.
*/
export function uiIcon(name, cls = "btn-ico") {
  const d = UI_ICON[name];
  if (!d) return "";
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="1.75" stroke-linecap="round"
    stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
}


/* The shape of the answer, while the answer is on its way.

   Both big lists used to say nothing at all: the reading list emptied itself
   and waited, and the vocabulary grid printed `загружаю…` in grey. Neither
   tells the eye where to be, and the moment the rows arrive the page jumps by
   whatever height they turned out to need.

   A skeleton is not decoration -- it is the same layout, drawn empty, so the
   arrival costs no movement. `rows` is what the request actually asked for,
   so twelve requested words leave room for twelve.
*/
export function skeleton(rows = 6, kind = "row") {
  const one = kind === "tile"
    ? `<div class="skel-tile"><span class="skel" style="width:52%"></span>
         <span class="skel skel-sm" style="width:78%"></span></div>`
    : `<div class="skel-row"><span class="skel" style="width:62%"></span>
         <span class="skel skel-sm" style="width:34%"></span></div>`;
  return `<div class="skel-wrap${kind === "tile" ? " skel-grid" : ""}"
    aria-hidden="true">${one.repeat(rows)}</div>`;
}


/* An empty view that says what it is, why, and what to do about it.

   `<p class="empty">Текстов нет…</p>` was a grey sentence where a panel's
   content should be, which reads as a page that failed rather than as a
   state the app understands. A mark, a statement and a next step is the
   same information with a shape.

   Russian throughout, including the heading: an empty view EXPLAINS -- why
   there is nothing here and what would put something here -- and the rule
   for anything that explains is that the learner has to be able to read it.
*/
export function emptyState({icon, title, note, action}) {
  return `<div class="empty-state">
    <div class="empty-mark">${uiIcon(icon, "")}</div>
    <h4>${title}</h4>
    ${note ? `<p>${note}</p>` : ""}
    ${action ? `<div class="row">${action}</div>` : ""}
  </div>`;
}


/* Buttons that live in the markup rather than in a template string.

   The page cannot call `uiIcon`, and inlining twenty lines of SVG into
   `index.html` would put the drawing in two places. So the id says which
   mark a control wants and this file decides what that mark is -- the same
   arrangement the navigation has always had. */
const BUTTON_ICON = {
  dictPlay: "play", dictNext: "skip", dictCheck: "check",
  recBtn: "record", speakPlay: "volume", speakNext: "skip",
  backToLib: "back", speakBtn: "volume", loadReview: "play",
  queueSend: "send", checkBtn: "check", practiceBtn: "play",
  drillBtn: "play", checkpointBtn: "paper", loadLib: "download",
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
       `display:none` -- which takes the text out of the accessibility tree
       with it, leaving seven buttons called nothing at all. The label is
       still the name; it is just carried by the attribute rather than by the
       glyph. `title` for a pointer, `aria-label` for everything else, and
       both are set at every width because a tooltip on a mark is useful on
       the desktop too. */
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
    if (b.querySelector(".ico")) return;
    const d = MODE_ICON[b.dataset.mode];
    if (!d) return;
    const span = document.createElement("span");
    span.className = "ico";
    span.setAttribute("aria-hidden", "true");
    span.innerHTML = navIcon(d);
    b.prepend(span);
  });
  document.querySelectorAll("[data-group]").forEach(el => {
    const d = GROUP_ICON[el.dataset.group];
    if (d) el.innerHTML = navIcon(d);
  });
}

const THEMES = [
  ["system", "Как в системе",
   '<path d="M8.5 2.5h5a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-11a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2h2"/><path d="M6 15.5h6"/>'],
  ["light", "Светлая тема",
   '<circle cx="9" cy="9" r="3.2"/><path d="M9 1.6v1.6M9 14.8v1.6M2.2 9H3.8M14.2 9h1.6M4.2 4.2l1.1 1.1M12.7 12.7l1.1 1.1M13.8 4.2l-1.1 1.1M5.3 12.7l-1.1 1.1"/>'],
  ["dark", "Тёмная тема",
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
    .forEach(el => { el.lang = "et"; gloss(el, RU[el.textContent.trim()]); });
  document.querySelectorAll("#modes button[data-mode], .modes button[data-mode]")
    .forEach(el => { el.lang = "et"; gloss(el, RU[el.textContent.trim()]); });
}
