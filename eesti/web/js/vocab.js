/* Sõnavara: the ladder, and the word card that both this and the reader open. */

import {$, api, esc} from "./core.js";
import {skeleton, uiIcon} from "./chrome.js";
import {refreshDueBadge} from "./review.js";

export async function showWordCard(word, card, contextFor) {
  card.hidden = false;
  card.innerHTML = skeleton(1);
  const d = await (await api("/api/lookup/" + encodeURIComponent(word), null, "GET")).json();
  /* `found:false` covers two different answers and used to render as one.
     A word can be genuinely absent from the lexicon -- or the lookup can be
     unable to run at all, which is what `error` says ("run `cli export`
     first" when the forms table was never exported). Reported as "не найдено"
     the second one blames the word for a missing build step, and the learner
     is told nothing they can act on about a card that would work fine
     tomorrow. The API knew; the card threw it away. */
  if (!d.found) {
    card.innerHTML = d.error
      ? `<span class="hint">${esc(d.word)} — разбор недоступен.
           <br>Словарь форм ещё не собран на этом сервере
           (<code>${esc(d.error)}</code>).</span>`
      : `<span class="hint">${esc(d.word)} — не найдено</span>`;
    return;
  }
  /* Two different things to say about a word, and until now only one of them
     could be said.

     "Add to review" queues the grammar pattern behind it. "I know this"
     records the lemma as known — and that was reachable only through
     `POST /api/vocab/known`, which nothing called, and `cli vocab`, which does
     not exist on the deployment. So on the running app no word could ever
     become known, and everything downstream of that sat at zero for good: the
     reading list's comprehensible-input ordering, dictation's easiest-first
     ordering, the vocabulary line in the readiness verdict, and the "N of the
     first 4000" counter. A whole pillar of the app with no input path. */
  // An anchor the late-arriving enrichment can insert *before*. It used to
  // insert before `#mineNote`, which sits under the buttons -- so what the word
  // means appeared below "+ Kordamisse", after the actions rather than with the
  // word they act on.
  const mineBtn = `<div id="cardExtra"></div>
    <div class="row" style="margin-top:var(--s2)">
      <button class="ghost" id="mineBtn">${uiIcon("plus")}Kordamisse</button>
      <button class="ghost" id="knowBtn">${uiIcon("check")}Tean seda sõna</button>
      <button class="ghost" id="skipBtn" title="Не тратить время на это слово">${uiIcon("ban")}Pole vaja</button></div>
    <div id="mineNote"></div>`;
  card.innerHTML = d.analyses.slice(0, 2).map(a => `
    <div class="lemma">${esc(a.lemma)}${a.level ? ` <span class="hint">${esc(a.level)}</span>` : ""}</div>
    <div class="tags">${a.tags.map(t => esc(t.name)).join(" · ")}</div>
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
    // A refusal is often temporary: the commonest one is "we do not know what
    // this word means yet", and the meaning arrives moments later from the
    // enrichment call this same card fires. Leaving the button disabled made
    // the advice to try again impossible to follow -- the only control that
    // could act on it was the one that had just switched itself off.
    else e.target.disabled = false;
  };

  /* Rection and inflection type, from Sõnaveeb.

     Fetched separately and appended when it arrives: this is the only call in
     the app that leaves the machine while the learner is waiting, and a word
     card must not be slower, or emptier, because a third party is having a bad
     afternoon. Nothing here is awaited before the card is usable. */
  // The LEMMA, not the word as it appears in the text. Sõnaveeb is a
  // dictionary: it knows `jätkuma`, not `jätkuvad`, and sending the surface
  // form returned "found: false" for every inflected word — which in Estonian
  // is most of them, so the enrichment looked like it simply never worked.
  const enrichLemma = d.analyses[0]?.lemma || word;
  fetch("/api/enrich/" + encodeURIComponent(enrichLemma))
    .then(r => r.json())
    .then(x => {
      if (!x.found) return;
      const bits = [];
      if (x.governs?.length) bits.push(`rektsioon: <b>${esc(x.governs.join(", "))}</b>`);
      if (x.inflection_type) bits.push(`muuttüüp <b>${esc(String(x.inflection_type))}</b>`);
      // The gloss, in the language this app explains things in. The API had
      // carried it all along under a key the provider never read, so the card
      // showed a muuttüüp number to someone who did not yet know the word.
      if (x.russian?.length)
        bits.push(`<span class="gloss">${esc(x.russian.join(", "))}</span>`);
      const slot = card.querySelector("#cardExtra");
      if (bits.length) {
        const extra = document.createElement("div");
        extra.className = "pair";
        extra.innerHTML = bits.join(" · ");
        slot.append(extra);
      }
      // Out to the real dictionary. Three fields is a reminder; the paradigm,
      // the audio and the rest live in Sõnaveeb, which this app deliberately
      // does not reimplement.
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

  // Marking a word known is an explicit act, never inferred from having read
  // it -- meeting a word is not knowing it, and a counter that inflates itself
  // measures reading rather than vocabulary.
  /* "Not worth my time" — the action a vocabulary list needs and a reader does
     not. Browsing B1 nouns turns up `riigivisiit` and `seinamaaling`: real
     words, correctly listed, and not what this learner is going to spend a
     morning on. Without this they return on every page and the "still to
     learn" count never means anything.

     Stored as `eiran` rather than as `tean`, because "I know this" and "this
     is not for me" are different facts and collapsing them would make the
     known-word count — which orders the reading list and feeds the verdict —
     quietly wrong. */
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
