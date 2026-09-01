/* Playing what the library holds: HLS, YouTube, plain audio, and one word.

   hls.js is vendored rather than loaded from a CDN, and it is load-bearing:
   44 of the 91 audio items are HLS streams, which Safari plays natively and
   Chrome and Firefox do not. */

import {api, esc} from "./core.js";

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
    if (!Hls || !Hls.isSupported()) throw new Error("Этот браузер не умеет играть такой поток.");
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
      браузере (поток HLS). Откройте в Safari или обновите страницу.</div>`;
  }
}


export async function speakWord(word, onError) {
  /* An empty catch here would be the pronunciation-privacy mistake again in
     miniature: the button appears to work, nothing happens, and the learner
     has no way to tell a dead synthesiser from a silent word. The URL is
     revoked once the clip ends -- a review session plays dozens, and each one
     pins its blob in memory until the page is closed. */
  let url = null;
  try {
    const r = await api("/api/speak", {text: word, speed: 0.9});
    url = URL.createObjectURL(await r.blob());
    const audio = new Audio(url);
    audio.onended = audio.onerror = () => { URL.revokeObjectURL(url); url = null; };
    await audio.play();
  } catch (e) {
    if (url) URL.revokeObjectURL(url);
    if (onError) onError("Звук не пришёл: " + e.message);
  }
}
