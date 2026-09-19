/* Kordamine: the queue, the due badge, grading a card, and the desktop rail. */

import {emptyState, navIcon} from "./chrome.js";
import {$, api, esc, md, ruCount, taskLine} from "./core.js";
import {speakWord} from "./media.js";
import {examLevel} from "./state.js";

export async function loadRail() {
  // The cards, not the rail: the rail keeps its heading.
  const rail = $("#railCards");
  if (!rail || !matchMedia("(min-width:1080px)").matches) return;
  try {
    /* `await` inside the array would serialise these — the promises have to
       be built first and awaited together. `soft` keeps the due count from
       being able to empty the whole rail. */
    const get = u => fetch(u).then(r => r.json());
    const soft = u => get(u).catch(() => ({}));
    const [ready, path, due] = await Promise.all([
      get(`/api/readiness/${examLevel()}`),
      get("/api/curriculum"),
      soft("/api/review/stats"),
    ]);

    const untouched = ready.parts.filter(p => p.touched === false);
    /* `resume` is an id (`kusisonad`); the learner knows the topic by its
       name. The path tab already resolves it this way. */
    const next = (path.topics || []).find(t => t.id === path.resume);
    /* One thing first: what to do next. Progress sits under it, the untouched exam
       parts after, and the exam date last — and only once a date is chosen: with
       none, "no exam chosen" on every screen is a countdown to nothing. `data-for` names the tab
       whose panel already says the same thing; the rail drops that card there. */
    const dated = ready.days_to_decide !== null && ready.days_to_decide !== undefined;
    rail.innerHTML = `
      <div class="rail-card" data-for="path">
        <h3>Järgmine <span class="ru">следующая тема</span></h3>
        ${next ? `<div class="rail-big rail-topic">${esc(next.et)}</div>
          <a class="rail-go" href="#path">Harjuta <i class="ru">тренировка</i></a>`
          : `<div class="rail-note">Все открытые темы пройдены.</div>`}
        <div class="rail-row"><span>Läbitud <i class="ru">пройдено</i></span>
          <b>${path.mastered}/${path.total}</b></div>
        ${due && due.due ? `<div class="rail-row">
          <a href="#review">Kordamist ootab <i class="ru">к повторению</i></a>
          <b>${due.due}</b></div>` : ""}
      </div>
      ${untouched.length ? `<div class="rail-card" data-for="exam">
        <h3>Puudutamata <span class="ru">не начато</span></h3>
        ${untouched.map(p => `<div class="rail-row"><span>${esc(p.et)}</span>
          ${p.next_task && p.next_task.url
            ? `<a href="${esc(p.next_task.url)}" target="_blank"
                 rel="noopener">ava</a>` : ""}</div>`).join("")}
        <div class="rail-note">Ни одна часть не должна быть нулём.</div>
      </div>` : ""}
      ${dated ? `<div class="rail-card" data-for="exam">
        <h3>Eksamini <span class="ru">до экзамена</span></h3>
        <div class="rail-big">${esc(ready.countdown)}</div>
        <div class="rail-note">${esc(ready.level)} · ${esc(ready.verdict)}</div>
      </div>` : ""}`;
  } catch (e) {
    rail.innerHTML = "";
  }
}

loadRail();


// ── review ──────────────────────────────────────────────────────────
export async function refreshDueBadge() {
  try {
    const s = await (await api("/api/review/stats", null, "GET")).json();
    const b = $("#dueBadge");
    b.hidden = !s.due; b.textContent = s.due || "";
    /* Nothing due means the button can only lead to "nothing to review", so it is
       off, and the line beside it says why and when that changes. The count is
       refreshed each time Järjekord opens and after every rating, so a card queued
       elsewhere switches it back on. A failed request leaves it on: the click then
       reports its own error. */
    $("#loadReview").disabled = !s.due;
    $("#reviewStats").textContent = s.due
      ? `${s.due} к повторению · ${s.total} всего`
      : s.total
        ? `Сегодня повторять нечего · ${s.total} в очереди на другие дни`
        : "";
    $("#reviewEmpty").hidden = !!s.total;

    /* Which words keep coming back wrong, named. A count says the queue is
       working; the names say what to look at. `lapses` is how many times the
       card has been failed after being learned, which is FSRS's own measure of
       "this one is not sticking". */
    const hard = $("#reviewHard"), rows = s.struggling || [];
    hard.hidden = !rows.length;
    if (rows.length)
      hard.innerHTML = `<div class="note">Не закрепляется — эти слова
        возвращаются чаще всего:</div>` + rows.map(r =>
        `<div class="lib-item"><b lang="et">${esc(r.lemma || "")}</b>
          <span class="lib-meta">${esc(r.kind_et || r.kind || "")} · ошибок
            ${r.lapses} из ${r.reps}</span></div>`).join("");
  } catch {}
}

refreshDueBadge();


$("#loadReview").onclick = async () => {
  const out = $("#reviewOut"); out.innerHTML = "";
  let items, glosses;
  try {
    ({items, glosses} = await (await api("/api/review?limit=20", null, "GET")).json());
  } catch (e) {
    out.innerHTML = `<div class="banner">Очередь не загрузилась. ${esc(e.message)}</div>`;
    return;
  }
  if (!items.length) {
    out.innerHTML = emptyState({
      icon: "done",
      title: "Повторять нечего",
      note: `Очередь пуста — всё, что было назначено на сегодня, сделано.
        Новые карточки появятся из ошибок и из слов, отмеченных при чтении.`,
    });
    return;
  }
  reviewSize = items.length; reviewRated = 0;
  for (const it of items) out.appendChild(renderReview(it, glosses || {}));
};


/* The end of a review session. Says it is done and, when more cards came due while
   the learner worked (an "again" rating brings one back today), offers them. */
let reviewSize = 0, reviewRated = 0;
async function finishReview() {
  const out = $("#reviewOut");
  if (out.querySelector(".set-end")) return;
  let due = 0;
  try { due = (await (await api("/api/review/stats", null, "GET")).json()).due; } catch {}
  const end = document.createElement("div");
  end.className = "set-end";
  end.setAttribute("role", "status");
  end.innerHTML = `<h4>Kordamine tehtud <i class="ru">повторение пройдено</i></h4>
    <p class="set-score">${ruCount(reviewSize, ["карточка", "карточки", "карточек"])}</p>
    ${due ? `<div class="row"><button class="go">Veel kaarte <span class="ru">ещё ${due}</span></button></div>`
          : `<p class="hint">На сегодня всё. Новые карточки появятся из ошибок и из
               слов, отмеченных при чтении.</p>`}`;
  end.querySelector("button")?.addEventListener("click", () => $("#loadReview").click());
  out.appendChild(end);
}

function renderVocabCard(it) {
  const el = document.createElement("div");
  el.className = "drill flashcard";
  el.innerHTML = `
    <div class="fc-face">
      <span class="fc-word" lang="et">${esc(it.lemma)}</span>
      <button class="iconbtn fc-say" type="button"
              title="Kuula — прослушать" aria-label="Kuula — прослушать"></button>
    </div>
    ${it.context ? `<div class="rev-ctx" lang="et">${esc(it.context)}</div>` : ""}
    <div class="row">
      <button class="go fc-show">Näita <i class="ru">показать</i></button>
      ${it.lapses ? `<span class="hint">ошибок: ${it.lapses}</span>` : ""}
    </div>
    <div class="fc-note hint" hidden></div>
    <div class="fc-back" hidden>
      <div class="fc-meaning">${esc(it.answer)}</div>
      ${it.why_ru ? `<div class="why">${md(it.why_ru)}</div>` : ""}
      <div class="row">
        <button class="ghost" data-r="again">Ei mäleta <i class="ru">не помню</i></button>
        <button class="ghost" data-r="hard">Raske <i class="ru">трудно</i></button>
        <button class="go" data-r="good">Teadsin <i class="ru">знал</i></button>
      </div>
    </div>
    <div class="verdict" role="status"></div>`;

  el.querySelector(".fc-say").innerHTML = navIcon(
    '<path d="M11 5 6.5 9H3v6h3.5L11 19z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/>'
    + '<path d="M18.5 5.5a9 9 0 0 1 0 13"/>');
  el.querySelector(".fc-say").onclick = () => speakWord(it.lemma, msg => {
    const note = el.querySelector(".fc-note");
    note.textContent = msg;
    note.hidden = false;
  });
  el.querySelector(".fc-show").onclick = e => {
    e.target.closest(".row").hidden = true;
    el.querySelector(".fc-back").hidden = false;
  };
  wireGrading(el, it);
  return el;
}

function wireGrading(el, it) {
  const verdict = el.querySelector(".verdict");
  const rate = on => el.querySelectorAll("button[data-r]").forEach(x => x.disabled = !on);
  el.querySelectorAll("button[data-r]").forEach(b => b.onclick = async () => {
    rate(false);
    let r;
    try {
      r = await (await api("/api/review/grade",
                           {id: it.id, rating: b.dataset.r})).json();
    } catch (e) {
      // Not recorded, so the card stays due: give the ratings back.
      rate(true);
      verdict.className = "verdict no";
      verdict.innerHTML = `Оценка не записана. ${esc(e.message)}
        <span class="hint">Попробуй ещё раз.</span>`;
      return;
    }
    reviewRated++;
    el.classList.add("done");
    if (reviewSize && reviewRated === reviewSize) finishReview();
    verdict.className = "verdict ok";
    verdict.innerHTML =
      `<strong>${esc(it.answer)}</strong> — снова ${r.interval_days < 1
        ? "сегодня" : `через ${Math.round(r.interval_days)} дн.`}` +
      (it.why_ru && !el.classList.contains("flashcard")
        ? `<br><span class="why">${md(it.why_ru)}</span>` : "");
    refreshDueBadge();
    loadRail();
  });
}


function renderReview(it, glosses) {
  if (it.kind === "vocab") return renderVocabCard(it);
  const ru = (glosses || {})[it.lemma] || [];
  const el = document.createElement("div");
  el.className = "drill";
  el.innerHTML = `
    <div class="prompt" lang="et">${esc(it.prompt).replace("____", '<span class="blank">____</span>')}</div>
    ${it.context ? `<div class="rev-ctx">${esc(it.context)}</div>` : ""}
    <div class="row" style="margin-top:var(--s2)">
      <button class="ghost" data-r="again">Ei mäleta <i class="ru">не помню</i></button>
      <button class="ghost" data-r="hard">Raske <i class="ru">трудно</i></button>
      <button class="go" data-r="good">Teadsin <i class="ru">знал</i></button>
      ${taskLine({lemma: it.lemma, label: it.kind_et || it.kind || "", level: ""},
                 ru, {quiet: true})}${
        it.lapses ? `<span class="hint">ошибок: ${it.lapses}</span>` : ""}
    </div>
    <div class="verdict" role="status"></div>`;
  wireGrading(el, it);
  return el;
}
