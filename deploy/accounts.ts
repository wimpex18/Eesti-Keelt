/**
 * In-app accounts (ADR-0006): sign-up, sign-in and the session cookie.
 *
 * Accounts live in the `singleton` LearnerState's SQL store, so they are as
 * permanent as the evidence log. The Worker answers `/api/auth/*` with these
 * helpers and turns a valid session into the scope headers the origin trusts
 * (`eesti/identity.py`). Not signed in is a guest.
 *
 * `docs/identity.md` ("Worker") is the specification.
 */

export const SESSION_COOKIE = "eesti_session";
export const SESSION_DAYS = 90;
export const PBKDF2_ITERATIONS = 100_000;
export const PASSWORD_MIN = 10;
export const PASSWORD_MAX = 1024;
export const EMAIL_MAX = 254;

export interface Account {
  /** `owner` for the first account, `l-` + 16 hex digits after that. */
  id: string;
  email: string;
  created: string;
}

/** Sensitive account record used only inside an encrypted disaster backup. */
export interface AccountBackup extends Account {
  salt: string;
  hash: string;
}

export type Who =
  | { scope: "owner"; id: "owner"; email: string }
  | { scope: "learner"; id: string; email: string }
  | { scope: "guest" };

/** Lower-case, trimmed; null when it does not look like an email. */
export function normaliseEmail(raw: string): string | null {
  const email = raw.trim().toLowerCase();
  return email.length <= EMAIL_MAX && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
    ? email : null;
}

/** `l-` + 16 hex digits from `crypto.getRandomValues`; `identity.learner_id` accepts it. */
export function newLearnerId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return "l-" + [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** PBKDF2-SHA-256 of the password with the account's salt, as hex. */
export async function hashPassword(password: string, salt: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({
    name: "PBKDF2",
    hash: "SHA-256",
    salt: fromHex(salt),
    iterations: PBKDF2_ITERATIONS,
  }, key, 256);
  return toHex(new Uint8Array(bits));
}

/** The cookie value `<id>.<expiry ms>.<hmac hex>`, signed with `SESSION_SECRET`. */
export async function signSession(id: string, secret: string): Promise<string> {
  const expiry = Date.now() + SESSION_DAYS * 24 * 60 * 60 * 1000;
  const payload = `${id}.${expiry}`;
  return `${payload}.${await hmac(payload, secret)}`;
}

/** The account id in a valid, unexpired cookie value, or null. Constant-time. */
export async function readSession(value: string, secret: string): Promise<string | null> {
  const parts = value.split(".");
  if (parts.length !== 3) return null;
  const [id, rawExpiry, given] = parts;
  if (id !== "owner" && !/^l-[0-9a-f]{16}$/.test(id)) return null;
  if (!/^\d{13}$/.test(rawExpiry) || !/^[0-9a-f]{64}$/.test(given)) return null;
  if (Number(rawExpiry) <= Date.now()) return null;
  const expected = await hmac(`${id}.${rawExpiry}`, secret);
  return constantTimeEqual(given, expected) ? id : null;
}

export class AccountError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "AccountError";
    this.status = status;
  }
}

interface AccountRow extends Record<string, SqlStorageValue> {
  id: string;
  email: string;
  salt: string;
  hash: string;
  created: string;
  failures: number;
  locked_until: number;
}

export function ensureAccounts(sql: SqlStorage): void {
  sql.exec(`CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    salt TEXT NOT NULL,
    hash TEXT NOT NULL,
    created TEXT NOT NULL,
    failures INTEGER NOT NULL DEFAULT 0,
    locked_until INTEGER NOT NULL DEFAULT 0
  )`);
}

export function accountCount(sql: SqlStorage): number {
  ensureAccounts(sql);
  return Number(sql.exec<{ count: number }>("SELECT COUNT(*) AS count FROM accounts")
    .toArray()[0]?.count ?? 0);
}

export function accountById(sql: SqlStorage, id: string): Account | null {
  ensureAccounts(sql);
  const row = sql.exec<AccountRow>(
    "SELECT id, email, created FROM accounts WHERE id = ?", id).toArray()[0];
  return row ? { id: row.id, email: row.email, created: row.created } : null;
}

export function backupAccounts(sql: SqlStorage): AccountBackup[] {
  ensureAccounts(sql);
  return sql.exec<AccountRow>(
    "SELECT id, email, salt, hash, created FROM accounts ORDER BY created, id",
  ).toArray().map(({ id, email, salt, hash, created }) =>
    ({ id, email, salt, hash, created }));
}

/** Insert missing account credentials, rejecting divergence before any write. */
export function restoreAccounts(sql: SqlStorage, incoming: AccountBackup[]): number {
  ensureAccounts(sql);
  const existing = sql.exec<AccountRow>(
    "SELECT id, email, salt, hash, created FROM accounts ORDER BY created, id",
  ).toArray();
  const byId = new Map(existing.map((row) => [row.id, row]));
  const byEmail = new Map(existing.map((row) => [row.email, row]));
  for (const account of incoming) {
    const current = byId.get(account.id) ?? byEmail.get(account.email);
    if (current && (current.id !== account.id || current.email !== account.email ||
        current.salt !== account.salt || current.hash !== account.hash ||
        current.created !== account.created)) {
      throw new Error(`account restore conflicts with ${account.id}`);
    }
  }
  let added = 0;
  for (const account of incoming) {
    if (byId.has(account.id)) continue;
    sql.exec(
      "INSERT INTO accounts (id,email,salt,hash,created,failures,locked_until) " +
        "VALUES (?,?,?,?,?,0,0)",
      account.id, account.email, account.salt, account.hash, account.created,
    );
    added += 1;
  }
  return added;
}

/** Remove a learner login. The caller separately clears that learner's object. */
export function deleteAccount(sql: SqlStorage, id: string): Account | null {
  if (id === "owner") throw new AccountError(400, "Основной аккаунт удалить нельзя.");
  ensureAccounts(sql);
  const account = accountById(sql, id);
  if (account) sql.exec("DELETE FROM accounts WHERE id = ?", id);
  return account;
}

export async function createAccount(
  sql: SqlStorage,
  emailRaw: string,
  password: string,
): Promise<Account> {
  const email = normaliseEmail(emailRaw);
  if (!email) throw new AccountError(400, "Введи действующий адрес электронной почты.");
  if (password.length < PASSWORD_MIN) {
    throw new AccountError(400, `Пароль должен содержать не менее ${PASSWORD_MIN} символов.`);
  }
  if (password.length > PASSWORD_MAX) {
    throw new AccountError(400, `Пароль должен содержать не более ${PASSWORD_MAX} символов.`);
  }
  ensureAccounts(sql);
  const saltBytes = crypto.getRandomValues(new Uint8Array(16));
  const salt = toHex(saltBytes);
  const hash = await hashPassword(password, salt);

  // No await occurs between the count and insert, so concurrent requests cannot
  // both see an empty table and claim the owner identity.
  const count = accountCount(sql);
  if (sql.exec<{ id: string }>("SELECT id FROM accounts WHERE email = ?", email).toArray().length) {
    throw new AccountError(409, "Этот адрес электронной почты уже зарегистрирован.");
  }
  const id = count === 0 ? "owner" : newLearnerId();
  const created = new Date().toISOString();
  try {
    sql.exec("INSERT INTO accounts (id,email,salt,hash,created) VALUES (?,?,?,?,?)",
      id, email, salt, hash, created);
  } catch {
    throw new AccountError(409, "Адрес уже используется. Попробуй другой.");
  }
  return { id, email, created };
}

export async function authenticate(
  sql: SqlStorage, emailRaw: string, password: string,
): Promise<Account> {
  if (password.length > PASSWORD_MAX) {
    throw new AccountError(400, `Пароль должен содержать не более ${PASSWORD_MAX} символов.`);
  }
  const email = normaliseEmail(emailRaw);
  ensureAccounts(sql);
  const row = email
    ? sql.exec<AccountRow>("SELECT * FROM accounts WHERE email = ?", email).toArray()[0]
    : undefined;
  const now = Date.now();
  const dummySalt = "00".repeat(16);
  const candidate = await hashPassword(password, row?.salt ?? dummySalt);
  if (!row) {
    // Keep unknown-account and wrong-password responses indistinguishable.
    constantTimeEqual(candidate, "00".repeat(32));
    throw new AccountError(401, "Электронная почта или пароль указаны неверно.");
  }
  if (row.locked_until > now) {
    throw new AccountError(429, "Слишком много попыток входа. Подожди минуту и попробуй снова.");
  }
  if (!constantTimeEqual(candidate, row.hash)) {
    const failures = row.failures + 1;
    const lock = failures >= 5 ? now + 60_000 : row.locked_until;
    sql.exec("UPDATE accounts SET failures = ?, locked_until = ? WHERE id = ?",
      failures >= 5 ? 0 : failures, lock, row.id);
    if (failures >= 5) {
      throw new AccountError(429, "Слишком много попыток входа. Подожди минуту и попробуй снова.");
    }
    throw new AccountError(401, "Электронная почта или пароль указаны неверно.");
  }
  sql.exec("UPDATE accounts SET failures = 0, locked_until = 0 WHERE id = ?", row.id);
  return { id: row.id, email: row.email, created: row.created };
}

async function hmac(value: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" },
    false, ["sign"]);
  return toHex(new Uint8Array(await crypto.subtle.sign(
    "HMAC", key, new TextEncoder().encode(value))));
}

function constantTimeEqual(a: string, b: string): boolean {
  let difference = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let i = 0; i < length; i++) {
    difference |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return difference === 0;
}

function toHex(bytes: Uint8Array): string {
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function fromHex(value: string): Uint8Array {
  if (!/^(?:[0-9a-f]{2})+$/i.test(value)) throw new Error("invalid hex input");
  return new Uint8Array(value.match(/.{2}/g)!.map((byte) => Number.parseInt(byte, 16)));
}
