/* Sõnavara: the ladder, and the word card that both this and the reader open. */

import {$, api, esc} from "./core.js";
import {skeleton, uiIcon} from "./chrome.js";
import {refreshDueBadge} from "./review.js";

/* A form's name as the exam says it, with its Russian gloss beside it. */
const tagLabel = t => t.ru
  ? `${esc(t.name)} <i class="ru">${esc(t.ru)}</i>` : esc(t.name);


export async function showWordCard(word, card, contextFor) {
  card.hidden = false;
  card.innerHTML = skeleton(1);
  const d = await (await api("/api/lookup/" + encodeURIComponent(word), null, "GET")).json();
  /* `found:false` covers two answers: the word is absent from the lexicon, or the
     lookup could not run (`error`, e.g. the forms table was never exported). The
     second must not read as "not found". */
  if (!d.found) {
    card.innerHTML = d.error
      ? `<span class="hint">${esc(d.word)} — разбор недоступен.
           <br>Словарь форм ещё не собран на этом сервере
           (<code>${esc(d.error)}</code>).</span>`
      : `<span class="hint">${esc(d.word)} — не найдено</span>`;
    return;
  }
  /* Two actions on a word: "Add to review" queues the grammar pattern behind it;
     "I know this" records the lemma as known. Known words drive the reading
     order, dictation order, the vocabulary line of the readiness verdict and the
     "N of the first 4000" counter. */
  // The anchor late-arriving enrichment inserts before, so the meaning sits with
  // the word rather than below the actions.
  const mineBtn = `<div id="cardExtra"></div>
    <div class="row" style="margin-top:var(--s2)">
      <button class="ghost" id="mineBtn">${uiIcon("plus")}Kordamisse</button>
      <button class="ghost" id="knowBtn">${uiIcon("check")}Tean seda sõna</button>
      <button class="ghost" id="skipBtn" title="Не тратить время на это слово">${uiIcon("ban")}Pole vaja</button></div>
    <div class="hint">«Tean» — выучено, идёт в счёт. «Pole vaja» — не предлагать,
      в счёт не идёт.</div>
    <div id="mineNote"></div>`;
  card.innerHTML = d.analyses.slice(0, 2).map(a => `
    <div class="lemma">${esc(a.lemma)}${a.level ? ` <span class="hint">${esc(a.level)}</span>` : ""}</div>
    <div class="tags">${a.tags.map(tagLabel).join(" · ")}</div>
    ${a.object_case_contrast ? `<div class="pair">sihitis: <b>${esc(a.genitive)}</b> (omastav) /
      <b>${esc(a.partitive)}</b> (osastav)</div>` : ""}`).join("<hr style='border:0;border-top:1px solid var(--line);margin:9px 0'>") + mineBtn;

  // Mining the word queues the GRAMMAR pattern behind it, with the sentence as
  // context — not a translation. Refusals explain themselves.
  card.querySelector("#mineBtn").onclick = async e => {
    e.target.disabled = true;
    const sentence = contextFor ? contextFor(word) : null;
    const r = await (await api("/api/mine", {word, context: sentence || null})).json();
    const note = card.querySelector("#mineNote");
    note.className = "mine-note" + (r.queued ? "" : " no");
    note.textContent = r.reason;
    if (r.queued) refreshDueBadge();
    // A refusal is often temporary ("meaning not known yet") and the meaning arrives
    // moments later from enrichment, so the button is re-enabled.
    else e.target.disabled = false;
  };

  /* Rection and inflection type, from Sõnaveeb.

     Fetched separately and appended when it arrives: the card is usable before any
     third-party call returns. */
  // The lemma, not the surface form: Sõnaveeb is a dictionary and does not know
  // inflected forms.
  const enrichLemma = d.analyses[0]?.lemma || word;
  fetch("/api/enrich/" + encodeURIComponent(enrichLemma))
    .then(r => r.json())
    .then(x => {
      if (!x.found) return;
      const bits = [];
      if (x.governs?.length) bits.push(`rektsioon: <b>${esc(x.governs.join(", "))}</b>`);
      if (x.inflection_type) bits.push(`muuttüüp <b>${esc(String(x.inflection_type))}</b>`);
      // The gloss, in the language the app explains things in.
      if (x.russian?.length)
        bits.push(`<span class="gloss">${esc(x.russian.join(", "))}</span>`);
      // EKI's Estonian-Russian dictionary is CC BY 4.0, so its Russian is credited —
      // only when it is EKI's, not Sõnaveeb's gloss in the same slot.
      if (x.russian_source === "ekilex")
        bits.push(`<span class="attrib">allikas: Ekilex (EKI) · CC BY 4.0</span>`);
      if (x.russian_source === "eki-evs")
        bits.push(`<span class="attrib">allikas: EKI eesti-vene sõnaraamat · CC BY 4.0</span>`);
      if (x.russian_source === "eki-har")
        bits.push(`<span class="attrib">allikas: EKI haridussõnastik · CC BY 4.0</span>`);
      /* The definition and the examples, from EKI's põhisõnavara sõnastik. */
      const meaning = [];
      if (x.definition)
        meaning.push(`<div class="def">${esc(x.definition)}</div>`);
      if (x.examples?.length)
        meaning.push(`<ul class="examples">` +
          x.examples.map(e => `<li>${esc(e)}</li>`).join("") + `</ul>`);
      /* Whose words those are.

         EKI publish the põhisõnavara sõnastik under CC BY 4.0: the material may be
         presented any way needed provided the reference to EKI is retained and changes
         are described. The card renders their text verbatim, so the credit goes here —
         the licence follows the text.

         The label is Estonian (a label, per the language rule), not an explanation. */
      if (x.definition_source === "eki-psv")
        meaning.push(`<div class="attrib">allikas: EKI põhisõnavara sõnastik` +
          ` 2014 · CC BY 4.0</div>`);
      if (x.definition_source === "ekilex")
        meaning.push(`<div class="attrib">allikas: Ekilex (EKI) · CC BY 4.0</div>`);
      if (x.definition_source === "eki-vsl")
        meaning.push(`<div class="attrib">allikas: EKI võõrsõnade leksikon · CC BY 4.0</div>`);
      if (x.definition_source === "eki-ekss")
        meaning.push(`<div class="attrib">allikas: EKI eesti keele seletav sõnaraamat · CC BY 4.0</div>`);
      /* The fuller, native-level wording beside PSV's learner definition. Folded,
         because the learner-level one is meant to be read first. Credited by source:
         Sõnaveeb (EKI's live database) or EKI's files. */
      if (x.full_definition) {
        const who = {
          "sonapi": "Sõnaveeb (EKI) · CC BY 4.0",
          "ekilex": "Ekilex (EKI) · CC BY 4.0",
          "eki-vsl": "EKI võõrsõnade leksikon · CC BY 4.0",
          "eki-ekss": "EKI eesti keele seletav sõnaraamat · CC BY 4.0",
        }[x.full_definition_source] || "";
        meaning.push(`<details class="fuller"><summary>täpsem seletus</summary>` +
          `<div class="def">${esc(x.full_definition)}</div>` +
          (who ? `<div class="attrib">allikas: ${esc(who)}</div>` : "") + `</details>`);
      }
      const slot = card.querySelector("#cardExtra");
      if (meaning.length) {
        const box = document.createElement("div");
        box.className = "pair meaning";
        box.innerHTML = meaning.join("");
        slot.append(box);
      }
      if (bits.length) {
        const extra = document.createElement("div");
        extra.className = "pair";
        extra.innerHTML = bits.join(" · ");
        slot.append(extra);
      }
      // Out to the real dictionary. The paradigm, audio and the rest live in
      // Sõnaveeb, which this app does not reimplement.
      if (x.sonaveeb) {
        const out = document.createElement("div");
        out.className = "hint";
        out.style.marginTop = "6px";
        out.innerHTML = `<a href="${esc(x.sonaveeb)}" target="_blank" rel="noopener">`
          + `Sõnaveebis →</a>`;
        slot.append(out);
      }
    })
    .catch(() => {});

  // Marking a word known is an explicit act, never inferred from having read it:
  // meeting a word is not knowing it.
  /* "Not worth my time": rare but correctly listed words (`riigivisiit`,
     `seinamaaling`) would otherwise return on every page and keep the "still to
     learn" count meaningless.

     Stored as `eiran`, not `tean`: "I know this" and "not for me" are different
     facts, and the known-word count orders the reading list and feeds the verdict. */
  card.querySelector("#skipBtn").onclick = async e => {
    e.target.disabled = true;
    const lemma = d.analyses[0]?.lemma || word;
    const note = card.querySelector("#mineNote");
    try {
      await api("/api/vocab/known", {lemmas: [lemma], status: "ignore"});
      e.target.innerHTML = uiIcon("ban") + "Jäetud";
      note.className = "mine-note";
      note.textContent = `«${lemma}» больше не будет предлагаться.`;
    } catch (err) {
      note.className = "mine-note no";
      note.textContent = err.message;
      e.target.disabled = false;
    }
  };

  card.querySelector("#knowBtn").onclick = async e => {
    e.target.disabled = true;
    const lemma = d.analyses[0]?.lemma || word;
    const note = card.querySelector("#mineNote");
    try {
      await api("/api/vocab/known", {lemmas: [lemma]});
      e.target.innerHTML = uiIcon("check") + "Teada";
      note.className = "mine-note";
      note.textContent = `«${lemma}» теперь известно — влияет на подбор текстов.`;
    } catch (err) {
      note.className = "mine-note no";
      note.textContent = err.message;
      e.target.disabled = false;
    }
  };
}

let vocOffset = 0;


function vocRow(it) {
  const pair = it.genitive
    ? `<span class="pair">${esc(it.genitive)} / ${esc(it.partitive)}</span>` : "";
  const ru = it.russian ? `<span class="gloss">${esc(it.russian)}</span>` : "";
  const settled = it.status >= 5;
  return `<button class="vocword${settled ? " settled" : ""}" data-word="${esc(it.word)}">
    <span class="w">${esc(it.word)}</span>
    ${it.level ? `<span class="lv" data-level="${esc(it.level)}">${esc(it.level)}</span>` : ""}
    ${pair}${ru}
    ${settled ? `<span class="lv">${esc(it.status_name)}</span>` : ""}
  </button>`;
}


export async function loadVocab(append) {
  const out = $("#vocOut"), more = $("#vocMore");
  const q = new URLSearchParams();
  const lvl = $("#vocLevel").value, pos = $("#vocPos").value, st = $("#vocStatus").value;
  if (lvl) q.set("level", lvl);
  if (pos) q.set("pos", pos);
  if (st) q.set("status", st);
  vocOffset = append ? vocOffset + 60 : 0;
  q.set("limit", "60");
  q.set("offset", String(vocOffset));
  if (!append) out.innerHTML = skeleton(8, "tile");
  try {
    const d = await (await api("/api/vocab?" + q, null, "GET")).json();
    if (!d.items.length && !append) {
      // An empty result is a real answer here, not a failure: filtering B2
      // verbs down to "known" legitimately finds nothing early on.
      out.innerHTML = `<p class="hint">С этим фильтром слов нет.</p>`;
      more.hidden = true;
      return;
    }
    const html = d.items.map(vocRow).join("");
    if (append) {
      // Into the grid, not after it: appending to `#vocOut` would start a
      // second column set that does not line up with the first.
      const grid = out.querySelector(".vocgrid");
      (grid || out).insertAdjacentHTML("beforeend", html);
    } else {
      out.innerHTML = `<div class="vocgrid">${html}</div>`;
    }
    more.hidden = !d.more;
  } catch (err) {
    out.innerHTML = `<p class="mine-note no">${esc(err.message)}</p>`;
    more.hidden = true;
  }
}


$("#vocBtn").onclick = () => loadVocab(false);

$("#vocMoreBtn").onclick = () => loadVocab(true);

$("#vocOut").addEventListener("click", e => {
  const b = e.target.closest(".vocword");
  if (!b) return;
  let card = $("#vocCard");
  if (!card) {
    card = document.createElement("div");
    card.id = "vocCard";
    $("#tab-sonad").append(card);
  }
  showWordCard(b.dataset.word, card, null);
});
