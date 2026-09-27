/* Profiil: who is learning and how far they have come (ADR-0006).

   SKELETON, kept here because `tests/test_ui_contract.py` rejects a page
   module nothing imports: move it to `eesti/web/js/profile.js` when wiring it
   up, and delete `docs/skeletons/`. `docs/identity.md` ("Profile page") is the
   specification: a `tab-profile` panel in the Eksam mode after Edenemine,
   content on the plain page (never glass), the shared exercise treatment and
   hairline rows (DESIGN.md "Layout rhythm"), reusing `sealsHtml` and
   `rhythmHtml` from `chrome.js` rather than drawing new ones. No streak: the
   app has a rhythm, and nothing resets.

   Konto shows Põhikonto, Õppija or Külaline (`me.scope`).

   Wire-up left to do:
   - markup: the panel in `index.html` and its tab button in `#nav-exam`;
   - `router.js`: `profile: () => loadProfile()` in `ON_OPEN`;
   - `main.js`: `paintScope()` once at boot, so a guest sees the sandbox line
     on every screen;
   - `docs/app-structure.md`: the tab in the diagram (the doc test checks it). */

import {$, api, esc} from "./core.js";
import {retryableError, rhythmHtml, sealsHtml} from "./chrome.js";

export async function loadProfile() {
  const out = $("#profileOut");
  if (!out) return;
  try {
    const me = await api("/api/me").then(r => r.json());
    out.innerHTML = profileHtml(me);
  } catch (err) {
    out.replaceChildren(retryableError(err.message, loadProfile));
  }
}

/* TODO(Luna): the full page per the spec: Nimi (editable, `Salvesta`),
   E-post, Õpib alates, Viimati, Tase, Märgid per level, Rütm, Kokku, and for a
   guest the sandbox line with `Tühjenda liivakast`. */
function profileHtml(me) {
  const level = me.level?.current || "A1";
  return `<p lang="et">${esc(me.name || "")}</p>`
    + sealsHtml(me.milestones?.[level] || [])
    + rhythmHtml(me.rhythm || []);
}

/* TODO(Luna): on a guest scope, one line at the top of the column on every
   screen: Külaline, and in Russian that progress is not saved. */
export async function paintScope() {}
