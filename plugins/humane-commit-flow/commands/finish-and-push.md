---
description: Hand finished work to Codex for logical commits, guards, and push
allowed-tools: Bash(codex:*), Bash(git status:*), Bash(git branch:*), Bash(git remote:*)
---

Confirm the implementation is finished and its focused checks pass. Then run Codex from the repository root with this request:

`Use $humane-commit-flow. Inspect the completed working tree, create the largest useful set of atomic logical commits with natural repository-specific messages, run every applicable guard skill and project check, fix and commit valid findings, then push the current branch to its configured remote. Do not touch unrelated changes, rewrite existing history, bypass hooks, or force-push.`

Return Codex's commit list, guard/check results, and pushed branch. If Codex or the skill is unavailable, stop and explain the missing prerequisite; do not push directly.
