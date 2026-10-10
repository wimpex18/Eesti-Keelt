/* Sõnavara: the ladder. A word opens the word card (`dictionary.js`), the one
   the reader and Sõnastik open too. */

import {$, api, esc} from "./core.js";
import {skeleton} from "./chrome.js";
import {showWordCard} from "./dictionary.js";

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
  showWordCard(b.dataset.word, null, null, b);
});
