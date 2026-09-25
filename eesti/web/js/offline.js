/* Practising with no connection.

   Drills are generated on the server, so without one there is nothing to
   answer — unless a set was fetched in advance. A pack is items *with* their
   answers: offline the page grades by comparing strings, which is the same
   rule the server applies (`item.GradedItem.check`).

   What was answered is queued with an id and the time it happened, and sent
   when the connection returns. The server re-grades each one from its signed
   token, so the page never decides what counts; the id makes sending the queue
   twice harmless (`eesti/evidence.py`). */

import {$, api, esc, ruCount} from "./core.js";

const DB = "eesti-offline";
const PACK = "pack", QUEUE = "queue";

function open() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(PACK)) db.createObjectStore(PACK);
      if (!db.objectStoreNames.contains(QUEUE)) db.createObjectStore(QUEUE);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function put(store, key, value) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function all(store) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readonly");
    const request = tx.objectStore(store).getAll();
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
}

async function drop(store, key) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).delete(key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function savedPack() {
  const packs = await all(PACK).catch(() => []);
  return packs[0] || null;
}

export async function fetchPack(count = 24) {
  const pack = await (await api(`/api/pack?count=${count}`, null, "GET")).json();
  await put(PACK, "current", pack);
  return pack;
}

/* The id is the learner's own: the server records the event under it, so the
   same answer sent twice is stored once. */
function newId() {
  return (crypto.randomUUID && crypto.randomUUID()) ||
    `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function queueAnswer(item, given, latencyMs) {
  const entry = {
    event_id: newId(),
    at: new Date().toISOString(),
    topic: item.topic, token: item.token || "",
    prompt: item.prompt, answer: item.answer, lemma: item.lemma || "",
    label: item.hint || "", rule: item.rule || "", why_ru: item.why_ru || "",
    given, latency_ms: latencyMs,
  };
  await put(QUEUE, entry.event_id, entry);
  return entry;
}

export async function pending() {
  return all(QUEUE).catch(() => []);
}

/** Send what was answered offline. Returns how many the server took. */
export async function flush() {
  const queued = await pending();
  let sent = 0;
  for (const entry of queued) {
    try {
      await api("/api/practice/answer", {...entry, record: true});
      await drop(QUEUE, entry.event_id);
      sent++;
    } catch {
      break;                    // still offline, or the server is unwell
    }
  }
  return sent;
}

export function graded(item, given) {
  // The server's rule, applied here because offline there is nobody to ask.
  // Parallel forms ("minule ~ mulle") accept either, as on the server.
  const said = (given || "").trim().toLocaleLowerCase("et");
  return (item.answer || "").split(" ~ ").some(v => said === v.trim().toLocaleLowerCase("et"));
}

export function describe(pack, queuedCount) {
  if (!pack) return "Набор не скачан.";
  const when = new Date(pack.issued).toLocaleDateString("ru-RU");
  const bits = [`${ruCount(pack.items.length, ["задание", "задания", "заданий"])} от ${esc(when)}`];
  if (queuedCount) bits.push(`${ruCount(queuedCount, ["ответ ждёт", "ответа ждут", "ответов ждут"])} отправки`);
  return bits.join(" · ");
}
