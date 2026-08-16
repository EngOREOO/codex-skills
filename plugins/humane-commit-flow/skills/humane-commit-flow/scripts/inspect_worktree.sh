#!/usr/bin/env bash
set -euo pipefail

git rev-parse --show-toplevel
git status --short
git diff --stat
git diff --cached --stat
git log -8 --pretty=format:'%h %s'
