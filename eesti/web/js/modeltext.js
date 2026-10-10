/* A model's words on the page (DESIGN.md, Model output): one block with a
   dashed outline and the engine named first, never a result colour or a score;
   the model's comments on writing and speaking against HARNO's descriptors,
   after code's checklist (`tutor.descriptor_feedback`); and the learner's
   explanation language, which every model call answers in.

   Shared by the session, the rule page, the mock exam's writing review and
   Rääkimine, so a model's text looks and is labelled the same everywhere. */

import {api, esc, md} from "./core.js";

let chosen = null;

/* The explanation language from onboarding (ru, uk, en); Russian until one is
   saved, and a failed read is not kept. Onboarding and Profiil announce a
   change (`eesti:language`); another identity reloads the page, which starts
   this afresh. */
export async function explanationLanguage() {
  if (chosen) return chosen;
  try {
    const me = await (await api("/api/me", null, "GET")).json();
    chosen = me.onboarding?.explanation_language || "ru";
  } catch { return "ru"; }
  return chosen;
}
addEventListener("eesti:language", e => { chosen = e.detail || null; });

export function modelBlock({engine, text = "", note = "", lang = "ru", source = "", body = ""}) {
  const by = engine && engine !== "none" ? engine.replace(/^llm:/, "") : "";
  return `<div class="model-out">
    <p class="model-by" lang="et">Selgitab mudel, ei hinda <span class="ru" lang="ru">объясняет модель, не оценивает${by ? `: ${esc(by)}` : ""}</span></p>
    ${text ? `<p class="model-text" lang="${esc(lang)}">${md(text)}</p>` : ""}
    ${body}
    ${note ? `<p class="hint" lang="${esc(lang)}">${esc(note)}</p>` : ""}
    ${source ? `<p class="model-src">${source}</p>` : ""}
  </div>`;
}

/* The slot the comments arrive in, while they load. */
export const commentsSlot = () =>
  `<div class="model-slot" aria-busy="true"><p class="loading-note" lang="et">Laadin… <span class="ru" lang="ru">загружаю комментарий модели</span></p></div>`;

/* Replace `box` with the model's comments on `text` (kind `kirjutamine` or
   `raakimine`) against HARNO's descriptors for `level`. Each comment names its
   criterion and quotes the learner; code has already dropped any that marks. */
export async function descriptorComments(box, {kind, text, level = "A2", task = ""}) {
  try {
    const lang = await explanationLanguage();
    const f = await (await api("/api/session/feedback", {kind, text, level, task, lang})).json();
    const points = f.points.map(p => `<li><span class="model-crit" lang="et">${esc(p.et)}</span>
      ${p.quote ? `<q lang="et">${esc(p.quote)}</q>` : ""} <span lang="${esc(f.lang)}">${md(p.comment)}</span></li>`).join("");
    box.outerHTML = modelBlock({engine: f.engine, lang: f.lang, note: f.note || "",
      body: points ? `<ul class="model-points">${points}</ul>` : "",
      source: `<span lang="ru">Критерии HARNO:</span> <a href="${esc(f.source.url)}" target="_blank" rel="noopener" lang="et">${esc(f.source.label)}</a>`});
  } catch (e) {
    box.outerHTML = `<p class="hint" role="alert">${esc(e.message)}</p>`;
  }
}
