/* The little state two screens share.

   The chosen exam level is written by the exam screen and read by the rail on
   the review side. It lives here, behind functions, for one reason: an
   `export let` cannot be assigned from another module, and reading one during
   another module's evaluation is the temporal-dead-zone crash this page has
   already had once ("Cannot access 'examLevel' before initialization"). A
   function call has neither problem, whatever order the modules load in. */

export const LEVELS_UI = ["A2", "B1"];

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
