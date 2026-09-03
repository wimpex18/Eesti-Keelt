/* Lugemine: the shelf, opening a text, and looking a word up inside it. */

import {emptyState, skeleton, uiIcon} from "./chrome.js";
import {$, api, esc} from "./core.js";
import {YT, mountAudio, mountVideo} from "./media.js";
import {showWordCard} from "./vocab.js";

let libShown = 0;


async function loadLibrary(append = false) {
  const choice = $("#readLevel").value;
  const list = $("#libList");
  // The shape of the answer while it is fetched, rather than a blank panel.
  if (!append) { list.innerHTML = skeleton(5); libShown = 0; }
  $("#reader").hidden = true;
  $("#libList").hidden = false;

  /* A failed request must say what the server said. Reading `.items` off an
     error payload threw, and the catch below printed the TypeError itself:
     the learner was shown "Viga: Cannot read properties of undefined (reading
     'length')". The drill and the writing check both surface `detail`
     correctly; this path was the odd one out. */
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
      // With nothing marked known, every text scores 0 % — true, and it reads
      // as "you know nothing" rather than "we have not measured yet". Suppress
      // the number until there is a vocabulary to measure against, and say why.
      measured = d.known_words > 0;
      note = measured
        ? `${d.known_words} слов знакомо`
        : "Слова ещё не отмечены — показаны самые простые тексты.";
      /* Counted by the endpoint on purpose -- its comment says a text dropped
         silently here is what produced "0 teksti · 411 слов знакомо", a
         contradiction with no explanation. The count existed; the page threw
         it away, which restores exactly the contradiction it was added to
         prevent. */
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

    /* The number said `items.length`, which is the page size and not the
       library size: 80 came back against 349 indexed, so the screen read "80
       текстов" and the other 269 could not be reached at all. `total` comes
       from the server counting the same filter it selected on. */
    $("#libCount").textContent = total != null && total > libShown
      ? `показано ${libShown} из ${total}${note ? " · " + note : ""}`
      : `${libShown} текстов${note ? " · " + note : ""}`;
    $("#libMore").hidden = !more;
    if (!items.length && !append) {
      list.innerHTML = emptyState({
        icon: "inbox",
        title: "Текстов нет",
        note: `Библиотека ещё не наполнена. Её собирают
          <code>cli harvest-reading</code> и <code>cli harvest-news</code>.`,
      });
      return;
    }
    for (const it of items) {
      const el = document.createElement("div");
      el.className = "lib-item" + (it.external ? " external" : "");
      // Coverage only appears where it was actually computed. Showing "0 %"
      // for a list that never measured it would read as "you know nothing".
      const cover = (measured && it.coverage !== undefined)
        ? ` · <b>${Math.round(it.coverage * 100)}%</b> знакомо` : "";
      const size = it.words !== undefined ? `${it.words} слов`
        : (it.total !== undefined ? `${it.total} слов` : "");
      /* HARNO's own tasks are indexed, never copied -- their `body` is empty
         by licence and a test asserts it. The list rendered them like any
         other text, so "Lugemine 1 (A2-tase)" advertised **0 слов** and opened
         a reader on nothing. The API has said `external` and carried the url
         since it was written; the page had never read either. */
      if (it.external) {
        el.innerHTML = `<h4>${esc(it.title)}</h4>
          <span class="lib-meta">HARNO · задание на сайте экзамена ↗</span>`;
        el.onclick = () => window.open(it.url, "_blank", "noopener");
      } else {
        el.innerHTML = `<h4>${esc(it.title)}</h4>
          <span class="lib-meta">${it.band ? esc(it.band) + " · " : ""}${size}${
            it.audio_url ? " · " + uiIcon("note", "inline-ico") : ""}${cover}</span>`;
        el.onclick = () => openItem(it.id);
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
