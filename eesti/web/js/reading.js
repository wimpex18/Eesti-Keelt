/* Lugemine: the shelf, opening a text, and looking a word up inside it. */

import {actsAsButton, emptyState, retryableError, skeleton, uiIcon} from "./chrome.js";
import {$, api, esc, langOf, ruCount} from "./core.js";
import {YT, mountAudio, mountVideo} from "./media.js";
import {showWordCard} from "./vocab.js";

let libShown = 0, libRequest = 0;
const WORDS = ["слово", "слова", "слов"], TEXTS = ["текст", "текста", "текстов"];


export async function loadLibrary(append = false) {
  const choice = $("#readLevel").value;
  const list = $("#libList");
  /* The list loads when the tab opens and again on `Näita`; only the latest request
     may paint, or a slow first answer lands on top of the filter chosen after it. */
  const mine = ++libRequest;
  // The shape of the answer while it is fetched, rather than a blank panel.
  if (!append) { list.innerHTML = skeleton(5); libShown = 0; }
  $("#reader").hidden = true;
  $("#libList").hidden = false;

  try {
    let items, note = "", why = "", fallback = false;
    let total = null, more = false;
    if (choice === "soovitatud") {
      const d = await (await api("/api/reading/next?limit=25", null, "GET")).json();
      items = d.items;
      /* Coverage counts words the learner knows *or* that sit at A1–A2, so it is
         meaningful before any word is marked known. */
      note = d.known_words > 0
        ? `${ruCount(d.known_words, WORDS)} знакомо`
        : "слова ещё не отмечены";
      /* The endpoint counts texts it could not score; showing the count explains why
         "texts known" and the list size can disagree. */
      if (d.unmeasurable)
        note += ` · ${d.unmeasurable} без разбора слов`;
      // How the list was chosen, and whether even the first text is above the learner.
      why = d.note || "";
      fallback = !!d.fallback;
    } else {
      const q = new URLSearchParams({
        skill: "lugemine", limit: "80", offset: String(libShown)});
      if (choice) q.set("band", choice);
      const d = await (await api("/api/library?" + q, null, "GET")).json();
      items = d.items;
      total = d.total;
      more = libShown + items.length < d.total;
    }
    if (mine !== libRequest) return;
    libShown += items.length;

    /* `total` is the server's count for the same filter; `items.length` is only the
       page size. */
    $("#libCount").textContent = total != null && total > libShown
      ? `показано ${libShown} из ${total}${note ? " · " + note : ""}`
      : `${ruCount(libShown, TEXTS)}${note ? " · " + note : ""}`;
    $("#libNote").textContent = why;
    $("#libNote").hidden = !why;
    // Nothing clears the floor: the note is a caution, so it looks like one.
    $("#libNote").className = fallback ? "banner" : "hint";
    $("#libMore").hidden = !more;
    if (!items.length && !append) {
      /* A band that happens to be empty is not an empty library: say which it is,
         and give the way back to the whole shelf. */
      const band = choice && choice !== "soovitatud";
      list.innerHTML = band
        ? emptyState({
            icon: "inbox",
            title: "В этой подборке текстов нет",
            note: "Другие подборки могут быть не пусты.",
            action: `<button class="ghost" id="libAll" lang="et">Kõik tekstid <span class="ru" lang="ru">все тексты</span></button>`,
          })
        : emptyState({
            icon: "inbox",
            title: "Текстов нет",
            note: "Тексты появятся здесь, когда библиотеку добавят в приложение.",
          });
      $("#libAll")?.addEventListener("click", () => {
        $("#readLevel").value = "";
        loadLibrary(false);
      });
      return;
    }
    // The skeleton stood in for this page of rows; they replace it, not follow it.
    if (!append) list.innerHTML = "";
    for (const it of items) {
      // An external row goes somewhere else, so it is a real link.
      const el = document.createElement(it.external ? "a" : "div");
      el.className = "lib-item" + (it.external ? " external" : "");
      // Coverage appears only where it was computed (the recommended list), so a
      // shelf row never shows "0 %". It is words within reach, not words known.
      const cover = it.coverage !== undefined
        ? ` · <b>${Math.round(it.coverage * 100)}%</b> посильных слов` : "";
      const n = it.words ?? it.total;
      const size = n !== undefined ? ruCount(n, WORDS) : "";
      /* HARNO's tasks are indexed, never copied: `body` is empty by licence. They
         open the official page (`external`, `url`) instead of an empty reader. */
      if (it.external) {
        el.innerHTML = `<h4 lang="${langOf(it.title)}">${esc(it.title)}</h4>
          <span class="lib-meta">HARNO · задание на сайте экзамена ↗</span>`;
        el.href = it.url;
        el.target = "_blank";
        el.rel = "noopener";
      } else {
        el.innerHTML = `<h4 lang="${langOf(it.title)}">${esc(it.title)}</h4>
          <span class="lib-meta">${it.band ? `<span lang="et">${esc(it.band)}</span> · ` : ""}${size}${
            it.audio_url ? " · " + uiIcon("note", "inline-ico") : ""}${cover}</span>`;
        actsAsButton(el, () => openItem(it.id));
      }
      list.appendChild(el);
    }
  } catch (e) {
    if (mine !== libRequest) return;
    list.replaceChildren(retryableError(e.message, () => loadLibrary(append)));
  }
  if (pendingItem && mine === libRequest) {
    const id = pendingItem;
    pendingItem = null;
    openItem(id);
  }
}


/* Open one text from elsewhere (the Reegel page). The tab's first load resets
   the reader to the list, so before that load the text waits for it. */
let pendingItem = null;
export function showItem(id) {
  if (libRequest) openItem(id);
  else pendingItem = id;
}

$("#loadLib").onclick = () => loadLibrary(false);

$("#libMoreBtn").onclick = () => loadLibrary(true);

$("#backToLib").onclick = () => { $("#reader").hidden = true; $("#libList").hidden = false; };


async function openItem(id) {
  /* The reader is shown only once it has something to show: a title and a body,
     or the error with its retry. Showing it first would flash an empty reader. */
  const show = () => { $("#libList").hidden = true; $("#reader").hidden = false; };
  let d;
  try {
    d = await (await api("/api/library/" + id, null, "GET")).json();
  } catch (e) {
    $("#readerTitle").textContent = "Текст не открылся";
    $("#readerMeta").textContent = e.message;
    $("#readerAudio").replaceChildren();
    $("#readerProfile").textContent = "";
    $("#readerBody").replaceChildren(retryableError(e.message, () => openItem(id)));
    show();
    return;
  }
  $("#readerTitle").textContent = d.title;
  /* Where the text comes from, as a name and a way back to the original. The
     licence terms live in the sources footer and `/api/sources`; a line of
     licence prose over every text is noise for the one learner reading it. */
  $("#readerMeta").innerHTML = `<span lang="et">Allikas</span> ${d.url
    ? `<a href="${esc(d.url)}" target="_blank" rel="noopener" lang="${langOf(d.source)}">${esc(d.source)}</a>`
    : `<span lang="${langOf(d.source)}">${esc(d.source)}</span>`}`;
  // An item is a text, a recording or a film; the reader shows whichever it
  // has rather than assuming audio.
  if (d.meta?.kind === "video" || YT.test(d.url || "")) {
    mountVideo($("#readerAudio"), d.url || d.audio_url);
  } else if ((d.meta?.audio || []).length > 1) {
    // An exam listening task is several short recordings, one per question,
    // numbered the way the task numbers them.
    const host = $("#readerAudio");
    host.replaceChildren();
    d.meta.audio.forEach((url, i) => {
      const row = document.createElement("div");
      row.className = "clip";
      row.innerHTML = `<span class="lib-meta">${i + 1}</span>`;
      const slot = document.createElement("div");
      row.append(slot);
      host.append(row);
      mountAudio(slot, url);
    });
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
  // Wrap each word so it can be clicked; non-words pass through untouched. One
  // word at a time is a tab stop (arrows move it), so a long text is one stop
  // and a screen reader still reads it as prose.
  $("#readerBody").innerHTML = esc(d.body).replace(
    /[A-Za-zÀ-ÿŠŽšžÕÄÖÜõäöü]+/g,
    m => `<w tabindex="-1" class="${hard.has(m.toLowerCase()) ? "hard" : ""}">${m}</w>`);
  const first = $("#readerBody w");
  if (first) first.tabIndex = 0;
  $("#wordCard").hidden = true;
  show();
  // The questions are a separate request: a text opens whether or not it has any.
  loadQuiz(id);
}

/* Questions about the text (ADR-0004): a model wrote them, the text keys them,
   and this page never sees an answer until it has sent the learner's own. */
let quizItem = null;
/* Which request the panel is showing. Opening a second text before the first
   answered used to paint the first one's questions under the second one's id,
   and the answer was then graded against whatever question shared that index. */
let quizRequest = 0;

function paintQuiz(d, token) {
  if (token !== quizRequest) return;        // a text the learner has left
  const list = $("#quizList"), hint = $("#quizHint"), btn = $("#quizBtn");
  list.replaceChildren();
  // Offered until it has been tried: a text whose proposals never verify would
  // otherwise cost a model call for every tap.
  btn.hidden = !d.can_make || !!d.questions.length || !!d.tried;
  hint.textContent = d.questions.length
    ? `${d.questions.length} · ответ словами текста`
    : (d.note || (d.can_make ? "" : "текст слишком короткий"));
  for (const q of d.questions) {
    const box = document.createElement("div");
    box.className = "quiz-item";
    box.innerHTML = `<p lang="et">${esc(q.question)}</p>
      <div class="row">
        <input type="text" lang="et" data-idx="${q.idx}"
               autocapitalize="off" autocomplete="off"
               placeholder="vastus tekstist">
        <button class="ghost" data-check="${q.idx}" lang="et">Kontrolli
          <span class="ru" lang="ru">проверить</span></button>
      </div>
      <div class="quiz-verdict" hidden></div>`;
    list.append(box);
  }
}

async function loadQuiz(id) {
  const token = ++quizRequest;
  quizItem = id;
  $("#quizList").replaceChildren();
  $("#quizHint").textContent = "";
  try {
    paintQuiz(await (await api(
      `/api/read/questions/${encodeURIComponent(id)}`)).json(), token);
  } catch {
    if (token === quizRequest) $("#quizHint").textContent = "";
  }
}

$("#quizBtn").onclick = async () => {
  if (!quizItem) return;
  const token = quizRequest, asked = quizItem;
  const btn = $("#quizBtn");
  btn.disabled = true;
  $("#quizHint").textContent = "составляю вопросы…";
  try {
    paintQuiz(await (await api(
      `/api/read/questions/${encodeURIComponent(asked)}`, {})).json(), token);
  } catch (err) {
    if (token === quizRequest) $("#quizHint").textContent = err.message;
  } finally {
    btn.disabled = false;
  }
};

$("#quizList").addEventListener("click", async e => {
  const btn = e.target.closest("button[data-check]");
  if (!btn || !quizItem) return;
  // The id the question was drawn for, not whatever is open now.
  const asked = quizItem;
  const box = btn.closest(".quiz-item");
  const field = box.querySelector("input");
  const out = box.querySelector(".quiz-verdict");
  btn.disabled = true;
  try {
    const r = await (await api("/api/read/answer", {
      item_id: asked, idx: Number(btn.dataset.check), answer: field.value,
    })).json();
    out.hidden = false;
    out.className = `quiz-verdict ${r.correct ? "right" : "wrong"}`;
    out.textContent = r.why_ru;
    field.disabled = true;
  } catch (err) {
    out.hidden = false;
    out.className = "quiz-verdict wrong";
    out.textContent = err.message;
    btn.disabled = false;
  }
});


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
/* The roving word: the one tab stop in the text. */
function rove(to) {
  $("#readerBody").querySelectorAll('w[tabindex="0"]').forEach(w => { w.tabIndex = -1; });
  to.tabIndex = 0;
  to.focus();
}

$("#readerBody").addEventListener("click", e => {
  if (e.target.tagName !== "W") return;
  rove(e.target);
  showWordCard(e.target.textContent, $("#wordCard"), w =>
    (($("#readerBody").textContent.match(new RegExp(
      "[^.!?]*" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "[^.!?]*[.!?]"))
      || [])[0] || "").trim() || null, e.target);
});
$("#readerBody").addEventListener("keydown", e => {
  if (e.target.tagName !== "W") return;
  if (["Enter", " "].includes(e.key)) {
    e.preventDefault();
    e.target.click();
    return;
  }
  const words = [...$("#readerBody").querySelectorAll("w")];
  const at = words.indexOf(e.target);
  const to = {ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: words.length - 1}[e.key];
  if (to === undefined || !words[to]) return;
  e.preventDefault();
  rove(words[to]);
});
