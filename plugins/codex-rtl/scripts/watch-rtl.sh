#!/bin/bash
set -u

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="$HOME/.codex/plugin-data/codex-rtl"
ASAR="/Applications/ChatGPT.app/Contents/Resources/app.asar"
NODE_BIN="${NODE_BIN:-/opt/homebrew/bin/node}"

mkdir -p "$STATE_DIR"

# Give Codex enough time to finish rendering the current task before a repair
# closes and reopens the desktop host.
sleep 8

while true; do
  if [ -f "$ASAR" ] && [ -x "$NODE_BIN" ]; then
    SIGNATURE="$(stat -f '%m:%z' "$ASAR" 2>/dev/null || true)"
    PREVIOUS="$(cat "$STATE_DIR/verified-signature" 2>/dev/null || true)"

    if [ -n "$SIGNATURE" ] && [ "$SIGNATURE" != "$PREVIOUS" ]; then
      if "$NODE_BIN" "$PLUGIN_DIR/scripts/check-rtl.mjs" >/dev/null 2>&1; then
        printf '%s' "$SIGNATURE" > "$STATE_DIR/verified-signature"
      elif mkdir "$STATE_DIR/repair.lock" 2>/dev/null; then
        nohup bash "$PLUGIN_DIR/scripts/repair-rtl.sh" >/tmp/codex-rtl-repair.log 2>&1 &
      fi
    fi
  fi

  sleep 15
done
