#!/bin/bash
set -eu

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="$HOME/.codex/plugin-data/codex-rtl"
APP="/Applications/ChatGPT.app"
ASAR="/Applications/ChatGPT.app/Contents/Resources/app.asar"
NODE_BIN="${NODE_BIN:-/opt/homebrew/bin/node}"
WAS_RUNNING=0

mkdir -p "$STATE_DIR"
trap 'rmdir "$STATE_DIR/repair.lock" 2>/dev/null || true' EXIT

if "$NODE_BIN" "$PLUGIN_DIR/scripts/check-rtl.mjs" >/dev/null 2>&1; then
  stat -f '%m:%z' "$ASAR" > "$STATE_DIR/verified-signature" 2>/dev/null || true
  exit 0
fi

if pgrep -x ChatGPT >/dev/null 2>&1; then
  WAS_RUNNING=1
  osascript -e 'tell application "ChatGPT" to quit' >/dev/null 2>&1 || true
  for _ in {1..40}; do
    pgrep -x ChatGPT >/dev/null 2>&1 || break
    sleep 0.5
  done
fi

if pgrep -x ChatGPT >/dev/null 2>&1; then
  killall ChatGPT >/dev/null 2>&1 || true
  sleep 1
fi

chmod -R u+w "$APP"
cd "$PLUGIN_DIR" || exit 1
"$NODE_BIN" scripts/install.mjs "--asar=$ASAR"
"$NODE_BIN" "$PLUGIN_DIR/scripts/check-rtl.mjs" >/dev/null
stat -f '%m:%z' "$ASAR" > "$STATE_DIR/verified-signature" 2>/dev/null || true

if [ "$WAS_RUNNING" -eq 1 ]; then
  open -a ChatGPT
fi
