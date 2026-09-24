/* Am I ready: the level, the official material, and the checkpoint. */

import {emptyState, markIcon, uiIcon} from "./chrome.js";
import {$, api, esc, langOf} from "./core.js";
import {paintMock} from "./mock.js";
import {newTally, renderPracticeItem} from "./path.js";
import {loadRail} from "./review.js";
import {examLevel, setExamLevel} from "./state.js";

const MARK = {
  true:  ["yes", `<circle cx="8" cy="8" r="6"/><path d="m5.2 8.2 2 2 3.6-4"/>`],
  false: ["no", `<circle cx="8" cy="8" r="6"/><path d="M5.2 8h5.6"/>`],
  null:  ["unknown", `<circle cx="8" cy="8" r="6" stroke-dasharray="2.2 2.4"/><path d="M8 10.8v.01"/><path d="M6.4 6.4a1.6 1.6 0 1 1 1.6 2v.9"/>`],
};


/* What the exam is, and which sitting is being prepared for. Both come from
   HARNO (`eesti/exam.py`), so the points and the dates are never hand-written. */
function paintSpec(spec, goal) {
  const box = $("#examSpec"), picker = $("#examGoal");
  if (!spec) { box.innerHTML = ""; picker.innerHTML = ""; return; }
  box.innerHTML = `
    <p class="hint">Четыре части (osad): ${spec.parts.map(p =>
      `<b lang="et">${esc(p.et)}</b> ${p.points} б. / ${p.minutes} мин`).join(" · ")}.
      Сдано, если в сумме <strong>≥ ${spec.pass_mark} из ${spec.total}</strong>
      и <strong>ни одна часть не равна 0</strong>.</p>
    <details class="exam-parts"><summary lang="et">Mis eksamil on
      <i class="ru" lang="ru">что на экзамене</i></summary>
      <ul class="hint">${spec.parts.map(p => `<li><b lang="et">${esc(p.et)}</b>
        <i lang="ru">${esc(p.ru)}</i> — ${esc(p.about)}
        ${p.note ? `<span class="hint">${esc(p.note)}</span>` : ""}</li>`).join("")}</ul>
    </details>`;

  const chosen = goal && goal.level === spec.level ? goal : null;
  // The options say when, in Russian, under an Estonian label: each carries its
  // own `lang`, or a screen reader reads the dates in the wrong voice.
  const options = [`<option value="" lang="ru">без даты</option>`].concat(
    (spec.sessions || []).map(s =>
      `<option value="${esc(s.sitting)}" lang="ru"${chosen && chosen.sitting === s.sitting
        ? " selected" : ""}>${esc(s.sitting)} · регистрация до ${esc(s.registration_closes)}</option>`));
  picker.innerHTML = `
    <label lang="et">Sessioon <i class="ru" lang="ru">когда сдаю</i>
      <select id="goalSitting">${options.join("")}</select>
    </label>
    <button class="ghost" id="goalSet" lang="et">Vali <span class="ru" lang="ru">выбрать</span></button>
    ${chosen && chosen.sitting
      ? `<a class="hint" href="/api/goal.ics" download>в календарь (.ics)</a>` : ""}
    <span class="hint">${esc(spec.next_year)}</span>`;
  $("#goalSet").onclick = async () => {
    $("#goalSet").disabled = true;
    try {
      await api("/api/goal", {level: spec.level, sitting: $("#goalSitting").value || null});
      loadExam(); loadRail();
    } catch (e) {
      picker.insertAdjacentHTML("beforeend",
        `<span class="hint">Не сохранилось: ${esc(e.message)}</span>`);
    } finally { $("#goalSet").disabled = false; }
  };
}


export async function loadExam() {
  // The buttons are authored with A2 selected; if a level was remembered, the
  // strip has to agree with the variable before anything is fetched, or the
  // panel shows B1 data under a highlighted A2.
  document.querySelectorAll("#tab-exam button[data-level]").forEach(x =>
    x.setAttribute("aria-selected", x.dataset.level === examLevel()));

  const get = u => api(u, null, "GET").then(r => r.json());
  const [ready, material, path, spec, goal, milestones] = await Promise.all([
    get(`/api/readiness/${examLevel()}`), get(`/api/exam/${examLevel()}`),
    get("/api/curriculum").catch(() => ({})),
    get(`/api/exam-spec/${examLevel()}`).catch(() => null),
    get("/api/goal").catch(() => ({goal: null})),
    get(`/api/milestones/${examLevel()}`).catch(() => ({milestones: []})),
  ]);
  const mock = await get(`/api/mock/${examLevel()}`).catch(() => null);

  paintSpec(spec, goal.goal);
  paintMock(mock && mock.counts);

  /* An empty countdown is a fact about the plan; `deadline.note` says which, in
     Russian, and is shown. */
  $("#countdown").textContent =
    ready.countdown || (ready.deadline && ready.deadline.note) || "";

  /* The one thing to do next leads the screen; the state of the four parts follows.
     A first-day learner meets an action before a column of zeros. */
  const next = (path.topics || []).find(t => t.id === path.resume);
  let html = next ? `<div class="next-step">
      <span lang="et">Järgmine samm <i class="ru" lang="ru">следующий шаг</i></span>
      <a class="rail-go" href="#path" lang="et"><b>${esc(next.et)}</b> → Harjuta</a>
    </div>` : "";
  html += `<div class="parts">`;
  for (const part of ready.parts) {
    const [cls, glyph] = MARK[String(part.touched)];
    html += `<div class="part-row">
      <span class="part-mark ${cls}">${markIcon(glyph)}</span>
      <span class="part-body">
        <span class="part-name" lang="et">${esc(part.et)}</span>
        <span class="part-ev"> · ${esc(part.evidence)}</span>
        ${part.next_task ? `<div class="part-next">${uiIcon("next", "inline-ico")} ${part.next_task.local
            ? `<button class="linky" data-open-task="${esc(part.next_task.id)}"
                 lang="${langOf(part.next_task.title)}">${esc(part.next_task.title)}</button>`
            : part.next_task.url ? `<a href="${esc(part.next_task.url)}" target="_blank"
                 rel="noopener" lang="${langOf(part.next_task.title)}">${esc(part.next_task.title)}</a>`
            : `<span lang="${langOf(part.next_task.title)}">${esc(part.next_task.title)}</span>`}</div>` : ""}
      </span></div>`;
  }
  html += `</div>`;
  if (milestones.milestones?.length) html += `<details class="more">
    <summary lang="et">Saavutused <i class="ru" lang="ru">этапы подготовки</i></summary>
    <ul class="hint">${milestones.milestones.map(m => `<li>
      ${m.complete ? "✓" : `${m.current}/${m.target}`} <b lang="et">${esc(m.et)}</b>
      <span lang="ru">${esc(m.ru)}</span></li>`).join("")}</ul>
  </details>`;

  /* The reasons and the lists of what is left are the detail behind the marks above:
     one tap away, not a wall under them. */
  let detail = "";
  if (ready.reasons.length)
    detail += `<ul class="hint">` + ready.reasons.map(r => `<li>${esc(r)}</li>`).join("") + `</ul>`;

  /* The two measures behind the verdict: `grammar.outstanding` names the exact
     topics standing between the learner and the level, and `vocabulary` the same
     for words. Named, not summarised: the names are a plan. */
  const g = ready.grammar || {}, v = ready.vocabulary || {};
  if (g.topics) {
    html += `<div class="verdict-detail"><b lang="et">Grammatika</b> · ` +
      `${g.mastered}/${g.topics} тем` +
      (g.checkpoint_passed ? " · контрольная пройдена" : "") + `</div>`;
    if ((g.outstanding || []).length)
      detail += `<div class="hint">Осталось по грамматике: <span lang="et">` +
        g.outstanding.map(esc).join(", ") + `</span></div>`;
  }
  if (v.measured)
    html += `<div class="verdict-detail"><b lang="et">Sõnavara</b> · ` +
      `${v.known} из ${v.level_words} слов уровня</div>`;
  if (detail)
    html += `<details class="more"><summary lang="et">Üksikasjad <i class="ru" lang="ru">что осталось</i></summary>${detail}</details>`;
  html += `<p class="hint">${esc(ready.caveat)}</p>`;
  $("#readiness").innerHTML = html;

  // Material, grouped by what each thing is for. The sample performance leads
  // because it is the only artefact that shows what a pass looks like.
  const groups = [
    ["sooritusnaidis", "Sooritusnäidis",
     "Настоящая работа с оценкой и комментариями."],
    ["video", "Tutvustav video", "Как проходит экзамен."],
    ["kirjeldus", "Tasemekirjeldus", "Что требуется на этом уровне."],
    ["teave", "Teave", "Информационный лист и регистрация."],
    /* `vorm` — the application and reimbursement forms. `exam_material` returns
       them under their own key, so they need their own group. */
    ["vorm", "Avaldused", "Бланки: регистрация, апелляция, возмещение платы."],
  ];
  let out = "";
  for (const [key, title, why] of groups) {
    const items = material[key] || [];
    if (!items.length) continue;
    out += `<div class="kindgroup"><h3 lang="et">${esc(title)}</h3>
      <p class="why">${esc(why)}</p>` + items.map(linkRow).join("") + `</div>`;
  }
  for (const [part, items] of Object.entries(material.ulesanded || {})) {
    out += `<div class="kindgroup"><h3 lang="et">${esc(part)} — ${items.length}</h3>` +
      items.map(linkRow).join("") + `</div>`;
  }
  /* Whatever no group above claimed. `exam_material` returns unknown kinds in
     `muu`, so a new kind never vanishes from this screen. */
  if ((material.muu || []).length) {
    out += `<div class="kindgroup"><h3 lang="et">Muu materjal <i class="ru" lang="ru">прочее</i></h3>
      <p class="why">Официальные файлы, не попавшие в разделы выше.</p>` +
      material.muu.map(linkRow).join("") + `</div>`;
  }
  $("#examMaterial").innerHTML = out ||
    emptyState({
      icon: "inbox",
      title: "Официальные материалы не загружены",
      note: "Здесь будут ссылки на официальные задания HARNO, когда их список добавят в приложение. Сами задания открываются на сайте экзамена.",
    });
}

/* A downloaded task opens here; anything not downloaded still links out
   (`cli harvest-exam --download`). */
const linkRow = it => it.local
  ? `<div class="lib-item">
       <button class="linky" data-task="${esc(it.id)}" data-fmt="${esc(it.format || "")}"
               data-file="${it.file ? 1 : 0}"
               lang="${langOf(it.title)}">${esc(it.title)}</button>
       <span class="lib-meta">${esc(it.format || "интерактивное")} · в приложении</span></div>`
  : `<div class="lib-item">
       <a href="${esc(it.url || "#")}" target="_blank" rel="noopener" lang="${langOf(it.title)}">${esc(it.title)}</a>
       <span class="lib-meta">${esc(it.format || "")}${
         it.audio_url ? " · " + uiIcon("note", "inline-ico") : ""}</span></div>`;


/* The task itself, opened where it was clicked: its text where the PDF gave
   any, the recording where the exam plays one, and the file itself always. */
async function openTask(row, id, format, hasFile) {
  const box = document.createElement("div");
  box.className = "exam-task";
  box.innerHTML = `<p class="hint">Загружаю…</p>`;
  row.after(box);
  const file = `/api/exam/file/${encodeURIComponent(id)}`;
  let text = null;
  try {
    text = await (await api(`/api/exam/text/${encodeURIComponent(id)}`)).json();
  } catch { /* audio, a scanned PDF, or a .docx: the file itself still opens */ }
  const own = ["mp3", "wav"].includes(format);       // the task *is* a recording
  const pdf = hasFile && format.toLowerCase() === "pdf";
  let native = null;
  if (pdf) {
    try {
      native = await (await api(`/api/exam/native/${encodeURIComponent(id)}`,
        null, "GET")).json();
    } catch { /* An older exam mount still has the original page reader. */ }
  }
  let pages = 0;
  if (pdf) {
    try {
      pages = (await (await api(`/api/exam/pages/${encodeURIComponent(id)}`,
        null, "GET")).json()).pages || 0;
    } catch { /* A corrupt PDF still leaves extracted text or a file fallback. */ }
  }
  // An EIS listening task carries its own recordings, one per question.
  const clips = own ? [file] : (text?.audio || []);
  let page = 1;
  box.innerHTML = `
    <div class="exam-task-head">
      ${hasFile && !pdf ? `<a class="ghost" href="${file}" target="_blank"
                      rel="noopener">открыть файл</a>` : ""}
      ${text?.url && !pdf ? `<a class="ghost" href="${esc(text.url)}" target="_blank"
                       rel="noopener">решить на сайте</a>` : ""}
      <button class="ghost" data-close lang="et">Sulge
        <span class="ru" lang="ru">закрыть</span></button>
    </div>
    ${clips.map((url, i) => `<div class="clip">${
        clips.length > 1 ? `<span class="lib-meta">${i + 1}</span>` : ""
      }<audio controls preload="none" src="${esc(url)}"></audio></div>`).join("")}
    ${native?.questions?.length ? `<form class="exam-native">
      <p class="hint">Официальные вопросы и проверенный ключ — © Haridus- ja Noorteamet.
        Результат этой тренировки не меняет освоение темы.</p>
      ${native.kind === "matching" ? `<p class="hint">Сопоставь каждую ситуацию с объявлением A–F.
        Букву можно выбрать для нескольких ситуаций.</p>` : ""}
      ${native.kind === "matching" ? `<div class="exam-figures">${native.figures.map(f =>
        `<figure><img src="/api/exam/image/${encodeURIComponent(id)}/${f.page}/${f.index}"
            alt="Официальное объявление ${f.letter}" loading="lazy">
            <figcaption lang="et">${f.letter}</figcaption></figure>`).join("")}</div>` : ""}
      ${native.questions.map(q => `<fieldset class="exam-question">
        <legend lang="et">${q.number}. ${esc(q.prompt)}</legend>
        ${native.kind === "matching" ? `<select name="q${q.number}"
          aria-label="${q.number}. kuulutus"><option value="" lang="et">Vali</option>
          ${native.figures.map(f => `<option value="${f.letter}">${f.letter}</option>`).join("")}
          </select>` : Object.entries(q.options).map(([key, value]) =>
          `<label lang="et"><input type="radio" name="q${q.number}" value="${key}">
          <b>${key}</b> ${esc(value)}</label>`).join("")}
      </fieldset>`).join("")}
      <button class="go" type="submit" lang="et">Kontrolli <span class="ru" lang="ru">проверить</span></button>
      <p class="hint" data-native-result role="status"></p>
    </form>` : ""}
    ${pdf ? `<details class="exam-preview" ${text ? "" : "open"}>
      <summary lang="et">Algne PDF <span class="ru" lang="ru">оригинал задания в приложении</span></summary>
      ${pages ? `<div class="exam-pages">
        <div class="row">
          <button class="ghost" data-prev disabled lang="et">Eelmine <span class="ru" lang="ru">назад</span></button>
          <span class="hint" data-page-label>1 / ${pages}</span>
          <button class="ghost" data-next ${pages === 1 ? "disabled" : ""} lang="et">Järgmine <span class="ru" lang="ru">дальше</span></button>
        </div>
        <img src="/api/exam/page/${encodeURIComponent(id)}/${page}"
          alt="Официальное задание, страница 1 из ${pages}" loading="lazy">
      </div>` : `<p class="hint">Страницы PDF не удалось показать.</p>
        <a href="${file}" target="_blank" rel="noopener">Открыть оригинал</a>`}
    </details>` : ""}
    ${native?.questions?.length ? "" : native?.pages?.some(p => p.text || p.images?.length)
      ? native.pages.map(p => `<section class="exam-page-text">
          <h4 lang="et">Lehekülg ${p.number}</h4>
          ${p.images?.length ? `<div class="exam-figures">${p.images.map((figure, i) =>
            `<figure><img src="/api/exam/image/${encodeURIComponent(id)}/${p.number}/${figure.index}"
               alt="Официальное изображение ${i + 1}, страница ${p.number}" loading="lazy">
               <figcaption lang="et">Pilt ${i + 1}</figcaption></figure>`).join("")}</div>` : ""}
          ${p.needs_review ? `<p class="hint">${p.method === "pdf-text"
            ? "На этой странице мало извлечённого текста. Проверь оригинал выше."
            : "Автоматическое распознавание — черновик; колонки и цифры могут быть неверными. Проверь оригинал выше."}</p>` : ""}
          ${p.method === "pdf-text" && p.text
            ? `<pre class="exam-text" lang="et">${esc(p.text)}</pre>`
            : p.method !== "pdf-text" ? `<details><summary lang="et">OCR tekst <span class="ru" lang="ru">черновик текста</span></summary>
                 <pre class="exam-text" lang="et">${esc(p.text)}</pre></details>` : ""}
        </section>`).join("")
      : text ? `<p class="hint">${esc(text.note)}</p>
              <pre class="exam-text" lang="et">${esc(text.text)}</pre>`
           : `<p class="hint">${own
                ? "Официальная запись — © Haridus- ja Noorteamet."
                : pdf ? "Текст не извлёкся; оригинал показан выше."
                : "Текст не разобрался — открой файл."}</p>`}`;
  box.querySelector("[data-close]").onclick = () => box.remove();
  const form = box.querySelector(".exam-native");
  if (form) form.onsubmit = async e => {
    e.preventDefault();
    const answers = {};
    for (const q of native.questions) {
      const choice = form.querySelector(`select[name="q${q.number}"]`) ||
        form.querySelector(`input[name="q${q.number}"]:checked`);
      if (choice?.value) answers[q.number] = choice.value;
    }
    const result = form.querySelector("[data-native-result]");
    if (Object.keys(answers).length !== native.questions.length) {
      result.textContent = "Ответь на все вопросы.";
      return;
    }
    try {
      const graded = await (await api(`/api/exam/native/${encodeURIComponent(id)}/check`,
        {answers})).json();
      result.textContent = `${graded.correct} из ${graded.total} верно. ` +
        graded.results.filter(x => !x.correct).map(x => `${x.number}: ${x.answer}`).join(" · ");
    } catch (error) { result.textContent = error.message; }
  };
  if (pages) {
    const image = box.querySelector(".exam-pages img");
    const show = n => {
      page = n;
      image.src = `/api/exam/page/${encodeURIComponent(id)}/${n}`;
      image.alt = `Официальное задание, страница ${n} из ${pages}`;
      box.querySelector("[data-page-label]").textContent = `${n} / ${pages}`;
      box.querySelector("[data-prev]").disabled = n === 1;
      box.querySelector("[data-next]").disabled = n === pages;
    };
    box.querySelector("[data-prev]").onclick = () => show(page - 1);
    box.querySelector("[data-next]").onclick = () => show(page + 1);
  }
}


document.addEventListener("click", e => {
  const next = e.target.closest("#tab-exam button[data-open-task]");
  if (next) {
    const target = [...document.querySelectorAll("#examMaterial button[data-task]")]
      .find(b => b.dataset.task === next.dataset.openTask);
    if (target) {
      target.click();
      target.scrollIntoView({behavior: "smooth", block: "start"});
    }
    return;
  }
  const b = e.target.closest("#tab-exam button[data-task]");
  if (!b) return;
  const row = b.closest(".lib-item");
  // A second click closes what the first opened.
  const open = row.nextElementSibling;
  if (open && open.classList.contains("exam-task")) open.remove();
  else openTask(row, b.dataset.task, b.dataset.fmt, b.dataset.file === "1");
});


document.querySelectorAll("#tab-exam .levels button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#tab-exam .levels button").forEach(x =>
    x.setAttribute("aria-selected", x === b));
  setExamLevel(b.dataset.level);
  loadExam();
  loadRail();
});


export async function loadVihikud() {
  const d = await (await api("/api/library?skill=eksam&limit=40", null, "GET")).json();
  const rows = (d.items || []).filter(i => i.external);
  $("#vihikudList").innerHTML = rows.length
    ? rows.map(linkRow).join("")
    : emptyState({
      icon: "inbox",
      title: "Тетради не загружены",
      note: "Здесь будут ссылки на консультационные тетради HARNO, когда их список добавят в приложение. Сами тетради открываются на сайте HARNO.",
    });
}

async function runCheckpoint() {
  const out = $("#checkpointOut"), note = $("#checkpointNote");
  const btn = $("#checkpointBtn");
  btn.disabled = true; out.innerHTML = ""; note.textContent = "Загружаю…";
  $("#checkpointScore").textContent = "";
  try {
    const d = await (await api(`/api/checkpoint/${examLevel()}?count=15`, null, "GET")).json();
    if (!d.items?.length) {
      note.textContent = "Для этого уровня упражнений пока нет.";
      return;
    }
    note.innerHTML = `${d.items.length} вопросов · для прохода ` +
      `<b>${Math.round(d.pass_mark * 100)}%</b>` +
      (d.ready === false ? " · <span class=\"hint\">уровень ещё не пройден</span>" : "");
    // Its own score line and end card: Rada's live in a panel that is not on screen.
    const tally = newTally("#checkpointScore", "#checkpointOut", runCheckpoint);
    tally.size = d.items.length;
    // Closing the set is what readiness counts as a checkpoint taken.
    const level = d.level;
    tally.done = async t => {
      try {
        await api(`/api/checkpoint/${level}/result`,
                  {asked: t.size, correct: t.correct});
        loadRail();
      } catch (e) {
        note.textContent = "Результат не сохранён: " + e.message;
      }
    };
    d.items.forEach((it, i) =>
      out.appendChild(renderPracticeItem(it, it.topic, i, {}, true, tally)));
  } catch (e) {
    note.textContent = "Ошибка: " + e.message;
  } finally { btn.disabled = false; }
}

$("#checkpointBtn").onclick = runCheckpoint;
