/* Sõnatrenn: from the meaning back to the Estonian word.

   Ten of the words the learner is learning (`õpin`), topped up with the
   commonest new words that have a Russian meaning. The Russian is shown; the
   learner types the Estonian; the answer is compared with the word list's own
   spelling, so the code decides and nothing is invented. Like Vaba harjutus it
   records nothing: a miss is offered to Kordamine, where the FSRS queue — and
   its self-rated vocabulary cards — take over (`/api/mine`). */

import {icon} from "./icons.js";
import {$, api, esc, ruCount, wrongVerdict} from "./core.js";
import {emptyState, uiIcon} from "./chrome.js";
import {speakWord} from "./media.js";
import {refreshDueBadge} from "./review.js";

const SIZE = 10;
let set = [], marks = [], missed = [];

// The word list's spelling is the answer; case and outer spaces are not the point.
const norm = s => (s || "").trim().replace(/\s+/g, " ").toLocaleLowerCase("et");

const shuffle = xs => {
  const a = xs.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};


async function pool() {
  const get = async q => ((await (await api(`/api/vocab?${q}`, null, "GET")).json()).items || [])
    .filter(w => (w.russian || "").trim());
  let words = await get("status=learning&limit=200");
  if (words.length < SIZE) {
    const fresh = await get("level=A1&status=new&limit=200");
    const have = new Set(words.map(w => w.word));
    words = words.concat(fresh.filter(w => !have.has(w.word)).slice(0, 60));
  }
  return shuffle(words).slice(0, SIZE);
}


function paintBeads() {
  $("#workoutBeads").innerHTML = set.map((_, i) => {
    const m = marks[i];
    const cls = m === true ? "ok" : m === false ? "no"
      : i === marks.filter(x => x !== undefined).length ? "now" : "";
    return `<span class="bead ${cls}"></span>`;
  }).join("");
  const done = marks.filter(x => x !== undefined).length;
  $("#workoutScore").textContent = done
    ? `${marks.filter(Boolean).length}/${done} верно` : "";
}


const forms = w => (w.genitive || w.partitive) ? `<div class="word-forms">
    ${w.genitive ? `<span><b lang="et">omastav</b> <span lang="et">${esc(w.genitive)}</span></span>` : ""}
    ${w.partitive ? `<span><b lang="et">osastav</b> <span lang="et">${esc(w.partitive)}</span></span>` : ""}
  </div>` : "";


async function queue(word, btn) {
  btn.disabled = true;
  try {
    const r = await (await api("/api/mine", {word, context: null})).json();
    btn.innerHTML = r.queued
      ? `${uiIcon("check")}<span lang="et">Kordamises <span class="ru" lang="ru">в повторении</span></span>`
      : `<span lang="ru">${esc(r.reason || "уже в очереди")}</span>`;
    refreshDueBadge();
  } catch (e) {
    btn.disabled = false;
    btn.insertAdjacentHTML("afterend", `<span class="hint">${esc(e.message)}</span>`);
  }
}


function renderWord(w, i) {
  const el = document.createElement("div");
  el.className = "drill word-q";
  el.innerHTML = `
    <div class="drill-pos">${i + 1} / ${set.length}${w.pos_name
      ? ` · <span lang="et">${esc(w.pos_name)}</span>` : ""}${w.level ? ` · ${esc(w.level)}` : ""}</div>
    <div class="word-meaning" lang="ru">${esc(w.russian)}</div>
    <p class="hint">Как это по-эстонски? Начальная форма.</p>
    <div class="row">
      <input type="text" size="18" placeholder="sõna" lang="et" aria-label="Sõna — слово"
        autocapitalize="off" autocorrect="off" spellcheck="false" autocomplete="off">
      <button class="go" type="button" data-check lang="et">Kontrolli</button>
      <button class="ghost" type="button" data-hint lang="et">Vihje <span class="ru" lang="ru">подсказка</span></button>
    </div>
    <div class="verdict" role="status"></div>`;
  const input = el.querySelector("input"), verdict = el.querySelector(".verdict");
  let hinted = 0;
  el.querySelector("[data-hint]").onclick = () => {
    // One more letter each time; the length shows as the gaps still left.
    hinted = Math.min(hinted + 1, w.word.length - 1);
    input.placeholder = w.word.slice(0, hinted) + " _".repeat(w.word.length - hinted).trim();
    input.focus();
  };
  const check = () => {
    if (el.classList.contains("done")) return;
    if (!input.value.trim()) {
      verdict.className = "verdict";
      verdict.innerHTML = `<span class="hint">Впиши слово — тогда проверю.</span>`;
      input.focus();
      return;
    }
    const ok = norm(input.value) === norm(w.word);
    marks[i] = ok;
    if (!ok) missed.push(w);
    el.classList.add("done");
    el.querySelectorAll("input, button").forEach(x => x.disabled = true);
    verdict.className = "verdict " + (ok ? "ok" : "no");
    verdict.innerHTML = (ok
      ? `<span lang="et">✓ õige <i class="ru" lang="ru">верно</i></span> — <ins lang="et">${esc(w.word)}</ins>`
      : wrongVerdict(input.value, w.word, ""))
      + forms(w)
      + `<div class="row">
          <button class="iconbtn word-say" type="button" title="Kuula — прослушать"
            aria-label="Kuula — прослушать">${icon("speaker-high")}</button>
          ${ok ? "" : `<button class="ghost" type="button" data-queue lang="et">${uiIcon("plus")}Kordamisse
            <span class="ru" lang="ru">в повторение</span></button>`}
        </div>`;
    verdict.querySelector(".word-say").onclick = () => speakWord(w.word, msg =>
      verdict.insertAdjacentHTML("beforeend", `<span class="hint">${esc(msg)}</span>`));
    verdict.querySelector("[data-queue]")?.addEventListener("click", e =>
      queue(w.word, e.currentTarget));
    paintBeads();
    const next = el.nextElementSibling?.querySelector("input");
    if (next) next.focus({preventScroll: true});
    else finish();
    requestAnimationFrame(() => verdict.scrollIntoView({block: "nearest"}));
  };
  el.querySelector("[data-check]").onclick = check;
  input.addEventListener("keydown", e => { if (e.key === "Enter") check(); });
  return el;
}


function finish() {
  const out = $("#workoutOut");
  const right = marks.filter(Boolean).length;
  const great = right >= 0.8 * set.length;
  const end = document.createElement("div");
  end.className = "set-end" + (great ? " great" : "");
  end.setAttribute("role", "status");
  end.innerHTML = `<h4 lang="et">Trenn tehtud <i class="ru" lang="ru">тренировка пройдена</i></h4>
    <p class="set-score">${right}<small> из ${set.length} верно</small></p>
    <div class="beads" aria-hidden="true">${$("#workoutBeads").innerHTML}</div>
    ${missed.length ? `<ul class="set-missed">${missed.map(w =>
      `<li><b lang="et">${esc(w.word)}</b> <span lang="ru">— ${esc(w.russian)}</span></li>`).join("")}</ul>` : ""}
    <div class="row">
      ${missed.length ? `<button class="ghost" type="button" data-all lang="et">Kõik vead kordamisse
        <span class="ru" lang="ru">все ошибки в повторение</span></button>` : ""}
      <button class="go" type="button" data-again lang="et">${uiIcon("next")}Uued sõnad
        <span class="ru" lang="ru">новые слова</span></button>
    </div>`;
  end.querySelector("[data-again]").onclick = start;
  end.querySelector("[data-all]")?.addEventListener("click", async e => {
    const btn = e.currentTarget;
    btn.disabled = true;
    let queued = 0;
    for (const w of missed) {
      try { if ((await (await api("/api/mine", {word: w.word, context: null})).json()).queued) queued++; }
      catch { /* one refusal does not stop the rest */ }
    }
    btn.innerHTML = `<span lang="ru">В повторении: ${ruCount(queued, ["слово", "слова", "слов"])}</span>`;
    refreshDueBadge();
  });
  out.appendChild(end);
  requestAnimationFrame(() => end.scrollIntoView({block: "nearest"}));
}


async function start() {
  const out = $("#workoutOut"), btn = $("#workoutStart");
  btn.disabled = true;
  $("#workoutStage").hidden = false;
  out.innerHTML = `<p class="hint">Подбираю слова…</p>`;
  try {
    set = await pool();
  } catch (e) {
    out.innerHTML = `<div class="banner">Слова не загрузились: ${esc(e.message)}</div>`;
    btn.disabled = false;
    return;
  } finally { btn.disabled = false; }
  marks = []; missed = [];
  if (!set.length) {
    out.innerHTML = emptyState({icon: "inbox", title: "Слов с переводом пока нет",
      note: "Отметь слова в списке ниже или почитай тексты — перевод появится у слов, которые ты встречаешь."});
    $("#workoutBeads").innerHTML = "";
    return;
  }
  out.innerHTML = "";
  set.forEach((w, i) => out.appendChild(renderWord(w, i)));
  paintBeads();
  out.querySelector("input")?.focus({preventScroll: true});
}

$("#workoutStart").onclick = start;
