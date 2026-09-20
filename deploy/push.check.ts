/**
 * Does a notification this Worker builds actually decrypt?
 *
 * Run by `tests/test_push_crypto.py` through Node, because the arithmetic in
 * `push.ts` is the kind that fails silently: a push service accepts the request
 * and the phone shows nothing. Here the subscription's own private key decrypts
 * what `encryptPayload` produced, and the VAPID signature is verified with the
 * public key the header carries.
 */
import { encryptPayload, vapidHeader, type PushSubscription } from "./push.ts";

const b64url = (bytes: Uint8Array | ArrayBuffer) => {
  const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  return Buffer.from(view).toString("base64url");
};
const fromB64url = (value: string) => new Uint8Array(Buffer.from(value, "base64url"));

async function main() {
  // A browser's subscription: an ECDH key pair plus 16 random bytes.
  const ua = await crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]) as CryptoKeyPair;
  const uaPublic = new Uint8Array(await crypto.subtle.exportKey("raw", ua.publicKey));
  const auth = crypto.getRandomValues(new Uint8Array(16));
  const sub: PushSubscription = {
    endpoint: "https://push.example.org/send/abc",
    keys: { p256dh: b64url(uaPublic), auth: b64url(auth) },
  };

  const message = JSON.stringify({ tag: "kordamine-2026-09-21", title: "Kordamine",
                                   body: "К повторению 12 карточек." });
  const body = await encryptPayload(sub, message);

  // Undo it the way a browser does (RFC 8291 §3.4).
  const salt = body.subarray(0, 16);
  const asPublic = body.subarray(21, 21 + body[20]);
  const ciphertext = body.subarray(21 + body[20]);
  const asKey = await crypto.subtle.importKey(
    "raw", asPublic, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const shared = new Uint8Array(await crypto.subtle.deriveBits(
    { name: "ECDH", public: asKey } as EcdhKeyDeriveParams, ua.privateKey, 256));

  const hkdf = async (s: Uint8Array, ikm: Uint8Array, info: Uint8Array, n: number) => {
    const key = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
    return new Uint8Array(await crypto.subtle.deriveBits(
      { name: "HKDF", hash: "SHA-256", salt: s, info }, key, n * 8));
  };
  const encoder = new TextEncoder();
  const ikm = await hkdf(auth, shared,
    Buffer.concat([encoder.encode("WebPush: info\0"), uaPublic, asPublic]), 32);
  const cek = await hkdf(salt, ikm, encoder.encode("Content-Encoding: aes128gcm\0"), 16);
  const nonce = await hkdf(salt, ikm, encoder.encode("Content-Encoding: nonce\0"), 12);
  const key = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["decrypt"]);
  const plain = new Uint8Array(await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: nonce }, key, ciphertext));
  // The last byte is the padding delimiter.
  const read = new TextDecoder().decode(plain.subarray(0, plain.length - 1));
  if (read !== message) throw new Error(`decrypted to ${read}`);

  /* VAPID: the header the push service checks, verified with its own key.

     The pair comes from `cli push-keys` when this is called with one, which is
     how `eesti/vapid.py` — thirty lines of curve arithmetic written here rather
     than pulled in as a compiled dependency — is checked against a real
     WebCrypto implementation. */
  const given = process.argv.slice(2);
  const keys = given.length === 2
    ? { VAPID_PUBLIC_KEY: given[0], VAPID_PRIVATE_KEY: given[1] }
    : await (async () => {
        const made = await crypto.subtle.generateKey(
          { name: "ECDSA", namedCurve: "P-256" }, true,
          ["sign", "verify"]) as CryptoKeyPair;
        return {
          VAPID_PUBLIC_KEY: b64url(
            new Uint8Array(await crypto.subtle.exportKey("raw", made.publicKey))),
          VAPID_PRIVATE_KEY: (await crypto.subtle.exportKey("jwk", made.privateKey)).d!,
        };
      })();
  const publicKey = await crypto.subtle.importKey(
    "raw", fromB64url(keys.VAPID_PUBLIC_KEY),
    { name: "ECDSA", namedCurve: "P-256" }, true, ["verify"]);
  const pair = { publicKey } as CryptoKeyPair;
  const header = await vapidHeader({
    ...keys, VAPID_SUBJECT: "mailto:learner@example.org",
  }, sub.endpoint);
  const token = header.match(/t=([^,]+)/)![1];
  const [head, claims, signature] = token.split(".");
  const ok = await crypto.subtle.verify(
    { name: "ECDSA", hash: "SHA-256" }, pair.publicKey, fromB64url(signature),
    encoder.encode(`${head}.${claims}`));
  if (!ok) throw new Error("VAPID signature does not verify");
  const payload = JSON.parse(Buffer.from(claims, "base64url").toString());
  if (payload.aud !== "https://push.example.org") throw new Error("wrong audience");
  if (payload.exp <= Math.floor(Date.now() / 1000)) throw new Error("already expired");

  console.log("ok");
}

main().catch((error) => { console.error(String(error)); process.exit(1); });
