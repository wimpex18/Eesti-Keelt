import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { afterEach, test } from "node:test";
import worker, { LearnerState } from "../deploy/worker.ts";
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
    async put(key, value) { values.set(key, structuredClone(value)); },
    async delete(key) { return values.delete(key); },
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
    ALLOW_UNAUTHENTICATED: "1",
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

test("the front door overwrites a forged social artwork origin", async () => {
  const app = setup();
  await seed(app);
  let forwarded;
  globalThis.fetch = async request => {
    forwarded = request;
    return new Response("<html>Estep</html>", {headers: {"content-type": "text/html"}});
  };
  const response = await worker.fetch(new Request("https://learn.test/", {
    headers: {"x-brand-origin": "https://forged.test"},
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
      const owner = await app.owner.createAccount("owner@example.test", "test-password");
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
  const response = await worker.fetch(new Request("https://app.test/api/profile"), app.env, app.ctx);
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
  const response = await worker.fetch(new Request("https://app.test/api/profile"), app.env, app.ctx);
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
    if (path === "/api/profile") return originResponse({ name: "saved" }, 10);
    if (path === "/api/events") copies++;
    throw new Error(path);
  };
  await seed(app);
  const response = await worker.fetch(new Request("https://app.test/api/profile"), app.env, app.ctx);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("x-eesti-durable-seq"), "10");
  assert.equal(copies, 0);
});

test("a failed copy preserves the origin's error and never confirms success", async () => {
  const app = setup();
  globalThis.fetch = async url => {
    const path = new URL(url instanceof Request ? url.url : url).pathname;
    if (path === "/api/health") return Response.json({ boot: "boot-A" });
    if (path === "/api/profile") return originResponse({ detail: "bad input" }, 11, "boot-A", 400);
    if (path === "/api/events") throw new Error("offline");
    throw new Error(path);
  };
  await seed(app);
  const response = await worker.fetch(new Request("https://app.test/api/profile"), app.env, app.ctx);
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
  const response = await worker.fetch(new Request("https://app.test/api/profile"), app.env, app.ctx);
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
    method: "POST", body: "test-audio", headers: { "content-type": "audio/webm" },
  }), app.env, app.ctx);
  assert.equal(response.status, 503);
  assert.equal(response.headers.get("retry-after"), "2");
});
