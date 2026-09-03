/* The four things every other module needs: the DOM shorthand, escaping, the
   API call, and the two helpers that write to a control without destroying it.

   `setLabel` is here rather than beside a button because of what it prevents:
   `btn.textContent = "…"` replaces *every* child, and once the buttons carried
   a Russian gloss that assignment silently deleted the only word on them the
   learner can read. Anything that changes a label goes through it. */


export const $ = s => document.querySelector(s);

export const esc = s => (s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

// Explanations use **bold** for the grammar term and *italic* for the Estonian
// form being cited. Bold must be replaced first, or its inner asterisks get
// consumed by the italic rule and the markup comes out mangled.
export const md = s => esc(s)
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/\*(.+?)\*/g, "<em>$1</em>");


export function once(fn) {
  let done = false;
  return () => { if (!done) { done = true; fn(); } };
}

export async function api(path, body, method) {
  const verb = method || (body === undefined || body === null ? "GET" : "POST");
  const init = { method: verb };
  if (verb !== "GET" && verb !== "HEAD") {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body ?? {});
  }
  let r;
  try {
    r = await fetch(path, init);
  } catch (err) {
    /* A failed fetch throws a TypeError whose message is the browser's own
       English string -- "Failed to fetch" in Chrome, "NetworkError when
       attempting to fetch resource" in Firefox. Every caller renders
       `err.message` into a banner, so with no connection the app told a
       Russian-speaking learner "Failed to fetch".

       Made reachable by the service worker: before it, losing the connection
       gave the browser's own offline page and the app never got to speak. Now
       the shell loads and this is what it says, so it has to say something
       true and readable. */
    throw new Error(
      "Нет соединения с сервером. Упражнения создаются на сервере, "
      + "поэтому без интернета их не открыть.");
  }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r;
}

export function taskLine(it, ru, opts) {
  const bits = [];
  if (it.lemma) bits.push(`<span class="word">${esc(it.lemma)}</span>`);
  const form = it.label || (it.lemma ? "" : it.hint || "");
  // The same string plays two roles. In a practice set it is the instruction
  // -- "produce the osastav" -- and earns the accent. In the review queue it
  // is which topic the card came from, which is provenance, not a task, and
  // rendering "TÄISSIHITIS JA OSASIHITIS" in accented capitals made the label
  // wider and louder than the word it described.
  const quiet = !!(opts && opts.quiet);
  if (form && !quiet) bits.push(`<span class="form">${esc(form)}</span>`);
  if (ru && ru.length)
    bits.push(`<span class="gloss">${esc(ru.slice(0, 2).join(", "))}</span>`);
  // Chips last, and in the quiet shape the meaning comes before the topic:
  // what the word is matters more than which lesson filed it.
  if (form && quiet) bits.push(`<span class="lvl">${esc(form)}</span>`);
  if (it.level) bits.push(`<span class="lvl">${esc(it.level)}</span>`);
  return `<span class="task">${bits.join("")}</span>`;
}

export function setLabel(el, text) {
  if (!el) return;
  const ru = el.querySelector(".ru");
  /* The mark survives a label change for the same reason the gloss does:
     `textContent =` wipes every child, and a button that loses its icon the
     first time it says "Laen…" never gets it back. */
  const ico = el.querySelector(".btn-ico");
  el.textContent = text;
  if (ico) el.prepend(ico);
  if (ru) el.append(ru);
}


/* Attach a small Russian gloss to an element without disturbing its label. */
export function gloss(el, ru) {
  if (!el || !ru || el.querySelector(".ru")) return;
  const s = document.createElement("span");
  s.className = "ru";
  s.lang = "ru";
  s.textContent = ru;
  el.append(s);
}
