/* Two optional starting questions. They tune recommendations only: the answers
   never skip the curriculum, award mastery or claim a CEFR result. */

import {$, api, esc} from "./core.js";
import {icon} from "./icons.js";
import {goToPlace} from "./router.js";
import {setExamLevel} from "./state.js";

const LEVELS = [
  ["a0", "A0", "Alustan nullist", "Начинаю с нуля"],
  ["a1", "A1", "Tean mõnda sõna", "Знаю отдельные слова и фразы"],
  ["a1-a2", "A1–A2", "Saan lihtsast jutust aru", "Понимаю простые бытовые фразы"],
  ["a2", "A2", "Räägin tuttavatel teemadel", "Могу говорить о знакомых темах"],
  ["a2-b1", "A2–B1", "Liigun B1 poole", "Готовлюсь двигаться к B1"],
];

const FOCUSES = [
  ["path", "path", "Rada", "Системно по темам"],
  ["words", "translate", "Sõnavara", "Слова и чтение"],
  ["speaking", "microphone", "Rääkimine", "Слушать и говорить"],
  ["exam", "flower", "Eksam", "Подготовка к экзамену"],
];

const TARGETS = {path: "path", words: "sonad", speaking: "speak", exam: "exam"};
const LEVEL_FILTER = {
  a0: "A1", a1: "A1", "a1-a2": "A1,A2", a2: "A1,A2", "a2-b1": "B1",
  unsure: "A1,A2,B1",
};

let me = null;
let step = 1;
let editing = false;
let saving = false;
let draft = {start_band: "", focus: "path"};

function recommendationText(band) {
  return ({a0: "A1", a1: "A1", "a1-a2": "A1–A2", a2: "A1–A2",
    "a2-b1": "B1", unsure: "A1–B1"})[band] || "A1–B1";
}

function syncRecommendation(onboarding) {
  document.querySelectorAll(".nav-recommend").forEach(mark => mark.remove());
  document.querySelectorAll("nav[data-mode-nav] button.recommended").forEach(button => {
    button.classList.remove("recommended");
    button.setAttribute("aria-label", button.dataset.baseLabel || button.getAttribute("aria-label") || "");
  });
  if (!onboarding || onboarding.skipped) return;

  const target = TARGETS[onboarding.focus] || "path";
  const button = document.querySelector(`nav[data-mode-nav] button[data-tab="${target}"]`);
  if (button) {
    button.dataset.baseLabel = button.dataset.baseLabel || button.getAttribute("aria-label") || "";
    button.classList.add("recommended");
    button.setAttribute("aria-label", `${button.dataset.baseLabel}. Sulle soovitatud — рекомендовано вам`);
    button.insertAdjacentHTML("beforeend", `<span class="nav-recommend" title="Sulle soovitatud — рекомендовано вам">
      ${icon("sparkle")}<span>Sulle</span></span>`);
  }

  const filter = LEVEL_FILTER[onboarding.start_band] || "A1,A2,B1";
  const free = $("#freeLevel");
  if (free && [...free.options].some(option => option.value === filter)) free.value = filter;
  const voc = $("#vocLevel");
  const vocLevel = filter === "B1" ? "B1" : filter === "A1,A2" ? "A2" : "A1";
  if (voc) voc.value = vocLevel;
  const text = `Soovitus: ${recommendationText(onboarding.start_band)}`;
  for (const id of ["#freeRecommendation", "#vocRecommendation"]) {
    const mark = $(id);
    if (mark) { mark.textContent = text; mark.hidden = false; }
  }
}

function scene() {
  return `<div class="onboarding-scene" aria-hidden="true">
    ${icon("path", {cls: "onboarding-path"})}
    <span></span><span></span><span></span>
  </div>`;
}

function progress() {
  return `<div class="onboarding-progress" aria-label="${step} из 2">
    <span class="done"></span><span class="${step === 2 ? "done" : ""}"></span>
  </div>`;
}

function levelScreen() {
  return `${scene()}${progress()}
    <div class="onboarding-copy">
      <h2 lang="et">Kust alustame? <span class="ru" lang="ru">с чего начнём?</span></h2>
      <p lang="ru">Это быстрая самооценка, не тест и не подтверждённый уровень CEFR. Она только настроит первые рекомендации.</p>
    </div>
    <fieldset class="onboarding-levels">
      <legend class="sr-only">Praegune algus — текущая точка старта</legend>
      ${LEVELS.map(([value, level, et, ru]) => `<label>
        <input type="radio" name="start-band" value="${value}"${draft.start_band === value ? " checked" : ""}>
        <strong>${level}</strong><span lang="et">${et}<small lang="ru">${ru}</small></span>
      </label>`).join("")}
    </fieldset>
    <div class="onboarding-actions">
      <button class="linky onboarding-skip" type="button" data-skip lang="et">${editing ? "Loobu" : "Praegu mitte"} <span class="ru" lang="ru">${editing ? "отмена" : "пропустить"}</span></button>
      <button class="go" type="button" data-next${draft.start_band ? "" : " disabled"} lang="et">Edasi <span class="ru" lang="ru">дальше</span></button>
    </div>`;
}

function focusScreen() {
  return `${scene()}${progress()}
    <div class="onboarding-copy">
      <h2 lang="et">Mis sind tagasi toob <span class="ru" lang="ru">что хочется делать?</span></h2>
      <p lang="ru">Выберите первое направление. Все разделы останутся доступны, а выбор можно изменить в профиле.</p>
    </div>
    <fieldset class="onboarding-focus">
      <legend class="sr-only">Esimene suund — первое направление</legend>
      ${FOCUSES.map(([value, mark, et, ru]) => `<label>
        <input type="radio" name="focus" value="${value}"${draft.focus === value ? " checked" : ""}>
        ${icon(mark)}<span lang="et">${et}<small lang="ru">${ru}</small></span>
      </label>`).join("")}
    </fieldset>
    <p class="onboarding-error" role="alert" hidden></p>
    <div class="onboarding-actions">
      <button class="ghost" type="button" data-back lang="et">Tagasi <span class="ru" lang="ru">назад</span></button>
      <button class="go" type="button" data-save lang="et">Näita minu algust <span class="ru" lang="ru">показать старт</span></button>
    </div>`;
}

function render() {
  const dialog = $("#onboardingSheet");
  if (!dialog) return;
  dialog.innerHTML = step === 1 ? levelScreen() : focusScreen();
  dialog.querySelectorAll('input[type="radio"]').forEach(input => input.addEventListener("change", () => {
    if (input.name === "start-band") draft.start_band = input.value;
    else draft.focus = input.value;
    render();
    dialog.querySelector(`input[value="${input.value}"]`)?.focus();
  }));
  dialog.querySelector("[data-next]")?.addEventListener("click", () => { step = 2; render(); });
  dialog.querySelector("[data-back]")?.addEventListener("click", () => { step = 1; render(); });
  dialog.querySelector("[data-skip]")?.addEventListener("click", skip);
  dialog.querySelector("[data-save]")?.addEventListener("click", save);
}

async function save() {
  if (saving || !draft.start_band || !draft.focus) return;
  saving = true;
  const dialog = $("#onboardingSheet");
  const button = dialog.querySelector("[data-save]");
  if (button) { button.disabled = true; button.textContent = "Salvestan…"; }
  try {
    me = await api("/api/me/onboarding", {...draft, skipped: false}).then(response => response.json());
    syncRecommendation(me.onboarding);
    dialog.close();
    if (editing) goToPlace("profile");
    else {
      if (draft.focus === "exam") {
        const level = draft.start_band === "a2-b1" ? "B1" : "A2";
        setExamLevel(level);
        document.querySelectorAll("#tab-exam .levels button").forEach(tab =>
          tab.setAttribute("aria-selected", String(tab.dataset.level === level)));
      }
      goToPlace(TARGETS[draft.focus] || "path");
    }
  } catch (error) {
    const out = dialog.querySelector(".onboarding-error");
    if (out) { out.textContent = error.message; out.hidden = false; }
    if (button) button.disabled = false;
  } finally { saving = false; }
}

async function skip() {
  const dialog = $("#onboardingSheet");
  if (editing) { dialog.close(); return; }
  if (saving) return;
  saving = true;
  try {
    me = await api("/api/me/onboarding", {
      start_band: "unsure", focus: "path", skipped: true,
    }).then(response => response.json());
    syncRecommendation(me.onboarding);
    dialog.close();
  } catch (error) {
    step = 2;
    render();
    const out = dialog.querySelector(".onboarding-error");
    if (out) { out.textContent = error.message; out.hidden = false; }
  } finally { saving = false; }
}

async function open({edit = false} = {}) {
  const dialog = $("#onboardingSheet");
  if (!dialog) return;
  if (!me || edit) {
    try { me = await api("/api/me").then(response => response.json()); }
    catch { return; }
  }
  if (me.scope === "guest") return;
  editing = edit;
  step = 1;
  draft = {
    start_band: me.onboarding?.start_band === "unsure" ? "" : (me.onboarding?.start_band || ""),
    focus: me.onboarding?.focus || "path",
  };
  render();
  if (!dialog.open) dialog.showModal();
}

export async function maybeShowOnboarding({force = false} = {}) {
  try {
    me = await api("/api/me").then(response => response.json());
    syncRecommendation(me.onboarding);
    // The origin's unauthenticated local owner has no durable account identity;
    // show automatically only once the front door provides a permanent email.
    if (me.scope !== "guest" && !me.onboarding && (force || me.email)) await open();
  } catch { /* A starting suggestion must never block the app. */ }
}

document.addEventListener("click", event => {
  if (event.target.closest("#editOnboarding")) open({edit: true});
});

$("#onboardingSheet")?.addEventListener("cancel", event => {
  event.preventDefault();
  skip();
});

window.addEventListener("eesti:identity-changed", () => maybeShowOnboarding({force: true}));
