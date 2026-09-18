/* Rada: the syllabus, where you stand on it, and one topic's practice. */

import {RU, stateIcon, uiIcon} from "./chrome.js";
import {$, api, esc, md, ruCount, setLabel, taskLine, wrongVerdict} from "./core.js";
import {loadRail, refreshDueBadge} from "./review.js";

// ── the path ────────────────────────────────────────────────────────
let pathTopic = null;

/* A running score for one set. Rada's is recorded by the server and shows the
   mastery window; Vaba harjutus is graded by the same code and recorded nowhere. */
const pathTally = {answered: 0, correct: 0, out: "#pathScore", record: true};
const freeTally = {answered: 0, correct: 0, out: "#freeScore", record: false};

let pathMeta = {};
let autoStarted = false;
const START = ["Harjuta", "тренировка"], NEW_SET = ["Uued laused", "новые задания"];

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


export async function loadPath() {
  try {
    const p = await (await api("/api/curriculum", null, "GET")).json();
    pathTopic = p.resume;
    const pct = p.total ? Math.round(p.mastered / p.total * 100) : 0;
    const ring = $("#pathRing");
    ring.style.setProperty("--pct", pct);
    ring.querySelector("span").textContent = pct + "%";
    const next = p.topics.find(t => t.id === p.resume);
    $("#pathNow").textContent = next ? next.et : "Все открытые темы пройдены";
    $("#pathOf").textContent =
      `${p.mastered}/${p.total} тем${next ? " · " + next.level : ""}`;
    p.topics.forEach(t => { pathMeta[t.id] = t; });
    paintTheme();
    /* Rada answers "what am I learning today?", so it opens on today's drill, not on
       a button that fetches it. Once per page: coming back to the tab keeps the set
       the learner is in. Nothing is focused, so a phone does not open its keyboard
       over the first sentence. */
    if (!autoStarted && !$("#practiceOut").children.length) {
      autoStarted = true;
      startPractice({focus: false});
    }

    $("#pathList").innerHTML = p.topics.map(t => {
      /* Names, not ids — the API resolves them. Tolerant of an older payload so a
         stale cached page never prints "undefined". */
      const needs = t.blocked_by || [];
      const blocked = needs.length ? ` ← ${needs.join(", ")}` : "";
      const acc = t.accuracy === null ? "" : ` · ${Math.round(t.accuracy * 100)}%`;
      pathMeta[t.id] = t;
      const testOut = t.state === "ready" || t.state === "in progress"
        ? `<button class="ghost" data-topic="${esc(t.id)}">harjuta <i class="ru">решать</i></button>` : "";
      return `<div class="topic ${t.state.replace(" ", "-")}">
        <span class="st">${stateIcon(t.state)}${esc(RU[t.state] || t.state)}</span>
        <span class="lv" data-level="${esc(t.level)}">${esc(t.level)}</span>
        <span>${esc(t.et)}${esc(blocked)}${acc}</span>
        ${testOut}</div>`;
    }).join("");
  } catch (e) {
    $("#pathHead").className = "banner";   // an error is the amber one
    $("#pathHead").hidden = false;
    $("#pathHead").textContent = e.message;
  }
}


// ── progress ────────────────────────────────────────────────────────
export async function loadStatus() {
  const out = $("#statusOut");
  try {
    const d = await (await api("/api/status", null, "GET")).json();
    const s = d.sections; let html = "";
    if (s.rada) html += `<div class="corr"><span class="tag">Rada</span>
      <div class="fix">${s.rada.mastered}/${s.rada.total} тем пройдено,
      ${s.rada.available} открыто</div>
      <div class="why">Следующая: ${esc(s.rada.next_et || "—")}${
        s.rada.next_ru ? ` — ${esc(s.rada.next_ru)}` : ""}</div></div>`;
    if (s.sonavara) html += `<div class="corr"><span class="tag">Sõnavara</span>
      <div class="fix">${ruCount(s.sonavara.known_in_top, ["слово", "слова", "слов"])} из первых
      ${s.sonavara.top}</div><div class="why">` +
      s.sonavara.bands.map(b =>
        `${b.from}–${b.to}: ${b.known}/${b.size}`).join(" · ") +
      // Two facts, kept apart: "known" is what the learner declared; this is what the
      // app can translate for them. The second grows on its own, so it is not
      // presented as an achievement.
      (s.sonavara.glossed != null
        ? `<div class="gloss-late">${ruCount(s.sonavara.glossed, ["слово", "слова", "слов"])} с переводом
           <span class="hint">(пополняется само · сегодня осталось
           ${s.sonavara.gloss_budget_left})</span></div>` : "") + `</div></div>`;
    if (s.kordamine) html += `<div class="corr"><span class="tag">Kordamine</span>
      <div class="fix">${s.kordamine.due} к повторению,
      ${s.kordamine.scheduled} всего</div></div>`;
    if (s.raamatukogu) html += `<div class="corr"><span class="tag">Lugemine · Kuulamine</span>
      <div class="fix">${ruCount(s.raamatukogu.items || 0, ["материал", "материала", "материалов"])} ·
      ${ruCount(Math.round(s.raamatukogu.minutes || 0), ["минута", "минуты", "минут"])}</div></div>`;
    // The caveat comes from the API, in Russian, so it is written once and matches
    // what the numbers mean.
    html += `<div class="engine">${esc(d.caveat || "")}</div>`;
    out.innerHTML = html;
  } catch (e) { out.textContent = e.message; }
}


$("#pathList").addEventListener("click", e => {
  const b = e.target.closest("button[data-topic]");
  if (b) {
    pathTopic = b.dataset.topic;
    $("#pathAll").open = false;
    paintTheme();
    startPractice();
  }
});


async function loadThemes() {
  try {
    const {themes} = await (await api("/api/themes", null, "GET")).json();
    $("#wordTheme").innerHTML = '<option value="">kõik sõnad</option>' +
      themes.map(t => `<option value="${esc(t.id)}">${esc(t.et)}</option>`).join("");
  } catch {}
}


async function startPractice({focus = true} = {}) {
  let loaded = false;
  const out = $("#practiceOut"); out.innerHTML = "";
  pathTally.answered = pathTally.correct = 0; $("#pathScore").textContent = "";
  const btn = $("#practiceBtn"); btn.disabled = true; setLabel(btn, "Загружаю…");
  try {
    const body = {count: 10};
    if (pathTopic) body.topic = pathTopic;
    const theme = themeApplies() ? $("#wordTheme").value : "";
    if (theme) body.theme = theme;
    const res = await (await api("/api/practice", body)).json();
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
        const again = document.createElement("button");
        again.className = "ghost";
        again.innerHTML = 'Proovi ilma teemata<span class="ru">без темы</span>';
        again.onclick = () => { $("#wordTheme").value = ""; startPractice(); };
        out.appendChild(again);
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
      bits.push(`<strong>${esc(res.et)}</strong> · ${esc(res.level)}`);
    /* A short set is not a broken one, but silence would read as "this topic only has
       three". */
    if (res.theme && res.items.length < 10)
      bits.push(`<span class="hint">по этой теме нашлось ${res.items.length}</span>`);
    if (res.reference && res.reference.known)
      bits.push(`<a href="${esc(res.reference.url)}" target="_blank" rel="noopener">EKK ${esc(res.reference.ekk_section)}</a>`);
    out.innerHTML = bits.length
      ? `<div class="banner info">${bits.join(" · ")}</div>` : "";
    loaded = true;
    res.items.forEach((it, i) =>
      out.appendChild(renderPracticeItem(it, res.topic, i, res.glosses || {}, focus)));
  } catch (e) {
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  } finally {
    btn.disabled = false;
    /* With a set on screen, answering is the main action; the button only swaps
       the set, so it steps down to a secondary one. */
    btn.className = loaded ? "ghost" : "go";
    btn.querySelector(".btn-ico")?.replaceWith(
      document.createRange().createContextualFragment(uiIcon(loaded ? "next" : "play")));
    const [et, ru] = loaded ? NEW_SET : START;
    setLabel(btn, et);
    btn.querySelector(".ru").textContent = ru;
  }
}


export function renderPracticeItem(it, topic, i, glosses, focus = true, tally = pathTally) {
  /* What the word means, when the app already knows.

     The gloss comes from the local store, so it is either instantly there or
     absent — a practice set never waits on a dictionary. */
  const ru = (glosses || {})[it.lemma] || [];
  const el = document.createElement("div");
  el.className = "drill";
  el.innerHTML = `
    <div class="prompt">${esc(it.prompt).replace("____", '<span class="blank">____</span>')}</div>
    ${it.choices && it.choices.length ? `
    <!-- Word order is the one topic whose unit is the whole sequence, so it
         is answered by choosing a sentence rather than typing a word.
         Everything after this point is unchanged: the chosen sentence is
         submitted as the answer, the server grades it by the same string
         comparison, and it reaches mastery and the review queue by the same
         path as every other item. -->
    <div class="choices">
      ${it.choices.map(c =>
        `<button class="choice" data-choice="${esc(c)}">${esc(c)}</button>`).join("")}
    </div>
    <div class="row">
      ${taskLine(it, ru)}
    </div>` : `
    <div class="row">
      <input type="text" size="18" placeholder="?">
      <button class="ghost">Kontrolli</button>
      ${taskLine(it, ru)}
    </div>`}
    <div class="verdict" role="status"></div>`;
  const input = el.querySelector("input"), verdict = el.querySelector(".verdict");
  const choices = [...el.querySelectorAll(".choice")];
  // One holder for "what was answered", whichever shape the item took, so the
  // submit path below stays single.
  let picked = "";
  const lock = () => {
    if (input) input.disabled = true;
    choices.forEach(b => b.disabled = true);
  };
  const unlock = () => {
    if (input) input.disabled = false;
    choices.forEach(b => { b.disabled = false; b.classList.remove("picked"); });
  };
  const locked = () => (input ? input.disabled : choices[0]?.disabled);

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
    lock();
    let res;
    try {
      // The server grades and records: the client must not be the judge of
      // whether a topic has been mastered.
      res = await (await api("/api/practice/answer", {
        topic, prompt: it.prompt, answer: it.answer,
        given: input ? input.value : picked,
        distractor: it.distractor || "", lemma: it.lemma || "",
        label: it.hint || "", why_ru: it.why_ru || "", record: tally.record,
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
    tally.answered++; if (res.correct) tally.correct++;
    verdict.className = "verdict " + (res.correct ? "ok" : "no");
    // A choice item's prompt is a question with no blank, so the answered sentence is
    // shown instead. The rule is shown either way: on a right answer it says why,
    // which for word order is the lesson.
    verdict.innerHTML = res.correct
      ? (choices.length
          ? `✓ õige <i class="ru">верно</i> — <strong>${esc(it.answer)}</strong><br>
             <span class="why">${md(it.why_ru || "")}</span>`
          : `✓ õige <i class="ru">верно</i> — <strong>${esc(it.prompt.replace("____", it.answer))}</strong>`)
      : wrongVerdict(input ? input.value : picked, it.answer, it.why_ru);
    /* The meaning arrives with the grade: `/api/practice/answer` looks up at most
       this one word. Only shown when the hint above did not already carry it. */
    if (res.russian?.length && !ru.length) {
      verdict.innerHTML += `<span class="gloss-late"><b>${esc(it.lemma)}</b> — `
        + `${esc(res.russian.slice(0, 3).join(", "))}</span>`;
    }
    let line = `${tally.correct}/${tally.answered} верных`;
    if (res.accuracy !== null) line += ` · ${Math.round(res.accuracy * 100)}% из последних ${res.gate.split("/")[1]}`;
    $(tally.out).textContent = line;
    if (res.just_mastered) {
      // Good news wears the accent. `#pathHead` is shared with the error path, so the
      // class is set at each use.
      $("#pathHead").className = "banner ok";
      $("#pathHead").innerHTML =
        `✓ <strong>${esc(topic)}</strong> пройдено — открывает следующие темы. ` +
        `Упражнения ушли в очередь повторения.`;
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


$("#freeBtn").onclick = async () => {
  const out = $("#freeOut"), btn = $("#freeBtn");
  out.innerHTML = "";
  freeTally.answered = freeTally.correct = 0; $("#freeScore").textContent = "";
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
    res.items.forEach((it, i) => out.appendChild(
      renderPracticeItem(it, res.topic, i, res.glosses || {}, true, freeTally)));
  } catch (e) {
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  } finally { btn.disabled = false; }
};

loadThemes();
