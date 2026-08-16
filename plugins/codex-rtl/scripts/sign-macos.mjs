import { execFileSync } from "node:child_process";
import path from "node:path";

export function signMacApp(asarPath) {
  if (process.platform !== "darwin") return;
  const marker = `${path.sep}Contents${path.sep}Resources${path.sep}app.asar`;
  if (!asarPath.endsWith(marker)) return;
  const appPath = asarPath.slice(0, -marker.length);
  execFileSync("codesign", ["--force", "--deep", "--sign", "-", appPath], {
    stdio: "inherit",
  });
}
