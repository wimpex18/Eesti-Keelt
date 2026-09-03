/* Kuulamine: dictation, the listening shelf, and turning any text into audio. */

import {$, api, esc, md, setLabel} from "./core.js";
import {mountAudio} from "./media.js";
import {loadRail} from "./review.js";

let dictNow = null, dictUrl = null;


export async function loadDictation() {
  const state = $("#dictState");
  try {
    const d = await (await api("/api/dictation/next?count=1", null, "GET")).json();
    $("#dictCaveat").innerHTML = md(d.caveat || "");
    dictNow = (d.passages || [])[0] || null;
    if (dictUrl) { URL.revokeObjectURL(dictUrl); dictUrl = null; }
    $("#dictTyped").value = "";
    $("#dictAudio").innerHTML = "";
    $("#dictOut").innerHTML = "";
    $("#dictScore").textContent = "";
    /* No corpus is a supported state, not an error — say which it is, in a
       place that survives the box being hidden. `#dictState` is inside
       `#dictBox`, so writing the explanation there and then hiding the box
       left the panel opening on the text-to-speech form with no hint that a
       dictation exercise exists at all. */
    $("#dictBox").hidden = !dictNow;
    const empty = $("#dictEmpty");
    empty.hidden = !!dictNow;
    if (dictNow) {
      state.textContent = d.note || "";
    } else {
      empty.textContent = d.note || "";
    }
  } catch (e) {
    state.textContent = "Не удалось получить предложение: " + e.message;
  }
}


async function dictAudio() {
  if (dictUrl) return dictUrl;
  // The voice comes with the sentence and is fixed for it, so replaying sounds
  // the same while different sentences bring different speakers -- which is what
  // the exam does and what one voice never trains.
  const r = await api("/api/speak",
                      {text: dictNow.text, speed: 0.7,
                       ...(dictNow.voice ? {voice: dictNow.voice} : {})});
  dictUrl = URL.createObjectURL(await r.blob());
  return dictUrl;
}


$("#dictPlay").onclick = async () => {
  if (!dictNow) return;
  const btn = $("#dictPlay"); btn.disabled = true;
  try {
    const url = await dictAudio();
    const out = $("#dictAudio");
    if (!out.querySelector("audio")) await mountAudio(out, url);
    const el = out.querySelector("audio");
    el.currentTime = 0; el.play().catch(() => {});
  } catch (e) {
    $("#dictState").textContent = "Звук не пришёл: " + e.message;
  } finally { btn.disabled = false; }
};


$("#dictNext").onclick = () => loadDictation();


$("#dictCheck").onclick = async () => {
  if (!dictNow) return;
  const btn = $("#dictCheck"); btn.disabled = true;
  try {
    const r = await (await api("/api/dictation/answer", {
      text: dictNow.text, typed: $("#dictTyped").value
    })).json();
    // Word by word, so a miss is visible as a miss rather than as a number.
    $("#dictOut").innerHTML =
      `<div class="corr"><div class="fix">` +
      r.words.map(w => w.ok
        ? `<span class="w-ok">${esc(w.target)}</span>`
        : `<span class="w-no">${esc(w.target)}</span>`).join(" ") +
      `</div>
      <div class="why">Правильно: ${esc(r.text)}</div>${r.extra.length
        ? `<div class="why">Лишнее: ${esc(r.extra.join(" "))}</div>` : ""}
      </div>`;
    $("#dictScore").textContent =
      `${r.matched}/${r.total} слов${r.correct ? " · пройдено" : ""}`;
    // The verdict counts dictations, so the rail is now out of date.
    loadRail();
  } catch (e) {
    $("#dictScore").textContent = "Ошибка: " + e.message;
  } finally { btn.disabled = false; }
};

export async function loadListenLibrary() {
  const box = $("#listenLib");
  if (!box) return;
  try {
    const {modes} = await (await api("/api/modes", null, "GET")).json();
    const learn = (modes || []).find(m => m.id === "oppimine");
    // Everything in this mode except reading, which has its own tab.
    const wanted = (learn?.sections || []).filter(
      sec => sec.id !== "lugemine" && sec.items > 0);
    /* Silence is the one answer that cannot be acted on. An archive with
       nothing in it looked identical to an archive that failed to load and
       to a panel that never had one. */
    if (!wanted.length) {
      box.innerHTML = `<p class="empty">Архив передач пуст — материал ещё не
        загружен. Его наполняют <code>cli harvest</code> и
        <code>cli harvest-reading</code>.</p>`;
      return;
    }

    box.innerHTML = wanted.map(sec => `
      <h3 class="sec-head">${esc(sec.et)}
        <span class="hint">${sec.items}${sec.with_audio ? " · ♪ " + sec.with_audio : ""}</span></h3>
      <p class="hint sec-note">${esc(sec.note || "")}</p>
      <div class="sec-list" data-section="${esc(sec.id)}"></div>`).join("");

    for (const el of box.querySelectorAll(".sec-list")) {
      const id = el.dataset.section;
      const {items} = await (await fetch(
        `/api/library?section=${encodeURIComponent(id)}&limit=60`)).json();
      // A pointer is a link, not a player. Ten of these are EIS tasks whose
      // audio and scoring live on eis.harno.ee — nothing of theirs is stored
      // here, so an expandable row would open on an empty panel. The exam
      // section already made this distinction; this list has to make it too.
      el.innerHTML = (items || []).map(it => it.external
        ? `<a class="lib-item" href="${esc(it.url || "#")}" target="_blank"
              rel="noopener">
             <h4>${esc(it.title)}</h4>
             <span class="lib-meta">${it.level ? esc(it.level) + " · " : ""}EIS ↗</span>
           </a>`
        : `<div class="lib-item" data-id="${esc(it.id)}">
             <h4>${esc(it.title)}</h4>
             <span class="lib-meta">${it.words ? it.words + " слов" : "аудио"}${
               it.audio_url ? " · ♪" : ""}${it.level ? " · " + esc(it.level) : ""}</span>
             <div class="lib-open" hidden></div>
           </div>`).join("");
      el.querySelectorAll(".lib-item[data-id]").forEach(row =>
        row.onclick = () => openListenItem(row));
    }
  } catch (e) {
    box.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  }
}

async function openListenItem(row) {
  const out = row.querySelector(".lib-open");
  if (!out.hidden) { out.hidden = true; out.innerHTML = ""; return; }
  out.hidden = false;
  out.innerHTML = `<span class="hint">Загружаю…</span>`;
  try {
    const d = await (await api("/api/library/" + row.dataset.id, null, "GET")).json();
    out.innerHTML = "";
    if (d.audio_url) await mountAudio(out, d.audio_url);
    if (d.body && d.body.trim()) {
      const p = document.createElement("div");
      p.className = "listen-text";
      p.textContent = d.body;
      out.appendChild(p);
    }
    // Opening one is contact with the language, and the verdict counts it.
    loadRail();
  } catch (e) {
    out.innerHTML = `<span class="hint">Не удалось открыть: ${esc(e.message)}</span>`;
  }
}


// ── listening: any text → audio ─────────────────────────────────────
$("#speakBtn").onclick = async () => {
  const text = $("#ttsText").value.trim();
  if (!text) return;
  const btn = $("#speakBtn"); btn.disabled = true; setLabel(btn, "Синтезирую…");
  const out = $("#ttsOut"); out.innerHTML = "";
  try {
    const r = await api("/api/speak", {
      text, voice: $("#voice").value, speed: +$("#speed").value
    });
    const url = URL.createObjectURL(await r.blob());
    await mountAudio(out, url);
    out.querySelector("audio")?.play().catch(() => {});
  } catch (e) {
    out.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  } finally { btn.disabled = false; setLabel(btn, "Loe ette"); }
};
