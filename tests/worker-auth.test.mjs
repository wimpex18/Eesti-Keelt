// Real workerd RPC: a direct LearnerState stub preserves custom prototypes and
// cannot reproduce the production login/validation errors crossing the DO.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { build } from "esbuild";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";

let runtime;
const password = "isolated-test-password";
async function post(path, body, headers = {}) {
  return runtime.dispatchFetch("https://learn.test/api/auth/" + path, {
    method: "POST", headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
}
before(async () => {
  const bundle = await build({ entryPoints: ["deploy/worker.ts"], bundle: true,
    format: "esm", platform: "browser", external: ["cloudflare:workers"], write: false });
  runtime = new Miniflare(convertV4MiniflareOptions({ modules: true, script: bundle.outputFiles[0].text,
    compatibilityDate: "2026-08-01", compatibilityFlags: ["nodejs_compat"],
    durableObjects: { LEARNER_STATE: { className: "LearnerState", useSQLite: true } },
    bindings: { SESSION_SECRET: "test-session",
      CLOUD_RUN_URL: "https://origin.test", PROXY_TOKEN: "test-proxy", STATE_TOKEN: "test-state" },
  }));
  const empty = await runtime.dispatchFetch("https://learn.test/api/auth/me");
  assert.equal((await empty.json()).scope, "guest");
  const first = await post("signup", { email: "first@example.test", password });
  assert.equal((await first.json()).scope, "learner");
  const blocked = await post("bootstrap", { email: "owner@example.test", password });
  assert.equal(blocked.status, 404);
  const owner = await post("bootstrap", { email: "owner@example.test", password }, {"x-state-token": "test-state"});
  assert.equal(owner.status, 200);
  assert.equal((await owner.json()).scope, "owner");
  assert.equal((await post("bootstrap", { email: "other@example.test", password }, {"x-state-token": "test-state"})).status, 409);
});
after(async () => { await runtime?.dispose(); });

test("RPC account validation returns actionable 400 and duplicate 409", async () => {
  for (const [email, value] of [["bad", password], ["short@example.test", "short"]]) {
    const response = await post("signup", { email, password: value });
    assert.equal(response.status, 400);
    assert.ok((await response.json()).detail.length > 0);
  }
  const duplicate = await post("signup", { email: " OWNER@example.test ", password });
  assert.equal(duplicate.status, 409);
});

test("RPC login keeps unknown email and wrong password indistinguishable", async () => {
  const unknown = await post("login", { email: "missing@example.test", password });
  const wrong = await post("login", { email: "owner@example.test", password: "wrong" });
  assert.equal(unknown.status, 401);
  assert.equal(wrong.status, 401);
  assert.deepEqual(await unknown.json(), await wrong.json());
});

test("RPC signup, session, logout and lockout work through actual Durable Objects", async () => {
  const created = await post("signup", { email: "learner@example.test", password });
  assert.equal(created.status, 200);
  assert.equal((await created.json()).scope, "learner");
  const cookie = created.headers.get("set-cookie");
  for (const flag of ["HttpOnly", "Secure", "SameSite=Lax", "Path=/"]) assert.ok(cookie.includes(flag));
  const me = await runtime.dispatchFetch("https://learn.test/api/auth/me", {
    headers: { cookie: cookie.split(";")[0] },
  });
  assert.equal((await me.json()).email, "learner@example.test");
  const out = await post("logout", {});
  assert.ok(out.headers.get("set-cookie").includes("Max-Age=0"));
  const login = await post("login", { email: "LEARNER@example.test", password });
  assert.equal(login.status, 200);
  for (let attempt = 1; attempt <= 5; attempt++) {
    const bad = await post("login", { email: "learner@example.test", password: "wrong" });
    assert.equal(bad.status, attempt === 5 ? 429 : 401);
  }
  assert.equal((await post("login", { email: "learner@example.test", password })).status, 429);
});

test("signed-out and forged scope requests always resolve to guests", async () => {
  for (const headers of [{}, {"x-eesti-scope": "owner"}, {cookie: "eesti_session=forged"}]) {
    const response = await runtime.dispatchFetch("https://learn.test/api/auth/me", {headers});
    assert.equal(response.status, 200);
    assert.equal((await response.json()).scope, "guest");
  }
});

test("existing owner credentials still access owner progress", async () => {
  const logged = await post("login", { email: "owner@example.test", password });
  assert.equal((await logged.json()).scope, "owner");
  const me = await runtime.dispatchFetch("https://learn.test/api/auth/me", {
    headers: {cookie: logged.headers.get("set-cookie").split(";")[0]},
  });
  assert.equal((await me.json()).scope, "owner");
});
