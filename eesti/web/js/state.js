/* The little state two screens share.

   The chosen exam level is written by the exam screen and read by the review
   rail. It sits behind functions because an `export let` cannot be assigned from
   another module, and reading one during another module's evaluation hits the
   temporal dead zone. A function call works whatever order the modules load in. */

const LEVELS_UI = ["A2", "B1"];

let level = "A2";

try {
  const saved = localStorage.getItem("examLevel");
  if (LEVELS_UI.includes(saved)) level = saved;
} catch (e) { /* private mode, or storage disabled: the default is fine */ }

export function examLevel() { return level; }

export function setExamLevel(next) {
  level = next;
  try { localStorage.setItem("examLevel", next); } catch (e) { /* see above */ }
}
