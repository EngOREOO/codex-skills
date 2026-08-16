import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { resolveAsar } from "./paths.mjs";
import { signMacApp } from "./sign-macos.mjs";

const asarPath = resolveAsar();
const stateDirectory = process.env.CODEX_RTL_STATE_DIR
  || path.join(os.homedir(), ".codex", "plugin-data", "codex-rtl");
const personalBackup = path.join(stateDirectory, "app.asar.codex-rtl-backup");
const legacyBackup = `${asarPath}.codex-rtl-backup`;
const backupPath = fs.existsSync(personalBackup) ? personalBackup : legacyBackup;

if (!fs.existsSync(backupPath)) throw new Error(`Backup not found: ${backupPath}`);
fs.copyFileSync(backupPath, asarPath);
signMacApp(asarPath);
console.log(`Original archive restored: ${asarPath}`);
console.log("Quit ChatGPT/Codex completely, then open it again.");
