/* Kirjutamine: the grammar check, the error queue, and the written drill. */

import {emptyState} from "./chrome.js";
import {$, api, esc, md, setLabel} from "./core.js";
import {loadRail} from "./review.js";


async function runCheck() {
  const text = $("#text").value.trim();
  /* An empty box gets a message, in the language explanations are written in,
     rather than a button that appears dead. */
  if (!text) {
    $("#checkOut").innerHTML =
      `<p class="hint">Вставь эстонский текст — тогда проверю.</p>`;
    return;
  }
  const btn = $("#checkBtn"); btn.disabled = true; setLabel(btn, "Проверяю…");
  /* The chain can take six or seven seconds when a provider times out before the
     offline fallback answers. Say so where the answer will appear, so a slow check
     is not mistaken for a dead one and pressed again. */
  const out = $("#checkOut");
  out.innerHTML = `<p class="hint">Проверяю… это может занять несколько
    секунд, если провайдер не отвечает и подключается офлайн-разбор.</p>`;
  try {
    const res = await (await api("/api/check", {text})).json();
    let html = "";
    // How the check is running is information, not a warning: the answer
    // below it is still an answer.
    if (res.degraded && res.note) html += `<div class="banner info">${esc(res.note)}</div>`;
    /* What the text actually says, read back in Russian.

       A grammar chain tells you whether the Estonian is well formed, not whether it
       says what you meant: `Ma käisin arstiga` is correct and means you went *with*
       a doctor. Reading it back catches that.

       TartuNLP's NMT rather than the LLM: Estonian-trained, free and keyless. Absent
       rather than blocking when unavailable. */
    if (res.back_translation) {
      html += `<div class="corr"><span class="tag">Mida sa ütlesid <i class="ru">что ты сказал</i></span>
        <div class="gloss-late">${esc(res.back_translation)}</div>
        <div class="why">Обратный перевод (TartuNLP). Грамматика может быть
        верной, а смысл — не тем, который ты имел в виду.</div></div>`;
    }
    if (!res.corrections.length) {
      html += emptyState({
        icon: "done",
        title: "Ошибок не найдено",
        note: "Разбор форм не нашёл, к чему придраться в этом тексте.",
      });
    } else {
      // Object-case errors first: that is the documented priority gap.
      const sorted = [...res.corrections].sort(
        (a, b) => (b.tag === "obj-case") - (a.tag === "obj-case"));
      for (const c of sorted) {
        const fix = c.correct
          ? `<del>${esc(c.wrong)}</del> → <ins>${esc(c.correct)}</ins>`
          : `<ins>${esc(c.wrong)}</ins>`;
        // The "log it" button is the on-screen confirmation the Notion log
        // depends on. That log's value is that it is curated -- three rows
        // sharing a tag become the week's focus -- so a checker that pushed
        // every suspicion would turn a picked record into a dump of model
        // output and start the rule firing on noise. One click per error, made
        // by a person, is the whole design.
        html += `<div class="corr ${c.tag === "obj-case" ? "objcase" : ""}">
          <span class="tag">${esc(c.tag)}</span>
          <div class="fix">${fix}</div>
          <div class="why">${md(c.why)}</div>
          ${c.correct ? `<button class="logbtn" type="button"
            data-wrong="${esc(c.wrong)}" data-correct="${esc(c.correct)}"
            data-why="${esc(c.why || "")}" data-tag="${esc(c.tag)}"
            >+ Vigade logisse <i class="ru">в журнал ошибок</i></button>` : ""}</div>`;
      }
    }
    html += `<div class="engine">движок: <b>${esc(res.engine)}</b>${res.degraded ? " (ограниченный режим)" : ""}</div>`;
    out.innerHTML = html;
    out.querySelectorAll(".logbtn").forEach(b => b.onclick = () => queueError(b));
  } catch (e) {
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  } finally { btn.disabled = false; setLabel(btn, "Kontrolli"); }
}

async function queueError(btn) {
  btn.disabled = true;
  try {
    const r = await (await api("/api/notion/queue", {
      wrong: btn.dataset.wrong, correct: btn.dataset.correct,
      why: btn.dataset.why, tag: btn.dataset.tag,
    })).json();
    btn.textContent = r.queued ? "✓ В журнале" : "✓ Уже в журнале";
    loadQueue();
  } catch (e) {
    btn.textContent = "Не вышло";
    btn.disabled = false;
  }
}

async function loadQueue() {
  try {
    const d = await (await api("/api/notion/pending", null, "GET")).json();
    const rows = d.items || [];
    $("#queueCount").textContent = rows.length ? `(${rows.length})` : "";
    $("#queueBox").hidden = !rows.length;
    $("#queueList").innerHTML = rows.map(r => `
      <label class="qrow">
        <input type="checkbox" value="${r.id}" checked>
        <span><b>${esc(r.wrong)}</b> → <b>${esc(r.correct)}</b>
          <span class="hint">${esc(r.tag)}</span></span>
      </label>`).join("");
    $("#queueSend").disabled = !d.can_push;
    $("#queueNote").textContent = d.can_push
      ? "Отправляются только отмеченные строки."
      : "NOTION_TOKEN не задан — строки останутся в очереди.";
  } catch { $("#queueBox").hidden = true; }
}

loadQueue();


$("#queueSend").onclick = async () => {
  const ids = [...$("#queueList").querySelectorAll("input:checked")]
    .map(i => +i.value);
  if (!ids.length) return;
  const btn = $("#queueSend"); btn.disabled = true;
  try {
    const r = await (await api("/api/notion/push", {ids})).json();
    // A row that failed stays queued, so reloading is the honest report of what is
    // left. The outcome line goes after the reload, or `loadQueue` would overwrite it.
    await loadQueue();
    $("#queueNote").textContent =
      `Отправлено ${r.sent.length}${r.failed.length
        ? `, не прошло ${r.failed.length}` : ""}.`;
    loadRail();
  } catch (e) {
    $("#queueNote").textContent = e.message;
  } finally { btn.disabled = false; }
};


$("#checkBtn").onclick = runCheck;

$("#text").addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runCheck();
});


// ── drills ──────────────────────────────────────────────────────────
let answered = 0, correct = 0;

$("#drillBtn").onclick = async () => {
  const rule = $("#rule").value;
  const body = {
    count: +$("#count").value,
    levels: $("#level").value.split(","),
    ...(rule ? {rules: [rule]} : {})
  };
  answered = correct = 0; $("#score").textContent = "";
  const out = $("#drillOut"); out.innerHTML = "";
  try {
    const {drills} = await (await api("/api/drills", body)).json();
    drills.forEach((d, i) => out.appendChild(renderDrill(d, i)));
  } catch (e) {
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  }
};


function renderDrill(d, i) {
  const el = document.createElement("div");
  el.className = "drill";
  el.innerHTML = `
    <div class="prompt">${esc(d.prompt).replace("____", '<span class="blank">____</span>')}</div>
    <div class="row">
      <input type="text" placeholder="${esc(d.lemma)} → ?" size="18">
      <button class="ghost">Kontrolli</button>
      <span class="hint">${esc(d.lemma)}${d.level ? " · " + esc(d.level) : ""}</span>
    </div>
    <div class="verdict" role="status"></div>`;
  const input = el.querySelector("input"), verdict = el.querySelector(".verdict");
  const grade = () => {
    if (input.disabled) return;
    /* An empty box is not an answer: submitting one would lock the item and score it
       wrong, and the first item is focused on load, so a stray Enter would count
       against the accuracy that gates mastery. Ask again instead. */
    if (!input.value.trim()) {
      verdict.className = "verdict";
      verdict.innerHTML = `<span class="hint">Впиши форму — тогда проверю.</span>`;
      input.focus();
      return;
    }
    const ok = input.value.trim().toLowerCase() === d.answer.toLowerCase();
    input.disabled = true;
    answered++; if (ok) correct++;
    verdict.className = "verdict " + (ok ? "ok" : "no");
    verdict.innerHTML = ok
      ? `✓ õige <i class="ru">верно</i> — <strong>${esc(d.prompt.replace("____", d.answer))}</strong>`
      : `✗ <strong>${esc(d.answer)}</strong>, а не <em>${esc(d.distractor)}</em><br>
         <span class="why">${md(d.why_ru)}</span>`;
    $("#score").textContent = `${correct}/${answered} верных`;
  };
  el.querySelector("button").onclick = grade;
  input.addEventListener("keydown", e => { if (e.key === "Enter") grade(); });
  if (i === 0) setTimeout(() => input.focus(), 0);
  return el;
}
