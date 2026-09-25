/* The Reegel page: one topic's rule, a table of its forms, examples and the
   learner's own mistakes (`eesti/lessons.py`). Opened from any element with
   `data-lesson="<topic id>"`: Kogu rada, a running set, free practice. */

import {$, api, esc, md} from "./core.js";
import {icon} from "./icons.js";
import {showItem} from "./reading.js";

const sheet = $("#lessonSheet");


function tableHtml(t) {
  if (!t) return "";
  /* An empty corner cell means the first column labels the rows (cases,
     persons); otherwise it is data like the rest (numerals). */
  const labelled = !t.columns[0];
  return `<div class="lesson-table${labelled ? " labelled" : ""}"><table lang="et">
    <thead><tr>${t.columns.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${t.rows.map(r => `<tr>${r.map((c, i) =>
      i === 0 && labelled ? `<th scope="row">${esc(c)}</th>` : `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody>
  </table></div>
  ${t.source ? `<p class="hint">${esc(t.source)}</p>` : ""}`;
}


function render(L) {
  const rule = L.rule;
  let html = `<header class="lesson-head">
      <div><span class="lv" data-level="${esc(L.level)}">${esc(L.level)}</span>
        <h2 lang="et">${esc(L.et)} <i class="ru" lang="ru">${esc(L.ru)}</i></h2></div>
      <button class="iconbtn" id="lessonClose" type="button" aria-label="Sulge — закрыть">${icon("x", {weight: "bold"})}</button>
    </header>`;
  /* The gist first, then the mistake it prevents: the shape of a flashcard. */
  if (L.tip) html += `<div class="lesson-tip">
      <p lang="ru">${md(L.tip.gist_ru)}</p>
      <p class="lesson-mistake"><span class="hint" lang="ru">Частая ошибка:</span>
        <del lang="et">${esc(L.tip.wrong)}</del> → <ins lang="et">${esc(L.tip.right)}</ins></p>
    </div>`;
  if (rule) html += `<p class="lesson-rule">${md(rule.summary_ru)}</p>`;
  if (L.points_ru.length)
    html += `<ul class="lesson-points">${L.points_ru.map(p => `<li>${md(p)}</li>`).join("")}</ul>`;
  html += tableHtml(L.table);
  if (L.examples.length) html += `<h3 lang="et">Näited <i class="ru" lang="ru">примеры</i></h3>
    <ul class="lesson-examples" lang="et">${L.examples.map(e =>
      `<li>${esc(e.before)}<strong>${esc(e.answer)}</strong>${esc(e.after)}</li>`).join("")}</ul>`;
  if (L.mistakes.length) html += `<h3 lang="et">Minu vead <i class="ru" lang="ru">мои ошибки</i></h3>
    <ul class="lesson-mistakes">${L.mistakes.map(m => `<li><span lang="et">${esc(m.prompt)}</span><br>
      <del lang="et">${esc(m.given || "—")}</del> → <ins lang="et">${esc(m.expected)}</ins></li>`).join("")}</ul>`;
  if (L.reading.length) html += `<h3 lang="et">Loe <i class="ru" lang="ru">тексты с этой темой</i></h3>
    <ul class="lesson-reading">${L.reading.map(r => r.skill === "kuulamine"
      ? `<li lang="et">${esc(r.title)}</li>`
      : `<li lang="et"><button class="linky" type="button" data-read="${esc(r.id)}">${esc(r.title)}</button></li>`).join("")}</ul>`;
  /* One link per label: a topic's own source can name the same EKK section as
     its rule, and that one points at the section itself, so it wins. */
  const refs = new Map(L.sources.map(s => [s.label, s.url]));
  if (rule && !refs.has(`EKK ${rule.ekk_section}`)) refs.set(`EKK ${rule.ekk_section}`, rule.url);
  if (refs.size) html += `<p class="hint lesson-sources">Источник: ${[...refs].map(([label, url]) =>
    `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)}</a>`).join(" · ")}</p>`;
  if (L.drillable) html += `<div class="row"><button class="go" id="lessonPractice" lang="et">Harjuta
    <span class="ru" lang="ru">упражняться</span></button></div>`;
  return html;
}


export async function openLesson(topic, onPractice) {
  sheet.innerHTML = `<p class="hint">Загружаю…</p>`;
  if (!sheet.open) sheet.showModal();
  try {
    const L = await (await api(`/api/lesson/${encodeURIComponent(topic)}`, null, "GET")).json();
    sheet.innerHTML = render(L);
    $("#lessonClose").onclick = () => sheet.close();
    sheet.querySelectorAll("[data-read]").forEach(b => b.onclick = () => {
      sheet.close();
      // Through the hash, so the tab change enters history like any other.
      location.hash = "#read";
      showItem(b.dataset.read);
    });
    const go = $("#lessonPractice");
    if (go) go.onclick = () => { sheet.close(); (onPractice || practiseHandler)(topic); };
    $("#lessonClose").focus();
  } catch (e) {
    sheet.innerHTML = `<div class="banner">${esc(e.message)}</div>
      <div class="row"><button class="ghost" type="button" lang="et">Sulge <span class="ru" lang="ru">закрыть</span></button></div>`;
    sheet.querySelector("button").onclick = () => sheet.close();
  }
}


/* Set by the path module: how "Harjuta" starts a set on this topic. */
let practiseHandler = () => {};
export function onLessonPractice(fn) { practiseHandler = fn; }


// A click on the backdrop closes the sheet; a click inside it does not.
sheet.addEventListener("click", e => { if (e.target === sheet) sheet.close(); });

document.addEventListener("click", e => {
  const b = e.target.closest("[data-lesson]");
  if (!b || !b.dataset.lesson) return;
  e.preventDefault();
  openLesson(b.dataset.lesson);
});
