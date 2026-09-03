/* Service worker: makes the installed app start, and say something useful
   when there is no connection.

   What this deliberately does NOT do is pretend the app works offline. Drills
   are generated on the server -- `POST /api/practice` runs Vabamorf against
   the wordlist -- so no amount of caching puts an exercise on the screen
   without a connection. The manifest already made the app installable; what
   was missing was any behaviour once installed, so an installed copy failed
   exactly like a browser tab with the network off, which is the worst of both.

   Three rules, and the second two matter more than the first:

   1. **The shell is cached, but code is never served stale.** The icons and
      the manifest are cache-first: they change when the app is redeployed and
      almost never otherwise. The page, the stylesheet and the ES modules are
      *network-first with a cached fallback* -- fetched fresh when there is a
      connection, served from disk when there is not.

      That distinction is load-bearing, and it was not needed until the app
      stopped being one file. While every line of JavaScript lived inside
      `index.html`, the navigation branch below fetched it fresh on every load
      and staleness was impossible. Split into `/app.css` and `/js/*.js`, with
      no build step to put a hash in the filename, cache-first would mean a
      redeploy that did not also edit this file served last week's code against
      this week's markup -- for ever, because the URLs never change.

   2. **The API is never cached. Not once, not stale-while-revalidate.**
      Every endpoint here is either the learner's own state (progress, review
      queue, vocabulary status) or freshly generated (drills, dictation). A
      cached `/api/review` would show a due count that is already wrong; a
      cached `/api/practice` would serve the same ten items forever and the
      mastery gate would count them. Study data has to be true, and a drill
      that is quietly a day old is worse than a drill that is unavailable.

   3. **Nothing that is not a clean 200 from this origin is stored.**
      Cloudflare Access guards this app, and a signed-out request gets a 302 to
      a login page. Caching that would pin the login redirect in front of the
      app until the cache was cleared -- from the learner's side, an app that
      had permanently broken itself. */

/* Stamped by the server with the running build's revision -- see
   `api/assets.py::service_worker`. The literal below is what a source checkout
   uses, and what the tests read.

   It has to be derived, not typed. The cache name is the only thing that
   retires an old shell: `activate` deletes every cache that is not the current
   one, so a redeploy that did not also edit this line left the previous
   `index.html` in the cache for ever -- and that page names the modules it
   loads. A hand-bumped version is a hand-maintained list of one, and this
   project has an entry in `docs/lessons.md` about every other one it has had. */
const VERSION = "dev";
const SHELL = `shell-${VERSION}`;

/* `/` is listed rather than `/index.html`: it is what the manifest's
   `start_url` opens and what a navigation requests.

   The stylesheet and the modules are listed too, and they have to be: the page
   is cached shell-first, so an offline open that could not fetch `/app.css`
   and `/js/*.js` would paint an unstyled document with no behaviour -- worse
   than the offline notice, because it looks like the app.

   This list and the page's own `<link>`/`<script src>` tags are two halves of
   one fact, and `tests/test_service_worker.py` checks them against each other
   in both directions. A hand-kept list that drifts from the thing it describes
   is the failure mode this project keeps paying for; here it cannot drift
   silently. */
const ASSETS = [
  "/", "/manifest.webmanifest", "/icon.svg", "/icon.png", "/app.css",
  "/js/main.js", "/js/core.js", "/js/state.js", "/js/router.js",
  "/js/chrome.js", "/js/media.js", "/js/path.js", "/js/review.js",
  "/js/vocab.js", "/js/reading.js", "/js/listen.js", "/js/speak.js",
  "/js/exam.js", "/js/write.js",
];

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    // Individually, not `addAll`: that rejects the whole install if one asset
    // 404s, and a worker that fails to install leaves the app with no offline
    // behaviour at all because one icon was renamed.
    await Promise.all(ASSETS.map(async url => {
      try {
        const res = await fetch(url, {cache: "reload"});
        if (res.ok && !res.redirected) await cache.put(url, res);
      } catch (err) { /* offline during install: nothing to cache, carry on */ }
    }));
    // Take over on the next load rather than waiting for every tab to close.
    // Safe here because the worker holds no state a previous version could be
    // mid-way through.
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    // Drop caches from earlier versions, or a redeploy leaves the previous
    // shell on disk forever and the app boots into last week's page.
    const names = await caches.keys();
    await Promise.all(
      names.filter(n => n !== SHELL).map(n => caches.delete(n)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const {request} = event;
  const url = new URL(request.url);

  // Only this origin, only GET. A POST is an action -- answering a drill,
  // marking a word known -- and replaying one from a cache would record
  // something the learner did not do.
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Rule 2. Let the API go to the network untouched, including its failures:
  // the page already knows how to render an error, and a stale success would
  // be indistinguishable from a real one.
  if (url.pathname.startsWith("/api/")) return;

  // A navigation is the case that decides whether the app opens at all.
  if (request.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const res = await fetch(request);
        // Keep the offline copy current. Without this the cached shell is
        // whatever `install` happened to fetch and never changes again inside
        // one version -- so the page served with no connection could name
        // modules the deployment has since renamed.
        if (res.ok && !res.redirected && res.type === "basic") {
          const cache = await caches.open(SHELL);
          cache.put("/", res.clone());
        }
        return res;
      } catch (err) {
        const cached = await caches.match("/");
        return cached || new Response(
          OFFLINE_PAGE, {status: 503, headers: {"Content-Type": "text/html; charset=utf-8"}});
      }
    })());
    return;
  }

  // The page's own code. Fresh when online, cached when not -- see rule 1.
  // `/app.css` and `/js/*.js` are unhashed URLs, so this is the only thing
  // standing between a redeploy and a permanently stale app.
  if (url.pathname === "/app.css" || url.pathname.startsWith("/js/")) {
    event.respondWith((async () => {
      try {
        const res = await fetch(request);
        if (res.ok && !res.redirected && res.type === "basic") {
          const cache = await caches.open(SHELL);
          cache.put(request, res.clone());
        }
        return res;
      } catch (err) {
        // Offline: the copy from the last successful load is exactly right.
        const cached = await caches.match(request);
        return cached || new Response("", {status: 504});
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
      const res = await fetch(request);
      // Rule 3: only a clean, unredirected 200 from this origin is kept.
      if (res.ok && !res.redirected && res.type === "basic") {
        const cache = await caches.open(SHELL);
        cache.put(request, res.clone());
      }
      return res;
    } catch (err) {
      return new Response("", {status: 504});
    }
  })());
});

/* Shown only if the shell itself was never cached -- a first run with no
   connection. In Russian, because it is the one thing on screen and it has to
   be read. */
const OFFLINE_PAGE = `<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Нет соединения</title>
<style>body{font:16px/1.5 system-ui,sans-serif;margin:0;min-height:100vh;
display:grid;place-items:center;background:#faf9f6;color:#1b1b19;padding:24px}
div{max-width:32ch;text-align:center}h1{font-size:19px;margin:0 0 8px}
p{margin:0;color:#6b6b66}</style>
<div><h1>Нет соединения</h1>
<p>Упражнения создаются на сервере, поэтому без интернета их не открыть.
Попробуй ещё раз, когда связь появится.</p></div>`;
