import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { extractFile } from "@electron/asar";
import { resolveAsar } from "./paths.mjs";

const pluginRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const sourcePatch = fs.readFileSync(path.join(pluginRoot, "rtl-arabic-patch.js"));

try {
  const asarPath = resolveAsar();
  const html = extractFile(asarPath, "webview/index.html").toString("utf8");
  const installedPatch = extractFile(asarPath, "webview/rtl-arabic-patch.js");
  const current = html.includes("rtl-arabic-patch.js") && installedPatch.equals(sourcePatch);
  if (current) {
    console.log(`Codex RTL is current: ${asarPath}`);
    process.exit(0);
  }
  console.error(`Codex RTL is missing or outdated: ${asarPath}`);
  process.exit(1);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
