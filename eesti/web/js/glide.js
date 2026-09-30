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

/* Adapted from WanderAlt's press/slide/release lens. Only the phone's two
   navigation rows opt in; ordinary segmented controls keep their quiet glide.
   The lens is an inert visual copy, so previews never activate a panel. */
function glassTabs(list, pill) {
  if (!list.matches('.modes, nav[data-mode-nav]')) return;
  const phone = matchMedia('(pointer: coarse) and (hover: none) and (max-width: 719px), (pointer: coarse) and (hover: none) and (max-width: 1079px) and (max-height: 559px)');
  const tabs = [...list.querySelectorAll('[role="tab"]')];
  const lens = document.createElement('span');
  lens.className = 'glass-lens glass';
  lens.setAttribute('aria-hidden', 'true');
  lens.inert = true;
  const copy = document.createElement('span');
  copy.className = 'glass-copy';
  lens.append(copy);
  list.append(lens);
  list.classList.add('glass-tabs');
  let gesture = null, frame = 0, swallow = false, committing = false;
  const selected = () => tabs.find(t => t.getAttribute('aria-selected') === 'true') || tabs[0];
  const nearest = x => tabs.reduce((best, tab) =>
    Math.abs(x - tab.offsetLeft - tab.offsetWidth / 2) <
    Math.abs(x - best.offsetLeft - best.offsetWidth / 2) ? tab : best, tabs[0]);
  const localX = x => x - list.getBoundingClientRect().left + list.scrollLeft;

  function syncCopy() {
    const clones = tabs.map(tab => {
      const option = document.createElement('span');
      option.className = 'glass-option';
      for (const child of tab.childNodes) option.append(child.cloneNode(true));
      option.querySelectorAll('[id]').forEach(n => n.removeAttribute('id'));
      const style = getComputedStyle(tab);
      // Exact source geometry, including a folded dock, loaded fonts and badges.
      for (const key of ['display', 'flexDirection', 'alignItems', 'justifyContent',
        'gap', 'padding', 'fontFamily', 'fontSize', 'fontWeight', 'lineHeight',
        'letterSpacing', 'gridTemplateColumns', 'columnGap', 'textAlign'])
        option.style[key] = style[key];
      Object.assign(option.style, {left: tab.offsetLeft + 'px', top: tab.offsetTop + 'px',
        width: tab.offsetWidth + 'px', height: tab.offsetHeight + 'px'});
      return option;
    });
    copy.replaceChildren(...clones);
    copy.style.width = list.scrollWidth + 'px';
    copy.style.height = list.clientHeight + 'px';
  }

  function aim(x, tab) {
    const width = Math.min(list.clientWidth, tab.offsetWidth * 1.16 + 8);
    const height = tab.offsetHeight + 8;
    const left = Math.max(list.scrollLeft, Math.min(x - width / 2,
      list.scrollLeft + list.clientWidth - width));
    const top = tab.offsetTop - 4;
    Object.assign(lens.style, {width: width + 'px', height: height + 'px',
      transform: `translate3d(${left}px, ${top}px, 0)`});
    copy.style.left = -left + 'px';
    copy.style.top = -top + 'px';
    copy.style.transformOrigin = `${left + width / 2}px ${top + height / 2}px`;
  }

  function preview() {
    if (!gesture?.lifted) return;
    const x = localX(gesture.x);
    gesture.tab = nearest(x);
    aim(x, gesture.tab);
  }

  function edgeScroll() {
    if (!gesture?.lifted) return;
    const rect = list.getBoundingClientRect();
    const edge = 32;
    let delta = 0;
    if (gesture.x > rect.right - edge) { delta = 7; }
    else if (gesture.x < rect.left + edge) { delta = -7; }
    if (delta && list.scrollWidth > list.clientWidth) {
      list.scrollLeft += delta;
      preview();
    }
    frame = requestAnimationFrame(edgeScroll);
  }

  function lift() {
    if (!gesture || gesture.lifted) return;
    gesture.lifted = true;
    syncCopy();
    preview();
    list.classList.add('glass-dragging');
    try { list.setPointerCapture(gesture.id); } catch (_) { /* pointer ended */ }
    frame = requestAnimationFrame(edgeScroll);
  }

  function end(cancelled) {
    if (!gesture) return;
    const {id, lifted, tab, timer} = gesture;
    clearTimeout(timer);
    gesture = null;
    cancelAnimationFrame(frame);
    list.classList.remove('glass-dragging');
    try { if (list.hasPointerCapture(id)) list.releasePointerCapture(id); } catch (_) {}
    if (!lifted) return;
    const target = cancelled ? selected() : tab;
    aim(target.offsetLeft + target.offsetWidth / 2, target);
    if (!cancelled && target !== selected()) {
      committing = true;
      target.click(); // Existing router owns URL history, focus and panel loading.
      committing = false;
    }
    place(list, pill);
    swallow = true;
    // Only swallow the pointer-generated click, never keyboard or scripted clicks.
    setTimeout(() => { swallow = false; }, 450);
  }

  list.addEventListener('pointerdown', event => {
    if (!phone.matches || !event.isPrimary || event.button !== 0 || gesture ||
        !event.target.closest('[role="tab"]')) return;
    swallow = false;
    gesture = {id: event.pointerId, x0: event.clientX, y0: event.clientY,
      x: event.clientX, lifted: false, tab: selected()};
    gesture.timer = setTimeout(lift, 140);
  });
  list.addEventListener('pointermove', event => {
    if (!gesture || gesture.id !== event.pointerId) return;
    const dx = Math.abs(event.clientX - gesture.x0);
    const dy = Math.abs(event.clientY - gesture.y0);
    if (!gesture.lifted && dy > 6 && dy > dx) { end(true); return; }
    gesture.x = event.clientX;
    if (!gesture.lifted && dx < 6) return;
    clearTimeout(gesture.timer);
    lift();
    event.preventDefault();
    preview();
  });
  list.addEventListener('pointerup', event => {
    if (gesture?.id === event.pointerId) end(false);
  });
  list.addEventListener('pointercancel', event => {
    if (gesture?.id === event.pointerId) end(true);
  });
  list.addEventListener('lostpointercapture', event => {
    // Touch begins with implicit capture on the tab; transferring it to the
    // list emits a bubbled loss from that tab, which is not a cancellation.
    if (event.target === list && gesture?.id === event.pointerId) end(true);
  });
  list.addEventListener('keydown', () => end(true));
  list.addEventListener('click', event => {
    if (swallow && !committing && event.detail > 0) {
      event.preventDefault(); event.stopImmediatePropagation(); swallow = false;
    }
  }, true);
  list.addEventListener('contextmenu', event => { if (phone.matches) event.preventDefault(); });
  list.addEventListener('scroll', preview, {passive: true});
  new ResizeObserver(() => { end(true); }).observe(list);
  phone.addEventListener('change', () => end(true));
  addEventListener('pagehide', () => end(true));
  addEventListener('blur', () => end(true));
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
  glassTabs(list, pill);
}

document.querySelectorAll('[role="tablist"]').forEach(glide);
new MutationObserver(records => {
  for (const r of records) for (const n of r.addedNodes) {
    if (n.nodeType !== 1) continue;
    if (n.matches('[role="tablist"]')) glide(n);
    n.querySelectorAll('[role="tablist"]').forEach(glide);
  }
}).observe(document.body, {childList: true, subtree: true});
