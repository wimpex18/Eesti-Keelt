/* Onboarding (ADR-0009): the first task within a minute. Four questions —
   the explanation language, the goal, the starting point, sessions a week —
   then straight into today's session. The exam sitting and reminders are asked
   after the first session, never before (`session.js`).

   Starting choices are navigation. The placement check asks at most twelve
   items, graded by the server from their tokens, and places by unit; it masters
   nothing (`eesti/session.py`). */
import {$, api, attribHtml, esc, setLabel, wrongVerdict} from "./core.js";
import {goToPlace} from "./router.js";

/* The default explanation language: the first of the browser's languages that
   is Ukrainian, Russian or English, else English (PRODUCT.md). Location is
   never used; a saved choice always wins. */
export function defaultLanguage(list = navigator.languages || [navigator.language || ""]) {
  for (const tag of list) {
    const primary = String(tag || "").toLowerCase().split("-")[0];
    if (["uk", "ru", "en"].includes(primary)) return primary;
  }
  return "en";
}

/* What the choice means today, said in the chosen language (`session.LANGUAGES`
   on the server): the app's own explanations are Russian until the catalogue
   has the others; the model's already answer in the chosen language. */
let languageNotes = null;
async function notes() {
  if (languageNotes) return languageNotes;
  try {
    const r = await (await api("/api/session/languages", null, "GET")).json();
    languageNotes = Object.fromEntries(r.languages.map(l => [l.id, l.note]));
  } catch { languageNotes = {}; }
  return languageNotes;
}

const GOALS = [
  ["igapaev", "Igapäevaelu", "для жизни: темы курса и четыре навыка"],
  ["too", "Töö", "для работы: темы курса и деловые ситуации"],
  ["a2", "A2 eksam", "подготовка к экзамену A2"],
  ["b1", "B1 eksam", "подготовка к экзамену B1"],
];
const STAGES = [
  ["a0", "Algus", "с нуля: звуки, приветствия, числа"],
  ["a1", "A1", "знаю отдельные слова и фразы"],
  ["a2", "A2", "общаюсь на знакомые темы"],
  ["a2-b1", "B1", "двигаюсь к самостоятельному уровню"],
];
const WEEK = [2, 3, 4, 5, 6, 7];

const choice = {lang: null, goal: null, band: null, perWeek: 5, placed: null};
let busy = false;

const out = () => $("#onboardingContent");
const glossed = (et, ru) => `<span lang="et">${esc(et)} <span class="ru" lang="ru">${esc(ru)}</span></span>`;

function route(tab) {
  goToPlace(tab);
  if (location.hash !== "#" + tab) history.pushState(null, "", "#" + tab);
}

/* One question per screen: its heading takes focus, its one primary goes on. */
function frame(html) {
  out().innerHTML = html + '<p class="start-error banner" role="alert" hidden></p>';
  // Each question starts at the top of the page, as a new screen does.
  if (!$("#tab-start").hidden) window.scrollTo({top: 0});
  const heading = out().querySelector("h2");
  if (heading && !$("#tab-start").hidden) {
    heading.tabIndex = -1;
    heading.focus({preventScroll: true});
  }
}

function error(message, retry) {
  const box = out().querySelector(".start-error");
  box.hidden = false; box.textContent = message;
  if (retry) {
    const b = document.createElement("button"); b.className = "ghost"; b.lang = "et"; b.type = "button";
    b.innerHTML = '<span lang="et">Proovi uuesti <span class="ru" lang="ru">попробовать снова</span></span>';
    b.onclick = retry; box.appendChild(b);
  }
}

/* A choice among rows: radio semantics, arrows move, one Tab stop. */
function rows(name, options, chosen, legend) {
  return `<fieldset class="start-q"><legend lang="et">${legend}</legend>
    <div class="start-routes" role="radiogroup">${options.map(([id, et, ru], i) =>
      `<button aria-checked="${id === chosen}" class="start-route" data-${name}="${esc(id)}" role="radio" type="button"
        tabindex="${id === chosen || (!chosen && i === 0) ? 0 : -1}" lang="et"><strong>${esc(et)}</strong>${ru ? `<span lang="ru">${esc(ru)}</span>` : ""}</button>`).join("")}
    </div></fieldset>`;
}

function wireRows(name, onPick) {
  const buttons = [...out().querySelectorAll(`[data-${name}]`)];
  const pick = b => {
    buttons.forEach(x => { x.setAttribute("aria-checked", String(x === b)); x.tabIndex = x === b ? 0 : -1; });
    onPick(b.dataset[name]);
  };
  buttons.forEach(b => b.addEventListener("click", () => pick(b)));
  out().querySelector(".start-routes")?.addEventListener("keydown", e => {
    if (!["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft"].includes(e.key)) return;
    e.preventDefault();
    const at = buttons.indexOf(document.activeElement);
    const to = buttons[(at + (["ArrowDown", "ArrowRight"].includes(e.key) ? 1 : buttons.length - 1)) % buttons.length];
    to.focus(); pick(to);
  });
}

const nav = (label, ru, back = true) => `<div class="start-actions">
  ${back ? `<button class="quiet" data-back type="button" lang="et">Tagasi <span class="ru" lang="ru">назад</span></button>` : ""}
  <button class="go" data-primary="" data-next type="button" lang="et">${glossed(label, ru)}</button></div>`;

function wireNav(next, back, ready = () => true) {
  const go = out().querySelector("[data-next]");
  const paint = () => go.setAttribute("aria-disabled", String(!ready()));
  go.onclick = () => { if (ready()) next(); };
  out().querySelector("[data-back]")?.addEventListener("click", back);
  paint();
  return paint;
}

// ── 1. The explanation language ────────────────────────────────────
const START_MARKUP = $("#onboardingContent").innerHTML;

export function renderStart() {
  choice.lang ??= defaultLanguage();
  frame(START_MARKUP);
  $("#startLangNote").insertAdjacentHTML("afterend", nav("Edasi", "дальше", false));
  out().querySelectorAll("[data-lang]").forEach(b => {
    b.disabled = false;
    b.setAttribute("aria-checked", String(b.dataset.lang === choice.lang));
    b.tabIndex = b.dataset.lang === choice.lang ? 0 : -1;
  });
  const note = async () => {
    const chosen = choice.lang, said = (await notes())[chosen] || "";
    const n = $("#startLangNote");
    if (!n || chosen !== choice.lang) return;
    n.lang = chosen; n.textContent = said;
  };
  note();
  wireRows("lang", lang => { choice.lang = lang; note(); });
  wireNav(renderGoal, () => {});
}

// ── 2. The goal ────────────────────────────────────────────────────
function renderGoal() {
  frame(`<h2 class="page-title" lang="et">${glossed("Milleks õpid?", "для чего учишься?")}</h2>
    <p lang="ru">Все разделы доступны всегда; цель меняет, что предлагается первым.</p>
    ${rows("goal", GOALS, choice.goal, glossed("Eesmärk", "цель"))}
    ${nav("Edasi", "дальше")}`);
  let paint = () => {};
  wireRows("goal", goal => { choice.goal = goal; paint(); });
  paint = wireNav(renderStartPoint, renderStart, () => !!choice.goal);
}

// ── 3. The starting point ──────────────────────────────────────────
function renderStartPoint() {
  frame(`<h2 class="page-title" lang="et">${glossed("Kust alustad?", "с чего начнёшь?")}</h2>
    <p lang="ru">Пропущенные блоки остаются в курсе, их можно вернуть. Освоение засчитывается только проверенными ответами.</p>
    ${rows("from", [["start", "Alustan algusest", "с первого блока: звуки, приветствия, числа"],
                    ["choose", "Valin alguse", "что-то уже знаю — выберу ступень сам"],
                    ["check", "Proovin ennast", "не уверен — до 12 заданий, и начну с нужного блока"]],
           choice.from, glossed("Algus", "точка старта"))}
    ${nav("Edasi", "дальше")}`);
  let paint = () => {};
  wireRows("from", from => { choice.from = from; paint(); });
  paint = wireNav(() => {
    if (choice.from === "start") { choice.band = "a0"; choice.placed = null; renderWeek(); }
    else if (choice.from === "choose") renderStages();
    else { choice.placed = null; placementAnswers = []; nextProbe(); }
  }, renderGoal, () => !!choice.from);
}

function renderStages() {
  frame(`<h2 class="page-title" lang="et">${glossed("Vali oma algus", "выбери ступень")}</h2>
    <p lang="ru">Блоки ступеней до выбранной будут отмечены «пропущено». Их можно вернуть в курсе.</p>
    ${rows("band", STAGES, choice.band, glossed("Aste", "ступень"))}
    ${nav("Edasi", "дальше")}`);
  let paint = () => {};
  wireRows("band", band => { choice.band = band; paint(); });
  paint = wireNav(renderWeek, renderStartPoint, () => !!choice.band);
}

// ── The placement check: at most twelve items, placing by unit ─────
let placementAnswers = [];

async function nextProbe() {
  frame(`<h2 class="page-title" lang="et">${glossed("Proovin ennast", "короткая проверка")}</h2>
    <p role="status" lang="ru">Подбираю задания…</p>`);
  let r;
  try {
    r = await (await api("/api/session/placement", {answers: placementAnswers})).json();
  } catch (e) { error(e.message, nextProbe); return; }
  if (r.done) { choice.placed = r; choice.band = "unsure"; showPlacement(r); return; }
  frame(`<h2 class="page-title" lang="et">${glossed(`${r.asked + 1}.–${r.asked + r.items.length}. ülesanne`,
      `задания блока «${r.et}»; всего не больше 12`)}</h2>
    <p lang="ru">Проверяются только эти задания; это не экзамен CEFR и не оценка уровня.</p>
    <form id="placementForm">${r.items.map((it, i) => `<label class="placement-task" lang="et">${esc(it.prompt)}
      <span class="hint">${esc([it.lemma, it.label].filter(Boolean).join(", "))}</span>
      <input name="answer${i}" aria-label="Vastus ${i + 1} — ответ" lang="et" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false">${attribHtml(it)}</label>`).join("")}
      <div class="start-actions"><button class="quiet" data-stop type="button" lang="et">Lõpeta siin <span class="ru" lang="ru">закончить здесь</span></button>
      <button class="go" data-primary="" type="submit" lang="et">${glossed("Kontrolli", "проверить")}</button></div></form>`);
  out().querySelector("[data-stop]").onclick = () => finishPlacement();
  out().querySelector("form").onsubmit = event => {
    event.preventDefault();
    const inputs = [...out().querySelectorAll("form input")];
    inputs.forEach((input, i) => placementAnswers.push({unit: r.unit, token: r.items[i].token, given: input.value}));
    nextProbe();
  };
  out().querySelector("form input")?.focus({preventScroll: true});
}

async function finishPlacement() {
  // Stopped early: what was answered so far places, conservatively.
  try {
    const r = await (await api("/api/session/placement", {answers: placementAnswers})).json();
    if (r.done) { choice.placed = r; choice.band = "unsure"; showPlacement(r); return; }
  } catch (e) { error(e.message); return; }
  choice.placed = {start: "tere", start_n: 1, start_et: "Tere!", review: [], skip: []};
  choice.band = "unsure";
  showPlacement(choice.placed);
}

function showPlacement(r) {
  const review = (r.review || []).map(row => `<li lang="et">${row.correct ? "✓" : ""}
    ${esc(row.prompt.replace("____", row.correct ? row.given : row.expected.split(" ~ ")[0]))}
    ${row.correct ? "" : `<span class="verdict no">${wrongVerdict(row.given, row.expected, "")}</span>`}</li>`).join("");
  frame(`<h2 class="page-title" lang="et">${glossed("Sinu algus", "твоя точка старта")}</h2>
    <p lang="ru">Начнёшь с блока ${r.start_n}: <span lang="et">${esc(r.start_et)}</span>.
      ${r.skip?.length ? "Блоки до него будут отмечены «пропущено» — их можно вернуть в курсе." : ""}</p>
    ${review ? `<ul class="placement-review">${review}</ul>` : ""}
    <p class="hint" lang="ru">Проверка касается грамматики; уровень CEFR не подтверждён.</p>
    ${nav("Edasi", "дальше")}`);
  wireNav(renderWeek, renderStartPoint);
}

// ── 4. Sessions a week ─────────────────────────────────────────────
function renderWeek() {
  frame(`<h2 class="page-title" lang="et">${glossed("Mitu korda nädalas?", "сколько занятий в неделю?")}</h2>
    <p lang="ru">Одно занятие — 20–30 минут: повторение, правило, упражнения, слова, слух, речь и короткая проверка. Блок курса — неделя, пять занятий.</p>
    <div class="seg start-week" role="radiogroup" aria-label="Tunde nädalas — занятий в неделю">${WEEK.map(n =>
      `<button type="button" role="radio" aria-checked="${n === choice.perWeek}" tabindex="${n === choice.perWeek ? 0 : -1}" data-week="${n}">${n}</button>`).join("")}</div>
    ${nav("Alusta", "начать первое задание")}`);
  const buttons = [...out().querySelectorAll("[data-week]")];
  const pick = b => {
    buttons.forEach(x => { x.setAttribute("aria-checked", String(x === b)); x.tabIndex = x === b ? 0 : -1; });
    choice.perWeek = Number(b.dataset.week);
  };
  buttons.forEach(b => b.addEventListener("click", () => pick(b)));
  out().querySelector(".start-week").addEventListener("keydown", e => {
    if (!["ArrowRight", "ArrowLeft", "ArrowDown", "ArrowUp"].includes(e.key)) return;
    e.preventDefault();
    const at = buttons.indexOf(document.activeElement);
    const to = buttons[(at + (["ArrowRight", "ArrowDown"].includes(e.key) ? 1 : buttons.length - 1)) % buttons.length];
    to.focus(); pick(to);
  });
  wireNav(save, choice.from === "choose" ? renderStages : renderStartPoint);
}

async function save() {
  if (busy) return; busy = true;
  const go = out().querySelector("[data-next]");
  go.setAttribute("aria-disabled", "true");
  setLabel(go, "Salvestan…");
  try {
    const exam = choice.goal === "a2" || choice.goal === "b1";
    const lane = exam ? "exam" : "path";
    await api("/api/me/onboarding", {start_band: choice.band || "a0", focus: lane,
      navigate: choice.band !== "unsure", explanation_language: choice.lang, skipped: false});
    // Every model call answers in it from now on (`modeltext.explanationLanguage`).
    window.dispatchEvent(new CustomEvent("eesti:language", {detail: choice.lang}));
    await api("/api/session/goal", {goal: choice.goal, per_week: choice.perWeek});
    if (choice.placed) await api("/api/session/placement", {answers: placementAnswers, apply: true});
    if (exam) {
      try { localStorage.setItem("examLevel", choice.goal.toUpperCase()); } catch { /* private mode */ }
    }
    // The first task within a minute: straight into today's session.
    route("session");
  } catch (e) {
    error(e.message, save);
    go.setAttribute("aria-disabled", "false");
    setLabel(go, "Alusta");
  } finally { busy = false; }
}

export async function maybeShowOnboarding({force = false} = {}) {
  try {
    const me = await api("/api/me", null, "GET").then(r => r.json());
    if (me.onboarding?.explanation_language) choice.lang = me.onboarding.explanation_language;
    // The router already drew the start screen; redrawing would undo a step taken meanwhile.
    if (!force && !$("#tab-start").hidden) return;
    if (location.hash === "#start" || force || !me.onboarding && location.hash === "#path") {
      renderStart(); route("start");
    }
  } catch { /* Core skills remain reachable when the profile cannot load. */ }
}
window.addEventListener("eesti:place", event => { if (event.detail === "start") renderStart(); });
document.addEventListener("click", event => { if (event.target.closest("#editOnboarding")) route("start"); });
window.addEventListener("eesti:identity-changed", () => maybeShowOnboarding({force: true}));
