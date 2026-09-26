/* Sõnavara: the ladder, and the word card that both this and the reader open. */

import {$, api, esc} from "./core.js";
import {icon} from "./icons.js";
import {navIcon, retryableError, skeleton, uiIcon} from "./chrome.js";
import {sayable, speakWord, withSlots} from "./media.js";
import {refreshDueBadge} from "./review.js";

/* A form's name as the exam says it, with its Russian gloss beside it. */
const tagLabel = t => t.ru
  ? `<span lang="et">${esc(t.name)} <i class="ru" lang="ru">${esc(t.ru)}</i></span>` : esc(t.name);


/* EVS's example phrases, each Estonian with EKI's Russian under it. An open
   slot (`{kelle}`) is set in italics: the phrase leaves it for the learner to
   fill. Three show; the rest (all of them — `käima` has
   144) are folded into a scrolling list, since the card is a reminder. */
const SHOWN_PHRASES = 3;

function phraseItem(p) {
  // A phrase with an open slot is not a sentence anyone says; it gets no voice.
  const say = p.et.includes("{") ? "" :
    `<button class="iconbtn phrase-say" type="button" data-say="${esc(sayable(p.et))}"
       title="Kuula — прослушать" aria-label="Kuula — прослушать">${navIcon("speaker-high")}</button>`;
  return `<li>${say}<span lang="et">${withSlots(p.et)}</span>` +
    `<span class="gloss" lang="ru">${withSlots(p.ru)}</span></li>`;
}

/* Idioms (väljendid) are folded whole: an idiom is worth knowing once the word
   is, and it does not mean what its words say. */
function phrasesHtml(phrases, idioms = []) {
  const head = phrases.slice(0, SHOWN_PHRASES), rest = phrases.slice(SHOWN_PHRASES);
  let html = "";
  if (head.length) html += `<h4 lang="et">Näited <i class="ru" lang="ru">с переводом</i></h4>` +
    `<ul class="phrase-list">${head.map(phraseItem).join("")}</ul>`;
  if (rest.length) {
    html += `<details class="fuller"><summary lang="et">veel ${rest.length} näidet</summary>` +
      `<ul class="phrase-list">${rest.map(phraseItem).join("")}</ul></details>`;
  }
  if (idioms.length) {
    html += `<details class="fuller"><summary lang="et">Väljendid (${idioms.length})
        <i class="ru" lang="ru">выражения</i></summary>` +
      `<ul class="phrase-list">${idioms.map(phraseItem).join("")}</ul></details>`;
  }
  html += `<div class="hint phrase-note" hidden></div>` +
    `<div class="attrib" lang="et">näited: EKI eesti-vene sõnaraamat · CC BY 4.0</div>`;
  return html;
}


/* One reading of the word: lemma, level, what the form is. In a sentence, the
   reading the sentence uses is marked and its form comes first; a word with no
   form to name (`kus`, `aga`) shows its part of speech instead. */
function analysisHtml(a, chosen = false) {
  const tags = a.tags.length
    ? a.tags.map(t => t.in_context ? `<b>${tagLabel(t)}</b>` : tagLabel(t)).join(" · ")
    : a.pos_name ? `<span lang="et">${esc(a.pos_name)} <i class="ru" lang="ru">${esc(a.pos_ru)}</i></span>` : "";
  return `
    <div class="lemma" lang="et">${esc(a.lemma)}${a.level ? ` <span class="hint">${esc(a.level)}</span>` : ""}</div>
    ${chosen ? `<div class="in-context" lang="et">selles lauses <i class="ru" lang="ru">в этом предложении</i></div>` : ""}
    ${tags ? `<div class="tags" lang="et">${tags}</div>` : ""}
    ${a.object_case_contrast ? `<div class="pair" lang="et">sihitis: <b>${esc(a.genitive)}</b> (omastav) /
      <b>${esc(a.partitive)}</b> (osastav)</div>` : ""}`;
}

async function fillWordCard(word, card, contextFor, retry) {
  card.hidden = false;
  card.innerHTML = skeleton(1);
  /* Which word the card is showing now. A lookup or enrichment that returns after
     the learner has tapped another word belongs to the old one and is dropped,
     instead of landing its meaning under the new word. */
  const shown = String(Math.random());
  card.dataset.shown = shown;
  const stale = () => card.dataset.shown !== shown;
  // The sentence the word was met in, so the card can say which reading it is.
  const sentence = contextFor ? contextFor(word) : null;
  const query = sentence ? "?sentence=" + encodeURIComponent(sentence.slice(0, 400)) : "";
  let d;
  try {
    d = await (await api("/api/lookup/" + encodeURIComponent(word) + query, null, "GET")).json();
  } catch (e) {
    if (stale()) return;
    card.replaceChildren(retryableError(e.message, retry));
    return;
  }
  if (stale()) return;
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
      <button class="ghost" id="mineBtn" lang="et">${uiIcon("plus")}Kordamisse</button>
      <button class="ghost" id="knowBtn" lang="et">${uiIcon("check")}Tean seda sõna</button>
      <button class="ghost" id="skipBtn" title="Не тратить время на это слово">${uiIcon("ban")}<span lang="et">Pole vaja</span></button></div>
    <div class="hint">«<span lang="et">Tean</span>» — выучено, идёт в счёт. «<span lang="et">Pole vaja</span>» — не предлагать,
      в счёт не идёт.</div>
    <div id="mineNote"></div>`;
  /* With the sentence's reading known, it is the card; the other readings are
     one quiet line, since the sentence has already chosen. */
  const others = d.in_context ? d.analyses.slice(1) : [];
  const otherName = a => a.tags[0] ? `${a.lemma} (${a.tags[0].name})` : a.lemma;
  const otherLine = others.length
    ? `<div class="hint other-readings" lang="et">muud võimalused:
        ${esc(others.map(otherName).join(", "))}</div>` : "";
  // "In this sentence" only where there was a choice to make.
  const ambiguous = d.analyses.length > 1 || d.analyses[0].tags.length > 1;
  const readings = d.in_context
    ? analysisHtml(d.analyses[0], ambiguous) + otherLine
    : d.analyses.slice(0, 2).map(a => analysisHtml(a))
        .join("<hr style='border:0;border-top:1px solid var(--line);margin:9px 0'>");
  card.innerHTML = readings + mineBtn;

  // Mining the word queues the GRAMMAR pattern behind it, with the sentence as
  // context — not a translation. Refusals explain themselves.
  card.querySelector("#mineBtn").onclick = async e => {
    e.target.disabled = true;
    const note = card.querySelector("#mineNote");
    try {
      const r = await (await api("/api/mine", {word, context: sentence || null})).json();
      note.className = "mine-note" + (r.queued ? "" : " no");
      note.textContent = r.reason;
      if (r.queued) refreshDueBadge();
      // A refusal is often temporary ("meaning not known yet") and the meaning arrives
      // moments later from enrichment, so the button is re-enabled.
      else e.target.disabled = false;
    } catch (err) {
      note.className = "mine-note no";
      note.textContent = err.message;
      e.target.disabled = false;
    }
  };

  /* Rection and inflection type, from Sõnaveeb.

     Fetched separately and appended when it arrives: the card is usable before any
     third-party call returns. */
  // The lemma, not the surface form: Sõnaveeb is a dictionary and does not know
  // inflected forms.
  const enrichLemma = d.analyses[0]?.lemma || word;
  api("/api/enrich/" + encodeURIComponent(enrichLemma), null, "GET")
    .then(r => r.json())
    .then(x => {
      if (!x.found || stale()) return;
      const bits = [];
      if (x.governs?.length) bits.push(`<span lang="et">rektsioon: <b>${esc(x.governs.join(", "))}</b></span>`);
      if (x.inflection_type) bits.push(`<span lang="et">muuttüüp <b>${esc(String(x.inflection_type))}</b></span>`);
      // The gloss, in the language the app explains things in.
      if (x.russian?.length)
        bits.push(`<span class="gloss">${esc(x.russian.join(", "))}</span>`);
      // EKI's Estonian-Russian dictionary is CC BY 4.0, so its Russian is credited —
      // only when it is EKI's, not Sõnaveeb's gloss in the same slot.
      if (x.russian_source === "ekilex")
        bits.push(`<span class="attrib" lang="et">allikas: Ekilex (EKI) · CC BY 4.0</span>`);
      if (x.russian_source === "eki-evs")
        bits.push(`<span class="attrib" lang="et">allikas: EKI eesti-vene sõnaraamat · CC BY 4.0</span>`);
      if (x.russian_source === "eki-har")
        bits.push(`<span class="attrib" lang="et">allikas: EKI haridussõnastik · CC BY 4.0</span>`);
      /* The definition and the examples, from EKI's põhisõnavara sõnastik. */
      const meaning = [];
      if (x.definition)
        meaning.push(`<div class="def" lang="et">${esc(x.definition)}</div>`);
      if (x.examples?.length) {
        meaning.push(`<ul class="examples" lang="et">` +
          x.examples.map(e => `<li>${esc(e)}</li>`).join("") + `</ul>`);
        // Sentences are somebody's text, so they are credited where they differ
        // from the definition above (EKI's learner dictionary is credited there).
        const from = {
          "ekilex": "Ekilex (EKI) · CC BY 4.0",
          "sonapi": "Sõnaveeb (EKI) · CC BY 4.0",
        }[x.examples_source];
        if (from && x.examples_source !== x.definition_source)
          meaning.push(`<div class="attrib" lang="et">näited: ${esc(from)}</div>`);
      }
      /* Whose words those are.

         EKI publish the põhisõnavara sõnastik under CC BY 4.0: the material may be
         presented any way needed provided the reference to EKI is retained and changes
         are described. The card renders their text verbatim, so the credit goes here —
         the licence follows the text.

         The label is Estonian (a label, per the language rule), not an explanation. */
      if (x.definition_source === "eki-psv")
        meaning.push(`<div class="attrib" lang="et">allikas: EKI põhisõnavara sõnastik` +
          ` 2014 · CC BY 4.0</div>`);
      if (x.definition_source === "ekilex")
        meaning.push(`<div class="attrib" lang="et">allikas: Ekilex (EKI) · CC BY 4.0</div>`);
      if (x.definition_source === "eki-vsl")
        meaning.push(`<div class="attrib" lang="et">allikas: EKI võõrsõnade leksikon · CC BY 4.0</div>`);
      if (x.definition_source === "eki-ekss")
        meaning.push(`<div class="attrib" lang="et">allikas: EKI eesti keele seletav sõnaraamat · CC BY 4.0</div>`);
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
        meaning.push(`<details class="fuller"><summary lang="et">täpsem seletus</summary>` +
          `<div class="def" lang="et">${esc(x.full_definition)}</div>` +
          (who ? `<div class="attrib" lang="et">allikas: ${esc(who)}</div>` : "") + `</details>`);
      }
      const slot = card.querySelector("#cardExtra");
      if (meaning.length) {
        const box = document.createElement("div");
        box.className = "pair meaning";
        box.innerHTML = meaning.join("");
        slot.append(box);
      }
      if (x.phrases?.length || x.idioms?.length) {
        const box = document.createElement("div");
        box.className = "pair meaning phrases";
        box.innerHTML = phrasesHtml(x.phrases || [], x.idioms || []);
        box.addEventListener("click", e => {
          const b = e.target.closest("[data-say]");
          // A failed voice is said under the list, where a phone shows it.
          if (b) speakWord(b.dataset.say, msg => {
            const note = box.querySelector(".phrase-note");
            note.textContent = msg;
            note.hidden = false;
          });
        });
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
        out.innerHTML = `<a href="${esc(x.sonaveeb)}" target="_blank" rel="noopener" lang="et">`
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
      e.target.innerHTML = uiIcon("ban") + '<span lang="et">Jäetud</span>';
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
    ? `<span class="pair" lang="et">${esc(it.genitive)} / ${esc(it.partitive)}</span>` : "";
  const ru = it.russian ? `<span class="gloss">${esc(it.russian)}</span>` : "";
  const settled = it.status >= 5;
  return `<button class="vocword${settled ? " settled" : ""}" data-word="${esc(it.word)}">
    <span class="w" lang="et">${esc(it.word)}</span>
    ${it.level ? `<span class="lv" data-level="${esc(it.level)}">${esc(it.level)}</span>` : ""}
    ${pair}${ru}
    ${settled ? `<span class="lv" lang="et">${esc(it.status_name)}</span>` : ""}
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
  showWordCard(b.dataset.word, card, null, b);
});


/* A word card, with a way to put it away: it floats over the text or the list
   it was opened from, so it must never be the only way back to them. */
export async function showWordCard(word, card, contextFor, opener = document.activeElement) {
  const previous = card.querySelector(".card-content");
  if (previous) previous.dataset.shown = "";
  card.hidden = false;
  card.innerHTML = `<button class="iconbtn card-close" type="button"
    title="Sulge — закрыть" aria-label="Sulge — закрыть">${icon("x", {weight: "bold"})}</button>`;
  const body = document.createElement("div");
  body.className = "card-content";
  card.append(body);
  const close = card.querySelector(".card-close");
  close.onclick = () => {
    body.dataset.shown = "";
    card.hidden = true;
    if (opener instanceof HTMLElement && opener.isConnected && !card.contains(opener))
      opener.focus({preventScroll: true});
  };
  card.onkeydown = e => {
    if (e.key === "Escape") { e.preventDefault(); close.click(); }
  };
  close.focus({preventScroll: true});
  await fillWordCard(word, body, contextFor, () => showWordCard(word, card, contextFor, opener));
}
