/* Service worker: the installed app starts, and says something useful offline.

   It does not pretend the app works offline: drills are generated on the server.

   1. **Code is never served stale.** Icons and the manifest are cache-first. The
      page, stylesheet and ES modules are network-first with a cached fallback,
      because their URLs are unhashed (no build step).
   2. **The API is never cached** — it is learner state or freshly generated.
   3. **Only clean 200 responses from this origin are stored** — caching Access's
      302 to a login page would pin it in front of the app. */

/* Stamped by the server with the build's revision (`api/assets.py::service_worker`);
   the literal is what a source checkout uses and what the tests read. The cache
   name retires old shells, so it must change with every build. */
const VERSION = "dev";
const SHELL = `shell-${VERSION}`;

/* The precached shell. `/`, not `/index.html` (what `start_url` opens). The
   stylesheet and modules are included so an offline open is not unstyled.
   `tests/test_service_worker.py` checks this list against the page's tags in both
   directions. */
const ASSETS = [
  "/", "/manifest.webmanifest", "/icon.svg", "/icon.png", "/app.css",
  "/js/main.js", "/js/core.js", "/js/state.js", "/js/router.js",
  "/js/chrome.js", "/js/media.js", "/js/path.js", "/js/review.js",
  "/js/vocab.js", "/js/reading.js", "/js/listen.js", "/js/speak.js",
  "/js/exam.js", "/js/mock.js", "/js/write.js", "/js/sources.js",
];

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    // Individually, not `addAll`, so one missing asset does not fail the install.
    await Promise.all(ASSETS.map(async url => {
      try {
        const res = await fetch(url, {cache: "reload"});
        if (res.ok && !res.redirected) await cache.put(url, res);
      } catch (err) { /* offline during install: nothing to cache, carry on */ }
    }));
    // Take over on the next load; the worker holds no state an old version could be
    // mid-way through.
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    // Delete caches from earlier versions.
    const names = await caches.keys();
    await Promise.all(
      names.filter(n => n !== SHELL).map(n => caches.delete(n)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const {request} = event;
  const url = new URL(request.url);

  // Only this origin, only GET: replaying a POST would record something the learner
  // did not do.
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Rule 2: API requests go to the network untouched, including failures.
  if (url.pathname.startsWith("/api/")) return;

  // A navigation is the case that decides whether the app opens at all.
  if (request.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const res = await fetch(request);
        // Refresh the cached page on every successful load, so the offline copy matches the
        // deployment.
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
