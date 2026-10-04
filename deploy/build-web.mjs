/* Build the same module graph the source checkout runs, without discovery waves.
   Only derived public assets; no environment or learner data enters the output. */
import {build} from "esbuild";
import {gzipSync} from "node:zlib";
import {readFile, writeFile} from "node:fs/promises";

await build({entryPoints: {main: "eesti/web/js/main.js", app: "eesti/web/app.css"},
  outdir: "eesti/web/.build", bundle: true, minify: true, format: "esm",
  target: ["es2022"], external: ["/fonts/*"], legalComments: "eof"});
for (const name of ["main.js", "app.css"]) {
  const bytes = await readFile(`eesti/web/.build/${name}`);
  await writeFile(`eesti/web/.build/${name}.gz`, gzipSync(bytes, {level: 9}));
  console.log(`${name}: ${bytes.length} bytes; gzip ${gzipSync(bytes).length} bytes`);
}
