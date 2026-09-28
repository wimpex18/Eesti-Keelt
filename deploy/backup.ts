import { normaliseEmail, type AccountBackup } from "./accounts";
import { type Who } from "./accounts";

export const BACKUP_FORMAT = "eesti-keelt-state";
export const BACKUP_VERSION = 1;
export const MAX_BACKUP_BYTES = 64 * 1024 * 1024;
export const MAX_BACKUP_ACCOUNTS = 10_000;
export const MAX_EVENTS_PER_LEARNER = 500_000;

export interface LearnerBackup {
  who: Exclude<Who, { scope: "guest" }>;
  events: Record<string, unknown>[];
}

export interface LearnerBackupPage {
  who: Exclude<Who, { scope: "guest" }>;
  eventsJson: string;
  next: number;
  done: boolean;
}

export interface StateBackup {
  format: typeof BACKUP_FORMAT;
  version: typeof BACKUP_VERSION;
  made: string;
  accounts: AccountBackup[];
  learners: LearnerBackup[];
}

function object(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function date(value: unknown): value is string {
  return typeof value === "string" && value.length <= 64 &&
    Number.isFinite(Date.parse(value));
}

function accountId(value: unknown): value is string {
  return value === "owner" ||
    (typeof value === "string" && /^l-[0-9a-f]{16}$/.test(value));
}

function validateAccount(value: unknown): asserts value is AccountBackup {
  if (!object(value) || !accountId(value.id) ||
      typeof value.email !== "string" || normaliseEmail(value.email) !== value.email ||
      typeof value.salt !== "string" || !/^[0-9a-f]{32}$/.test(value.salt) ||
      typeof value.hash !== "string" || !/^[0-9a-f]{64}$/.test(value.hash) ||
      !date(value.created)) {
    throw new Error("backup contains an invalid account");
  }
}

function validateLearner(value: unknown): asserts value is LearnerBackup {
  if (!object(value) || !object(value.who) || !Array.isArray(value.events) ||
      value.events.length > MAX_EVENTS_PER_LEARNER) {
    throw new Error("backup contains an invalid learner log");
  }
  const who = value.who;
  if (who.scope !== "owner" && who.scope !== "learner") {
    throw new Error("backup cannot contain a guest");
  }
  if (!accountId(who.id) || (who.scope === "owner" && who.id !== "owner") ||
      (who.scope === "learner" && who.id === "owner") ||
      typeof who.email !== "string" ||
      (who.email && normaliseEmail(who.email) !== who.email)) {
    throw new Error("backup contains an invalid learner identity");
  }
  const ids = new Set<string>();
  for (const event of value.events) {
    if (!object(event) || typeof event.id !== "string" || !event.id ||
        event.id.length > 200 || typeof event.type !== "string" || !event.type ||
        !date(event.ts) || (event.v !== 0 && event.v !== 1) ||
        event.learner !== who.id || !object(event.payload) || ids.has(event.id)) {
      throw new Error(`backup contains an invalid event for ${who.id}`);
    }
    ids.add(event.id);
  }
  if (value.events.length && !ids.has("backfill")) {
    throw new Error(`backup log for ${who.id} has no completeness marker`);
  }
}

/** Validate the complete envelope before restore mutates any Durable Object. */
export function validateBackup(value: unknown): asserts value is StateBackup {
  if (!object(value) || value.format !== BACKUP_FORMAT ||
      value.version !== BACKUP_VERSION || !date(value.made) ||
      !Array.isArray(value.accounts) || !Array.isArray(value.learners) ||
      value.accounts.length > MAX_BACKUP_ACCOUNTS ||
      value.learners.length > MAX_BACKUP_ACCOUNTS + 1) {
    throw new Error("unsupported or malformed backup envelope");
  }
  const accounts = new Map<string, AccountBackup>();
  const emails = new Set<string>();
  for (const account of value.accounts) {
    validateAccount(account);
    if (accounts.has(account.id) || emails.has(account.email)) {
      throw new Error("backup contains duplicate accounts");
    }
    accounts.set(account.id, account);
    emails.add(account.email);
  }
  const learners = new Set<string>();
  for (const learner of value.learners) {
    validateLearner(learner);
    const id = learner.who.id;
    if (learners.has(id)) throw new Error("backup contains duplicate learner logs");
    learners.add(id);
    const account = accounts.get(id);
    if (account && account.email !== learner.who.email) {
      throw new Error(`backup identity differs from account ${id}`);
    }
    if (!account && !(id === "owner" && accounts.size === 0)) {
      throw new Error(`backup has no account for learner ${id}`);
    }
  }
  for (const id of accounts.keys()) {
    if (!learners.has(id)) throw new Error(`backup has no learner log for account ${id}`);
  }
  if (!learners.has("owner")) throw new Error("backup has no owner log");
}

/** Stable comparison makes resumable restore insensitive to JSON key order. */
export function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (object(value)) {
    return `{${Object.keys(value).sort().map((key) =>
      `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
