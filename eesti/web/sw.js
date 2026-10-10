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
  "/js/dictionary.js", "/js/session.js",
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
   be read. On the app's own ground and ink (DESIGN.md), in system fonts so it
   asks for nothing; it follows a saved appearance as the shell does. */
const OFFLINE_PAGE = `<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#F1F4F1" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#141F19" media="(prefers-color-scheme: dark)">
<title>Нет соединения</title>
<script>try{const t=localStorage.getItem("theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t}catch(e){}</script>
<style>:root{--ground:#F1F4F1;--ink:#15201A;--muted:#56635B;--act:#15201A;--on-act:#FFFFFF;--on-act-gloss:#D0D2D1;--focus:#2645B5;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#141F19;--ink:#E8EFEA;--muted:#A1AEA6;
--act:#E8EFEA;--on-act:#141F19;--on-act-gloss:#3E4943;--focus:#A9BCFF;color-scheme:dark}}
:root[data-theme="dark"]{--ground:#141F19;--ink:#E8EFEA;--muted:#A1AEA6;--act:#E8EFEA;--on-act:#141F19;
--on-act-gloss:#3E4943;--focus:#A9BCFF;color-scheme:dark}
*{box-sizing:border-box}body{font:1rem/1.5 system-ui,sans-serif;margin:0;min-height:100vh;
display:grid;place-items:center;background:var(--ground);color:var(--ink);
padding:24px max(16px,env(safe-area-inset-right)) 24px max(16px,env(safe-area-inset-left))}
main{width:100%;max-width:36ch}h1{font-size:1.5rem;line-height:1.25;font-weight:600;margin:0 0 12px}
p{margin:0 0 24px;color:var(--muted)}
a{display:inline-flex;align-items:baseline;gap:6px;min-height:48px;padding:12px 24px;
border-radius:14px;background:var(--act);color:var(--on-act);font-weight:600;text-decoration:none}
a:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.ru{font-size:.75rem;font-weight:400;color:var(--on-act-gloss)}</style>
<main><h1>Нет соединения</h1>
<p>Приложение ещё не сохранено для работы без сети.
Подключись к интернету и попробуй снова.</p>
<a href="/" lang="et">Proovi uuesti <span class="ru" lang="ru">повторить</span></a></main>`;
