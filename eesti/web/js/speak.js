/* Rääkimine: reading aloud, the question bank, and recording yourself.

   What the recogniser says it heard is the only model output on this screen,
   and the caveat beside it is Russian on purpose: a miss may be the recogniser
   rather than the learner's mouth, and a caveat nobody can read is not one. */

import {$, api, esc, md, rawApi, ruCount, setLabel} from "./core.js";


// ── speaking ────────────────────────────────────────────────────────
// getUserMedia needs a secure context: HTTPS (the Cloudflare deployment) or
// localhost. The only failing case is plain http from another machine, and the
// page says which one applies rather than leaving a dead button.
const canRecord = window.isSecureContext &&
  navigator.mediaDevices && typeof MediaRecorder !== "undefined";

let recorder = null, chunks = [], recording = false, asrReady = false;
let evalAvailable = false, practiceClip = null;


// Ask once what this deployment can do, and say so rather than offering a
// feature that silently does nothing.
api("/api/asr", null, "GET").then(r => r.json()).then(a => {
  asrReady = Boolean(a.ready);
  const destination = a.cloudflare ? "в Cloudflare"
    : a.openrouter ? "в OpenRouter"
      : a.huggingface ? "в Hugging Face" : "во внешний сервис";
  // The Worker uses only Cloudflare in production. `cli serve` can walk its
  // configured hosted fallbacks, so disclose those without implying that the
  // deployed app sends recordings to them.
  const otherHosts = [a.cloudflare && a.openrouter && "OpenRouter",
    a.huggingface && a.cloudflare && "Hugging Face",
    a.openrouter && a.huggingface && !a.cloudflare && "Hugging Face"]
    .filter(Boolean);
  const fallback = otherHosts.length
    ? ` При локальном запуске запасной движок может отправить аудио в ${otherHosts.join(" или ")}.`
    : "";
  $("#recPrivacy").textContent = a.hosted
    ? `Для распознавания запись отправляется ${destination}.${fallback} Аудиофайл обычного упражнения приложение не сохраняет; остаётся текст.`
    : a.local || a.voxtral
      ? "Распознавание выполняется на этом компьютере. Аудиофайл обычного упражнения приложение не сохраняет; остаётся текст."
      : "Распознавание сейчас недоступно. Запись можно прослушать здесь; приложение не сохраняет аудиофайл обычного упражнения.";
  $("#evalPrivacy").textContent = a.hosted
    ? `Копия записи сохраняется на этом компьютере. Для черновой расшифровки аудио отправляется ${destination}.${fallback}`
    : a.local || a.voxtral
      ? "Запись и черновая расшифровка остаются на этом компьютере."
      : "Запись сохраняется на этом компьютере; черновая расшифровка сейчас недоступна.";
  $("#vestlusMic").disabled = !canRecord || !asrReady;
  $("#vestlusMicState").textContent = !canRecord
    ? "Для разговора голосом нужен микрофон и защищённое соединение (HTTPS)."
    : asrReady ? "Скажи ответ, проверь распознанный текст и нажми Vasta."
      : "Распознавание сейчас недоступно; можно отвечать текстом.";
  $("#vestlusPrivacy").textContent = a.hosted
    ? `Запись для распознавания отправляется ${destination}.${fallback} Аудиофайл разговора приложение не сохраняет.`
    : a.local || a.voxtral
      ? "Распознавание выполняется на этом компьютере. Аудиофайл разговора приложение не сохраняет."
      : "Аудиофайл разговора приложение не сохраняет.";
}).catch(() => {
  $("#recPrivacy").textContent = "Не удалось узнать, куда отправится запись. Попробуй обновить страницу перед записью.";
  $("#evalPrivacy").textContent = "Распознавание недоступно; запись сохранится только на этом компьютере.";
  $("#vestlusMic").disabled = true;
  $("#vestlusMicState").textContent = "Не удалось проверить распознавание; можно отвечать текстом.";
});


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
    `${esc(it.text)}<div class="why instr" lang="ru" style="margin-top:var(--s2)">Прочитай вслух.
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
      .map((q, i) => `<option value="${i}" lang="et">${esc(q.topic)}</option>`).join("");
    window.__speak = questions;
    showSpeakQuestion();
  } catch (e) { $("#speakPrompt").textContent = e.message; }
}


function showSpeakQuestion() {
  const q = (window.__speak || [])[$("#speakTopic").value | 0];
  if (!q) return;
  $("#speakPrompt").innerHTML =
    `${esc(q.question)}<div class="why" lang="ru" style="margin-top:var(--s2)">${esc(q.hint_ru)}</div>`;
  $("#speakModel").hidden = true;
  $("#recPlayback").hidden = true;
}

$("#speakTopic").addEventListener("change", showSpeakQuestion);


$("#speakPlay").onclick = async () => {
  const text = currentTarget() || currentQuestion();
  if (!text) return;
  const btn = $("#speakPlay"); btn.disabled = true; setLabel(btn, "Готовлю звук…");
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
    : "Для записи нужен микрофон и защищённое соединение (HTTPS).";
} else {
  $("#recState").textContent = "Ответь вслух и прослушай себя.";
  $("#recBtn").onclick = async () => {
    if (recording) {
      recorder.stop(); return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true});
      const task = {text: currentTarget() || "", question: currentQuestion(),
        planted: "", correct: ""};
      practiceClip = null;
      $("#recSaveEval").hidden = true;
      chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = e => e.data.size && chunks.push(e.data);
      recorder.onstop = async () => {
        const seconds = (performance.now() - startedAt) / 1000;
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunks, {type: recorder.mimeType || "audio/webm"});
        practiceClip = {blob, task, transcript: "", engine: ""};
        $("#recSaveEval").hidden = !evalAvailable;
        const el = $("#recPlayback");
        el.src = URL.createObjectURL(blob);
        el.hidden = false;
        recording = false;
        setLabel($("#recBtn"), "Salvesta vastus");
        $("#recState").textContent = "Прослушай себя и сравни с образцом.";
        // Transcription is enrichment: the recording and the playback are the
        // exercise, and they already happened. Nothing here can fail in a way
        // that costs the learner their answer.
        if (!asrReady) return;
        const heard = $("#recHeard");
        heard.hidden = false;
        heard.innerHTML = `<span class="tag" lang="et">Kuuldi <i class="ru" lang="ru">услышано</i></span><div class="fix">…</div>`;
        try {
          const target = task.text;
          const params = new URLSearchParams();
          if (target) params.set("target", target);
          else params.set("q", task.question);
          const r = await rawApi("/api/transcribe?" + params, {
            method: "POST", headers: {"Content-Type": blob.type}, body: blob,
          });
          const t = await r.json();
          if (practiceClip?.blob === blob) {
            practiceClip.transcript = t.text || "";
            practiceClip.engine = t.engine || "";
            if (t.text && practiceClip.saved) {
              api(`/api/eval/draft/${practiceClip.saved}`,
                {text: t.text, engine: t.engine || ""}).catch(() => {});
              if (reviewStem === practiceClip.saved &&
                  !$("#evalTranscript").value.trim()) {
                $("#evalTranscript").value = t.text;
                reviewReady();
              }
            }
          }
          if (!t.text) {
            heard.innerHTML = `<span class="tag" lang="et">Kuuldi <i class="ru" lang="ru">услышано</i></span><div class="why">${esc(t.note || "не разобрал")}</div>`;
            return;
          }
          let html = `<span class="tag" lang="et">Kuuldi <i class="ru" lang="ru">услышано</i></span><div class="fix" lang="et">${esc(t.text)}</div>`;
          if (t.comparison) {
            const c = t.comparison;
            // Word by word, because "7/9" is actionable and "78%" is not: the
            // two that were missed are the two to say again.
            html += `<div class="fix" lang="et">` + c.words.map(w =>
              w.ok ? `<ins>${esc(w.target)}</ins>`
                   : `<del>${esc(w.target)}</del>`).join(" ") + `</div>`;
            html += `<div class="why">${c.matched}/${c.total} слов распознано.
              ${c.missed.length ? "Повтори: <b lang=\"et\">" + c.missed.map(esc).join(", ") + "</b>. " : ""}
              ${esc(c.caveat)}</div>`;
          } else {
            html += `<div class="why">Движок: ${esc(t.engine)}.</div>`;
            // An open answer is text once transcribed, so it goes through the
            // same grammar check as writing.
            try {
              const fb = await (await api("/api/speaking/feedback", {
                transcript: t.text, question: task.question, seconds,
              })).json();
              html += `<div class="why">${ruCount(fb.words, ["слово", "слова", "слов"])}` +
                (fb.pace_wpm ? ` · ${fb.pace_wpm} слов/мин` : "") + `</div>`;
              if (fb.corrections.length) html += fb.corrections.map(c =>
                `<div class="why">✗ <del lang="et">${esc(c.wrong)}</del> →
                 <ins lang="et">${esc(c.correct)}</ins> — ${esc(c.why || "")}</div>`).join("");
            } catch {}
          }
          heard.innerHTML = html;
        } catch (e) {
          heard.innerHTML = `<span class="tag" lang="et">Kuuldi <i class="ru" lang="ru">услышано</i></span><div class="why">${esc(e.message)}</div>`;
        }
      };
      const startedAt = performance.now();
      recorder.start();
      recording = true;
      setLabel($("#recBtn"), "■ Lõpeta");
      $("#recState").innerHTML = `<span class="dot"></span> Записываю…`;
    } catch (e) {
      $("#recState").textContent = "Микрофон не открылся: " + e.message;
    }
  };
  /* Said once, plainly: this records, it does not score. Pronunciation scoring
     from audio is a research problem, and EKI already publishes free exercises.

     Where the audio goes is `#recPrivacy`'s job; this note is only about what the
     practice is worth. */
  $("#recNote").innerHTML =
    "Здесь <b>не выставляют баллов</b> — произношение по записи не оценивается." +
    "<details><summary>Почему</summary><b lang=\"et\">Rääkimiseksam</b> на B1 — " +
    "<b>парный</b>: два кандидата отвечают по очереди, а затем разговаривают " +
    "между собой. В одиночку имеет смысл тренировать построение ответа и " +
    "беглость, а не баллы.</details>";
}


/* Vestlus: the partner the paired exam has and a solo learner does not.

   A model plays it (ADR-0002): Estonian in, Estonian out, one question back,
   and nothing it says is a verdict. The exchange lives here in the page — the
   server keeps no conversation — and the words Vabamorf does not know are
   named rather than passed off as Estonian. */
let vestlus = {task: "", turns: []};
let vestlusRecorder = null, vestlusStream = null, vestlusChunks = [];
let vestlusEpoch = 0, vestlusVoiceUrl = null;

function paintVestlus(reply) {
  const log = $("#vestlusLog");
  log.innerHTML = vestlus.turns.map(t => t.who === "learner"
    ? `<div class="vestlus-me" lang="et">${esc(t.text)}</div>`
    : `<div class="vestlus-them" lang="et">${esc(t.text)}</div>`).join("");
  const bits = [];
  if (reply && reply.hint_ru) bits.push(esc(reply.hint_ru));
  if (reply && reply.unknown && reply.unknown.length)
    bits.push(`Vabamorf не знает: <b lang="et">${reply.unknown.map(esc).join(", ")}</b>
      — не бери эти формы за образец.`);
  if (reply && reply.note) bits.push(esc(reply.note));
  if (reply && reply.engine && reply.engine !== "none")
    bits.push(`собеседник: ${esc(reply.engine)} · не проверка`);
  log.insertAdjacentHTML("beforeend",
    bits.length ? `<div class="hint">${bits.join(" · ")}</div>` : "");
  $("#vestlusTurns").textContent = reply
    ? `${reply.turns} из ${8}` : "";
  log.scrollTop = log.scrollHeight;
}

async function vestlusTurn(said) {
  const send = $("#vestlusSend"), start = $("#vestlusStart"), mic = $("#vestlusMic");
  const epoch = vestlusEpoch;
  send.disabled = start.disabled = mic.disabled = true;
  $("#vestlusVoice").pause();
  try {
    const reply = await (await api("/api/tutor", {
      intent: "converse", task: vestlus.task, said,
      history: vestlus.turns.map(t => ({who: t.who, text: t.text})),
    })).json();
    if (said) vestlus.turns.push({who: "learner", text: said});
    if (reply.reply_et) vestlus.turns.push({who: "partner", text: reply.reply_et});
    paintVestlus(reply);
    $("#vestlusRow").hidden = !reply.reply_et;
    if (reply.reply_et) $("#vestlusSay").focus();
    const voice = $("#vestlusVoice");
    voice.hidden = !reply.reply_et;
    if (reply.reply_et) {
      try {
        const spoken = await api("/api/speak", {text: reply.reply_et, speed: 0.9});
        if (epoch !== vestlusEpoch) return;
        if (vestlusVoiceUrl) URL.revokeObjectURL(vestlusVoiceUrl);
        vestlusVoiceUrl = URL.createObjectURL(await spoken.blob());
        voice.src = vestlusVoiceUrl;
        voice.play().catch(() => {});
      } catch (_) {
        voice.hidden = true;
        $("#vestlusMicState").textContent = "Озвучивание недоступно; ответ показан текстом.";
      }
    }
  } catch (e) {
    $("#vestlusLog").insertAdjacentHTML("beforeend",
      `<div class="hint">Не отправилось: ${esc(e.message)}</div>`);
  } finally {
    send.disabled = start.disabled = false;
    mic.disabled = !asrReady;
  }
}

$("#vestlusStart").onclick = () => {
  const questions = window.__speak || [];
  const picked = questions[$("#speakTopic").selectedIndex] || questions[0];
  if (!picked) return;
  vestlusEpoch += 1;
  vestlus = {task: picked.question, turns: []};
  $("#vestlusLog").innerHTML = "";
  $("#vestlusVoice").pause();
  $("#vestlusVoice").hidden = true;
  vestlusTurn("");
};

$("#vestlusMic").onclick = async () => {
  const button = $("#vestlusMic"), status = $("#vestlusMicState");
  if (vestlusRecorder?.state === "recording") {
    vestlusRecorder.stop();
    return;
  }
  if (!canRecord || !asrReady || !vestlus.task) return;
  button.disabled = $("#vestlusSend").disabled = $("#vestlusStart").disabled = true;
  try {
    vestlusStream = await navigator.mediaDevices.getUserMedia({audio: true});
    const epoch = vestlusEpoch;
    vestlusChunks = [];
    vestlusRecorder = new MediaRecorder(vestlusStream);
    vestlusRecorder.ondataavailable = event => event.data.size && vestlusChunks.push(event.data);
    vestlusRecorder.onstop = async () => {
      vestlusStream.getTracks().forEach(track => track.stop());
      button.disabled = true;
      setLabel(button, "Räägi");
      status.textContent = "Распознаю ответ…";
      const blob = new Blob(vestlusChunks, {type: vestlusRecorder.mimeType || "audio/webm"});
      try {
        const query = new URLSearchParams({q: vestlus.task});
        const result = await (await rawApi("/api/transcribe?" + query, {
          method: "POST", headers: {"Content-Type": blob.type}, body: blob,
        })).json();
        if (epoch !== vestlusEpoch) return;
        $("#vestlusSay").value = result.text || "";
        status.textContent = result.text
          ? "Проверь распознанный текст и нажми Vasta."
          : "Речь не распознана. Повтори или напиши ответ.";
        $("#vestlusSay").focus();
      } catch (error) {
        status.textContent = `Распознавание не ответило: ${error.message}`;
      } finally {
        button.disabled = !asrReady;
        $("#vestlusSend").disabled = $("#vestlusStart").disabled = false;
      }
    };
    vestlusRecorder.start();
    button.disabled = false;
    setLabel(button, "Lõpeta");
    status.textContent = "Говори; нажми Lõpeta, когда закончишь.";
  } catch (error) {
    vestlusStream?.getTracks().forEach(track => track.stop());
    button.disabled = !asrReady;
    $("#vestlusSend").disabled = $("#vestlusStart").disabled = false;
    status.textContent = `Микрофон недоступен: ${error.message}`;
  }
};

$("#vestlusSend").onclick = () => {
  const said = $("#vestlusSay").value.trim();
  if (!said) return;
  $("#vestlusSay").value = "";
  vestlusTurn(said);
};

$("#vestlusSay").addEventListener("keydown", e => {
  if (e.key === "Enter") $("#vestlusSend").click();
});


/* Recording the speech eval set (ADR-0003).

   Local only: `/api/eval/available` is 404 on the deployment, so the block stays
   hidden there. Every clip is written next to what was actually read — and for
   a planted prompt, next to the word that was deliberately said wrong, which is
   what makes "did the engine correct my mistake away?" measurable. */
let evalNow = null, evalRecorder = null, evalChunks = [];
let evalQuestions = [], evalQuestionIdx = -1;
let reviewStem = "";

(async () => {
  try {
    await api("/api/eval/available", null, "GET");
    evalAvailable = true;
    $("#evalSet").hidden = false;
    if (practiceClip) $("#recSaveEval").hidden = false;
  } catch { /* Deployed, or the local server is unreachable. */ }
})();

function reviewReady() {
  $("#evalVerify").disabled = !reviewStem || !$("#evalListened").checked ||
    !$("#evalTranscript").value.trim();
}

$("#evalTranscript").addEventListener("input", reviewReady);
$("#evalListened").addEventListener("change", reviewReady);

async function saveEvalClip(task, blob, draft = {}) {
  const q = new URLSearchParams(task.question
    ? {question: task.question} : {text: task.text});
  if (task.planted) {
    q.set("planted", task.planted);
    q.set("accepted", task.correct);
  }
  const saved = await (await rawApi("/api/eval/clip?" + q, {
    method: "POST", headers: {"Content-Type": blob.type}, body: blob,
  })).json();
  reviewStem = saved.saved;
  $("#evalSet").open = true;
  $("#evalPlayback").src = URL.createObjectURL(blob);
  $("#evalPlayback").hidden = false;
  $("#evalReview").hidden = false;
  $("#evalTranscript").value = draft.transcript || "";
  $("#evalListened").checked = false;
  $("#evalPlanted").checked = false;
  $("#evalPlantedRow").hidden = !task.planted;
  $("#evalPlantedWord").textContent = task.planted || "";
  $("#evalReviewNote").textContent =
    `Запись ${saved.saved} сохранена. Прослушай её целиком и исправь текст.`;
  $("#evalCount").textContent = `записано: ${saved.clips}`;
  reviewReady();
  if (draft.transcript) {
    try {
      await api(`/api/eval/draft/${saved.saved}`,
        {text: draft.transcript, engine: draft.engine || ""});
    } catch (e) {
      $("#evalReviewNote").textContent += ` Черновик не сохранился: ${e.message}`;
    }
  }
  return saved;
}

$("#recSaveEval").onclick = async () => {
  if (!practiceClip) return;
  const btn = $("#recSaveEval");
  btn.disabled = true;
  try {
    const candidate = practiceClip;
    const saved = await saveEvalClip(candidate.task, candidate.blob, candidate);
    candidate.saved = saved.saved;
    btn.hidden = true;
    $("#evalReview").scrollIntoView({block: "nearest"});
  } catch (e) {
    $("#recState").textContent = `Не удалось сохранить запись: ${e.message}`;
  } finally { btn.disabled = false; }
};

$("#evalVerify").onclick = async () => {
  const btn = $("#evalVerify");
  if (!reviewStem || !$("#evalListened").checked) return;
  btn.disabled = true;
  try {
    const result = await (await api(`/api/eval/review/${reviewStem}`, {
      transcript: $("#evalTranscript").value.trim(), listened: true,
      planted_said: $("#evalPlanted").checked,
    })).json();
    $("#evalReviewNote").textContent =
      `Запись ${result.verified} проверена и готова к сравнению движков.`;
    reviewStem = "";
  } catch (e) {
    $("#evalReviewNote").textContent = `Не удалось подтвердить: ${e.message}`;
  } finally { reviewReady(); }
};

async function evalPrompt() {
  evalNow = null;
  $("#evalRec").disabled = true;
  $("#evalPlayback").hidden = true;
  $("#evalHeard").hidden = true;
  $("#evalPrompt").textContent = "";
  const answer = $("#evalMode").value === "answer";
  try {
    if (answer) {
      if (!evalQuestions.length) {
        const {questions} = await (await api("/api/speaking", null, "GET")).json();
        evalQuestions = questions.filter(q => q.question.length <= 220);
      }
      if (!evalQuestions.length) throw new Error("Вопросы сейчас недоступны.");
      evalQuestionIdx = (evalQuestionIdx + 1) % evalQuestions.length;
      const q = evalQuestions[evalQuestionIdx];
      evalNow = {question: q.question, text: "", planted: ""};
      $("#evalPrompt").textContent = q.question;
      $("#evalNote").textContent = q.hint_ru || "Ответь на вопрос своими словами.";
    } else {
      // About one in four reading prompts probes false acceptance of an error.
      const planted = Math.random() < 0.25;
      const got = await (await api(
        `/api/eval/prompt?planted=${planted}`, null, "GET")).json();
      evalNow = {...got, question: ""};
      $("#evalPrompt").textContent = got.text;
      $("#evalNote").innerHTML = md(got.note || "Прочитай вслух, как написано.");
    }
    $("#evalRec").disabled = false;
  } catch (e) {
    $("#evalNote").textContent = e.message;
  }
}

$("#evalNext").onclick = evalPrompt;
$("#evalMode").addEventListener("change", evalPrompt);

$("#evalRec").onclick = async () => {
  const btn = $("#evalRec");
  if (evalRecorder && evalRecorder.state === "recording") {
    evalRecorder.stop();
    return;
  }
  if (!evalNow) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    const task = evalNow;
    evalChunks = [];
    evalRecorder = new MediaRecorder(stream);
    evalRecorder.ondataavailable = e => e.data.size && evalChunks.push(e.data);
    evalRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      setLabel(btn, "● Salvesta");
      btn.disabled = true;
      const blob = new Blob(evalChunks, {type: evalRecorder.mimeType || "audio/webm"});
      const playback = $("#evalPlayback");
      playback.src = URL.createObjectURL(blob);
      playback.hidden = false;
      try {
        const saved = await saveEvalClip(task, blob);
        $("#evalNote").textContent = `Запись ${saved.saved} сохранена. Проверь её ниже.`;
        if (asrReady) {
          const heard = $("#evalHeard");
          heard.hidden = false;
          heard.innerHTML = `<span class="tag" lang="et">Kuuldi <i class="ru" lang="ru">черновик распознавания</i></span><div class="fix">…</div>`;
          try {
            const context = task.question
              ? "?" + new URLSearchParams({q: task.question}) : "";
            const t = await (await rawApi("/api/transcribe" + context, {
              method: "POST", headers: {"Content-Type": blob.type}, body: blob,
            })).json();
            if (t.text) {
              heard.innerHTML = `<span class="tag" lang="et">Kuuldi <i class="ru" lang="ru">черновик распознавания</i></span><div class="fix" lang="et">${esc(t.text)}</div><div class="why">${esc(t.engine)} · Не эталон: проверь на слух.</div>`;
              if (reviewStem === saved.saved && !$("#evalTranscript").value.trim()) {
                $("#evalTranscript").value = t.text;
                reviewReady();
              }
              try {
                await api(`/api/eval/draft/${saved.saved}`,
                  {text: t.text, engine: t.engine || ""});
              } catch (e) {
                $("#evalReviewNote").textContent += ` Черновик не сохранился: ${e.message}`;
              }
            } else {
              heard.innerHTML = `<span class="tag" lang="et">Kuuldi <i class="ru" lang="ru">черновик распознавания</i></span><div class="why">${esc(t.note || "Речь не разобрана.")} Запись сохранена; расшифруй её на слух.</div>`;
            }
          } catch (e) {
            heard.textContent = `Не удалось распознать: ${e.message}. Запись сохранена; расшифруй её на слух.`;
          }
        }
      } catch (e) {
        $("#evalNote").textContent = "Не сохранилось: " + e.message;
      } finally {
        btn.disabled = false;
        $("#evalNext").disabled = false;
        $("#evalMode").disabled = false;
      }
    };
    evalRecorder.start();
    setLabel(btn, "■ Lõpeta");
    $("#evalNext").disabled = true;
    $("#evalMode").disabled = true;
  } catch (e) {
    $("#evalNote").textContent = "Микрофон не открылся: " + e.message;
  }
};
