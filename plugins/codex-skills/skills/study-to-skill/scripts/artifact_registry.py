#!/usr/bin/env python3
"""Register and search evidence-backed reports, skills, and plugins."""

from __future__ import annotations

import argparse
import hashlib
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_registry_path() -> Path:
    configured_root = os.environ.get("CODEX_HOME")
    if configured_root:
        return Path(configured_root).expanduser() / "study-library" / "registry.json"
    return Path.home() / ".codex" / "study-library" / "registry.json"


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "artifacts": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read registry {path}: {exc}")
    if not isinstance(payload, dict) or not isinstance(payload.get("artifacts"), list):
        fail(f"registry must contain an artifacts list: {path}")
    if payload.get("schema_version") != 1:
        fail(f"unsupported registry schema: {path}")
    return payload


def parse_skill(path: Path) -> tuple[str, str]:
    skill_file = path / "SKILL.md"
    if not skill_file.is_file():
        fail(f"skill is missing SKILL.md: {path}")
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        fail(f"skill has no YAML frontmatter: {skill_file}")
    try:
        end = lines.index("---", 1)
    except ValueError:
        fail(f"skill frontmatter is not closed: {skill_file}")
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("\"'")
    if not fields.get("name") or not fields.get("description"):
        fail(f"skill frontmatter needs name and description: {skill_file}")
    return fields["name"], fields["description"]


def parse_plugin(path: Path) -> tuple[str, str]:
    manifest = path / ".codex-plugin" / "plugin.json"
    if not manifest.is_file():
        fail(f"plugin is missing .codex-plugin/plugin.json: {path}")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read plugin manifest {manifest}: {exc}")
    name = payload.get("name") if isinstance(payload, dict) else None
    if not isinstance(name, str) or not name.strip():
        fail(f"plugin manifest has no valid name: {manifest}")
    description = payload.get("description", "")
    return name.strip(), description if isinstance(description, str) else ""


def parse_report(path: Path) -> tuple[str, str]:
    if path.is_dir():
        study_file = path / "study.json"
        if study_file.is_file():
            try:
                payload = json.loads(study_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                fail(f"cannot read study metadata {study_file}: {exc}")
            topic = str(payload.get("topic") or path.name)
            objective = str(payload.get("objective") or "")
            return path.name, f"{topic}: {objective}".strip(": ")
        return path.name, "Study report directory"
    return path.stem, "Study report"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_manifest_metadata(value: str | None) -> tuple[str | None, str | None, int | None]:
    if not value:
        return None, None, None
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        fail(f"source manifest does not exist: {path}")
    count: int | None = None
    if path.suffix == ".jsonl":
        count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    else:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for key in ("sources", "pages", "chunks"):
                    if isinstance(payload.get(key), list):
                        count = len(payload[key])
                        break
        except json.JSONDecodeError:
            count = None
    return str(path), file_sha256(path), count


def register(args: argparse.Namespace) -> None:
    artifact_path = Path(args.artifact_path).expanduser().resolve()
    if not artifact_path.exists():
        fail(f"artifact path does not exist: {artifact_path}")
    if args.kind == "skill":
        if not artifact_path.is_dir():
            fail("a skill artifact path must be a directory")
        name, detected_summary = parse_skill(artifact_path)
    elif args.kind == "plugin":
        if not artifact_path.is_dir():
            fail("a plugin artifact path must be a directory")
        name, detected_summary = parse_plugin(artifact_path)
    else:
        name, detected_summary = parse_report(artifact_path)

    manifest_path, manifest_sha256, source_count = source_manifest_metadata(args.source_manifest)
    tags = sorted({tag.strip().lower() for tag in args.tags.split(",") if tag.strip()})
    record = {
        "kind": args.kind,
        "name": name,
        "path": str(artifact_path),
        "topic": args.topic,
        "summary": args.summary or detected_summary,
        "tags": tags,
        "limitations": args.limitations,
        "source_manifest": manifest_path,
        "source_manifest_sha256": manifest_sha256,
        "source_count": source_count,
        "updated_at": utc_now(),
    }
    registry_path = Path(args.registry).expanduser().resolve() if args.registry else default_registry_path()
    payload = load_registry(registry_path)
    key = (record["kind"], record["name"])
    artifacts = [
        item for item in payload["artifacts"]
        if not isinstance(item, dict) or (item.get("kind"), item.get("name")) != key
    ]
    artifacts.append(record)
    payload["artifacts"] = sorted(
        artifacts,
        key=lambda item: (str(item.get("kind", "")), str(item.get("name", ""))) if isinstance(item, dict) else ("", ""),
    )
    atomic_write_json(registry_path, payload)
    print(json.dumps({"registry": str(registry_path), "record": record}, ensure_ascii=False, indent=2))


def score(record: dict[str, Any], tokens: list[str]) -> int:
    haystack = " ".join(
        str(record.get(field, "")) for field in (
            "kind", "name", "topic", "summary", "tags", "limitations"
        )
    ).lower()
    return sum(3 if token in str(record.get("name", "")).lower() else 1 for token in tokens if token in haystack)


def find(args: argparse.Namespace) -> None:
    registry_path = Path(args.registry).expanduser().resolve() if args.registry else default_registry_path()
    payload = load_registry(registry_path)
    tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9_-]+", args.query)]
    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in payload["artifacts"]:
        if not isinstance(item, dict):
            continue
        item_score = score(item, tokens)
        if item_score > 0 and (not args.kind or item.get("kind") == args.kind):
            ranked.append((item_score, item))
    ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("kind", "")), str(pair[1].get("name", ""))))
    results = [item for _, item in ranked[: args.limit]]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    if not results:
        print("No learned artifacts matched the query.")
        return
    for item in results:
        print(f"{item.get('kind')}:{item.get('name')}\n  {item.get('summary')}\n  path: {item.get('path')}\n  updated: {item.get('updated_at')}")


def list_artifacts(args: argparse.Namespace) -> None:
    registry_path = Path(args.registry).expanduser().resolve() if args.registry else default_registry_path()
    payload = load_registry(registry_path)
    records = [
        item for item in payload["artifacts"]
        if isinstance(item, dict) and (not args.kind or item.get("kind") == args.kind)
    ]
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        for item in records:
            print(f"{item.get('kind')}\t{item.get('name')}\t{item.get('path')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", help="override the default registry path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_parser = subparsers.add_parser("register", help="add or update one learned artifact")
    register_parser.add_argument("--kind", required=True, choices=("report", "skill", "plugin"))
    register_parser.add_argument("--artifact-path", required=True)
    register_parser.add_argument("--topic", required=True)
    register_parser.add_argument("--tags", default="")
    register_parser.add_argument("--summary")
    register_parser.add_argument("--limitations", default="")
    register_parser.add_argument("--source-manifest")
    register_parser.set_defaults(handler=register)

    find_parser = subparsers.add_parser("find", help="search learned artifacts")
    find_parser.add_argument("--query", required=True)
    find_parser.add_argument("--kind", choices=("report", "skill", "plugin"))
    find_parser.add_argument("--limit", type=int, default=10)
    find_parser.add_argument("--json", action="store_true")
    find_parser.set_defaults(handler=find)

    list_parser = subparsers.add_parser("list", help="list learned artifacts")
    list_parser.add_argument("--kind", choices=("report", "skill", "plugin"))
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(handler=list_artifacts)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
