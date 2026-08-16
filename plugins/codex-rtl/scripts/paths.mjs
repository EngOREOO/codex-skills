import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export function requestedAsar() {
  const argument = process.argv.find((item) => item.startsWith("--asar="));
  return argument ? path.resolve(argument.slice("--asar=".length)) : null;
}

export function candidates() {
  if (process.platform === "darwin") {
    return ["/Applications/ChatGPT.app/Contents/Resources/app.asar"];
  }
  if (process.platform === "win32") {
    return [
      path.join(process.env.LOCALAPPDATA || "", "Programs", "ChatGPT", "resources", "app.asar"),
      path.join(process.env.LOCALAPPDATA || "", "Programs", "Codex", "resources", "app.asar"),
      path.join(process.env.ProgramFiles || "", "ChatGPT", "resources", "app.asar"),
      path.join(process.env.ProgramFiles || "", "Codex", "resources", "app.asar"),
    ];
  }
  return [
    "/opt/ChatGPT/resources/app.asar",
    "/usr/lib/chatgpt/resources/app.asar",
    "/opt/Codex/resources/app.asar",
    "/usr/lib/codex/resources/app.asar",
  ];
}

export function resolveAsar() {
  const explicit = requestedAsar();
  if (explicit) return explicit;
  const found = candidates().find((candidate) => candidate && fs.existsSync(candidate));
  if (!found) {
    throw new Error("Could not find app.asar. Re-run with --asar=/absolute/path/to/app.asar");
  }
  return found;
}

export function tempDirectory(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}
