/**
 * Web Push, the parts that are only arithmetic: VAPID (RFC 8292) and the
 * encrypted payload (RFC 8291).
 *
 * Kept out of `worker.ts` so it can be run and checked outside Cloudflare —
 * `tests/test_push_crypto.py` decrypts what `encryptPayload` produces with the
 * subscription's own private key, which is the only way to know a notification
 * would arrive rather than be dropped by the push service.
 */

/* ------------------------------------------------------------------ *
 * Web Push: VAPID (RFC 8292) and the encrypted payload (RFC 8291).
 *
 * A reminder carries counts only (`eesti/reminders.py`), but it still travels
 * through Apple's or Google's push service, so it is encrypted to the
 * subscription's own key and those services see ciphertext. The app decides
 * *what* is worth sending; this only sends it.
 * ------------------------------------------------------------------ */

export interface PushKeys {
  VAPID_PUBLIC_KEY?: string;
  VAPID_PRIVATE_KEY?: string;
  VAPID_SUBJECT?: string;
}

export interface PushSubscription {
  endpoint: string;
  keys: { p256dh: string; auth: string };
}

function b64urlToBytes(value: string): Uint8Array {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/")
    + "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (c) => c.charCodeAt(0));
}

function bytesToB64url(bytes: ArrayBuffer | Uint8Array): string {
  const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let binary = "";
  for (let i = 0; i < view.length; i += 0x8000) {
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function concat(...parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const part of parts) { out.set(part, at); at += part.length; }
  return out;
}

/** HKDF, the two halves the spec names separately. */
async function hkdf(salt: Uint8Array, ikm: Uint8Array, info: Uint8Array,
                    length: number): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "HKDF", hash: "SHA-256", salt, info }, key, length * 8);
  return new Uint8Array(bits);
}

/** The private VAPID key as a signing key; the public one gives x and y. */
export async function vapidKey(env: PushKeys): Promise<CryptoKey> {
  const pub = b64urlToBytes(env.VAPID_PUBLIC_KEY!);
  const jwk: JsonWebKey = {
    kty: "EC", crv: "P-256", ext: true,
    d: env.VAPID_PRIVATE_KEY!,
    x: bytesToB64url(pub.subarray(1, 33)),
    y: bytesToB64url(pub.subarray(33, 65)),
  };
  return crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" },
                                 false, ["sign"]);
}

/** The `Authorization: vapid ...` header for one push service. */
export async function vapidHeader(env: PushKeys, endpoint: string): Promise<string> {
  const aud = new URL(endpoint).origin;
  const header = bytesToB64url(new TextEncoder().encode(
    JSON.stringify({ typ: "JWT", alg: "ES256" })));
  const claims = bytesToB64url(new TextEncoder().encode(JSON.stringify({
    aud,
    exp: Math.floor(Date.now() / 1000) + 12 * 3600,
    sub: env.VAPID_SUBJECT || "mailto:none@example.org",
  })));
  const signed = `${header}.${claims}`;
  const signature = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" }, await vapidKey(env),
    new TextEncoder().encode(signed));
  return `vapid t=${signed}.${bytesToB64url(signature)}, k=${env.VAPID_PUBLIC_KEY}`;
}

/** RFC 8291: the body of one push message, encrypted to the subscription. */
export async function encryptPayload(sub: PushSubscription, plaintext: string)
    : Promise<Uint8Array> {
  const uaPublic = b64urlToBytes(sub.keys.p256dh);
  const auth = b64urlToBytes(sub.keys.auth);

  const ephemeral = await crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]) as CryptoKeyPair;
  const asPublic = new Uint8Array(
    await crypto.subtle.exportKey("raw", ephemeral.publicKey) as ArrayBuffer);
  const uaKey = await crypto.subtle.importKey(
    "raw", uaPublic, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const shared = new Uint8Array(await crypto.subtle.deriveBits(
    // `public` is the name WebCrypto uses; the Workers types spell it
    // `$public` because their code generator reserves the word.
    { name: "ECDH", public: uaKey } as unknown as Parameters<SubtleCrypto["deriveBits"]>[0],
    ephemeral.privateKey, 256));

  const encoder = new TextEncoder();
  const ikm = await hkdf(
    auth, shared,
    concat(encoder.encode("WebPush: info\0"), uaPublic, asPublic), 32);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const cek = await hkdf(salt, ikm, encoder.encode("Content-Encoding: aes128gcm\0"), 16);
  const nonce = await hkdf(salt, ikm, encoder.encode("Content-Encoding: nonce\0"), 12);

  const key = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["encrypt"]);
  // 0x02 is the padding delimiter for the last (only) record.
  const body = concat(encoder.encode(plaintext), new Uint8Array([2]));
  const sealed = new Uint8Array(await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce }, key, body));

  const recordSize = new Uint8Array(4);
  new DataView(recordSize.buffer).setUint32(0, 4096);
  return concat(salt, recordSize, new Uint8Array([asPublic.length]), asPublic, sealed);
}

/** Send one notification. Returns the push service's status. */
export async function sendPush(env: PushKeys, sub: PushSubscription, payload: unknown)
    : Promise<number> {
  const body = await encryptPayload(sub, JSON.stringify(payload));
  const response = await fetch(sub.endpoint, {
    method: "POST",
    headers: {
      authorization: await vapidHeader(env, sub.endpoint),
      "content-encoding": "aes128gcm",
      "content-type": "application/octet-stream",
      ttl: "86400",
      urgency: "normal",
    },
    body,
  });
  return response.status;
}
