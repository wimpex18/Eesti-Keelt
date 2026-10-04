/* The four things every other module needs: the DOM shorthand, escaping, the
   API call, and the two helpers that write to a control without destroying it.

   `btn.textContent = "…"` replaces every child, including the Russian gloss and
   the icon. Anything that changes a label goes through `setLabel`.

   Which voice reads what. The page is `lang="ru"`, so text is Russian unless it
   says otherwise: an element whose own text is an Estonian label carries
   `lang="et"`, and its Russian gloss (`.ru`) carries `lang="ru"` again —
   `<button lang="et">Kontrolli <span class="ru" lang="ru">проверить</span></button>`.
   The language sits on the element that already holds the label, so no wrapper
   is added and nothing moves. `setLabel` and `gloss` keep it right when a label
   changes at run time; `tests/test_ui_language.py` checks the markup and the
   templates. */


export const $ = s => document.querySelector(s);

export const esc = s => (s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* Which language a title is in, read off its script rather than assumed.
   Most library titles are Estonian, but ERR's Russian-language programmes
   ("Как это по-эстонски?") are not, and a screen reader told they are Estonian
   reads Russian words with Estonian phonology. */
export const langOf = s => /[Ѐ-ӿ]/.test(s || "") ? "ru" : "et";

// Explanations use **bold** for the grammar term and *italic* for the Estonian
// form being cited. Bold must be replaced first, or its inner asterisks get
// consumed by the italic rule and the markup comes out mangled.
export const md = s => esc(s)
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/\*(.+?)\*/g, "<em>$1</em>");


/* How to scroll: smoothly, unless the learner asked the system for less motion
   (a smooth `behavior` passed in script overrides the stylesheet's reduced motion). */
export const glide = () =>
  matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";


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


async function responseError(response) {
  const body = await response.json().catch(() => ({}));
  /* Server-side detail is already product copy and can describe a precise recovery.
     FastAPI's validation payload is an object, though, and the browser's status text is
     English; neither is a useful explanation for this learner. */
  if (typeof body.detail === "string" && body.detail.trim())
    return new Error(body.detail);
  const byStatus = {
    400: "Сервер не принял запрос. Проверь введённые данные и попробуй ещё раз.",
    401: "Войди в аккаунт ещё раз.",
    403: "Это действие недоступно в текущем аккаунте.",
    404: "Эта часть приложения не найдена. Обнови страницу и попробуй ещё раз.",
    408: "Сервер не ответил вовремя. Попробуй ещё раз.",
    422: "Сервер не смог проверить эти данные. Исправь их и попробуй ещё раз.",
    429: "Слишком много запросов. Подожди немного и попробуй ещё раз.",
  };
  return new Error(byStatus[response.status]
    || (response.status >= 500
      ? "Сервер временно не ответил. Попробуй ещё раз."
      : "Не удалось выполнить действие. Попробуй ещё раз."));
}


/* The one raw request escape hatch: speech uploads have a binary body rather than
   JSON, but deserve the same offline and HTTP-error behaviour as every other call. */
export async function rawApi(path, init = {}) {
  let response;
  const controller = new AbortController();
  // Home speech can take 25 seconds before falling back to hosted ASR.
  const timeout = setTimeout(() => controller.abort(),
    path.startsWith("/api/transcribe") ? 60000 : 30000);
  try {
    response = await fetch(path, {...init, signal: init.signal || controller.signal});
  } catch (err) {
    if (controller.signal.aborted)
      throw new Error("Сервер не ответил вовремя. Попробуй ещё раз.");
    throw new Error(
      "Нет соединения с сервером. Упражнения создаются на сервере, "
      + "поэтому без интернета их не открыть.");
  } finally {
    clearTimeout(timeout);
  }
  if (!response.ok) throw await responseError(response);
  return response;
}


export async function api(path, body, method) {
  const verb = method || (body === undefined || body === null ? "GET" : "POST");
  const init = { method: verb };
  if (verb !== "GET" && verb !== "HEAD") {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body ?? {});
  }
  return rawApi(path, init);
}

export function taskLine(it, ru, opts) {
  const bits = [];
  if (it.lemma) bits.push(`<span class="word" lang="et">${esc(it.lemma)}</span>`);
  const form = it.label || (it.lemma ? "" : it.hint || "");
  // The same string plays two roles. In a practice set it is the instruction
  // ("produce the osastav") and earns the accent. In the review queue it is the
  // card's topic — provenance, not a task — so it takes the quiet shape.
  const quiet = !!(opts && opts.quiet);
  if (form && !quiet) bits.push(`<span class="form" lang="et">${esc(form)}</span>`);
  if (it.lemma_ru) ru = [it.lemma_ru];
  if (ru && ru.length)
    bits.push(`<span class="gloss" lang="ru">${esc(ru.slice(0, 2).join(", "))}</span>`);
  // Chips last, and in the quiet shape the meaning comes before the topic:
  // what the word is matters more than which lesson filed it.
  if (form && quiet) bits.push(`<span class="lvl" lang="et">${esc(form)}</span>`);
  if (it.level) bits.push(`<span class="lvl">${esc(it.level)}</span>`);
  return `<span class="task">${bits.join("")}</span>`;
}

// Plain-language readings of the EKI case questions and personal pronouns.
// A choice exercise keeps its empty label: guidance must not choose its answer.
const FORM_RU = {
  alaleütlev: "кому? на что? куда?", alalütlev: "у кого? на чём? где?",
  alaltütlev: "от кого? с чего? откуда?", sisseütlev: "в кого? во что? куда?",
  seesütlev: "в ком? в чём? где?", seestütlev: "из кого? из чего? откуда?",
  omastav: "родительный падеж", osastav: "частичный падеж",
  kaasaütlev: "с кем? с чем?", ilmaütlev: "без кого? без чего?",
  olevik: "настоящее время", lihtminevik: "простое прошедшее время",
  mina: "я", ma: "я", sina: "ты", sa: "ты", tema: "он / она", ta: "он / она",
  meie: "мы", me: "мы", teie: "вы", te: "вы", nemad: "они", nad: "они",
};

export function addPracticeSupport(el, it, {offline = false} = {}) {
  const prompt = el.querySelector(".prompt");
  if (!prompt) return;
  const instruction = document.createElement("p");
  instruction.className = "practice-instruction";
  instruction.lang = "ru";
  const form = it.form_ru ? `${it.label} — ${it.form_ru}` : (it.label || "").split(", ").map(term =>
    FORM_RU[term] ? `${term} — ${FORM_RU[term]}` : term).join("; ");
  instruction.textContent = it.choices?.length
    ? (it.prompt.includes("____") ? "Выбери подходящую форму." : "Выбери подходящее предложение.")
    : `Впиши форму${it.lemma ? ` слова ${it.lemma}` : " слова"}.${form ? ` ${form}${/[?.!]$/.test(form) ? "" : "."}` : ""}`;
  prompt.before(instruction);
  const support = document.createElement("div");
  support.className = "practice-meaning";
  prompt.after(support);
  if (it.sentence_ru) {
    support.lang = "ru";
    support.textContent = it.sentence_ru;
    return;
  }
  // Offline packs never make a network request for an optional crutch.
  if (offline) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ghost";
  button.lang = "et";
  button.innerHTML = '<span lang="et">Tõlge <span class="ru" lang="ru">перевод предложения</span></span>';
  const result = document.createElement("p");
  result.lang = "ru";
  result.setAttribute("role", "status");
  support.append(button, result);
  button.addEventListener("click", async () => {
    button.disabled = true;
    result.textContent = "Перевожу…";
    try {
      const text = it.choices?.length ? it.answer
        : it.prompt.replace("____", (it.answer || "").split(" ~ ")[0]);
      const translated = await (await api("/api/translate", {text, target: "rus"})).json();
      result.textContent = translated.ok
        ? `${translated.text} · автоматический перевод (${translated.engine})`
        : translated.detail;
      if (translated.ok) button.hidden = true;
    } catch (err) {
      result.textContent = err.message;
    } finally {
      button.disabled = false;
    }
  });
}

const CYRILLIC = /[\u0400-\u04ff]/;

export function setLabel(el, text) {
  if (!el) return;
  const ru = el.querySelector(".ru");
  /* The mark survives a label change: `textContent =` wipes every child. */
  const ico = el.querySelector(".btn-ico");
  el.textContent = text;
  /* A label is Estonian ("Kontrolli"); a passing state is Russian ("Проверяю…").
     The element's language follows the text it now holds, so neither is read in
     the other's voice. */
  el.lang = CYRILLIC.test(text) ? "ru" : "et";
  if (ico) el.prepend(ico);
  if (ru) { el.append(" "); el.append(ru); }
}


/* Attach a small Russian gloss to an element without disturbing its label.

   Being glossed makes `el` an Estonian label, so it is marked as one; an element
   that already declares a language keeps it. */
export function gloss(el, ru) {
  if (!el || !ru || el.querySelector(".ru")) return;
  if (!el.lang) el.lang = "et";
  const s = document.createElement("span");
  s.className = "ru";
  s.lang = "ru";
  s.textContent = ru;
  el.append(" ", s);
}
