/* The session (DESIGN.md, The session; ADR-0009): today's steps, one item at a
   time, with one primary that changes its label and never its place.

   The server composes the session and holds every key (`eesti/session.py`,
   `api/session.py`). An item comes with its token, its choices where it is a
   choice, and no answer; the verdict brings the key, the reason and the form's
   name, which `interlinear()` writes under the word only then. A first miss in
   guided practice and words comes back with a hint from code and one retry;
   only the first attempt is recorded. Nothing here decides a result.

   The item's states (DESIGN.md, Practice rhythm): awaiting → ready → checking →
   right | hint | revealed, or skipped. While an item awaits its answer or shows
   its correction it carries `data-dock-task`, so a phone's dock steps aside and
   the primary rides above the keyboard.

   Kinds of unit in a step: an item (typed, chosen or built from tiles), a review
   card, a word, a question on a heard or read text, a dictation sentence, a
   sentence to repeat, a spoken or written task, and the step's intro or close
   (the rule after the choices, a transcript after the questions). */

import {$, api, attribHtml, esc, fitInterlinear, formGloss, interlinear, md, ruCount, setLabel,
  TASK_RU} from "./core.js";
import {sayHtml, speakWord, wireSay} from "./media.js";
import {icon} from "./icons.js";
import {loadRail, refreshDueBadge} from "./review.js";
import {keepLinesInside, onLessonPractice} from "./lesson.js";
import {addMic} from "./voice.js";

/* Count words for the plan, as Estonian says them: the singular after one, the
   singular partitive after more (Vabamorf's forms of each noun, `sg p`). */
export const STEP_UNITS = {
  kordamine: ["kaart", "kaarti"], reegel: ["ülesanne", "ülesannet"],
  harjutamine: ["ülesanne", "ülesannet"], sonad: ["sõna", "sõna"],
  kuulamine: ["ülesanne", "ülesannet"], lugemine: ["küsimus", "küsimust"],
  raakimine: ["ülesanne", "ülesannet"], kirjutamine: ["tekst", "teksti"],
  kontroll: ["ülesanne", "ülesannet"],
};
export const etCount = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/* What the learner types is what is graded: no capitals, corrections or fills. */
const ANSWER_FIELD = `autocapitalize="off" autocorrect="off" spellcheck="false" autocomplete="off"`;
const glossed = (et, ru) => `<span lang="et">${esc(et)} <span class="ru" lang="ru">${esc(ru)}</span></span>`;
const markIcon = name => icon(name, {weight: "bold", cls: "sess-mark"});

function announce(text) {
  const out = $("#announce");
  if (!out) return;
  out.textContent = "";
  requestAnimationFrame(() => { out.textContent = text; });
}

const store = {
  get(key) { try { return JSON.parse(localStorage.getItem(key) || "null"); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode */ } },
  drop(key) { try { localStorage.removeItem(key); } catch { /* private mode */ } },
};

// ── State ──────────────────────────────────────────────────────────
const S = {
  run: 0,               // a load generation: a slow answer never paints a newer screen
  mode: "today",        // today | topic | check
  topic: null, rules: null, from: null, check: null,
  session: null, step: null, content: null,
  units: [], pos: 0, marks: [], tally: null,
  summary: [], missed: [], lang: "ru", next: null,
  unit: null,           // the controller of the unit on screen
};

const primary = () => $("#sessPrimary");

/* The one primary: its label changes, its place never does. Off is the ink
   fill at 40 % with the label kept (`aria-disabled`), so it is never mistaken
   for a second button and its reason can still be announced. */
function setPrimary(et, ru, enabled = true) {
  const btn = primary();
  setLabel(btn, et);
  btn.querySelector(".ru").textContent = ru;
  btn.setAttribute("aria-disabled", String(!enabled));
}

let checkingTimer = 0;
function checking(on) {
  clearTimeout(checkingTimer);
  if (on) checkingTimer = setTimeout(() => setPrimary("Kontrollin…", "проверяю", false), 300);
}

$("#sessPrimary").addEventListener("click", () => {
  const u = S.unit;
  if (!u) return;
  if (primary().getAttribute("aria-disabled") === "true") { u.nudge?.(); return; }
  u.primary?.();
});
$("#sessSkip").addEventListener("click", () => S.unit?.skip?.());

function setSkip(on) { $("#sessSkip").hidden = !on; }

/* The microphone: a key in the task row beside the primary (DESIGN.md), filling
   the answer with what was heard for the learner to check before Kontrolli. */
function dropMic() {
  document.querySelectorAll("#sessActions .mic").forEach(b => b.remove());
  document.body.classList.remove("has-mic");
}
function micFor(input, prompt, run) {
  dropMic();
  const holder = document.createElement("span");
  holder.hidden = true;
  input.after(holder);
  addMic(null, input, prompt).then(() => {
    const mic = input.nextElementSibling;
    if (run !== S.run || !mic?.classList.contains("mic")) return;
    mic.classList.add("sess-mic");
    $("#sessActions").insertBefore(mic, primary());
    document.body.classList.add("has-mic");
  }).finally(() => holder.remove());
}
function setChecked(html) { $("#sessChecked").innerHTML = html || ""; }
const CHECKED_BY_CODE = `<span lang="et">Kontrollis kood <span class="ru" lang="ru">проверено кодом: Vabamorf и ключ задания</span></span>`;


// ── The session line and the beads ─────────────────────────────────
function paintLine() {
  const s = S.session;
  if (!s || S.mode === "check") { $("#sessLine").innerHTML = ""; return; }
  const steps = s.steps;
  const here = steps.findIndex(st => st.id === S.step?.id);
  const phases = s.phases.filter(p => steps.some(st => st.phase === p.id));
  const name = steps[here] ? `Samm ${here + 1}/${steps.length}: ${steps[here].et}` : "Tund";
  $("#sessLine").innerHTML = `<ol class="sess-phases" aria-label="${esc(name)}">${phases.map(p => `
    <li class="sess-phase" style="--n:${steps.filter(st => st.phase === p.id).length}"><span class="sess-phase-name" lang="et">${glossed(p.et, p.ru)}</span>
      <ol class="sess-segs">${steps.filter(st => st.phase === p.id).map(st => {
        const i = steps.indexOf(st);
        const state = i === here ? "current" : st.state === "done" ? "done" : "todo";
        return `<li class="sess-seg" data-state="${state}"${state === "current" ? ' aria-current="step"' : ""}>
          <span class="sr-only">${esc(st.et)}, ${state === "done" ? "tehtud" : state === "current" ? "praegu" : "ees"}</span></li>`;
      }).join("")}</ol></li>`).join("")}</ol>`;
}

const BEAD_WORDS = {right: "õige", wrong: "pole õige", skipped: "vahele jäetud",
                    answered: "vastatud", current: "praegu", todo: "ees"};

function paintBeads() {
  const beads = S.units.filter(u => u.bead);
  const current = S.units[S.pos];
  $("#sessBeads").innerHTML = beads.map((u, i) => {
    const mark = S.marks[S.units.indexOf(u)] || (u === current ? "current" : "todo");
    return `<li class="sess-bead" data-mark="${mark}"${mark === "current" ? ' aria-current="step"' : ""}>
      <span class="sr-only" lang="et">Ülesanne ${i + 1}/${beads.length}, ${BEAD_WORDS[mark]}</span></li>`;
  }).join("");
}


// ── Loading a session ──────────────────────────────────────────────
async function language() {
  try {
    const me = await (await api("/api/me", null, "GET")).json();
    return me.onboarding?.explanation_language || "ru";
  } catch { return "ru"; }
}

function title(et, ru) {
  const h = $("#sessionTitle");
  h.innerHTML = glossed(et, ru);
}

function inSession(on) {
  document.body.classList.toggle("in-session", on);
  const pause = document.querySelector(".hdr-pause");
  if (pause) pause.hidden = !on;
}
addEventListener("eesti:place", e => inSession(e.detail === "session"));

function body(html) {
  const out = $("#sessBody");
  out.innerHTML = html;
  return out;
}

function loading() {
  S.unit = null;
  setSkip(false); setChecked("");
  setPrimary("Laadin…", "загружаю", false);
  body(`<p class="loading-note" lang="et">Laadin… <span class="ru" lang="ru">загружаю</span></p>`);
}

function failed(message, retry) {
  S.unit = {primary: retry};
  setPrimary("Proovi uuesti", "загрузить ещё раз");
  body(`<div class="banner recoverable-error" role="alert">${esc(message)}</div>`);
}

let started = "";   // the route this runner last started, so re-selecting does not restart it

/* Opened by the router for `#session` and `#session/<topic>`. */
export async function ensureSession(topic) {
  const route = topic ? `topic:${topic}` : "today";
  if (S.check && S.check.pending) {
    S.check.pending = false;
    started = route;
    return runCheck();
  }
  if (started === route && S.session) return;
  started = route;
  if (topic) {
    if (S.topic !== topic) { S.rules = null; S.from = null; }
    S.mode = "topic"; S.topic = topic;
  } else {
    S.mode = "today"; S.topic = null; S.rules = null; S.from = null;
  }
  S.check = null;
  return load();
}

/* Kursus' Õpi, a remediation, the rule page's Harjuta: a session on one topic. */
export function openTopic(topic, {rules = null, from = null} = {}) {
  S.rules = rules; S.from = from; S.topic = topic; S.check = null;
  started = "";
  const hash = "#session/" + encodeURIComponent(topic);
  if (location.hash === hash) ensureSession(topic);
  else location.hash = hash;
}

/* Kursus' test-out and unit check: a set answered whole and graded by the server
   from its seed (`placement.probe`, `unitcheck.grade`). */
export function startCheckSet(check) {
  S.check = {...check, pending: true};
  S.mode = "check";
  started = "";
  const hash = "#session/" + encodeURIComponent(check.topic || "");
  if (location.hash === hash) { S.check.pending = false; runCheck(); }
  else location.hash = hash;
}

onLessonPractice(topic => openTopic(topic, {from: "rule"}));

const query = () => {
  const q = new URLSearchParams();
  if (S.mode === "topic" && S.topic) q.set("topic", S.topic);
  if (S.rules?.length) q.set("rules", S.rules.join(","));
  return q.toString();
};

async function load() {
  const run = ++S.run;
  loading();
  $("#sessLine").innerHTML = ""; $("#sessBeads").innerHTML = ""; $("#sessStep").textContent = "";
  try {
    S.lang = await language();
    let made;
    if (S.mode === "topic") {
      const r = await (await api(`/api/session/topic/${encodeURIComponent(S.topic)}?${query()}`, null, "GET")).json();
      made = r.session; S.next = r.next;
    } else {
      made = await (await api("/api/session/start", {})).json();
    }
    if (run !== S.run) return;
    S.session = made;
    S.summary = []; S.missed = [];
    // The screen is named by what it teaches: the topic, or the unit and the
    // session's place in it.
    if (S.mode === "topic" && made.topic) title(made.topic.et, made.topic.ru);
    else title(`${made.unit.n}. ${made.unit.et}`, `занятие ${made.n} из ${made.of}`);
    let first = made.steps.find(st => st.state !== "done");
    // The rule page's Harjuta: the rule was just read there.
    if (S.from === "rule" && first?.id === "reegel")
      first = made.steps.find(st => st.id === "harjutamine") || first;
    if (!first) return finish(run);
    await openStep(first, run);
  } catch (e) {
    if (run !== S.run) return;
    failed(e.message, load);
  }
}


// ── Steps ──────────────────────────────────────────────────────────
const keyOf = step => `klint.session.${S.session.id}.${step.id}${S.rules ? "." + S.rules.join("+") : ""}`;

async function openStep(step, run = S.run) {
  S.step = step;
  loading();
  paintLine();
  const h = $("#sessStep");
  h.innerHTML = glossed(step.et, step.ru);
  $("#sessWhy").textContent = step.why_ru || "";
  try {
    S.content = await (await api(`/api/session/step/${step.id}?${query()}`, null, "GET")).json();
  } catch (e) {
    if (run !== S.run) return;
    return failed(e.message, () => openStep(step, run));
  }
  if (run !== S.run) return;
  S.units = unitsOf(step, S.content);
  const kept = store.get(keyOf(step));
  S.pos = kept && kept.pos < S.units.length ? kept.pos : 0;
  S.marks = kept?.marks || [];
  S.tally = kept?.tally || {asked: 0, correct: 0, skipped: 0};
  if (!S.units.length) return nextStep(run);
  // The step's name is the bench heading once, as the step begins.
  h.focus({preventScroll: true});
  show(run);
}

async function nextStep(run = S.run) {
  const step = S.step;
  S.summary.push({id: step.id, et: step.et, ru: step.ru, ...S.tally});
  store.drop(keyOf(step));
  let after;
  try {
    after = await (await api(`/api/session/step/${step.id}/done`, {
      session: S.session.id, asked: S.tally.asked, correct: S.tally.correct,
      skipped: S.tally.skipped})).json();
  } catch (e) {
    if (run !== S.run) return;
    return failed(e.message, () => nextStep(run));
  }
  if (run !== S.run) return;
  S.next = after.next;
  const steps = S.session.steps;
  const at = steps.findIndex(st => st.id === step.id);
  steps[at] = {...steps[at], state: "done"};
  const following = steps.slice(at + 1).find(st => st.state !== "done");
  if (following) return openStep(following, run);
  return finish(run);
}

function advance(run = S.run) {
  if (run !== S.run) return;
  S.pos += 1;
  // A set answered whole has no session to come back to: nothing to keep.
  if (S.session) store.set(keyOf(S.step), {pos: S.pos, marks: S.marks, tally: S.tally});
  if (S.pos >= S.units.length) return nextStep(run);
  show(run);
}

/* Put the unit at `S.pos` on the bench. A new item takes the focus at its
   answer; the view transition, where there is one, fades the old one out. */
function show(run = S.run) {
  const unit = S.units[S.pos];
  const paint = () => {
    S.unit = null;
    // The step's purpose is said as it begins, not on every item.
    $("#sessWhy").hidden = S.pos > 0;
    dropMic();
    setSkip(false); setChecked("");
    body("");
    // Which unit is on the bench: set once it is, never before.
    $("#sessBody").dataset.unit = `${S.step?.id || ""}:${S.pos}`;
    unit.render($("#sessBody"), run);
    fitLines();
    paintBeads();
    paintLine();
  };
  if (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches
      && $("#sessBody").childElementCount && document.visibilityState === "visible") {
    // A transition skipped (a hidden tab, another one starting) still paints.
    const t = document.startViewTransition(paint);
    t.ready.catch(() => {}); t.finished.catch(() => {}); t.updateCallbackDone.catch(() => {});
  } else paint();
}

/* A form line hangs from its word's start and does not wrap: near the end of
   a short line it moves left inside its sentence, and wider than the sentence
   it wraps there (the rule page's own fitting, `keepLinesInside`). Measured
   again whenever the bench changes width. */
function fitLines() {
  const out = $("#sessBody");
  out.querySelectorAll(".prompt").forEach(fitInterlinear);
  keepLinesInside(out);
}
let benchWidth = 0;
new ResizeObserver(([entry]) => {
  const width = Math.round(entry.contentRect.width);
  if (width !== benchWidth) { benchWidth = width; fitLines(); }
}).observe($("#sessBody"));

function mark(result) {
  S.marks[S.pos] = result;
  if (result === "skipped") S.tally.skipped += 1;
  else if (result !== "answered") {
    S.tally.asked += 1;
    if (result === "right") S.tally.correct += 1;
  }
  paintBeads();
}

/* The units of one step, in the order the learner meets them. */
function unitsOf(step, c) {
  const units = [];
  if (c.kind === "cards") c.cards.forEach(card => units.push(card.kind === "vocab"
    ? {bead: true, render: (root, run) => vocabCard(root, card, run)}
    : {bead: true, render: (root, run) => itemUnit(root, card, {kind: "card", glosses: c.glosses}, run)}));
  if (c.kind === "rule") {
    if (c.notice) units.push({render: (root, run) => noticeUnit(root, c.notice, run)});
    c.items.forEach(it => units.push({bead: true, render: (root, run) =>
      itemUnit(root, it, {kind: "item", glosses: c.glosses}, run)}));
    units.push({render: (root, run) => ruleAfter(root, c, run)});
  }
  if (c.kind === "items") c.items.forEach((it, i) => units.push({bead: true, render: (root, run) =>
    itemUnit(root, it, {kind: "item", glosses: c.glosses || {}, noHints: !!c.no_hints,
                        mixedNow: it.block === "mixed" && c.items[i - 1]?.block === "blocked"}, run)}));
  if (c.kind === "words") c.items.forEach(w => units.push({bead: true, render: (root, run) =>
    itemUnit(root, w, {kind: "word"}, run)}));
  if (c.kind === "material") {
    const heard = c.material.kind === "dialoog" && step.id === "kuulamine";
    if (heard) units.push({render: (root, run) => listenIntro(root, c.material, run)});
    c.questions.forEach(q => units.push({bead: true, render: (root, run) =>
      questionUnit(root, c.material, q, {heard}, run)}));
    if (heard) units.push({render: (root, run) => transcriptUnit(root, c.material, run)});
  }
  if (c.kind === "dictation") (c.passages || []).forEach(p => units.push({bead: true, render: (root, run) =>
    dictationUnit(root, p, run)}));
  if (c.kind === "speaking") {
    c.shadow.forEach(text => units.push({render: (root, run) => shadowUnit(root, text, run)}));
    c.tasks.forEach(task => units.push({render: (root, run) => speakTask(root, task, c.level, run)}));
  }
  if (c.kind === "writing") units.push({render: (root, run) => writingUnit(root, c, run)});
  if (c.kind === "unit-check") {
    answers.length = 0;
    c.items.forEach((it, i) => units.push({bead: true, render: (root, run) => itemUnit(root, it,
      {kind: "item", glosses: c.glosses || {}, set: {index: i, size: c.items.length}}, run)}));
    units.push({render: (root, run) => setResult(root, {kind: "unit", unit: c.unit, seed: c.seed,
                                                         parts: c.parts}, run)});
  }
  return units;
}


// ── An item: the state machine ─────────────────────────────────────
/* The instruction: one sentence in the explanation language, without the lemma,
   which is under the gap. The form asked for is named where the task is to
   produce it; a choice names nothing. */
function instruction(it, kind) {
  if (kind === "word") return "Впиши слово, которое подходит по смыслу.";
  if (kind === "card" && it.choices?.length) return "Выбери форму, которая подходит.";
  if (it.tiles?.length) return `Собери фразу из слов: «${it.ru}».`;
  const label = it.label || "";
  if (TASK_RU[label]) return TASK_RU[label];
  if (it.choices?.length) return it.prompt.includes("____")
    ? "Выбери форму, которая подходит." : "Выбери подходящее предложение.";
  if (!label) return "Впиши нужную форму.";
  const gloss = formGloss(it, label);
  return `Впиши форму: ${label}${gloss ? ` — ${gloss}` : ""}.`;
}

/* The line under the gap before an attempt: the lemma and its meaning (for a
   word, the meaning alone: the word is the answer). Never the form's name. */
function awaitingLine(it, kind, glosses) {
  const meaning = it.lemma_ru || ((glosses || {})[it.lemma] || []).slice(0, 2).join(", ")
    || (it.answer_ru || []).join(", ");
  const head = kind === "word" ? "" : (it.lemma || "");
  if (!head && !meaning) return "";
  return `<span class="il-f">${head ? `<span class="sr-only">, </span><span class="il-name" lang="et">${esc(head)}</span>` : ""}`
    + (meaning ? `<span class="sr-only">, </span><span class="il-gloss" lang="ru">${esc(meaning)}</span>` : "")
    + "</span>";
}

function gapHtml(it, kind, glosses, typed) {
  const field = typed
    ? `<input class="gap-field" type="text" size="6" lang="et" aria-label="Vastus — ответ" ${ANSWER_FIELD}>`
    : `<span class="gap-blank" aria-hidden="true"></span><span class="sr-only" lang="ru">пропуск</span>`;
  return `<span class="il" data-state="awaiting" lang="et"><span class="il-w">${field}</span>${awaitingLine(it, kind, glosses)}</span>`;
}

function sentenceHtml(it, kind, glosses, typed) {
  const prompt = it.prompt || "";
  if (!prompt.includes("____")) return `<p class="prompt sess-sentence" lang="et">${esc(prompt)}</p>`;
  const [before, after] = prompt.split("____");
  return `<p class="prompt sess-sentence" lang="et">${esc(before)}${gapHtml(it, kind, glosses, typed)}${esc(after)}</p>`;
}

/* The sentence's support before a check: the item's own translation where it
   carries one, else Tõlge on request (labelled with its engine). Out of the way
   of the answer, in the correction region. */
function supportHtml(it) {
  if (it.sentence_ru) return `<p class="sess-support" lang="ru">${esc(it.sentence_ru)}</p>`;
  if (it.translate === false || it.tiles?.length) return "";
  return `<button class="ghost sess-translate" type="button" lang="et">Tõlge <span class="ru" lang="ru">перевод предложения</span></button>`;
}

function itemUnit(root, it, {kind = "item", glosses = {}, noHints = false, mixedNow = false,
                            set = null} = {}, run) {
  const step = S.step.id;
  const typed = !it.choices?.length && !it.tiles?.length;
  const el = document.createElement("div");
  el.className = "sess-item";
  el.dataset.state = "awaiting";
  el.setAttribute("data-dock-task", "");
  const note = mixedNow ? glossed("Nüüd segamini", "теперь вперемешку с другой темой")
    : set?.index === 0 ? glossed("Ilma vihjeteta", "без подсказок; результат — после последнего задания, считается один раз") : "";
  el.innerHTML = `${note ? `<p class="sess-note" lang="et">${note}</p>` : ""}
    <p class="sess-instr" lang="ru">${esc(instruction(it, kind))}</p>
    ${sayHtml(it)}
    ${it.tiles?.length ? `<div class="sess-tiles"><p class="prompt sess-line" lang="et" aria-label="Fraas — фраза" aria-live="polite"></p><div class="sess-bank"></div></div>`
      : sentenceHtml(it, kind, glosses, typed)}
    ${typed && !(it.prompt || "").includes("____")
      ? `<input class="gap-field sess-answer" type="text" lang="et" aria-label="Vastus — ответ" ${ANSWER_FIELD}>` : ""}
    ${it.choices?.length ? `<div class="sess-choices" role="radiogroup" aria-label="Valikud — варианты">${it.choices.map((c, i) =>
      `<button class="sess-choice" type="button" role="radio" aria-checked="false" tabindex="${i ? -1 : 0}" data-choice="${esc(c)}" lang="et">${esc(c)}</button>`).join("")}</div>` : ""}
    <div class="sess-corr" aria-live="polite">${supportHtml(it)}</div>
    ${attribHtml(it)}`;
  root.appendChild(el);
  const corr = el.querySelector(".sess-corr");
  wireSay(el, message => { corr.insertAdjacentHTML("beforeend", `<p class="hint">${esc(message)}</p>`); });
  const input = el.querySelector(".gap-field");
  const choices = [...el.querySelectorAll(".sess-choice")];
  const sentence = el.querySelector(".sess-sentence");
  fitInterlinear(sentence);
  let given = "", attempt = 1, eventId = crypto.randomUUID(), firstEvent = null;
  const shownAt = performance.now();
  let startedAt = null;
  el.addEventListener("focusin", () => { startedAt ??= performance.now(); });

  const ready = () => given.trim().length > 0;
  // In a set answered whole the last Kontrolli hands the set in.
  const last = set && set.index === set.size - 1;
  const paintPrimary = () => last ? setPrimary("Valmis", "сдать проверку", ready())
    : setPrimary("Kontrolli", set ? "дальше" : "проверить", ready());
  // The translation, on request only, labelled with its engine.
  el.querySelector(".sess-translate")?.addEventListener("click", async e => {
    const b = e.currentTarget; b.disabled = true;
    try {
      const text = (it.prompt || "").replace("____", "…");
      const t = await (await api("/api/translate", {text, target: "rus"})).json();
      b.outerHTML = t.ok ? `<p class="sess-support" lang="ru">${esc(t.text)} <span class="hint">автоматический перевод (${esc(t.engine)})</span></p>`
        : `<p class="hint">${esc(t.detail || "перевод недоступен")}</p>`;
    } catch (err) { b.disabled = false; b.insertAdjacentHTML("afterend", `<p class="hint">${esc(err.message)}</p>`); }
  });

  if (input) {
    const size = () => { input.size = Math.max(6, input.value.length + 1); };
    input.addEventListener("input", () => { given = input.value; size(); paintPrimary(); });
    input.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); primary().click(); } });
    micFor(input, it.prompt || "", run);
    requestAnimationFrame(() => input.focus({preventScroll: true}));
  }
  if (choices.length) {
    const pick = b => {
      if (el.dataset.state !== "awaiting" && el.dataset.state !== "ready") return;
      choices.forEach(x => { x.setAttribute("aria-checked", String(x === b)); x.tabIndex = x === b ? 0 : -1; });
      given = b.dataset.choice;
      el.dataset.state = "ready";
      const blank = el.querySelector(".gap-blank");
      if (blank) blank.textContent = given;
      paintPrimary();
    };
    choices.forEach(b => b.addEventListener("click", () => pick(b)));
    el.querySelector(".sess-choices").addEventListener("keydown", e => {
      const keys = ["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft"];
      if (!keys.includes(e.key)) return;
      e.preventDefault();
      const at = choices.indexOf(document.activeElement);
      const to = choices[(at + (e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : choices.length - 1)) % choices.length];
      to.focus(); pick(to);
    });
    requestAnimationFrame(() => choices[0].focus({preventScroll: true}));
  }
  if (it.tiles?.length) {
    const line = el.querySelector(".sess-line"), bank = el.querySelector(".sess-bank");
    it.tiles.forEach(word => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "ghost sess-tile"; b.lang = "et"; b.textContent = word;
      b.onclick = () => {
        if (el.dataset.state !== "awaiting" && el.dataset.state !== "ready") return;
        (b.parentElement === bank ? line : bank).appendChild(b);
        given = line.children.length === it.tiles.length ? [...line.children].map(x => x.textContent).join(" ") : "";
        el.dataset.state = given ? "ready" : "awaiting";
        paintPrimary();
      };
      bank.appendChild(b);
    });
  }

  const lock = on => {
    if (input) input.readOnly = on;
    choices.forEach(b => b.disabled = on);
    el.querySelectorAll(".sess-tile").forEach(b => b.disabled = on);
  };

  async function check() {
    if (!ready()) return;
    if (set) {
      // The server grades the set whole from its seed: the answer is taken,
      // with no verdict of its own.
      answers[set.index] = given;
      mark("answered");
      return advance(run);
    }
    el.dataset.state = "checking";
    lock(true);
    checking(true);
    let res;
    const latency = Math.round(performance.now() - (startedAt ?? shownAt));
    try {
      const sent = kind === "card"
        ? {kind: "card", id: it.id, given, event_id: eventId, latency_ms: latency}
        : kind === "word"
        ? {kind: "word", token: it.token, given, attempt}
        : {kind: "item", step, token: it.token, given, attempt, choice: !typed,
           event_id: attempt === 1 ? eventId : "", latency_ms: latency};
      res = await (await api("/api/session/answer", sent)).json();
    } catch (e) {
      checking(false);
      if (run !== S.run) return;
      // The item is not spent: the same answer goes again with the same identity.
      el.dataset.state = "ready"; lock(false);
      corr.innerHTML = `<p class="sess-verdict" role="alert" lang="ru">Ответ пока не сохранён. ${esc(e.message)}</p>`;
      paintPrimary();
      return;
    }
    checking(false);
    if (run !== S.run) return;
    if (attempt === 1) firstEvent = res.event_id || null;
    if (res.retry || (kind === "word" && !res.correct && attempt === 1 && !noHints)) {
      // A first miss: the hint from code, the answer kept and selected, one retry.
      attempt = 2;
      el.dataset.state = "hint";
      mark("wrong");
      S.marks[S.pos] = "wrong";
      corr.innerHTML = `<p class="sess-verdict sess-hint" lang="et">${glossed("Proovi veel", "попробуй ещё раз")}</p>
        <p class="sess-hint-text" lang="ru">${md(res.hint_ru || "")}</p>`;
      lock(false);
      setPrimary("Kontrolli", "проверить", ready());
      if (input) { input.focus({preventScroll: true}); input.select(); }
      return;
    }
    const counted = attempt === 1;
    if (counted) mark(res.correct ? "right" : "wrong");
    verdict(res);
  }

  function verdict(res) {
    const right = !!res.correct;
    const key = (res.answer || "").split(" ~ ")[0];
    const form = right && typed && given.trim() ? given.trim() : key || given;
    el.dataset.state = right ? "right" : "revealed";
    // The sentence completes itself at the word: the form, its bar and its name.
    // A task's label (`kuula`, `sõnadega`) names no form, so it is never the name.
    const named = {...it, label: TASK_RU[it.label] ? "" : it.label,
                   lemma_ru: it.lemma_ru || (res.lemma_ru || "")};
    const il = el.querySelector(".sess-sentence .il");
    if (il && form) {
      il.outerHTML = interlinear(form, named, {state: right ? "right" : "revealed", glosses});
      fitLines();
    } else if (it.tiles?.length || (!il && res.solution)) {
      const line = el.querySelector(".sess-line") || el.querySelector(".sess-sentence");
      if (line) line.textContent = res.solution || res.answer || "";
    }
    // A choice hid its form until now: the reason is the lesson either way.
    const reason = !right || it.form_after || !typed ? (res.why_ru || "") : "";
    const queued = kind === "word" && res.queued
      ? `<p class="hint" lang="ru">Слово <span lang="et">${esc(res.lemma || it.lemma)}</span> добавлено в повторение.</p>` : "";
    corr.innerHTML = right
      ? `<p class="sess-verdict sess-ok">${markIcon("check")}${glossed("Õige", "верно")}</p>
         ${reason ? `<p class="sess-reason" lang="ru">${md(reason)}</p>` : ""}${queued}`
      : `<p class="sess-verdict sess-no">${markIcon("x")}${glossed("Pole õige", "неверно")}</p>
         ${given && typed ? `<p class="sess-yours" lang="et">Sinu vastus <span class="ru" lang="ru">твой ответ</span> <del>${esc(given)}</del></p>` : ""}
         <div class="sess-help">${firstEvent ? `<button class="ghost sess-miks" type="button" lang="et">Miks? <span class="ru" lang="ru">объясни</span></button>` : ""}
           ${it.topic && it.topic !== "sonad" ? `<a class="ghost" href="#rule/${esc(it.topic)}" lang="et">Reegel <span class="ru" lang="ru">правило</span></a>` : ""}</div>
         ${reason ? `<p class="sess-reason" lang="ru">${md(reason)}</p>` : ""}`;
    if (!right && kind !== "card") {
      S.missed.push(`${esc((it.prompt || "").split("____")[0])}${interlinear(key, named, {state: "revealed", glosses})}${esc((it.prompt || "").split("____")[1] || "")}`);
    }
    corr.querySelector(".sess-miks")?.addEventListener("click", e => miks(e.currentTarget, firstEvent));
    // The chosen row says what became of it: a tick only where it was right.
    choices.forEach(b => {
      if (b.dataset.choice !== given) return;
      b.dataset.result = right ? "right" : "wrong";
    });
    if (kind === "card") refreshDueBadge();
    if (res.just_mastered) announce(`Teema läbitud. Тема пройдена: следующие темы открыты.`);
    setChecked(CHECKED_BY_CODE);
    setSkip(false);
    dropMic();
    setPrimary("Edasi", "дальше");
    S.unit = {primary: () => advance(run)};
    primary().focus({preventScroll: true});
  }

  S.unit = {
    primary: check,
    nudge: () => { (input || choices[0])?.focus(); },
    skip: () => {
      if (el.dataset.state === "checking") return;
      el.dataset.state = "skipped";
      lock(true);
      if (attempt === 1) mark("skipped");
      corr.innerHTML = `<p class="sess-verdict sess-skipped" lang="et">${glossed("Vahele jäetud", "пропущено, без оценки")}</p>`;
      setSkip(false);
      setPrimary("Edasi", "дальше");
      S.unit = {primary: () => advance(run)};
      primary().focus({preventScroll: true});
    },
  };
  setSkip(!set);
  paintPrimary();
}

/* Miks?: the model's explanation of this miss, in the explanation language,
   from the item's EKK section. Labelled with its engine; no result colour. */
async function miks(btn, eventId) {
  btn.disabled = true;
  try {
    const a = await (await api("/api/session/miks", {event_id: eventId, lang: S.lang})).json();
    const ref = a.reference?.known
      ? `<a href="${esc(a.reference.url)}" target="_blank" rel="noopener" lang="et">EKK ${esc(a.reference.ekk_section)}</a>` : "";
    btn.closest(".sess-help").insertAdjacentHTML("afterend", modelBlock({
      engine: a.engine, text: a.text, note: a.note, lang: a.lang, source: ref}));
    btn.hidden = true;
  } catch (e) {
    btn.disabled = false;
    btn.insertAdjacentHTML("afterend", `<p class="hint">${esc(e.message)}</p>`);
  }
}

/* A model's words: a dashed outline, the engine named first, never a result
   colour or a score (DESIGN.md, Model output). */
function modelBlock({engine, text = "", note = "", lang = "ru", source = "", body = ""}) {
  const by = engine && engine !== "none" ? engine.replace(/^llm:/, "") : "";
  return `<div class="model-out">
    <p class="model-by" lang="et">Selgitab mudel, ei hinda <span class="ru" lang="ru">объясняет модель, не оценивает${by ? `: ${esc(by)}` : ""}</span></p>
    ${text ? `<p class="model-text" lang="${esc(lang)}">${md(text)}</p>` : ""}
    ${body}
    ${note ? `<p class="hint" lang="${esc(lang)}">${esc(note)}</p>` : ""}
    ${source ? `<p class="model-src">${source}</p>` : ""}
  </div>`;
}


// ── The rule step: notice, choose, then the rule ───────────────────
function noticeUnit(root, notice, run) {
  root.innerHTML = `<div class="sess-notice">
    <p class="sess-instr" lang="ru">Посмотри на подчёркнутые слова.</p>
    ${notice.examples.map(e => `<p class="prompt sess-sentence" lang="et">${esc(e.before)}${interlinear(e.form, {}, {state: "notice"})}${esc(e.after)}</p>`).join("")}
    <p class="sess-question" lang="ru">${md(notice.question_ru)}</p></div>`;
  setPrimary("Proovi", "выбери форму сам");
  S.unit = {primary: () => advance(run)};
}

function ruleAfter(root, c, run) {
  const a = c.after;
  const sources = (a.sources || []).map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener" lang="et">${esc(s.label)}</a>`).join("");
  root.innerHTML = `<div class="sess-rule">
    <h4 lang="et">${glossed("Miks nii", "почему так")}</h4>
    ${a.gist_ru ? `<p class="sess-gist" lang="ru">${md(a.gist_ru)}</p>` : ""}
    ${a.explain ? modelBlock({engine: a.explain.engine, text: a.explain.text, lang: a.explain.lang,
        source: `<a href="${esc(a.explain.source.url)}" target="_blank" rel="noopener" lang="et">${esc(a.explain.source.label)}</a>`}) : ""}
    ${a.contrast?.length ? `<ul class="sess-pairs">${a.contrast.map(p => `<li>
        <p class="rw-cond" lang="et">${glossed(p.et, p.ru)}</p>
        <p class="sess-wrong" lang="et">${markIcon("x")}<span class="sr-only" lang="ru">неверно: </span>${esc(p.before)}<del>${esc(p.wrong)}</del>${esc(p.after)}</p>
        <p class="sess-right prompt" lang="et">${markIcon("check")}<span class="sr-only" lang="ru">верно: </span>${esc(p.before)}${interlinear(p.form, {form_after: p.name, lemma: p.lemma, form_ru: p.form_ru}, {state: "reference"})}${esc(p.after)}</p>
      </li>`).join("")}</ul>` : ""}
    ${a.points_ru?.length ? `<h4 lang="et">${glossed("Reegel", "правило по источникам")}</h4>
      <ul class="sess-points">${a.points_ru.map(p => `<li>${md(p)}</li>`).join("")}</ul>` : ""}
    <p class="sess-sources" lang="et">Allikad <span class="ru" lang="ru">источники</span> ${sources}
      <a href="#rule/${esc(c.topic)}" lang="et">Reegel tervikuna <span class="ru" lang="ru">всё правило</span></a></p>
  </div>`;
  fitLines();
  setPrimary("Edasi", "к упражнениям");
  S.unit = {primary: () => advance(run)};
  root.querySelector("h4").setAttribute("tabindex", "-1");
  root.querySelector("h4").focus({preventScroll: true});
}


// ── Review: a meaning card is rated by the learner ─────────────────
function vocabCard(root, card, run) {
  const el = document.createElement("div");
  el.className = "sess-item sess-card";
  el.setAttribute("data-dock-task", "");
  el.innerHTML = `<p class="sess-instr" lang="ru">Вспомни, что значит слово, потом открой ответ и оцени себя.</p>
    <p class="prompt sess-word" lang="et">${esc(card.lemma)} <button class="iconbtn sess-say" type="button" aria-label="Kuula — прослушать">${icon("speaker-high")}</button></p>
    ${card.context ? `<p class="sess-context" lang="et">${esc(card.context)}</p>` : ""}
    <div class="sess-corr" aria-live="polite"></div>`;
  root.appendChild(el);
  const corr = el.querySelector(".sess-corr");
  el.querySelector(".sess-say").onclick = () => speakWord(card.lemma,
    message => corr.insertAdjacentHTML("beforeend", `<p class="hint">${esc(message)}</p>`));
  const eventId = crypto.randomUUID();
  const reveal = () => {
    corr.innerHTML = `<p class="sess-meaning" lang="ru">${esc(card.meaning)}</p>
      ${card.phrase ? `<p class="sess-phrase" lang="et">${esc(card.phrase.et)} <span class="ru" lang="ru">${esc(card.phrase.ru)}</span></p>
        <p class="attrib" lang="et">näide: EKI eesti-vene sõnaraamat · CC BY 4.0</p>` : ""}
      <div class="sess-choices sess-rates" role="radiogroup" aria-label="Hinnang — насколько хорошо вспомнил">
        ${[["again", "Ei mäleta", "не помню"], ["hard", "Raske", "с трудом"], ["good", "Teadsin", "знал"]].map(([r, et, ru]) =>
          `<button class="sess-choice" type="button" role="radio" aria-checked="false" data-r="${r}" lang="et">${glossed(et, ru)}</button>`).join("")}
      </div>`;
    corr.querySelectorAll("[data-r]").forEach(b => b.onclick = async () => {
      corr.querySelectorAll("[data-r]").forEach(x => { x.disabled = true; x.setAttribute("aria-checked", String(x === b)); });
      try {
        const r = await (await api("/api/session/answer", {kind: "card", id: card.id, rating: b.dataset.r,
                                                           event_id: eventId})).json();
        if (run !== S.run) return;
        mark(b.dataset.r === "again" ? "wrong" : "right");
        corr.insertAdjacentHTML("beforeend", `<p class="hint" lang="ru">Снова ${r.interval_days < 1 ? "сегодня" : `через ${Math.round(r.interval_days)} дн.`}</p>`);
        refreshDueBadge();
        setPrimary("Edasi", "дальше");
        S.unit = {primary: () => advance(run)};
        primary().focus({preventScroll: true});
      } catch (e) {
        corr.querySelectorAll("[data-r]").forEach(x => { x.disabled = false; });
        corr.insertAdjacentHTML("beforeend", `<p class="hint" role="alert">${esc(e.message)}</p>`);
      }
    });
    setPrimary("Hinda", "оцени себя", false);
    S.unit = {nudge: () => corr.querySelector("[data-r]")?.focus()};
    corr.querySelector("[data-r]")?.focus({preventScroll: true});
  };
  setPrimary("Näita", "показать ответ");
  S.unit = {primary: reveal, skip: () => { mark("skipped"); advance(run); }};
  setSkip(true);
}


// ── Listening and reading: a checked text, questions graded by code ─
const VOICES = ["mari", "tambet", "liivika", "kalev"];

async function playTurns(material, btn) {
  btn.disabled = true;
  const voice = Object.fromEntries(material.speakers.map((s, i) => [s.name, VOICES[i % VOICES.length]]));
  try {
    for (const t of material.turns) {
      const q = new URLSearchParams({text: t.text, voice: voice[t.speaker] || VOICES[0], speed: "0.85"});
      const url = URL.createObjectURL(await (await api("/api/speak?" + q, null, "GET")).blob());
      await new Promise(done => {
        const audio = new Audio(url);
        audio.onended = audio.onerror = () => { URL.revokeObjectURL(url); done(); };
        audio.play().catch(done);
      });
    }
  } catch (e) {
    btn.insertAdjacentHTML("afterend", `<p class="hint" role="alert">Звук не загрузился: ${esc(e.message)}</p>`);
  } finally { btn.disabled = false; }
}

const labelLine = m => `<p class="hint model-label" lang="ru">${esc(m.label)} (${esc(m.engine)}).</p>`;

function listenIntro(root, m, run) {
  root.innerHTML = `<div class="sess-listen">
    <p class="sess-instr" lang="ru">Послушай диалог «<span lang="et">${esc(m.title)}</span>». Текст покажем после вопросов.</p>
    <button class="ghost sess-play" type="button" lang="et">${icon("speaker-high", {cls: "btn-ico"})}Kuula <span class="ru" lang="ru">прослушать</span></button>
    ${labelLine(m)}</div>`;
  const play = root.querySelector(".sess-play");
  play.onclick = () => playTurns(m, play);
  setPrimary("Küsimused", "к вопросам");
  S.unit = {primary: () => advance(run)};
}

function questionUnit(root, m, q, {heard}, run) {
  const el = document.createElement("div");
  el.className = "sess-item";
  el.setAttribute("data-dock-task", "");
  el.innerHTML = `${heard ? `<button class="ghost sess-play" type="button" lang="et">${icon("speaker-high", {cls: "btn-ico"})}Kuula uuesti <span class="ru" lang="ru">прослушать ещё раз</span></button>`
      : `<div class="sess-text prose" lang="et">${m.paragraphs.map(p => `<p>${esc(p)}</p>`).join("")}</div>${labelLine(m)}`}
    <p class="sess-instr" lang="ru">Ответь словами из ${heard ? "диалога" : "текста"}.</p>
    <p class="prompt sess-question-et" lang="et">${esc(q.question)}</p>
    <input class="sess-answer" type="text" lang="et" aria-label="Vastus — ответ" ${ANSWER_FIELD}>
    <div class="sess-corr" aria-live="polite"></div>`;
  root.appendChild(el);
  el.querySelector(".sess-play")?.addEventListener("click", e => playTurns(m, e.currentTarget));
  const input = el.querySelector(".sess-answer"), corr = el.querySelector(".sess-corr");
  input.addEventListener("input", () => setPrimary("Kontrolli", "проверить", !!input.value.trim()));
  input.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); primary().click(); } });
  requestAnimationFrame(() => input.focus({preventScroll: true}));
  const check = async () => {
    input.readOnly = true;
    checking(true);
    let r;
    try {
      r = await (await api("/api/session/answer", {kind: "material", material: m.id, item: q.id,
                                                   given: input.value})).json();
    } catch (e) {
      checking(false); input.readOnly = false;
      corr.innerHTML = `<p class="sess-verdict" role="alert" lang="ru">${esc(e.message)}</p>`;
      setPrimary("Kontrolli", "проверить", true);
      return;
    }
    checking(false);
    if (run !== S.run) return;
    mark(r.correct ? "right" : "wrong");
    corr.innerHTML = r.correct
      ? `<p class="sess-verdict sess-ok">${markIcon("check")}${glossed("Õige", "верно")}</p>`
      : `<p class="sess-verdict sess-no">${markIcon("x")}${glossed("Pole õige", "неверно")}</p>
         <p class="sess-yours" lang="et">Sinu vastus <span class="ru" lang="ru">твой ответ</span> <del>${esc(input.value)}</del></p>
         <p class="sess-reason" lang="et">${esc(r.expected || "")}</p>`;
    setChecked(`<span lang="et">Kontrollis kood <span class="ru" lang="ru">проверено кодом по самому тексту</span></span>`);
    setPrimary("Edasi", "дальше");
    S.unit = {primary: () => advance(run)};
    setSkip(false);
    primary().focus({preventScroll: true});
  };
  setPrimary("Kontrolli", "проверить", false);
  S.unit = {primary: check, nudge: () => input.focus(),
            skip: () => { mark("skipped"); advance(run); }};
  setSkip(true);
}

function transcriptUnit(root, m, run) {
  root.innerHTML = `<div class="sess-transcript">
    <h4 lang="et">${glossed("Tekst", "текст диалога")}</h4>
    <dl class="sess-turns">${m.turns.map(t => `<dt lang="et">${esc(t.speaker)}</dt><dd lang="et">${esc(t.text)}</dd>`).join("")}</dl>
    ${labelLine(m)}</div>`;
  setPrimary("Edasi", "дальше");
  S.unit = {primary: () => advance(run)};
}

function dictationUnit(root, p, run) {
  const el = document.createElement("div");
  el.className = "sess-item";
  el.setAttribute("data-dock-task", "");
  el.innerHTML = `<p class="sess-instr" lang="ru">Послушай и запиши предложение.</p>
    <button class="ghost sess-play" type="button" lang="et">${icon("speaker-high", {cls: "btn-ico"})}Kuula <span class="ru" lang="ru">прослушать</span></button>
    <input class="sess-answer" type="text" lang="et" aria-label="Kirjuta kuuldu — запиши услышанное" ${ANSWER_FIELD}>
    <div class="sess-corr" aria-live="polite"></div>`;
  root.appendChild(el);
  const input = el.querySelector(".sess-answer"), corr = el.querySelector(".sess-corr");
  let url = null;
  el.querySelector(".sess-play").onclick = async e => {
    const b = e.currentTarget; b.disabled = true;
    try {
      if (!url) {
        const q = new URLSearchParams({text: p.text, speed: "0.7"});
        if (p.voice) q.set("voice", p.voice);
        url = URL.createObjectURL(await (await api("/api/speak?" + q, null, "GET")).blob());
      }
      await new Audio(url).play();
    } catch (err) {
      corr.innerHTML = `<p class="hint" role="alert">Звук не загрузился: ${esc(err.message)}</p>`;
    } finally { b.disabled = false; }
  };
  input.addEventListener("input", () => setPrimary("Kontrolli", "проверить", !!input.value.trim()));
  input.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); primary().click(); } });
  const check = async () => {
    input.readOnly = true;
    checking(true);
    let r;
    try {
      r = await (await api("/api/session/answer", {kind: "dictation", token: p.token, given: input.value})).json();
    } catch (e) {
      checking(false); input.readOnly = false;
      corr.innerHTML = `<p class="sess-verdict" role="alert" lang="ru">${esc(e.message)}</p>`;
      setPrimary("Kontrolli", "проверить", true);
      return;
    }
    checking(false);
    if (run !== S.run) return;
    mark(r.correct ? "right" : "wrong");
    corr.innerHTML = `<p class="sess-verdict ${r.correct ? "sess-ok" : "sess-no"}">${markIcon(r.correct ? "check" : "x")}${r.correct
        ? glossed("Õige", "верно") : glossed(`${r.matched}/${r.total} sõna`, `${r.matched} из ${r.total} слов`)}</p>
      <p class="sess-dict" lang="et">${r.words.map(w => w.ok ? `<span>${esc(w.target)}</span>`
        : `<mark class="sess-missed-word">${esc(w.target)}</mark>`).join(" ")}</p>`;
    setChecked(CHECKED_BY_CODE);
    setPrimary("Edasi", "дальше");
    S.unit = {primary: () => advance(run)};
    setSkip(false);
    loadRail();
    primary().focus({preventScroll: true});
  };
  setPrimary("Kontrolli", "проверить", false);
  S.unit = {primary: check, nudge: () => input.focus(), skip: () => { mark("skipped"); advance(run); }};
  setSkip(true);
}


// ── Speaking: repeat after the recording, then answer ──────────────
let asrReady = null;
async function canHear() {
  if (!(window.isSecureContext && navigator.mediaDevices && typeof MediaRecorder !== "undefined")) return false;
  asrReady ??= api("/api/asr", null, "GET").then(r => r.json()).then(a => !!a.ready).catch(() => false);
  return asrReady;
}

function shadowUnit(root, said, run) {
  const text = said.text;
  root.innerHTML = `<div class="sess-shadow">
    <p class="sess-instr" lang="ru">Послушай и повтори вслух.</p>
    <p class="prompt sess-say-line" lang="et">${esc(text)}</p>
    ${said.attribution ? `<p class="attrib" lang="et">${esc(said.attribution)}</p>` : ""}
    <div class="row"><button class="ghost sess-play" type="button" lang="et">${icon("speaker-high", {cls: "btn-ico"})}Kuula <span class="ru" lang="ru">прослушать</span></button>
      <input class="sess-heard" type="text" lang="et" aria-label="Mida kuuldi — что распознано" readonly hidden></div>
    <div class="sess-corr" aria-live="polite"><p class="hint" lang="ru">Повторение не оценивается: это тренировка слуха и произношения.</p></div></div>`;
  root.querySelector(".sess-play").onclick = e => speakWord(text, m => root.querySelector(".sess-corr").insertAdjacentHTML("beforeend", `<p class="hint">${esc(m)}</p>`));
  canHear().then(ok => {
    if (!ok || run !== S.run) return;
    const heard = root.querySelector(".sess-heard");
    heard.hidden = false;
    heard.readOnly = false;
    addMic(root.querySelector(".row"), heard, "");
  });
  setPrimary("Edasi", "дальше");
  S.unit = {primary: () => advance(run)};
}

function speakTask(root, task, level, run) {
  root.innerHTML = `<div class="sess-item sess-speak" data-dock-task>
    <p class="sess-instr" lang="ru">${esc(task.hint_ru)}</p>
    <p class="prompt sess-say-line" lang="et">${esc(task.question)}</p>
    <label class="sess-field" lang="et">Sinu vastus <span class="ru" lang="ru">скажи в микрофон или напиши; проверь распознанный текст</span>
      <textarea class="sess-answer" rows="4" lang="et" ${ANSWER_FIELD}></textarea></label>
    <div class="sess-corr" aria-live="polite"></div></div>`;
  const text = root.querySelector("textarea"), corr = root.querySelector(".sess-corr");
  canHear().then(ok => { if (ok && run === S.run) addMic(root.querySelector(".sess-field"), text, ""); });
  text.addEventListener("input", () => setPrimary("Kinnita", "это мой ответ", !!text.value.trim()));
  const confirm = async () => {
    text.readOnly = true;
    checking(true);
    let code;
    try {
      code = await (await api("/api/speaking/feedback", {transcript: text.value, question: task.question})).json();
    } catch (e) {
      checking(false); text.readOnly = false;
      corr.innerHTML = `<p class="sess-verdict" role="alert" lang="ru">${esc(e.message)}</p>`;
      setPrimary("Kinnita", "это мой ответ", true);
      return;
    }
    checking(false);
    if (run !== S.run) return;
    const unknown = Math.round((code.signals?.unknown_share || 0) * 100);
    corr.innerHTML = `<p class="sess-verdict" lang="et">${glossed("Kood loendas", "что посчитал код")}</p>
      <p lang="ru">${ruCount(code.words, ["слово", "слова", "слов"])}${code.signals && "unknown_share" in code.signals
        ? `; слов, которых Vabamorf не знает: ${unknown}%` : ""}. Говорение не оценивается.</p>
      <div class="sess-model" aria-busy="true"><p class="loading-note" lang="et">Laadin… <span class="ru" lang="ru">загружаю комментарий модели</span></p></div>
      <p class="hint"><a href="#speak" lang="et">Vestlus <span class="ru" lang="ru">поговорить дальше с моделью-собеседником</span></a></p>`;
    setPrimary("Edasi", "дальше");
    S.unit = {primary: () => advance(run)};
    primary().focus({preventScroll: true});
    feedback(corr.querySelector(".sess-model"), "raakimine", text.value, level, task.question);
  };
  setPrimary("Kinnita", "это мой ответ", false);
  S.unit = {primary: confirm, nudge: () => text.focus()};
  requestAnimationFrame(() => text.focus({preventScroll: true}));
}

/* The model's comments against HARNO's descriptors, after code's checklist. */
async function feedback(box, kind, text, level, task) {
  try {
    const f = await (await api("/api/session/feedback", {kind, text, level, task, lang: S.lang})).json();
    const points = f.points.map(p => `<li><span class="model-crit" lang="et">${esc(p.et)}</span>
      ${p.quote ? `<q lang="et">${esc(p.quote)}</q>` : ""} <span lang="${esc(f.lang)}">${md(p.comment)}</span></li>`).join("");
    box.outerHTML = modelBlock({engine: f.engine, lang: f.lang, note: f.note || "",
      body: points ? `<ul class="model-points">${points}</ul>` : "",
      source: `<span lang="ru">Критерии HARNO:</span> <a href="${esc(f.source.url)}" target="_blank" rel="noopener" lang="et">${esc(f.source.label)}</a>`});
  } catch (e) {
    box.outerHTML = `<p class="hint" role="alert">${esc(e.message)}</p>`;
  }
}

function writingUnit(root, c, run) {
  const t = c.task;
  root.innerHTML = `<div class="sess-item sess-write" data-dock-task>
    <p class="prompt sess-task-et" lang="et">${esc(t.prompt_et)}</p>
    <p class="sess-instr" lang="ru">${esc(t.prompt_ru)}</p>
    <p class="hint" lang="ru">${esc(c.prompts_by)}</p>
    <label class="sess-field" lang="et">Sinu tekst <span class="ru" lang="ru">${t.at_least ? "не меньше" : "около"} ${t.target_words} слов</span>
      <textarea class="sess-answer" rows="7" lang="et" ${ANSWER_FIELD}></textarea></label>
    <p class="hint sess-count" lang="ru" aria-live="polite">0 слов</p>
    <div class="sess-corr" aria-live="polite"></div></div>`;
  const text = root.querySelector("textarea"), corr = root.querySelector(".sess-corr");
  text.addEventListener("input", () => {
    const n = text.value.trim() ? text.value.trim().split(/\s+/).length : 0;
    root.querySelector(".sess-count").textContent = ruCount(n, ["слово", "слова", "слов"]);
    setPrimary("Kontrolli", "проверить", n > 0);
  });
  const check = async () => {
    text.readOnly = true;
    checking(true);
    let r;
    try {
      r = await (await api("/api/session/writing", {task: t.id, text: text.value})).json();
    } catch (e) {
      checking(false); text.readOnly = false;
      corr.innerHTML = `<p class="sess-verdict" role="alert" lang="ru">${esc(e.message)}</p>`;
      setPrimary("Kontrolli", "проверить", true);
      return;
    }
    checking(false);
    if (run !== S.run) return;
    const item = (ok, et, ru) => `<li data-ok="${ok}">${markIcon(ok ? "check" : "x")}${glossed(et, ru)}</li>`;
    corr.innerHTML = `<p class="sess-verdict" lang="et">${glossed("Koodi kontroll-leht", "что проверил код — это не оценка")}</p>
      <ul class="sess-checklist">
        ${item(r.long_enough, `${r.words} sõna`, `${r.at_least ? "нужно не меньше" : "нужно около"} ${r.target_words}`)}
        ${r.points.map(p => item(p.found, p.et, p.ru)).join("")}
        ${r.opening === null ? "" : item(r.opening, "Pöördumine", "обращение")}
        ${r.closing === null ? "" : item(r.closing, "Lõpetus", "завершение")}
        ${item(!r.errors, r.errors ? `${r.errors} kohta` : "Vigu ei leitud", r.errors ? "места, к которым у проверки есть вопросы" : "проверка Vabamorf и EKK")}
      </ul>
      ${r.findings?.length ? `<ul class="sess-findings">${r.findings.map(f => `<li lang="ru"><del lang="et">${esc(f.wrong || "")}</del>${f.correct
        ? ` <span lang="et">${esc(f.correct)}</span>` : ""} ${md(f.why || "")}</li>`).join("")}</ul>` : ""}
      <div class="sess-model" aria-busy="true"><p class="loading-note" lang="et">Laadin… <span class="ru" lang="ru">загружаю комментарий модели</span></p></div>`;
    setChecked(`<span lang="et">Kontrollis kood <span class="ru" lang="ru">длина, пункты задания, Vabamorf и EKK</span></span>`);
    setPrimary("Edasi", "дальше");
    S.unit = {primary: () => advance(run)};
    feedback(corr.querySelector(".sess-model"), "kirjutamine", text.value, c.level, t.prompt_et);
  };
  setPrimary("Kontrolli", "проверить", false);
  S.unit = {primary: check, nudge: () => text.focus()};
  requestAnimationFrame(() => text.focus({preventScroll: true}));
}


// ── A set answered whole: the unit check and a test-out ────────────
/* Kursus' test-out and unit check, and a unit's fifth session: answered item
   by item with `itemUnit` (`set`), handed in whole with the last. */
const answers = [];

async function setResult(root, set, run) {
  root.innerHTML = `<p class="loading-note" lang="et">Kontrollin… <span class="ru" lang="ru">проверяю</span></p>`;
  setPrimary("Kontrollin…", "проверяю", false);
  let r;
  try {
    const url = set.kind === "unit" ? `/api/units/${encodeURIComponent(set.unit)}/check`
      : `/api/testout/${encodeURIComponent(set.topic)}`;
    r = await (await api(url, {seed: set.seed, given: answers.slice()})).json();
  } catch (e) {
    if (run !== S.run) return;
    root.innerHTML = `<div class="banner recoverable-error" role="alert">Не проверено: ${esc(e.message)}</div>`;
    setPrimary("Proovi uuesti", "отправить ещё раз");
    S.unit = {primary: () => setResult(root, set, run)};
    return;
  }
  if (run !== S.run) return;
  const items = r.items || [];
  items.forEach((row, k) => {
    const at = S.units.findIndex((u, n) => u.bead && S.units.slice(0, n + 1).filter(x => x.bead).length === k + 1);
    if (at >= 0) S.marks[at] = row.correct ? "right" : "wrong";
  });
  const right = items.filter(row => row.correct).length;
  S.tally = {asked: items.length, correct: right, skipped: 0};
  paintBeads();
  const names = Object.fromEntries((set.parts || []).map(p => [p.topic, p.et]));
  const passed = r.passed;
  const SAID = {unit: [["Veel mitte", "пока не сдан — ничего не потеряно"], ["Ühik kontrollitud", "блок проверен"]],
                topic: [[`${r.correct}/${r.asked}`, "тема остаётся в пути — ничего не потеряно"],
                        [`${r.correct}/${r.asked}`, "тема засчитана"]]};
  const [headEt, headRu] = SAID[set.kind === "unit" ? "unit" : "topic"][Number(!!passed)];
  root.innerHTML = `<div class="sess-result">
    <p class="sess-verdict${passed ? " sess-ok" : ""}">${markIcon(passed ? "check" : "x")}${glossed(headEt, headRu)}</p>
    ${r.parts ? `<ul class="sess-parts">${r.parts.map(p => `<li lang="et">${esc(names[p.topic] || p.topic)}: ${p.correct}/${p.asked}${p.passed ? " ✓" : ""}</li>`).join("")}</ul>` : ""}
    <ol class="sess-review">${items.map(row => `<li class="prompt" lang="et">${row.correct ? markIcon("check") : markIcon("x")}${esc((row.prompt || "").split("____")[0])}${
      interlinear((row.answer || "").split(" ~ ")[0], {lemma: ""}, {state: row.correct ? "right" : "revealed"})}${esc((row.prompt || "").split("____")[1] || "")}${
      row.correct ? "" : ` <span class="sess-yours"><span class="sr-only" lang="ru">твой ответ: </span><del>${esc(row.given || "")}</del></span>`}</li>`).join("")}</ol></div>`;
  setChecked(CHECKED_BY_CODE);
  refreshDueBadge(); loadRail();
  setPrimary("Edasi", "дальше");
  S.unit = {primary: () => advance(run)};
}

async function runCheck() {
  const run = ++S.run;
  const check = S.check;
  S.session = null; S.step = {id: "kontroll", et: "Kontroll", ru: "проверка"};
  loading();
  $("#sessLine").innerHTML = "";
  title(check.et || "Kontroll", check.kind === "unit" ? "проверка блока" : "проверить знания");
  $("#sessStep").innerHTML = glossed(check.kind === "unit" ? "Ühiku kontroll" : "Kontrolli teadmisi",
                                     check.kind === "unit" ? "по пять заданий на тему" : "пять заданий, нужно все пять");
  let set;
  try {
    const url = check.kind === "unit" ? `/api/units/${encodeURIComponent(check.unit)}/check`
      : `/api/testout/${encodeURIComponent(check.topic)}`;
    set = await (await api(url, null, "GET")).json();
  } catch (e) {
    if (run !== S.run) return;
    return failed(e.message, runCheck);
  }
  if (run !== S.run) return;
  S.content = {glosses: set.glosses || {}};
  S.units = set.items.map((it, i) => ({bead: true, render: (root, r) => itemUnit(root, it,
    {kind: "item", glosses: set.glosses || {}, set: {index: i, size: set.items.length}}, r)}));
  S.units.push({render: (root, r) => setResult(root, {kind: check.kind, unit: check.unit, topic: check.topic,
                                                       seed: set.seed, parts: set.parts}, r)});
  S.units.push({render: (root, r) => { location.hash = "#course"; }});
  S.pos = 0; S.marks = []; S.tally = {asked: 0, correct: 0, skipped: 0};
  answers.length = 0;
  show(run);
}


// ── The end of a session ───────────────────────────────────────────
async function finish(run) {
  if (run !== S.run) return;
  S.step = null;
  paintLine();
  $("#sessBeads").innerHTML = "";
  $("#sessWhy").hidden = true;
  $("#sessStep").innerHTML = glossed(S.mode === "topic" ? "Tehtud" : "Tänane tund on tehtud",
                                     S.mode === "topic" ? "готово" : "занятие на сегодня пройдено");
  let next = S.next, done = 0, goal = null;
  try {
    const t = await (await api("/api/session", null, "GET")).json();
    if (S.mode !== "topic") next = t.next;
    done = t.sessions_done || 0;
    goal = t.goal;
  } catch { /* the summary stands without the next task */ }
  if (run !== S.run) return;
  const rows = S.summary.filter(s => s.asked || s.skipped).map(s => `<li lang="et">${glossed(s.et, s.ru)}
    <span class="sess-sum-count">${s.correct}/${s.asked}${s.skipped ? ` <span class="hint" lang="ru">пропущено ${s.skipped}</span>` : ""}</span></li>`).join("");
  const alt = (next?.alternatives || []).map(a => `<li><a href="${esc(a.href)}" lang="et">${glossed(a.et, a.ru)}</a>
    <p class="tana-alt-why" lang="ru">${esc(a.why_ru)}</p></li>`).join("");
  const isFirst = S.mode === "today" && done === 1;
  body(`<div class="sess-end">
    ${rows ? `<ul class="sess-sum">${rows}</ul>` : ""}
    ${S.missed.length ? `<h4 lang="et">${glossed("Vead", "ошибки — правильная форма под словом")}</h4>
      <ul class="sess-missed">${S.missed.slice(0, 5).map(m => `<li class="prompt" lang="et">${m}</li>`).join("")}</ul>
      ${S.missed.length > 5 ? `<details class="rule-more"><summary lang="et">Veel <span class="ru" lang="ru">ещё ${S.missed.length - 5}</span></summary>
        <ul class="sess-missed">${S.missed.slice(5).map(m => `<li class="prompt" lang="et">${m}</li>`).join("")}</ul></details>` : ""}` : ""}
    ${next ? `<p class="sess-next-why" lang="ru">${esc(next.primary.why_ru)}</p>` : ""}
    ${alt ? `<h4 lang="et">${glossed("Või", "или")}</h4><ul class="tana-alt">${alt}</ul>` : ""}
    ${isFirst ? afterFirstHtml(goal) : ""}
  </div>`);
  fitLines();
  if (isFirst) wireAfterFirst(goal);
  setChecked(""); setSkip(false);
  if (next) {
    setPrimary(next.primary.et, next.primary.ru);
    S.unit = {primary: () => { location.hash = next.primary.href; }};
  } else {
    setPrimary("Täna", "на сегодня");
    S.unit = {primary: () => { location.hash = "#path"; }};
  }
  S.session = null;
  started = "";
  refreshDueBadge(); loadRail();
  $("#sessStep").focus({preventScroll: true});
}

/* After the first session, never before (ADR-0009): the exam sitting and the
   reminders. */
function afterFirstHtml(goal) {
  const exam = goal === "a2" || goal === "b1";
  return `<section class="sess-after-first" aria-labelledby="afterFirstH">
    <h4 id="afterFirstH" lang="et">${glossed("Järgmiseks", "на будущее")}</h4>
    ${exam ? `<p lang="ru">Если ты уже знаешь дату экзамена, выбери её: подготовка будет учитывать срок.</p>
      <div class="row"><select id="afterSitting" lang="et" aria-label="Eksami aeg — дата экзамена"></select>
      <button class="ghost" id="afterSittingSave" type="button" lang="et">Salvesta <span class="ru" lang="ru">сохранить</span></button></div>
      <p class="hint" id="afterSittingNote" lang="ru" aria-live="polite"></p>` : ""}
    <p lang="ru">Напоминания можно включить в разделе <a href="#status" lang="et">Edenemine</a>: они говорят только, что пора повторить или что занятия давно не было.</p>
  </section>`;
}

async function wireAfterFirst(goal) {
  const select = $("#afterSitting");
  if (!select) return;
  const level = goal === "b1" ? "B1" : "A2";
  try {
    const spec = await (await api(`/api/exam/${level}`, null, "GET")).json();
    const sittings = spec.sittings || spec.upcoming || [];
    select.innerHTML = `<option value="" lang="ru">дата пока неизвестна</option>` + sittings.map(s =>
      `<option value="${esc(s.sitting)}">${esc(s.sitting)}${s.registration_open === false ? " — регистрация закрыта" : ""}</option>`).join("");
  } catch { select.innerHTML = `<option value="" lang="ru">дата пока неизвестна</option>`; }
  $("#afterSittingSave").onclick = async () => {
    try {
      await api("/api/goal", {level, sitting: select.value || null});
      $("#afterSittingNote").textContent = "Сохранено.";
    } catch (e) { $("#afterSittingNote").textContent = e.message; }
  };
}
