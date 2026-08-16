#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
marketplace_name="codex-skills"
bundle_name="codex-skills"
install_optional=0

if [[ "${1:-}" == "--all" ]]; then
  install_optional=1
elif [[ $# -gt 0 ]]; then
  printf 'Usage: %s [--all]\n' "$0" >&2
  exit 2
fi

if ! command -v codex >/dev/null 2>&1; then
  printf 'Codex CLI is required. Install Codex, then run this script again.\n' >&2
  exit 1
fi

if codex plugin marketplace add "$repo_root"; then
  :
elif codex plugin marketplace list | grep -Fq "$repo_root"; then
  printf 'Marketplace already registered: %s\n' "$repo_root"
else
  printf 'Could not register the local Codex marketplace.\n' >&2
  exit 1
fi

if codex plugin add --help >/dev/null 2>&1; then
  plugin_command=(codex plugin add)
elif codex plugin install --help >/dev/null 2>&1; then
  plugin_command=(codex plugin install)
else
  printf 'This Codex version has no supported plugin installation command.\n' >&2
  exit 1
fi

"${plugin_command[@]}" "$bundle_name@$marketplace_name"

if [[ "$install_optional" -eq 1 ]]; then
  for plugin_name in \
    arabic-rtl-ui \
    backend-architect \
    codex-rtl \
    devops-automator \
    filament-optimization-specialist \
    filament-smart-arabic \
    humane-commit-flow \
    mem0 \
    mem0-memory \
    senior-developer; do
    "${plugin_command[@]}" "$plugin_name@$marketplace_name"
  done
fi

printf '\nInstalled %s from %s. Restart Codex to load the skills.\n' "$bundle_name" "$repo_root"
if [[ "$install_optional" -eq 0 ]]; then
  printf 'Run %s --all to install the separately packaged plugins too.\n' "$0"
fi
