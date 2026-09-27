/**
 * The guest door (ADR-0006): the same app, no sign-in, nothing permanent.
 *
 * Deployed as `wrangler deploy --env guest` (`eesti-keelt-guest`), beside the
 * owner's Worker (`deploy/worker.ts`) and in front of the same Cloud Run
 * origin. It holds `GUEST_PROXY_TOKEN` and not the owner's `PROXY_TOKEN`, so
 * the origin files every request it forwards under a guest sandbox, whatever
 * the request says about itself. It has no Durable Object, no snapshots, no
 * reminder cron, no Workers AI and no route to the owner's Mac mini: guest
 * progress lives on the container's disk and is meant to vanish.
 *
 * SKELETON. `docs/identity.md` ("Guest Worker") is the specification; the
 * TODOs below are what is left.
 */

interface GuestEnv {
  /** Base URL of the Cloud Run service; the same origin as the owner's Worker. */
  CLOUD_RUN_URL: string;
  /** The guest's secret. The origin maps it to guest scope. */
  GUEST_PROXY_TOKEN: string;
}

/** Routes that must never be reachable from here, whatever the origin says. */
const REFUSED = [
  "/api/events",
  "/api/events/import",
  "/api/state/export",
  "/api/state/import",
  "/api/content/export",
  "/api/content/import",
  "/api/progress/reset",
  "/api/reminders",
];

/** Request headers a caller may not set: the front door sets them or nobody does. */
const FRONT_DOOR_HEADERS = ["x-proxy-token", "x-state-token", "x-eesti-scope", "x-eesti-email"];

export default {
  async fetch(request: Request, env: GuestEnv): Promise<Response> {
    if (!env.CLOUD_RUN_URL || !env.GUEST_PROXY_TOKEN) {
      return new Response("The guest door is not configured. See docs/identity.md.",
        { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } });
    }
    const url = new URL(request.url);
    if (REFUSED.includes(url.pathname) || url.pathname.startsWith("/api/push/")) {
      return new Response("not found", { status: 404 });
    }
    // TODO(Luna): `/api/transcribe` has no engine here; answer the degraded
    // body `deploy/worker.ts` returns when no engine is bound, so the page
    // falls back to typing. `/api/asr/home` answers `{configured: false}`.

    const headers = new Headers(request.headers);
    for (const name of FRONT_DOOR_HEADERS) headers.delete(name);
    headers.set("x-proxy-token", env.GUEST_PROXY_TOKEN);
    headers.delete("host");
    try {
      return await fetch(new Request(new URL(url.pathname + url.search, env.CLOUD_RUN_URL), {
        method: request.method,
        headers,
        body: request.body,
        redirect: "manual",
      }));
    } catch (error) {
      return new Response(
        `The app is unreachable: ${error instanceof Error ? error.message : error}`,
        { status: 502, headers: { "content-type": "text/plain; charset=utf-8" } });
    }
  },
};
