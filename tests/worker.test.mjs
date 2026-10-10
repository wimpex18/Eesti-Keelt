import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { afterEach, test } from "node:test";
import worker, { LearnerState } from "../deploy/worker.ts";
import { BACKUP_CRON } from "../deploy/schedule.ts";
import { readFileSync } from "node:fs";
import { signSession } from "../deploy/accounts.ts";

const originalFetch = globalThis.fetch;
const stores = [];
afterEach(() => {
  globalThis.fetch = originalFetch;
  for (const db of stores.splice(0)) db.close();
});

function object(env) {
  const db = new DatabaseSync(":memory:");
  stores.push(db);
  const values = new Map();
  const storage = {
    sql: {
      exec(query, ...params) {
        const rows = db.prepare(query).all(...params);
        return { toArray: () => rows, [Symbol.iterator]: () => rows.values() };
      },
    },
    async get(key) { return values.get(key); },
    async put(key, value) {
      if (typeof key === "object") {
        for (const [k, v] of Object.entries(key)) values.set(k, structuredClone(v));
      } else values.set(key, structuredClone(value));
    },
    async delete(key) {
      if (Array.isArray(key)) return key.reduce((n, k) => n + Number(values.delete(k)), 0);
      return values.delete(key);
    },
    async list({ prefix }) { return new Map([...values].filter(([key]) => key.startsWith(prefix))); },
    async setAlarm() {},
  };
  return { state: new LearnerState({ storage }, env), db, storage };
}

function setup() {
  const objects = new Map();
  const env = {
    CLOUD_RUN_URL: "https://origin.test",
    PROXY_TOKEN: "test-proxy",
    STATE_TOKEN: "test-state",

    LEARNER_STATE: {
      idFromName(name) { return name; },
      get(name) {
        if (!objects.has(name)) objects.set(name, object(env));
        return objects.get(name).state;
      },
    },
  };
  const pending = [];
  const ctx = { waitUntil(promise) { pending.push(promise); } };
  return { env, objects, ctx, pending, owner: env.LEARNER_STATE.get("singleton") };
}

function event(id, seq) {
  return { id, type: "profile-set", v: 1, learner: "owner",
    ts: "2026-01-01T00:00:00.000Z", payload: { name: id }, ...(seq ? { seq } : {}) };
}

function originResponse(body, seq, boot = "boot-A", status = 200) {
  return Response.json(body, { status, headers: { "x-events-seq": String(seq), "x-boot-id": boot } });
}

async function seed(app, count = 10, cursor = count) {
  app.env.SESSION_SECRET = "test-session-secret";
  const account = await app.owner.createOwnerAccount("owner@example.test", "test-password");
  app.cookie = `eesti_session=${await signSession(account.id, app.env.SESSION_SECRET)}`;
  await app.owner.bindWho({ scope: "owner", id: "owner", email: "" });
  const { storage } = app.objects.get("singleton");
  for (let i = 1; i <= count; i++) {
    const ev = event(`saved-${i}`);
    storage.sql.exec("INSERT INTO events (id, body) VALUES (?, ?)", ev.id, JSON.stringify(ev));
  }
  await storage.put("origin", { boot: "boot-A", cursor });
  await app.owner.prepareOrigin();
  // These tests isolate evidence durability from the independent snapshot cache.
  app.owner.snapshot = async () => true;
}

test("a guest restores the shared reading corpus before opening the library", async () => {
  const app = setup();
  let restored = false;
  app.owner.ensureRestored = async () => { restored = true; return true; };
  globalThis.fetch = async request => {
    assert.equal(request.headers.get("x-eesti-scope"), "guest");
    assert.equal(request.headers.get("x-eesti-guest"), "materials-audit");
    return Response.json({ total: restored ? 349 : 0 });
  };
  const response = await worker.fetch(new Request("https://learn.test/api/library", {
    headers: { "x-eesti-guest": "materials-audit" },
  }), app.env, app.ctx);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).total, 349);
});

test("the front door overwrites a forged social artwork origin", async () => {
  const app = setup();
  await seed(app);
  let forwarded;
  globalThis.fetch = async request => {
    forwarded = request;
    return new Response("<html>Klint</html>", {headers: {"content-type": "text/html"}});
  };
  const response = await worker.fetch(new Request("https://learn.test/", {
    headers: {"x-brand-origin": "https://forged.test", cookie: app.cookie},
  }), app.env, app.ctx);
  assert.equal(response.status, 200);
  assert.equal(forwarded.headers.get("x-brand-origin"), "https://learn.test");
  assert.equal(forwarded.headers.get("host"), null);
});

for (const mode of ["legacy", "bootstrap", "owner", "learner"]) {
  test(`an explicit sandbox cannot write into the ${mode} account`, async () => {
    const app = setup();
    if (mode !== "legacy") app.env.SESSION_SECRET = "test-session-secret";
    let cookie = "";
    if (mode === "owner" || mode === "learner") {
      const owner = await app.owner.createOwnerAccount("owner@example.test", "test-password");
      const account = mode === "owner" ? owner : await app.owner.createAccount(
        "learner@example.test", "test-password");
      cookie = `eesti_session=${await signSession(account.id, app.env.SESSION_SECRET)}`;
    }
    let forwarded;
    globalThis.fetch = async request => {
      forwarded = request;
      return Response.json({ scope: request.headers.get("x-eesti-scope") });
    };
    const response = await worker.fetch(new Request("https://learn.test/api/check", {
      method: "POST", headers: { "x-eesti-guest": "qa-run-42", cookie,
        "x-eesti-scope": "owner", "x-eesti-learner": "l-1234567890abcdef" },
    }), app.env, app.ctx);
    assert.equal(response.status, 200);
    assert.equal((await response.json()).scope, "guest");
    assert.equal(forwarded.headers.get("x-eesti-guest"), "qa-run-42");
    assert.equal(forwarded.headers.get("x-eesti-learner"), null);
    assert.equal(forwarded.headers.get("x-eesti-email"), null);
    assert.equal(app.pending.length, 0);
  });
}

test("an invalid explicit sandbox fails before origin or account access", async () => {
  const app = setup();
  app.env.LEARNER_STATE.get = () => { throw new Error("account accessed"); };
  globalThis.fetch = async () => { throw new Error("origin accessed"); };
  for (const name of ["", "../owner", "a".repeat(41)]) {
    const response = await worker.fetch(new Request("https://learn.test/api/check", {
      method: "POST", headers: { "x-eesti-guest": name }, body: "{}",
    }), app.env, app.ctx);
    assert.equal(response.status, 400);
  }
});

for (const identity of [
  "faster-whisper/1.2.1 ctranslate2/4.6.0 cpu/int8 beam=5 temperature=0 artifacts-sha256:" + "a".repeat(64),
  "future-recogniser/" + "v".repeat(200),
]) {
  test(`home speech fits the origin engine contract (${identity.split("/")[0]})`, async () => {
    const app = setup();
    app.env.HOME_ASR_TOKEN = "test-home-token";
    app.env.HOME_ASR = { async fetch() {
      return Response.json({ text: "Tere", engine: identity });
    } };
    globalThis.fetch = async (url, init) => {
      const body = JSON.parse(init.body);
      // TranscriptIn rejects a longer label before grading or recording evidence.
      return Response.json(body, { status: body.engine.length <= 120 ? 200 : 422 });
    };
    const response = await worker.fetch(new Request("https://learn.test/api/transcribe", {
      method: "POST", headers: { "x-eesti-guest": "speech-qa" },
      body: new Uint8Array([1, 2, 3]),
    }), app.env, app.ctx);
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.text, "Tere");
    assert.equal(body.degraded, false);
    assert.ok(body.engine.startsWith(identity.split("/")[0]));
    assert.ok(body.engine.endsWith(" · Mac mini"));
    assert.ok(!body.engine.includes("artifacts-sha256:"));
  });
}

for (const homeOnline of [true, false]) {
  test(`speech retains its guest sandbox when home ASR is ${homeOnline ? "online" : "offline"}`, async () => {
    const app = setup();
    app.env.SESSION_SECRET = "test-session-secret";
    app.env.HOME_ASR_TOKEN = "test-home-token";
    app.env.HOME_ASR = { async fetch() {
      return homeOnline ? Response.json({ text: "Tere", engine: "home-test" })
        : new Response("unavailable", { status: 503 });
    } };
    let fallbackCalls = 0;
    app.env.AI = { async run() { fallbackCalls++; return { text: "Tere" }; } };
    let forwarded;
    globalThis.fetch = async (url, init) => {
      forwarded = { url, init };
      return Response.json({ ...JSON.parse(init.body), scope: init.headers.get("x-eesti-scope") });
    };
    const response = await worker.fetch(new Request("https://learn.test/api/transcribe", {
      method: "POST", headers: { "x-eesti-guest": "speech-qa", "content-type": "audio/wav" },
      body: new Uint8Array([1, 2, 3]),
    }), app.env, app.ctx);
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.scope, "guest");
    assert.equal(forwarded.init.headers.get("x-eesti-guest"), "speech-qa");
    assert.equal(fallbackCalls, homeOnline ? 0 : 1);
    assert.match(body.engine, homeOnline ? /Mac mini/ : /Workers AI/);
    assert.equal(app.pending.length, 0);
  });
}

test("a replacement boot cannot acknowledge a lost event at the same sequence", async () => {
  const app = setup();
  globalThis.fetch = async url => {
    const path = new URL(url instanceof Request ? url.url : url).pathname;
    if (path === "/api/health") return Response.json({ boot: "boot-A" });
    throw new Error(path);
  };
  await seed(app);
  globalThis.fetch = async url => {
    const path = new URL(url instanceof Request ? url.url : url).pathname;
    if (path === "/api/profile") return originResponse({ saved: "lost-A" }, 11);
    if (path === "/api/health") return Response.json({ boot: "boot-B" });
    if (path === "/api/content/export") return Response.json({ present: false });
    if (path === "/api/events/import") return Response.json({ ingested_seq: 10 });
    if (path === "/api/events") return originResponse({ events: [event("different-B", 11)], last_seq: 11 }, 11, "boot-B");
    throw new Error(path);
  };
  const response = await worker.fetch(new Request("https://app.test/api/profile", {headers: {cookie: app.cookie}}), app.env, app.ctx);
  assert.equal(response.status, 503);
  assert.equal(response.headers.get("x-eesti-durability"), "unconfirmed");
  assert.equal(app.objects.get("singleton").db.prepare("SELECT COUNT(*) AS n FROM events WHERE id='lost-A'").get().n, 0);
});

test("an old boot's higher cursor cannot skip copying new evidence", async () => {
  const app = setup();
  globalThis.fetch = async () => Response.json({ boot: "boot-A" });
  await seed(app, 10, 100);
  let copied = 0;
  globalThis.fetch = async url => {
    const path = new URL(url instanceof Request ? url.url : url).pathname;
    if (path === "/api/profile") return originResponse({ saved: "new-B" }, 11, "boot-B");
    if (path === "/api/health") return Response.json({ boot: "boot-B" });
    if (path === "/api/content/export") return Response.json({ present: false });
    if (path === "/api/events/import") return Response.json({ ingested_seq: 10 });
    if (path === "/api/events") {
      copied++;
      return originResponse({ events: [event("new-B", 11)], last_seq: 11 }, 11, "boot-B");
    }
    throw new Error(path);
  };
  const response = await worker.fetch(new Request("https://app.test/api/profile", {headers: {cookie: app.cookie}}), app.env, app.ctx);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("x-eesti-durable-seq"), "11");
  assert.equal(copied, 1);
  assert.equal(app.objects.get("singleton").db.prepare("SELECT COUNT(*) AS n FROM events WHERE id='new-B'").get().n, 1);
});

test("unchanged reads reuse a cursor only from their own boot", async () => {
  const app = setup();
  let copies = 0;
  globalThis.fetch = async url => {
    const path = new URL(url instanceof Request ? url.url : url).pathname;
    if (path === "/api/health") return Response.json({ boot: "boot-A" });
    if (path === "/api/content/export") return Response.json({ present: false });
    if (path === "/api/profile") return originResponse({ name: "saved" }, 10);
    if (path === "/api/events") copies++;
    throw new Error(path);
  };
  await seed(app);
  const response = await worker.fetch(new Request("https://app.test/api/profile", {headers: {cookie: app.cookie}}), app.env, app.ctx);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("x-eesti-durable-seq"), "10");
  assert.equal(copies, 0);
});

test("a failed copy preserves the origin's error and never confirms success", async () => {
  const app = setup();
  globalThis.fetch = async url => {
    const path = new URL(url instanceof Request ? url.url : url).pathname;
    if (path === "/api/health") return Response.json({ boot: "boot-A" });
    if (path === "/api/content/export") return Response.json({ present: false });
    if (path === "/api/profile") return originResponse({ detail: "bad input" }, 11, "boot-A", 400);
    if (path === "/api/events") throw new Error("offline");
    throw new Error(path);
  };
  await seed(app);
  const response = await worker.fetch(new Request("https://app.test/api/profile", {headers: {cookie: app.cookie}}), app.env, app.ctx);
  assert.equal(response.status, 400);
  assert.equal(response.headers.get("x-eesti-durable-seq"), null);
  assert.deepEqual(await response.json(), { detail: "bad input" });
});

test("a transient copy failure retries the same boot before acknowledging", async () => {
  const app = setup();
  globalThis.fetch = async () => Response.json({ boot: "boot-A" });
  await seed(app);
  let calls = 0;
  globalThis.fetch = async url => {
    const path = new URL(url instanceof Request ? url.url : url).pathname;
    if (path === "/api/health") return Response.json({ boot: "boot-A" });
    if (path === "/api/profile") return originResponse({ saved: "new-A" }, 11);
    if (path === "/api/events") {
      if (++calls === 1) throw new Error("temporary connection failure");
      return originResponse({ events: [event("new-A", 11)], last_seq: 11 }, 11);
    }
    throw new Error(path);
  };
  const response = await worker.fetch(new Request("https://app.test/api/profile", {headers: {cookie: app.cookie}}), app.env, app.ctx);
  assert.equal(response.status, 200);
  assert.equal(calls, 2);
  assert.equal(app.objects.get("singleton").db.prepare("SELECT COUNT(*) AS n FROM events").get().n, 11);
});

test("speech evidence follows the same boot-bound acknowledgement", async () => {
  const app = setup();
  app.env.HOME_ASR = { async fetch() { return Response.json({ text: "Tere", engine: "test-ASR" }); } };
  app.env.HOME_ASR_TOKEN = "test-home-token";
  globalThis.fetch = async () => Response.json({ boot: "boot-A" });
  await seed(app);
  globalThis.fetch = async url => {
    const path = new URL(url instanceof Request ? url.url : url).pathname;
    if (path === "/api/transcribe/text") return originResponse({ text: "Tere" }, 11);
    if (path === "/api/events") throw new Error("offline");
    if (path === "/api/health") return Response.json({ boot: "boot-A" });
    throw new Error(path);
  };
  const response = await worker.fetch(new Request("https://app.test/api/transcribe", {
    method: "POST", body: "test-audio", headers: { "content-type": "audio/webm", cookie: app.cookie },
  }), app.env, app.ctx);
  assert.equal(response.status, 503);
  assert.equal(response.headers.get("retry-after"), "2");
});

test("public identity remains guest when sessions are not configured", async () => {
  const app = setup();
  app.env.LEARNER_STATE.get = () => { throw new Error("anonymous probe must not read account state"); };
  for (const headers of [{}, {"x-eesti-scope": "owner", cookie: "eesti_session=forged"}]) {
    const response = await worker.fetch(new Request("https://learn.test/api/auth/me", {headers}), app.env, app.ctx);
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), {scope: "guest", signup_open: false});
  }
  const signup = await worker.fetch(new Request("https://learn.test/api/auth/signup", {
    method: "POST", body: JSON.stringify({email: "visitor@example.test", password: "test-password"}),
  }), app.env, app.ctx);
  assert.equal(signup.status, 503);
});

test("public audio never reuses the old unscoped cache or caches private owner clips", async () => {
  const app = setup();
  app.owner.ensureRestored = async () => true;
  const previousCaches = globalThis.caches;
  const seen = [], written = [];
  globalThis.caches = {default: {
    async match(request) { seen.push(request.url); return undefined; },
    async put(request) { written.push(request.url); },
  }};
  globalThis.fetch = async request => {
    assert.equal(request.headers.get("x-eesti-scope"), "guest");
    return new Response("private clip", {headers: {"cache-control": "private, no-store"}});
  };
  try {
    const response = await worker.fetch(new Request("https://learn.test/api/speak?text=Tere"), app.env, app.ctx);
    assert.equal(response.status, 200);
    assert.equal(new URL(seen[0]).searchParams.get("__scope"), "public");
    assert.equal(new URL(seen[0]).searchParams.get("__grove_audio"), "public-v1");
    assert.deepEqual(written, []);
    globalThis.fetch = async () => new Response("synthesis", {headers: {"cache-control": "public, max-age=31536000"}});
    await worker.fetch(new Request("https://learn.test/api/speak?text=Tere"), app.env, app.ctx);
    await Promise.all(app.pending);
    assert.deepEqual(written, [seen[1]]);
  } finally { globalThis.caches = previousCaches; }
});

test("a rejected corpus restore retries before accepting the new origin boot", async () => {
  const app = setup();
  await app.owner.bindWho({ scope: "owner", id: "owner", email: "" });
  const { storage } = app.objects.get("singleton");
  const corpus = JSON.stringify({ database: "archived-private-corpus" });
  await storage.put("corpus-meta", { chunks: 1, bytes: corpus.length, at: 0 });
  await storage.put("corpus/0", corpus);
  let imports = 0;
  globalThis.fetch = async (input, init) => {
    const path = new URL(String(input)).pathname;
    if (path === "/api/health") return Response.json({ boot: "fresh-boot" });
    if (path === "/api/content/export") return Response.json({ present: false });
    if (path === "/api/content/import") {
      assert.equal(init.body, corpus);
      return Response.json({}, { status: ++imports === 1 ? 422 : 200 });
    }
    if (path === "/api/events/import") return Response.json({ ingested_seq: 0 });
    throw new Error(`Unexpected origin request: ${path}`);
  };
  assert.equal(await app.owner.ensureRestored(), false);
  assert.equal(await storage.get("origin"), undefined);
  assert.equal(await app.owner.ensureRestored(), true);
  assert.equal(imports, 2);
  assert.equal((await storage.get("origin")).boot, "fresh-boot");
});

test("a warm-origin corpus update is archived and restored on the next boot", async () => {
  const app = setup();
  app.env.SESSION_SECRET = "test-session-secret";
  const account = await app.owner.createOwnerAccount("owner@example.test", "test-password");
  const cookie = `eesti_session=${await signSession(account.id, app.env.SESSION_SECRET)}`;
  await app.owner.bindWho({ scope: "owner", id: "owner", email: "" });
  const { storage } = app.objects.get("singleton");
  let boot = "warm-boot", revision = "old-hash", present = true, broken = false;
  let corpus = JSON.stringify({ database: "old-private-corpus" });
  let replayed = 0;
  globalThis.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input));
    if (url.pathname === "/api/health") return Response.json({ boot, corpus_revision: revision });
    if (url.pathname === "/api/content/export") {
      if (url.searchParams.has("full")) return new Response(broken ? "{}" : corpus);
      return Response.json({ present });
    }
    if (url.pathname === "/api/content/import") {
      assert.equal(init.body, corpus, "cold start must receive the newer corpus");
      present = true;
      return Response.json({});
    }
    if (url.pathname === "/api/events/import") {
      replayed++;
      return Response.json({ ingested_seq: 0 });
    }
    throw new Error(`Unexpected origin request: ${url.pathname}`);
  };
  assert.equal(await app.owner.ensureRestored(), true);
  assert.equal(await app.owner.load("corpus"), corpus);
  const old = corpus;
  corpus = JSON.stringify({ database: "new-private-corpus".repeat(13000) });
  revision = "new-hash";
  app.owner.lastSeen = 0; // Advance past the ordinary liveness cache.
  broken = true;
  assert.equal(await app.owner.ensureRestored(), false);
  assert.equal(await app.owner.load("corpus"), old, "failed export keeps the usable archive");
  broken = false;
  const put = storage.put;
  let partial = true;
  storage.put = async (key, value) => {
    if (typeof key === "object" && partial) {
      partial = false;
      await put(Object.fromEntries(Object.entries(key).slice(0, 1)));
      throw new Error("interrupted chunk write");
    }
    return put(key, value);
  };
  assert.equal(await app.owner.ensureRestored(), false);
  assert.equal(await app.owner.load("corpus"), old, "interrupted chunks retain the old pointer");
  storage.put = put;
  assert.equal(await app.owner.ensureRestored(), true);
  assert.equal(await app.owner.load("corpus"), corpus);
  assert.equal((await storage.list({ prefix: "corpus/" })).size,
    (await storage.get("corpus-meta")).chunks, "old/interrupted generations are cleaned");
  assert.equal(replayed, 1, "a corpus update must not replay learner progress");
  corpus = JSON.stringify({ database: "explicit-publication-check" });
  revision = "checked-hash";
  const guest = await worker.fetch(new Request("https://learn.test/api/health"), app.env, app.ctx);
  assert.equal((await guest.json()).corpus_archived_revision, undefined,
    "guest health must not attest an owner's publication");
  const checked = await worker.fetch(new Request("https://learn.test/api/health", {
    headers: { cookie },
  }), app.env, app.ctx);
  const health = await checked.json();
  assert.equal(health.corpus_revision, revision);
  assert.equal(health.corpus_archived_revision, revision, "owner health bypasses the liveness cache");
  assert.equal(await app.owner.load("corpus"), corpus);
  boot = "cold-boot";
  present = false;
  revision = null;
  app.owner.lastSeen = 0;
  assert.equal(await app.owner.ensureRestored(), true);
  assert.equal(replayed, 2);
});

/** Run `body` with the clock moved forward, as a minute passing would. */
async function later(ms, body) {
  const now = Date.now;
  const offset = ms;
  Date.now = () => now() + offset;
  try { return await body(); } finally { Date.now = now; }
}

test("guest traffic never rewrites the owner's stored identity", async () => {
  const app = setup();
  await app.owner.bindWho({ scope: "owner", id: "owner", email: "owner@example.test" });
  app.owner.ensureRestored = async () => true;
  const { storage } = app.objects.get("singleton");
  const put = storage.put;
  const written = [];
  storage.put = async (key, value) => {
    written.push(typeof key === "object" ? Object.keys(key) : [key]);
    return put(key, value);
  };
  globalThis.fetch = async () => Response.json({ total: 1 });
  for (let i = 0; i < 3; i++) {
    const response = await worker.fetch(new Request("https://learn.test/api/library", {
      headers: { "x-eesti-guest": "materials-audit" },
    }), app.env, app.ctx);
    assert.equal(response.status, 200);
  }
  assert.deepEqual(written.flat().filter(key => key === "who"), [],
    "each request must not spend a Durable Object write rebinding the owner");
  assert.equal((await storage.get("who")).email, "owner@example.test",
    "back-channel calls keep the owner's email");
});

test("a fresh singleton is still restored as the owner before guest requests", async () => {
  const app = setup();
  globalThis.fetch = async request => {
    const url = new URL(request instanceof Request ? request.url : String(request));
    if (url.pathname === "/api/health") return Response.json({ boot: "boot-A" });
    if (url.pathname === "/api/content/export") return Response.json({ present: false });
    if (url.pathname === "/api/events/import") return Response.json({ ingested_seq: 0 });
    return Response.json({ total: 1 });
  };
  const response = await worker.fetch(new Request("https://learn.test/api/library", {
    headers: { "x-eesti-guest": "materials-audit" },
  }), app.env, app.ctx);
  assert.equal(response.status, 200);
  assert.deepEqual(await app.objects.get("singleton").storage.get("who"),
    { scope: "owner", id: "owner", email: "" });
});

test("the corpus is archived once: not again after eviction or a cold restore", async () => {
  const app = setup();
  await app.owner.bindWho({ scope: "owner", id: "owner", email: "owner@example.test" });
  const { storage } = app.objects.get("singleton");
  const corpus = JSON.stringify({ database: "private-corpus".repeat(9000) });
  let boot = "warm-boot", present = true, fullExports = 0, imports = 0;
  const probes = [];
  globalThis.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input));
    if (url.pathname === "/api/health") {
      probes.push(url.searchParams.get("live"));
      return Response.json({ boot, corpus_revision: present ? "rev-1" : null });
    }
    if (url.pathname === "/api/content/export") {
      if (!url.searchParams.has("full")) return Response.json({ present });
      fullExports++;
      return new Response(corpus);
    }
    if (url.pathname === "/api/content/import") {
      assert.equal(init.body, corpus);
      imports++;
      present = true;
      return Response.json({ bytes: 1, items: 1 });
    }
    if (url.pathname === "/api/events/import") return Response.json({ ingested_seq: 0 });
    throw new Error(`Unexpected origin request: ${url.pathname}`);
  };
  assert.equal(await app.owner.ensureRestored(), true);
  assert.equal(fullExports, 1);

  // Evicted from memory while the same origin instance keeps serving.
  const revived = new LearnerState({ storage }, app.env);
  assert.equal(await revived.ensureRestored(), true);
  assert.equal(fullExports, 1, "eviction must not re-export and re-archive the corpus");

  // A cold start: the archive goes back in, and the next liveness check finds
  // the container holding exactly what was archived.
  boot = "cold-boot";
  present = false;
  await later(61_000, () => revived.ensureRestored());
  assert.equal(imports, 1);
  await later(122_000, () => revived.ensureRestored());
  assert.equal(fullExports, 1, "a restored corpus must not be archived back");
  assert.ok(probes.length >= 3);
  assert.ok(probes.every(live => live === "1"), "restore uses the cheap liveness probe");
});

/** A subscribed learner whose origin answers `/api/reminders` with `answer`. */
async function subscribed(app, answer) {
  const vapid = await crypto.subtle.generateKey(
    { name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const jwk = await crypto.subtle.exportKey("jwk", vapid.privateKey);
  const raw = new Uint8Array(await crypto.subtle.exportKey("raw", vapid.publicKey));
  app.env.VAPID_PRIVATE_KEY = jwk.d;
  app.env.VAPID_PUBLIC_KEY = Buffer.from(raw).toString("base64url");
  app.env.VAPID_SUBJECT = "mailto:owner@example.test";
  const ua = await crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const uaPublic = new Uint8Array(await crypto.subtle.exportKey("raw", ua.publicKey));
  const learner = app.env.LEARNER_STATE.get("learner:l-0123456789abcdef");
  await learner.bindWho({ scope: "learner", id: "l-0123456789abcdef", email: "l@example.test" });
  await learner.subscribe({ endpoint: "https://push.example.test/sub", keys: {
    p256dh: Buffer.from(uaPublic).toString("base64url"),
    auth: Buffer.from(crypto.getRandomValues(new Uint8Array(16))).toString("base64url"),
  } });
  const calls = { reminders: 0, origin: 0, pushes: 0, pushStatus: 201 };
  globalThis.fetch = async input => {
    const url = new URL(input instanceof Request ? input.url : String(input));
    if (url.hostname === "push.example.test") {
      calls.pushes++;
      return new Response(null, { status: calls.pushStatus });
    }
    calls.origin++;
    if (url.pathname === "/api/health") return Response.json({ boot: calls.boot ?? "boot-A" });
    if (url.pathname === "/api/events/import") return Response.json({ ingested_seq: 0 });
    if (url.pathname === "/api/reminders") {
      calls.reminders++;
      return Response.json(answer());
    }
    throw new Error(`Unexpected origin request: ${url.pathname}`);
  };
  return { learner, calls, db: app.objects.get("learner:l-0123456789abcdef").db };
}

const HOUR = 3600_000;

test("the reminder cron leaves a sleeping origin alone until something can be due", async () => {
  const app = setup();
  let next = new Date(Date.now() + 3 * HOUR).toISOString();
  const { learner, calls, db } = await subscribed(app, () => ({ reminders: [], next_check: next }));
  await learner.remind();
  assert.equal(calls.reminders, 1);
  const contacted = calls.origin;

  // An hour later the instance has gone cold; nothing can be due yet.
  calls.boot = "boot-B";
  await later(HOUR, () => learner.remind());
  assert.equal(calls.origin, contacted, "no wake-up or restore before next_check");

  // New evidence (a settings change, a review) can change the answer.
  db.prepare("INSERT INTO events (id, body) VALUES ('settings-1', '{}')").run();
  await later(HOUR, () => learner.remind());
  assert.equal(calls.reminders, 2, "new evidence asks again");

  // The moment the app named.
  next = null;
  await later(4 * HOUR, () => learner.remind());
  assert.equal(calls.reminders, 3);
  // `null` (off, or quiet all day) still looks again within the safety cap.
  await later(5 * HOUR, () => learner.remind());
  assert.equal(calls.reminders, 3);
  await later(11 * HOUR, () => learner.remind());
  assert.equal(calls.reminders, 4, "a stale answer is re-checked at least every six hours");
});

test("an origin that does not name a next check is asked every hour", async () => {
  const app = setup();
  const { learner, calls } = await subscribed(app, () => ({ reminders: [] }));
  await learner.remind();
  await later(HOUR, () => learner.remind());
  assert.equal(calls.reminders, 2);
});

test("a reminder the push service refused is retried the next hour", async () => {
  const app = setup();
  const reminder = { tag: "kordamine-2026-10-08", title: "Kordamine", body: "12", url: "/#review" };
  const { learner, calls } = await subscribed(app, () => ({
    reminders: [reminder], next_check: new Date(Date.now() + 10 * HOUR).toISOString() }));
  calls.pushStatus = 503;
  await learner.remind();
  calls.pushStatus = 201;
  const second = await later(HOUR, () => learner.remind());
  assert.equal(calls.reminders, 2);
  assert.deepEqual([second.sent, calls.pushes], [1, 2]);
  await later(2 * HOUR, () => learner.remind());
  assert.equal(calls.reminders, 2, "delivered: sleep until the named moment");
});

async function gunzip(body) {
  const stream = new Response(body).body.pipeThrough(new DecompressionStream("gzip"));
  return new Response(stream).text();
}

test("the nightly cron sends every account's own log off Cloudflare", async () => {
  const app = setup();
  await app.owner.createOwnerAccount("owner@example.test", "test-password");
  const learner = await app.owner.createAccount("learner@example.test", "test-password");
  const logs = { singleton: [event("owner-1"), event("owner-2")],
                 [`learner:${learner.id}`]: [{ ...event("learner-1"), learner: learner.id }] };
  for (const [name, events] of Object.entries(logs)) {
    app.env.LEARNER_STATE.get(name);
    for (const ev of events) app.objects.get(name).db
      .prepare("INSERT INTO events (id, body) VALUES (?, ?)").run(ev.id, JSON.stringify(ev));
  }
  const sent = [];
  globalThis.fetch = async (input, init) => {
    const url = new URL(String(input));
    if (url.pathname !== "/api/state/backup") throw new Error(`Unexpected: ${url.pathname}`);
    assert.equal(init.headers["x-state-token"], "test-state");
    assert.equal(init.headers["content-type"], "application/gzip");
    sent.push({ scope: init.headers["x-eesti-scope"], learner: init.headers["x-eesti-learner"],
                body: await gunzip(init.body) });
    return Response.json({ verified: true, events: 1, object: "events/x" });
  };
  await worker.scheduled({ cron: BACKUP_CRON }, app.env, app.ctx);
  await Promise.all(app.pending);
  assert.equal(sent.length, 2);
  const owner = sent.find(s => s.scope === "owner");
  assert.deepEqual(owner.body.trim().split("\n").map(line => JSON.parse(line).id),
    ["owner-1", "owner-2"], "the log travels whole and in replay order");
  const other = sent.find(s => s.scope === "learner");
  assert.equal(other.learner, learner.id);
  assert.deepEqual(other.body.trim().split("\n").map(line => JSON.parse(line).id), ["learner-1"]);
  assert.equal((await app.objects.get("singleton").storage.get("backup-last")).ok, true);
});

test("the hourly cron reminds and the nightly one only backs up", async () => {
  const app = setup();
  await app.owner.createOwnerAccount("owner@example.test", "test-password");
  const called = [];
  app.owner.remind = async () => { called.push("remind"); return { sent: 0, skipped: 0 }; };
  app.owner.backup = async () => { called.push("backup"); return { ok: true, events: 0 }; };
  await worker.scheduled({ cron: "7 * * * *" }, app.env, app.ctx);
  await worker.scheduled({ cron: BACKUP_CRON }, app.env, app.ctx);
  await Promise.all(app.pending);
  assert.deepEqual(called, ["remind", "backup"]);
  assert.ok(readFileSync("wrangler.jsonc", "utf8").includes(`"${BACKUP_CRON}"`),
    "the nightly schedule is configured");
});

test("a refused backup is recorded and an empty log sends nothing", async () => {
  const app = setup();
  await app.owner.bindWho({ scope: "owner", id: "owner", email: "owner@example.test" });
  let requests = 0;
  globalThis.fetch = async () => {
    requests++;
    return Response.json({ detail: "not stored: cannot replay" }, { status: 422 });
  };
  const errors = [];
  const error = console.error;
  console.error = message => errors.push(message);
  try {
    assert.deepEqual(await app.owner.backup(), { ok: true, events: 0 });
    assert.equal(requests, 0);
    app.objects.get("singleton").db
      .prepare("INSERT INTO events (id, body) VALUES ('e', ?)").run(JSON.stringify(event("e")));
    const result = await app.owner.backup();
    assert.equal(result.ok, false);
    assert.equal(result.status, 422);
  } finally { console.error = error; }
  assert.equal((await app.objects.get("singleton").storage.get("backup-last")).ok, false);
  assert.ok(errors.some(line => String(line).includes("backup")), "a failure reaches the logs");
});
