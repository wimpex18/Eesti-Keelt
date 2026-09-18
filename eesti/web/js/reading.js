/* Lugemine: the shelf, opening a text, and looking a word up inside it. */

import {actsAsButton, emptyState, skeleton, uiIcon} from "./chrome.js";
import {$, api, esc, ruCount} from "./core.js";
import {YT, mountAudio, mountVideo} from "./media.js";
import {showWordCard} from "./vocab.js";

let libShown = 0;
const WORDS = ["слово", "слова", "слов"], TEXTS = ["текст", "текста", "текстов"];


async function loadLibrary(append = false) {
  const choice = $("#readLevel").value;
  const list = $("#libList");
  // The shape of the answer while it is fetched, rather than a blank panel.
  if (!append) { list.innerHTML = skeleton(5); libShown = 0; }
  $("#reader").hidden = true;
  $("#libList").hidden = false;

  /* Show the server's `detail` on a failed request; an error payload has no
     `.items`. */
  const ask = async (url) => {
    const r = await fetch(url);
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.detail || `${r.status} ${r.statusText}`);
    return body;
  };

  try {
    let items, note = "";
    let measured = true;
    let total = null, more = false;
    if (choice === "soovitatud") {
      const d = await ask("/api/reading/next?limit=25");
      items = d.items;
      // With nothing marked known, every text would score 0 %, which reads as "you
      // know nothing" rather than "not measured yet". Hide the number until there is a
      // vocabulary to measure against, and say why.
      measured = d.known_words > 0;
      note = measured
        ? `${ruCount(d.known_words, WORDS)} знакомо`
        : "Слова ещё не отмечены — показаны самые простые тексты.";
      /* The endpoint counts texts it could not score; showing the count explains why
         "texts known" and the list size can disagree. */
      if (d.unmeasurable)
        note += ` · ${d.unmeasurable} без разбора слов`;
    } else {
      const q = new URLSearchParams({
        skill: "lugemine", limit: "80", offset: String(libShown)});
      if (choice) q.set("band", choice);
      const d = await ask("/api/library?" + q);
      items = d.items;
      total = d.total;
      more = libShown + items.length < d.total;
    }
    libShown += items.length;

    /* `total` is the server's count for the same filter; `items.length` is only the
       page size. */
    $("#libCount").textContent = total != null && total > libShown
      ? `показано ${libShown} из ${total}${note ? " · " + note : ""}`
      : `${ruCount(libShown, TEXTS)}${note ? " · " + note : ""}`;
    $("#libMore").hidden = !more;
    if (!items.length && !append) {
      list.innerHTML = emptyState({
        icon: "inbox",
        title: "Текстов нет",
        note: `Тексты появятся здесь, когда библиотеку загрузят на сервер
          <span class="hint">(<code>cli harvest-reading</code>, <code>cli harvest-news</code>)</span>.`,
      });
      return;
    }
    // The skeleton stood in for this page of rows; they replace it, not follow it.
    if (!append) list.innerHTML = "";
    for (const it of items) {
      // An external row goes somewhere else, so it is a real link.
      const el = document.createElement(it.external ? "a" : "div");
      el.className = "lib-item" + (it.external ? " external" : "");
      // Coverage appears only where it was computed, so an unmeasured list never
      // shows "0 %".
      const cover = (measured && it.coverage !== undefined)
        ? ` · <b>${Math.round(it.coverage * 100)}%</b> знакомо` : "";
      const n = it.words ?? it.total;
      const size = n !== undefined ? ruCount(n, WORDS) : "";
      /* HARNO's tasks are indexed, never copied: `body` is empty by licence. They
         open the official page (`external`, `url`) instead of an empty reader. */
      if (it.external) {
        el.innerHTML = `<h4>${esc(it.title)}</h4>
          <span class="lib-meta">HARNO · задание на сайте экзамена ↗</span>`;
        el.href = it.url;
        el.target = "_blank";
        el.rel = "noopener";
      } else {
        el.innerHTML = `<h4>${esc(it.title)}</h4>
          <span class="lib-meta">${it.band ? esc(it.band) + " · " : ""}${size}${
            it.audio_url ? " · " + uiIcon("note", "inline-ico") : ""}${cover}</span>`;
        actsAsButton(el, () => openItem(it.id));
      }
      list.appendChild(el);
    }
  } catch (e) {
    list.innerHTML = `<div class="banner">Ошибка: ${esc(e.message)}</div>`;
  }
}

$("#loadLib").onclick = () => loadLibrary(false);

$("#libMoreBtn").onclick = () => loadLibrary(true);

$("#backToLib").onclick = () => { $("#reader").hidden = true; $("#libList").hidden = false; };


async function openItem(id) {
  const d = await (await api("/api/library/" + id, null, "GET")).json();
  $("#libList").hidden = true;
  $("#reader").hidden = false;
  $("#readerTitle").textContent = d.title;
  $("#readerMeta").textContent = `${esc(d.source)} · ${esc(d.licence)}`;
  // An item is a text, a recording or a film; the reader shows whichever it
  // has rather than assuming audio.
  if (d.meta?.kind === "video" || YT.test(d.url || "")) {
    mountVideo($("#readerAudio"), d.url || d.audio_url);
  } else {
    mountAudio($("#readerAudio"), d.audio_url);
  }

  const p = d.profile || {};
  // Coverage is the number that decides whether a text is worth your time:
  // not how long it is, but how much of it you can already handle.
  $("#readerProfile").textContent = p.coverage != null
    ? `Знакомых слов: ${Math.round(p.coverage * 100)}% · ${p.unique} разных слов`
    : "";

  const hard = new Set((p.hard_words || []).map(w => w.toLowerCase()));
  // Wrap each word so it can be clicked; non-words pass through untouched.
  $("#readerBody").innerHTML = esc(d.body).replace(
    /[A-Za-zÀ-ÿŠŽšžÕÄÖÜõäöü]+/g,
    m => `<w class="${hard.has(m.toLowerCase()) ? "hard" : ""}">${m}</w>`);
  $("#wordCard").hidden = true;
}

$("#xlBtn").onclick = async () => {
  const picked = (window.getSelection?.().toString() || "").trim();
  const out = $("#xlOut"), hint = $("#xlHint");
  if (!picked) { hint.textContent = "выдели предложение в тексте"; out.hidden = true; return; }
  hint.textContent = "перевожу…";
  out.hidden = true;
  try {
    const r = await (await api("/api/translate", {text: picked.slice(0, 1200)})).json();
    if (!r.ok) { hint.textContent = r.detail || "не вышло"; return; }
    out.textContent = r.text;
    out.hidden = false;
    hint.textContent = "TartuNLP";
  } catch (err) {
    hint.textContent = err.message;
  }
};


// The reader supplies the sentence around the word; the vocabulary list, which
// has no sentence, passes nothing and the card behaves identically otherwise.
$("#readerBody").addEventListener("click", e => {
  if (e.target.tagName !== "W") return;
  showWordCard(e.target.textContent, $("#wordCard"), w =>
    (($("#readerBody").textContent.match(new RegExp(
      "[^.!?]*" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "[^.!?]*[.!?]"))
      || [])[0] || "").trim() || null);
});
