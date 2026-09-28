// Node runs the real Worker modules; only the platform base class is replaced.
import { existsSync } from "node:fs";
import { registerHooks } from "node:module";

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === "cloudflare:workers") {
      const source = "export class DurableObject { constructor(ctx, env) { this.ctx = ctx; this.env = env; } }";
      return nextResolve(`data:text/javascript,${encodeURIComponent(source)}`, context);
    }
    if (specifier.startsWith(".") && context.parentURL?.endsWith(".ts")) {
      const file = new URL(`${specifier}.ts`, context.parentURL);
      if (existsSync(file)) {
        return { ...nextResolve(file.href, context), format: "module-typescript" };
      }
    }
    const resolved = nextResolve(specifier, context);
    return resolved.url.endsWith(".ts") ? { ...resolved, format: "module-typescript" } : resolved;
  },
});
