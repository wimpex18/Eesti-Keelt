/* Playing what the library holds: HLS, YouTube, plain audio, and one word.

   hls.js is vendored rather than loaded from a CDN, and it is load-bearing:
   44 of the 91 audio items are HLS streams, which Safari plays natively and
   Chrome and Firefox do not. */

import {api, esc} from "./core.js";
import {icon} from "./icons.js";

const isHls = url => /\.m3u8(\?|$)/i.test(url || "");

let hlsReady = null;


function loadHls() {
  if (hlsReady) return hlsReady;
  hlsReady = new Promise((resolve, reject) => {
    const tag = document.createElement("script");
    tag.src = "/vendor/hls.light.min.js";
    tag.onload = () => resolve(window.Hls);
    tag.onerror = () => reject(new Error("Плеер не загрузился."));
    document.head.appendChild(tag);
  });
  return hlsReady;
}

export const YT = /(?:youtu\.be\/|v=)([\w-]{6,})/;


export function mountVideo(host, url) {
  const id = (url || "").match(YT)?.[1];
  if (!id) { host.innerHTML = ""; return; }
  host.innerHTML = `<div class="video"><iframe
    src="https://www.youtube-nocookie.com/embed/${esc(id)}"
    title="Eksami tutvustav video — вводное видео об экзамене" loading="lazy" allowfullscreen
    referrerpolicy="no-referrer"></iframe></div>`;
}


export async function mountAudio(host, url) {
  host.innerHTML = "";
  if (!url) return;

  const el = document.createElement("audio");
  el.controls = true;
  el.preload = "none";
  host.appendChild(el);

  const native = el.canPlayType("application/vnd.apple.mpegurl");
  if (!isHls(url) || native) { el.src = url; return; }

  try {
    const Hls = await loadHls();
    if (!Hls || !Hls.isSupported()) throw new Error("Этот браузер не может воспроизвести такой поток.");
    const hls = new Hls({ enableWorker: false });
    hls.loadSource(url);
    hls.attachMedia(el);
    // Free the stream when the panel is replaced, or a long session
    // accumulates one buffering player per episode opened.
    host._hls?.destroy();
    host._hls = hls;
  } catch (e) {
    // Say so rather than showing a dead player. Russian: this is an
    // explanation, and the reader is still learning Estonian.
    host.innerHTML = `<div class="banner">Аудио не воспроизводится в этом
      браузере (поток HLS). Открой в Safari или обнови страницу.</div>`;
  }
}


/* A dictionary phrase as it is said: EVS's alternatives (`valjusti / kõvasti`)
   read as a list, optional parts (`[on]`) read in. */
export const sayable = text => text.replace(/\s+\/\s+/g, ", ").replace(/[[\]]/g, "");

/* EVS marks an open slot in braces (`{kelle}`); it is set in italics. */
export const withSlots = text =>
  esc(text).replace(/\{([^{}]+)\}/g, '<i class="phrase-slot">$1</i>');


export async function speakWord(word, onError, tag = "") {
  /* A native speaker where EKI recorded one, synthesis otherwise.

     Estonian quantity (`koera` vs `k`oera`) is not in the spelling, so a
     synthesiser guesses it; EKI's recordings are read by people who know which
     word it is. A missing recording is a 404, not an error — most words have
     none (`eesti/haaldus.py`).

     Errors are shown, so a failed synthesiser is distinguishable from a silent
     word. The URL is revoked once the clip ends: a review session plays dozens,
     and each would otherwise pin its blob until the page closes. */
  let url = null;
  try {
    const q = new URLSearchParams({form: word});
    if (tag) q.set("tag", tag);
    let r = null;
    try {
      r = await api("/api/pronounce?" + q, null, "GET");
    } catch {
      r = await api("/api/speak", {text: word, speed: 0.9});
    }
    url = URL.createObjectURL(await r.blob());
    const audio = new Audio(url);
    audio.onended = audio.onerror = () => { URL.revokeObjectURL(url); url = null; };
    await audio.play();
  } catch (e) {
    if (url) URL.revokeObjectURL(url);
    if (onError) onError("Звук не загрузился: " + e.message);
  }
}


/* ── Mängija: one player for every sound ─────────────────────────────
   Every `<audio>` the app shows — dictation, reading, radio lessons, exam
   recordings, the read-aloud model, the conversation partner — gets the same
   controls: play, a seek track, the time, five seconds back and the speed. The
   native element stays the engine (it plays HLS on Safari, takes hls.js
   elsewhere, and keeps `src`, `hidden` and `play()` working for the code that
   made it); only its browser chrome is replaced. The speed is one preference
   for the whole app, because a learner slows everything down or nothing. */

const SPEEDS = [1, 0.75, 1.25];

function speed() {
  try { return Number(localStorage.getItem("playbackRate")) || 1; } catch { return 1; }
}

const clock = s => {
  if (!Number.isFinite(s) || s < 0) return "–:––";
  const m = Math.floor(s / 60), r = Math.floor(s % 60);
  return `${m}:${String(r).padStart(2, "0")}`;
};

export function enhanceAudio(audio) {
  if (audio._player || audio.closest(".player")) return audio._player;
  audio.controls = false;
  audio.classList.add("enhanced");
  const p = document.createElement("div");
  p.className = "player";
  p.hidden = audio.hidden;
  p.innerHTML = `
    <button class="pl-play" type="button" aria-label="Mängi — воспроизвести">${icon("play-fill", {weight: "bold"})}</button>
    <span class="pl-time pl-now">0:00</span>
    <input class="pl-seek" type="range" min="0" max="1000" step="1" value="0"
      aria-label="Asukoht — позиция в записи">
    <span class="pl-time pl-end">–:––</span>
    <button class="pl-back" type="button" aria-label="5 sekundit tagasi — назад на 5 секунд">−5</button>
    <button class="pl-rate" type="button" aria-label="Kiirus — скорость">1×</button>
    <span class="pl-err" role="status" hidden></span>`;
  audio.after(p);
  audio._player = p;
  const $p = s => p.querySelector(s);
  const play = $p(".pl-play"), seek = $p(".pl-seek"), rate = $p(".pl-rate");
  let dragging = false;

  const paintRate = () => {
    const r = speed();
    rate.textContent = `${r}×`;
    rate.classList.toggle("on", r !== 1);
    audio.playbackRate = r;
  };
  const paintTime = () => {
    const d = audio.duration, t = audio.currentTime;
    $p(".pl-now").textContent = clock(t);
    $p(".pl-end").textContent = Number.isFinite(d) ? clock(d) : "";
    // A live stream has no end: the track has nothing to point at.
    seek.disabled = !Number.isFinite(d) || d <= 0;
    if (!dragging && Number.isFinite(d) && d > 0) seek.value = String(Math.round(t / d * 1000));
    p.style.setProperty("--p", `${Number(seek.value) / 10}%`);
  };
  const paintState = () => {
    const on = !audio.paused && !audio.ended;
    p.classList.toggle("playing", on);
    play.innerHTML = icon(on ? "pause-fill" : "play-fill", {weight: "bold"});
    play.setAttribute("aria-label", on ? "Paus — пауза" : "Mängi — воспроизвести");
  };

  play.onclick = () => {
    if (audio.paused || audio.ended) {
      audio.playbackRate = speed();
      audio.play().catch(e => {
        $p(".pl-err").hidden = false;
        $p(".pl-err").textContent = "Не воспроизводится: " + e.message;
      });
    } else audio.pause();
  };
  $p(".pl-back").onclick = () => { audio.currentTime = Math.max(0, audio.currentTime - 5); };
  rate.onclick = () => {
    const next = SPEEDS[(SPEEDS.indexOf(speed()) + 1) % SPEEDS.length];
    try { localStorage.setItem("playbackRate", String(next)); } catch {}
    document.querySelectorAll("audio.enhanced").forEach(a => a._player?._paintRate?.());
  };
  p._paintRate = paintRate;
  seek.addEventListener("input", () => {
    dragging = true;
    p.style.setProperty("--p", `${Number(seek.value) / 10}%`);
    $p(".pl-now").textContent = clock(Number(seek.value) / 1000 * audio.duration);
  });
  seek.addEventListener("change", () => {
    if (Number.isFinite(audio.duration)) audio.currentTime = Number(seek.value) / 1000 * audio.duration;
    dragging = false;
  });

  for (const ev of ["timeupdate", "durationchange", "loadedmetadata", "seeked"])
    audio.addEventListener(ev, paintTime);
  for (const ev of ["play", "pause", "ended", "playing"])
    audio.addEventListener(ev, paintState);
  audio.addEventListener("waiting", () => p.classList.add("loading"));
  audio.addEventListener("playing", () => p.classList.remove("loading"));
  audio.addEventListener("canplay", () => p.classList.remove("loading"));
  audio.addEventListener("ratechange", () => { if (audio.playbackRate !== speed()) audio.playbackRate = speed(); });
  audio.addEventListener("error", () => {
    p.classList.remove("loading");
    const err = $p(".pl-err");
    err.hidden = false;
    err.textContent = "Запись не воспроизводится в этом браузере.";
  });
  // The code that made the element still shows and hides it; the player follows.
  new MutationObserver(() => { p.hidden = audio.hidden; })
    .observe(audio, {attributes: true, attributeFilter: ["hidden"]});
  paintRate(); paintTime(); paintState();
  return p;
}

// Every audio element, whenever it arrives.
document.querySelectorAll("audio").forEach(enhanceAudio);
new MutationObserver(records => {
  for (const r of records) for (const n of r.addedNodes) {
    if (n.nodeType !== 1) continue;
    if (n.tagName === "AUDIO") enhanceAudio(n);
    else n.querySelectorAll?.("audio").forEach(enhanceAudio);
  }
}).observe(document.body, {childList: true, subtree: true});
