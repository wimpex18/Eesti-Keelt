/* Rääkimine: reading aloud, the question bank, and recording yourself.

   What the recogniser says it heard is the only model output on this screen,
   and the caveat beside it is Russian on purpose: a miss may be the recogniser
   rather than the learner's mouth, and a caveat nobody can read is not one. */

import {$, api, esc, setLabel} from "./core.js";


// ── speaking ────────────────────────────────────────────────────────
// getUserMedia needs a secure context. On a phone that means HTTPS, which is
// what the Cloudflare deployment provides and what `serve` on localhost also
// counts as — so the failure is only ever "opened over plain http from another
// machine", and it is worth saying which of those you are in rather than
// leaving a dead button.
const canRecord = window.isSecureContext &&
  navigator.mediaDevices && typeof MediaRecorder !== "undefined";

let recorder = null, chunks = [], recording = false, asrReady = false;


// Ask once what this deployment can do, and say so rather than offering a
// feature that silently does nothing.
fetch("/api/asr").then(r => r.json()).then(a => { asrReady = a.ready; })
  .catch(() => {});


let readAloud = [], readIdx = 0;


function speakMode() { return $("#speakMode").value; }


export async function loadReadAloud(kind) {
  try {
    const {items} = await (await api(`/api/speaking/readaloud?kind=${kind}&n=12`, null, "GET")).json();
    readAloud = items; readIdx = 0;
    $("#speakTopic").hidden = true;
    $("#speakNext").hidden = false;
    showReadAloud();
  } catch (e) { $("#speakPrompt").textContent = e.message; }
}


function showReadAloud() {
  const it = readAloud[readIdx];
  if (!it) return;
  $("#speakPrompt").innerHTML =
    `${esc(it.text)}<div class="why" style="margin-top:var(--s2)">Прочитай вслух.
     ${it.level ? esc(it.level) : ""}</div>`;
  $("#speakModel").hidden = true;
  $("#recPlayback").hidden = true;
  $("#recHeard").hidden = true;
}


$("#speakNext").onclick = () => {
  readIdx = (readIdx + 1) % Math.max(readAloud.length, 1);
  showReadAloud();
};


$("#speakMode").addEventListener("change", () => {
  const m = speakMode();
  if (m === "vastus") {
    $("#speakTopic").hidden = false;
    $("#speakNext").hidden = true;
    showSpeakQuestion();
  } else {
    loadReadAloud(m);
  }
});


// What the microphone is aimed at right now: a known target when reading
// aloud, an open question otherwise. The distinction decides whether the
// result can be checked at all.
function currentTarget() {
  if (speakMode() === "vastus") return null;
  const it = readAloud[readIdx];
  return it ? it.text : null;
}

function currentQuestion() {
  if (speakMode() !== "vastus") return "";
  const q = (window.__speak || [])[$("#speakTopic").value | 0];
  return q ? q.question : "";
}


export async function loadSpeakQuestions() {
  try {
    const {questions} = await (await api("/api/speaking", null, "GET")).json();
    $("#speakTopic").innerHTML = questions
      .map((q, i) => `<option value="${i}">${esc(q.topic)}</option>`).join("");
    window.__speak = questions;
    showSpeakQuestion();
  } catch (e) { $("#speakPrompt").textContent = e.message; }
}


function showSpeakQuestion() {
  const q = (window.__speak || [])[$("#speakTopic").value | 0];
  if (!q) return;
  $("#speakPrompt").innerHTML =
    `${esc(q.question)}<div class="why" style="margin-top:var(--s2)">${esc(q.hint_ru)}</div>`;
  $("#speakModel").hidden = true;
  $("#recPlayback").hidden = true;
}

$("#speakTopic").addEventListener("change", showSpeakQuestion);


$("#speakPlay").onclick = async () => {
  const text = currentTarget() || currentQuestion();
  if (!text) return;
  const btn = $("#speakPlay"); btn.disabled = true; setLabel(btn, "Синтезирую…");
  try {
    const r = await api("/api/speak", {text, speed: 0.85});
    const el = $("#speakModel");
    el.src = URL.createObjectURL(await r.blob());
    el.hidden = false; el.play().catch(() => {});
  } catch (e) {
    $("#recNote").textContent = "Синтез речи не ответил: " + e.message;
  } finally { btn.disabled = false; setLabel(btn, "Kuula ette"); }
};


if (!canRecord) {
  $("#recBtn").disabled = true;
  $("#recState").textContent = window.isSecureContext
    ? "Этот браузер не умеет записывать звук."
    : "Микрофону нужен HTTPS (или localhost).";
} else {
  $("#recState").textContent = "Ответь вслух и прослушай себя.";
  $("#recBtn").onclick = async () => {
    if (recording) {
      recorder.stop(); return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true});
      chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = e => e.data.size && chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunks, {type: recorder.mimeType || "audio/webm"});
        const el = $("#recPlayback");
        el.src = URL.createObjectURL(blob);
        el.hidden = false;
        recording = false;
        setLabel($("#recBtn"), "● Salvesta vastus");
        $("#recState").textContent = "Прослушай себя и сравни с образцом.";
        // Transcription is enrichment: the recording and the playback are the
        // exercise, and they already happened. Nothing here can fail in a way
        // that costs the learner their answer.
        if (!asrReady) return;
        const heard = $("#recHeard");
        heard.hidden = false;
        heard.innerHTML = `<span class="tag">Kuuldi <i class="ru">услышано</i></span><div class="fix">…</div>`;
        try {
          const target = currentTarget();
          const params = new URLSearchParams();
          if (target) params.set("target", target);
          else params.set("q", currentQuestion());
          const r = await fetch("/api/transcribe?" + params, {
            method: "POST", headers: {"Content-Type": blob.type}, body: blob,
          });
          const t = await r.json();
          if (!t.text) {
            heard.innerHTML = `<span class="tag">Kuuldi <i class="ru">услышано</i></span><div class="why">${esc(t.note || "не разобрал")}</div>`;
            return;
          }
          let html = `<span class="tag">Kuuldi <i class="ru">услышано</i></span><div class="fix">${esc(t.text)}</div>`;
          if (t.comparison) {
            const c = t.comparison;
            // Word by word, because "7/9" is actionable and "78%" is not: the
            // two that were missed are the two to say again.
            html += `<div class="fix">` + c.words.map(w =>
              w.ok ? `<ins>${esc(w.target)}</ins>`
                   : `<del>${esc(w.target)}</del>`).join(" ") + `</div>`;
            html += `<div class="why">${c.matched}/${c.total} слов распознано.
              ${c.missed.length ? "Повтори: <b>" + c.missed.map(esc).join(", ") + "</b>. " : ""}
              ${esc(c.caveat)}</div>`;
          } else {
            html += `<div class="why">Движок: ${esc(t.engine)}.</div>`;
            // An open answer is text once transcribed, so it goes through the
            // same grammar check as writing.
            try {
              const fb = await (await api("/api/speaking/feedback", {
                transcript: t.text, question: currentQuestion(),
              })).json();
              html += `<div class="why">${fb.words} слов` +
                (fb.pace_wpm ? ` · ${fb.pace_wpm} слов/мин` : "") + `</div>`;
              if (fb.corrections.length) html += fb.corrections.map(c =>
                `<div class="why">✗ <del>${esc(c.wrong)}</del> →
                 <ins>${esc(c.correct)}</ins> — ${esc(c.why || "")}</div>`).join("");
            } catch {}
          }
          heard.innerHTML = html;
        } catch (e) {
          heard.innerHTML = `<span class="tag">Kuuldi <i class="ru">услышано</i></span><div class="why">${esc(e.message)}</div>`;
        }
      };
      recorder.start();
      recording = true;
      setLabel($("#recBtn"), "■ Lõpeta");
      $("#recState").innerHTML = `<span class="dot"></span> Записываю…`;
    } catch (e) {
      $("#recState").textContent = "Микрофон не открылся: " + e.message;
    }
  };
  /* Said once, plainly: this records, it does not score. Pronunciation
     scoring from audio is a research problem, and EKI already publishes free
     exercises.

     It used to open by promising the recording never left the device, which
     stopped being true when recognition moved to Cloudflare — and sat
     directly under `#recPrivacy` saying the opposite. Where the audio goes is
     that notice's job; this one is only about what the practice is worth. */
  $("#recNote").innerHTML =
    "Здесь <b>не выставляют баллов</b> — произношение по записи не " +
    "оценивается. <b>Rääkimiseksam</b> на B1 — <b>парный</b>: два кандидата " +
    "отвечают по очереди, а затем разговаривают между собой. Поэтому в " +
    "одиночку имеет смысл тренировать построение ответа и беглость, а не " +
    "баллы.";
}
