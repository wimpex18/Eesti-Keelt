/* Exercise the account helpers under Node's WebCrypto implementation. */
import {
  AccountError,
  accountById,
  accountCount,
  authenticate,
  createAccount,
  deleteAccount,
  hashPassword,
  normaliseEmail,
  readSession,
  signSession,
} from "./accounts.ts";

type Row = Record<string, string | number>;

class MemorySql {
  rows = new Map<string, Row>();

  exec<T extends Row = Row>(query: string, ...values: unknown[]) {
    const sql = query.replace(/\s+/g, " ").trim().toLowerCase();
    const cursor = (rows: T[] = []) => ({ toArray: () => rows });
    if (sql.startsWith("create table")) return cursor();
    if (sql.startsWith("select count(*) as count"))
      return cursor([{count: this.rows.size} as unknown as T]);
    if (sql.includes("from accounts where email = ?") && sql.startsWith("select id from")) {
      const row = [...this.rows.values()].find(account => account.email === values[0]);
      return cursor(row ? [{id: row.id} as unknown as T] : []);
    }
    if (sql.startsWith("select * from accounts where email = ?")) {
      const row = [...this.rows.values()].find(account => account.email === values[0]);
      return cursor(row ? [row as unknown as T] : []);
    }
    if (sql.startsWith("select id, email, created from accounts where id = ?")) {
      const row = this.rows.get(String(values[0]));
      return cursor(row ? [{id: row.id, email: row.email, created: row.created} as unknown as T] : []);
    }
    if (sql.startsWith("insert into accounts")) {
      const [id, email, salt, hash, created] = values as string[];
      if ([...this.rows.values()].some(row => row.email === email)) throw new Error("duplicate");
      this.rows.set(id, {id, email, salt, hash, created, failures: 0, locked_until: 0});
      return cursor();
    }
    if (sql.startsWith("update accounts set failures = ?, locked_until = ? where id = ?")) {
      const [failures, locked, id] = values as [number, number, string];
      const row = this.rows.get(id);
      if (row) { row.failures = failures; row.locked_until = locked; }
      return cursor();
    }
    if (sql.startsWith("update accounts set failures = 0, locked_until = 0 where id = ?")) {
      const row = this.rows.get(String(values[0]));
      if (row) { row.failures = 0; row.locked_until = 0; }
      return cursor();
    }
    if (sql.startsWith("delete from accounts where id = ?")) {
      this.rows.delete(String(values[0]));
      return cursor();
    }
    throw new Error(`Unsupported SQL in check: ${sql}`);
  }
}

function assert(ok: unknown, message: string): asserts ok {
  if (!ok) throw new Error(message);
}

async function expectStatus(action: () => unknown | Promise<unknown>, status: number) {
  try { await action(); }
  catch (error) {
    assert(error instanceof AccountError && error.status === status,
      `expected AccountError ${status}, got ${String(error)}`);
    return;
  }
  throw new Error(`expected AccountError ${status}`);
}

async function main() {
  assert(normaliseEmail(" Person@Example.com ") === "person@example.com", "email normalization failed");
  assert(normaliseEmail("not-an-email") === null, "invalid email accepted");
  const sql = new MemorySql() as unknown as SqlStorage;
  const owner = await createAccount(sql, "Owner@example.com", "long-password-1");
  assert(owner.id === "owner" && owner.email === "owner@example.com", "first account is not owner");
  const accounts = [owner];
  for (let i = 0; i < 8; i++) {
    accounts.push(await createAccount(sql, `person${i}@example.com`, `long-password-${i + 2}`));
  }
  const learners = accounts.slice(1);
  assert(learners.every(a => /^l-[0-9a-f]{16}$/.test(a.id)), "learner id shape mismatch");
  assert(new Set(accounts.map(a => a.id)).size === accounts.length, "duplicate account id");
  assert(accountCount(sql) === 9, "account creation stopped below an unlimited test set");
  assert(accountById(sql, owner.id)?.email === owner.email, "account lookup failed");

  await expectStatus(() => createAccount(sql, "bad", "long-password-1"), 400);
  await expectStatus(() => createAccount(sql, "new@example.com", "short"), 400);
  await expectStatus(() => createAccount(sql, owner.email, "another-password"), 409);

  const good = await authenticate(sql, "PERSON0@example.com", "long-password-2");
  assert(good.id === learners[0].id, "password authentication failed");
  await expectStatus(() => authenticate(sql, "missing@example.com", "wrong-password"), 401);
  for (let i = 0; i < 4; i++) {
    await expectStatus(() => authenticate(sql, good.email, "wrong-password"), 401);
  }
  await expectStatus(() => authenticate(sql, good.email, "wrong-password"), 429);
  const now = Date.now;
  Date.now = () => now() + 60_001;
  assert((await authenticate(sql, good.email, "long-password-2")).id === good.id,
    "successful login did not clear the failed-login lock");
  Date.now = now;

  const hash = await hashPassword("same password", "11".repeat(16));
  assert(hash.length === 64 && hash === await hashPassword("same password", "11".repeat(16)),
    "PBKDF2 hash shape or determinism failed");
  const secret = "a-local-test-secret-with-32-bytes-minimum";
  const session = await signSession(good.id, secret);
  assert(await readSession(session, secret) === good.id, "signed session did not verify");
  assert(await readSession(session + "x", secret) === null, "tampered session verified");
  assert(await readSession(session, "different secret") === null, "wrong secret verified session");

  assert(deleteAccount(sql, good.id)?.id === good.id, "learner account was not removed");
  await expectStatus(() => deleteAccount(sql, "owner"), 400);
  assert(accountCount(sql) === 8, "account removal did not update the registry");
  console.log("ok");
}

main().catch(error => { console.error(String(error)); process.exit(1); });
