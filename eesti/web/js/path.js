/* Rada: the syllabus, where you stand on it, and one topic's practice. */

import {RU, stateIcon, uiIcon} from "./chrome.js";
import {$, api, esc, md, ruCount, setLabel, taskLine, wrongVerdict} from "./core.js";
import {loadRail, refreshDueBadge} from "./review.js";

// ── the path ────────────────────────────────────────────────────────
let pathTopic = null;

/* A running score for one set. Rada's is recorded by the server and shows the
   mastery window; Vaba harjutus is graded by the same code and recorded nowhere. */
const pathTally = {answered: 0, correct: 0, size: 0, missed: [], out: "#pathScore", box: "#practiceOut",
                   record: true, gate: true, again: () => startPractice()};
const freeTally = {answered: 0, correct: 0, size: 0, missed: [], out: "#freeScore", box: "#freeOut",
                   record: false, again: () => $("#freeBtn").click()};

/* A new set on a tally. `gen` names the set, so an answer still in flight from the
   set it replaced is not counted in this one (see `grade`). */
function newSet(tally) {
  Object.assign(tally, {answered: 0, correct: 0, size: 0, missed: [],
                        gen: (tally.gen || 0) + 1});
}

/* A tally for a set rendered somewhere else (the Kontrolltöö). */
export function newTally(out, box, again) {
  // A Kontrolltöö is a test: its misses are listed, not re-drilled on the spot.
  return {answered: 0, correct: 0, size: 0, missed: [], out, box, record: true, again,
          redo: false};
}

let pathMeta = {};
let autoStarted = false, practiceRequest = 0;
/* What the learner types is the thing being graded: iOS must not capitalise it,
   correct it or underline it, and a password manager must not offer to fill it. */
const ANSWER_FIELD = `autocapitalize="off" autocorrect="off" spellcheck="false" autocomplete="off"`;
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
        ? `<button class="ghost" data-topic="${esc(t.id)}" lang="et">harjuta <i class="ru" lang="ru">решать</i></button>` : "";
      return `<div class="topic ${t.state.replace(" ", "-")}">
        <span class="st">${stateIcon(t.state)}${esc(RU[t.state] || t.state)}</span>
        <span class="lv" data-level="${esc(t.level)}">${esc(t.level)}</span>
        <span lang="et">${esc(t.et)}${esc(blocked)}${acc}</span>
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
    if (s.rada) html += `<div class="corr stat"><span class="tag" lang="et">Rada</span>
      <div class="fix">${s.rada.mastered}/${s.rada.total} тем пройдено,
      ${s.rada.available} открыто</div>
      <div class="why">Следующая: <span lang="et">${esc(s.rada.next_et || "—")}</span>${
        s.rada.next_ru ? ` — ${esc(s.rada.next_ru)}` : ""}</div></div>`;
    if (s.sonavara) html += `<div class="corr stat"><span class="tag" lang="et">Sõnavara</span>
      <div class="fix">${ruCount(s.sonavara.known_in_top, ["слово", "слова", "слов"])} из первых
      ${s.sonavara.top}</div><details class="more"><summary lang="et">Sageduse järgi <i class="ru" lang="ru">по частотности</i></summary><div class="why">` +
      s.sonavara.bands.map(b =>
        `${b.from}–${b.to}: ${b.known}/${b.size}`).join(" · ") + `</div></details><div class="why">` +
      // Two facts, kept apart: "known" is what the learner declared; this is what the
      // app can translate for them. The second grows on its own, so it is not
      // presented as an achievement.
      (s.sonavara.glossed != null
        ? `<div class="gloss-late">${ruCount(s.sonavara.glossed, ["слово", "слова", "слов"])} с переводом
           <span class="hint">(пополняется само · сегодня осталось
           ${s.sonavara.gloss_budget_left})</span></div>` : "") + `</div></div>`;
    if (s.kordamine) html += `<div class="corr stat"><span class="tag" lang="et">Kordamine</span>
      <div class="fix">${s.kordamine.due} к повторению,
      ${s.kordamine.scheduled} всего</div></div>`;
    if (s.raamatukogu) html += `<div class="corr stat"><span class="tag" lang="et">Lugemine · Kuulamine</span>
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
    if (res.reference && res.reference.known)
      bits.push(`<a href="${esc(res.reference.url)}" target="_blank" rel="noopener">EKK ${esc(res.reference.ekk_section)}</a>`);
    out.innerHTML = bits.length
      ? `<div class="banner info">${bits.join(" · ")}</div>` : "";
    loaded = true;
    pathTally.size = res.items.length;
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
  const gate = tally.gate && res.accuracy !== null && !res.just_mastered
    ? `<p class="hint">Тема засчитывается, когда из последних ${esc(of)} ответов
         верны ${esc(need)}. Сейчас: ${Math.round(res.accuracy * 100)}%.</p>` : "";
  /* What went wrong, in the sentence it went wrong in, with the right form: the end
     of a set is where a learner looks back, so the misses are there to look at. */
  const missed = tally.missed.length ? `<ul class="set-missed" lang="et">${
    tally.missed.map(({it}) => `<li>${esc(it.prompt).replace("____",
      `<b>${esc(it.answer)}</b>`)}</li>`).join("")}</ul>` : "";
  const redo = tally.missed.length && tally.redo !== false
    ? `<button class="ghost" data-act="redo" lang="et">Korda vigu <span class="ru" lang="ru">ещё раз ошибки</span></button>` : "";
  const end = document.createElement("div");
  end.className = "set-end";
  end.setAttribute("role", "status");
  end.innerHTML = `<h4 lang="et">Komplekt tehtud <i class="ru" lang="ru">набор пройден</i></h4>
    <p class="set-score">${tally.correct} из ${tally.size} верно</p>${gate}${missed}
    <div class="row">${redo}<button class="go" data-act="new" lang="et">${uiIcon("next")}Uued laused <span class="ru" lang="ru">новые задания</span></button></div>`;
  end.querySelector('[data-act="new"]').onclick = tally.again;
  end.querySelector('[data-act="redo"]')?.addEventListener("click", () => redoMissed(tally));
  // The score line said the same thing one line lower; the card says it now.
  $(tally.out).textContent = "";
  box.appendChild(end);
  // Fully in view, above the thumb bar: this is the moment the set exists for.
  requestAnimationFrame(() => requestAnimationFrame(() =>
    end.scrollIntoView({block: "nearest", behavior: "smooth"})));
}


/* The missed items again, as a short set of their own: graded and recorded the same
   way as the first time (a Rada miss is already in the review queue either way). */
function redoMissed(tally) {
  const again = tally.missed;
  const box = $(tally.box);
  box.innerHTML = "";
  newSet(tally);
  tally.size = again.length;
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
  // Where this item sits in its set; shown on a phone, where one item is on screen.
  // The set this item belongs to; a later set on the same tally has another.
  const set = tally.gen || 0;
  const place = tally.size ? `${i + 1}/${tally.size}` : `${i + 1}`;
  const pos = tally.size ? `<div class="drill-pos">${i + 1} / ${tally.size}</div>` : "";
  el.innerHTML = `${pos}
    <div class="prompt" lang="et">${esc(it.prompt).replace("____", '<span class="blank">____</span>')}</div>
    ${it.choices && it.choices.length ? `
    <!-- Word order is the one topic whose unit is the whole sequence, so it
         is answered by choosing a sentence rather than typing a word.
         Everything after this point is unchanged: the chosen sentence is
         submitted as the answer, the server grades it by the same string
         comparison, and it reaches mastery and the review queue by the same
         path as every other item. -->
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
    // Answered, but the set was replaced while the answer was on its way: this item
    // is gone from the screen and must not count in the set that replaced it.
    if ((tally.gen || 0) !== set) return;
    tally.answered++; if (res.correct) tally.correct++;
    else tally.missed.push({it, topic});
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
          : `<span lang="et">✓ õige <i class="ru" lang="ru">верно</i></span> — <strong lang="et">${esc(it.prompt.replace("____", it.answer))}</strong>`
            // A choice topic hid its form until now; the rule is the lesson either way.
            + (it.form_after ? `<br><span class="why">${md(it.why_ru || "")}</span>` : ""))
      : wrongVerdict(input ? input.value : picked, it.answer, it.why_ru);
    /* The meaning arrives with the grade: `/api/practice/answer` looks up at most
       this one word. Only shown when the hint above did not already carry it. */
    if (res.russian?.length && !ru.length) {
      verdict.innerHTML += `<span class="gloss-late"><b lang="et">${esc(it.lemma)}</b> — `
        + `${esc(res.russian.slice(0, 3).join(", "))}</span>`;
    }
    let line = `${tally.correct}/${tally.answered} верных`;
    if (res.accuracy !== null) line += ` · ${Math.round(res.accuracy * 100)}% из последних ${res.gate.split("/")[1]}`;
    $(tally.out).textContent = line;
    if (tally.size && tally.answered === tally.size) finishSet(tally, res);
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
    res.items.forEach((it, i) => out.appendChild(
      renderPracticeItem(it, res.topic, i, res.glosses || {}, false, freeTally)));
    foldFreeControls(true);
    /* The set, not the settings, is what the learner came for: bring its first item
       into view and hand it the keyboard. */
    const first = out.querySelector(".drill");
    first?.scrollIntoView({block: "start", behavior: "smooth"});
    first?.querySelector("input")?.focus({preventScroll: true});
  } catch (e) {
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  } finally { btn.disabled = false; }
};

loadThemes();
