/* The selection glides.

   Every tab list (the modes, each mode's tabs, Minu rada / Vaba harjutus, A2 / B1)
   carries one capsule that slides to the selected tab, the way a Liquid Glass tab
   bar moves its lens, instead of the old capsule vanishing here and appearing
   there. Nothing opts in: anything with `role="tablist"`, in the markup or added
   later, glides. Without this script each tab paints its own capsule (`app.css`),
   so the page reads the same, only still. Reduced motion makes the slide instant
   (the global rule in `app.css`). */

const done = new WeakSet();

function place(list, pill) {
  const tab = list.querySelector('[role="tab"][aria-selected="true"]');
  if (!tab || !tab.offsetWidth || !list.offsetWidth) {
    // Hidden (another mode's tabs): the next showing jumps, it does not slide
    // in from wherever the capsule was left.
    pill.hidden = true;
    return;
  }
  const jump = pill.hidden;
  pill.hidden = false;
  if (jump) pill.classList.add("glide-jump");
  pill.style.width = tab.offsetWidth + "px";
  pill.style.height = tab.offsetHeight + "px";
  pill.style.transform = `translate(${tab.offsetLeft}px, ${tab.offsetTop}px)`;
  if (jump) {
    void pill.offsetWidth;   // commit the jump before transitions return
    pill.classList.remove("glide-jump");
  }
}

export function glide(list) {
  if (done.has(list)) return;
  done.add(list);
  const pill = document.createElement("span");
  pill.className = "glide";
  pill.hidden = true;
  pill.setAttribute("aria-hidden", "true");
  list.prepend(pill);
  list.classList.add("gliding");
  const again = () => place(list, pill);
  new MutationObserver(again).observe(list, {
    subtree: true, attributes: true, attributeFilter: ["aria-selected"]});
  // Size changes move tabs without a new selection: the folding dock, the font
  // arriving, a gloss appearing, the spine and the phone swapping layouts.
  const sized = new ResizeObserver(again);
  sized.observe(list);
  list.querySelectorAll('[role="tab"]').forEach(t => sized.observe(t));
  again();
}

document.querySelectorAll('[role="tablist"]').forEach(glide);
new MutationObserver(records => {
  for (const r of records) for (const n of r.addedNodes) {
    if (n.nodeType !== 1) continue;
    if (n.matches('[role="tablist"]')) glide(n);
    n.querySelectorAll('[role="tablist"]').forEach(glide);
  }
}).observe(document.body, {childList: true, subtree: true});
