/* Service worker: the installed app starts, and says something useful offline.

   New drills require the server. Previously downloaded packs are handled by
   offline.js; this worker keeps the shell readable and APIs uncached.

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
  "/favicon.ico", "/apple-touch-icon.png",
  "/brand/mark.svg", "/brand/favicon.svg", "/brand/favicon-32.png",
  "/brand/safari-pinned-tab.svg", "/brand/icon-192.png", "/brand/icon-512.png",
  "/brand/icon-maskable.png", "/brand/icon-mono.png",
  "/js/main.js", "/js/core.js", "/js/state.js", "/js/router.js", "/js/profile.js",
  "/js/onboarding.js",
  "/js/chrome.js", "/js/media.js", "/js/path.js", "/js/review.js",
  "/js/vocab.js", "/js/voice.js", "/js/reading.js", "/js/listen.js", "/js/speak.js",
  "/js/exam.js", "/js/mock.js", "/js/offline.js", "/js/write.js", "/js/sources.js",
  "/js/remind.js", "/js/icons.js", "/js/words.js", "/js/lesson.js",
  "/fonts/geologica-latin.woff2", "/fonts/geologica-latin-ext.woff2",
  "/fonts/geologica-cyrillic.woff2",
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

/* Reminders (`eesti/reminders.py`, sent by the Worker's cron).

   The payload carries a count and a fixed phrase — never a sentence the
   learner wrote — so nothing private is handed to Apple's or Google's push
   service even before encryption. A tag means the same fact replaces itself
   on screen rather than stacking. */
self.addEventListener("push", event => {
  let said = {};
  try {
    said = event.data ? event.data.json() : {};
  } catch { said = {}; }
  const title = said.title || "Eesti keel";
  event.waitUntil(self.registration.showNotification(title, {
    body: said.body || "",
    tag: said.tag || "eesti",
    lang: "ru",
    icon: "/icon.png",
    badge: "/icon.png",
    data: {url: said.url || "/"},
  }));
});

/* One tap opens the app where the reminder was about, reusing the window that
   is already open rather than adding another. */
self.addEventListener("notificationclick", event => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil((async () => {
    const open = await self.clients.matchAll({type: "window", includeUncontrolled: true});
    for (const client of open) {
      if (new URL(client.url).origin === self.location.origin) {
        await client.focus();
        return client.navigate(target).catch(() => {});
      }
    }
    return self.clients.openWindow(target);
  })());
});

/* Shown only if the shell itself was never cached -- a first run with no
   connection. In Russian, because it is the one thing on screen and it has to
   be read. */
const OFFLINE_PAGE = `<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Нет соединения</title>
<style>*{box-sizing:border-box}body{font:16px/1.6 system-ui,sans-serif;margin:0;
min-height:100vh;display:grid;place-items:center;background:#f0f6fd;color:#172f4b;padding:24px}
main{width:100%;max-width:36ch}h1{font-size:24px;line-height:1.3;margin:0 0 12px}
p{margin:0 0 24px;color:#506681}
a{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:12px 16px;
border-radius:12px;background:#2359c4;color:#fff;font-weight:600;text-decoration:none}
a:focus-visible{outline:3px solid #2359c4;outline-offset:4px}
.ru{font-size:14px;font-weight:400}
@media (prefers-color-scheme:dark){body{background:#152236;color:#edf4ff}
p{color:#b3c5de}a{background:#aac9ff;color:#16345e}
a:focus-visible{outline-color:#aac9ff}}</style>
<main><h1>Нет соединения</h1>
<p>Приложение ещё не сохранено для работы без сети.
Подключись к интернету и попробуй снова.</p>
<a href="/" lang="et">Proovi uuesti <span class="ru" lang="ru">повторить</span></a></main>`;
