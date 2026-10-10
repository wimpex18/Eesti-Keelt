/* The Reegel page (DESIGN.md, Reegel): one topic's rule as a page with a back
   control. Its sources come first, then the gist (the first sentence of the
   topic's sourced summary), then — for a topic with a rule walk
   (`eesti/rulewalk.py`) — notice, ask, explain and contrast, and the form
   switch; then the sourced points, the forms, examples, the learner's own
   mistakes and texts. One primary: Harjuta, set in the phone's action bar.

   Every Estonian form here is code's: Vabamorf's, a generator's key, or a
   quoted source example, and every form name comes from the item through
   `interlinear()`. The one model-written paragraph (the walk's explanation) is
   labelled with its engine and takes no result colour. The ask step is graded
   by the server from the item it signed and records nothing.

   Opened from any element with `data-lesson="<topic id>"` (Kursus, a running
   set, free practice) and by the `#rule/<topic>` route. */

import {$, api, esc, md, interlinear} from "./core.js";
import {icon} from "./icons.js";
import {showItem} from "./reading.js";
import {retryableError, skeleton} from "./chrome.js";

const sheet = $("#lessonSheet");
let previous = "#course";
let request = 0;
function closeRule() { location.hash = previous; }

/* What depends on the page's width (form lines, a table that may scroll, the
   switch's height) is measured again when the width changes. One observer for
   the page; each render says what to measure. */
let measure = () => {};
let measuredWidth = 0;
new ResizeObserver(([entry]) => {
  const width = Math.round(entry.contentRect.width);
  if (width === measuredWidth) return;
  measuredWidth = width;
  measure();
}).observe(sheet);

/* Said once, politely, by the page's one announcer. Emptied first, so the same
   words said twice are heard twice. */
function say(text) {
  const out = $("#announce");
  if (!out) return;
  out.textContent = "";
  requestAnimationFrame(() => { out.textContent = text; });
}

/* An Estonian label and its gloss, each in its own voice. */
const glossed = (et, ru) => `<span lang="et">${esc(et)} <span class="ru" lang="ru">${esc(ru)}</span></span>`;
const heading = (id, et, ru) => `<h3 id="${id}" lang="et">${glossed(et, ru)}</h3>`;

/* A sentence of the walk with its word as an interlinear word in `state`. The
   name and its gloss are the server's, from the word's Vabamorf tag. */
const named = s => ({form_after: s.name || "", lemma: s.lemma, form_ru: s.form_ru || ""});
const line = (s, state) => `${esc(s.before)}${interlinear(s.form, named(s), {state})}${esc(s.after)}`;

/* A form line hangs from its word's start and does not wrap, so near the end
   of a narrow line it would run off the screen and widen the page. Here it
   moves left just enough to stay inside its sentence, still under the word;
   wider than the sentence itself (a 320px phone), it wraps at the sentence's
   width and the sentence makes room below for the extra line. */
function keepLinesInside(root = sheet) {
  root.querySelectorAll(".il-f").forEach(f => {
    const holder = f.closest(".rw-line") || f.closest("p, li") || sheet;
    f.style.left = f.style.width = f.style.whiteSpace = "";
    holder.style.paddingBottom = "";
    const box = holder.getBoundingClientRect();
    const room = Math.max(0, f.parentElement.getBoundingClientRect().left - box.left);
    if (f.getBoundingClientRect().width > box.width) {
      Object.assign(f.style, {whiteSpace: "normal", width: `${box.width}px`, left: `${-room}px`});
      const extra = f.getBoundingClientRect().bottom - holder.getBoundingClientRect().bottom;
      if (extra > 0) holder.style.paddingBottom = `${Math.ceil(extra) + 4}px`;
      return;
    }
    const over = f.getBoundingClientRect().right - box.right;
    if (over > 0) f.style.left = `${-Math.min(over, room)}px`;
  });
}

/* Where the walk's sentences come from, said under them. */
function provenance(list) {
  const quoted = [...new Set(list.map(s => s.source).filter(Boolean))];
  const built = list.some(s => !s.source);
  const parts = [];
  if (quoted.length) parts.push(`цитаты из ${quoted.join(", ")}`);
  if (built) parts.push("предложения из заданий Klint, формы — Vabamorf");
  return parts.length ? `<p class="hint rw-from" lang="ru">${esc(parts.join("; "))}.</p>` : "";
}


/* ── The head: back, title, sources ─────────────────────────────────── */

function sourcesOf(L) {
  /* One link per label: a topic's own source can name the same EKK section as
     its rule, and that one points at the section itself, so it wins. */
  const refs = new Map(L.sources.map(s => [s.label, s.url]));
  const rule = L.rule;
  if (rule && !refs.has(`EKK ${rule.ekk_section}`)) refs.set(`EKK ${rule.ekk_section}`, rule.url);
  return [...refs];
}

function headHtml(L) {
  const refs = sourcesOf(L);
  return `<a class="rule-back" href="${esc(previous)}" lang="et">${icon("arrow-left", {weight: "bold"})}Tagasi <span class="ru" lang="ru">назад</span></a>
    <header class="rule-head">
      <h2 id="ruleTitle" tabindex="-1" lang="et">${glossed(L.et, L.ru)}</h2>
      ${refs.length ? `<p class="rule-sources" lang="et">Allikad <span class="ru" lang="ru">источники</span>
        ${refs.map(([label, url]) => `<a href="${esc(url)}" target="_blank" rel="noopener" lang="et">${esc(label)}</a>`).join("")}</p>` : ""}
    </header>
    ${L.gist_ru ? `<p class="rule-gist" lang="ru">${md(L.gist_ru)}</p>` : ""}`;
}


/* ── The walk: notice, ask, explain, contrast ─────────────────────── */

function noticeHtml(n) {
  if (!n.examples.length) return "";
  return `<section class="rw-step rw-notice" aria-labelledby="rwNoticeH">
    ${heading("rwNoticeH", "Märka", "заметь разницу")}
    <ul class="rw-notice-list" role="list">${n.examples.map(e =>
      `<li class="rw-line prompt" lang="et">${line(e, "notice")}</li>`).join("")}</ul>
    <p class="rw-q" lang="ru">${md(n.question_ru)}</p>
  </section>`;
}

/* The gap, as the interlinear word awaits it: a blank with the lemma and its
   meaning under it. */
function gap(it) {
  return interlinear("   ", {lemma: it.lemma, lemma_ru: it.lemma_ru}, {state: "awaiting"})
    .replace('<span class="il-w">', '<span class="il-w"><span class="sr-only" lang="ru">пропуск</span>');
}

function askHtml(items) {
  if (!items.length) return "";
  return `<section class="rw-step rw-ask" aria-labelledby="rwAskH">
    ${heading("rwAskH", "Proovi", "выбери форму сам")}
    <ol class="rw-items" role="list">${items.map((it, i) => `<li class="rw-item" data-i="${i}"${i ? " hidden" : ""}>
      <p class="rw-line prompt" id="rwQ${i}" lang="et">${esc(it.before)}${gap(it)}${esc(it.after)}</p>
      <div class="rw-choices" role="group" aria-labelledby="rwQ${i}">${it.choices.map(c =>
        `<button type="button" class="rw-choice" data-form="${esc(c)}" lang="et">${esc(c)}</button>`).join("")}</div>
      <p class="rw-verdict"></p>
    </li>`).join("")}</ol>
    <p class="rw-checked" lang="et">Kontrollib kood <span class="ru" lang="ru">ответ проверяет код: Vabamorf и ключ задания; в прогресс не записывается</span></p>
    <button type="button" class="quiet rw-skip" lang="et">Näita selgitust <span class="ru" lang="ru">показать объяснение сразу</span></button>
  </section>`;
}

function explainHtml(e, hidden) {
  if (!e) return "";
  return `<section class="rw-step rw-explain rw-after" aria-labelledby="rwWhyH"${hidden ? " hidden" : ""}>
    <h3 id="rwWhyH" tabindex="-1" lang="et">${glossed("Miks nii", "почему так")}</h3>
    <div class="rw-model">
      <p class="rw-model-by" lang="et">Mudeli tekst <span class="ru" lang="ru">${esc(`написала модель ${e.engine} по ${e.source.label}; эстонские слова в нём проверены кодом`)}</span></p>
      <p class="rw-model-text" lang="ru">${md(e.text)}</p>
      <p class="rw-model-src" lang="et">Allikas <span class="ru" lang="ru">источник</span>
        <a href="${esc(e.source.url)}" target="_blank" rel="noopener" lang="et">${esc(e.source.label)}</a></p>
    </div>
  </section>`;
}

function contrastHtml(pairs, hidden) {
  if (!pairs.length) return "";
  return `<section class="rw-step rw-contrast rw-after" aria-labelledby="rwPairH"${hidden ? " hidden" : ""}>
    <h3 id="rwPairH" tabindex="-1" lang="et">${glossed("Vastanda", "неверно и верно")}</h3>
    <ul class="rw-pairs" role="list">${pairs.map(p => `<li class="rw-pair">
      <p class="rw-cond" lang="et">${glossed(p.et, p.ru)}</p>
      <p class="rw-wrong" lang="et">${icon("x", {weight: "bold", cls: "rw-mark"})}<span class="sr-only" lang="ru">неверно: </span>${esc(p.before)}<del>${esc(p.wrong)}</del>${esc(p.after)}</p>
      <p class="rw-right rw-line prompt" lang="et">${icon("check", {weight: "bold", cls: "rw-mark"})}<span class="sr-only" lang="ru">верно: </span>${line(p, "reference")}</p>
    </li>`).join("")}</ul>
  </section>`;
}


/* ── The form switch: one condition at a time ─────────────────────── */

function switchHtml(conditions, shown) {
  if (conditions.length < 2) return provenance(shown);
  const n = conditions.length;
  return `<section class="rw-switch" aria-labelledby="rwSwitchH">
    ${heading("rwSwitchH", "Muuda tingimust", "выбери условие — форма изменится")}
    <div class="seg rw-tabs" role="tablist" aria-labelledby="rwSwitchH" style="--n:${n};--n-phone:${n > 4 ? 3 : 2}">${conditions.map((c, i) =>
      `<button type="button" role="tab" id="rwTab${i}" aria-selected="${i === 0}" aria-controls="rwPanel" tabindex="${i === 0 ? 0 : -1}" data-i="${i}" lang="et">${glossed(c.et, c.ru)}</button>`).join("")}</div>
    <div class="rw-panel" role="tabpanel" id="rwPanel" aria-labelledby="rwTab0" tabindex="0">
      <p class="rw-line rw-big prompt" lang="et">${line(conditions[0], "reference")}</p>
    </div>
    ${provenance(shown)}
  </section>`;
}


/* ── The rest: points, forms, examples, mistakes, texts ───────────── */

function pointsHtml(points) {
  if (!points.length) return "";
  const li = p => `<li>${md(p)}</li>`;
  const more = points.slice(3);
  return `<section class="rule-points" aria-labelledby="rulePointsH">
    ${heading("rulePointsH", "Reegel", "правило по источникам")}
    <ul>${points.slice(0, 3).map(li).join("")}</ul>
    ${more.length ? `<details class="rule-more"><summary lang="et">Lisaks <span class="ru" lang="ru">подробнее, ещё ${more.length}</span></summary>
      <ul>${more.map(li).join("")}</ul></details>` : ""}
  </section>`;
}

/* A row label that names a case and its number ("nimetav · ainsus"): the
   number in the quieter voice, not after a dot. */
function rowLabel(c) {
  const [head, ...rest] = String(c).split(" · ");
  return rest.length ? `${esc(head)} <span class="sub">${esc(rest.join(" "))}</span>` : esc(c);
}

/* A table wider than the page scrolls inside itself; only then is it a region
   the keyboard can focus and scroll. */
function scrollable(box) {
  if (box.scrollWidth > box.clientWidth + 1) {
    box.tabIndex = 0;
    box.setAttribute("role", "region");
  } else {
    box.removeAttribute("tabindex");
    box.removeAttribute("role");
  }
}

function tableHtml(t) {
  if (!t) return "";
  /* An empty corner cell means the first column labels the rows (cases,
     persons); otherwise it is data like the rest (numerals). */
  const labelled = !t.columns[0];
  return `<section class="rule-forms" aria-labelledby="ruleFormsH">
    ${heading("ruleFormsH", "Vormid", "формы")}
    <div class="lesson-table${labelled ? " labelled" : ""}" aria-labelledby="ruleFormsH"><table lang="et">
    <thead><tr>${t.columns.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${t.rows.map(r => `<tr>${r.map((c, i) =>
      i === 0 && labelled ? `<th scope="row">${rowLabel(c)}</th>` : `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody>
    </table></div>
    ${t.source ? `<p class="hint" lang="ru">${esc(t.source)}</p>` : ""}
  </section>`;
}

function examplesHtml(L) {
  if (L.walk || !L.examples.length) return "";
  return `<section aria-labelledby="ruleExamplesH">
    ${heading("ruleExamplesH", "Näited", "примеры")}
    <ul class="rule-examples" lang="et">${L.examples.map(e =>
      `<li>${esc(e.before)}<strong>${esc(e.answer)}</strong>${esc(e.after)}</li>`).join("")}</ul>
  </section>`;
}

function mistakesHtml(list) {
  if (!list.length) return "";
  const solved = m => {
    const [before, ...after] = (m.prompt || "").split("____");
    return after.length ? `${esc(before)}<strong>${esc(m.expected)}</strong>${esc(after.join("____"))}` : esc(m.prompt);
  };
  return `<section aria-labelledby="ruleMistakesH">
    ${heading("ruleMistakesH", "Minu vead", "мои ошибки")}
    <ul class="rule-mistakes">${list.map(m => `<li><span class="rule-solved" lang="et">${solved(m)}</span>
      <span class="rule-yours" lang="et">Sinu vastus <span class="ru" lang="ru">твой ответ</span> <del>${esc(m.given || "—")}</del></span></li>`).join("")}</ul>
  </section>`;
}

function readingHtml(list) {
  if (!list.length) return "";
  return `<section aria-labelledby="ruleReadH">
    ${heading("ruleReadH", "Loe", "тексты с этой темой")}
    <ul class="rule-reading">${list.map(r => r.skill === "kuulamine"
      ? `<li lang="et">${esc(r.title)}</li>`
      : `<li lang="et"><button class="linky" type="button" data-read="${esc(r.id)}">${esc(r.title)}</button></li>`).join("")}</ul>
  </section>`;
}

function render(L) {
  const w = L.walk;
  const asked = w && w.ask.items.length > 0;
  return headHtml(L)
    + (w ? `<div class="rw">${noticeHtml(w.notice)}${askHtml(w.ask.items)}${explainHtml(w.explain, asked)}${contrastHtml(w.contrast, asked)}</div>
        ${switchHtml(w.switch.conditions, [...w.notice.examples, ...w.contrast, ...w.switch.conditions])}` : "")
    + pointsHtml(L.points_ru)
    + tableHtml(L.table)
    + examplesHtml(L)
    + mistakesHtml(L.mistakes)
    + readingHtml(L.reading)
    + (L.drillable ? `<div class="rule-actions"><button class="go" id="lessonPractice" type="button" data-primary lang="et">Harjuta <span class="ru" lang="ru">упражняться</span></button></div>` : "");
}


/* ── Behaviour ─────────────────────────────────────────────────────── */

/* The explanation and the pair appear once every item is answered, or when
   the learner asks for them: the learner chooses first (ADR-0009). */
function reveal(focus) {
  sheet.querySelectorAll(".rw-after[hidden]").forEach(s => { s.hidden = false; s.classList.add("rw-shown"); });
  sheet.querySelector(".rw-skip")?.remove();
  if (focus) sheet.querySelector("#rwWhyH, #rwPairH")?.focus();
}

function wireAsk(items) {
  const rows = [...sheet.querySelectorAll(".rw-item")];
  rows.forEach((row, i) => {
    const it = items[i];
    const buttons = [...row.querySelectorAll(".rw-choice")];
    const verdict = row.querySelector(".rw-verdict");
    const sentence = row.querySelector(".rw-line");
    buttons.forEach(b => b.addEventListener("click", async () => {
      const given = b.dataset.form;
      buttons.forEach(x => { x.disabled = true; });
      b.classList.add("picked");
      verdict.replaceChildren();
      let said;
      try {
        said = await (await api("/api/practice/answer", {
          topic: it.topic, prompt: it.prompt, answer: "", given, token: it.token, record: false})).json();
      } catch (error) {
        buttons.forEach(x => { x.disabled = false; });
        b.classList.remove("picked");
        verdict.replaceChildren(retryableError(error.message, () => b.click()));
        b.focus();
        return;
      }
      const ok = !!said.correct;
      const key = said.answer;
      sentence.innerHTML = `${esc(it.before)}${interlinear(key, {form_after: it.form_after, lemma: it.lemma, form_ru: it.form_ru},
        {state: ok ? "right" : "revealed"})}${esc(it.after)}`;
      keepLinesInside(sentence);
      verdict.innerHTML = ok
        ? `<span class="rw-ok" lang="et">${icon("check", {weight: "bold", cls: "rw-mark"})}Õige <span class="ru" lang="ru">верно</span></span>`
        : `<span class="rw-no" lang="et">${icon("x", {weight: "bold", cls: "rw-mark"})}Pole õige <span class="ru" lang="ru">неверно</span></span>
           <span class="rw-yours" lang="et">Sinu valik <span class="ru" lang="ru">твой выбор</span> <del>${esc(given)}</del></span>`;
      const next = rows[i + 1];
      const verdictSaid = `${ok ? "Верно" : `Неверно, твой выбор ${given}`}. ${key} — ${it.form_after}, ${it.form_ru}.`;
      if (next) {
        next.hidden = false;
        next.querySelector(".rw-choice")?.focus();
        say(verdictSaid);
      } else {
        reveal(true);
        say(`${verdictSaid} Ниже — объяснение.`);
      }
    }));
  });
  sheet.querySelector(".rw-skip")?.addEventListener("click", () => reveal(true));
}

/* The switch is a tablist: arrows, Home and End move the selection and the
   focus together, and only the selected tab is in the Tab order. The changed
   form is said once. */
function wireSwitch(conditions) {
  const list = sheet.querySelector(".rw-tabs");
  if (!list) return () => {};
  const tabs = [...list.querySelectorAll('[role="tab"]')];
  const panel = sheet.querySelector("#rwPanel");
  const sentence = panel.querySelector(".rw-line");
  /* The panel keeps the height of its tallest sentence, so switching moves
     nothing below it. Measured with each sentence in place, before paint. */
  const fit = () => {
    const shown = sentence.innerHTML;
    panel.style.minHeight = "";
    panel.style.minHeight = `${Math.max(...conditions.map(c => {
      sentence.innerHTML = line(c, "reference");
      keepLinesInside(sentence);
      return sentence.offsetHeight;
    }))}px`;
    sentence.innerHTML = shown;
    keepLinesInside(sentence);
  };
  const choose = (i, focus) => {
    tabs.forEach((t, k) => {
      t.setAttribute("aria-selected", String(k === i));
      t.tabIndex = k === i ? 0 : -1;
    });
    if (focus) tabs[i].focus();
    const c = conditions[i];
    if (panel.getAttribute("aria-labelledby") === tabs[i].id) return;
    panel.setAttribute("aria-labelledby", tabs[i].id);
    sentence.innerHTML = line(c, "reference");
    // Crossfade: restart the animation the stylesheet gives a fresh sentence.
    sentence.classList.remove("rw-swap");
    void sentence.offsetWidth;
    sentence.classList.add("rw-swap");
    keepLinesInside(sentence);
    say(`${c.et}: ${c.before}${c.form}${c.after} ${c.form} — ${c.name}, ${c.form_ru}.`);
  };
  tabs.forEach((t, i) => t.addEventListener("click", () => choose(i, false)));
  list.addEventListener("keydown", e => {
    const keys = ["ArrowRight", "ArrowLeft", "ArrowDown", "ArrowUp", "Home", "End"];
    if (!keys.includes(e.key)) return;
    const here = tabs.indexOf(document.activeElement);
    if (here < 0) return;
    e.preventDefault();
    const back = e.key === "ArrowLeft" || e.key === "ArrowUp";
    const next = e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1
      : back ? (here - 1 + tabs.length) % tabs.length : (here + 1) % tabs.length;
    choose(next, true);
  });
  return fit;
}

function wire(L, onPractice) {
  sheet.querySelectorAll("[data-read]").forEach(b => b.onclick = () => {
    closeRule();
    // Through the hash, so the tab change enters history like any other.
    location.hash = "#read";
    showItem(b.dataset.read);
  });
  const go = $("#lessonPractice");
  if (go) go.onclick = () => { closeRule(); (onPractice || practiseHandler)(L.id); };
  if (L.walk) wireAsk(L.walk.ask.items);
  const fitSwitch = L.walk ? wireSwitch(L.walk.switch.conditions) : () => {};
  measure = () => {
    sheet.querySelectorAll(".lesson-table").forEach(scrollable);
    keepLinesInside();
    fitSwitch();
  };
  measure();
}


export async function openLesson(topic, onPractice) {
  const mine = ++request;
  sheet.dataset.topic = topic;
  sheet.innerHTML = skeleton();
  if (!location.hash.startsWith("#rule/")) previous = location.hash || "#course";
  location.hash = "#rule/" + encodeURIComponent(topic);
  try {
    const L = await (await api(`/api/lesson/${encodeURIComponent(topic)}`, null, "GET")).json();
    if (mine !== request) return;
    sheet.innerHTML = render(L);
    wire(L, onPractice);
    $("#ruleTitle")?.focus({preventScroll: true});
  } catch (e) {
    if (mine !== request) return;
    sheet.innerHTML = `<a class="rule-back" href="${esc(previous)}" lang="et">${icon("arrow-left", {weight: "bold"})}Tagasi <span class="ru" lang="ru">назад</span></a>`;
    sheet.append(retryableError(e.message, () => openLesson(topic, onPractice)));
  }
}

export function ensureRule(topic) {
  if (topic && sheet.dataset.topic !== topic) openLesson(topic);
}


/* Set by the path module: how "Harjuta" starts a set on this topic. */
let practiseHandler = () => {};
export function onLessonPractice(fn) { practiseHandler = fn; }


document.addEventListener("click", e => {
  const b = e.target.closest("[data-lesson]");
  if (!b || !b.dataset.lesson) return;
  e.preventDefault();
  openLesson(b.dataset.lesson);
});
