/* Reminders: the switch, and the browser's half of Web Push.

   What can be told is decided on the server (`eesti/reminders.py`) and sent by
   the Worker's cron; this page only asks the browser for permission, hands the
   subscription to the Worker and shows what is in force.

   On iOS a notification is possible only from a PWA added to the Home Screen
   (16.4+), so the switch says that rather than failing silently when the API
   is missing. */

import {$, api} from "./core.js";

const SUPPORTED = "serviceWorker" in navigator && "PushManager" in window;

function urlBase64ToUint8Array(value) {
  const padded = (value + "=".repeat((4 - value.length % 4) % 4))
    .replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(padded), c => c.charCodeAt(0));
}

function say(text) { $("#remindHint").textContent = text; }

async function current() {
  const reg = await navigator.serviceWorker.getRegistration();
  return reg ? reg.pushManager.getSubscription() : null;
}

/** Draw the switch from what is true now: permission, subscription, settings. */
async function paint() {
  const box = $("#remind");
  if (!box) return;
  if (!SUPPORTED) {
    // Standalone is the iOS condition; on a desktop browser the API is simply
    // absent and the honest answer is the same.
    say(window.matchMedia("(display-mode: standalone)").matches
      ? "этот браузер не поддерживает напоминания"
      : "добавь приложение на главный экран — тогда можно включить напоминания");
    $("#remindBtn").disabled = true;
    return;
  }
  let key;
  try {
    key = await (await api("/api/push/key")).json();
  } catch {
    say("напоминания сейчас недоступны");
    $("#remindBtn").disabled = true;
    return;
  }
  if (!key.configured) {
    say("напоминания не настроены на сервере");
    $("#remindBtn").disabled = true;
    return;
  }
  const prefs = await (await api("/api/reminders/settings")).json();
  const sub = await current();
  const on = Boolean(sub) && prefs.on && Notification.permission === "granted";
  $("#remindBtn").dataset.on = on ? "1" : "0";
  $("#remindBtn").setAttribute("aria-pressed", on ? "true" : "false");
  $("#remindWhen").hidden = !on;
  paintHours(prefs.hour);
  say(on
    ? `включены · тихо с ${prefs.quiet_from}:00 до ${prefs.quiet_to}:00 · уходит только число, не текст`
    : "выключены");
}

function paintHours(chosen) {
  const select = $("#remindHour");
  if (select.options.length === 0) {
    for (let hour = 6; hour <= 23; hour++) {
      const option = document.createElement("option");
      option.value = String(hour);
      option.textContent = `${hour}:00`;
      select.append(option);
    }
  }
  select.value = String(chosen);
}

async function turnOn() {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    say("браузер не разрешил уведомления");
    return;
  }
  const key = await (await api("/api/push/key")).json();
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(key.key),
  });
  await api("/api/push/subscribe", sub.toJSON());
  await api("/api/reminders/settings", {on: true});
}

async function turnOff() {
  const sub = await current();
  if (sub) {
    await api("/api/push/unsubscribe", {endpoint: sub.endpoint});
    await sub.unsubscribe().catch(() => {});
  }
  await api("/api/reminders/settings", {on: false});
}

export async function loadReminders() {
  if (!$("#remind")) return;
  await paint();
}

$("#remindBtn")?.addEventListener("click", async () => {
  const btn = $("#remindBtn");
  btn.disabled = true;
  say("…");
  try {
    if (btn.dataset.on === "1") await turnOff();
    else await turnOn();
  } catch (err) {
    say(err.message);
  } finally {
    btn.disabled = false;
    await paint();
  }
});

$("#remindHour")?.addEventListener("change", async e => {
  await api("/api/reminders/settings", {hour: Number(e.target.value)});
  await paint();
});
