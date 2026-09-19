/* The licence ledger, rendered.

   `sources.REGISTRY` records every third party this project touches and the
   terms that govern it.

   It is on screen because CC BY 4.0 asks for the source to be named and changes
   indicated wherever the material is presented. EKI's terms
   (arhiiv.eki.ee/litsents/) allow processing and presentation provided the
   reference to EKI is retained and modifications are described.

   Loaded on first open, not on boot. */

import {$, api, esc, once} from "./core.js";

const load = once(async () => {
  const box = $("#sourceList");
  if (!box) return;
  try {
    // `api()` hands back the Response, not the body — the idiom every
    // other loader here uses.
    const {sources} = await (await api("/api/sources")).json();
    box.innerHTML = (sources || []).map(s => {
      const bits = [`<b>${esc(s.name)}</b>`];
      // The link belongs to the credit: "reference to EKI" is a reference
      // somebody can follow, not a name in small type.
      if (s.url) bits.push(`<a href="${esc(s.url)}" target="_blank"
        rel="noopener">${esc(new URL(s.url).hostname)}</a>`);
      bits.push(`<span class="lic">${esc(s.licence)}</span>`);
      // Only where a licence asks for it, which is exactly where `changes` is
      // non-empty. Printing "no changes" under everything else would turn a
      // legal statement into decoration.
      const changed = s.changes
        ? `<div class="changed"><span lang="et">Muudatused:</span> ${esc(s.changes)}</div>` : "";
      return `<div class="src">${bits.join(" · ")}${changed}</div>`;
    }).join("");
  } catch {
    // A failed fetch must not leave an empty disclosure looking like a page
    // that credits nobody.
    box.innerHTML = `<p class="note">Источники сейчас не загрузились.</p>`;
  }
});

$("#sourceBox")?.addEventListener("toggle", e => {
  if (e.target.open) load();
});
