/* Rada: the syllabus, where you stand on it, and one topic's practice. */

import {RU, stateIcon} from "./chrome.js";
import {$, api, esc, md, setLabel, taskLine} from "./core.js";
import {loadRail, refreshDueBadge} from "./review.js";

if (matchMedia("(min-width:1080px)").matches) {
  const all = $("#pathAll");
  if (all) all.open = true;
}


// ── the path ────────────────────────────────────────────────────────
let pathTopic = null, pathAnswered = 0, pathCorrect = 0;

let pathMeta = {};

function themeApplies() {
  const meta = pathMeta[pathTopic];
  // Unknown topic (a stale page, or before the first load) errs towards
  // offering the control: a filter that silently does nothing is the bug being
  // fixed, and a filter withheld from a topic that supports it is the same bug
  // pointing the other way.
  return !meta || meta.themed !== false;
}


/* The note under the row, and the state of the select itself. */
function paintThemeNote() {
  const sel = $("#wordTheme"), note = $("#themeNote");
  if (!sel || !note) return;
  const meta = pathMeta[pathTopic];
  const name = meta ? meta.et : null;
  if (themeApplies()) {
    sel.disabled = false;
    note.innerHTML = `<b>Rada</b> выбирает <b>правило</b>, а
      <b>sõnavara teema</b> — <b>слова</b>, на которых это правило
      отрабатывается. Оси независимые: список тем ниже от этого выбора не
      меняется.`;
  } else {
    // Reset rather than leave a stale value behind a disabled control: a
    // selection nothing reads is the same lie in a quieter form.
    sel.value = "";
    sel.disabled = true;
    note.innerHTML = `У темы ${name ? "<b>" + esc(name) + "</b>" : "этой"}
      нет слов, которые можно заменить — это закрытый список форм, а не
      словарная тема. Выбор слов здесь ничего не изменил бы, поэтому он
      выключен.`;
  }
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
    paintThemeNote();

    $("#pathList").innerHTML = p.topics.map(t => {
      /* Names, not ids — the API resolves them now. Kept tolerant of an older
         payload so a stale cached page degrades to the previous behaviour
         rather than printing "undefined". */
      const needs = t.blocked_by || [];
      const blocked = needs.length ? ` ← ${needs.join(", ")}` : "";
      const acc = t.accuracy === null ? "" : ` · ${Math.round(t.accuracy * 100)}%`;
      pathMeta[t.id] = t;
      const testOut = t.state === "ready" || t.state === "in progress"
        ? `<button class="ghost" data-topic="${esc(t.id)}">harjuta <i class="ru">решать</i></button>` : "";
      return `<div class="topic ${t.state.replace(" ", "-")}">
        <span class="st">${stateIcon(t.state)}${esc(RU[t.state] || t.state)}</span>
        <span class="lv" data-level="${esc(t.level)}">${esc(t.level)}</span>
        <span>${esc(t.et)}${esc(blocked)}${acc}</span>
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
    if (s.rada) html += `<div class="corr"><span class="tag">Rada</span>
      <div class="fix">${s.rada.mastered}/${s.rada.total} тем пройдено,
      ${s.rada.available} открыто</div>
      <div class="why">Следующая: ${esc(s.rada.next_et || "—")}${
        s.rada.next_ru ? ` — ${esc(s.rada.next_ru)}` : ""}</div></div>`;
    if (s.sonavara) html += `<div class="corr"><span class="tag">Sõnavara</span>
      <div class="fix">${s.sonavara.known_in_top} слов из первых
      ${s.sonavara.top}</div><div class="why">` +
      s.sonavara.bands.map(b =>
        `${b.from}–${b.to}: ${b.known}/${b.size}`).join(" · ") +
      // Two different facts, kept apart. "known" is what the learner declared
      // they know; this is what the app can translate for them. The second
      // grows on its own as they study, so it is not an achievement and is not
      // presented as one.
      (s.sonavara.glossed != null
        ? `<div class="gloss-late">${s.sonavara.glossed} слов с переводом
           <span class="hint">(пополняется само · сегодня осталось
           ${s.sonavara.gloss_budget_left})</span></div>` : "") + `</div></div>`;
    if (s.kordamine) html += `<div class="corr"><span class="tag">Kordamine</span>
      <div class="fix">${s.kordamine.due} к повторению,
      ${s.kordamine.scheduled} всего</div></div>`;
    if (s.raamatukogu) html += `<div class="corr"><span class="tag">Raamatukogu</span>
      <div class="fix">${s.raamatukogu.items || 0} открыто,
      ${s.raamatukogu.minutes || 0} минут</div></div>`;
    // The caveat comes from the API, in Russian, so it is written once and
    // cannot drift out of step with what the numbers mean.
    html += `<div class="engine">${esc(d.caveat || "")}</div>`;
    out.innerHTML = html;
  } catch (e) { out.textContent = e.message; }
}


$("#pathList").addEventListener("click", e => {
  const b = e.target.closest("button[data-topic]");
  if (b) {
    pathTopic = b.dataset.topic;
    $("#pathAll").open = false;
    paintThemeNote();
    startPractice();
  }
});


async function loadThemes() {
  try {
    const {themes} = await (await api("/api/themes", null, "GET")).json();
    $("#wordTheme").innerHTML = '<option value="">kõik sõnad</option>' +
      themes.map(t => `<option value="${esc(t.id)}">${esc(t.et)}</option>`).join("");
  } catch {}
}


async function startPractice() {
  const out = $("#practiceOut"); out.innerHTML = "";
  pathAnswered = 0; pathCorrect = 0; $("#pathScore").textContent = "";
  const btn = $("#practiceBtn"); btn.disabled = true; setLabel(btn, "Загружаю…");
  try {
    const body = {count: 10};
    if (pathTopic) body.topic = pathTopic;
    const theme = themeApplies() ? $("#wordTheme").value : "";
    if (theme) body.theme = theme;
    const res = await (await api("/api/practice", body)).json();
    if (!res.items.length) {
      // An empty topic is still a topic. The 13 with no generator carry an EKK
      // reference, and dropping it here left the learner with a sentence
      // explaining that nothing would happen and nowhere to go instead.
      let msg = `<div class="banner">${esc(res.detail || "ничего не пришло")}`;
      if (res.reference && res.reference.known)
        msg += ` · <a href="${esc(res.reference.url)}" target="_blank" rel="noopener">EKK ${esc(res.reference.ekk_section)}</a>`;
      out.innerHTML = msg + `</div>`;
      /* Measured across the whole grid: 31 of 198 topic x theme pairs return
         fewer than three items and 6 return none, because a corpus cloze needs
         a sentence *containing* a theme noun, which is far rarer than the noun
         existing. The learner picked a legitimate combination and hit a dead
         end; the way out is one click, so it is a button and not a sentence. */
      if (res.theme_emptied) {
        const again = document.createElement("button");
        again.className = "ghost";
        again.innerHTML = 'Proovi ilma teemata<span class="ru">без темы</span>';
        again.onclick = () => { $("#wordTheme").value = ""; startPractice(); };
        out.appendChild(again);
      }
      return;
    }
    pathTopic = res.topic;
    paintThemeNote();
    // A reference, not a warning: `info` rather than the default amber.
    let head = `<div class="banner info"><strong>${esc(res.et)}</strong> · ${esc(res.level)}`;
    /* A short set is not a broken one, but it is not the ten that were asked
       for either, and silence there reads as "this topic only has three". */
    if (res.theme && res.items.length < 10)
      head += ` · <span class="hint">по этой теме нашлось ${res.items.length}</span>`;
    if (res.reference && res.reference.known)
      head += ` · <a href="${esc(res.reference.url)}" target="_blank" rel="noopener">EKK ${esc(res.reference.ekk_section)}</a>`;
    head += `</div>`;
    out.innerHTML = head;
    res.items.forEach((it, i) =>
      out.appendChild(renderPracticeItem(it, res.topic, i, res.glosses || {})));
  } catch (e) {
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  } finally { btn.disabled = false; setLabel(btn, "Harjuta"); }
}


export function renderPracticeItem(it, topic, i, glosses) {
  /* What the word means, when the app already knows.

     A B1 object-case set draws lemmas like `etendus`, `luuletus` and
     `rahakott`. The morphology can be got right without knowing any of them,
     and then the exercise has taught half of what it appears to teach. The
     gloss comes from the local store, so it is either instantly there or
     absent — a practice set never waits on a dictionary. */
  const ru = (glosses || {})[it.lemma] || [];
  const el = document.createElement("div");
  el.className = "drill";
  el.innerHTML = `
    <div class="prompt">${esc(it.prompt).replace("____", '<span class="blank">____</span>')}</div>
    ${it.choices && it.choices.length ? `
    <!-- Word order is the one topic whose unit is the whole sequence, so it
         is answered by choosing a sentence rather than typing a word.
         Everything after this point is unchanged: the chosen sentence is
         submitted as the answer, the server grades it by the same string
         comparison, and it reaches mastery and the review queue by the same
         path as every other item. -->
    <div class="choices">
      ${it.choices.map(c =>
        `<button class="choice" data-choice="${esc(c)}">${esc(c)}</button>`).join("")}
    </div>
    <div class="row">
      ${taskLine(it, ru)}
    </div>` : `
    <div class="row">
      <input type="text" size="18" placeholder="?">
      <button class="ghost">Kontrolli</button>
      ${taskLine(it, ru)}
    </div>`}
    <div class="verdict"></div>`;
  const input = el.querySelector("input"), verdict = el.querySelector(".verdict");
  const choices = [...el.querySelectorAll(".choice")];
  // One holder for "what was answered", whichever shape the item took, so the
  // submit path below stays single.
  let picked = "";
  const lock = () => {
    if (input) input.disabled = true;
    choices.forEach(b => b.disabled = true);
  };
  const locked = () => (input ? input.disabled : choices[0]?.disabled);

  const grade = async () => {
    if (locked()) return;
    lock();
    let res;
    try {
      // The server grades and records: the client must not be the judge of
      // whether a topic has been mastered.
      res = await (await api("/api/practice/answer", {
        topic, prompt: it.prompt, answer: it.answer,
        given: input ? input.value : picked,
        distractor: it.distractor || "", lemma: it.lemma || "",
        label: it.hint || "", why_ru: it.why_ru || "",
      })).json();
    } catch (e) {
      verdict.className = "verdict no"; verdict.textContent = e.message; return;
    }
    pathAnswered++; if (res.correct) pathCorrect++;
    verdict.className = "verdict " + (res.correct ? "ok" : "no");
    // A choice item's prompt is a question with no blank in it, so filling the
    // blank echoed "Какое предложение верное?" back at the learner instead of
    // showing the sentence they got right. The rule is worth seeing either
    // way here: on a right answer it says *why* it was right, which for word
    // order is the whole lesson.
    verdict.innerHTML = res.correct
      ? (choices.length
          ? `✓ õige <i class="ru">верно</i> — <strong>${esc(it.answer)}</strong><br>
             <span class="why">${md(it.why_ru || "")}</span>`
          : `✓ õige <i class="ru">верно</i> — <strong>${esc(it.prompt.replace("____", it.answer))}</strong>`)
      : `✗ <strong>${esc(it.answer)}</strong>${it.distractor ? `, а не <em>${esc(it.distractor)}</em>` : ""}<br>
         <span class="why">${md(it.why_ru || "")}</span>`;
    /* The meaning arrives with the grade, not before it. `/api/practice/answer`
       looks up at most this one word, which is the "word in front of the
       learner" case rather than a batch — and after wrestling with the form is
       when it sticks. Only shown when the hint above did not already carry it. */
    if (res.russian?.length && !ru.length) {
      verdict.innerHTML += `<span class="gloss-late"><b>${esc(it.lemma)}</b> — `
        + `${esc(res.russian.slice(0, 3).join(", "))}</span>`;
    }
    let line = `${pathCorrect}/${pathAnswered} верных`;
    if (res.accuracy !== null) line += ` · ${Math.round(res.accuracy * 100)}% из последних ${res.gate.split("/")[1]}`;
    $("#pathScore").textContent = line;
    if (res.just_mastered) {
      // Good news wears the accent. `#pathHead` is shared with the error
      // path below, so the class is set at each use rather than once in the
      // markup -- otherwise whichever spoke last decides how the next one
      // looks.
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
    if (i === 0) setTimeout(() => input.focus(), 0);
  }
  return el;
}


$("#practiceBtn").onclick = startPractice;

loadThemes();
