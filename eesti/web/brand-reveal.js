/* Inlined by api/assets.py into head: eligibility is decided before the body
   appears, with no additional fetch. The mobile passage lasts 900 ms and
   never waits for a font, module, network response, or learner data. */
(() => {
  const root = document.documentElement;
  try {
    const phone = matchMedia("(pointer: coarse) and (hover: none) and (max-width: 719px), (pointer: coarse) and (hover: none) and (max-width: 1023px) and (max-height: 559px)");
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    if (!phone.matches || reduced.matches || document.prerendering) return;
    const navigation = performance.getEntriesByType("navigation")[0];
    if (navigation && navigation.type === "back_forward") return;
    if (navigation?.type !== "reload" && document.referrer &&
        new URL(document.referrer).origin === location.origin) return;

    root.dataset.brandReveal = "";
    const finish = () => {
      delete root.dataset.brandReveal;
      document.getElementById("brandSplash")?.remove();
    };
    // Independent CSS dismissal covers an interrupted script as well.
    setTimeout(finish, 900);
    addEventListener("pagehide", finish, {once: true});
    addEventListener("pageshow", event => { if (event.persisted) finish(); });
    reduced.addEventListener("change", event => { if (event.matches) finish(); });
    // A learner can proceed immediately with a touch or key; no focus trap.
    addEventListener("pointerdown", finish, {once: true, passive: true});
    addEventListener("keydown", finish, {once: true});
  } catch (_) { delete root.dataset.brandReveal; }
})();
