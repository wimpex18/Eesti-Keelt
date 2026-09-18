/* The four things every other module needs: the DOM shorthand, escaping, the
   API call, and the two helpers that write to a control without destroying it.

   `btn.textContent = "…"` replaces every child, including the Russian gloss and
   the icon. Anything that changes a label goes through `setLabel`. */


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

/* A count with its Russian noun in the right form: 1 слово, 2 слова, 5 слов.
   `forms` is [one, few, many]; Intl picks which applies to the number. */
const RU_PLURAL = new Intl.PluralRules("ru");
export function ruCount(n, [one, few, many]) {
  const form = {one, few, many}[RU_PLURAL.select(n)] || many;
  return `${n.toLocaleString("ru")} ${form}`;
}


/* A wrong answer, shown as what was written and what is right.

   The learner's own attempt is struck through, then the right form. The drill's
   distractor (the typical confusion, e.g. osastav for omastav) is not printed: when
   the learner wrote it, it is already the struck form, and when they did not,
   "а не <distractor>" blamed a form nobody typed. */
export function wrongVerdict(given, answer, why) {
  const tried = (given || "").trim();
  return `✗ ${tried ? `<del>${esc(tried)}</del> → ` : ""}<ins>${esc(answer)}</ins>`
    + (why ? `<br><span class="why">${md(why)}</span>` : "");
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
    /* A failed fetch throws the browser's own English message ("Failed to fetch").
       Every caller renders `err.message`, so it is replaced with a Russian one —
       with the service worker serving the shell offline, this is what the learner
       sees. */
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
  // ("produce the osastav") and earns the accent. In the review queue it is the
  // card's topic — provenance, not a task — so it takes the quiet shape.
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
  /* The mark survives a label change: `textContent =` wipes every child. */
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
