/**
 * In-app accounts (ADR-0006): sign-up, sign-in and the session cookie.
 *
 * Accounts live in the `singleton` LearnerState's SQL store, so they are as
 * permanent as the evidence log. The Worker answers `/api/auth/*` with these
 * helpers and turns a valid session into the scope headers the origin trusts
 * (`eesti/identity.py`). Not signed in is a guest.
 *
 * SKELETON: `docs/identity.md` ("Worker changes") is the specification. Nothing
 * imports this file yet; replace every TODO(Luna).
 */

export const SESSION_COOKIE = "eesti_session";
export const SESSION_DAYS = 90;
export const PBKDF2_ITERATIONS = 100_000;
export const PASSWORD_MIN = 10;
export const DEFAULT_MAX_ACCOUNTS = 2;

export interface Account {
  /** `owner` for the first account, `l-` + 16 hex digits after that. */
  id: string;
  email: string;
  created: string;
}

export type Who =
  | { scope: "owner"; id: "owner"; email: string }
  | { scope: "learner"; id: string; email: string }
  | { scope: "guest" };

/** Lower-case, trimmed; null when it does not look like an email. */
export function normaliseEmail(raw: string): string | null {
  const email = raw.trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : null;
}

/** `l-` + 16 hex digits from `crypto.getRandomValues`; `identity.learner_id` accepts it. */
export function newLearnerId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return "l-" + [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** PBKDF2-SHA-256 of the password with the account's salt, hex. TODO(Luna). */
export async function hashPassword(_password: string, _salt: string): Promise<string> {
  throw new Error("TODO(Luna): crypto.subtle PBKDF2, PBKDF2_ITERATIONS, 32 bytes");
}

/** The cookie value `<id>.<expiry ms>.<hmac hex>`, signed with `SESSION_SECRET`. TODO(Luna). */
export async function signSession(_id: string, _secret: string): Promise<string> {
  throw new Error("TODO(Luna): HMAC-SHA-256 over `<id>.<expiry>`");
}

/** The account id in a valid, unexpired cookie value, or null. Constant-time. TODO(Luna). */
export async function readSession(_value: string, _secret: string): Promise<string | null> {
  throw new Error("TODO(Luna)");
}
