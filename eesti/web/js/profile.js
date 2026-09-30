/* Identity and the evidence behind a learner's progress. */

import {$, api, esc, ruCount} from "./core.js";
import {icon} from "./icons.js";
import {retryableError, rhythmHtml, sealsHtml} from "./chrome.js";

let currentMe = null;
let authInfo = {scope: "owner", signup_open: false, available: false};
let sealLevel = "A1";
let authView = "login";
let resetNotice = "";

const LEVELS = ["A1", "A2", "B1"];
const START_BAND_NAMES = {
  a0: "A0", a1: "A1", "a1-a2": "A1–A2", a2: "A2", "a2-b1": "A2–B1",
  unsure: "pole valitud",
};
const FOCUS_NAMES = {
  path: "Rada", words: "Sõnavara", speaking: "Rääkimine", exam: "Eksam",
};

function date(value) {
  if (!value) return '<span lang="et">Veel mitte <span class="ru" lang="ru">пока нет</span></span>';
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf())
    ? '<span lang="et">Veel mitte <span class="ru" lang="ru">пока нет</span></span>'
    : `<span lang="ru">${esc(parsed.toLocaleDateString("ru", {
      day: "numeric", month: "long", year: "numeric",
    }))}</span>`;
}

function scopeName(scope) {
  return ({owner: "Põhikonto", learner: "Õppija", guest: "Külaline"})[scope] || "Külaline";
}

function scopeDescription(scope) {
  return ({
    owner: "основной аккаунт; прогресс сохраняется",
    learner: "отдельный аккаунт; прогресс сохраняется",
    guest: "временная гостевая песочница",
  })[scope] || "временная гостевая песочница";
}

function needsFirstAccount() {
  return currentMe?.scope === "owner" && authInfo.signup_open && !authInfo.email;
}

function count(value, words) { return ruCount(Number(value) || 0, words); }

function profileRows(me) {
  const level = me.level || {};
  const goal = level.goal;
  const checkpointText = (level.checkpoints || []).join(", ") || "пока нет";
  const target = goal
    ? `${esc(goal.level || goal.target || "")} · ${date(goal.sitting)}`
    : '<a href="#exam" lang="et">Vali eesmärk <span class="ru" lang="ru">выбрать цель в обзоре Eksam</span></a>';
  let controls = "";
  if (me.scope === "guest") {
    controls = `<div class="profile-reset-actions">
      <button class="ghost" type="button" id="guestReset" aria-expanded="false" aria-controls="guestResetConfirm" lang="et">Tühjenda liivakast <span class="ru" lang="ru">очистить песочницу</span></button>
      <div class="profile-reset-confirm" id="guestResetConfirm" hidden>
        <p lang="ru">Будут удалены имя и временный прогресс этой песочницы.</p>
        <button class="ghost profile-reset-yes" type="button" id="guestResetYes" lang="et">Jah, tühjenda <span class="ru" lang="ru">да, очистить</span></button>
        <button class="ghost" type="button" id="guestResetCancel" lang="et">Loobu <span class="ru" lang="ru">отмена</span></button>
      </div>
    </div>`;
  } else if (authInfo.available && !needsFirstAccount()) {
    controls = '<button class="ghost" type="button" id="logoutBtn" lang="et">Logi välja <span class="ru" lang="ru">выйти</span></button>';
  }
  const nameValue = esc(me.name || "");
  const emailValue = me.email
    ? esc(me.email)
    : '<span lang="et">puudub</span><span class="profile-sub" lang="ru">не указан</span>';
  const start = me.onboarding;
  const startValue = start
    ? `${esc(START_BAND_NAMES[start.start_band] || "—")} · ${esc(FOCUS_NAMES[start.focus] || "Rada")}`
    : '<span lang="et">pole valitud</span><span class="profile-sub" lang="ru">ещё не выбрано</span>';
  const startControl = me.scope === "guest" ? "" :
    `<button class="linky" type="button" id="editOnboarding" lang="et">${start ? "Muuda" : "Vali"} <span class="ru" lang="ru">${start ? "изменить" : "выбрать"}</span></button>`;
  return `<dl class="profile-rows">
    <div class="profile-row"><dt lang="et">Nimi <span class="ru" lang="ru">имя</span></dt>
      <dd><span id="profileName">${nameValue || '<span class="hint">—</span>'}</span>
        <button class="linky" type="button" id="editName" lang="et">Muuda <span class="ru" lang="ru">изменить</span></button>
        <form id="nameForm" class="profile-name-form" hidden>
          <label lang="et" for="nameInput">Nimi <i class="ru" lang="ru">имя</i></label>
          <input id="nameInput" name="name" type="text" maxlength="60" autocomplete="name" value="${nameValue}">
          <button class="primary" type="submit" lang="et">Salvesta <span class="ru" lang="ru">сохранить</span></button>
          <button class="ghost" type="button" id="cancelName" lang="et">Loobu <span class="ru" lang="ru">отмена</span></button>
          <p class="profile-error" id="nameError" role="alert" hidden></p>
        </form>
      </dd></div>
    <div class="profile-row"><dt lang="et">E-post <span class="ru" lang="ru">эл. почта</span></dt><dd>${emailValue}</dd></div>
    <div class="profile-row"><dt lang="et">Konto <span class="ru" lang="ru">аккаунт</span></dt><dd><span lang="et">${scopeName(me.scope)}</span><span class="profile-sub profile-scope-description" lang="ru">${scopeDescription(me.scope)}</span>${controls}</dd></div>
    <div class="profile-row"><dt lang="et">Algus <span class="ru" lang="ru">старт</span></dt><dd>${startValue}${startControl}
      <span class="profile-sub" lang="ru">Самооценка для рекомендаций, не подтверждённый уровень CEFR.</span></dd></div>
    <div class="profile-row"><dt lang="et">Õpib alates <span class="ru" lang="ru">учится с</span></dt><dd>${date(me.since)}</dd></div>
    <div class="profile-row"><dt lang="et">Viimati <span class="ru" lang="ru">последнее занятие</span></dt><dd>${date(me.last_active)}</dd></div>
    <div class="profile-row"><dt lang="et">Tase <span class="ru" lang="ru">уровень</span></dt>
      <dd><span>${esc(level.current || "—")}</span><span class="profile-sub">Экзаменационная цель: ${target}</span>
        <span class="profile-sub">Зачтённые рубежи: ${esc(checkpointText)}</span></dd></div>
  </dl>`;
}

function authHtml() {
  if (currentMe?.scope !== "guest" && !needsFirstAccount()) return "";
  const canSignup = !!authInfo.signup_open;
  const tabs = canSignup
    ? `<div class="levels profile-auth-tabs" role="tablist" aria-label="Konto — аккаунт">
        <button type="button" role="tab" aria-selected="${authView === "login"}" data-auth-view="login" lang="et">Logi sisse <i class="ru" lang="ru">войти</i></button>
        <button type="button" role="tab" aria-selected="${authView === "signup"}" data-auth-view="signup" lang="et">Loo konto <i class="ru" lang="ru">создать аккаунт</i></button>
      </div>` : `<h3 class="sec-title" lang="et">Logi sisse <i class="ru" lang="ru">войти</i></h3>`;
  const signup = authView === "signup" && canSignup;
  return `<section class="profile-auth" aria-label="Sisselogimine">
    ${tabs}
    <form id="authForm" data-mode="${signup ? "signup" : "login"}">
      ${signup ? `<label lang="et" for="authName">Nimi <i class="ru" lang="ru">имя</i></label>
        <input id="authName" name="name" type="text" maxlength="60" autocomplete="name" required>` : ""}
      <label lang="et" for="authEmail">E-post <i class="ru" lang="ru">эл. почта</i></label>
      <input id="authEmail" name="email" type="email" autocomplete="email" required>
      <label lang="et" for="authPassword">Parool <i class="ru" lang="ru">пароль</i></label>
      <input id="authPassword" name="password" type="password" autocomplete="${signup ? "new-password" : "current-password"}" minlength="${signup ? 10 : 1}" maxlength="1024" required>
      <button class="go" type="submit" lang="et">${signup ? "Loo konto" : "Logi sisse"}<span class="ru" lang="ru">${signup ? "создать аккаунт" : "войти"}</span></button>
      <p id="authError" class="profile-error" role="alert" hidden></p>
    </form>
    ${signup ? `<p class="note">${needsFirstAccount()
      ? "Первый аккаунт продолжит историю, уже записанную в приложении."
      : "Новая учётная запись получит отдельный прогресс."}</p>` : ""}
  </section>`;
}

function profileHtml(me, notice = "") {
  const level = LEVELS.includes(sealLevel) ? sealLevel : "A1";
  const totals = me.totals || {};
  const seals = me.milestones?.[level] || [];
  const activeDays = Number(me.active_days_28) || 0;
  const scopes = authHtml();
  return `${scopes}
    ${notice ? `<p class="profile-success" lang="ru" role="status" aria-live="polite">${esc(notice)}</p>` : ""}
    ${me.scope === "guest" ? `<p class="profile-sandbox" lang="ru">Гостевой прогресс хранится только во временной песочнице и будет удалён. После регистрации он не переносится.</p>` : ""}
    ${startOptionsHtml(me)}
    ${profileRows(me)}
    <section class="profile-section">
      <h3 class="sec-head" lang="et">Märgid <i class="ru" lang="ru">значки</i></h3>
      <p class="hint profile-legend" lang="ru">Этапы: первая тренировка, освоенная тема, контрольная уровня и практика по всем четырём частям экзамена.</p>
      <div class="levels profile-levels" role="tablist" aria-label="Tase — уровень">
        ${LEVELS.map(item => `<button type="button" role="tab" aria-selected="${item === level}" data-seal-level="${item}">${item}</button>`).join("")}
      </div>
      <div id="profileSeals">${sealsHtml(seals)}</div>
    </section>
    <section class="profile-section">
      <h3 class="sec-head" lang="et">Rütm <i class="ru" lang="ru">ритм</i></h3>
      ${rhythmHtml(me.rhythm || [])}
      <p class="hint profile-legend" lang="ru">Каждый столбик — один день; чем темнее клетка, тем больше было упражнений.</p>
      <p class="hint profile-active-days">${count(activeDays, ["активный день", "активных дня", "активных дней"])} с занятиями за последние 4 недели.</p>
    </section>
    <section class="profile-section">
      <h3 class="sec-head" lang="et">Kokku <i class="ru" lang="ru">итого</i></h3>
      <ul class="profile-totals">
        <li>${count(totals.attempts, ["попытка", "попытки", "попыток"])}</li>
        <li>${count(totals.mastered, ["освоенная тема", "освоенные темы", "освоенных тем"])} из ${count(totals.topics, ["тема", "темы", "тем"])}</li>
        <li>${count(totals.review_cards, ["карточка повторения", "карточки повторения", "карточек повторения"])}</li>
        <li>${count(totals.known_words, ["известное слово", "известных слова", "известных слов"])}</li>
      </ul>
    </section>
    ${restoreHtml(me)}
    ${me.scope !== "guest" && !needsFirstAccount() ? `<section class="profile-section profile-reset-section">
      <h3 class="sec-head" lang="et">Lähtesta edenemine <i class="ru" lang="ru">сброс прогресса</i></h3>
      <p class="hint profile-reset-copy" lang="ru">Занятия, контрольные, повторы и словарь будут сброшены. Аккаунт, имя и дата регистрации сохранятся. До следующего сброса прогресс можно восстановить здесь.</p>
      <div class="profile-reset-actions">
        <button class="ghost" type="button" id="profileReset" aria-expanded="false" aria-controls="profileResetConfirm" lang="et">Lähtesta edenemine <span class="ru" lang="ru">сбросить прогресс</span></button>
        <div class="profile-reset-confirm" id="profileResetConfirm" hidden>
          <p lang="ru">После сброса прогресс можно восстановить в профиле. Новый сброс заменит эту точку восстановления.</p>
          <button class="ghost profile-reset-yes" type="button" id="profileResetYes" lang="et">Jah, lähtesta <span class="ru" lang="ru">да, сбросить</span></button>
          <button class="ghost" type="button" id="profileResetCancel" lang="et">Loobu <span class="ru" lang="ru">отмена</span></button>
        </div>
      </div>
    </section>` : ""}`;
}

function startOptionsHtml(me) {
  if ((Number(me.totals?.attempts) || 0) > 0 || me.onboarding) return "";
  return `<section class="profile-section profile-start-section" aria-labelledby="profileStartTitle">
    <h3 class="sec-head" id="profileStartTitle" lang="et">Alusta siit <i class="ru" lang="ru">начните здесь</i></h3>
    <p class="hint profile-start-copy" lang="ru">Выберите, с чего начать. В «Vaba harjutus» (свободной практике) можно менять сложность A1–B1; другие разделы доступны в любой момент.</p>
    <nav class="profile-start-actions" aria-label="Alustamine — начало">
      <a class="ghost" id="profileStartPath" href="#path" lang="et">Õpi rajal <span class="ru" lang="ru">учиться по плану</span></a>
      <a class="ghost" id="profileStartPractice" href="#drill" lang="et">Harjuta vabalt <span class="ru" lang="ru">свободная практика</span></a>
      <a class="ghost" id="profileStartExam" href="#exam" lang="et">Valmistu eksamiks <span class="ru" lang="ru">подготовка к экзамену</span></a>
    </nav>
  </section>`;
}

function restoreHtml(me) {
  if (me.scope === "guest" || !me.restore_available || needsFirstAccount()) return "";
  return `<section class="profile-section profile-restore-section">
    <h3 class="sec-head" lang="et">Taasta edenemine <i class="ru" lang="ru">восстановить прогресс</i></h3>
    <p class="hint profile-reset-copy" lang="ru">Можно вернуть прогресс до последнего сброса. Занятия, сделанные после него, тоже сохранятся. Следующий сброс заменит эту точку восстановления.</p>
    <div class="profile-reset-actions">
      <button class="ghost" type="button" id="profileRestore" aria-expanded="false" aria-controls="profileRestoreConfirm" lang="et">Taasta edenemine <span class="ru" lang="ru">восстановить прогресс</span></button>
      <div class="profile-reset-confirm" id="profileRestoreConfirm" hidden>
        <p lang="ru">Вернуть прогресс до последнего сброса, включая занятия после него? Аккаунт и профиль останутся без изменений.</p>
        <button class="ghost profile-restore-yes" type="button" id="profileRestoreYes" lang="et">Jah, taasta <span class="ru" lang="ru">да, восстановить</span></button>
        <button class="ghost" type="button" id="profileRestoreCancel" lang="et">Loobu <span class="ru" lang="ru">отмена</span></button>
      </div>
    </div>
  </section>`;
}

function paintAccount() {
  const button = $("#accountBtn");
  if (!button) return;
  const signedOut = authInfo.scope === "guest" ||
    (authInfo.available && authInfo.signup_open && !authInfo.email);
  const label = signedOut ? "Logi sisse — войти" : "Profiil — профиль";
  button.innerHTML = icon(signedOut ? "sign-in" : "user-circle");
  button.title = label;
  button.setAttribute("aria-label", label);
}

// A neutral profile icon is ready before the account probe returns.
paintAccount();

async function readAuth() {
  try {
    const info = await api("/api/auth/me").then(r => r.json());
    return {...info, available: true};
  } catch {
    return {scope: currentMe?.scope || "owner", signup_open: false, available: false};
  }
}

export async function loadProfile() {
  const out = $("#profileOut");
  if (!out) return;
  try {
    currentMe = await api("/api/me").then(r => r.json());
    authInfo = await readAuth();
    if (authInfo.scope !== currentMe.scope) authInfo.scope = currentMe.scope;
    paintAccount();
    authView = needsFirstAccount() ? "signup" : "login";
    const notice = resetNotice;
    resetNotice = "";
    out.innerHTML = profileHtml(currentMe, notice);
    bindProfile(out);
  } catch (err) {
    out.replaceChildren(retryableError(err.message, loadProfile));
  }
}

function bindProfile(out) {
  out.querySelectorAll('.profile-levels, .profile-auth-tabs').forEach(list => {
    const tabs = [...list.querySelectorAll('[role="tab"]')];
    const select = selected => tabs.forEach(tab => {
      const active = tab === selected;
      tab.tabIndex = active ? 0 : -1;
      tab.setAttribute("aria-selected", String(active));
    });
    select(tabs.find(tab => tab.getAttribute("aria-selected") === "true") || tabs[0]);
    tabs.forEach(tab => tab.addEventListener("click", () => select(tab)));
    list.addEventListener("keydown", event => {
      if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
      const here = tabs.indexOf(document.activeElement);
      if (here < 0) return;
      event.preventDefault();
      const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1
        : event.key === "ArrowRight" ? (here + 1) % tabs.length
        : (here - 1 + tabs.length) % tabs.length;
      tabs[next].focus();
      tabs[next].click();
    });
  });
  out.querySelectorAll("[data-seal-level]").forEach(button => button.addEventListener("click", () => {
    sealLevel = button.dataset.sealLevel;
    out.querySelectorAll("[data-seal-level]").forEach(tab =>
      tab.setAttribute("aria-selected", String(tab === button)));
    $("#profileSeals").innerHTML = sealsHtml(currentMe.milestones?.[sealLevel] || []);
  }));
  out.querySelectorAll("[data-auth-view]").forEach(button => button.addEventListener("click", () => {
    authView = button.dataset.authView;
    out.innerHTML = profileHtml(currentMe);
    bindProfile(out);
  }));
  $("#editName")?.addEventListener("click", () => {
    $("#profileName").hidden = true;
    $("#editName").hidden = true;
    $("#nameForm").hidden = false;
    $("#nameInput").focus();
  });
  $("#cancelName")?.addEventListener("click", () => loadProfile());
  $("#nameForm")?.addEventListener("submit", async event => {
    event.preventDefault();
    const error = $("#nameError");
    error.hidden = true;
    try {
      await api("/api/me", {name: $("#nameInput").value});
      await loadProfile();
    } catch (err) {
      error.textContent = err.message;
      error.hidden = false;
    }
  });
  $("#authForm")?.addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const submit = form.querySelector('button[type="submit"]');
    const error = $("#authError");
    error.hidden = true;
    submit.disabled = true;
    const values = Object.fromEntries(new FormData(form).entries());
    try {
      const authRoute = form.dataset.mode === "signup"
        ? "/api/auth/signup" : "/api/auth/login";
      await api(authRoute, {
        email: values.email, password: values.password,
      });
      let profileError = "";
      if (form.dataset.mode === "signup") {
        try { await api("/api/me", {name: values.name}); }
        catch (err) { profileError = err.message; }
      }
      authView = "login";
      await Promise.all([loadProfile(), paintScope()]);
      window.dispatchEvent(new CustomEvent("eesti:identity-changed"));
      if (profileError) {
        showError(out, `Аккаунт создан, но имя не сохранено. ${profileError}`);
      }
    } catch (err) {
      error.textContent = err.message;
      error.hidden = false;
    } finally { submit.disabled = false; }
  });
  $("#logoutBtn")?.addEventListener("click", async event => {
    event.currentTarget.disabled = true;
    try { await api("/api/auth/logout", {}); location.reload(); }
    catch (err) { event.currentTarget.disabled = false; showError(out, err.message); }
  });
  bindReset({
    trigger: $("#profileReset"), confirm: $("#profileResetYes"),
    cancel: $("#profileResetCancel"), box: $("#profileResetConfirm"),
    endpoint: "/api/me/reset", message: "Прогресс сброшен. Аккаунт и профиль сохранены.",
  });
  bindReset({
    trigger: $("#profileRestore"), confirm: $("#profileRestoreYes"),
    cancel: $("#profileRestoreCancel"), box: $("#profileRestoreConfirm"),
    endpoint: "/api/me/restore", message: "Прогресс восстановлен вместе с занятиями после сброса.",
    successFocus: "#profileReset",
  });
  bindReset({
    trigger: $("#guestReset"), confirm: $("#guestResetYes"),
    cancel: $("#guestResetCancel"), box: $("#guestResetConfirm"),
    endpoint: "/api/guest/reset", message: "Гостевая песочница очищена.", guest: true,
    successFocus: "#guestReset",
  });
}

function bindReset({trigger, confirm, cancel, box, endpoint, message, guest = false,
                    successFocus = "#profileRestore"}) {
  if (!trigger || !confirm || !cancel || !box) return;
  trigger.addEventListener("click", () => {
    box.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    box.scrollIntoView({block: "nearest"});
    confirm.focus({preventScroll: true});
  });
  cancel.addEventListener("click", () => {
    box.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    trigger.focus();
  });
  confirm.addEventListener("click", async () => {
    trigger.disabled = true;
    confirm.disabled = true;
    try {
      await api(endpoint, {});
      resetNotice = message;
      if (guest) await paintScope();
      await loadProfile();
      const next = $(successFocus);
      if (next) {
        next.scrollIntoView({block: "center"});
        next.focus({preventScroll: true});
      }
    } catch (err) {
      trigger.disabled = false;
      confirm.disabled = false;
      box.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      showError($("#profileOut"), err.message);
      trigger.focus();
    }
  });
}

function showError(out, message) {
  const notice = document.createElement("p");
  notice.className = "profile-error";
  notice.setAttribute("role", "alert");
  notice.textContent = message;
  out.prepend(notice);
}

export async function paintScope() {
  const box = $("#scopeNotice");
  if (!box) return;
  try {
    const info = await api("/api/auth/me").then(r => r.json());
    authInfo = {...info, available: true};
  } catch {
    if (!currentMe) {
      try { currentMe = await api("/api/me").then(r => r.json()); }
      catch { return; }
    }
    authInfo = {scope: currentMe.scope, signup_open: false, available: false};
  }
  paintAccount();
  const guest = authInfo.scope === "guest";
  box.hidden = !guest;
  box.innerHTML = guest
    ? '<span lang="et">Külaline</span><span lang="ru">Гостевой прогресс временный и не сохраняется.</span><a href="#profile" lang="et">Profiil <span class="ru" lang="ru">войти или создать аккаунт</span></a>'
    : "";
}
