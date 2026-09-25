/* Say a drill answer instead of typing it.

   The recogniser fills the answer box and nothing else: the learner sees what
   was heard, can fix it, and presses Kontrolli, so code grades exactly what is
   in the box. No hint goes to the recogniser; priming it with the sentence
   would make it hear the right form whether or not it was said. */

import {api, rawApi} from "./core.js";
import {icon} from "./icons.js";

const canRecord = window.isSecureContext &&
  navigator.mediaDevices && typeof MediaRecorder !== "undefined";

const ready = canRecord
  ? api("/api/asr", null, "GET").then(r => r.json()).then(a => Boolean(a.ready)).catch(() => false)
  : Promise.resolve(false);

const clean = w => w.toLowerCase().replace(/[.,!?;:«»"()]/g, "");


/* The learner may say the whole sentence; the answer is what the prompt lacks. */
export function answerFrom(heard, prompt) {
  const said = heard.split(/\s+/).map(clean).filter(Boolean);
  const known = new Set(prompt.replace("____", " ").split(/\s+/).map(clean));
  const rest = said.filter(w => !known.has(w));
  return (rest.length && rest.length < said.length ? rest : said).join(" ");
}


export async function addMic(row, input, prompt) {
  if (!input || !(await ready)) return;
  const btn = document.createElement("button");
  btn.className = "iconbtn mic";
  btn.type = "button";
  btn.lang = "et";
  btn.innerHTML = icon("microphone");
  btn.title = "Ütle vastus — сказать ответ вслух";
  btn.setAttribute("aria-label", "Ütle vastus — сказать ответ вслух");
  input.after(btn);
  let rec = null;
  btn.onclick = async () => {
    if (rec) { rec.stop(); return; }
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({audio: true}); }
    catch { btn.title = "Микрофон не открылся"; return; }
    const chunks = [];
    rec = new MediaRecorder(stream);
    rec.ondataavailable = e => e.data.size && chunks.push(e.data);
    rec.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(chunks, {type: rec.mimeType || "audio/webm"});
      rec = null;
      btn.setAttribute("aria-busy", "true");
      btn.disabled = true;
      try {
        const t = await (await rawApi("/api/transcribe", {
          method: "POST", headers: {"Content-Type": blob.type}, body: blob,
        })).json();
        if (t.text) {
          input.value = answerFrom(t.text, prompt);
          input.focus();
        } else {
          input.placeholder = "не разобрал";
        }
      } catch {
        input.placeholder = "не разобрал";
      } finally {
        btn.disabled = false;
        btn.removeAttribute("aria-busy");
        btn.innerHTML = icon("microphone");
        btn.classList.remove("on");
      }
    };
    rec.start();
    btn.classList.add("on");
  };
}
