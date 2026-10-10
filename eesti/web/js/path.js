/* Täna and Kursus: today's session at a glance (ADR-0009), the syllabus, free
   practice, the offline pack and the progress page. The session itself runs in
   `session.js`. */

import {RU, celebrate, forecastHtml, rhythmHtml, sealsHtml, stateIcon, uiIcon} from "./chrome.js";
import {$, api, attribHtml, blankForm, esc, glide, interlinear, md, ruCount, setLabel, taskLine,
  wrongVerdict, addPracticeSupport} from "./core.js";
import {sayHtml, wireSay} from "./media.js";
import * as offline from "./offline.js";
import {loadReminders} from "./remind.js";
import {addMic} from "./voice.js";
import {loadRail, refreshDueBadge} from "./review.js";
import {examLevel} from "./state.js";
import {icon} from "./icons.js";
import {etCount, openTopic, startCheckSet, STEP_UNITS} from "./session.js";


// ── Täna ────────────────────────────────────────────────────────────
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

/* A sentence of the rule walk with its word underlined and not named: the
   learner has not tried yet (DESIGN.md, Principles). */
const noticeLine = e => `<p class="tana-sent" lang="et">${esc(e.before)}${interlinear(e.form, {}, {state: "notice"})}${esc(e.after)}</p>`;

function heroHtml(t) {
  const s = t.session, h = t.hero;
  if (s.done) {
    const done = s.steps.map(st => `${st.et}`).join(", ");
    return `<p class="tana-done" lang="et">Tänane tund on tehtud <span class="ru" lang="ru">занятие на сегодня пройдено</span></p>
      <p class="tana-lead" lang="ru">Сделано: <span lang="et">${esc(done)}</span>.</p>`;
  }
  if (h.kind === "notice")
    return `<div class="tana-notice">${h.examples.map(noticeLine).join("")}</div>
      <p class="tana-lead" lang="ru">${md(h.question_ru)} Сначала попробуешь сам, потом прочитаешь правило.</p>`;
  return `<p class="tana-unit-title" lang="et">${esc(h.et)}</p>
    <p class="tana-lead" lang="ru">${esc(h.goal_ru)}</p>`;
}

const STATE_ET = {done: ["tehtud", "сделано"], current: ["praegu", "сейчас"], todo: ["", ""]};

function stepRow(st) {
  const [unitOne, unitMany] = STEP_UNITS[st.id] || ["", ""];
  const count = unitOne ? etCount(st.count, unitOne, unitMany) : "";
  const [stateEt, stateRu] = STATE_ET[st.state] || ["", ""];
  return `<li class="tana-step" data-state="${esc(st.state)}"${st.state === "current" ? ' aria-current="step"' : ""}>
    <span class="tana-dot" aria-hidden="true"></span>
    <span class="tana-step-name" lang="et">${esc(st.et)} <span class="ru" lang="ru">${esc(st.ru)}</span></span>
    <span class="tana-step-count" lang="et">${esc(count)}${stateEt ? `<span class="sr-only">, ${esc(stateEt)}</span>` : ""}</span></li>`;
}

const altRow = a => `<li><a href="${esc(a.href)}" lang="et">${esc(a.et)} <span class="ru" lang="ru">${esc(a.ru)}</span></a>
  <p class="tana-alt-why" lang="ru">${esc(a.why_ru)}</p></li>`;

let todayLoad = 0;
export async function loadToday() {
  paintDate();
  const mine = ++todayLoad;
  const btn = $("#practiceBtn");
  try {
    const t = await (await api("/api/session", null, "GET")).json();
    if (mine !== todayLoad) return;
    const s = t.session, next = t.next;
    $("#tanaHero").innerHTML = heroHtml(t);
    const unit = s.unit;
    $("#tanaUnit").innerHTML = `<span lang="et">${unit.n}. ${esc(unit.et)}
      <span class="ru" lang="ru">занятие ${s.n} из ${s.of}: ${esc(s.emphasis.ru)}</span></span>`;
    // Before the first session: what a session gives, in one sentence.
    $("#tanaFirst").hidden = !t.first;
    $("#tanaSteps").innerHTML = s.steps.map(stepRow).join("");
    $("#tanaAlt").innerHTML = next.alternatives.map(altRow).join("");
    const primary = next.primary;
    const minutes = primary.minutes ? `, ${primary.minutes} мин` : "";
    if (primary.kind === "session") {
      // Alusta until the day's session has begun; then Jätka.
      const begun = t.started || s.steps.some(st => st.state === "done");
      setLabel(btn, begun ? "Jätka" : "Alusta");
      btn.querySelector(".ru").textContent = `${begun ? "продолжить" : "начать"}${minutes}`;
      $("#tanaWhy").textContent = "";
    } else {
      setLabel(btn, primary.et);
      btn.querySelector(".ru").textContent = primary.ru + minutes;
      $("#tanaWhy").textContent = primary.why_ru;
    }
    btn.dataset.href = primary.href;
    btn.disabled = false;
  } catch (e) {
    if (mine !== todayLoad) return;
    $("#tanaHero").innerHTML = `<div class="banner recoverable-error" role="alert">${esc(e.message)}
      <button class="ghost" id="tanaRetry" type="button" lang="et">Proovi uuesti <span class="ru" lang="ru">загрузить ещё раз</span></button></div>`;
    $("#tanaRetry").onclick = loadToday;
    btn.disabled = true;
  }
}

$("#practiceBtn").onclick = () => {
  const href = $("#practiceBtn").dataset.href || "#session";
  if (location.hash !== href) location.hash = href;
};


// ── Kursus ──────────────────────────────────────────────────────────
let pathMeta = {};
/* What the learner types is the thing being graded: iOS must not capitalise it,
   correct it or underline it, and a password manager must not offer to fill it. */
const ANSWER_FIELD = `autocapitalize="off" autocorrect="off" spellcheck="false" autocomplete="off"`;

let pathLoad = 0;

export async function loadPath() {
  const mine = ++pathLoad;
  try {
    const p = await (await api("/api/curriculum", null, "GET")).json();
    if (mine !== pathLoad) return;
    p.topics.forEach(t => { pathMeta[t.id] = t; });
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
      const counted = u.complete ? " · блок пройден"
        : u.skipped ? " · пропущено"
        : u.topics.length ? ` · ${u.mastered} из ${u.topics.length} пройдено` : " · повторение";
      const check = u.checkable ? `<p class="hint"><button class="ghost" data-unitcheck="${esc(u.id)}"
          data-title="${esc(u.et)}" data-first="${esc(u.topics[0] || "")}" lang="et">Ühiku kontroll <span class="ru" lang="ru">${u.checked
          ? "проверка пройдена, можно ещё раз" : "проверить блок"}</span></button></p>` : "";
      /* Navigation only (ADR-0009): a skipped unit's topics are not mastered,
         and every skip can be undone. "Alusta siit" moves past all earlier units. */
      const earlier = p.units.slice(0, p.units.indexOf(u))
        .filter(e => e.topics.length && !e.skipped && !e.complete).map(e => e.id);
      const moves = u.complete || !u.topics.length && !earlier.length ? "" : `<p class="hint unit-moves">${u.topics.length && !u.complete
        ? `<button class="quiet" data-unitskip="${esc(u.id)}" data-unitmove="${u.skipped ? "back" : "skip"}" lang="et">${u.skipped
          ? `<span lang="et">Too ühik tagasi <span class="ru" lang="ru">вернуть блок в маршрут</span></span>`
          : `<span lang="et">Jäta ühik vahele <span class="ru" lang="ru">пропустить блок</span></span>`}</button>` : ""}${earlier.length
        ? ` <button class="quiet" data-unitskip="${esc(earlier.join(","))}" data-unitmove="skip" lang="et">Alusta siit
          <span class="ru" lang="ru">начать с этого блока: пропустить ${earlier.length === 1 ? "предыдущий блок" : `предыдущие блоки (${earlier.length})`}</span></button>` : ""}</p>`;
      const exam = `<p class="hint"><span lang="et">HARNO: ${esc(u.harno.join("; "))}</span>${u.checkpoint
        ? ` · <span lang="et">Kontrolltöö ${esc(u.checkpoint)}</span> <span lang="ru">— контрольная уровня в конце</span>` : ""}</p>`;
      return fold(u.current, `<span class="lv" data-level="${esc(u.stage)}">${u.n}</span> <span lang="et">${esc(u.et)}</span>`,
        `<span lang="et">${esc(stage)}</span>${counted}`,
        `<p class="why" lang="ru">${esc(u.goal_ru)}</p>${here.map(topicRow).join("")}${revisits}${check}${words}${exam}${course}${moves}`);
    }).join("") : [...new Set(p.topics.map(t => t.level))].map(lv => {
      const here = p.topics.filter(t => t.level === lv);
      const done = here.filter(t => t.state === "mastered").length;
      return fold(here.some(t => t.id === p.resume), `<span class="lv" data-level="${esc(lv)}">${esc(lv)}</span>`,
        `${done} из ${here.length} пройдено`, here.map(topicRow).join(""));
    }).join("");
  } catch (e) {
    if (mine !== pathLoad) return;
    $("#pathList").innerHTML = `<div class="banner" role="alert">${esc(e.message)}</div>`;
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
  const units = e.target.closest("button[data-unitskip]");
  if (units) {
    units.disabled = true;
    try {
      await api("/api/course/units/skip",
        {units: units.dataset.unitskip.split(","), skip: units.dataset.unitmove === "skip"});
      await loadPath();
    } catch (error) { units.disabled = false; units.parentElement.insertAdjacentHTML("beforeend", `<p role="alert">${esc(error.message)}</p>`); }
    return;
  }
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
  if (test) { startCheckSet({kind: "testout", topic: test.dataset.testout, et: pathMeta[test.dataset.testout]?.et}); return; }
  const unitCheck = e.target.closest("button[data-unitcheck]");
  if (unitCheck) {
    startCheckSet({kind: "unit", unit: unitCheck.dataset.unitcheck, et: unitCheck.dataset.title,
                   topic: unitCheck.dataset.first});
    return;
  }
  const b = e.target.closest("button[data-topic]");
  // A unit's revisit practises only the rules its stage unlocks.
  if (b) openTopic(b.dataset.topic, {rules: b.dataset.rules ? b.dataset.rules.split(",") : null});
});


// ── Free practice and the checkpoint's sets ─────────────────────────
/* A running score for one set. Vaba harjutus is graded by the same server code
   as everything else and recorded nowhere; a Kontrolltöö (exam.js) is recorded. */
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

/* One bead per item in the set: a filled disc for right, a slashed ring for
   wrong, a dash for skipped, a ring for the one being answered. */
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

/* The end of a set: how it went in one line and the next set under the thumb.
   No streak, no confetti: the count is the reward. */
function finishSet(tally, res) {
  const box = $(tally.box);
  if (!box || box.querySelector(".set-end")) return;
  /* What went wrong, in the sentence it went wrong in, with the right form: the end
     of a set is where a learner looks back, so the misses are there to look at. */
  const missed = tally.missed.length ? `<ul class="set-missed" lang="et">${
    tally.missed.map(({it}) => `<li>${esc(it.prompt).replace("____",
      `<b>${esc(blankForm(it.prompt, it.answer.split(" ~ ")[0]))}</b>`)}</li>`).join("")}</ul>` : "";
  const redo = tally.missed.length && tally.redo !== false
    ? `<button class="ghost" data-act="redo" lang="et">Korda vigu <span class="ru" lang="ru">повторить ошибки</span></button>` : "";
  const progress = tally.skipped ? `<p lang="ru">Пропущено: ${tally.skipped}. Они не проверены и не засчитаны.</p>` : "";
  const end = document.createElement("div");
  end.className = "set-end";
  if (tally.size && tally.correct >= 0.8 * tally.size) end.classList.add("great");
  end.setAttribute("role", "status");
  end.innerHTML = `<h4 lang="et">Komplekt tehtud <i class="ru" lang="ru">набор пройден</i></h4>
    <p class="set-score">${tally.correct}<small> из ${tally.answered} проверенных верно</small></p>
    <div class="beads" aria-hidden="true">${beadsHtml(tally)}</div>${progress}${missed}
    <div class="row">${redo}<button class="go" data-act="new" lang="et">${uiIcon("next")}Uued laused <span class="ru" lang="ru">ещё задания</span></button></div>`;
  end.querySelector('[data-act="new"]').onclick = tally.again;
  end.querySelector('[data-act="redo"]')?.addEventListener("click", () => redoMissed(tally));
  $(tally.out).textContent = "";
  box.appendChild(end);
  requestAnimationFrame(() => requestAnimationFrame(() =>
    end.scrollIntoView({block: "nearest", behavior: glide()})));
  tally.done?.(tally);
}

/* The missed items again, as a short set of their own, graded the same way. */
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


export function renderPracticeItem(it, topic, i, glosses, focus = true, tally = freeTally) {
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
      // Mastery, decided by the server, is said once through the live region.
      celebrate({title: "Teema läbitud", name: pathMeta[topic]?.et || topic,
                 note: "Тема пройдена: следующие темы открыты."});
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
    p.topics.forEach(t => { pathMeta[t.id] = t; });
    paintFreeRule();
    paintTheme();
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
$("#freeTopic").onchange = () => { paintFreeRule(); paintTheme(); };

/* The word theme: a theme picks words, the topic picks the rule. Shown only
   where it changes the drill: a closed-class topic (küsisõnad) has no word to
   vary, so the control is reset, disabled and taken off the screen. */
function themeApplies() {
  const meta = pathMeta[$("#freeTopic").value];
  return !meta || meta.themed !== false;
}
function paintTheme() {
  const sel = $("#wordTheme");
  const applies = themeApplies();
  if (!applies) sel.value = "";
  sel.disabled = !applies;
  sel.closest("label").hidden = !applies;
}
async function loadThemes() {
  try {
    const {themes} = await (await api("/api/themes", null, "GET")).json();
    $("#wordTheme").innerHTML = '<option value="" lang="et">kõik sõnad</option>' +
      themes.map(t => `<option value="${esc(t.id)}" lang="et">${esc(t.et)}</option>`).join("");
  } catch { /* the control keeps its one option: every word */ }
}
loadThemes();


/* Folded: one line saying what is being practised, and "Muuda" to change it. */
function foldFreeControls(fold) {
  const pick = sel => sel.options[sel.selectedIndex]?.text || "";
  $("#freeWhat").textContent = [pick($("#freeTopic")),
    $("#freeRule").value ? pick($("#freeRule")) : "",
    $("#wordTheme").value ? pick($("#wordTheme")) : "", pick($("#freeLevel"))]
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
    // A disabled control posts no leftover theme value.
    const theme = themeApplies() ? $("#wordTheme").value : "";
    const res = await (await api("/api/practice", {
      topic: $("#freeTopic").value, count: 10,
      levels: $("#freeLevel").value.split(","),
      ...(rule ? {rules: [rule]} : {}),
      ...(theme ? {theme} : {}),
    })).json();
    if (!res.items.length) {
      out.innerHTML = `<div class="banner">${esc(res.detail || "ничего не пришло")}</div>`;
      /* A topic × theme pair can leave no sentence with a theme noun; the way
         out is one click. */
      if (res.theme_emptied) {
        out.insertAdjacentHTML("beforeend",
          `<button class="ghost" type="button" lang="et">Proovi ilma teemata <span class="ru" lang="ru">без темы</span></button>`);
        out.lastElementChild.onclick = () => { $("#wordTheme").value = ""; $("#freeBtn").click(); };
      }
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



// ── Offline ─────────────────────────────────────────────────────────
/* A pack is fetched while there is a connection and answered without one. The
   page grades by the same rule the server does, queues what was answered, and
   sends it when the connection returns — the server re-grades each answer from
   its token, so nothing here decides what counts (`js/offline.js`). */
const offlineTally = {answered: 0, correct: 0, size: 0, marks: [], beads: "#offlineBeads"};

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
  $("#offlineStage").hidden = false;
  const out = $("#offlineOut");
  out.innerHTML = `<div class="banner info">Офлайн-набор: ответы записываются
    на сервере, когда связь вернётся.</div>`;
  Object.assign(offlineTally, {answered: 0, correct: 0, size: pack.items.length, marks: []});
  paintBeads(offlineTally);
  pack.items.forEach((it, i) => out.appendChild(
    renderOfflineItem(it, i, pack.glosses || {})));
  out.querySelector("input, select")?.focus();
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
    offlineTally.marks[i] = ok;
    offlineTally.answered++; if (ok) offlineTally.correct++;
    paintBeads(offlineTally);
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


