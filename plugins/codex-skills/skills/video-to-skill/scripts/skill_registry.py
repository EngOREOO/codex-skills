#!/usr/bin/env python3
"""Register and search skills learned from videos.

The registry is a small local index. It stores metadata and paths, not
transcripts, credentials, or source dumps.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn


def fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_registry_path() -> Path:
    codex_root = os.environ.get("CODEX_HOME")
    if codex_root:
        return Path(codex_root).expanduser() / "video-skill-library" / "registry.json"
    return Path.home() / ".codex" / "video-skill-library" / "registry.json"


def read_frontmatter(skill_path: Path) -> dict[str, str]:
    skill_file = skill_path / "SKILL.md"
    try:
        lines = skill_file.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"cannot read {skill_file}: {exc}")
    if not lines or lines[0].strip() != "---":
        fail(f"{skill_file} has no YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError:
        fail(f"{skill_file} has an unclosed YAML frontmatter block")
    result: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            value = match.group(2).strip().strip("\"'")
            result[match.group(1)] = value
    if not result.get("name") or not result.get("description"):
        fail(f"{skill_file} needs name and description frontmatter")
    return result


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "skills": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read registry {path}: {exc}")
    if not isinstance(payload, dict) or not isinstance(payload.get("skills", []), list):
        fail(f"registry must contain an object with a skills list: {path}")
    payload.setdefault("schema_version", 1)
    return payload


def save_registry(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def register(args: argparse.Namespace) -> None:
    skill_path = Path(args.skill_path).expanduser().resolve()
    if not skill_path.is_dir():
        fail(f"skill directory does not exist: {skill_path}")
    frontmatter = read_frontmatter(skill_path)
    tags = sorted({tag.strip().lower() for tag in args.tags.split(",") if tag.strip()})
    record = {
        "name": frontmatter["name"],
        "path": str(skill_path),
        "source_url": args.source_url,
        "topic": args.topic,
        "summary": args.summary or frontmatter["description"],
        "tags": tags,
        "updated_at": now(),
    }
    registry_path = Path(args.registry).expanduser() if args.registry else default_registry_path()
    payload = load_registry(registry_path)
    skills = [item for item in payload["skills"] if item.get("name") != record["name"]]
    skills.append(record)
    payload["skills"] = sorted(skills, key=lambda item: item.get("name", ""))
    save_registry(registry_path, payload)
    print(json.dumps({"registry": str(registry_path), "record": record}, ensure_ascii=False))


def matching_score(record: dict[str, Any], tokens: list[str]) -> int:
    haystack = " ".join(
        str(record.get(field, ""))
        for field in ("name", "topic", "summary", "source_url", "tags")
    ).lower()
    return sum(1 for token in tokens if token in haystack)


def find(args: argparse.Namespace) -> None:
    registry_path = Path(args.registry).expanduser() if args.registry else default_registry_path()
    payload = load_registry(registry_path)
    tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9_-]+", args.query)]
    records = [item for item in payload["skills"] if isinstance(item, dict)]
    ranked = [
        (matching_score(record, tokens), record)
        for record in records
        if matching_score(record, tokens) > 0
    ]
    ranked.sort(key=lambda item: (-item[0], item[1].get("name", "")))
    results = [record for _, record in ranked[: args.limit]]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    if not results:
        print("No learned skills matched the query.")
        return
    for record in results:
        tags = ", ".join(record.get("tags", []))
        print(f"{record.get('name')}\n  {record.get('summary')}\n  path: {record.get('path')}\n  tags: {tags}")


def list_skills(args: argparse.Namespace) -> None:
    registry_path = Path(args.registry).expanduser() if args.registry else default_registry_path()
    payload = load_registry(registry_path)
    records = payload["skills"]
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        for record in records:
            print(f"{record.get('name')}\t{record.get('path')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", help="override the default local registry path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_parser = subparsers.add_parser("register", help="add or update one learned skill")
    register_parser.add_argument("--skill-path", required=True)
    register_parser.add_argument("--source-url", default=None)
    register_parser.add_argument("--topic", default=None)
    register_parser.add_argument("--summary", default=None)
    register_parser.add_argument("--tags", default="")
    register_parser.set_defaults(handler=register)

    find_parser = subparsers.add_parser("find", help="search registered skills")
    find_parser.add_argument("--query", required=True)
    find_parser.add_argument("--limit", type=int, default=10)
    find_parser.add_argument("--json", action="store_true")
    find_parser.set_defaults(handler=find)

    list_parser = subparsers.add_parser("list", help="list registered skills")
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(handler=list_skills)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
