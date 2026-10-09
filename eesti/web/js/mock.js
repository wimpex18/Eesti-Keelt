/* Proovieksam: one exam part, on the exam's own clock.

   Not HARNO's paper — the app cannot write comprehension questions without
   inventing them (`eesti/mock.py` says what each section really is). What it
   does give is the clock, the shape and a verdict from code where code can
   decide. Nothing is graded here in the page: answers go back to the server.

   Reading and listening come in HARNO's own task types where the server can
   build them (`eesti/harnotasks.py`): the instruction, the question numbers,
   a letter or a word in the gap, recordings heard at most twice. After a part,
   every question is reviewed with its key and evidence, and a task with a miss
   can be practised now and comes back for a re-test (Kordamine). */

import {$, api, esc, md, ruCount} from "./core.js";
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
let playing = null;    // the recording being played, stopped when a section ends

// Parts with HARNO's task types (`?format=harno`); the others are the app's own.
const HARNO = new Set(["lugemine", "kuulamine"]);
// How often a recording may be heard: twice, as in the exam.
const PLAYS = 2;

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
  paintRetests();
}


/* Kordamine: HARNO task types with a miss come back one, three and six days
   later (`mock.retests`). Due ones start a practice of that task. */
async function paintRetests() {
  const box = $("#mockParts");
  if (!box) return;
  let due;
  try {
    due = await (await api(`/api/mock/${examLevel()}`, null, "GET")).json();
  } catch (e) { return; }          // the part buttons still work
  document.getElementById("mockRetests")?.remove();
  if (!(due.retests || []).length) return;
  const name = Object.fromEntries(PARTS.map(([id, et]) => [id, et]));
  box.insertAdjacentHTML("afterend", `<div class="hint" id="mockRetests">
    <span lang="et">Kordamine</span> <span lang="ru">— задания с ошибками, на повтор:</span>
    ${due.retests.map(r => r.due <= due.today
      ? `<button class="ghost" data-retest="${esc(r.part)}" data-no="${r.no}" lang="et">${
          esc(name[r.part] || r.part)} · ${r.no}. ülesanne <span class="ru" lang="ru">сегодня</span></button>`
      : `<span lang="et">${esc(name[r.part] || r.part)} · ${r.no}. ülesanne</span>
         <span lang="ru">— ${esc(day(r.due))}</span>`).join(" · ")}</div>`);
  document.querySelectorAll("#mockRetests button[data-retest]").forEach(b => b.onclick = () => {
    queue = []; run = [];
    start(b.dataset.retest, Number(b.dataset.no));
  });
}

const day = iso => iso.slice(8, 10) + "." + iso.slice(5, 7);


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
  if (playing) { playing.pause(); playing = null; }
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

async function start(part, task = null) {
  const out = $("#mockOut");
  out.innerHTML = `<p class="hint">Загружаю…</p>`;
  let section = null;
  // The level the section was sat at, fixed now: switching A2/B1 mid-section must
  // not file the result under the other level.
  const level = examLevel();
  try {
    if (HARNO.has(part)) {
      // HARNO's task types first; the app's own section where none can be built.
      const q = new URLSearchParams({format: "harno"});
      if (task) q.set("task", task);
      section = await (await api(`/api/mock/${level}/${part}?` + q, null, "GET")).json();
      if (!section.tasks.length && !task) section = null;
      else if (!section.tasks.length) section.detail = "Для этого задания пока нет материала.";
    }
    section ??= await (await api(`/api/mock/${level}/${part}`, null, "GET")).json();
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
  const practised = section.task ? section.blocks?.[0] : null;
  out.innerHTML = `
    <div class="mock-head">
      <strong lang="et">${esc(section.et || section.part)}${practised
        ? ` · ${practised.no}. ülesanne` : ""}</strong>
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

/* One recording, fetched once per section: a turn in its own voice. */
const clips = new Map();
function clip(text, voice) {
  const key = `${voice}|${text}`;
  if (!clips.has(key)) {
    const q = new URLSearchParams({text, voice, speed: "0.85"});
    clips.set(key, api("/api/speak?" + q, null, "GET")
      .then(r => r.blob()).then(b => URL.createObjectURL(b)));
  }
  return clips.get(key);
}

/* The turns one after another, each in its speaker's voice. */
async function playTurns(turns) {
  const urls = await Promise.all(turns.map(t => clip(t.text, t.voice)));
  for (const url of urls) {
    await new Promise(done => {
      const el = new Audio(url);
      playing = el;
      el.onended = el.onerror = el.onpause = done;
      el.play().catch(done);
    });
    if (playing === null) return;           // the section ended mid-play
  }
  playing = null;
}

/* A play button that allows `PLAYS` hearings, as the exam does. */
function wirePlays(button, turns) {
  let left = PLAYS;
  const count = button.querySelector(".plays");
  button.onclick = async () => {
    if (left <= 0) return;
    left -= 1;
    count.textContent = `· ${left}`;
    button.disabled = true;
    try { await playTurns(turns); }
    catch (e) { button.insertAdjacentHTML("afterend", `<span class="hint">${esc(e.message)}</span>`); }
    finally { button.disabled = left <= 0; }
  };
}

const playButton = `<button type="button" class="ghost" lang="et">Kuula
  <span class="ru" lang="ru">слушать</span> <span class="plays">· ${PLAYS}</span></button>`;

/* The text with its numbered gaps marked. */
const gapped = text => esc(text).replace(/\((\d+)\) ____/g, "<b>($1)</b> ______");

function harnoQuestion(t, i, block) {
  const input = `<input type="text" size="${block.answer === "choice" ? 3 : 18}" lang="et"
    data-answer aria-label="${t.no}. Vastus — ответ" autocapitalize="${
      block.answer === "choice" ? "characters" : "off"}" autocorrect="off" spellcheck="false" autocomplete="off">`;
  // The bank of task 4 is listed once, above; elsewhere each question has its own.
  const chips = block.bank.length ? "" : t.options.map(o =>
    `<button type="button" class="ghost" data-pick="${o.letter}"><b>${o.letter}</b>
      <span lang="et">${esc(o.text)}</span></button>`).join(" ");
  const said = t.turns ? `<div class="row" data-turns="${i}">${playButton}</div>` : "";
  const prompt = block.text ? "" : `<div class="prompt" lang="et">${t.no}. ${
    esc(t.prompt).replace("____", '<span class="blank">____</span>')}</div>`;
  return `<div class="mock-task" data-i="${i}">${said}${prompt}
    <div class="row">${block.text ? `<b>${t.no}.</b>` : ""} ${chips} ${input}</div></div>`;
}

function renderHarno(section, box) {
  box.innerHTML = section.blocks.map(b => {
    const qs = section.tasks.slice(b.first_index, b.first_index + b.count);
    const credit = [b.label, b.attribution].filter(Boolean).join(" · ");
    return `<div class="mock-block" data-code="${esc(b.code)}">
      <p lang="et"><b>${b.no}. ülesanne</b> · ${esc(b.et)}
        <span class="hint">· küsimused ${qs[0]?.no}–${qs[qs.length - 1]?.no}</span></p>
      <p lang="et">${esc(b.instruction_et)}</p>
      <p class="hint" lang="ru">${esc(b.instruction_ru)} ${esc(b.note)}</p>
      ${b.audio.length ? `<div class="row" data-heard="${esc(b.code)}">${playButton}</div>` : ""}
      ${b.title && b.text ? `<p lang="et"><b>${esc(b.title)}</b></p>` : ""}
      ${b.text ? `<div class="prompt" lang="et">${gapped(b.text)}</div>` : ""}
      ${b.bank.length ? `<ul lang="et">${b.bank.map(x =>
        `<li><b>${x.letter}</b> ${esc(x.text)}</li>`).join("")}</ul>` : ""}
      ${qs.map((t, k) => harnoQuestion(t, b.first_index + k, b)).join("")}
      ${credit ? `<p class="hint">${esc(credit)}</p>` : ""}
    </div>`;
  }).join("") + ((section.missing || []).length ? `<p class="hint">Не вошли: ${
    section.missing.map(m => `<span lang="et">${m.no}. ülesanne</span>`).join(", ")} —
    для них пока нет материала. Официальные задания HARNO — во вкладке
    <b lang="et">Eksam</b>.</p>` : "");

  section.blocks.forEach(b => {
    const host = box.querySelector(`[data-heard="${CSS.escape(b.code)}"] button`);
    if (host) wirePlays(host, b.audio);
  });
  box.querySelectorAll("[data-turns]").forEach(row =>
    wirePlays(row.querySelector("button"), section.tasks[Number(row.dataset.turns)].turns));
  box.querySelectorAll("button[data-pick]").forEach(b => b.onclick = () => {
    const input = b.closest(".mock-task").querySelector("input[data-answer]");
    input.value = b.dataset.pick;
  });
}

function renderTasks(section) {
  const box = $("#mockTasks");
  if (section.kind === "harno") {
    renderHarno(section, box);
    return;
  }
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
  const level = section.level || examLevel();
  if (section.kind === "harno") {
    body.format = "harno";
    body.task = section.task ?? null;
    body.answers = section.tasks.map((t, i) => ({token: t.token, given:
      document.querySelector(`#mockTasks .mock-task[data-i="${i}"] input[data-answer]`)?.value || ""}));
  } else if (section.kind === "cloze") {
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
      ${spent} мин из ${section.kind === "harno" ? section.minutes : r.minutes}.
      <span class="hint">Это не оценка экзамена: ${section.kind === "harno"
        ? "задания в формате HARNO, но материал и ключ — приложения."
        : "здесь задания приложения, а не HARNO."}</span>`;
    // Item by item: what was asked, what was written, and the answer.
    if ((section.kind === "cloze" || section.kind === "dictation") && (r.items || []).length) {
      verdict.insertAdjacentHTML("beforeend", `<ol class="mock-review">${r.items.map(row =>
        `<li lang="et">${row.correct ? "✓" : "✗"} ${esc(row.solution || row.text)}${row.correct
          ? "" : `<br><span class="hint">${row.given
            ? `<del>${esc(row.given)}</del>` : '<span lang="ru">нет ответа</span>'}${row.answer
            ? ` → <ins>${esc(row.answer.split(" ~ ")[0])}</ins>` : ""}</span>`}</li>`).join("")}</ol>`);
    }
    if (section.kind === "harno") reviewHarno(verdict, r, section);
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
    document.querySelectorAll("#mockTasks input, #mockTasks textarea, #mockTasks button[data-pick]")
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


/* The review of a HARNO-format part: every question with what was written,
   the key, the evidence (the sentence or what was heard, the deciding words in
   bold) and, for a miss, the rule and its topic. Then practice of each task
   with a miss, and when it comes back. */
function reviewHarno(verdict, r, section) {
  const marked = (text, mark) => {
    const safe = esc(text);
    const at = mark ? safe.indexOf(esc(mark)) : -1;
    return at < 0 ? safe : `${safe.slice(0, at)}<b>${esc(mark)}</b>${safe.slice(at + esc(mark).length)}`;
  };
  const written = row => row.given
    ? `<del>${esc(row.given)}${row.chosen && row.chosen !== row.given ? ` (${esc(row.chosen)})` : ""}</del>`
    : '<span lang="ru">нет ответа</span>';
  verdict.insertAdjacentHTML("beforeend", `<ol class="mock-review">${(r.items || []).map(row =>
    `<li lang="et" value="${row.no}">${row.correct ? "✓" : "✗"} ${marked(row.evidence, row.mark)}${
      row.correct ? "" : `<br><span class="hint">${written(row)} → <ins>${
        row.letter ? `${esc(row.letter)} ` : ""}${esc(row.answer)}</ins></span>${row.why_ru
        ? `<br><span class="hint" lang="ru">${md(row.why_ru)}</span>` : ""}${row.topic
        ? ` <a class="hint" href="#session/${encodeURIComponent(row.topic)}" lang="et">${
          esc(row.topic_et || row.topic)}</a>` : ""}`}</li>`).join("")}</ol>`);

  const missed = (r.blocks || []).filter(b => b.correct < b.asked);
  if (!missed.length) return;
  const due = Object.fromEntries((r.retests || []).map(x => [x.code, x.due]));
  verdict.insertAdjacentHTML("beforeend", `<div class="row" id="mockPractise">${missed.map(b =>
    `<button class="ghost" data-practise="${b.no}" lang="et">Harjuta: ${b.no}. ülesanne
      <span class="ru" lang="ru">ещё раз сейчас${due[b.code] ? `, повтор ${esc(day(due[b.code]))}` : ""}</span></button>`
  ).join("")}</div>`);
  verdict.querySelectorAll("button[data-practise]").forEach(b => b.onclick = () => {
    queue = []; run = [];
    start(section.part, Number(b.dataset.practise));
  });
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
