/* Proovieksam: one exam part, on the exam's own clock.

   Not HARNO's paper — the app cannot write comprehension questions without
   inventing them (`eesti/mock.py` says what each section really is). What it
   does give is the clock, the shape and a verdict from code where code can
   decide. Nothing is graded here in the page: answers go back to the server. */

import {$, api, esc, ruCount} from "./core.js";
import {mountAudio} from "./media.js";
import {examLevel} from "./state.js";

const WORDS = ["слово", "слова", "слов"];

const PARTS = [
  ["lugemine", "Lugemine", "чтение"],
  ["kuulamine", "Kuulamine", "аудирование"],
  ["kirjutamine", "Kirjutamine", "письмо"],
  ["raakimine", "Rääkimine", "говорение"],
];

let clock = null;      // the interval, cleared whenever a section ends
let current = null;    // the section being sat
let queue = [];        // the parts still to sit in a whole-sitting run
let run = [];          // what each finished part scored, for the summary

export function paintMock(counts) {
  const box = $("#mockParts");
  if (!box) return;
  box.innerHTML = PARTS.map(([id, et, ru]) => {
    const sat = (counts || {})[id] || 0;
    return `<button class="ghost" data-part="${id}" lang="et">${esc(et)}
      <span class="ru" lang="ru">${esc(ru)}</span>${
        sat ? `<span class="hint"> · ${sat}</span>` : ""}</button>`;
  }).join("");
  box.querySelectorAll("button[data-part]").forEach(
    b => b.onclick = () => { queue = []; run = []; start(b.dataset.part); });

  const whole = $("#mockWhole");
  if (whole) whole.onclick = () => startRun();
}


/* The whole sitting: four parts in the exam's order, each on its own clock.
   Stopping between parts is fine — every part is recorded as it finishes. */
async function startRun() {
  let plan;
  try {
    plan = await (await api(`/api/mock-run/${examLevel()}`, null, "GET")).json();
  } catch (e) {
    $("#mockOut").innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
    return;
  }
  queue = plan.parts.slice();
  run = [];
  $("#mockOut").innerHTML = `<p class="hint">${esc(plan.note)}
    Всего ${plan.minutes} минут.</p>`;
  start(queue.shift());
}

function stopClock() {
  if (clock) { clearInterval(clock); clock = null; }
}

function runClock(seconds, onEnd) {
  const el = $("#mockClock");
  const started = performance.now();
  const tick = () => {
    const left = Math.max(0, seconds - (performance.now() - started) / 1000);
    const mm = String(Math.floor(left / 60)).padStart(2, "0");
    const ss = String(Math.floor(left % 60)).padStart(2, "0");
    el.textContent = `${mm}:${ss}`;
    el.classList.toggle("low", left <= 60);
    if (left <= 0) { stopClock(); onEnd(); }
  };
  stopClock();
  tick();
  clock = setInterval(tick, 1000);
  return () => (performance.now() - started) / 1000;
}

async function start(part) {
  const out = $("#mockOut");
  out.innerHTML = `<p class="hint">Загружаю…</p>`;
  let section;
  // The level the section was sat at, fixed now: switching A2/B1 mid-section must
  // not file the result under the other level.
  const level = examLevel();
  try {
    section = await (await api(`/api/mock/${level}/${part}`, null, "GET")).json();
    section.level ??= level;
  } catch (e) {
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
    return;
  }
  current = section;
  if (!section.tasks.length) {
    out.innerHTML = `<div class="banner">${esc(section.detail || "заданий нет")}</div>`;
    return;
  }
  out.innerHTML = `
    <div class="mock-head">
      <strong lang="et">${esc(section.et || section.part)}</strong>
      <span class="mock-clock" id="mockClock" role="timer">--:--</span>
      <button class="go" id="mockDone" lang="et">Valmis <span class="ru" lang="ru">готово</span></button>
    </div>
    <p class="hint">${esc(section.note)}</p>
    <div id="mockTasks"></div>
    <div id="mockVerdict" class="verdict" role="status"></div>
    <div class="row" id="mockNext"></div>`;
  renderTasks(section);
  const elapsed = runClock(section.minutes * 60, () => finish(true));
  $("#mockDone").onclick = () => finish(false, elapsed());
}

function renderTasks(section) {
  const box = $("#mockTasks");
  if (section.kind === "cloze") {
    box.innerHTML = section.tasks.map((t, i) => `
      <div class="mock-task" data-i="${i}">
        <div class="prompt" lang="et">${esc(t.prompt).replace("____",
          '<span class="blank">____</span>')}</div>
        <div class="row"><span class="hint" lang="et">${esc(t.hint || "")}</span>
          <input type="text" size="16" lang="et" aria-label="Vastus — ответ"
            autocapitalize="off" autocorrect="off" spellcheck="false" autocomplete="off">
        </div></div>`).join("");
    return;
  }
  if (section.kind === "dictation") {
    box.innerHTML = section.tasks.map((t, i) => `
      <div class="mock-task" data-i="${i}">
        <div class="row">
          <button class="ghost" data-play="${i}" lang="et">Kuula <span class="ru" lang="ru">слушать</span></button>
          <input type="text" size="28" lang="et" aria-label="Kirjuta kuuldu — запиши услышанное"
            autocapitalize="off" autocorrect="off" spellcheck="false" autocomplete="off">
        </div>
        <div class="mock-audio"></div></div>`).join("");
    box.querySelectorAll("button[data-play]").forEach(b => b.onclick = async () => {
      const i = Number(b.dataset.play), task = section.tasks[i];
      b.disabled = true;
      try {
        const q = new URLSearchParams({text: task.text, speed: "0.7"});
        if (task.voice) q.set("voice", task.voice);
        const r = await api("/api/speak?" + q, null, "GET");
        const host = box.querySelector(`.mock-task[data-i="${i}"] .mock-audio`);
        await mountAudio(host, URL.createObjectURL(await r.blob()));
        host.querySelector("audio")?.play().catch(() => {});
      } catch (e) {
        b.insertAdjacentHTML("afterend", `<span class="hint">${esc(e.message)}</span>`);
      } finally { b.disabled = false; }
    });
    return;
  }
  if (section.kind === "writing") {
    /* Both of HARNO's tasks, each in its variants; the learner picks one per
       task. No spellcheck or autocorrect: the exam is written by hand. */
    const field = v => v.kind === "kusimustik"
      ? v.questions.map((q, n) => `<label class="placement-task" lang="et">${esc(q)}
          <input data-q="${n}" lang="et" autocomplete="off" autocapitalize="sentences"
            autocorrect="off" spellcheck="false" aria-label="Vastus ${n + 1} — ответ"></label>`).join("")
      : `${v.card.length ? `<pre class="mock-card" lang="et">${esc(v.card.join("\n"))}</pre>` : ""}
         <textarea lang="et" rows="7" autocapitalize="sentences" autocorrect="off"
           spellcheck="false" aria-label="Tekst — твой текст"></textarea>
         <p class="hint mock-words">0 слов</p>`;
    const variant = v => `<div class="mock-variant" data-id="${esc(v.id)}" data-kind="${esc(v.kind)}">
        <p class="prompt" lang="et">${esc(v.prompt_et)}</p>
        <p class="hint" lang="ru">${esc(v.prompt_ru)}</p>${field(v)}</div>`;
    box.innerHTML = section.tasks.map(t => `
      <div class="mock-task mock-writing" data-no="${t.no}">
        <p lang="et"><b>${t.no}. ülesanne</b>${t.points ? ` · ${t.points} toorpunkti` : ""}</p>
        <label lang="et">Variant <i class="ru" lang="ru">вариант</i>
          <select data-pick="${t.no}">${t.variants.map(v =>
            `<option value="${esc(v.id)}">${esc(v.kind_et)}</option>`).join("")}</select></label>
        ${t.variants.map(variant).join("")}
      </div>`).join("");
    box.querySelectorAll(".mock-writing").forEach(task => {
      const pick = task.querySelector("select");
      const show = () => task.querySelectorAll(".mock-variant").forEach(v =>
        v.hidden = v.dataset.id !== pick.value);
      pick.addEventListener("change", show);
      show();
      task.querySelectorAll("textarea").forEach(area => area.addEventListener("input", () => {
        area.parentElement.querySelector(".mock-words").textContent =
          ruCount(area.value.split(/\s+/).filter(Boolean).length, WORDS);
      }));
    });
    return;
  }
  // speaking: the exam is paired, so this is practice, not a score
  box.innerHTML = section.tasks.map(t => `
    <div class="mock-task">
      <div class="prompt" lang="et">${esc(t.question)}</div>
      <p class="hint">${esc(t.hint_ru)}</p>
    </div>`).join("") +
    `<p class="hint">Ответь вслух, засекая время. Записать и послушать себя
      можно во вкладке <b lang="et">Rääkimine</b>.</p>`;
}

async function finish(ranOut, seconds) {
  stopClock();
  const section = current;
  if (!section) return;
  current = null;
  const body = {seconds: seconds ?? section.minutes * 60, answers: []};
  const tasks = [...document.querySelectorAll("#mockTasks .mock-task")];
  if (section.kind === "cloze") {
    body.answers = tasks.map((el, i) => ({
      token: section.tasks[i].token, given: el.querySelector("input").value}));
  } else if (section.kind === "dictation") {
    body.answers = tasks.map((el, i) => ({
      text: section.tasks[i].text, given: el.querySelector("input").value}));
  } else if (section.kind === "writing") {
    body.tasks = [...document.querySelectorAll("#mockTasks .mock-writing")].map(task => {
      const v = task.querySelector(`.mock-variant[data-id="${task.querySelector("select").value}"]`);
      return v.dataset.kind === "kusimustik"
        ? {id: v.dataset.id, answers: [...v.querySelectorAll("input[data-q]")].map(x => x.value)}
        : {id: v.dataset.id, text: v.querySelector("textarea").value};
    });
  } else {
    body.answers = section.tasks.map(() => ({given: ""}));
  }

  const verdict = $("#mockVerdict");
  try {
    const level = section.level || examLevel();
    const r = await (await api(`/api/mock/${level}/${section.part}`, body)).json();
    const spent = Math.round(r.seconds / 60);
    const d = r.detail || {};
    const score = r.correct === null
      ? "без оценки — на экзамене эта часть сдаётся в паре"
      : section.kind === "writing"
        ? `список выполнен в ${r.correct} из ${r.asked} заданий`
        : `${r.correct} из ${r.asked}`;
    verdict.className = "verdict ok";
    verdict.innerHTML = `${ranOut ? "Время вышло. " : ""}${esc(score)} ·
      ${spent} мин из ${r.minutes}.
      <span class="hint">Это не оценка экзамена: здесь задания приложения,
      а не HARNO.</span>`;
    // Item by item: what was asked, what was written, and the answer.
    if ((section.kind === "cloze" || section.kind === "dictation") && (r.items || []).length) {
      verdict.insertAdjacentHTML("beforeend", `<ol class="mock-review">${r.items.map(row =>
        `<li lang="et">${row.correct ? "✓" : "✗"} ${esc(row.solution || row.text)}${row.correct
          ? "" : `<br><span class="hint">${row.given
            ? `<del>${esc(row.given)}</del>` : '<span lang="ru">нет ответа</span>'}${row.answer
            ? ` → <ins>${esc(row.answer.split(" ~ ")[0])}</ins>` : ""}</span>`}</li>`).join("")}</ol>`);
    }
    // The topics behind the misses: review leads straight to practice.
    if ((r.practise || []).length) {
      verdict.insertAdjacentHTML("beforeend", `<p class="hint"><span lang="et">Harjuta neid</span>
        <span lang="ru">— потренируй правила, где были ошибки:</span> ${r.practise.map(t =>
          `<a href="#session/${encodeURIComponent(t)}" lang="et">${esc(t)}</a>`).join(" · ")}</p>`);
    }
    // Writing: each task's checklist — what code found, never a mark.
    if (section.kind === "writing") {
      const mark = ok => ok ? "✓" : "✗";
      verdict.insertAdjacentHTML("beforeend", (r.detail.tasks || []).map(t => `
        <div class="hint"><b lang="et">${esc(t.kind_et)}</b>:
          ${t.answered !== null ? `ответов ${t.answered} из 10` : `${ruCount(t.words, WORDS)}
            (${t.at_least ? "нужно не меньше" : "около"} ${t.target_words})`} ${mark(t.long_enough)}
          ${t.points.map(p => `<div>${mark(p.found)} <span lang="et">${esc(p.et)}</span>
            <span lang="ru">— ${esc(p.ru)}</span></div>`).join("")}
          ${t.opening !== null ? `<div>${mark(t.opening)} <span lang="ru">приветствие</span>
            · ${mark(t.closing)} <span lang="ru">прощание и подпись</span></div>` : ""}
          ${t.findings.map(f => `<div>✗ <del lang="et">${esc(f.wrong)}</del>${f.correct
            ? ` → <ins lang="et">${esc(f.correct)}</ins>` : ""} — ${esc(f.why || "")}</div>`).join("")}
        </div>`).join("") + `<p class="hint">Список проверяет код: есть ли в тексте
          признаки каждого пункта. Это подсказка, а не оценка экзамена.
          Авторство заданий: ${esc(r.detail.prompts_by || "")}.</p>`);
    }
    document.querySelectorAll("#mockTasks input, #mockTasks textarea")
      .forEach(x => x.disabled = true);
    run.push({part: section.et, score});
    paintNext();
    const counts = await (await api(`/api/mock/${examLevel()}`, null, "GET")).json();
    paintMock(counts.counts);
  } catch (e) {
    verdict.className = "verdict no";
    verdict.innerHTML = `Результат не записан: ${esc(e.message)}`;
  }
}


/* Between the parts of a whole sitting: what is next, or how it went. */
function paintNext() {
  const box = $("#mockNext");
  if (!box) return;
  if (queue.length) {
    box.innerHTML = `<button class="go" id="mockGoNext" lang="et">Järgmine osa
      <span class="ru" lang="ru">следующая часть</span></button>`;
    $("#mockGoNext").onclick = () => start(queue.shift());
    return;
  }
  box.innerHTML = run.length > 1
    ? `<div class="hint" id="mockSummary">Весь экзамен пройден: ` +
      run.map(r => `<b lang="et">${esc(r.part)}</b> — ${esc(r.score)}`).join("; ") +
      `. Это не оценка HARNO.</div>`
    : "";
}
