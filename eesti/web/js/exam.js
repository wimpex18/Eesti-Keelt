/* Am I ready: the level, the official material, and the checkpoint. */

import {emptyState, markIcon, uiIcon} from "./chrome.js";
import {$, api, esc} from "./core.js";
import {newTally, renderPracticeItem} from "./path.js";
import {loadRail} from "./review.js";
import {examLevel, setExamLevel} from "./state.js";

const MARK = {
  true:  ["yes", `<circle cx="8" cy="8" r="6"/><path d="m5.2 8.2 2 2 3.6-4"/>`],
  false: ["no", `<circle cx="8" cy="8" r="6"/><path d="M5.2 8h5.6"/>`],
  null:  ["unknown", `<circle cx="8" cy="8" r="6" stroke-dasharray="2.2 2.4"/><path d="M8 10.8v.01"/><path d="M6.4 6.4a1.6 1.6 0 1 1 1.6 2v.9"/>`],
};


export async function loadExam() {
  // The buttons are authored with A2 selected; if a level was remembered, the
  // strip has to agree with the variable before anything is fetched, or the
  // panel shows B1 data under a highlighted A2.
  document.querySelectorAll("#tab-exam button[data-level]").forEach(x =>
    x.setAttribute("aria-selected", x.dataset.level === examLevel()));

  const get = u => api(u, null, "GET").then(r => r.json());
  const [ready, material, path] = await Promise.all([
    get(`/api/readiness/${examLevel()}`), get(`/api/exam/${examLevel()}`),
    get("/api/curriculum").catch(() => ({})),
  ]);

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
        ${part.next_task ? `<div class="part-next">${uiIcon("next", "inline-ico")} ${part.next_task.url
            ? `<a href="${esc(part.next_task.url)}" target="_blank"
                 rel="noopener" lang="et">${esc(part.next_task.title)}</a>`
            : `<span lang="et">${esc(part.next_task.title)}</span>`}</div>` : ""}
      </span></div>`;
  }
  html += `</div>`;

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

const linkRow = it => `<div class="lib-item">
  <a href="${esc(it.url || "#")}" target="_blank" rel="noopener" lang="et">${esc(it.title)}</a>
  <span class="lib-meta">${esc(it.format || "")}${
    it.audio_url ? " · " + uiIcon("note", "inline-ico") : ""}</span></div>`;


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
