/* Generate one account-table UPDATE for a lost password, without echoing the
   replacement while it is typed. Run locally with Node 24 and paste the SQL
   into Data Studio for the singleton object. */

import { createInterface } from "node:readline/promises";
import { stdin, stdout } from "node:process";
import { hashPassword, normaliseEmail, PASSWORD_MIN } from "./accounts.ts";

function readHidden(prompt: string): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!stdin.isTTY || !stdin.setRawMode) {
      reject(new Error("Run this helper in a terminal."));
      return;
    }
    let value = "";
    stdout.write(prompt);
    stdin.setEncoding("utf8");
    stdin.setRawMode(true);
    stdin.resume();
    const finish = (error?: Error) => {
      stdin.off("data", onData);
      stdin.setRawMode(false);
      stdin.pause();
      stdout.write("\n");
      if (error) reject(error);
      else resolve(value);
    };
    const onData = (input: string) => {
      for (const char of input) {
        if (char === "\u0003") return finish(new Error("Cancelled."));
        if (char === "\r" || char === "\n") return finish();
        if (char === "\u007f" || char === "\b") value = value.slice(0, -1);
        else value += char;
      }
    };
    stdin.on("data", onData);
  });
}

async function main() {
  const terminal = createInterface({ input: stdin, output: stdout });
  const rawEmail = await terminal.question("Account email: ");
  terminal.close();
  const email = normaliseEmail(rawEmail);
  if (!email) throw new Error("Enter a valid account email.");

  const password = await readHidden("New password (at least 10 characters): ");
  if (password.length < PASSWORD_MIN) {
    throw new Error(`Password must contain at least ${PASSWORD_MIN} characters.`);
  }
  const salt = [...crypto.getRandomValues(new Uint8Array(16))]
    .map((byte) => byte.toString(16).padStart(2, "0")).join("");
  const hash = await hashPassword(password, salt);
  const escapedEmail = email.replaceAll("'", "''");
  stdout.write("Paste this SQL into Data Studio for the singleton object:\n");
  stdout.write(`UPDATE accounts SET salt='${salt}', hash='${hash}', failures=0, locked_until=0 WHERE email='${escapedEmail}';\n`);
}

main().catch((error) => {
  stdout.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
