import { cp, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";

const require = createRequire(import.meta.url);
const packageRoot = dirname(require.resolve("monaco-editor/package.json"));
const publicRoot = new URL("../public/monaco/", import.meta.url);
await mkdir(publicRoot, { recursive: true });
await cp(resolve(packageRoot, "min/vs"), new URL("vs", publicRoot), { recursive: true });

for (const notice of ["LICENSE", "ThirdPartyNotices.txt"]) {
  await cp(resolve(packageRoot, notice), new URL(notice, publicRoot));
}
