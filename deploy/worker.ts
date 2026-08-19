/**
 * The doorman in front of the container — and the keeper of its memory.
 *
 * Two jobs, and the second one is not optional.
 *
 * **Routing.** Every request is forwarded to a single container instance,
 * because the Python app needs Vabamorf, which is a compiled C++ extension and
 * cannot run in a Worker.
 *
 * **Persistence.** Cloudflare Containers have ephemeral disk: "when a Container
 * instance goes to sleep, the next time it is started, it will have a fresh
 * disk as defined by its container image." The learner's progress, review queue
 * and vocabulary live in SQLite files on that disk. Without the snapshotting
 * below, a ten-minute break would reset everything steps 3 to 9 exist to
 * accumulate — silently, which is the worst way for it to happen.
 *
 * So the durable copy lives in this Durable Object's storage, which survives
 * container restarts, and the container is asked to hand its state over before
 * it sleeps and to take it back when it starts.
 *
 * **What this is NOT:** the security boundary. That is Cloudflare Access, in
 * front of this Worker. Around 421 harvested items are owner-only by licence —
 * ERR transcripts are © ERR, Selges keeles carries no reuse grant — so
 * deploying without an Access policy publishes someone else's copyrighted work.
 */
import { Container, getContainer } from "@cloudflare/containers";

interface Env {
  EESTI_APP: DurableObjectNamespace<EestiApp>;
  STATE_TOKEN: string;
}

const SNAPSHOT_KEY = "learner-state";
// Snapshot on a timer as well as before sleep. The sleep hook covers the
// ordinary case; the alarm covers the ones it cannot — an OOM kill, a host
// going away, a deploy rollout replacing the instance mid-session.
const SNAPSHOT_EVERY_MS = 5 * 60 * 1000;

export class EestiApp extends Container<Env> {
  defaultPort = 8080;
  // A learner answers ten questions over a few minutes; sleeping between them
  // would mean a cold start per answer. Idle past this and it stops, which is
  // what keeps a single-user app close to free.
  sleepAfter = "10m";

  override envVars = { STATE_TOKEN: this.env.STATE_TOKEN };

  /** Push the last snapshot back in before the learner touches anything. */
  override async onStart(): Promise<void> {
    const saved = await this.ctx.storage.get<string>(SNAPSHOT_KEY);
    if (!saved) return;
    await this.containerFetch(
      new Request("http://container/api/state/import", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-state-token": this.env.STATE_TOKEN,
        },
        body: saved,
      }),
    );
    await this.ctx.storage.setAlarm(Date.now() + SNAPSHOT_EVERY_MS);
  }

  /** Take a copy out. Called on the timer and before sleeping. */
  async snapshot(): Promise<boolean> {
    try {
      const res = await this.containerFetch(
        new Request("http://container/api/state/export", {
          headers: { "x-state-token": this.env.STATE_TOKEN },
        }),
      );
      if (!res.ok) return false;
      await this.ctx.storage.put(SNAPSHOT_KEY, await res.text());
      return true;
    } catch {
      // A failed snapshot must never take the app down with it: the learner's
      // session is more valuable than this cycle's backup, and the next alarm
      // will try again.
      return false;
    }
  }

  override async alarm(): Promise<void> {
    await this.snapshot();
    await this.ctx.storage.setAlarm(Date.now() + SNAPSHOT_EVERY_MS);
  }

  /** The container is about to be stopped for idleness — save first. */
  override async onActivityExpired(): Promise<void> {
    await this.snapshot();
    await this.stop();
  }

  override onError(error: unknown): Response {
    return new Response(
      `Container unavailable: ${error instanceof Error ? error.message : error}`,
      { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }
}

export default {
  async fetch(request: Request, env: Env) {
    // One learner, one instance: a fixed name means every request lands on the
    // same container, and the same snapshot follows it.
    return getContainer(env.EESTI_APP, "singleton").fetch(request);
  },
};
