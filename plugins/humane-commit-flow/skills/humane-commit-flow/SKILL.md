---
name: humane-commit-flow
description: Finish coding work as the largest useful set of small, logical, reviewable Git commits; write natural repository-specific commit messages; run applicable Codex guard skills and project checks; then push the current branch when publishing was requested or pre-authorized. Use after implementing, fixing, refactoring, documenting, or testing code, and whenever the user asks to commit, push, publish, ship, or prepare a PR. Also use as the final handoff from Claude Code to Codex.
---

# Humane Commit Flow

Turn completed work into an honest, readable Git history. Maximize useful separation, not commit count for its own sake.

## Workflow

1. Inspect `git status`, the repository instructions, recent commit style, the full diff, and untracked files. Never stage secrets, generated clutter, or unrelated user changes.
2. Run `scripts/inspect_worktree.sh` for a compact inventory when useful.
3. Build a commit map before staging. Split by independently understandable intent and dependency order:
   - schema/configuration before consumers;
   - production behavior before focused tests when each remains coherent;
   - refactors separate from behavior changes;
   - documentation separate when it stands alone;
   - unrelated fixes always separate.
4. Prefer more commits only while every commit remains buildable or meaningfully verifiable, reviewable, and safe to revert. Do not split inseparable code and its required contract merely to inflate the count. Never create whitespace-only fragments unless formatting is the actual task.
5. Stage explicit paths or hunks for one mapped intent. Review the staged diff and verify no unrelated edits entered it.
6. Run the narrowest relevant checks for that commit. Fix failures before committing. Do not bypass hooks with `--no-verify`.
7. Write the message from the staged diff, following the repository's established style. Use an imperative, specific subject describing the outcome. Keep it concise; add a body only for non-obvious motivation or tradeoffs. Never mention an AI, assistant, prompt, generated code, or invented ticket. Never impersonate a person or add fake authorship/co-author trailers.
8. Commit and repeat until all in-scope changes are committed. Leave unrelated user changes untouched.
9. Before publishing, run the guard gate in [guard-gate.md](references/guard-gate.md), then the repository's broader relevant test/lint/type/build checks. Re-run after any guard-driven edits and commit those fixes as their own logical commits or fold them into the affected unpushed commit only when rewriting history is safe and clearly appropriate.
10. Review the final range with `git log`, `git status`, and the aggregate diff against the starting point. Confirm every commit is coherent and no requested work is missing.
11. Push only when the user requested publishing/pushing or repository instructions explicitly pre-authorize it. Confirm the remote and branch, avoid force push, and use `git push -u <remote> <branch>` when upstream is absent. Stop on guard/test failure, ambiguous remote, protected branch risk, credentials failure, or rejected push; report the exact blocker.

## Non-negotiable rules

- Preserve authorship truth. “Human-like” means clear, contextual writing—not deception.
- Do not amend, rebase, reset, or rewrite existing commits unless the user explicitly authorizes history rewriting.
- Do not commit secrets, local environment files, dependency caches, build output, or unrelated changes.
- Do not push directly to a protected/default branch unless the user explicitly requested that exact destination.
- Never claim a guard ran unless it actually ran. If an applicable guard skill is unavailable, perform the closest manual review and disclose the substitution.
- If the task only requested local commits, stop before push.

## Completion report

Report the created commit hashes and subjects, checks and guards run, pushed remote/branch (if any), and any intentionally uncommitted files.
