/* Rada: the syllabus, where you stand on it, and one topic's practice. */

import {RU, celebrate, flowerSvg, forecastHtml, gateHtml, kindIcon, rhythmHtml, sealsHtml,
  stateIcon, uiIcon} from "./chrome.js";
import {$, api, esc, glide, md, ruCount, setLabel, taskLine, wrongVerdict} from "./core.js";
import * as offline from "./offline.js";
import {loadReminders} from "./remind.js";
import {onLessonPractice} from "./lesson.js";
import {loadRail, refreshDueBadge} from "./review.js";
import {examLevel} from "./state.js";

// ── the path ────────────────────────────────────────────────────────
let pathTopic = null;
/* Sub-rules for the next Rada set only: set by a plan block (object case, one
   rule), dropped after that set is fetched. */
let pathRules = null;

/* A running score for one set. Rada's is recorded by the server and shows the
   mastery window; Vaba harjutus is graded by the same code and recorded nowhere. */
const pathTally = {answered: 0, correct: 0, size: 0, missed: [], marks: [], out: "#pathScore",
                   box: "#practiceOut", beads: "#pathBeads",
                   record: true, gate: true, again: () => startPractice()};
const freeTally = {answered: 0, correct: 0, size: 0, missed: [], marks: [], out: "#freeScore",
                   box: "#freeOut", beads: "#freeBeads",
                   record: false, again: () => $("#freeBtn").click()};

/* A new set on a tally. `gen` names the set, so an answer still in flight from the
   set it replaced is not counted in this one (see `grade`). */
function newSet(tally) {
  Object.assign(tally, {answered: 0, correct: 0, size: 0, missed: [], marks: [],
                        gen: (tally.gen || 0) + 1});
  paintBeads(tally);
}


/* One bead per item in the set: moss for right, cranberry for wrong, cornflower for
   the one being answered. A wrong answer stays visible; the row is the set's shape
   at a glance, and it is what the end card repeats. */
function beadsHtml(tally) {
  return Array.from({length: tally.size}, (_, i) => {
    const m = tally.marks[i];
    const cls = m === true ? "ok" : m === false ? "no"
      : i === tally.marks.filter(x => x !== undefined).length ? "now" : "";
    return `<span class="bead ${cls}"></span>`;
  }).join("");
}

function paintBeads(tally) {
  const box = tally.beads && $(tally.beads);
  if (box) box.innerHTML = tally.size ? beadsHtml(tally) : "";
}

/* A tally for a set rendered somewhere else (the Kontrolltöö). */
export function newTally(out, box, again) {
  // A Kontrolltöö is a test: its misses are listed, not re-drilled on the spot.
  return {answered: 0, correct: 0, size: 0, missed: [], marks: [], out, box, record: true,
          again, redo: false};
}

let pathMeta = {};
let autoStarted = false, practiceRequest = 0;
/* What the learner types is the thing being graded: iOS must not capitalise it,
   correct it or underline it, and a password manager must not offer to fill it. */
const ANSWER_FIELD = `autocapitalize="off" autocorrect="off" spellcheck="false" autocomplete="off"`;
const START = ["Harjuta", "упражняться"], NEW_SET = ["Uued laused", "новые задания"];

function themeApplies() {
  const meta = pathMeta[pathTopic];
  // An unknown topic (a stale page, or before the first load) offers the control:
  // withholding a filter from a topic that supports it is as wrong as offering
  // one that does nothing.
  return !meta || meta.themed !== false;
}


/* The theme select is shown only where it changes the drill.

   A closed-class topic (e.g. küsisõnad) has no words to swap, so the control would
   do nothing: it is reset, disabled and taken off the screen rather than left there
   with a paragraph explaining why it does nothing. */
function paintTheme() {
  const sel = $("#wordTheme");
  if (!sel) return;
  const applies = themeApplies();
  if (!applies) sel.value = "";
  sel.disabled = !applies;
  sel.closest("label").hidden = !applies;
}


// ── today's plan ────────────────────────────────────────────────────
function todayMinutes() {
  try { return Number(localStorage.getItem("todayMinutes")) || 20; } catch { return 20; }
}

async function loadToday() {
  const list = $("#todayList");
  if (!list) return;
  const minutes = todayMinutes();
  $("#todayMinutes").value = String(minutes);
  const strip = $("#todayStrip");
  try {
    const p = await (await api(`/api/plan?minutes=${minutes}`, null, "GET")).json();
    if (!(p.blocks || []).length) {
      list.innerHTML = `<li class="hint">На сегодня ничего не запланировано.</li>`;
      $("#todaySum").textContent = "";
      strip.innerHTML = "";
      return;
    }
    $("#todaySum").textContent = `${p.minutes} мин · ` +
      ruCount(p.blocks.length, ["шаг", "шага", "шагов"]);
    /* The day as time: one segment per block, as long as its minutes. */
    strip.innerHTML = p.blocks.map((b, i) =>
      `<span class="strip-seg" data-kind="${esc(b.kind)}"
         style="flex-grow:${b.minutes};animation-delay:${i * 90}ms"></span>`).join("");
    // Up to three blocks read left to right under the strip; more stack as a list.
    list.classList.toggle("as-row", p.blocks.length <= 3);
    list.innerHTML = p.blocks.map((b, i) => {
      const d = b.detail;
      const mistake = d ? `<div class="today-mistake" lang="et">
          <del>${esc(d.answer || "—")}</del> → <ins>${esc(d.expected)}</ins>
          · ${esc(d.solution)}</div>` : "";
      return `<li class="today-block" data-kind="${esc(b.kind)}">
        <span class="today-kind" aria-hidden="true">${kindIcon(b.kind)}</span>
        <div class="today-what">
          <span class="today-min">${b.minutes} мин</span>
          <strong lang="et">${esc(b.et)} <i class="ru" lang="ru">${esc(b.ru)}</i></strong>
          <p class="hint">${esc(b.why)}</p>${mistake}
        </div>
        <button class="ghost" data-i="${i}" lang="et">Alusta <span class="ru" lang="ru">начать</span></button>
      </li>`;
    }).join("");
    list.querySelectorAll("button[data-i]").forEach(btn => btn.onclick = () =>
      startBlock(p.blocks[Number(btn.dataset.i)].action));
  } catch (e) {
    strip.innerHTML = "";
    list.innerHTML = `<li class="hint">План не загрузился: ${esc(e.message)}</li>`;
  }
}

function startBlock(action) {
  if (action.tab === "path") {
    pathTopic = action.topic;
    pathRules = action.rules || null;
    paintTheme();
    startPractice();
    $("#practiceOut").scrollIntoView({block: "start", behavior: glide()});
    return;
  }
  // The router follows the hash (`main.js`), and Back returns to the plan.
  location.hash = "#" + action.tab;
}

$("#todayMinutes").onchange = e => {
  try { localStorage.setItem("todayMinutes", e.target.value); } catch {}
  loadToday();
};


/* Today's date in Estonian: the interface is exposure, and a date is a word the
   learner reads every day. */
function paintDate() {
  const el = $("#pathDate");
  if (!el) return;
  try {
    el.textContent = new Intl.DateTimeFormat("et", {weekday: "long", day: "numeric",
                                                    month: "long"}).format(new Date());
  } catch { el.textContent = ""; }
}


/* The boardwalk: a window of the path around the resume topic, drawn as planks
   with one node per topic. Mastered nodes are moss with a tick, the resume topic
   is cornflower with a halo, open ones are outlined, later ones grey, theory
   dashed. As many nodes as the width holds; the whole path is one tap away. */
let trailData = null;

function drawTrail() {
  const box = $("#pathTrail");
  if (!box || !trailData) return;
  const {topics, resume, mastered, total} = trailData;
  const width = box.clientWidth || 600;
  const count = Math.max(5, Math.min(13, Math.floor(width / 72)));
  const here = Math.max(0, topics.findIndex(t => t.id === resume));
  let start = Math.max(0, here - Math.floor(count * 0.4));
  start = Math.min(start, Math.max(0, topics.length - count));
  const shown = topics.slice(start, start + count);
  if (!shown.length) { box.innerHTML = ""; return; }
  const step = 72, W = step * (shown.length - 1) + 40, H = 70;
  const pts = shown.map((_, i) => [20 + i * step,
    35 + Math.sin((start + i) * 0.95) * 15]);
  // A smooth line through the nodes (Catmull-Rom as cubic Béziers).
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    d += ` C${p1[0] + (p2[0] - p0[0]) / 6} ${p1[1] + (p2[1] - p0[1]) / 6},` +
         `${p2[0] - (p3[0] - p1[0]) / 6} ${p2[1] - (p3[1] - p1[1]) / 6},${p2[0]} ${p2[1]}`;
  }
  const nodes = shown.map((t, i) => {
    const [x, y] = pts[i], now = t.id === resume;
    const r = now ? 12 : t.state === "mastered" ? 10 : t.state === "locked"
      || t.state === "reference" ? 6.5 : 8.5;
    const cls = `node ${t.state.replace(" ", "-")}${now ? " now" : ""}`;
    const tick = t.state === "mastered"
      ? `<path class="tick" d="M${x - 4.5} ${y}l3 3 6-6.5"/>` : "";
    const halo = now ? `<circle class="halo" cx="${x}" cy="${y}" r="17"/>` : "";
    return `<g><title>${esc(t.et)} — ${esc(RU[t.state] || t.state)}</title>
      ${halo}<circle class="${cls}" cx="${x}" cy="${y}" r="${r}"/>${tick}</g>`;
  }).join("");
  const label = `Rada: ${mastered} из ${total} пройдено` +
    (topics[here] ? `, сейчас ${topics[here].et}` : "");
  box.innerHTML = `<svg viewBox="-4 0 ${W + 8} ${H}" role="img" aria-label="${esc(label)}">
      <path class="plank" d="${d}"/><path class="seam" d="${d}"/>${nodes}</svg>
    <div class="trail-legend"><span lang="ru">${mastered} из ${total} пройдено ·
      ${ruCount(topics.filter(t => t.state === "ready" || t.state === "in progress").length,
                ["тема открыта", "темы открыты", "тем открыто"])}</span>
      <a href="#pathAll" data-open-path lang="et">Kogu rada →</a></div>`;
  box.querySelector("[data-open-path]").onclick = e => {
    e.preventDefault();
    $("#pathAll").open = true;
    $("#pathAll").scrollIntoView({block: "start", behavior: glide()});
  };
}

if ("ResizeObserver" in window) {
  let lastWidth = 0;
  new ResizeObserver(([entry]) => {
    const w = Math.round(entry.contentRect.width);
    if (Math.abs(w - lastWidth) > 30) { lastWidth = w; drawTrail(); }
  }).observe($("#pathTrail"));
}


/* `loadPath` runs from several places (the tab, a mastery, a test-out, an offline
   send); only the latest request may paint. */
let pathLoad = 0;

/* The pulse: three small tiles where the desk has its rail — what is due, how the
   exam flower stands, and the rhythm of the last four weeks. Each opens its screen. */
async function paintPulse() {
  const box = $("#pathPulse");
  if (!box || matchMedia("(min-width:1080px)").matches) { if (box) box.innerHTML = ""; return; }
  const get = u => api(u, null, "GET").then(r => r.json()).catch(() => null);
  const [due, ready, status] = await Promise.all([
    get("/api/review/stats"), get(`/api/readiness/${examLevel()}`), get("/api/status")]);
  const tiles = [];
  if (due) tiles.push(`<a class="pulse-tile" href="#review">
      <span class="pulse-label" lang="et">Kordamine</span>
      <span class="pulse-big">${due.due || 0}</span>
      <span class="pulse-sub">${due.due ? "к повторению сегодня"
        : due.total ? "сегодня ничего" : "очередь пуста"}</span></a>`);
  if (ready && ready.parts) {
    const open = ready.parts.filter(p => p.touched === false).length;
    tiles.push(`<a class="pulse-tile pulse-flower" href="#exam">
      <span class="pulse-label" lang="et">Eksam ${esc(ready.level)}</span>
      ${flowerSvg(ready.parts, ready.contact_target || 3, {labels: false})}
      <span class="pulse-sub">${open ? `не начато: ${open} из 4` : "все части начаты"}</span></a>`);
  }
  if (status && status.rhythm && status.rhythm.length) {
    const active = status.rhythm.slice(-28).filter(d => d.n > 0).length;
    const week = status.rhythm.slice(-7).map(d =>
      `<i class="${d.n ? "on" : ""}"></i>`).join("");
    tiles.push(`<a class="pulse-tile" href="#status">
      <span class="pulse-label" lang="et">Rütm</span>
      <span class="pulse-big">${active}<small>/28</small></span>
      <span class="pulse-week" aria-hidden="true">${week}</span>
      <span class="sr-only">дней с занятиями за 4 недели</span></a>`);
  }
  box.innerHTML = tiles.join("");
}

export async function loadPath() {
  loadToday();
  paintDate();
  paintPulse();
  const mine = ++pathLoad;
  try {
    const p = await (await api("/api/curriculum", null, "GET")).json();
    if (mine !== pathLoad) return;
    // A load that worked clears an earlier load's error (never a mastery note).
    if ($("#pathHead").className === "banner") $("#pathHead").hidden = true;
    pathTopic = p.resume;
    const next = p.topics.find(t => t.id === p.resume);
    const place = p.topics.findIndex(t => t.id === p.resume);
    $("#pathNow").textContent = next ? next.et : "Все открытые темы пройдены";
    $("#pathPos").textContent = next ? `тема ${place + 1} из ${p.total}` : "";
    const tried = next && next.attempts
      ? ` · ${ruCount(next.attempts, ["попытка", "попытки", "попыток"])}` +
        (next.accuracy != null ? `, ${Math.round(next.accuracy * 100)}% верно` : "")
      : "";
    $("#pathOf").innerHTML = next
      ? `${next.ru ? `<span lang="ru">${esc(next.ru)}</span> · ` : ""}${esc(next.level)}${tried}`
      : `${p.mastered}/${p.total} тем`;
    $("#pathGate").innerHTML = next && p.gate ? gateHtml(p.resume_recent || [], p.gate) : "";
    p.topics.forEach(t => { pathMeta[t.id] = t; });
    trailData = {topics: p.topics, resume: p.resume, mastered: p.mastered, total: p.total};
    drawTrail();
    paintTheme();
    /* Rada answers "what am I learning today?", so it opens on today's drill, not on
       a button that fetches it. Once per page: coming back to the tab keeps the set
       the learner is in. Nothing is focused, so a phone does not open its keyboard
       over the first sentence. */
    if (!autoStarted && !$("#practiceOut").children.length) {
      autoStarted = true;
      startPractice({focus: false});
    }

    /* The whole path, level by level, as one boardwalk per level. */
    const levels = [...new Set(p.topics.map(t => t.level))];
    $("#pathList").innerHTML = levels.map(lv => {
      const here = p.topics.filter(t => t.level === lv);
      const done = here.filter(t => t.state === "mastered").length;
      const rows = here.map(t => {
        /* Names, not ids — the API resolves them. Tolerant of an older payload so a
           stale cached page never prints "undefined". */
        const needs = t.blocked_by || [];
        const meta = [
          t.ru ? `<span lang="ru">${esc(t.ru)}</span>` : "",
          needs.length ? `<span lang="ru">после:</span> <span lang="et">${esc(needs.join(", "))}</span>` : "",
          t.accuracy === null || t.accuracy === undefined ? "" : `${Math.round(t.accuracy * 100)}%`,
        ].filter(Boolean).join(" · ");
        const rule = `<button class="ghost" data-lesson="${esc(t.id)}" lang="et">reegel <i class="ru" lang="ru">правило</i></button>`;
        const acts = t.state === "ready" || t.state === "in progress"
          ? `<span class="acts">${rule}<button class="ghost" data-topic="${esc(t.id)}" lang="et">harjuta <i class="ru" lang="ru">решать</i></button>
             <button class="ghost" data-testout="${esc(t.id)}" lang="et">testi välja <i class="ru" lang="ru">сдать экстерном</i></button></span>`
          : `<span class="acts">${rule}</span>`;
        return `<div class="topic ${t.state.replace(" ", "-")}${t.id === p.resume ? " now" : ""}">
          <span class="st" title="${esc(RU[t.state] || t.state)}">${stateIcon(t.state)}<span class="st-word" lang="ru">${esc(RU[t.state] || t.state)}</span></span>
          <span class="name" lang="et">${esc(t.et)}</span>
          ${meta ? `<span class="meta">${meta}</span>` : ""}
          ${acts}</div>`;
      }).join("");
      return `<div class="path-level"><h4><span class="lv" data-level="${esc(lv)}">${esc(lv)}</span>
        <span class="hint">${done} из ${here.length} пройдено</span></h4>${rows}</div>`;
    }).join("");
  } catch (e) {
    if (mine !== pathLoad) return;
    $("#pathHead").className = "banner";   // an error is the amber one
    $("#pathHead").hidden = false;
    $("#pathHead").textContent = e.message;
  }
}


// ── progress ────────────────────────────────────────────────────────
export async function loadStatus() {
  const out = $("#statusOut");
  loadReminders();
  try {
    const [d, marks, queue] = await Promise.all([
      (await api("/api/status", null, "GET")).json(),
      api(`/api/milestones/${examLevel()}`, null, "GET").then(r => r.json())
        .catch(() => ({milestones: []})),
      api("/api/review/stats", null, "GET").then(r => r.json()).catch(() => ({})),
    ]);
    const s = d.sections; let html = "";
    const pct = (a, b) => b ? Math.max(0, Math.min(100, a / b * 100)) : 0;
    if (d.rhythm?.length) html += `<section class="stat-card wide">
      <h3 lang="et">Rütm <i class="ru" lang="ru">занятия по дням, 12 недель</i></h3>
      ${rhythmHtml(d.rhythm)}</section>`;
    if (s.rada) html += `<section class="stat-card">
      <h3 lang="et">Rada <i class="ru" lang="ru">путь</i></h3>
      <div class="stat-big">${s.rada.mastered}<small> / ${s.rada.total} тем</small></div>
      <div class="meter good" aria-hidden="true"><span style="width:${pct(s.rada.mastered, s.rada.total)}%"></span></div>
      <p class="why">${ruCount(s.rada.available, ["тема открыта", "темы открыты", "тем открыто"])}.
        Следующая: <span lang="et">${esc(s.rada.next_et || "—")}</span>${
        s.rada.next_ru ? ` — ${esc(s.rada.next_ru)}` : ""}</p></section>`;
    if (s.kordamine) html += `<section class="stat-card">
      <h3 lang="et">Kordamine <i class="ru" lang="ru">повторение</i></h3>
      <div class="stat-big">${s.kordamine.due}<small> к повторению</small></div>
      <p class="why">${ruCount(s.kordamine.scheduled, ["карточка", "карточки", "карточек"])} в очереди всего.</p>
      ${queue.forecast && s.kordamine.scheduled ? forecastHtml(queue.forecast) : ""}
      ${s.kordamine.due ? `<a class="rail-go" href="#review" lang="et">Alusta kordamist →</a>` : ""}</section>`;
    if (s.sonavara) {
      /* Words known in each frequency band, commonest first: where the everyday
         vocabulary is and is not yet. Heights are each band's own share. */
      const bands = s.sonavara.bands || [];
      html += `<section class="stat-card wide">
        <h3 lang="et">Sõnavara <i class="ru" lang="ru">словарь по частотности</i></h3>
        <div class="stat-big">${s.sonavara.known_in_top}<small> из первых ${s.sonavara.top} слов</small></div>
        <div class="bands" role="img" aria-label="${esc(bands.map(b =>
          `${b.from}–${b.to}: ${b.known} из ${b.size}`).join("; "))}">${bands.map((b, i) =>
          `<div class="band"><span style="height:${pct(b.known, b.size)}%;animation-delay:${i * 60}ms"></span></div>`).join("")}</div>
        <div class="band-labels" aria-hidden="true">${bands.map(b => `<span>${b.to}</span>`).join("")}</div>
        ${s.sonavara.glossed != null ? `<p class="gloss-late">${ruCount(s.sonavara.glossed,
          ["слово", "слова", "слов"])} с переводом <span class="hint">(пополняется само ·
          сегодня осталось ${s.sonavara.gloss_budget_left})</span></p>` : ""}</section>`;
      // Two facts, kept apart: "known" is what the learner declared; the glossed count
      // is what the app can translate. The second grows on its own, so it is not
      // presented as an achievement.
    }
    if (s.raamatukogu) html += `<section class="stat-card">
      <h3 lang="et">Lugemine · Kuulamine <i class="ru" lang="ru">чтение и аудирование</i></h3>
      <div class="stat-big">${s.raamatukogu.items || 0}<small> ${ruCount(s.raamatukogu.items || 0,
        ["материал", "материала", "материалов"]).replace(/^\S+ /, "")}</small></div>
      <p class="why">${ruCount(Math.round(s.raamatukogu.minutes || 0), ["минута", "минуты", "минут"])} с текстами и записями.</p></section>`;
    if (marks.milestones?.length) html += `<section class="stat-card">
      <h3 lang="et">Märgid <i class="ru" lang="ru">вехи ${esc(examLevel())}</i></h3>
      ${sealsHtml(marks.milestones)}
      <p class="hint">Отмечают сделанное; очков и серий нет.</p></section>`;
    // The caveat comes from the API, in Russian, so it is written once and matches
    // what the numbers mean.
    html += `<div class="engine">${esc(d.caveat || "")}</div>`;
    out.innerHTML = html;
  } catch (e) { out.textContent = e.message; }
}


$("#pathList").addEventListener("click", e => {
  const out = e.target.closest("button[data-testout]");
  if (out) {
    $("#pathAll").open = false;
    startTestOut(out.dataset.testout);
    return;
  }
  const b = e.target.closest("button[data-topic]");
  if (b) {
    pathTopic = b.dataset.topic;
    $("#pathAll").open = false;
    paintTheme();
    startPractice();
  }
});


/* A missed item can be explained — by a model, saying so, grounded in Vabamorf
   and EKK, and never deciding anything (`eesti/tutor.py`). */
function offerExplanation(verdict, eventId) {
  verdict.insertAdjacentHTML("beforeend",
    `<div class="row"><button class="ghost tutorbtn" type="button" lang="et">Selgita
      <span class="ru" lang="ru">объяснить</span></button></div>`);
  const btn = verdict.querySelector(".tutorbtn");
  btn.onclick = async () => {
    btn.disabled = true;
    try {
      const a = await (await api("/api/tutor", {intent: "explain_attempt",
                                                event_id: eventId})).json();
      const ref = a.reference && a.reference.known
        ? ` <a href="${esc(a.reference.url)}" target="_blank" rel="noopener">EKK ${esc(a.reference.ekk_section)}</a>` : "";
      btn.closest(".row").outerHTML = a.explanation_ru
        ? `<div class="why">${md(a.explanation_ru)}
             <span class="hint">объяснил ${esc(a.engine)} · это не проверка ответа</span>${ref}</div>`
        : `<div class="why"><span class="hint">${esc(a.note || "объяснение недоступно")}</span>${ref}</div>`;
    } catch (e) {
      btn.disabled = false;
      btn.insertAdjacentHTML("afterend", `<span class="hint">${esc(e.message)}</span>`);
    }
  };
}


/* Test-out: five items, all five right marks the topic known (`placement.py`).
   Answered as one set, graded by the server, so the page never decides. */
async function startTestOut(topic) {
  const out = $("#practiceOut");
  out.innerHTML = `<p class="hint">Загружаю…</p>`;
  let set;
  try {
    set = await (await api(`/api/testout/${encodeURIComponent(topic)}`, null, "GET")).json();
  } catch (e) {
    out.innerHTML = `<div class="banner">${esc(e.message)}</div>`;
    return;
  }
  out.innerHTML = `
    <div class="banner info"><b lang="et">${esc(set.et)}</b> · ${esc(set.note)}</div>
    <div id="testoutTasks">${set.items.map((it, i) => `
      <div class="mock-task" data-i="${i}">
        <div class="prompt" lang="et">${esc(it.prompt).replace("____",
          '<span class="blank">____</span>')}</div>
        <div class="row"><span class="hint" lang="et">${esc(it.hint || "")}</span>
          <input type="text" size="16" lang="et" aria-label="Vastus — ответ"
            ${ANSWER_FIELD}></div>
      </div>`).join("")}</div>
    <div class="row"><button class="go" id="testoutDone" lang="et">Valmis
      <span class="ru" lang="ru">проверить</span></button></div>
    <div class="verdict" id="testoutVerdict" role="status"></div>`;
  out.querySelector("input")?.focus();
  $("#testoutDone").onclick = async () => {
    $("#testoutDone").disabled = true;
    const given = [...out.querySelectorAll("#testoutTasks input")].map(x => x.value);
    const verdict = $("#testoutVerdict");
    try {
      const r = await (await api(`/api/testout/${encodeURIComponent(topic)}`,
                                 {seed: set.seed, given})).json();
      verdict.className = r.passed ? "verdict ok" : "verdict no";
      verdict.innerHTML = r.passed
        ? `${r.correct} из ${r.asked} — тема засчитана.`
        : `${r.correct} из ${r.asked}. Нужно ${set.required} из ${set.required};
           ничего не потеряно — тема просто остаётся в пути.`;
      loadPath(); loadRail();
    } catch (e) {
      $("#testoutDone").disabled = false;
      verdict.className = "verdict no";
      verdict.innerHTML = `Не проверено: ${esc(e.message)}`;
    }
  };
}


async function loadThemes() {
  try {
    const {themes} = await (await api("/api/themes", null, "GET")).json();
    $("#wordTheme").innerHTML = '<option value="" lang="et">kõik sõnad</option>' +
      themes.map(t => `<option value="${esc(t.id)}" lang="et">${esc(t.et)}</option>`).join("");
  } catch {}
}


async function startPractice({focus = true} = {}) {
  let loaded = false;
  /* The auto-start and a topic picked from Kogu rada can be in flight together; only
     the latest may paint, or a slow first answer replaces the learner's choice. */
  const mine = ++practiceRequest;
  const out = $("#practiceOut"); out.innerHTML = "";
  newSet(pathTally);
  $("#pathScore").textContent = "";
  const btn = $("#practiceBtn"); btn.disabled = true; setLabel(btn, "Загружаю…");
  try {
    const body = {count: 10};
    if (pathTopic) body.topic = pathTopic;
    if (pathRules) { body.rules = pathRules; pathRules = null; }
    const theme = themeApplies() ? $("#wordTheme").value : "";
    if (theme) body.theme = theme;
    const res = await (await api("/api/practice", body)).json();
    if (mine !== practiceRequest) return;
    if (!res.items.length) {
      // An empty topic is still a topic: those with no generator carry an EKK
      // reference, which is the learner's way forward.
      let msg = `<div class="banner">${esc(res.detail || "ничего не пришло")}`;
      if (res.reference && res.reference.known)
        msg += ` · <a href="${esc(res.reference.url)}" target="_blank" rel="noopener">EKK ${esc(res.reference.ekk_section)}</a>`;
      out.innerHTML = msg + `</div>`;
      /* Some topic × theme pairs return fewer than three items or none, because a
         corpus cloze needs a sentence containing a theme noun. The way out is one
         click, so it is a button. */
      if (res.theme_emptied) {
        out.insertAdjacentHTML("beforeend",
          `<button class="ghost" lang="et">Proovi ilma teemata <span class="ru" lang="ru">без темы</span></button>`);
        out.lastElementChild.onclick = () => { $("#wordTheme").value = ""; startPractice(); };
      }
      return;
    }
    pathTopic = res.topic;
    paintTheme();
    // A reference, not a warning: `info` rather than the default amber.
    /* The topic line above already names the resume topic; the head names it only
       when a different one was picked from the list. */
    const bits = [];
    if (res.et !== $("#pathNow").textContent)
      bits.push(`<strong lang="et">${esc(res.et)}</strong> · ${esc(res.level)}`);
    /* A short set is not a broken one, but silence would read as "this topic only has
       three". */
    if (res.theme && res.items.length < 10)
      bits.push(`<span class="hint">по этой теме нашлось ${res.items.length}</span>`);
    bits.push(`<button class="linky" type="button" data-lesson="${esc(res.topic)}" lang="et">Reegel
      <span class="ru" lang="ru">правило</span></button>`);
    out.innerHTML = bits.length
      ? `<div class="banner info">${bits.join(" · ")}</div>` : "";
    loaded = true;
    pathTally.size = res.items.length;
    paintBeads(pathTally);
    res.items.forEach((it, i) =>
      out.appendChild(renderPracticeItem(it, res.topic, i, res.glosses || {}, focus)));
  } catch (e) {
    if (mine !== practiceRequest) return;
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  } finally {
    // A superseded request leaves the button to the one that replaced it.
    if (mine !== practiceRequest) return;
    btn.disabled = false;
    /* With a set on screen, answering is the main action; the button only swaps
       the set, so it steps down to a secondary one. */
    btn.className = loaded ? "ghost" : "go";
    // With a set on screen the next set is offered at its end, not above it.
    btn.hidden = loaded;
    btn.querySelector(".btn-ico")?.replaceWith(
      document.createRange().createContextualFragment(uiIcon(loaded ? "next" : "play")));
    const [et, ru] = loaded ? NEW_SET : START;
    setLabel(btn, et);
    btn.querySelector(".ru").textContent = ru;
  }
}


/* The end of a set: the one moment a session has. It says how the set went in one
   line and puts the next set under the thumb. No streak, no confetti: the count is
   the reward, and the path's own gate says how far there is to go. */
function finishSet(tally, res) {
  const box = $(tally.box);
  if (!box || box.querySelector(".set-end")) return;
  const [need, of] = (res.gate || "").split("/");
  // Only Rada's set is one topic, so only there does the topic's gate apply.
  const gate = tally.gate && res.accuracy != null && res.gate && !res.just_mastered
    ? `<p class="hint">Тема засчитывается, когда из последних ${esc(of)} ответов
         верны ${esc(need)}. Сейчас: ${Math.round(res.accuracy * 100)}%.</p>` : "";
  /* What went wrong, in the sentence it went wrong in, with the right form: the end
     of a set is where a learner looks back, so the misses are there to look at. */
  const missed = tally.missed.length ? `<ul class="set-missed" lang="et">${
    tally.missed.map(({it}) => `<li>${esc(it.prompt).replace("____",
      `<b>${esc(it.answer)}</b>`)}</li>`).join("")}</ul>` : "";
  const redo = tally.missed.length && tally.redo !== false
    ? `<button class="ghost" data-act="redo" lang="et">Korda vigu <span class="ru" lang="ru">повторить ошибки</span></button>` : "";
  const end = document.createElement("div");
  /* The score, the beads again, and the next set under the thumb. A set nearly all
     right wears moss; the count is the reward, not a streak. */
  end.className = "set-end";
  if (tally.size && tally.correct >= 0.8 * tally.size) end.classList.add("great");
  end.setAttribute("role", "status");
  end.innerHTML = `<h4 lang="et">Komplekt tehtud <i class="ru" lang="ru">набор пройден</i></h4>
    <p class="set-score">${tally.correct}<small> из ${tally.size} верно</small></p>
    <div class="beads" aria-hidden="true">${beadsHtml(tally)}</div>${gate}${missed}
    <div class="row">${redo}<button class="go" data-act="new" lang="et">${uiIcon("next")}Uued laused <span class="ru" lang="ru">новые задания</span></button></div>`;
  end.querySelector('[data-act="new"]').onclick = tally.again;
  end.querySelector('[data-act="redo"]')?.addEventListener("click", () => redoMissed(tally));
  // The score line said the same thing one line lower; the card says it now.
  $(tally.out).textContent = "";
  box.appendChild(end);
  // Fully in view, above the dock: this is the moment the set exists for.
  requestAnimationFrame(() => requestAnimationFrame(() =>
    end.scrollIntoView({block: "nearest", behavior: glide()})));
  tally.done?.(tally);
}


/* The missed items again, as a short set of their own: graded and recorded the same
   way as the first time (a Rada miss is already in the review queue either way). */
function redoMissed(tally) {
  const again = tally.missed;
  const box = $(tally.box);
  box.innerHTML = "";
  newSet(tally);
  tally.size = again.length;
  paintBeads(tally);
  again.forEach(({it, topic}, i) =>
    box.appendChild(renderPracticeItem(it, topic, i, {}, true, tally)));
}


export function renderPracticeItem(it, topic, i, glosses, focus = true, tally = pathTally) {
  /* What the word means, when the app already knows.

     The gloss comes from the local store, so it is either instantly there or
     absent — a practice set never waits on a dictionary.

     A küsisõnad item has no lemma — its word is the answer — so it carries
     `answer_ru` instead: EKI's Russian for the question word the blank wants
     (где, куда), which says what to ask without printing the Estonian. */
  const ru = (it.answer_ru && it.answer_ru.length)
    ? it.answer_ru : (glosses || {})[it.lemma] || [];
  const el = document.createElement("div");
  el.className = "drill";
  /* The answer time starts when the learner turns to the item (its field gets
     focus), not when the set was built: items wait their turn on a phone. */
  let started = null;
  const rendered = performance.now();
  el.addEventListener("focusin", () => { started ??= performance.now(); });
  // Where this item sits in its set; shown on a phone, where one item is on screen.
  // The set this item belongs to; a later set on the same tally has another.
  const set = tally.gen || 0;
  const place = tally.size ? `${i + 1}/${tally.size}` : `${i + 1}`;
  const pos = tally.size ? `<div class="drill-pos">${i + 1} / ${tally.size}</div>` : "";
  /* Word order is the one topic whose unit is the whole sequence, so it is answered
     by choosing a sentence rather than typing a word. The chosen sentence is
     submitted as the answer and graded by the same comparison as everything else. */
  el.innerHTML = `${pos}
    <div class="prompt" lang="et">${esc(it.prompt).replace("____", '<span class="blank">____</span>')}</div>
    ${it.choices && it.choices.length ? `
    <div class="choices">
      ${it.choices.map(c =>
        `<button class="choice" lang="et" data-choice="${esc(c)}">${esc(c)}</button>`).join("")}
    </div>
    <div class="row">
      ${taskLine(it, ru)}
    </div>` : `
    <div class="row">
      <input type="text" size="18" placeholder="?" lang="et" ${ANSWER_FIELD}
             aria-label="Vastus ${place} — ответ">
      <button class="ghost" lang="et" aria-label="Kontrolli ${place} — проверить">Kontrolli</button>
      ${taskLine(it, ru)}
    </div>`}
    <div class="verdict" role="status"></div>`;
  const input = el.querySelector("input"), verdict = el.querySelector(".verdict");
  const choices = [...el.querySelectorAll(".choice")];
  // One holder for "what was answered", whichever shape the item took, so the
  // submit path below stays single.
  let picked = "";
  const check = el.querySelector(".row > button.ghost");
  const lock = () => {
    if (input) input.disabled = true;
    if (check) check.disabled = true;
    choices.forEach(b => b.disabled = true);
  };
  const unlock = () => {
    if (input) input.disabled = false;
    if (check) check.disabled = false;
    choices.forEach(b => { b.disabled = false; b.classList.remove("picked"); });
  };
  const locked = () => (input ? input.disabled : choices[0]?.disabled);

  const grade = async () => {
    if (locked()) return;
    // Answered from the keyboard: the next item gets the keyboard when this is graded.
    const typed = !!input && document.activeElement === input;
    /* An empty box is not an answer. Here it would also be recorded: against the
       accuracy that gates mastery, and into the review queue. The first item is
       focused on load, so one stray Enter would do it. Ask again instead. */
    if (input && !input.value.trim()) {
      verdict.className = "verdict";
      verdict.innerHTML = `<span class="hint">Впиши форму — тогда проверю.</span>`;
      input.focus();
      return;
    }
    lock();
    let res;
    try {
      // The server grades and records: the client must not be the judge of
      // whether a topic has been mastered.
      // The token is what the server grades from; the rest is for a page
      // cached from before tokens existed.
      res = await (await api("/api/practice/answer", {
        topic, prompt: it.prompt, answer: it.answer,
        given: input ? input.value : picked,
        distractor: it.distractor || "", lemma: it.lemma || "",
        label: it.hint || "", rule: it.rule || "", why_ru: it.why_ru || "",
        token: it.token || "",
        latency_ms: Math.round(performance.now() - (started ?? rendered)),
        record: tally.record,
      })).json();
    } catch (e) {
      /* Nothing was recorded, so the item is not spent: unlock it and keep what was
         typed, so the learner can send it again once the connection is back. */
      unlock();
      verdict.className = "verdict no";
      verdict.innerHTML = `Ответ не проверен. ${esc(e.message)}
        <span class="hint">Попробуй ещё раз.</span>`;
      return;
    }
    // Answered, but the set was replaced while the answer was on its way: this item
    // is gone from the screen and must not count in the set that replaced it.
    if ((tally.gen || 0) !== set) return;
    tally.answered++; if (res.correct) tally.correct++;
    tally.marks[i] = !!res.correct;
    paintBeads(tally);
    /* The sentence completes itself: the blank takes the right form, moss when it
       was the learner's, underlined in cranberry when it was not. */
    const blank = el.querySelector(".prompt .blank");
    // With parallel forms ("tube ~ tubasid") the sentence takes the one typed, if right.
    const said = res.correct && input ? input.value.trim() : it.answer.split(" ~ ")[0];
    if (blank && !choices.length) {
      blank.textContent = said;
      blank.classList.add("filled", res.correct ? "ok" : "no");
    }
    // A miss goes on the set's list, to be looked at and redone at its end.
    if (!res.correct) tally.missed.push({it, topic});
    /* Graded: on a phone the next item appears under this one (see `.drill.done`
       in app.css). Keep this verdict in view above the keyboard and the thumb bar. */
    el.classList.add("done");
    requestAnimationFrame(() => verdict.scrollIntoView({block: "nearest"}));
    if (typed) el.nextElementSibling?.querySelector?.("input")?.focus({preventScroll: true});
    verdict.className = "verdict " + (res.correct ? "ok" : "no");
    // A choice item's prompt is a question with no blank, so the answered sentence is
    // shown instead. The rule is shown either way: on a right answer it says why,
    // which for word order is the lesson.
    verdict.innerHTML = res.correct
      ? (choices.length
          ? `<span lang="et">✓ õige <i class="ru" lang="ru">верно</i></span> — <strong lang="et">${esc(it.answer)}</strong><br>
             <span class="why">${md(it.why_ru || "")}</span>`
          : `<span lang="et">✓ õige <i class="ru" lang="ru">верно</i></span> — <strong lang="et">${esc(it.prompt.replace("____", said))}</strong>`
            // A choice topic hid its form until now; the rule is the lesson either way.
            + (it.form_after ? `<br><span class="why">${md(it.why_ru || "")}</span>` : ""))
      : wrongVerdict(input ? input.value : picked, it.answer, it.why_ru);
    /* The meaning arrives with the grade: `/api/practice/answer` looks up at most
       this one word. Only shown when the hint above did not already carry it. */
    if (res.russian?.length && !ru.length) {
      verdict.innerHTML += `<span class="gloss-late"><b lang="et">${esc(it.lemma)}</b> — `
        + `${esc(res.russian.slice(0, 3).join(", "))}</span>`;
    }
    /* A recorded miss can be explained. After the verdict is written: writing
       `innerHTML` would otherwise wipe the button and its handler. */
    if (!res.correct && res.event_id) offerExplanation(verdict, res.event_id);
    let line = `${tally.correct}/${tally.answered} верных`;
    if (res.accuracy != null && res.gate)
      line += ` · ${Math.round(res.accuracy * 100)}% из последних ${res.gate.split("/")[1]}`;
    $(tally.out).textContent = line;
    if (tally.size && tally.answered === tally.size) finishSet(tally, res);
    if (res.just_mastered) {
      // Good news wears the accent. `#pathHead` is shared with the error path, so the
      // class is set at each use.
      const name = pathMeta[topic]?.et || topic;
      $("#pathHead").className = "banner ok";
      $("#pathHead").hidden = false;
      $("#pathHead").innerHTML =
        `✓ Тема <strong lang="et">${esc(name)}</strong> пройдена и открывает следующие темы. ` +
        `Упражнения ушли в очередь повторения.`;
      celebrate({title: "Teema läbitud", name,
                 note: "Тема пройдена: следующие темы открыты."});
      loadPath();
      refreshDueBadge();
      loadRail();
    }
  };
  if (choices.length) {
    // Clicking a sentence both records the choice and submits it: a separate
    // "check" step would be one tap of ceremony on a phone for no decision.
    choices.forEach(b => b.onclick = () => {
      picked = b.dataset.choice;
      b.classList.add("picked");
      grade();
    });
  } else {
    el.querySelector("button").onclick = grade;
    input.addEventListener("keydown", e => { if (e.key === "Enter") grade(); });
    if (i === 0 && focus) setTimeout(() => input.focus(), 0);
  }
  return el;
}


$("#practiceBtn").onclick = () => startPractice();
// A new word theme is a new set: with the button folded into the end card, the
// select itself starts it.
$("#wordTheme").addEventListener("change", () => startPractice());


// ── Rada or Vaba harjutus ───────────────────────────────────────────
/* One panel, two ways through the same drills. The switch changes only what is
   recorded: Vaba harjutus is graded by the same server code, with `record: false`. */
export function setPathMode(mode) {
  document.querySelectorAll("#pathModes button").forEach(b =>
    b.setAttribute("aria-selected", b.dataset.pm === mode));
  $("#pathRada").hidden = mode !== "rada";
  $("#pathFree").hidden = mode !== "vaba";
  if (mode === "vaba") fillFreeTopics();
}

document.querySelectorAll("#pathModes button").forEach(b =>
  b.onclick = () => setPathMode(b.dataset.pm));


/* Every topic with drills, by level, locked ones included: free practice is where a
   learner looks ahead or goes back. Object case first selected — the #1 weakness. */
async function fillFreeTopics() {
  const sel = $("#freeTopic");
  if (sel.options.length) return;
  try {
    const p = await (await api("/api/curriculum", null, "GET")).json();
    const levels = [...new Set(p.topics.map(t => t.level))];
    sel.innerHTML = levels.map(lv => `<optgroup label="${esc(lv)}">${
      p.topics.filter(t => t.level === lv && t.state !== "reference").map(t =>
        `<option value="${esc(t.id)}">${esc(t.et)}</option>`).join("")}</optgroup>`
    ).join("");
    sel.value = "obj-case";
    paintFreeRule();
  } catch (e) {
    $("#freeOut").innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  }
}

// Object case alone has sub-rules; the control exists only where it narrows something.
function paintFreeRule() {
  const on = $("#freeTopic").value === "obj-case";
  $("#freeRuleLabel").hidden = !on;
  if (!on) $("#freeRule").value = "";
}
$("#freeTopic").onchange = paintFreeRule;


/* Folded: one line saying what is being practised, and "Muuda" to change it. */
function foldFreeControls(fold) {
  const pick = sel => sel.options[sel.selectedIndex]?.text || "";
  $("#freeWhat").textContent = [pick($("#freeTopic")),
    $("#freeRule").value ? pick($("#freeRule")) : "", pick($("#freeLevel"))]
    .filter(Boolean).join(" · ");
  $("#freeSummary").hidden = !fold;
  $("#freeControls").hidden = fold;
  $("#freeNote").hidden = fold;
}
$("#freeEdit").onclick = () => { foldFreeControls(false); $("#freeTopic").focus(); };


$("#freeBtn").onclick = async () => {
  const out = $("#freeOut"), btn = $("#freeBtn");
  out.innerHTML = "";
  newSet(freeTally);
  $("#freeScore").textContent = "";
  btn.disabled = true;
  try {
    const rule = $("#freeRule").value;
    const res = await (await api("/api/practice", {
      topic: $("#freeTopic").value, count: 10,
      levels: $("#freeLevel").value.split(","),
      ...(rule ? {rules: [rule]} : {}),
    })).json();
    if (!res.items.length) {
      out.innerHTML = `<div class="banner">${esc(res.detail || "ничего не пришло")}</div>`;
      return;
    }
    freeTally.size = res.items.length;
    paintBeads(freeTally);
    res.items.forEach((it, i) => out.appendChild(
      renderPracticeItem(it, res.topic, i, res.glosses || {}, false, freeTally)));
    $("#freeLesson").dataset.lesson = res.topic || $("#freeTopic").value;
    foldFreeControls(true);
    /* The set, not the settings, is what the learner came for: bring its first item
       into view and hand it the keyboard. */
    const first = out.querySelector(".drill");
    first?.scrollIntoView({block: "start", behavior: glide()});
    first?.querySelector("input")?.focus({preventScroll: true});
  } catch (e) {
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  } finally { btn.disabled = false; }
};

loadThemes();


// ── offline ─────────────────────────────────────────────────────────
/* A pack is fetched while there is a connection and answered without one. The
   page grades by the same rule the server does, queues what was answered, and
   sends it when the connection returns — the server re-grades each answer from
   its token, so nothing here decides what counts (`js/offline.js`). */

async function paintOffline() {
  const pack = await offline.savedPack();
  const queued = await offline.pending();
  $("#offlineState").textContent = offline.describe(pack, queued.length);
  $("#offlinePractice").hidden = !pack;
  $("#offlineSend").hidden = !queued.length;
}

$("#offlineGet").onclick = async () => {
  const btn = $("#offlineGet");
  btn.disabled = true;
  try {
    await offline.fetchPack(24);
    await paintOffline();
  } catch (e) {
    $("#offlineState").textContent = "Не скачалось: " + e.message;
  } finally { btn.disabled = false; }
};

$("#offlinePractice").onclick = async () => {
  const pack = await offline.savedPack();
  if (!pack) return;
  /* A set fetched on load can still be in flight; claiming the request id
     stops it painting over the offline one when it lands. */
  practiceRequest++;
  const out = $("#practiceOut");
  out.innerHTML = `<div class="banner info">Офлайн-набор: ответы записываются
    на сервере, когда связь вернётся.</div>`;
  newSet(pathTally);
  pathTally.size = pack.items.length;
  paintBeads(pathTally);
  pack.items.forEach((it, i) => out.appendChild(
    renderOfflineItem(it, i, pack.glosses || {})));
  out.querySelector("input")?.focus();
};

$("#offlineSend").onclick = async () => {
  const btn = $("#offlineSend");
  btn.disabled = true;
  const sent = await offline.flush();
  $("#offlineState").textContent = sent
    ? `Отправлено ответов: ${sent}.`
    : "Ответы пока не отправлены — нет связи.";
  await paintOffline();
  if (sent) { loadPath(); loadRail(); }
  btn.disabled = false;
};

/* One offline item: graded here because there is nobody to ask, and queued
   with its own id so sending it twice changes nothing. */
function renderOfflineItem(it, i, glosses) {
  const el = document.createElement("div");
  el.className = "drill";
  const ru = (glosses || {})[it.lemma] || [];
  el.innerHTML = `
    <div class="prompt" lang="et">${esc(it.prompt).replace("____",
      '<span class="blank">____</span>')}</div>
    <div class="row">
      <input type="text" size="18" lang="et" aria-label="Vastus — ответ" ${ANSWER_FIELD}>
      <button class="go" lang="et">Kontrolli <span class="ru" lang="ru">проверить</span></button>
      ${taskLine({lemma: it.lemma, label: it.hint || "", level: it.level || ""},
                 ru, {quiet: true})}
    </div>
    <div class="verdict" role="status"></div>`;
  const input = el.querySelector("input"), verdict = el.querySelector(".verdict");
  const started = performance.now();
  const check = async () => {
    if (!input.value.trim()) return;
    input.disabled = el.querySelector("button").disabled = true;
    const ok = offline.graded(it, input.value);
    /* The verdict first: it is what the learner is waiting for, and it must not
       depend on the queue write succeeding. Then the item is spent, so the next
       one appears (one item at a time), and its bead is filled. */
    verdict.className = ok ? "verdict ok" : "verdict no";
    verdict.innerHTML = ok
      ? `<span lang="et">✓ õige <i class="ru" lang="ru">верно</i></span>`
      : wrongVerdict(input.value, it.answer, it.why_ru);
    const blank = el.querySelector(".prompt .blank");
    if (blank) {
      blank.textContent = ok ? input.value.trim() : it.answer.split(" ~ ")[0];
      blank.classList.add("filled", ok ? "ok" : "no");
    }
    el.classList.add("done");
    pathTally.marks[i] = ok;
    pathTally.answered++; if (ok) pathTally.correct++;
    paintBeads(pathTally);
    el.nextElementSibling?.querySelector?.("input")?.focus({preventScroll: true});
    try {
      await offline.queueAnswer(it, input.value,
                                Math.round(performance.now() - started));
      verdict.insertAdjacentHTML("beforeend",
        `<span class="hint">записано локально</span>`);
    } catch (e) {
      verdict.insertAdjacentHTML("beforeend",
        `<span class="hint">не записано: ${esc(e.message)}</span>`);
    }
    paintOffline();
  };
  el.querySelector("button").onclick = check;
  input.addEventListener("keydown", e => { if (e.key === "Enter") check(); });
  return el;
}

addEventListener("online", () => offline.flush().then(paintOffline));
paintOffline();


/* "Harjuta" on a Reegel page starts a Minu rada set on that topic. */
onLessonPractice(topic => {
  pathTopic = topic;
  $("#pathAll").open = false;
  paintTheme();
  startPractice();
});
