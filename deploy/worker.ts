/**
 * The doorman in front of the app — and the keeper of its memory.
 *
 * The app itself is a FastAPI process on **Google Cloud Run**, not in this
 * Worker and not in a Cloudflare Container. `cloze`, `conjugation`, `patterns`
 * and `verbs` all call Vabamorf at request time, and Vabamorf is a compiled C++
 * Python extension; Workers run JavaScript and WASM. Cloudflare Containers
 * would have hosted it directly, but they require the Workers Paid plan, and
 * this has to cost nothing. Cloud Run's always-free tier runs the same image.
 *
 * That split gives this Worker three jobs.
 *
 * **Routing.** Forward every request to the Cloud Run service, unchanged.
 *
 * **Closing the back door.** Cloud Run must allow unauthenticated invocations
 * for the free path to work, so its `run.app` URL answers the whole internet.
 * Cloudflare Access guards *this* Worker, not that URL. So every proxied
 * request carries `PROXY_TOKEN`, a secret only this Worker holds, and the app
 * refuses anything without it. Access guards the front door; the token means
 * there is only one door.
 *
 * **Persistence.** Cloud Run disk is ephemeral and the service scales to zero,
 * so a fresh instance starts with the image's databases and none of the
 * learner's. Mastery, review queue and vocabulary are SQLite files on that
 * disk. Without the snapshotting below, a lunch break would silently reset
 * everything the curriculum exists to accumulate.
 *
 * There is no shutdown hook a Worker can observe, so restarts are noticed
 * rather than announced: the app stamps every response with a boot id, and a
 * boot id this Worker has not seen means a new, empty instance.
 *
 * **What this is NOT:** the security boundary on its own. That is Cloudflare
 * Access, in front of this Worker. Around 421 harvested items are owner-only by
 * licence — ERR transcripts are © ERR, Selges keeles carries no reuse grant —
 * so deploying without an Access policy publishes someone else's copyrighted
 * work.
 */
import { DurableObject } from "cloudflare:workers";

interface Env {
  LEARNER_STATE: DurableObjectNamespace<LearnerState>;
  /** Workers AI, for speech recognition. See `transcribe`. */
  AI?: Ai;
  /** Base URL of the Cloud Run service, e.g. https://eesti-keelt-xxxx.run.app */
  CLOUD_RUN_URL: string;
  /** Shared secret proving a request came through this Worker. */
  PROXY_TOKEN: string;
  /** Guards the snapshot endpoints on the app. */
  STATE_TOKEN: string;
  /**
   * Set to "1" to serve without Cloudflare Access. The escape hatch, not the
   * default -- see `requireAccess`.
   */
  ALLOW_UNAUTHENTICATED?: string;
}

/* Refuse anything that did not come through Cloudflare Access.

   Access is a dashboard setting, which can be switched off by accident or fail to
   apply without anything complaining. Enforcing it in code makes losing it a
   locked door rather than a silent opening.

   When Access is enabled, the runtime puts an identity on every request that
   passed it; without one this returns a page saying so. `ALLOW_UNAUTHENTICATED`
   exists for deliberately serving without Access, and is deliberately awkward:
   the default has to be the safe one. */
function requireAccess(env: Env, ctx: ExecutionContext): Response | null {
  if (ctx.access || env.ALLOW_UNAUTHENTICATED === "1") return null;
  return new Response(
    "This app is not protected by Cloudflare Access, so it will not serve.\n\n" +
      "Enable it: Workers & Pages -> eesti-keelt -> Access -> All traffic,\n" +
      "with the 'Cloudflare account' policy.\n\n" +
      "To serve without Access on purpose, set ALLOW_UNAUTHENTICATED=1.\n" +
      "See docs/deploy.md.",
    { status: 403, headers: { "content-type": "text/plain; charset=utf-8" } },
  );
}

/** Snapshot on a timer as well as after work, so a crash costs minutes at most. */
const SNAPSHOT_EVERY_MS = 5 * 60 * 1000;
/**
 * How long a known-live instance is trusted without re-checking. Inside this
 * window requests go straight through; outside it, one `/api/health` call is
 * spent to find out whether the instance is still the one holding the state.
 */
const LIVENESS_TTL_MS = 60 * 1000;
/** Floor on how often a write triggers a snapshot. See `snapshot`. */
const SNAPSHOT_MIN_GAP_MS = 60 * 1000;
/**
 * Storage values have a per-entry size limit, and a year of answers will not
 * fit in one. Chunking at 96 KiB stays under it with room to spare and costs
 * one row written per chunk — a full snapshot is a handful of rows, against a
 * free-plan budget of 100,000 a day.
 */
const CHUNK = 96 * 1024;

/* Two blobs live in this store and they are not the same kind of thing.

   `snap` is the learner's progress: written constantly, never overwritten on
   restore, and the thing the snapshot mechanism exists to protect.

   `corpus` is the harvested reading library: written once from a laptop,
   overwritten freely, and owner-only by licence — so it cannot ship inside an
   image built from a public repository, and travels this way instead. */
type Blob = "snap" | "corpus";

/** The instance this object last restored, and how far its log was copied. */
interface Origin {
  boot: string;
  cursor: number;
}

interface BlobMeta {
  chunks: number;
  bytes: number;
  at: number;
  /** Learner rows in a `snap` export (see `/api/state/export`); absent before
   *  the origin reported them. */
  rows?: number;
}

/**
 * One instance, named "singleton": one learner, one body of state.
 *
 * It holds the snapshot and does all the talking to Cloud Run that is *about*
 * state. Ordinary traffic does not come through here — a Durable Object in the
 * request path would add a hop to every drill for no benefit.
 */
export class LearnerState extends DurableObject<Env> {
  /** The boot id of the instance we last confirmed holds the learner's state. */
  private lastBoot: string | null = null;
  private lastSeen = 0;
  private lastSnapshot = 0;
  /** The origin's event sequence number already copied here, for `lastBoot`. */
  private cursor = 0;
  /** One restore at a time: concurrent requests wait for the same one. */
  private restoring: Promise<boolean> | null = null;

  /* The evidence log (`eesti/evidence.py`): the learner's source of truth.
     Append-only and keyed by event id, so pulling the same event twice, or
     pushing it back into an instance that has it, changes nothing. `dseq` keeps
     the order the events arrived in, which is the order they are replayed in. */
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    ctx.storage.sql.exec(
      `CREATE TABLE IF NOT EXISTS events (
         dseq INTEGER PRIMARY KEY AUTOINCREMENT,
         id   TEXT NOT NULL UNIQUE,
         body TEXT NOT NULL
       )`,
    );
  }

  private origin(path: string): string {
    return new URL(path, this.env.CLOUD_RUN_URL).toString();
  }

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    return {
      "x-proxy-token": this.env.PROXY_TOKEN,
      "x-state-token": this.env.STATE_TOKEN,
      ...extra,
    };
  }

  /** Read a blob back out of storage, or null if there isn't a whole one. */
  private async load(blob: Blob): Promise<string | null> {
    const meta = await this.ctx.storage.get<BlobMeta>(`${blob}-meta`);
    if (!meta) return null;
    const parts = await this.ctx.storage.list<string>({ prefix: `${blob}/` });
    if (parts.size !== meta.chunks) {
      // A blob half-written by an interrupted save is worse than none: it would
      // restore a truncated SQLite file over a working one.
      return null;
    }
    let out = "";
    for (let i = 0; i < meta.chunks; i++) {
      const part = parts.get(`${blob}/${i}`);
      if (part === undefined) return null;
      out += part;
    }
    return out;
  }

  private async save(blob: Blob, body: string, rows?: number): Promise<void> {
    const chunks: Record<string, string> = {};
    for (let i = 0; i * CHUNK < body.length; i++) {
      chunks[`${blob}/${i}`] = body.slice(i * CHUNK, (i + 1) * CHUNK);
    }
    const count = Object.keys(chunks).length;
    // Meta last, and deletes first: the meta key is what makes a blob readable,
    // so writing it only after every chunk has landed means an interrupted save
    // leaves the previous one unreadable rather than leaving a mixture of two
    // readable.
    await this.ctx.storage.delete(`${blob}-meta`);
    const stale = [
      ...(await this.ctx.storage.list<string>({ prefix: `${blob}/` })),
    ].map(([k]) => k);
    if (stale.length) await this.ctx.storage.delete(stale);
    // Storage writes are capped per call; a ten-megabyte corpus is a hundred
    // chunks, so they go in batches rather than one enormous put.
    const entries = Object.entries(chunks);
    for (let i = 0; i < entries.length; i += 64) {
      await this.ctx.storage.put(Object.fromEntries(entries.slice(i, i + 64)));
    }
    await this.ctx.storage.put<BlobMeta>(`${blob}-meta`, {
      chunks: count,
      bytes: body.length,
      at: Date.now(),
      ...(rows === undefined ? {} : { rows }),
    });
  }

  /* Keep the harvested library alive across cold starts, in whichever direction
     is needed.

     The corpus cannot ship in the image (owner-only by licence, public
     repository) and cannot be uploaded through this Worker (Access is an
     interactive login a script cannot satisfy). So it is pushed to the origin,
     which a script can authenticate to, and archived from there.

     Which way it moves depends on who has it:

     - the container has one and this store does not  ->  **archive it**, which
       is how a freshly pushed harvest becomes permanent
     - this store has one and the container does not  ->  **restore it**, which
       is every cold start after that

     Both are no-ops once they agree, so this runs on every boot change without
     costing anything in the ordinary case. */
  private async syncCorpus(): Promise<void> {
    let onContainer = false;
    try {
      const res = await fetch(this.origin("/api/content/export"), {
        headers: this.headers(),
      });
      if (res.ok) {
        onContainer = ((await res.json()) as { present?: boolean }).present ?? false;
      }
    } catch {
      return;
    }

    const stored = await this.ctx.storage.get<BlobMeta>("corpus-meta");

    if (onContainer && !stored) {
      const res = await fetch(this.origin("/api/content/export?full=1"), {
        headers: this.headers(),
      });
      if (res.ok) await this.save("corpus", await res.text());
      return;
    }

    if (!onContainer && stored) {
      const corpus = await this.load("corpus");
      if (!corpus) return;
      // The app takes `{database: "<base64>"}`; the archive holds the whole
      // export envelope, which carries the same key.
      await fetch(this.origin("/api/content/import"), {
        method: "POST",
        headers: this.headers({ "content-type": "application/json" }),
        body: corpus,
      });
    }
  }

  /** Throw the archived library away, so the next push replaces it. */
  async forgetCorpus(): Promise<void> {
    await this.ctx.storage.delete("corpus-meta");
    const stale = [
      ...(await this.ctx.storage.list<string>({ prefix: "corpus/" })),
    ].map(([k]) => k);
    if (stale.length) await this.ctx.storage.delete(stale);
  }

  /**
   * Make sure the instance now serving requests has the learner's state.
   *
   * Called before proxying, but only once a minute — the common case is a
   * warm instance we checked recently, and that path costs nothing.
   *
   * Returns false when it could not confirm that: the caller must not let a
   * write reach an instance that may be missing the learner's history, or that
   * write becomes the only thing the next snapshot holds.
   */
  async ensureRestored(): Promise<boolean> {
    if (this.lastBoot && Date.now() - this.lastSeen < LIVENESS_TTL_MS) return true;
    // Durable Objects interleave requests at every `await`: without this, two
    // requests arriving on a cold start would each run a restore.
    this.restoring ??= this.restore().finally(() => {
      this.restoring = null;
    });
    return this.restoring;
  }

  private async restore(): Promise<boolean> {

    let boot: string;
    try {
      const res = await fetch(this.origin("/api/health"), {
        headers: this.headers(),
      });
      if (!res.ok) return false;
      boot = ((await res.json()) as { boot?: string }).boot ?? "";
    } catch {
      // Cloud Run cold-starting or briefly unreachable. Reads may still go
      // through and surface the real error; writes wait.
      return false;
    }
    if (!boot) return false;

    if (boot === this.lastBoot) {
      this.lastSeen = Date.now();
      return true;
    }
    // This object may have been evicted from memory while the instance lived
    // on: then the instance already holds the log, and a restore would only
    // replay it again.
    const known = await this.ctx.storage.get<Origin>("origin");
    if (known?.boot === boot) {
      this.lastBoot = boot;
      this.cursor = known.cursor;
      this.lastSeen = Date.now();
      return true;
    }

    await this.syncCorpus();

    const saved = await this.load("snap");
    // The snapshot first: it carries the caches (dictionary answers, the
    // provider breaker) the log does not. The log second, which rebuilds the
    // learner's tables over whatever the snapshot put there.
    if (saved) {
      // `/api/state/import` refuses any database that already holds learner
      // rows, so a restore aimed at the wrong moment declines rather than
      // overwrites. A failed import leaves `lastBoot` unset, so the next
      // request tries again instead of trusting an empty instance.
      try {
        const res = await fetch(this.origin("/api/state/import"), {
          method: "POST",
          headers: this.headers({ "content-type": "application/json" }),
          body: saved,
        });
        if (!res.ok) return false;
      } catch {
        return false;
      }
    }

    const pushed = await this.pushEvents();
    if (pushed === null) return false;

    this.lastBoot = boot;
    this.lastSeen = Date.now();
    this.cursor = pushed;
    await this.ctx.storage.put<Origin>("origin", { boot, cursor: pushed });
    // A new instance is the moment to start the clock, so the first session's
    // work gets a snapshot too.
    await this.ctx.storage.setAlarm(Date.now() + SNAPSHOT_EVERY_MS);
    return true;
  }

  /**
   * Give a fresh instance the whole log, in batches, then have it settle: rebuild
   * its projections from the log, or, the first time ever, backfill the log from
   * the rows it has. Returns the origin's sequence number afterwards, or null.
   */
  private async pushEvents(): Promise<number | null> {
    const BATCH = 500;
    let after = 0;
    let last = 0;
    for (;;) {
      const rows = this.ctx.storage.sql
        .exec<{ dseq: number; body: string }>(
          "SELECT dseq, body FROM events WHERE dseq > ? ORDER BY dseq LIMIT ?",
          after,
          BATCH,
        )
        .toArray();
      const settle = rows.length < BATCH;
      try {
        const res = await fetch(this.origin("/api/events/import"), {
          method: "POST",
          headers: this.headers({ "content-type": "application/json" }),
          body: JSON.stringify({
            events: rows.map((r) => JSON.parse(r.body)),
            settle,
          }),
        });
        if (!res.ok) return null;
        // Where the pushed log ends, not where the origin's does: settling may
        // append (the first backfill), and those events must still be pulled.
        last = ((await res.json()) as { ingested_seq?: number }).ingested_seq ?? 0;
      } catch {
        return null;
      }
      if (settle) return last;
      after = rows[rows.length - 1].dseq;
    }
  }

  /**
   * Copy events the origin has and this store lacks. `seen` is the origin's
   * `x-events-seq`; nothing is fetched when it is not ahead of the cursor. Only
   * the instance this object restored is asked, as for snapshots.
   */
  async pullEvents(seen: number): Promise<void> {
    if (!this.lastBoot || seen <= this.cursor) return;
    for (;;) {
      let body: { events?: { id: string; seq: number }[]; last_seq?: number };
      try {
        const res = await fetch(
          this.origin(`/api/events?after=${this.cursor}&limit=500`),
          { headers: this.headers() },
        );
        if (!res.ok || res.headers.get("x-boot-id") !== this.lastBoot) return;
        body = await res.json();
      } catch {
        return;
      }
      const batch = body.events ?? [];
      for (const ev of batch) {
        const { seq, ...event } = ev;
        this.ctx.storage.sql.exec(
          "INSERT OR IGNORE INTO events (id, body) VALUES (?, ?)",
          event.id,
          JSON.stringify(event),
        );
        this.cursor = Math.max(this.cursor, seq);
      }
      await this.ctx.storage.put<Origin>("origin", {
        boot: this.lastBoot,
        cursor: this.cursor,
      });
      if (batch.length === 0 || this.cursor >= (body.last_seq ?? 0)) return;
    }
  }

  /**
   * Take a copy out of the running instance.
   *
   * Debounced: a practice session is a POST per answer, and copying three
   * databases after each one would spend bandwidth and storage writes to
   * capture work that the next answer changes a few seconds later. A minute is
   * short enough that nothing meaningful is at risk and long enough that a
   * ten-minute session costs ten snapshots rather than a hundred.
   */
  async snapshot(force = false): Promise<boolean> {
    if (!force && Date.now() - this.lastSnapshot < SNAPSHOT_MIN_GAP_MS) {
      return false;
    }
    // Only the instance this object restored holds the learner's history. Any
    // other one — a second instance, or a fresh one not yet restored — would
    // hand back a partial copy.
    if (!this.lastBoot) return false;
    try {
      const res = await fetch(this.origin("/api/state/export"), {
        headers: this.headers(),
      });
      if (!res.ok) return false;
      if (res.headers.get("x-boot-id") !== this.lastBoot) return false;
      const body = await res.text();
      const rows = (JSON.parse(body) as { learner_rows?: number }).learner_rows;
      if (typeof rows !== "number") return false;
      // An export that holds no learner rows is empty work; letting it replace
      // a snapshot that holds some would be the bug the whole mechanism exists
      // to prevent. Byte size cannot tell: an empty schema is not empty.
      const stored = await this.ctx.storage.get<BlobMeta>("snap-meta");
      if (rows === 0 && stored && (stored.rows ?? 1) > 0) return false;
      await this.save("snap", body, rows);
      this.lastSnapshot = Date.now();
      return true;
    } catch {
      // A failed snapshot must never take the session down with it: the next
      // alarm will try again.
      return false;
    }
  }

  override async alarm(): Promise<void> {
    await this.snapshot(true);
    await this.ctx.storage.setAlarm(Date.now() + SNAPSHOT_EVERY_MS);
  }
}

/**
 * Whisper, on the platform the app is already fronted by.
 *
 * Recognition happens here rather than on the origin for one reason worth
 * stating: the binding needs no API token. Calling Workers AI over REST from
 * Cloud Run would mean putting a Cloudflare credential on the origin, and the
 * only token template that covers Workers can also edit them — far more
 * authority than "turn this audio into words" deserves.
 *
 * What it does NOT do is decide anything. The transcript goes straight to the
 * app, which compares it against a target it already knows. A model says what
 * it heard; nothing else in this app is a model's opinion.
 */
const WHISPER = "@cf/openai/whisper-large-v3-turbo";

async function transcribe(
  request: Request,
  env: Env,
  url: URL,
): Promise<Response> {
  if (!env.AI) {
    return Response.json(
      { text: "", engine: "", degraded: true, note: "no speech engine" },
      { status: 200 },
    );
  }

  const audio = await request.arrayBuffer();
  if (audio.byteLength === 0) {
    return Response.json({ detail: "no audio" }, { status: 400 });
  }
  if (audio.byteLength > 12_000_000) {
    return Response.json({ detail: "recording too long" }, { status: 413 });
  }

  // The question being answered. A few seconds of accented Estonian is exactly
  // what a recogniser guesses wrong on, and the topic's own vocabulary is a free
  // hint. Never the read-aloud target: priming the recogniser with the words it
  // is about to be compared against makes it hear them whether or not they were
  // said, and inflates the comparison.
  const context = (url.searchParams.get("q") ?? "").slice(0, 220);

  let text = "";
  let note = "";
  try {
    const out = (await env.AI.run(WHISPER, {
      audio: base64(audio),
      task: "transcribe",
      // Pinned, not guessed: Whisper reaches for a bigger language otherwise.
      language: "et",
      vad_filter: true,
      // Whisper repeats itself on silence; these are its documented guards.
      condition_on_previous_text: false,
      ...(context ? { initial_prompt: context } : {}),
    })) as { text?: string };
    text = (out.text ?? "").trim();
  } catch (error) {
    note = error instanceof Error ? error.message.slice(0, 200) : String(error);
  }

  // Hand the transcript to the app, which owns every judgement made about it.
  const target = url.searchParams.get("target") ?? "";
  const graded = new URL("/api/transcribe/text", env.CLOUD_RUN_URL);
  if (target) graded.searchParams.set("target", target);
  return fetch(graded, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-proxy-token": env.PROXY_TOKEN,
    },
    body: JSON.stringify({
      text,
      engine: text ? `Workers AI (${WHISPER})` : "",
      degraded: !text,
      note,
    }),
  });
}

/** ArrayBuffer -> base64, in chunks so a long recording does not blow the stack. */
function base64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

function notRestored(): Response {
  return new Response(
    "Приложение запускается и восстанавливает прогресс. Повторите через несколько секунд.",
    {
      status: 503,
      headers: { "content-type": "text/plain; charset=utf-8", "retry-after": "5" },
    },
  );
}

function stub(env: Env) {
  return env.LEARNER_STATE.get(env.LEARNER_STATE.idFromName("singleton"));
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext) {
    if (!env.CLOUD_RUN_URL) {
      return new Response(
        "CLOUD_RUN_URL is not configured. See docs/deploy.md.",
        { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } },
      );
    }

    const denied = requireAccess(env, ctx);
    if (denied) return denied;

    // The Worker's own back channel. Exposing these through the proxy would let
    // anyone past Access overwrite everything.
    //
    // The exact set of origin routes that require `STATE_TOKEN`, not a path prefix:
    // the reset and content-import routes do not share the `/api/state/` prefix. The
    // origin still demands the token; this is the second layer.
    //
    // Hand-maintained, because a Worker cannot import Python — so a test checks it
    // against `eesti/api/state.py` in both directions.
    const BACK_CHANNEL = [
      "/api/events",
      "/api/events/import",
      "/api/state/export",
      "/api/state/import",
      "/api/content/export",
      "/api/content/import",
      "/api/progress/reset",
    ];
    const url = new URL(request.url);
    if (BACK_CHANNEL.includes(url.pathname)) {
      return new Response("not found", { status: 404 });
    }

    const learner = stub(env);
    const restored = await learner.ensureRestored();
    const writes = request.method !== "GET" && request.method !== "HEAD";

    // Speech is answered here, not forwarded: see `transcribe`. It records
    // evidence on the origin, so it waits for the restore like any write, and
    // what it recorded is copied out like any other.
    if (url.pathname === "/api/transcribe" && request.method === "POST") {
      if (!restored) return notRestored();
      const heard = await transcribe(request, env, url);
      const seen = Number(heard.headers.get("x-events-seq") ?? "");
      if (Number.isFinite(seen) && seen > 0) ctx.waitUntil(learner.pullEvents(seen));
      return heard;
    }

    // Any API call may record evidence (opening a text is a GET that does), so
    // until the instance holds the learner's history only the health probe and
    // the static shell go through.
    const api = url.pathname.startsWith("/api/") && url.pathname !== "/api/health";
    if (!restored && (writes || api)) {
      // A write to an instance that may not hold the learner's history would
      // be recorded against an empty copy. Better to ask for a retry.
      return notRestored();
    }

    const target = new URL(url.pathname + url.search, env.CLOUD_RUN_URL);
    const headers = new Headers(request.headers);
    headers.set("x-proxy-token", env.PROXY_TOKEN);
    // Cloud Run routes on Host; forwarding the Worker's hostname 404s.
    headers.delete("host");

    let response: Response;
    try {
      response = await fetch(
        new Request(target, {
          method: request.method,
          headers,
          body: request.body,
          redirect: "manual",
        }),
      );
    } catch (error) {
      return new Response(
        `The app is unreachable: ${error instanceof Error ? error.message : error}`,
        { status: 502, headers: { "content-type": "text/plain; charset=utf-8" } },
      );
    }

    // Anything that changed state is worth a snapshot, but not synchronously —
    // the learner should never wait on a backup. Debounced by the alarm the
    // Durable Object already holds.
    if (writes) {
      ctx.waitUntil(learner.snapshot());
    }
    // New evidence is copied out right away, not on the snapshot's timer.
    const seq = Number(response.headers.get("x-events-seq") ?? "");
    if (Number.isFinite(seq) && seq > 0) {
      ctx.waitUntil(learner.pullEvents(seq));
    }

    // The origin cannot see the AI binding, so it reports every hosted engine
    // as absent and the UI hides the microphone. Correct the one fact this
    // Worker knows better than the app does.
    if (url.pathname === "/api/asr" && env.AI && response.ok) {
      const engines = (await response.json()) as Record<string, unknown>;
      return Response.json({
        ...engines,
        cloudflare: true,
        ready: true,
        hosted: true,
      });
    }
    return response;
  },
};
