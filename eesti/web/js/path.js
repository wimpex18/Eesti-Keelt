/* Rada: the syllabus, where you stand on it, and one topic's practice. */

import {RU, celebrate, flowerSvg, forecastHtml, gateHtml, kindIcon, rhythmHtml, sealsHtml,
  stateIcon, uiIcon} from "./chrome.js";
import {$, addPracticeSupport, api, attribHtml, blankForm, esc, glide, md, ruCount,
  setLabel, taskLine, wrongVerdict} from "./core.js";
import {sayHtml, wireSay} from "./media.js";
import * as offline from "./offline.js";
import {loadReminders} from "./remind.js";
import {onLessonPractice} from "./lesson.js";
import {addMic} from "./voice.js";
import {loadRail, refreshDueBadge} from "./review.js";
import {examLevel} from "./state.js";
import {icon} from "./icons.js";

// ── the path ────────────────────────────────────────────────────────
let pathTopic = null;
/* Sub-rules for one topic's sets: a unit's revisit practises only the rules
   its stage unlocks, for as long as that topic's session runs. */
let pathRules = null;   // {topic, rules}

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
  $(tally.box)?.parentElement.querySelector(".session-history")?.remove();
  Object.assign(tally, {answered: 0, correct: 0, size: 0, skipped: 0, missed: [], marks: [],
                        gen: (tally.gen || 0) + 1});
  paintBeads(tally);
}


/* One bead per item in the set: moss for right, cranberry for wrong, cornflower for
   the one being answered. A wrong answer stays visible; the row is the set's shape
   at a glance, and it is what the end card repeats. */
function beadsHtml(tally) {
  return Array.from({length: tally.size}, (_, i) => {
    const m = tally.marks[i];
    const cls = m === true ? "ok" : m === false ? "no" : m === "skipped" ? "skipped"
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
  $(box)?.parentElement.querySelector(".session-history")?.remove();
  // A Kontrolltöö is a test: its misses are listed, not re-drilled on the spot.
  return {answered: 0, correct: 0, size: 0, missed: [], marks: [], out, box, record: true,
          again, redo: false};
}

let pathMeta = {};
let practiceRequest = 0, lessonRequest = 0, sessionTopic = null;
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


let pathLoad = 0;

export async function loadPath() {
  paintDate();
  const mine = ++pathLoad;
  try {
    const p = await (await api("/api/curriculum", null, "GET")).json();
    if (mine !== pathLoad) return;
    // A load that worked clears an earlier load's error (never a mastery note).
    if ($("#pathHead").className === "banner") $("#pathHead").hidden = true;
    if (!sessionTopic) pathTopic = p.resume;
    const next = p.topics.find(t => t.id === (sessionTopic || p.resume));
    $("#pathNow").textContent = next ? next.et : "Все открытые темы пройдены";
    // A reference topic has no checked exercises: promise only what it gives.
    $("#tab-path .lesson-purpose").textContent = next && next.drillable === false
      ? "Разбери правило на примерах. Упражнений с проверкой по этой теме пока нет."
      : "Разбери правило на примерах, попробуй сам и получи проверку.";
    const tried = next && next.attempts
      ? ` · ${ruCount(next.attempts, ["попытка", "попытки", "попыток"])}` +
        (next.accuracy != null ? `, ${Math.round(next.accuracy * 100)}% верно` : "")
      : "";
    // Where the topic sits in the course: its unit, else (an older payload) its level.
    const unit = p.units?.find(u => u.topics.includes(next?.id));
    $("#pathOf").innerHTML = next
      ? `${next.ru ? `<span lang="ru">${esc(next.ru)}</span> · ` : ""}${unit
        ? `<span lang="et">${unit.n}. ${esc(unit.et)}</span>` : esc(next.level)}${tried}`
      : `${p.mastered}/${p.total} тем`;
    p.topics.forEach(t => { pathMeta[t.id] = t; });
    paintTheme();
    setLabel($("#practiceBtn"), sessionTopic ? "Jätka" : "Alusta");
    $("#practiceBtn .ru").textContent = sessionTopic ? "продолжить урок" : "начать урок";
    $("#practiceBtn").disabled = !next && !sessionTopic;
    $("#practiceBtn").hidden = false;
    /* One topic's row: state, name, gloss, and its actions. */
    const topicRow = t => {
      /* Names, not ids — the API resolves them. Tolerant of an older payload so a
         stale cached page never prints "undefined". */
      const needs = t.blocked_by || [];
      const meta = [
        t.ru ? `<span lang="ru">${esc(t.ru)}</span>` : "",
        needs.length ? `<span lang="ru">после:</span> <span lang="et">${esc(needs.join(", "))}</span>` : "",
        t.accuracy === null || t.accuracy === undefined ? "" : `${Math.round(t.accuracy * 100)}%`,
      ].filter(Boolean).join(" · ");
      const rule = `<button class="quiet" data-lesson="${esc(t.id)}" lang="et">reegel <i class="ru" lang="ru">правило</i></button>`;
      const acts = `<span class="acts"><button class="ghost" data-topic="${esc(t.id)}" lang="et">Õpi <i class="ru" lang="ru">изучить</i></button>
        <details class="topic-options"><summary lang="et">Veel <span class="ru" lang="ru">действия</span></summary>
        ${rule}${t.state !== "reference" ? `<button class="quiet" data-testout="${esc(t.id)}" lang="et">Kontrolli teadmisi <span class="ru" lang="ru">проверить знания</span></button>` : ""}
        ${t.state === "mastered" ? "" : `<button class="quiet" data-skip="${esc(t.id)}" data-skipped="${t.state === "skipped"}" lang="et">${t.state === "skipped" ? "Too tagasi" : "Jäta vahele"}<span class="ru" lang="ru">${t.state === "skipped" ? "вернуть в маршрут" : "пропустить тему"}</span></button>`}</details></span>`;
      return `<div class="topic ${t.state.replace(" ", "-")}${t.id === p.resume ? " now" : ""}">
        <span class="st" title="${esc(RU[t.state] || t.state)}">${stateIcon(t.state)}<span class="st-word" lang="ru">${esc(RU[t.state] || t.state)}</span></span>
        <span class="name" lang="et">${esc(t.et)}</span>
        ${meta ? `<span class="meta">${meta}</span>` : ""}
        ${acts}</div>`;
    };
    const fold = (open, head, hint, body) => `<details class="path-level"${open ? " open" : ""}><summary>${head}
        <span class="hint">${hint}</span>${icon("caret-down", {cls: "fold-chevron"})}</summary>${body}</details>`;
    const byId = Object.fromEntries(p.topics.map(t => [t.id, t]));
    /* The course, unit by unit (`docs/course-structure.md`); an older payload
       without units keeps the level-by-level path. */
    $("#pathList").innerHTML = p.units ? p.units.map(u => {
      const here = u.topics.map(id => byId[id]).filter(Boolean);
      const stage = u.stage === "algus" ? "Algus" : `sihttase ${u.stage}`;
      const revisits = u.revisits.map(r => `<p class="hint"><button class="quiet" data-topic="${esc(r.topic)}"
          data-rules="${esc(r.rules.join(","))}" lang="et">Kordus: ${esc(byId[r.topic]?.et || r.topic)}
          <span class="ru" lang="ru">повторить с новым правилом</span></button>${r.note_ru ? ` <span lang="ru">${esc(r.note_ru)}</span>` : ""}</p>`).join("");
      const words = u.words.length ? `<details class="topic-options"><summary lang="et">Esimesed sõnad <span class="ru" lang="ru">первые слова</span></summary>
          <p>${u.words.map(w => `<span lang="et">${esc(w.et)}</span>${w.ru.length ? ` <i lang="ru">${esc(w.ru[0])}</i>` : ""}`).join(" · ")}</p>
          <p class="hint"><a href="${esc(u.pictures_url)}" target="_blank" rel="noopener" lang="et">EKI piltsõnastik</a>
          <span lang="ru">— слова с картинками на Sõnaveeb</span></p></details>` : "";
      const course = u.course_url ? `<p class="hint"><a href="${esc(u.course_url)}" target="_blank" rel="noopener" lang="et">${esc(u.course)}</a>
          <span lang="ru">— бесплатный курс с видео, на внешнем сайте</span></p>` : "";
      const counted = u.skipped ? " · пропущено"
        : u.topics.length ? ` · ${u.mastered} из ${u.topics.length} пройдено` : " · повторение";
      const exam = `<p class="hint"><span lang="et">HARNO: ${esc(u.harno.join("; "))}</span>${u.checkpoint
        ? ` · <span lang="et">Kontrolltöö ${esc(u.checkpoint)}</span> <span lang="ru">— контрольная уровня в конце</span>` : ""}</p>`;
      return fold(u.current, `<span class="lv" data-level="${esc(u.stage)}">${u.n}</span> <span lang="et">${esc(u.et)}</span>`,
        `<span lang="et">${esc(stage)}</span>${counted}`,
        `<p class="why" lang="ru">${esc(u.goal_ru)}</p>${here.map(topicRow).join("")}${revisits}${words}${exam}${course}`);
    }).join("") : [...new Set(p.topics.map(t => t.level))].map(lv => {
      const here = p.topics.filter(t => t.level === lv);
      const done = here.filter(t => t.state === "mastered").length;
      return fold(lv === next?.level, `<span class="lv" data-level="${esc(lv)}">${esc(lv)}</span>`,
        `${done} из ${here.length} пройдено`, here.map(topicRow).join(""));
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
    if (d.rhythm?.length) html += `<details class="progress-details"><summary lang="et">Rütm <span class="ru" lang="ru">история занятий</span></summary><section class="stat-card wide">
      <h3 lang="et">Rütm <i class="ru" lang="ru">занятия по дням, 12 недель</i></h3>
      ${rhythmHtml(d.rhythm)}</section></details>`;
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
        ${s.sonavara.glossed_of ? `<p class="gloss-late">с переводом: ${s.sonavara.glossed} из ${s.sonavara.glossed_of} частотных слов <span class="hint">(словари EKI;
          онлайн-словарь дополняет, сегодня ещё ${s.sonavara.gloss_budget_left} запросов)</span></p>` : ""}</section>`;
      // Two facts, kept apart: "known" is what the learner declared; the glossed count
      // is what the app can translate (EKI's dictionaries, topped up by the live
      // one), so it is not presented as an achievement.
    }
    if (s.raamatukogu) html += `<section class="stat-card">
      <h3 lang="et">Lugemine · Kuulamine <i class="ru" lang="ru">чтение и аудирование</i></h3>
      <div class="stat-big">${s.raamatukogu.items || 0}<small> ${ruCount(s.raamatukogu.items || 0,
        ["материал", "материала", "материалов"]).replace(/^\S+ /, "")}</small></div>
      <p class="why">${ruCount(Math.round(s.raamatukogu.minutes || 0), ["минута", "минуты", "минут"])} с текстами и записями.</p></section>`;
    if (marks.milestones?.length) html += `<details class="progress-details"><summary lang="et">Märgid <span class="ru" lang="ru">этапы обучения</span></summary><section class="stat-card">
      <h3 lang="et">Märgid <i class="ru" lang="ru">вехи ${esc(examLevel())}</i></h3>
      ${sealsHtml(marks.milestones)}
      <p class="hint">Отмечают сделанное; очков и серий нет.</p></section></details>`;
    // The caveat comes from the API, in Russian, so it is written once and matches
    // what the numbers mean.
    html += `<div class="engine">${esc(d.caveat || "")}</div>`;
    out.innerHTML = html;
  } catch (e) { out.textContent = e.message; }
}


$("#pathList").addEventListener("click", async e => {
  const skip = e.target.closest("button[data-skip]");
  if (skip) {
    skip.disabled = true;
    try {
      await api(`/api/course/topics/${encodeURIComponent(skip.dataset.skip)}/skip`,
        {skip: skip.dataset.skipped !== "true"});
      await loadPath();
    } catch (error) { skip.disabled = false; skip.parentElement.insertAdjacentHTML("beforeend", `<p role="alert">${esc(error.message)}</p>`); }
    return;
  }
  const test = e.target.closest("button[data-testout]");
  if (test) { startTestOut(test.dataset.testout); return; }
  const b = e.target.closest("button[data-topic]");
  // A unit's revisit practises only the rules its stage unlocks.
  if (b) {
    pathRules = b.dataset.rules ? {topic: b.dataset.topic, rules: b.dataset.rules.split(",")} : null;
    beginLesson(b.dataset.topic);
  }
});

function sessionStep(step) {
  document.querySelectorAll(".lesson-steps li").forEach(li => {
    if (li.dataset.step === step) li.setAttribute("aria-current", "step");
    else li.removeAttribute("aria-current");
  });
}
function showSession() {
  const hash = "#session/" + encodeURIComponent(sessionTopic || pathTopic || "");
  if (location.hash !== hash) location.hash = hash;
}
export async function ensureSession(topic) {
  if (sessionTopic && (!topic || sessionTopic === topic)) return;
  if (!topic) await loadPath();
  beginLesson(topic || pathTopic);
}
async function beginLesson(topic = pathTopic) {
  if (!topic) return;
  const request = ++lessonRequest;
  sessionTopic = topic; pathTopic = topic;
  showSession(); sessionStep("learn");
  $("#pathRada").hidden = true;
  const intro = $("#lessonIntro"); intro.hidden = false;
  intro.innerHTML = '<p role="status">Загружаю правило и примеры…</p>';
  try {
    const lesson = await api(`/api/lesson/${encodeURIComponent(topic)}`, null, "GET").then(r => r.json());
    if (request !== lessonRequest) return;
    setLabel($("#sessionTitle"), lesson.et);
    const points = lesson.points_ru || [];
    intro.innerHTML = `<div class="lesson-copy">
      <p class="lesson-gist" lang="ru">${md(lesson.tip?.gist_ru || lesson.rule?.summary_ru || lesson.ru || "")}</p>
      ${points.length ? `<ul>${points.slice(0, 3).map(point => `<li>${md(point)}</li>`).join("")}</ul>` : ""}
      ${(lesson.examples || []).length ? `<div class="lesson-examples" lang="et">${lesson.examples.slice(0, 3).map(ex => `<p>${esc(ex.before)}<strong>${esc(ex.answer)}</strong>${esc(ex.after)}</p>`).join("")}</div>` : ""}
      <div class="lesson-source" lang="ru">${(lesson.sources || []).map(ref => `<a href="${esc(ref.url)}" target="_blank" rel="noopener">${esc(ref.label)}</a>`).join(" · ")}</div>
      <button class="quiet" data-lesson="${esc(topic)}" lang="et">Reegel tervikuna <span class="ru" lang="ru">полное правило</span></button></div>
      <div class="lesson-actions">${lesson.drillable ? `<button class="go" id="beginPractice" lang="et">Harjuta <span class="ru" lang="ru">попробовать на заданиях</span></button>` : `<a class="go" href="#course" lang="et">Kursuse juurde <span class="ru" lang="ru">к темам курса</span></a>`}
      <button class="quiet" id="skipLesson" lang="et">Tean juba — jäta vahele <span class="ru" lang="ru">уже знаю — пропустить тему</span></button></div>`;
    $("#beginPractice")?.addEventListener("click", () => startPractice({focus: false}));
    $("#skipLesson").onclick = async () => {
      $("#skipLesson").disabled = true;
      try { await api(`/api/course/topics/${encodeURIComponent(topic)}/skip`, {skip: true}); sessionTopic = null; await loadPath(); location.hash = "#path"; }
      catch (error) { $("#skipLesson").disabled = false; intro.insertAdjacentHTML("beforeend", `<p role="alert">${esc(error.message)}</p>`); }
    };
    loadPath();
  } catch (error) {
    intro.innerHTML = `<p role="alert">${esc(error.message)}</p><button class="go" id="retryLesson" lang="et">Proovi uuesti <span class="ru" lang="ru">загрузить урок ещё раз</span></button>`;
    $("#retryLesson").onclick = () => beginLesson(topic);
  }
}

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
  sessionTopic = topic;
  showSession(); sessionStep("check");
  $("#lessonIntro").hidden = true; $("#pathRada").hidden = false;
  setLabel($("#sessionTitle"), pathMeta[topic]?.et || "Kontroll");
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
        ${sayHtml(it)}
        <div class="row"><span class="hint" lang="et">${esc(it.hint || "")}</span>
          ${it.choices && it.choices.length
            ? `<select lang="et" aria-label="Vastus — ответ"><option value=""></option>${it.choices.map(c =>
                `<option value="${esc(c)}">${esc(c)}</option>`).join("")}</select>`
            : `<input type="text" size="16" lang="et" aria-label="Vastus — ответ" ${ANSWER_FIELD}>`}</div>
        ${attribHtml(it)}
      </div>`).join("")}</div>
    <div class="row"><button class="go" id="testoutDone" lang="et">Valmis
      <span class="ru" lang="ru">проверить</span></button></div>
    <div class="verdict" id="testoutVerdict" role="status"></div>`;
  out.querySelector("input, select")?.focus();
  wireSay(out, message => { $("#testoutVerdict").textContent = message; });
  $("#testoutDone").onclick = async () => {
    $("#testoutDone").disabled = true;
    const given = [...out.querySelectorAll("#testoutTasks .mock-task")]
      .map(task => task.querySelector("input, select").value);
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
  showSession(); sessionStep("practice");
  $("#lessonIntro").hidden = true; $("#pathRada").hidden = false;
  sessionTopic = pathTopic;
  /* The auto-start and a topic picked from Kogu rada can be in flight together; only
     the latest may paint, or a slow first answer replaces the learner's choice. */
  const mine = ++practiceRequest;
  const out = $("#practiceOut"); out.innerHTML = "";
  $("#pathRada").classList.remove("has-running-set");
  newSet(pathTally);
  $("#pathScore").textContent = "";
  const btn = $("#practiceBtn"); btn.disabled = true; setLabel(btn, "Laadin…");
  try {
    const body = {count: 5};
    if (pathTopic) body.topic = pathTopic;
    if (pathRules && pathRules.topic === pathTopic) body.rules = pathRules.rules;
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
    /* The topic line above already names the resume topic; the head names it only
       when a different one was picked from the list. */
    const bits = [];
    if (res.et !== $("#pathNow").textContent)
      bits.push(`<strong lang="et">${esc(res.et)}</strong> · ${esc(res.level)}`);
    /* A short set is not a broken one, but silence would read as "this topic only has
       three". */
    if (res.theme && res.items.length < 10)
      bits.push(`<span class="hint">по этой теме нашлось ${res.items.length}</span>`);
    /* A plain line, not a banner: the set starts right under it. The rule is a
       quiet action at its end, one tap away without competing with the drill. */
    out.innerHTML = `<div class="set-head"><span>${bits.join(" · ")}</span>
      <button class="quiet" type="button" data-lesson="${esc(res.topic)}" lang="et">reegel
        <i class="ru" lang="ru">правило</i></button></div>`;
    loaded = true;
    $("#pathRada").classList.add("has-running-set");
    pathTally.size = res.items.length;
    paintBeads(pathTally);
    res.items.forEach((it, i) =>
      out.appendChild(renderPracticeItem(it, res.topic, i, res.glosses || {}, focus)));
    // A phone session opens on the task. Added reading support must not push
    // its answer below the dock; scroll without opening the software keyboard.
    if (matchMedia("(max-width:719px), (hover:none) and (max-width:1079px) and (max-height:559px)").matches) {
      requestAnimationFrame(() => {
        const first = out.querySelector(".drill");
        if (first?.checkVisibility()) first.scrollIntoView({block: "start", behavior: "instant"});
      });
    }
  } catch (e) {
    if (mine !== practiceRequest) return;
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  } finally {
    // A superseded request leaves the button to the one that replaced it.
    if (mine !== practiceRequest) return;
    btn.disabled = false;
    /* With a set on screen, answering is the main action; the button only swaps
       the set, so it steps down to a secondary one. */
    btn.className = "go";
    // With a set on screen the next set is offered at its end, not above it.
    btn.hidden = false;
    btn.querySelector(".btn-ico")?.replaceWith(
      document.createRange().createContextualFragment(uiIcon(loaded ? "next" : "play")));
    const [et, ru] = loaded ? ["Jätka", "продолжить урок"] : ["Alusta", "начать урок"];
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
      `<b>${esc(blankForm(it.prompt, it.answer.split(" ~ ")[0]))}</b>`)}</li>`).join("")}</ul>` : "";
  const redo = tally.missed.length && tally.redo !== false
    ? `<button class="ghost" data-act="redo" lang="et">Korda vigu <span class="ru" lang="ru">повторить ошибки</span></button>` : "";
  if (tally === pathTally) sessionStep("check");
  const progress = tally.skipped ? `<p lang="ru">Пропущено: ${tally.skipped}. Они не проверены и не засчитаны.</p>` : "";
  const advance = tally === pathTally && (res.just_mastered || pathMeta[sessionTopic]?.state === "mastered");
  const continuation = `<button class="go" data-act="new" lang="et">${uiIcon("next")}${advance ? "Järgmine teema" : "Uued laused"} <span class="ru" lang="ru">${advance ? "следующая тема" : "ещё задания"}</span></button>
    <a class="ghost" href="#path" lang="et">Kodu <span class="ru" lang="ru">на главную</span></a>`;
  const end = document.createElement("div");
  /* The score, the beads again, and the next set under the thumb. A set nearly all
     right wears moss; the count is the reward, not a streak. */
  end.className = "set-end";
  if (tally.size && tally.correct >= 0.8 * tally.size) end.classList.add("great");
  end.setAttribute("role", "status");
  end.innerHTML = `<h4 lang="et">Komplekt tehtud <i class="ru" lang="ru">набор пройден</i></h4>
    <p class="set-score">${tally.correct}<small> из ${tally.answered} проверенных верно</small></p>
    <div class="beads" aria-hidden="true">${beadsHtml(tally)}</div>${gate}${progress}${missed}
    <div class="row">${redo}${continuation}</div>`;
  end.querySelector('[data-act="new"]').onclick = advance ? async e => {
    const button = e.currentTarget;
    button.disabled = true;
    try {
      const p = await (await api("/api/curriculum", null, "GET")).json();
      if (p.resume) await beginLesson(p.resume);
      else location.hash = "#course";
    } catch (error) {
      button.disabled = false;
      end.insertAdjacentHTML("beforeend", `<p class="banner">Следующая тема не загрузилась: ${esc(error.message)}. Попробуй ещё раз.</p>`);
    }
  } : tally.again;
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
  // First exposure offers recognition before recall, using only issued forms.
  // The signed server item still grades the selected form; skipping submits none.
  if (tally === pathTally && !(pathMeta[topic]?.attempts) && !it.choices?.length
      && it.distractor && !it.answer.split(" ~ ").includes(it.distractor)) {
    const options = [it.answer.split(" ~ ")[0], it.distractor];
    it = {...it, choices: i % 2 ? options : options.reverse()};
  }
  /* What the word means, when the app already knows.

     The gloss comes from the local store, so it is either instantly there or
     absent — a practice set never waits on a dictionary.

     A küsisõnad item has no lemma — its word is the answer — so it carries
     `answer_ru` instead: EKI's Russian for the question word the blank wants
     (где, куда), which says what to ask without printing the Estonian. */
  const ru = (it.answer_ru && it.answer_ru.length)
    ? it.answer_ru : (glosses || {})[it.lemma] || [];
  const el = document.createElement("div");
  el.className = "drill guided-item";
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
     submitted as the answer and graded by the same comparison as everything else.
     Outside the owner's corpus it is EKI's phrase rebuilt from its words: the
     built phrase is the answer, graded the same way (`wordorder.phrase_tiles`). */
  const tiles = it.tiles?.length ? it.tiles : null;
  el.innerHTML = `${pos}
    ${tiles ? `
    <div class="prompt tile-build" lang="et">
      <div class="fc-line" aria-label="Fraas — фраза" aria-live="polite"></div>
      <div class="fc-bank"></div>
    </div>
    <div class="row">
      <button class="ghost" lang="et" disabled aria-label="Kontrolli ${place} — проверить">Kontrolli</button>
      ${taskLine(it, ru)}
    </div>` : `
    <div class="prompt" lang="et">${esc(it.prompt).replace("____", '<span class="blank">____</span>')}</div>
    ${sayHtml(it)}`}
    ${tiles ? "" : it.choices && it.choices.length ? `
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
    ${attribHtml(it)}
    <div class="verdict" role="status"></div>`;
  addPracticeSupport(el, it);
  const input = el.querySelector("input"), verdict = el.querySelector(".verdict");
  wireSay(el, message => { verdict.className = "verdict no"; verdict.textContent = message; });
  // One answer keeps one identity while the learner retries a durability 503.
  // The origin already deduplicates event_id, so a confirmed-but-interrupted
  // first response cannot count the same drill twice.
  const eventId = tally.record ? crypto.randomUUID() : "";
  addMic(input?.parentElement, input, it.prompt);
  const choices = [...el.querySelectorAll(".choice")];
  // One holder for "what was answered", whichever shape the item took, so the
  // submit path below stays single.
  let picked = "";
  let submittedGiven = null;
  let submittedLatency = null;
  let inFlight = false;
  const check = el.querySelector(".row > button.ghost");
  const tileButtons = () => [...el.querySelectorAll(".fc-tile")];
  const lock = () => {
    inFlight = true;
    if (input) input.disabled = true;
    if (check) check.disabled = true;
    choices.forEach(b => b.disabled = true);
    tileButtons().forEach(b => b.disabled = true);
  };
  const unlockRetry = () => {
    inFlight = false;
    if (input) input.disabled = tally.record;
    if (check) check.disabled = false;
    choices.forEach(b => {
      b.disabled = tally.record && b.dataset.choice !== submittedGiven;
      if (!tally.record) b.classList.remove("picked");
    });
    tileButtons().forEach(b => b.disabled = tally.record);
    if (!tally.record) {
      submittedGiven = null;
      submittedLatency = null;
    }
  };
  const locked = () => inFlight;

  const grade = async () => {
    if (locked()) return;
    /* An empty box is not an answer. Here it would also be recorded: against the
       accuracy that gates mastery, and into the review queue. The first item is
       focused on load, so one stray Enter would do it. Ask again instead. */
    if (input && !input.value.trim()) {
      verdict.className = "verdict";
      verdict.innerHTML = `<span class="hint">Впиши форму — тогда проверю.</span>`;
      input.focus();
      return;
    }
    submittedGiven ??= input ? input.value : picked;
    submittedLatency ??= Math.round(performance.now() - (started ?? rendered));
    lock();
    let res;
    try {
      // The server grades and records: the client must not be the judge of
      // whether a topic has been mastered.
      // The token is what the server grades from; the rest is for a page
      // cached from before tokens existed.
      res = await (await api("/api/practice/answer", {
        topic, prompt: it.prompt, answer: it.answer,
        given: submittedGiven,
        distractor: it.distractor || "", lemma: it.lemma || "",
        label: it.hint || "", rule: it.rule || "", why_ru: it.why_ru || "",
        token: it.token || "",
        event_id: eventId,
        latency_ms: submittedLatency,
        record: tally.record,
      })).json();
    } catch (e) {
      /* The item is not spent. Recorded practice retries the same event and
         answer; free practice lets the learner edit the answer. */
      unlockRetry();
      verdict.className = "verdict no";
      verdict.innerHTML = `${tally.record
        ? "Сохранение ответа пока не подтверждено."
        : "Ответ пока не проверен."} ${esc(e.message)}
        <span class="hint">Задание осталось на экране.</span>`;
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
    const said = res.correct && input ? submittedGiven.trim() : it.answer.split(" ~ ")[0];
    if (blank) {
      blank.textContent = blankForm(it.prompt, said);
      blank.classList.add("filled", res.correct ? "ok" : "no");
    }
    // A miss goes on the set's list, to be looked at and redone at its end.
    if (!res.correct) tally.missed.push({it, topic});
    // Correction stays with this task until the learner chooses to continue.
    // No completed stack can move the next question down the workspace.
    el.classList.add("done", "await-next");
    el.querySelector(".exercise-skip").hidden = true;
    requestAnimationFrame(() => verdict.scrollIntoView({block: "nearest"}));
    verdict.className = "verdict " + (res.correct ? "ok" : "no");
    // A choice item's prompt is a question with no blank, so the answered sentence is
    // shown instead. The rule is shown either way: on a right answer it says why,
    // which for word order is the lesson.
    verdict.innerHTML = res.correct
      ? ((choices.length || tiles) && !blank
          ? `<span lang="et">✓ õige <i class="ru" lang="ru">верно</i></span> — <strong lang="et">${esc(it.answer)}</strong><br>
             <span class="why">${md(it.why_ru || "")}</span>`
          : `<span lang="et">✓ õige <i class="ru" lang="ru">верно</i></span> — <strong lang="et">${esc(it.prompt.replace("____", blankForm(it.prompt, said)))}</strong>`
            // A choice topic hid its form until now; the rule is the lesson either way.
            + (it.form_after ? `<br><span class="why">${md(it.why_ru || "")}</span>` : ""))
      : wrongVerdict(submittedGiven, it.answer, it.why_ru);
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
    awaitForward(res);
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
  } else if (tiles) {
    // A tap moves a word between the bank and the phrase; the check opens once
    // every word is placed, and the phrase as built is what is graded.
    const line = el.querySelector(".fc-line"), bank = el.querySelector(".fc-bank");
    tiles.forEach(word => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "ghost fc-tile"; b.lang = "et"; b.textContent = word;
      b.onclick = () => {
        if (locked() || el.classList.contains("done")) return;
        (b.parentElement === bank ? line : bank).appendChild(b);
        picked = [...line.children].map(x => x.textContent).join(" ");
        check.disabled = line.children.length !== tiles.length;
      };
      bank.appendChild(b);
    });
    check.onclick = grade;
  } else {
    check.onclick = grade;
    input.addEventListener("keydown", e => { if (e.key === "Enter") grade(); });
    if (i === 0 && focus) setTimeout(() => input.focus(), 0);
  }
  const skip = document.createElement("button");
  skip.className = "quiet exercise-skip"; skip.lang = "et";
  skip.innerHTML = '<span lang="et">Jäta ülesanne vahele <span class="ru" lang="ru">пропустить задание</span></span>';
  skip.onclick = () => {
    if (inFlight || el.classList.contains("done")) return;
    el.classList.add("done", "skipped", "await-next"); tally.skipped = (tally.skipped || 0) + 1;
    tally.marks[i] = "skipped"; paintBeads(tally);
    input && (input.disabled = true); if (check) check.disabled = true;
    choices.forEach(b => b.disabled = true);
    tileButtons().forEach(b => b.disabled = true);
    verdict.textContent = "Пропущено — ответ не проверен и не засчитан. Можно попробовать в следующем наборе.";
    skip.hidden = true;
    awaitForward({});
  };
  const feedback = document.createElement("div");
  feedback.className = "exercise-feedback";
  el.appendChild(feedback);
  feedback.appendChild(verdict);
  const actions = document.createElement("div");
  actions.className = "exercise-actions";
  actions.appendChild(skip);
  const forward = document.createElement("button");
  forward.className = "go exercise-next"; forward.lang = "et"; forward.hidden = true;
  forward.innerHTML = '<span lang="et">Edasi <span class="ru" lang="ru">дальше</span></span>';
  actions.appendChild(forward); feedback.appendChild(actions);
  function awaitForward(res) {
    forward.hidden = false;
    forward.onclick = () => {
      forward.disabled = true;
      const box = $(tally.box);
      let history = box.parentElement.querySelector(".session-history");
      if (!history) {
        history = document.createElement("details"); history.className = "session-history fold";
        history.innerHTML = '<summary lang="et">Minu vastused <span class="ru" lang="ru">ответы этого набора</span></summary><ol></ol>';
        box.after(history);
      }
      const entry = document.createElement("li");
      const sentence = document.createElement("p"); sentence.lang = "et";
      sentence.textContent = tiles ? it.answer : el.querySelector(".prompt").textContent;
      const result = verdict.cloneNode(true);
      result.removeAttribute("role");
      result.querySelectorAll("button").forEach(button => button.remove());
      result.querySelectorAll(".row:empty").forEach(row => row.remove());
      entry.append(sentence, result); history.querySelector("ol").appendChild(entry);
      el.classList.remove("await-next"); el.classList.add("archived"); el.hidden = true;
      if (tally.answered + (tally.skipped || 0) === tally.size) finishSet(tally, res);
      else {
        const next = box.querySelector(".drill:not(.done)");
        next?.scrollIntoView({block: "nearest"});
        next?.querySelector("input, .choice, .fc-tile")?.focus({preventScroll: true});
      }
    };
  }
  return el;
}


$("#practiceBtn").onclick = () => {
  if (sessionTopic) showSession(); else beginLesson();
};
// A new word theme is a new set: with the button folded into the end card, the
// select itself starts it.
$("#wordTheme").addEventListener("change", () => startPractice());


// ── Rada or Vaba harjutus ───────────────────────────────────────────
/* One panel, two ways through the same drills. The switch changes only what is
   recorded: Vaba harjutus is graded by the same server code, with `record: false`. */
export function setPathMode(mode) {
  document.querySelectorAll("#pathModes button").forEach(b =>
    b.setAttribute("aria-selected", b.dataset.pm === mode));
  $("#courseTopics").hidden = mode !== "rada";
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
    await offline.fetchPack(5);
    await paintOffline();
  } catch (e) {
    $("#offlineState").textContent = "Не скачалось: " + e.message;
  } finally { btn.disabled = false; }
};

$("#offlinePractice").onclick = async () => {
  const pack = await offline.savedPack();
  if (!pack) return;
  sessionTopic = pack.items[0]?.topic || pathTopic;
  showSession(); sessionStep("practice");
  $("#lessonIntro").hidden = true;
  $("#pathRada").hidden = false;
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
      ${it.choices && it.choices.length
        ? `<select lang="et" aria-label="Vastus — ответ"><option value=""></option>${it.choices.map(c =>
            `<option value="${esc(c)}">${esc(c)}</option>`).join("")}</select>`
        : `<input type="text" size="18" lang="et" aria-label="Vastus — ответ" ${ANSWER_FIELD}>`}
      <button class="go" lang="et">Kontrolli <span class="ru" lang="ru">проверить</span></button>
      ${taskLine({lemma: it.lemma, lemma_ru: it.lemma_ru, label: it.hint || "", level: it.level || ""},
                 ru, {quiet: true})}
    </div>
    ${attribHtml(it)}
    <div class="verdict" role="status"></div>`;
  addPracticeSupport(el, it, {offline: true});
  const input = el.querySelector("input, select"), verdict = el.querySelector(".verdict");
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
      blank.textContent = blankForm(it.prompt, ok ? input.value.trim() : it.answer.split(" ~ ")[0]);
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
  paintTheme();
  startPractice();
});
