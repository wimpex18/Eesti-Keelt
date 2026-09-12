/* The licence ledger, rendered.

   `sources.REGISTRY` records every third party this project touches and the
   terms that govern it, and until now nothing served it — a record kept
   carefully and read by nobody, which is a writer with no caller pointing the
   other way.

   It has to reach the screen because of what the licences say rather than for
   tidiness. Three sources are CC BY 4.0, and that licence asks for the source
   to be named and the changes indicated *wherever the material is presented*.
   EKI's own terms on arhiiv.eki.ee/litsents/ put it plainly: the material may
   be processed and presented in any way needed, provided the reference to EKI
   is retained and the modifications described. Their definitions are on the
   word card and their levels are under every drill.

   Loaded on first open, not on boot. An obligation the page must be able to
   discharge is not a thing the learner needs fetched before their first
   drill. */

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
        ? `<div class="changed">Muudatused: ${esc(s.changes)}</div>` : "";
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
