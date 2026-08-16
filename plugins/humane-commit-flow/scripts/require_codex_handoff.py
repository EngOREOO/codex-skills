#!/usr/bin/env python3
"""Request one final Codex handoff when Claude stops with a dirty Git tree."""

import json
import subprocess
import sys


def read_event() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):

        return {}


def has_uncommitted_changes(cwd: str) -> bool:
    probe = subprocess.run(
        ["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=False
    )
    return probe.returncode == 0 and bool(probe.stdout.strip())


def block_message() -> dict:
    return {
        "decision": "block",
        "reason": (
            "The working tree still has changes. Invoke /humane-commit-flow:finish-and-push "
            "now so Codex can create logical commits, run applicable guard skills and checks, "
            "and push safely. Preserve unrelated user changes. If publishing was not authorized "
            "for this task, run the same flow through local commits and explicitly stop before push."
        ),
    }


def main() -> int:
    event = read_event()

    if event.get("stop_hook_active"):
        return 0

    cwd = event.get("cwd")
    if not cwd or not has_uncommitted_changes(cwd):
        return 0

    print(json.dumps(block_message()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
