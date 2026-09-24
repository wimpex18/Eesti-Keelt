/* Kordamine: the queue, the due badge, grading a card, and the desktop rail. */

import {emptyState, flowerSvg, forecastHtml, navIcon, sealsHtml} from "./chrome.js";
import {$, api, esc, md, ruCount, taskLine} from "./core.js";
import {speakWord} from "./media.js";
import {examLevel} from "./state.js";

/* The rail is refreshed after every graded answer; only the latest request paints. */
let railLoad = 0;

export async function loadRail() {
  // The cards, not the rail: the rail keeps its heading.
  const rail = $("#railCards");
  if (!rail || !matchMedia("(min-width:1080px)").matches) return;
  const mine = ++railLoad;
  try {
    /* `await` inside the array would serialise these — the promises have to
       be built first and awaited together. `soft` keeps the due count from
       being able to empty the whole rail. */
    const get = async u => (await (await api(u, null, "GET")).json());
    const soft = u => get(u).catch(() => ({}));
    const [ready, path, due, marks] = await Promise.all([
      get(`/api/readiness/${examLevel()}`),
      get("/api/curriculum"),
      soft("/api/review/stats"),
      soft(`/api/milestones/${examLevel()}`),
    ]);

    if (mine !== railLoad) return;
    /* `resume` is an id (`kusisonad`); the learner knows the topic by its
       name. The path tab already resolves it this way. */
    const next = (path.topics || []).find(t => t.id === path.resume);
    ready.parts = ready.parts || [];
    const untouched = ready.parts.filter(p => p.touched === false);
    /* The exam first, as the flower: four parts, none of which may be zero. Then
       what to do next, the queue, and the marks already made. The date only once
       one is chosen: with none, a countdown counts down to nothing. `data-for`
       names the tab whose panel already says the same thing; the rail drops that
       card there. */
    const dated = ready.days_to_decide !== null && ready.days_to_decide !== undefined;
    rail.innerHTML = `
      <div class="rail-card" data-for="exam">
        <h3 lang="et"><span>Eksam ${esc(ready.level)} <i class="ru" lang="ru">готовность</i></span>
          <a href="#exam" lang="et">Ülevaade</a></h3>
        ${flowerSvg(ready.parts, ready.contact_target || 3)}
        <div class="rail-note">${untouched.length
          ? `Не тронуто: <span lang="et">${untouched.map(p => esc(p.et)).join(", ")}</span>.
             Ни одна часть не должна быть нулём.`
          : "Контакт есть со всеми измеряемыми частями. Это не прогноз результата."}
          ${dated ? `<br><b>${esc(ready.countdown)}</b>` : ""}</div>
      </div>
      <div class="rail-card" data-for="path">
        <h3 lang="et">Järgmine <i class="ru" lang="ru">следующая тема</i></h3>
        ${next ? `<div class="rail-topic" lang="et">${esc(next.et)}</div>
          <a class="rail-go" href="#path" lang="et">Harjuta <i class="ru" lang="ru">упражняться</i></a>`
          : `<div class="rail-note">Все открытые темы пройдены.</div>`}
        <div class="rail-row"><span lang="et">Läbitud <i class="ru" lang="ru">пройдено</i></span>
          <b>${path.mastered}/${path.total}</b></div>
      </div>
      <div class="rail-card" data-for="review" data-also="status">
        <h3 lang="et"><span>Kordamist ootab <i class="ru" lang="ru">к повторению</i></span></h3>
        <div class="rail-row"><span class="rail-big">${due && due.due ? due.due : 0}</span>
          ${due && due.due ? `<a class="rail-go" href="#review" lang="et">Alusta →</a>` : ""}</div>
        ${due && due.total && due.forecast ? forecastHtml(due.forecast) : ""}
        <div class="rail-note">${due && due.total
          ? `${ruCount(due.total, ["карточка", "карточки", "карточек"])} в очереди.`
          : "Очередь пуста — ошибки и отмеченные слова вернутся сюда."}</div>
      </div>
      ${marks.milestones?.length ? `<div class="rail-card" data-for="status">
        <h3 lang="et">Märgid <i class="ru" lang="ru">вехи ${esc(ready.level)}</i></h3>
        ${sealsHtml(marks.milestones)}</div>` : ""}`;
  } catch (e) {
    rail.innerHTML = "";
  }
}

loadRail();
// A window widened past the desk width gets its rail at once.
matchMedia("(min-width:1080px)").addEventListener("change", loadRail);


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
    // The week ahead, so a quiet day is visibly a quiet day and not a broken queue.
    $("#reviewForecast").innerHTML = s.total && s.forecast ? forecastHtml(s.forecast) : "";
    // With nothing queued at all, the empty view is the whole screen.
    $("#reviewStart").hidden = !s.total;

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
          <span class="lib-meta"><span lang="et">${esc(r.kind_et || r.kind || "")}</span> · ошибок
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
  end.innerHTML = `<h4 lang="et">Kordamine tehtud <i class="ru" lang="ru">повторение пройдено</i></h4>
    <p class="set-score">${ruCount(reviewSize, ["карточка", "карточки", "карточек"])}</p>
    ${due ? `<div class="row"><button class="go" lang="et">Veel kaarte <span class="ru" lang="ru">ещё ${due}</span></button></div>`
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
      <button class="go fc-show" lang="et">Näita <i class="ru" lang="ru">показать</i></button>
      ${it.lapses ? `<span class="hint">ошибок: ${it.lapses}</span>` : ""}
    </div>
    <div class="fc-note hint" hidden></div>
    <div class="fc-back" hidden>
      <div class="fc-meaning">${esc(it.answer)}</div>
      ${it.why_ru ? `<div class="why">${md(it.why_ru)}</div>` : ""}
      <div class="row">
        <button class="ghost" data-r="again" lang="et">Ei mäleta <i class="ru" lang="ru">не помню</i></button>
        <button class="ghost" data-r="hard" lang="et">Raske <i class="ru" lang="ru">трудно</i></button>
        <button class="go" data-r="good" lang="et">Teadsin <i class="ru" lang="ru">знал</i></button>
      </div>
    </div>
    <div class="verdict" role="status"></div>`;

  el.querySelector(".fc-say").innerHTML = navIcon("speaker-high");
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
  /* A grammar card is answered, not self-rated: code grades what is typed (or
     which form is picked) and chooses the FSRS rating (`review.auto_rating`). */
  const ru = (glosses || {})[it.lemma] || [];
  const el = document.createElement("div");
  el.className = "drill";
  const forms = it.distractor
    ? [it.answer, it.distractor].sort((a, b) => a.localeCompare(b, "et")) : [];
  const answerBox = forms.length
    ? forms.map(f => `<button class="ghost" data-pick="${esc(f)}" lang="et">${esc(f)}</button>`).join("")
    : `<input type="text" size="18" placeholder="?" lang="et" aria-label="Vastus — ответ"
         autocapitalize="off" autocorrect="off" spellcheck="false" autocomplete="off">
       <button class="go" data-check lang="et">Kontrolli <i class="ru" lang="ru">проверить</i></button>`;
  el.innerHTML = `
    <div class="prompt" lang="et">${esc(it.prompt).replace("____", '<span class="blank">____</span>')}</div>
    ${it.context ? `<div class="rev-ctx" lang="et">${esc(it.context)}</div>` : ""}
    <div class="row" style="margin-top:var(--s2)">
      ${answerBox}
      ${taskLine({lemma: it.lemma, label: it.kind_et || it.kind || "", level: ""},
                 ru, {quiet: true})}${
        it.lapses ? `<span class="hint">ошибок: ${it.lapses}</span>` : ""}
    </div>
    <div class="verdict" role="status"></div>`;
  wireAnswer(el, it);
  return el;
}


function wireAnswer(el, it) {
  const verdict = el.querySelector(".verdict");
  const input = el.querySelector("input");
  const controls = () => el.querySelectorAll("button[data-pick], button[data-check], input");
  let started = null;
  const rendered = performance.now();
  el.addEventListener("focusin", () => { started ??= performance.now(); });
  const send = async given => {
    if (!given.trim()) {
      verdict.className = "verdict";
      verdict.innerHTML = `<span class="hint">Впиши форму — тогда проверю.</span>`;
      input?.focus();
      return;
    }
    controls().forEach(x => x.disabled = true);
    let r;
    try {
      r = await (await api("/api/review/grade", {
        id: it.id, given,
        latency_ms: Math.round(performance.now() - (started ?? rendered)),
      })).json();
    } catch (e) {
      controls().forEach(x => x.disabled = false);
      verdict.className = "verdict no";
      verdict.innerHTML = `Ответ не записан. ${esc(e.message)}
        <span class="hint">Попробуй ещё раз.</span>`;
      return;
    }
    reviewRated++;
    el.classList.add("done");
    if (reviewSize && reviewRated === reviewSize) finishReview();
    const when = r.interval_days < 1 ? "сегодня" : `через ${Math.round(r.interval_days)} дн.`;
    verdict.className = r.correct ? "verdict ok" : "verdict no";
    verdict.innerHTML = (r.correct
      ? `Верно: <strong lang="et">${esc(r.answer)}</strong>`
      : `Нужно: <strong lang="et">${esc(r.answer)}</strong>`)
      + ` — снова ${when}.`
      + (it.why_ru ? `<br><span class="why">${md(it.why_ru)}</span>` : "");
    refreshDueBadge();
    loadRail();
  };
  el.querySelectorAll("button[data-pick]").forEach(b =>
    b.onclick = () => send(b.dataset.pick));
  el.querySelector("button[data-check]")?.addEventListener("click", () => send(input.value));
  input?.addEventListener("keydown", e => { if (e.key === "Enter") send(input.value); });
}
