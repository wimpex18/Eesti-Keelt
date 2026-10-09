/* Starting choices are navigation. Only server-checked probes award mastery. */
import {$, api, attribHtml, esc, setLabel, wrongVerdict} from "./core.js";
import {goToPlace} from "./router.js";
const LEVELS = [
  ["a1", "Tean mõnda sõna", "Знаю отдельные слова — начальные темы"],
  ["a1-a2", "Saan lihtsast jutust aru", "Понимаю простые фразы — начальные темы"],
  ["a2", "Räägin tuttavatel teemadel", "Общаюсь на знакомые темы — после начальных тем"],
  ["a2-b1", "Liigun edasi", "Хочу двигаться дальше — после базовых тем"],
];
let busy = false, seen = [], failed = [], probe = null, entry = null;
const out = () => $("#onboardingContent");
function route(tab) {
  goToPlace(tab);
  if (location.hash !== "#" + tab) history.pushState(null, "", "#" + tab);
}
function error(message, retry) {
  const box = out().querySelector(".start-error");
  box.hidden = false; box.textContent = message;
  if (retry) {
    const b = document.createElement("button"); b.className = "ghost"; b.lang = "et";
    b.innerHTML = '<span lang="et">Proovi uuesti <span class="ru" lang="ru">попробовать снова</span></span>';
    b.onclick = retry; box.appendChild(b);
  }
}
function frame(body, back = renderStart) {
  out().innerHTML = body + '<p class="start-error banner" role="alert" hidden></p>';
  out().querySelector("[data-back]")?.addEventListener("click", back);
  const heading = out().querySelector("h2");
  if (heading && !$("#tab-start").hidden) {
    heading.tabIndex = -1;
    heading.focus({preventScroll: true});
  }
}
const START_MARKUP = $("#onboardingContent").innerHTML;

export function renderStart() {
  frame(START_MARKUP);
  out().querySelectorAll("button").forEach(b => b.disabled = false);
  out().querySelector("[data-start]").onclick = () => chooseGoal("a0");
  out().querySelector("[data-choose]").onclick = renderLevels;
  out().querySelector("[data-assess]").onclick = () => {seen = []; failed = []; nextProbe();};
}
function renderLevels() {
  frame(`<h2 class="page-title" lang="et">Vali oma algus <i class="ru" lang="ru">выбери точку старта</i></h2>
    <p lang="ru">Знакомые темы останутся в курсе с отметкой «пропущено». Их можно вернуть. Освоение засчитывается только после проверки.</p>
    <div class="start-routes">${LEVELS.map(([band, et, ru]) => `<button class="start-route" data-band="${band}" lang="et"><strong>${et}</strong><span lang="ru">${ru}</span></button>`).join("")}</div>
    <button class="ghost" data-back lang="et">Tagasi <span class="ru" lang="ru">назад</span></button>`);
  out().querySelectorAll("[data-band]").forEach(b => b.onclick = () => chooseGoal(b.dataset.band));
}
function chooseGoal(band) {
  frame(`<h2 class="page-title" lang="et">Milleks õpid? <i class="ru" lang="ru">для чего учишься?</i></h2>
    <p lang="ru">Оба направления доступны всегда. Сейчас выберем первый шаг.</p>
    <div class="start-routes"><button class="start-route" data-focus="path" lang="et"><strong>Igapäevane eesti keel</strong><span lang="ru">Учиться для жизни: темы курса и четыре навыка.</span></button>
    <button class="start-route" data-focus="exam" lang="et"><strong>Valmistun eksamiks</strong><span lang="ru">Подготовка A2/B1: задания и пробный экзамен.</span></button></div>
    <button class="ghost" data-back lang="et">Tagasi <span class="ru" lang="ru">назад</span></button>`,
    band === "a0" ? renderStart : renderLevels);
  out().querySelectorAll("[data-focus]").forEach(b => b.onclick = () => save(band, b.dataset.focus, true));
}
async function save(band, focus = "path", navigate = false) {
  if (busy) return; busy = true;
  out().querySelectorAll("button").forEach(b => b.disabled = true);
  try {
    await api("/api/me/onboarding", {start_band: band, focus, navigate,
      explanation_language: "ru", skipped: false});
    route(focus === "exam" ? "exam" : "path");
  } catch (e) { error(e.message); }
  finally { busy = false; out().querySelectorAll("button").forEach(b => b.disabled = false); }
}
async function nextProbe() {
  frame('<h2 class="page-title" lang="et">Proovin ennast <i class="ru" lang="ru">короткая проверка</i></h2><p role="status" lang="ru">Подбираю задания…</p>');
  try {
    const query = new URLSearchParams({seen: seen.join(","), failed: failed.join(","), limit: "3"});
    const result = await api("/api/placement/next?" + query, null, "GET").then(r => r.json());
    entry = result.entry;
    if (result.done) { showResult(); return; }
    probe = result.next;
    frame(`<h2 class="page-title" lang="et">${esc(probe.et)}</h2><p lang="ru">Тема ${seen.length + 1} из максимум 3. Проверяются только эти задания; это не экзамен CEFR.</p>
      <form id="placementForm">${probe.items.map((it, i) => `<label class="placement-task" lang="et">${esc(it.prompt)}
        <span class="hint">${esc([it.lemma, it.label].filter(Boolean).join(", "))}${(probe.glosses || {})[it.lemma]?.length
          ? ` <i lang="ru">${esc(probe.glosses[it.lemma].join(", "))}</i>` : ""}</span><input name="answer${i}" aria-label="Vastus ${i + 1} — ответ" lang="et" required autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false">${attribHtml(it)}</label>`).join("")}
      <button class="go" type="submit" lang="et">Kontrolli <span class="ru" lang="ru">проверить</span></button></form>
      <button class="quiet" data-stop lang="et">Lõpeta siin <span class="ru" lang="ru">закончить здесь</span></button>`);
    out().querySelector("[data-stop]").onclick = showResult;
    out().querySelector("form").onsubmit = async event => {
      event.preventDefault(); if (busy) return; busy = true;
      const form = event.currentTarget, b = form.querySelector("button"); b.disabled = true; setLabel(b, "Kontrollin…");
      try {
        const r = await api(`/api/testout/${encodeURIComponent(probe.topic)}`, {seed: probe.seed,
          given: [...form.querySelectorAll("input")].map(input => input.value)}).then(response => response.json());
        seen.push(probe.topic); if (!r.passed) failed.push(probe.topic);
        // Each answer, with the right form where it was wrong.
        const review = (r.items || []).map(row => `<li lang="et">${esc(row.solution)}
          ${row.correct ? "✓" : `<span class="verdict no">${wrongVerdict(row.given, row.answer, "")}</span>`}</li>`).join("");
        frame(`<h2 class="page-title" lang="et">${esc(probe.et)}</h2><p class="verdict ${r.passed ? "ok" : "no"}" lang="ru">${r.correct} из ${r.asked} верно. ${r.passed ? "Тема засчитана по проверенным ответам." : "Тема остаётся для изучения."}</p>${review ? `<ul class="placement-review">${review}</ul>` : ""}<button class="go" data-next lang="et">Edasi <span class="ru" lang="ru">дальше</span></button>`);
        out().querySelector("[data-next]").onclick = nextProbe;
      } catch (e) { error(e.message); b.disabled = false; setLabel(b, "Kontrolli"); }
      finally { busy = false; }
    };
  } catch (e) { error(e.message, nextProbe); }
}
function showResult() {
  frame(`<h2 class="page-title" lang="et">Sinu algus <i class="ru" lang="ru">твоя точка старта</i></h2>
    <p lang="ru">${seen.length ? `Проверено тем: ${seen.length}.` : "Проверка остановлена без результата."} ${entry ? `Начни с темы <span lang="et">${esc(entry.et)}</span>.` : "Начни с первой доступной темы курса."} Можно пропускать знакомое и возвращаться.</p>
    <p class="hint" lang="ru">Проверка касается грамматики; уровень CEFR не подтверждён.</p>
    <button class="go" data-save lang="et">Alusta õppimist <span class="ru" lang="ru">начать учиться</span></button>
    <button class="ghost" data-back lang="et">Muuda algust <span class="ru" lang="ru">выбрать иначе</span></button>`);
  out().querySelector("[data-save]").onclick = () => save("unsure");
}
export async function maybeShowOnboarding({force = false} = {}) {
  try {
    const me = await api("/api/me", null, "GET").then(r => r.json());
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
