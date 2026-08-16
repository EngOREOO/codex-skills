import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createPackage, extractAll } from "@electron/asar";
import { resolveAsar, tempDirectory } from "./paths.mjs";
import { signMacApp } from "./sign-macos.mjs";

const asarPath = resolveAsar();
const stateDirectory = process.env.CODEX_RTL_STATE_DIR
  || path.join(os.homedir(), ".codex", "plugin-data", "codex-rtl");
const backupPath = path.join(stateDirectory, "app.asar.codex-rtl-backup");
const workDirectory = tempDirectory("codex-rtl-");
const unpackedDirectory = path.join(workDirectory, "unpacked");
const rebuiltAsar = path.join(workDirectory, "app.asar");
const patchSource = path.resolve("rtl-arabic-patch.js");

if (!fs.existsSync(asarPath)) throw new Error(`app.asar not found: ${asarPath}`);
if (!fs.existsSync(patchSource)) throw new Error(`Patch file not found: ${patchSource}`);
fs.mkdirSync(stateDirectory, { recursive: true });

extractAll(asarPath, unpackedDirectory);
const indexPath = path.join(unpackedDirectory, "webview", "index.html");
const patchTarget = path.join(unpackedDirectory, "webview", "rtl-arabic-patch.js");
let html = fs.readFileSync(indexPath, "utf8");

// Refresh the backup when an application update replaced the patch. Keeping a
// pre-update backup would make restore roll the entire desktop app backwards.
if (!html.includes("rtl-arabic-patch.js")) {
  fs.copyFileSync(asarPath, backupPath);
}

if (!html.includes("rtl-arabic-patch.js")) {
  const mainScript = /(<script\s+type="module"[^>]+src="\.\/assets\/index-[^"]+\.js"[^>]*><\/script>)/;
  if (!mainScript.test(html)) throw new Error("Could not locate the Codex entry script in webview/index.html");
  html = html.replace(mainScript, '<script type="module" src="./rtl-arabic-patch.js"></script>\n    $1');
  fs.writeFileSync(indexPath, html);
}

fs.copyFileSync(patchSource, patchTarget);
await createPackage(unpackedDirectory, rebuiltAsar);
fs.copyFileSync(rebuiltAsar, asarPath);
signMacApp(asarPath);

console.log(`RTL patch installed: ${asarPath}`);
console.log(`Backup: ${backupPath}`);
console.log("Quit ChatGPT/Codex completely, then open it again.");
