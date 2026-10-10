/* Sõnastik and the word card: one entry per word, every part from a source
   that is named (`eesti/dictionary.py`).

   The card is a sheet: a bottom sheet on a phone that opens at half height and
   rises to full when the learner scrolls it or asks, an anchored dialog beside
   the word on a desktop. The word the learner tapped heads it as an interlinear
   word: its form name is Vabamorf's reading of it in its sentence, written by
   `interlinear()` from that reading alone; a reading Vabamorf leaves open shows
   the lemma and its meaning, and no form name.

   Two requests, as the card always made: the entry (`/api/dictionary/entry`,
   reference tables only, so the card is usable at once) and the live
   dictionary (`/api/enrich`), which may take seconds and fills in what EKI's
   current database adds. A model's English or Ukrainian draft is shown in the
   model block with its engine, and only until a source answers. */

import {$, api, esc, interlinear} from "./core.js";
import {icon} from "./icons.js";
import {emptyState, retryableError, skeleton, uiIcon} from "./chrome.js";
import {sayable, speakWord, withSlots} from "./media.js";
import {refreshDueBadge} from "./review.js";

/* ── Words the interface shows ──────────────────────────────────────── */

const LANG_RU = {en: "по-английски", uk: "по-украински"};
const ENGINE = {"claude-opus-5-5": "Claude Opus 5.5", "claude-haiku-5-5": "Claude Haiku 5.5"};
/* The learner's word status, as `vocab.STATUS_NAMES` names it, glossed. */
const STATUS_RU = {"õpin": "учу", "tean": "знаю", "eiran": "не нужно", "teadsin ammu": "знал раньше"};
/* Case names in the forms table, glossed once (`lookup._CASES_RU`). */
const CASE_RU = {nimetav: "именительный", omastav: "родительный", osastav: "частичный"};
/* What each source gave, as the entry's `sources` list names it. */
const WHAT_RU = {"vormid": "формы", "tase": "уровень", "tõlge": "перевод", "hääldus": "произношение",
  "seletus": "толкование", "näited": "примеры", "mudeli koostatud tõlge": "черновик модели",
  "mudel": "модель"};
const SHOWN_PHRASES = 3;

const sourceName = (e, id) => (e.sources.find(s => s.id === id) || {}).name || id;

/* A list of words, as EKI writes alternatives. */
const listed = words => esc(words.join(", "));

/* ── The head: the tapped form, or the headword ─────────────────────── */

/* The reading the card speaks for, and whether Vabamorf settled it.

   In a sentence, the reading Vabamorf's disambiguator marks; without one, the
   only reading there is. Several readings with none marked is an open
   question, and the form line then names no form. */
function chosenReading(look) {
  const analyses = look.analyses || [];
  if (look.in_context) {
    const a = analyses[0];
    const tags = a.tags.filter(t => t.in_context);
    return {analysis: a, tag: tags.length === 1 ? tags[0] : null, open: false};
  }
  const open = analyses.length > 1 || (analyses[0]?.tags.length || 0) > 1;
  return {analysis: analyses[0], tag: open ? null : analyses[0]?.tags[0] || null, open};
}

function headHtml(e, tapped, titleId) {
  const meaning = e.meanings.ru?.words.slice(0, 2).join(", ") || "";
  if (tapped) {
    // The form line's only source is this item, built from Vabamorf's reading.
    const item = tapped.tag
      ? {label: tapped.tag.name, form_ru: tapped.tag.ru, lemma: e.lemma}
      : {lemma: e.lemma, lemma_ru: meaning};
    return `<h2 class="dict-head tapped" id="${titleId}" tabindex="-1">${interlinear(tapped.form, item)}</h2>`;
  }
  return `<h2 class="dict-head" id="${titleId}" lang="et" tabindex="-1">${esc(e.lemma)}</h2>`;
}

/* EKI's recording where PSV has one; otherwise synthesis, and it says so. */
function sayButton(e) {
  const rec = e.recording;
  const label = rec ? "Kuula — запись EKI" : "Kuula — синтез речи";
  return `<span class="dict-say"><button class="iconbtn" type="button" data-say="${esc(rec ? rec.form : e.lemma)}"
      data-say-tag="${esc(rec ? rec.tag : "")}" aria-label="${label}" title="${label}">
      ${icon("speaker-high", {weight: "bold"})}</button>
    <span class="dict-voice" lang="ru" aria-hidden="true">${rec ? "запись EKI" : "синтез"}</span></span>`;
}

function metaHtml(e, tapped) {
  const bits = [];
  // The headword when the head is a form of it (*mulle* is *mina*).
  if (tapped && tapped.form.toLocaleLowerCase("et") !== e.lemma.toLocaleLowerCase("et"))
    bits.push(`<span class="dict-lemma" lang="et">${esc(e.lemma)}</span>`);
  e.pos.names.forEach((name, i) => bits.push(
    `<span class="dict-pos" lang="et">${esc(name)} <span class="ru" lang="ru">${esc(e.pos.ru[i] || "")}</span></span>`));
  const lv = e.level;
  // A level the list gives the word, or an estimate, which says it is one.
  if (lv && lv.same_word)
    bits.push(lv.estimate
      ? `<span class="dict-level" lang="et" title="${esc(sourceName(e, lv.source))}"><span class="sr-only">tase </span>${esc(lv.level)} <span class="ru" lang="ru">оценка</span></span>`
      : `<span class="dict-level" lang="et" title="${esc(sourceName(e, lv.source))}"><span class="sr-only">tase </span>${esc(lv.level)}</span>`);
  return bits.length ? `<div class="dict-meta">${bits.join("")}</div>` : "";
}

/* ── Meanings ───────────────────────────────────────────────────────── */

function meaningsHtml(e) {
  const m = e.meanings;
  const sourced = ["en", "uk"].filter(l => m[l] && m[l].source);
  const drafted = ["en", "uk"].filter(l => m[l] && m[l].model);
  const sources = [...new Set([m.ru?.source, ...sourced.map(l => m[l].source)].filter(Boolean))];
  let html = "";
  if (m.ru) html += `<p class="dict-ru" lang="ru">${listed(m.ru.words)}</p>`;
  if (sourced.length) html += `<dl class="dict-langs">${sourced.map(l =>
    `<div><dt lang="ru">${LANG_RU[l]}</dt><dd lang="${l}">${listed(m[l].words)}</dd></div>`).join("")}</dl>`;
  if (sources.length) html += `<p class="dict-src" lang="et">allikas: ${sources.map(id =>
    esc(sourceName(e, id))).join("; ")}</p>`;
  if (!m.ru && !sourced.length && !drafted.length)
    html += `<p class="dict-none" lang="ru">Перевода нет ни в одном словаре приложения.</p>`;
  if (drafted.length) {
    const model = m[drafted[0]].model;
    const back = drafted.map(l => m[l].model.back[0]).filter(Boolean)[0] || e.lemma;
    html += `<div class="model-out">
      <p class="model-head"><span lang="et">Mudeli mustand <span class="ru" lang="ru">черновик модели</span></span>
        <span class="model-engine">${esc(ENGINE[model.engine] || model.engine)}</span></p>
      <dl class="dict-langs">${drafted.map(l =>
        `<div><dt lang="ru">${LANG_RU[l]}</dt><dd lang="${l}">${listed(m[l].words)}</dd></div>`).join("")}</dl>
      <p class="model-note" lang="ru">Не из словаря: ${esc(ENGINE[model.checker] || model.checker)}
        перевёл черновик обратно, не видя слова, и назвал <span lang="et">${esc(back)}</span>.</p>
    </div>`;
  }
  return html;
}

/* ── Forms ──────────────────────────────────────────────────────────── */

function formCell(row, tapped) {
  const recorded = new Set(row.recorded || []);
  return row.forms.map(f => {
    const here = tapped && tapped.tag && tapped.tag.tag === row.tag &&
      f.toLocaleLowerCase("et") === tapped.form.toLocaleLowerCase("et");
    const say = recorded.has(f)
      ? `<button class="iconbtn form-say" type="button" data-say="${esc(f)}" data-say-tag="${esc(row.tag)}"
          aria-label="Kuula ${esc(f)} — запись EKI" title="Kuula — запись EKI">${icon("speaker-high", {weight: "bold"})}</button>` : "";
    return `<span class="form${here ? " here" : ""}" lang="et">${esc(f)}${say}</span>`;
  }).join(`<span class="form-alt" aria-hidden="true"> ~ </span>`);
}

function nounTable(rows, tapped) {
  const by = Object.fromEntries(rows.map(r => [r.tag, r]));
  const line = c => `<tr><th scope="row" lang="et">${c} <span class="ru" lang="ru">${CASE_RU[c]}</span></th>
    ${["sg", "pl"].map(n => {
      const r = by[`${n} ${({nimetav: "n", omastav: "g", osastav: "p"})[c]}`];
      return `<td>${r ? formCell(r, tapped) : "—"}</td>`;
    }).join("")}</tr>`;
  return `<table class="dict-forms noun"><thead><tr><td></td>
      <th scope="col" lang="et">ainsus <span class="ru" lang="ru">ед. ч.</span></th>
      <th scope="col" lang="et">mitmus <span class="ru" lang="ru">мн. ч.</span></th></tr></thead>
    <tbody>${["nimetav", "omastav", "osastav"].map(line).join("")}</tbody></table>`;
}

function rowTable(rows, tapped, cls) {
  return `<table class="dict-forms ${cls}"><tbody>${rows.map(r =>
    `<tr${tapped && tapped.tag && tapped.tag.tag === r.tag ? ' class="here"' : ""}>
      <th scope="row" lang="et">${esc(r.name)} <span class="ru" lang="ru">${esc(r.ru)}</span></th>
      <td>${formCell(r, tapped)}</td></tr>`).join("")}</tbody></table>`;
}

function formsHtml(e, tapped, page) {
  const f = e.forms;
  if (!f.rows.length) {
    if (f.kind === "pronoun")
      return `<p class="dict-none" lang="ru">Формы местоимений берутся из таблиц EKI; для этого слова таблицы нет.</p>`;
    return `<p class="dict-none" lang="ru">Не склоняется и не спрягается.</p>`;
  }
  const head = `<h3 class="dict-sec" lang="et">Vormid <span class="ru" lang="ru">формы</span></h3>`;
  const table = f.kind === "noun" ? nounTable(f.rows, tapped) : rowTable(f.rows, tapped, f.kind || "");
  const src = `<p class="dict-src" lang="et">allikas: ${esc(sourceName(e, f.source))}</p>${f.variants
    ? `<p class="dict-src" lang="ru">Vabamorf знает две парадигмы этого слова, а примеры EKI не показывают, какая нужна: даны обе.</p>` : ""}`;
  const all = page && f.paradigm.length > f.rows.length
    ? `<details class="fold dict-all"><summary lang="et">Kõik vormid <span class="ru" lang="ru">все формы</span></summary>
        ${rowTable(f.paradigm, tapped, "paradigm")}</details>` : "";
  return `<section class="dict-part">${head}<div class="dict-scroll">${table}</div>${src}${all}</section>`;
}

/* ── Definition, examples, idioms ───────────────────────────────────── */

function definitionHtml(e) {
  const d = e.definition;
  if (!d || (!d.text && !d.examples.length)) return "";
  return `<section class="dict-part dict-def-part">
    <h3 class="dict-sec" lang="et">Seletus <span class="ru" lang="ru">толкование по-эстонски</span></h3>
    ${d.text ? `<p class="dict-def" lang="et">${esc(d.text)}</p>` : ""}
    ${d.examples.length ? `<ul class="dict-uses" lang="et">${d.examples.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
    <p class="dict-src" lang="et">allikas: ${esc(sourceName(e, d.source))}</p>
    <div class="dict-live-def"></div></section>`;
}

function phraseItem(p) {
  // A phrase with an open slot is not a sentence anyone says; it gets no voice.
  const say = p.et.includes("{") ? "" :
    `<button class="iconbtn phrase-say" type="button" data-say="${esc(sayable(p.et))}"
       aria-label="Kuula — синтез речи" title="Kuula — синтез речи">${icon("speaker-high", {weight: "bold"})}</button>`;
  return `<li>${say}<span lang="et">${withSlots(p.et)}</span><span class="gloss" lang="ru">${withSlots(p.ru)}</span></li>`;
}

function examplesHtml(e) {
  if (!e.examples.length && !e.idioms.length) return "";
  const head = e.examples.slice(0, SHOWN_PHRASES), rest = e.examples.slice(SHOWN_PHRASES);
  let html = `<h3 class="dict-sec" lang="et">Näited <span class="ru" lang="ru">примеры с переводом</span></h3>`;
  if (head.length) html += `<ul class="phrase-list">${head.map(phraseItem).join("")}</ul>`;
  if (rest.length) html += `<details class="fold dict-more"><summary lang="et">veel ${rest.length} näidet
      <span class="ru" lang="ru">ещё примеры</span></summary><ul class="phrase-list">${rest.map(phraseItem).join("")}</ul></details>`;
  if (e.idioms.length) html += `<details class="fold dict-more"><summary lang="et">Väljendid (${e.idioms.length})
      <span class="ru" lang="ru">выражения</span></summary><ul class="phrase-list">${e.idioms.map(phraseItem).join("")}</ul></details>`;
  html += `<p class="dict-src" lang="et">allikas: ${esc(sourceName(e, "eki-evs"))}</p>`;
  return `<section class="dict-part phrases">${html}</section>`;
}

function sourcesHtml(e) {
  return `<details class="fold dict-sources"><summary lang="et">Allikad <span class="ru" lang="ru">источники статьи</span></summary>
    <ul>${e.sources.map(s => `<li><span lang="${/[Ѐ-ӿ]/.test(s.name) ? "ru" : "et"}">${esc(s.name)}</span>
      <span class="dict-src-what" lang="ru">${esc(s.what.split(", ").map(w => WHAT_RU[w] || w).join(", "))}${
        s.licence ? `; ${esc(s.licence)}` : ""}</span></li>`).join("")}</ul></details>`;
}

/* ── The learner's actions ──────────────────────────────────────────── */

function actionsHtml(e, page) {
  const status = e.status ? `<p class="dict-status" lang="et">olek: ${esc(e.status)}
      <span class="ru" lang="ru">${esc(STATUS_RU[e.status] || "")}</span></p>` : "";
  const queued = e.in_review;
  const add = `<button class="go" type="button" data-act="mine"${page ? " data-primary" : ""}${
      queued ? ' aria-disabled="true"' : ""} lang="et">${uiIcon(queued ? "check" : "plus")}${
      queued ? "Kordamises" : "Lisa kordamisse"} <span class="ru" lang="ru">${queued ? "в повторении" : "в повторение"}</span></button>`;
  const known = e.status === "tean" || e.status === "teadsin ammu";
  return `<div class="dict-actions${page ? " sticky" : ""}">
      <div class="dict-quiet">
        <button class="quiet" type="button" data-act="know"${known ? ' aria-disabled="true"' : ""} lang="et">Tean seda sõna
          <span class="ru" lang="ru">знаю, идёт в счёт</span></button>
        <button class="quiet" type="button" data-act="ignore"${e.status === "eiran" ? ' aria-disabled="true"' : ""} lang="et">Pole vaja
          <span class="ru" lang="ru">не предлагать</span></button>
      </div>${add}</div>
    ${status}<p class="dict-note" role="status" lang="ru"></p>`;
}

/* ── One entry, in the card or on its page ──────────────────────────── */

let seq = 0;

function entryHtml(e, {tapped = null, page = false, others = []} = {}) {
  const titleId = `dictTitle${++seq}`;
  // Another reading is another lemma; its form name is shown after it, in
  // Estonian, as Vabamorf names it.
  const other = others.length ? `<p class="dict-others" lang="ru">Другие разборы:
      ${others.map(a => `<button class="quiet" type="button" data-lemma="${esc(a.lemma)}" lang="et">${esc(a.lemma)}${
        a.tags.length === 1 ? `<span class="dict-other-form">${esc(a.tags[0].name)}</span>` : ""}</button>`).join("")}</p>` : "";
  return {titleId, html: `<div class="dict-top">${headHtml(e, tapped, titleId)}${sayButton(e)}</div>${metaHtml(e, tapped)}${other}
    <section class="dict-part dict-means">${meaningsHtml(e)}</section>
    ${formsHtml(e, tapped, page)}${definitionHtml(e)}${examplesHtml(e)}
    <div class="dict-live"></div>
    ${actionsHtml(e, page)}
    ${page ? "" : `<a class="quiet dict-open" href="#sonastik/${encodeURIComponent(e.lemma)}" lang="et">Ava sõnastikus
      <span class="ru" lang="ru">открыть статью целиком</span></a>`}
    ${sourcesHtml(e)}`};
}

/* What the live dictionary adds, merged into the entry the card shows. A
   source's English or Ukrainian replaces a model's draft. */
function mergeLive(e, x) {
  if (x.russian?.length && x.russian_source)
    e.meanings.ru = {words: x.russian.slice(0, 3), source: x.russian_source};
  for (const [lang, key] of [["en", "english"], ["uk", "ukrainian"]])
    if (x[key]?.length && x.translations_source)
      e.meanings[lang] = {words: x[key].slice(0, 3), source: x.translations_source};
  for (const id of [x.russian_source, x.translations_source, x.definition_source].filter(Boolean))
    if (!e.sources.some(s => s.id === id)) e.sources.push({id, name: LIVE_NAME[id] || id, what: "tõlge", licence: "CC-BY-4.0"});
}
const LIVE_NAME = {ekilex: "Ekilex API (EKI)", sonapi: "Sõnaveeb via api.sonapi.ee",
  "eki-vsl": "Võõrsõnade leksikon (EKI)", "eki-ekss": "Eesti keele seletav sõnaraamat (EKI)"};

function liveHtml(e, x) {
  const bits = [];
  if (!e.definition?.text && x.definition && x.definition_source)
    bits.push(`<p class="dict-def" lang="et">${esc(x.definition)}</p>
      <p class="dict-src" lang="et">allikas: ${esc(LIVE_NAME[x.definition_source] || sourceName(e, x.definition_source))}</p>`);
  /* The native-level wording beside the learner's, folded: the learner-level
     one is meant to be read first. Credited by source. */
  if (x.full_definition && x.full_definition_source)
    bits.push(`<details class="fold dict-more"><summary lang="et">täpsem seletus <span class="ru" lang="ru">подробнее по-эстонски</span></summary>
      <p class="dict-def" lang="et">${esc(x.full_definition)}</p>
      <p class="dict-src" lang="et">allikas: ${esc(LIVE_NAME[x.full_definition_source] || sourceName(e, x.full_definition_source))}</p></details>`);
  const facts = [];
  if (x.governs?.length) facts.push(`<div><dt lang="et">rektsioon <span class="ru" lang="ru">управление</span></dt>
      <dd lang="et">${esc(x.governs.join(", "))}</dd></div>`);
  if (x.inflection_type) facts.push(`<div><dt lang="et">muuttüüp <span class="ru" lang="ru">тип словоизменения</span></dt>
      <dd>${esc(String(x.inflection_type))}</dd></div>`);
  if (facts.length) bits.push(`<dl class="dict-facts">${facts.join("")}</dl>`);
  if (x.sonaveeb) bits.push(`<p class="dict-out"><a href="${esc(x.sonaveeb)}" target="_blank" rel="noopener" lang="et">Sõnaveeb
      <span class="ru" lang="ru">полная статья EKI</span>${uiIcon("out", "inline-ico")}</a></p>`);
  return bits.length ? `<section class="dict-part">${bits.join("")}</section>` : "";
}

/* Clicks inside an entry: voices, another reading, the three actions. One
   listener per root; what it acts on is the root's current `_dict`
   ({state, other}), so a card reopened on another word acts on that word. */
function wire(root) {
  if (root.dataset.wired) return;
  root.dataset.wired = "1";
  root.addEventListener("click", async ev => {
    const {state, other: open} = root._dict || {};
    if (!state) return;
    const say = ev.target.closest("[data-say]");
    if (say) {
      speakWord(say.dataset.say, msg => note(root, msg), say.dataset.sayTag || "");
      return;
    }
    const other = ev.target.closest("[data-lemma]");
    if (other) { open(other.dataset.lemma); return; }
    const act = ev.target.closest("[data-act]");
    if (!act || act.getAttribute("aria-disabled") === "true") return;
    act.setAttribute("aria-disabled", "true");
    const e = state.entry;
    try {
      if (act.dataset.act === "mine") {
        // The tapped form with its sentence, so mining reads the same word.
        const r = await (await api("/api/mine", {
          word: state.tapped?.form || e.lemma, context: state.sentence || null})).json();
        note(root, r.reason, !r.queued);
        if (r.queued) {
          act.innerHTML = `${uiIcon("check")}<span lang="et">Kordamises <span class="ru" lang="ru">в повторении</span></span>`;
          refreshDueBadge();
        } else act.removeAttribute("aria-disabled");
      } else {
        await api("/api/vocab/known", {lemmas: [e.lemma],
          ...(act.dataset.act === "ignore" ? {status: "ignore"} : {})});
        note(root, act.dataset.act === "ignore"
          ? `«${e.lemma}» больше не будет предлагаться.`
          : `«${e.lemma}» отмечено известным: это влияет на подбор текстов.`);
      }
    } catch (err) {
      note(root, err.message, true);
      act.removeAttribute("aria-disabled");
    }
  });
}

function note(root, text, bad = false) {
  const el = root.querySelector(".dict-note");
  if (!el) return;
  el.textContent = text || "";
  el.classList.toggle("no", !!bad);
}

/* Ask the live dictionary, and fill in what it adds. Never blocks the card. */
function enrich(root, state, stillHere) {
  api("/api/enrich/" + encodeURIComponent(state.entry.lemma), null, "GET")
    .then(r => r.json())
    .then(x => {
      if (!x.found || !stillHere()) return;
      mergeLive(state.entry, x);
      const means = root.querySelector(".dict-means");
      if (means) means.innerHTML = meaningsHtml(state.entry);
      const live = root.querySelector(".dict-live");
      if (live) live.innerHTML = liveHtml(state.entry, x);
    })
    .catch(() => {});
}

async function fetchEntry(lemma) {
  return (await api("/api/dictionary/entry/" + encodeURIComponent(lemma), null, "GET")).json();
}

/* ── The card ───────────────────────────────────────────────────────── */

const DESKTOP = matchMedia("(min-width:720px) and (hover:hover), (min-width:720px) and (min-height:560px)");
let cardToken = 0;

/* The sheet. The shell closes it (its close key, Escape, the scrim) and gives
   focus back to the word that opened it (`chrome.js`, Sheets); this adds the
   half and full heights and lets the looked-up word go. */
function sheet() {
  const el = $("#wordCard");
  if (!el.dataset.wired) {
    el.dataset.wired = "1";
    el.addEventListener("click", e => {
      if (e.target.closest(".word-grab")) setFull(el, !el.classList.contains("full"));
      // A link out of the card (its entry in Sõnastik) leaves the page it covers.
      else if (e.target.closest('a[href^="#"]')) el.close();
    });
    el.addEventListener("close", () => {
      cardToken++;
      setFull(el, false);
      document.querySelectorAll(".looked-up").forEach(w => w.classList.remove("looked-up"));
    });
    // Scrolling the half-height sheet raises it, as a phone's sheets do.
    el.querySelector(".word-body").addEventListener("scroll", ev => {
      if (ev.target.scrollTop > 8 && !DESKTOP.matches && !el.classList.contains("full")) setFull(el, true);
    }, {passive: true});
  }
  return el;
}

function setFull(el, full) {
  el.classList.toggle("full", full);
  const grab = el.querySelector(".word-grab");
  grab.setAttribute("aria-expanded", String(full));
  grab.setAttribute("aria-label", full ? "Vähenda — свернуть" : "Laienda — развернуть");
}

/* Beside the word on a desktop, on whichever side has more room, never over
   it: the sentence stays readable while the card is open. With too little
   room either side the card keeps its place in the middle. */
function place(el, opener) {
  for (const prop of ["top", "left", "max-height"]) el.style.removeProperty(prop);
  if (!DESKTOP.matches || !(opener instanceof HTMLElement) || !opener.isConnected) return;
  const r = opener.getBoundingClientRect(), gap = 12;
  const below = innerHeight - r.bottom - 2 * gap, above = r.top - 2 * gap;
  const room = Math.max(below, above);
  if (room < 280) return;
  el.style.maxHeight = `${Math.round(Math.min(room, 672))}px`;
  const w = el.offsetWidth, h = el.offsetHeight;
  el.style.left = `${Math.round(Math.max(gap, Math.min(r.left - 24, innerWidth - w - gap)))}px`;
  el.style.top = `${Math.round(below >= above ? r.bottom + gap : r.top - gap - h)}px`;
}

/* Open the card on a word met in a text (`contextFor` gives its sentence) or
   in a list. `card` is the old in-page container's argument, kept so callers
   need not change; the card is the one sheet now. */
export async function showWordCard(word, card, contextFor, opener = document.activeElement) {
  const el = sheet();
  const token = ++cardToken;
  const stillHere = () => token === cardToken && el.open;
  const body = el.querySelector(".word-body");
  el.hidden = false;
  el.opener = opener;
  if (opener instanceof HTMLElement && opener.matches("w, [data-word]")) opener.classList.add("looked-up");
  body.innerHTML = skeleton();
  el.setAttribute("aria-label", word);
  if (!el.open) el.showModal();
  place(el, opener);
  el.querySelector(".sheet-close").focus({preventScroll: true});
  const sentence = contextFor ? contextFor(word) : null;
  const state = {sentence, tapped: null, entry: null, analyses: [], first: {}};
  let look;
  try {
    const q = sentence ? "?sentence=" + encodeURIComponent(sentence.slice(0, 400)) : "";
    look = await (await api("/api/lookup/" + encodeURIComponent(word) + q, null, "GET")).json();
  } catch (e) {
    if (stillHere()) body.replaceChildren(retryableError(e.message, () => showWordCard(word, card, contextFor, opener)));
    return;
  }
  if (!stillHere()) return;
  if (!look.found) {
    body.innerHTML = emptyState({
      title: look.error ? "Разбор слова недоступен" : `«${esc(word)}» нет в словаре форм`,
      note: look.error ? "Словарь форм не собран на этом сервере." : "Проверь написание или найди слово в Sõnastik.",
      action: `<a class="ghost" href="#sonastik" lang="et">Sõnastik <span class="ru" lang="ru">словарь</span></a>`});
    return;
  }
  const reading = chosenReading(look);
  state.analyses = look.analyses;
  state.first = {lemma: reading.analysis?.lemma, tag: reading.tag};
  state.tapped = {form: word};
  // The lemma, not the surface form: the live dictionary does not know forms.
  const lemma = reading.analysis?.lemma || word;
  await renderCard(el, state, lemma, stillHere);
}

/* The card for one reading of the tapped word. The form is named only from
   Vabamorf's reading of it as this lemma: the one the sentence settled, or,
   once the learner picks another lemma, that lemma's only reading. */
async function renderCard(el, state, lemma, stillHere) {
  const body = el.querySelector(".word-body");
  let e;
  try {
    e = await fetchEntry(lemma);
  } catch (err) {
    if (stillHere()) body.replaceChildren(retryableError(err.message, () => renderCard(el, state, lemma, stillHere)));
    return;
  }
  if (!stillHere()) return;
  const analysis = state.analyses.find(a => a.lemma === lemma);
  const tag = lemma === state.first.lemma ? state.first.tag
    : analysis?.tags.length === 1 ? analysis.tags[0] : null;
  state.entry = e;
  state.tapped = {form: state.tapped.form, tag};
  const others = state.analyses.filter(a => a.lemma !== lemma);
  const {titleId, html} = entryHtml(e, {tapped: state.tapped, others});
  body.innerHTML = html;
  body.scrollTop = 0;
  el.removeAttribute("aria-label");
  el.setAttribute("aria-labelledby", titleId);
  body._dict = {state, other: next => renderCard(el, state, next, stillHere)};
  wire(body);
  place(el, el.opener);
  enrich(body, state, stillHere);
}

/* ── The Sõnastik page ──────────────────────────────────────────────── */

let searchToken = 0, timer = 0;
const RECENT_KEY = "dictRecent";

function recent() {
  try { return JSON.parse(sessionStorage.getItem(RECENT_KEY) || "[]"); } catch { return []; }
}
function remember(lemma) {
  try {
    sessionStorage.setItem(RECENT_KEY, JSON.stringify([lemma, ...recent().filter(l => l !== lemma)].slice(0, 8)));
  } catch { /* a private window keeps no list */ }
}

function rowHtml(r) {
  const tag = r.match?.tags.length === 1 ? `<span class="dict-tag" lang="et">${esc(r.match.tags[0].name)}</span>` : "";
  return `<li><a class="dict-row" href="#sonastik/${encodeURIComponent(r.lemma)}">
      <span class="dict-row-head"><span class="dict-row-word" lang="et">${esc(r.lemma)}</span>${
        r.level ? `<span class="dict-row-level">${esc(r.level)}</span>` : ""}</span>
      <span class="dict-row-sub">${tag}${r.russian.length
        ? `<span class="dict-row-gloss" lang="ru">${listed(r.russian)}</span>` : ""}</span></a></li>`;
}

function emptySearch() {
  const words = recent();
  return `<p class="dict-hint" lang="ru">Впиши слово в любой форме — <span lang="et">majja</span>,
      <span lang="et">loeb</span> — или русское слово, и откроется его статья.</p>${words.length
    ? `<h3 class="dict-sec" lang="et">Viimati vaadatud <span class="ru" lang="ru">недавно открытые</span></h3>
       <ul class="dict-results">${words.map(l => `<li><a class="dict-row" href="#sonastik/${encodeURIComponent(l)}">
         <span class="dict-row-head"><span class="dict-row-word" lang="et">${esc(l)}</span></span></a></li>`).join("")}</ul>` : ""}`;
}

/* The one form the query was, at the word, when Vabamorf reads it one way:
   *majja* over *maja, lühike sisseütlev*. */
function formHtml(d) {
  const matched = d.results.filter(r => r.match);
  if (matched.length !== 1 || matched[0].match.tags.length !== 1 || d.results[0] !== matched[0]) return "";
  const r = matched[0], t = r.match.tags[0];
  return `<p class="dict-form-of">${interlinear(r.match.form, {label: t.name, form_ru: t.ru, lemma: r.lemma})}
    <span class="dict-form-lemma" lang="ru">форма слова <span lang="et">${esc(r.lemma)}</span></span></p>`;
}

async function runSearch(q) {
  const out = $("#dictResults"), count = $("#dictCount");
  const mine = ++searchToken;
  try { sessionStorage.setItem("dictQuery", q); } catch { /* not kept */ }
  if (!q.trim()) {
    out.innerHTML = emptySearch();
    count.textContent = "";
    return;
  }
  let d;
  try {
    d = await (await api("/api/dictionary/search?q=" + encodeURIComponent(q), null, "GET")).json();
  } catch (e) {
    if (mine === searchToken) out.replaceChildren(retryableError(e.message, () => runSearch(q)));
    return;
  }
  if (mine !== searchToken) return;
  if (!d.results.length) {
    count.textContent = "Ничего не найдено.";
    out.innerHTML = emptyState({
      title: `«${esc(q.trim())}» нет в словарях приложения`,
      note: d.suggestions.length ? "Может быть, имелось в виду одно из этих слов (подсказки Vabamorf):"
        : "Проверь написание. Искать можно в любой форме или по-русски.",
      action: d.suggestions.map(s => `<button class="ghost" type="button" data-suggest="${esc(s)}" lang="et">${esc(s)}</button>`).join("")});
    return;
  }
  count.textContent = `Найдено: ${d.results.length}${d.results.length >= 20 ? " (первые 20)" : ""}.`;
  out.innerHTML = `${formHtml(d)}<ul class="dict-results">${d.results.map(rowHtml).join("")}</ul>`;
}

/* The entry page, `#sonastik/<lemma>`. */
async function showEntry(lemma) {
  const box = $("#dictEntry");
  $("#dictSearch").hidden = true;
  box.hidden = false;
  box.innerHTML = `<a class="quiet dict-back" href="#sonastik" lang="et">Sõnastik <span class="ru" lang="ru">к поиску</span></a>${skeleton()}`;
  const token = ++searchToken;
  let e;
  try {
    e = await fetchEntry(lemma);
  } catch (err) {
    if (token !== searchToken) return;
    box.lastElementChild.replaceWith(err.message.includes("нет в словарях")
      ? Object.assign(document.createElement("div"), {innerHTML: emptyState({
          title: `«${esc(lemma)}» нет в словарях приложения`,
          note: "Проверь написание или поищи слово в другой форме.",
          action: `<a class="ghost" href="#sonastik" lang="et">Otsi <span class="ru" lang="ru">искать</span></a>`})})
      : retryableError(err.message, () => showEntry(lemma)));
    return;
  }
  if (token !== searchToken) return;
  remember(e.lemma);
  const state = {entry: e, tapped: null, sentence: null};
  const {html} = entryHtml(e, {page: true});
  const body = document.createElement("article");
  body.className = "dict-entry";
  body.innerHTML = html;
  box.lastElementChild.replaceWith(body);
  body._dict = {state, other: next => { location.hash = "#sonastik/" + encodeURIComponent(next); }};
  wire(body);
  enrich(body, state, () => token === searchToken && !box.hidden);
  window.scrollTo({top: 0});
  body.querySelector(".dict-head").focus({preventScroll: true});
}

/* Opened by the router: the search, or one entry. */
export function ensureDictionary(lemma) {
  if (lemma) { showEntry(lemma); return; }
  ++searchToken;
  $("#dictEntry").hidden = true;
  $("#dictSearch").hidden = false;
  const field = $("#dictQ");
  if (!field.dataset.wired) {
    field.dataset.wired = "1";
    let kept = "";
    try { kept = sessionStorage.getItem("dictQuery") || ""; } catch { /* none */ }
    field.value = kept;
    field.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => runSearch(field.value), 200);
    });
    $("#dictForm").addEventListener("submit", ev => {
      ev.preventDefault();
      clearTimeout(timer);
      runSearch(field.value);
    });
    $("#dictResults").addEventListener("click", ev => {
      const s = ev.target.closest("[data-suggest]");
      if (!s) return;
      field.value = s.dataset.suggest;
      runSearch(field.value);
      field.focus();
    });
  }
  runSearch(field.value);
}
