#!/usr/bin/env node
/** Encrypt, verify and restore a full Worker state backup from an external host. */
import {
  constants,
  createCipheriv,
  createDecipheriv,
  createHash,
  generateKeyPairSync,
  privateDecrypt,
  publicEncrypt,
  randomBytes,
} from "node:crypto";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { gzipSync, gunzipSync } from "node:zlib";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const MAX_BYTES = 64 * 1024 * 1024;
const ENCRYPTED_FORMAT = "eesti-keelt-encrypted-backup";
const STATE_FORMAT = "eesti-keelt-state";

function fail(message) {
  throw new Error(message);
}

function option(args, name, required = true) {
  const at = args.indexOf(name);
  if (at >= 0 && args[at + 1] && !args[at + 1].startsWith("--")) return args[at + 1];
  if (required) fail(`missing ${name}`);
  return null;
}

function absolute(value, label) {
  if (!isAbsolute(value)) fail(`${label} must be an absolute path`);
  return resolve(value);
}

function object(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function validDate(value) {
  return typeof value === "string" && value.length <= 64 && Number.isFinite(Date.parse(value));
}

function validId(value) {
  return value === "owner" || (typeof value === "string" && /^l-[0-9a-f]{16}$/.test(value));
}

function validateBundle(bundle) {
  if (!object(bundle) || bundle.format !== STATE_FORMAT || bundle.version !== 1 ||
      !validDate(bundle.made) || !Array.isArray(bundle.accounts) ||
      !Array.isArray(bundle.learners) || bundle.accounts.length > 10_000 ||
      bundle.learners.length > 10_001) {
    fail("unsupported or malformed state backup");
  }
  const accounts = new Map();
  const emails = new Set();
  for (const account of bundle.accounts) {
    if (!object(account) || !validId(account.id) || typeof account.email !== "string" ||
        account.email !== account.email.trim().toLowerCase() ||
        !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(account.email) ||
        !/^[0-9a-f]{32}$/.test(account.salt) || !/^[0-9a-f]{64}$/.test(account.hash) ||
        !validDate(account.created) || accounts.has(account.id) || emails.has(account.email)) {
      fail("backup contains an invalid or duplicate account");
    }
    accounts.set(account.id, account);
    emails.add(account.email);
  }
  const learners = new Set();
  for (const log of bundle.learners) {
    if (!object(log) || !object(log.who) || !validId(log.who.id) ||
        !["owner", "learner"].includes(log.who.scope) ||
        (log.who.scope === "owner") !== (log.who.id === "owner") ||
        typeof log.who.email !== "string" || !Array.isArray(log.events) ||
        log.events.length > 500_000 || learners.has(log.who.id)) {
      fail("backup contains an invalid or duplicate learner log");
    }
    const account = accounts.get(log.who.id);
    if ((!account && !(log.who.id === "owner" && accounts.size === 0)) ||
        (account && account.email !== log.who.email)) {
      fail(`backup account does not match learner ${log.who.id}`);
    }
    const eventIds = new Set();
    for (const event of log.events) {
      if (!object(event) || typeof event.id !== "string" || !event.id ||
          event.id.length > 200 || eventIds.has(event.id) ||
          typeof event.type !== "string" || !event.type || !validDate(event.ts) ||
          ![0, 1].includes(event.v) || event.learner !== log.who.id || !object(event.payload)) {
        fail(`backup contains an invalid event for ${log.who.id}`);
      }
      eventIds.add(event.id);
    }
    if (log.events.length && !eventIds.has("backfill")) {
      fail(`backup log for ${log.who.id} has no completeness marker`);
    }
    learners.add(log.who.id);
  }
  for (const id of accounts.keys()) {
    if (!learners.has(id)) fail(`backup has no learner log for account ${id}`);
  }
  if (!learners.has("owner")) fail("backup has no owner log");
  return bundle;
}

function pythonExecutable() {
  if (process.env.EESTI_BACKUP_PYTHON) return process.env.EESTI_BACKUP_PYTHON;
  const virtual = join(ROOT, ".venv", "bin", "python");
  return existsSync(virtual) ? virtual : "python";
}

function verifyReplay(bundle) {
  let events = 0;
  let replayed = 0;
  const program = [
    "import json,sys",
    "from eesti.recovery import verify_events",
    "print(json.dumps(verify_events(json.load(sys.stdin))))",
  ].join("; ");
  for (const log of bundle.learners) {
    events += log.events.length;
    if (!log.events.length) continue;
    const checked = spawnSync(pythonExecutable(), ["-c", program], {
      cwd: ROOT,
      encoding: "utf8",
      input: JSON.stringify(log.events),
      maxBuffer: MAX_BYTES,
    });
    if (checked.status !== 0) {
      fail(`replay verification failed for ${log.who.id}: ${(checked.stderr || checked.stdout).trim()}`);
    }
    const result = JSON.parse(checked.stdout);
    if (!result.verified || result.events !== log.events.length) {
      fail(`replay verification was incomplete for ${log.who.id}`);
    }
    replayed += 1;
  }
  return { learners: bundle.learners.length, replayed, events };
}

function digest(value) {
  return createHash("sha256").update(value).digest("hex");
}

function header(envelope) {
  return {
    format: envelope.format,
    version: envelope.version,
    created: envelope.created,
    cipher: envelope.cipher,
    wrapping: envelope.wrapping,
    compression: envelope.compression,
    sha256: envelope.sha256,
  };
}

function encrypt(plain, publicKey) {
  const key = randomBytes(32);
  const iv = randomBytes(12);
  const base = {
    format: ENCRYPTED_FORMAT,
    version: 1,
    created: new Date().toISOString(),
    cipher: "aes-256-gcm",
    wrapping: "rsa-oaep-sha256",
    compression: "gzip",
    sha256: digest(plain),
  };
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  cipher.setAAD(Buffer.from(JSON.stringify(base)));
  const data = Buffer.concat([cipher.update(gzipSync(plain)), cipher.final()]);
  return {
    ...base,
    wrapped_key: publicEncrypt({
      key: publicKey,
      padding: constants.RSA_PKCS1_OAEP_PADDING,
      oaepHash: "sha256",
    }, key).toString("base64"),
    iv: iv.toString("base64"),
    tag: cipher.getAuthTag().toString("base64"),
    data: data.toString("base64"),
  };
}

function decrypt(envelope, privateKey) {
  if (!object(envelope) || envelope.format !== ENCRYPTED_FORMAT || envelope.version !== 1 ||
      envelope.cipher !== "aes-256-gcm" || envelope.wrapping !== "rsa-oaep-sha256" ||
      envelope.compression !== "gzip" || !validDate(envelope.created) ||
      !/^[0-9a-f]{64}$/.test(envelope.sha256) ||
      !["wrapped_key", "iv", "tag", "data"].every((key) => typeof envelope[key] === "string")) {
    fail("unsupported or malformed encrypted backup");
  }
  const key = privateDecrypt({
    key: privateKey,
    padding: constants.RSA_PKCS1_OAEP_PADDING,
    oaepHash: "sha256",
  }, Buffer.from(envelope.wrapped_key, "base64"));
  const decipher = createDecipheriv("aes-256-gcm", key, Buffer.from(envelope.iv, "base64"));
  decipher.setAAD(Buffer.from(JSON.stringify(header(envelope))));
  decipher.setAuthTag(Buffer.from(envelope.tag, "base64"));
  const plain = gunzipSync(Buffer.concat([
    decipher.update(Buffer.from(envelope.data, "base64")),
    decipher.final(),
  ]), { maxOutputLength: MAX_BYTES });
  if (digest(plain) !== envelope.sha256) fail("backup digest does not match its plaintext");
  return plain;
}

function atomicWrite(path, body, beforeCommit = null) {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = `${path}.${process.pid}.${Date.now()}.tmp`;
  try {
    writeFileSync(temporary, body, { mode: 0o600, flag: "wx" });
    if (beforeCommit) beforeCommit(temporary);
    renameSync(temporary, path);
    chmodSync(path, 0o600);
  } catch (error) {
    rmSync(temporary, { force: true });
    throw error;
  }
}

function loadEncrypted(path, privatePath) {
  const bytes = readFileSync(path);
  if (bytes.byteLength > MAX_BYTES * 2) fail("encrypted backup is too large");
  const envelope = JSON.parse(bytes.toString("utf8"));
  const plain = decrypt(envelope, readFileSync(privatePath, "utf8"));
  const bundle = validateBundle(JSON.parse(plain.toString("utf8")));
  const verified = verifyReplay(bundle);
  return { bundle, verified };
}

async function keygen(args) {
  const publicPath = absolute(option(args, "--public"), "public key path");
  const privatePath = absolute(option(args, "--private"), "private key path");
  if (existsSync(publicPath) || existsSync(privatePath)) fail("refusing to overwrite an existing key");
  const pair = generateKeyPairSync("rsa", {
    modulusLength: 3072,
    publicKeyEncoding: { type: "spki", format: "pem" },
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
  });
  atomicWrite(privatePath, pair.privateKey);
  atomicWrite(publicPath, pair.publicKey);
  console.log(JSON.stringify({ generated: true, public_key: publicPath, private_key: privatePath }));
}

async function backup(args) {
  const base = option(args, "--url").replace(/\/$/, "");
  const publicPath = absolute(option(args, "--public-key"), "public key path");
  const privatePath = absolute(option(args, "--private-key"), "private key path");
  const out = absolute(option(args, "--out"), "backup directory");
  const token = process.env.BACKUP_TOKEN;
  if (!token || token.length < 32) fail("BACKUP_TOKEN must be set and at least 32 characters");
  const response = await fetch(`${base}/api/backup/export`, {
    headers: { authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(120_000),
  });
  if (!response.ok) fail(`backup export returned ${response.status}: ${(await response.text()).slice(0, 500)}`);
  const plain = Buffer.from(await response.arrayBuffer());
  if (plain.byteLength > MAX_BYTES) fail("state backup is too large");
  const bundle = validateBundle(JSON.parse(plain.toString("utf8")));
  const envelope = encrypt(plain, readFileSync(publicPath, "utf8"));
  const stamp = bundle.made.replace(/[:.]/g, "-");
  const target = join(out, `eesti-keelt-${stamp}.ekb`);
  let verified;
  // Decrypt and replay the actual bytes before their atomic rename. A green
  // daily run is therefore a restore rehearsal, not only an export check.
  atomicWrite(target, JSON.stringify(envelope) + "\n", (temporary) => {
    verified = loadEncrypted(temporary, privatePath).verified;
  });
  console.log(JSON.stringify({ backed_up: true, path: target, ...verified }));
}

async function verify(args) {
  const file = absolute(args[0] ?? fail("missing encrypted backup file"), "backup file");
  const privatePath = absolute(option(args, "--private-key"), "private key path");
  const { bundle, verified } = loadEncrypted(file, privatePath);
  console.log(JSON.stringify({ verified: true, made: bundle.made, ...verified }));
}

async function restore(args) {
  const file = absolute(args[0] ?? fail("missing encrypted backup file"), "backup file");
  const privatePath = absolute(option(args, "--private-key"), "private key path");
  const { bundle, verified } = loadEncrypted(file, privatePath);
  if (!args.includes("--apply")) {
    console.log(JSON.stringify({ dry_run: true, made: bundle.made, ...verified }));
    return;
  }
  const base = option(args, "--url").replace(/\/$/, "");
  const token = process.env.RESTORE_TOKEN;
  if (!token || token.length < 32) fail("RESTORE_TOKEN must be set and at least 32 characters");
  const response = await fetch(`${base}/api/backup/restore`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(bundle),
    signal: AbortSignal.timeout(120_000),
  });
  const result = await response.text();
  if (!response.ok) fail(`restore returned ${response.status}: ${result.slice(0, 1000)}`);
  console.log(result);
}

async function selfTest() {
  const folder = join(process.cwd(), `.backup-self-test-${process.pid}-${Date.now()}`);
  mkdirSync(folder, { mode: 0o700 });
  try {
    const publicPath = join(folder, "public.pem");
    const privatePath = join(folder, "private.pem");
    await keygen(["--public", publicPath, "--private", privatePath]);
    const bundle = validateBundle({
      format: STATE_FORMAT,
      version: 1,
      made: "2026-01-01T00:00:00.000Z",
      accounts: [],
      learners: [{
        who: { scope: "owner", id: "owner", email: "" },
        events: [{
          id: "backfill",
          type: "backfill",
          ts: "2026-01-01T00:00:00.000+00:00",
          v: 1,
          learner: "owner",
          payload: { rows: 0 },
        }],
      }],
    });
    const plain = Buffer.from(JSON.stringify(bundle));
    const envelope = encrypt(plain, readFileSync(publicPath, "utf8"));
    const damaged = { ...envelope };
    const changed = Buffer.from(damaged.data, "base64");
    changed[0] ^= 1;
    damaged.data = changed.toString("base64");
    let tamperRejected = false;
    try {
      decrypt(damaged, readFileSync(privatePath, "utf8"));
    } catch {
      tamperRejected = true;
    }
    if (!tamperRejected) fail("self-test accepted a modified encrypted backup");
    const file = join(folder, "self-test.ekb");
    atomicWrite(file, JSON.stringify(envelope));
    const checked = loadEncrypted(file, privatePath);
    if (checked.verified.events !== 1) fail("self-test event was not replayed");
    console.log(JSON.stringify({
      self_test: true,
      encrypted: true,
      tamper_rejected: true,
      replayed: true,
    }));
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
}

function usage() {
  console.error(`Usage:
  backup-state.mjs keygen --public /path/public.pem --private /path/private.pem
  backup-state.mjs backup --url https://app.example --public-key /path/public.pem --private-key /path/private.pem --out /backup/dir
  backup-state.mjs verify /backup/file.ekb --private-key /path/private.pem
  backup-state.mjs restore /backup/file.ekb --private-key /path/private.pem [--url URL --apply]
  backup-state.mjs self-test`);
}

const command = process.argv[2];
const args = process.argv.slice(3);
try {
  if (command === "keygen") await keygen(args);
  else if (command === "backup") await backup(args);
  else if (command === "verify") await verify(args);
  else if (command === "restore") await restore(args);
  else if (command === "self-test") await selfTest();
  else {
    usage();
    process.exitCode = 2;
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
