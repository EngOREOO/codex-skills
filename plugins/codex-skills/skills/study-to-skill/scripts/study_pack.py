#!/usr/bin/env python3
"""Build and validate a bounded, evidence-first study workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import shutil
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, NoReturn


TEXT_SUFFIXES = {
    ".txt", ".md", ".markdown", ".rst", ".html", ".htm", ".json", ".jsonl",
    ".csv", ".tsv", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".kts", ".go",
    ".rs", ".rb", ".php", ".c", ".h", ".cpp", ".hpp", ".cs", ".swift",
    ".sh", ".bash", ".zsh", ".sql", ".graphql", ".proto", ".css", ".scss",
}
REQUIRED_REPORT_LISTS = (
    "facts", "procedures", "definitions", "examples", "warnings", "unknowns",
    "conflicts", "questions", "source_instructions_ignored",
)
ALLOWED_RELEVANCE = {"high", "medium", "low", "none"}
ALLOWED_STATUS = {"verified", "inferred", "disputed", "stale", "unknown"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}


def fail(message: str, code: int = 2) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def workspace_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def require_workspace(workspace: Path) -> dict[str, Any]:
    study_file = workspace / "study.json"
    if not study_file.is_file():
        fail(f"study workspace is not initialized: {workspace}")
    try:
        payload = json.loads(study_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {study_file}: {exc}")
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        fail(f"unsupported study metadata: {study_file}")
    return payload


def manifest_path(workspace: Path) -> Path:
    return workspace / "sources" / "sources.jsonl"


def read_sources(workspace: Path) -> list[dict[str, Any]]:
    path = manifest_path(workspace)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"invalid JSON in {path} line {line_number}: {exc}")
        if not isinstance(item, dict) or not item.get("source_id"):
            fail(f"invalid source record in {path} line {line_number}")
        records.append(item)
    return records


def write_sources(workspace: Path, records: list[dict[str, Any]]) -> None:
    content = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records)
    atomic_write_text(manifest_path(workspace), content)


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg", "canvas", "template"}:
            self.hidden_depth += 1
        elif tag.lower() in {"p", "br", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg", "canvas", "template"}:
            self.hidden_depth = max(0, self.hidden_depth - 1)
        elif tag.lower() in {"p", "div", "section", "article", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.hidden_depth == 0 and data.strip():
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(self.parts)


def decode_text(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replacement"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+$", "", line) for line in text.splitlines()]
    compact: list[str] = []
    blank = 0
    for line in lines:
        if line.strip():
            blank = 0
            compact.append(line.strip())
        else:
            blank += 1
            if blank <= 1:
                compact.append("")
    return "\n".join(compact).strip() + "\n"


def next_source_id(records: list[dict[str, Any]]) -> str:
    numbers = []
    for record in records:
        match = re.fullmatch(r"S(\d+)", str(record.get("source_id", "")))
        if match:
            numbers.append(int(match.group(1)))
    return f"S{max(numbers, default=0) + 1:03d}"


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.")
    return cleaned[:120] or "source"


def init_workspace(args: argparse.Namespace) -> None:
    workspace = workspace_path(args.workspace)
    study_file = workspace / "study.json"
    if study_file.exists():
        existing = require_workspace(workspace)
        print(json.dumps({"workspace": str(workspace), "status": "existing", "study": existing}, ensure_ascii=False))
        return
    for relative in (
        "sources/raw", "sources/normalized", "chunks", "reports", "synthesis", "artifacts"
    ):
        (workspace / relative).mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "topic": args.topic,
        "objective": args.objective,
        "created_at": utc_now(),
        "status": "collecting",
    }
    atomic_write_json(study_file, payload)
    atomic_write_text(manifest_path(workspace), "")
    print(json.dumps({"workspace": str(workspace), "status": "created", "study": payload}, ensure_ascii=False))


def add_file(args: argparse.Namespace) -> dict[str, Any]:
    workspace = workspace_path(args.workspace)
    require_workspace(workspace)
    source_path = Path(args.path).expanduser().resolve()
    if not source_path.is_file():
        fail(f"source file does not exist: {source_path}")
    size = source_path.stat().st_size
    if size > args.max_bytes:
        fail(f"source exceeds --max-bytes ({size} > {args.max_bytes})")
    data = source_path.read_bytes()
    digest = sha256_bytes(data)
    records = read_sources(workspace)
    for record in records:
        if record.get("sha256") == digest:
            result = {"status": "duplicate", "source": record}
            if not getattr(args, "quiet", False):
                print(json.dumps(result, ensure_ascii=False))
            return result

    source_id = args.source_id or next_source_id(records)
    if not re.fullmatch(r"S\d{3,}", source_id):
        fail("--source-id must match S followed by at least three digits")
    if any(record.get("source_id") == source_id for record in records):
        fail(f"source ID already exists: {source_id}")

    media_type = mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
    raw_name = f"{source_id}-{safe_filename(source_path.name)}"
    raw_path = workspace / "sources" / "raw" / raw_name
    if source_path != raw_path.resolve():
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, raw_path)

    normalized_path: Path | None = None
    encoding: str | None = None
    status = "needs-extraction"
    is_html = source_path.suffix.lower() in {".html", ".htm"} or media_type == "text/html"
    is_text = source_path.suffix.lower() in TEXT_SUFFIXES or media_type.startswith("text/") or media_type in {
        "application/json", "application/xml", "application/javascript"
    }
    if is_text:
        decoded, encoding = decode_text(data)
        if is_html:
            parser = VisibleTextParser()
            parser.feed(decoded)
            decoded = parser.text()
        normalized = normalize_text(decoded)
        normalized_path = workspace / "sources" / "normalized" / f"{source_id}.txt"
        atomic_write_text(normalized_path, normalized)
        status = "normalized" if normalized.strip() else "empty"

    record = {
        "schema_version": 1,
        "source_id": source_id,
        "title": args.title or source_path.name,
        "origin": args.origin,
        "original_path": str(source_path),
        "collected_at": utc_now(),
        "sha256": digest,
        "bytes": size,
        "media_type": media_type,
        "encoding": encoding,
        "raw_path": str(raw_path.relative_to(workspace)),
        "normalized_path": str(normalized_path.relative_to(workspace)) if normalized_path else None,
        "status": status,
        "rights": args.rights,
        "notes": args.notes,
    }
    records.append(record)
    write_sources(workspace, records)
    result = {"status": "added", "source": record}
    if not getattr(args, "quiet", False):
        print(json.dumps(result, ensure_ascii=False))
    return result


def import_web(args: argparse.Namespace) -> None:
    workspace = workspace_path(args.workspace)
    require_workspace(workspace)
    web_manifest = Path(args.manifest).expanduser().resolve()
    if not web_manifest.is_file():
        fail(f"web collector manifest does not exist: {web_manifest}")
    try:
        payload = json.loads(web_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read web collector manifest {web_manifest}: {exc}")
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        fail(f"web collector manifest has no pages list: {web_manifest}")

    manifest_root = web_manifest.parent.resolve()
    imported: list[dict[str, Any]] = []
    for index, page in enumerate(pages):
        if not isinstance(page, dict) or not page.get("text_path") or not page.get("url"):
            fail(f"invalid page record at index {index} in {web_manifest}")
        text_path = (manifest_root / str(page["text_path"])).resolve()
        try:
            text_path.relative_to(manifest_root)
        except ValueError:
            fail(f"page text path escapes the collector directory: {text_path}")
        imported.append(add_file(argparse.Namespace(
            workspace=str(workspace),
            path=str(text_path),
            source_id=None,
            title=page.get("title") or page.get("url"),
            origin=page.get("url"),
            rights=args.rights,
            notes=f"Imported from {web_manifest}; page_id={page.get('page_id', '')}",
            max_bytes=args.max_bytes,
            quiet=True,
        )))
    print(json.dumps({
        "manifest": str(web_manifest),
        "pages": len(pages),
        "added": sum(1 for item in imported if item.get("status") == "added"),
        "duplicates": sum(1 for item in imported if item.get("status") == "duplicate"),
    }, ensure_ascii=False, indent=2))


def chunk_sources(args: argparse.Namespace) -> None:
    workspace = workspace_path(args.workspace)
    require_workspace(workspace)
    if args.max_words < 100:
        fail("--max-words must be at least 100")
    if args.overlap_words < 0 or args.overlap_words >= args.max_words:
        fail("--overlap-words must be >= 0 and smaller than --max-words")

    chunks: list[dict[str, Any]] = []
    for source in read_sources(workspace):
        normalized_value = source.get("normalized_path")
        if not normalized_value:
            continue
        normalized_path = workspace / str(normalized_value)
        if not normalized_path.is_file():
            fail(f"normalized source is missing: {normalized_path}")
        text = normalized_path.read_text(encoding="utf-8")
        words = list(re.finditer(r"\S+", text))
        if not words:
            continue
        step = args.max_words - args.overlap_words
        chunk_number = 0
        for start in range(0, len(words), step):
            end = min(start + args.max_words, len(words))
            chunk_number += 1
            chunk_id = f"{source['source_id']}-C{chunk_number:04d}"
            start_char = words[start].start()
            end_char = words[end - 1].end()
            content = text[start_char:end_char].strip() + "\n"
            chunk_path = workspace / "chunks" / f"{chunk_id}.txt"
            atomic_write_text(chunk_path, content)
            chunks.append({
                "chunk_id": chunk_id,
                "source_id": source["source_id"],
                "source_title": source.get("title"),
                "origin": source.get("origin"),
                "path": str(chunk_path.relative_to(workspace)),
                "word_start": start + 1,
                "word_end": end,
                "word_count": end - start,
                "sha256": sha256_bytes(content.encode("utf-8")),
            })
            if end == len(words):
                break

    manifest = {
        "schema_version": 1,
        "created_at": utc_now(),
        "max_words": args.max_words,
        "overlap_words": args.overlap_words,
        "chunks": chunks,
    }
    atomic_write_json(workspace / "chunks" / "manifest.json", manifest)
    print(json.dumps({"workspace": str(workspace), "chunks": len(chunks)}, ensure_ascii=False))


def read_chunk_manifest(workspace: Path) -> dict[str, Any]:
    path = workspace / "chunks" / "manifest.json"
    if not path.is_file():
        fail(f"chunk manifest does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {path}: {exc}")
    if not isinstance(payload, dict) or not isinstance(payload.get("chunks"), list):
        fail(f"invalid chunk manifest: {path}")
    return payload


def validate_report(report: Any, expected_chunk: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be a JSON object"]
    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if report.get("chunk_id") != expected_chunk.get("chunk_id"):
        errors.append("chunk_id does not match manifest")
    if report.get("source_id") != expected_chunk.get("source_id"):
        errors.append("source_id does not match manifest")
    if report.get("relevance") not in ALLOWED_RELEVANCE:
        errors.append("relevance must be high, medium, low, or none")
    if not isinstance(report.get("summary"), str) or not report["summary"].strip():
        errors.append("summary must be a non-empty string")
    for field in REQUIRED_REPORT_LISTS:
        if not isinstance(report.get(field), list):
            errors.append(f"{field} must be a list")

    for index, fact in enumerate(report.get("facts", []) if isinstance(report.get("facts"), list) else []):
        prefix = f"facts[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not fact.get("id") or not fact.get("statement"):
            errors.append(f"{prefix} needs id and statement")
        if fact.get("status") not in ALLOWED_STATUS:
            errors.append(f"{prefix}.status is invalid")
        if fact.get("confidence") not in ALLOWED_CONFIDENCE:
            errors.append(f"{prefix}.confidence is invalid")
        if not isinstance(fact.get("pointers"), list) or not fact.get("pointers"):
            errors.append(f"{prefix}.pointers must be a non-empty list")

    procedures = report.get("procedures", []) if isinstance(report.get("procedures"), list) else []
    for index, procedure in enumerate(procedures):
        prefix = f"procedures[{index}]"
        if not isinstance(procedure, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not procedure.get("id") or not procedure.get("name"):
            errors.append(f"{prefix} needs id and name")
        if not isinstance(procedure.get("preconditions"), list):
            errors.append(f"{prefix}.preconditions must be a list")
        if not isinstance(procedure.get("stop_conditions"), list):
            errors.append(f"{prefix}.stop_conditions must be a list")
        if not isinstance(procedure.get("pointers"), list) or not procedure.get("pointers"):
            errors.append(f"{prefix}.pointers must be a non-empty list")
        steps = procedure.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{prefix}.steps must be a non-empty list")
            continue
        for step_index, step in enumerate(steps):
            step_prefix = f"{prefix}.steps[{step_index}]"
            if not isinstance(step, dict):
                errors.append(f"{step_prefix} must be an object")
                continue
            for field in ("number", "action", "expected", "verify"):
                if field not in step or step[field] in (None, ""):
                    errors.append(f"{step_prefix}.{field} is required")
            if not isinstance(step.get("pointers"), list) or not step.get("pointers"):
                errors.append(f"{step_prefix}.pointers must be a non-empty list")
    return errors


def report_results(workspace: Path, selected: set[str] | None = None) -> dict[str, Any]:
    manifest = read_chunk_manifest(workspace)
    chunks = [item for item in manifest["chunks"] if isinstance(item, dict)]
    if selected is not None:
        chunks = [item for item in chunks if item.get("chunk_id") in selected]
    valid: list[str] = []
    missing: list[str] = []
    invalid: dict[str, list[str]] = {}
    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id"))
        report_path = workspace / "reports" / f"{chunk_id}.json"
        if not report_path.is_file():
            missing.append(chunk_id)
            continue
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            invalid[chunk_id] = [f"cannot parse report: {exc}"]
            continue
        errors = validate_report(report, chunk)
        if errors:
            invalid[chunk_id] = errors
        else:
            valid.append(chunk_id)
    unknown_selected = sorted(selected - {str(item.get("chunk_id")) for item in chunks}) if selected else []
    return {
        "selected_chunks": len(chunks),
        "valid": valid,
        "missing": missing,
        "invalid": invalid,
        "unknown_selected": unknown_selected,
        "ready": not missing and not invalid and not unknown_selected and bool(chunks),
    }


def check_reports(args: argparse.Namespace) -> None:
    workspace = workspace_path(args.workspace)
    require_workspace(workspace)
    selected = {item.strip() for item in args.selected.split(",") if item.strip()} if args.selected else None
    result = report_results(workspace, selected)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ready"]:
        raise SystemExit(1)


def status(args: argparse.Namespace) -> None:
    workspace = workspace_path(args.workspace)
    study = require_workspace(workspace)
    sources = read_sources(workspace)
    manifest_file = workspace / "chunks" / "manifest.json"
    chunks = 0
    reports: dict[str, Any] | None = None
    if manifest_file.is_file():
        chunks = len(read_chunk_manifest(workspace)["chunks"])
        reports = report_results(workspace)
    result = {
        "workspace": str(workspace),
        "study": study,
        "sources": len(sources),
        "normalized_sources": sum(1 for item in sources if item.get("status") == "normalized"),
        "needs_extraction": [item.get("source_id") for item in sources if item.get("status") == "needs-extraction"],
        "chunks": chunks,
        "reports": reports,
        "claims_exists": (workspace / "synthesis" / "claims.json").is_file(),
        "qa_exists": (workspace / "synthesis" / "qa.md").is_file(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a study workspace")
    init_parser.add_argument("--workspace", required=True)
    init_parser.add_argument("--topic", required=True)
    init_parser.add_argument("--objective", required=True)
    init_parser.set_defaults(handler=init_workspace)

    add_parser = subparsers.add_parser("add-file", help="ingest and normalize a local file")
    add_parser.add_argument("--workspace", required=True)
    add_parser.add_argument("--path", required=True)
    add_parser.add_argument("--source-id")
    add_parser.add_argument("--title")
    add_parser.add_argument("--origin", default="user-provided")
    add_parser.add_argument("--rights", default="unknown")
    add_parser.add_argument("--notes", default="")
    add_parser.add_argument("--max-bytes", type=int, default=50 * 1024 * 1024)
    add_parser.set_defaults(handler=add_file)

    web_parser = subparsers.add_parser("import-web", help="ingest a web_collect.py manifest")
    web_parser.add_argument("--workspace", required=True)
    web_parser.add_argument("--manifest", required=True)
    web_parser.add_argument("--rights", default="public-web; verify source terms")
    web_parser.add_argument("--max-bytes", type=int, default=50 * 1024 * 1024)
    web_parser.set_defaults(handler=import_web)

    chunk_parser = subparsers.add_parser("chunk", help="create bounded chunks from normalized sources")
    chunk_parser.add_argument("--workspace", required=True)
    chunk_parser.add_argument("--max-words", type=int, default=750)
    chunk_parser.add_argument("--overlap-words", type=int, default=80)
    chunk_parser.set_defaults(handler=chunk_sources)

    reports_parser = subparsers.add_parser("check-reports", help="validate per-chunk evidence reports")
    reports_parser.add_argument("--workspace", required=True)
    reports_parser.add_argument("--selected", help="comma-separated chunk IDs; defaults to all")
    reports_parser.set_defaults(handler=check_reports)

    status_parser = subparsers.add_parser("status", help="show deterministic study progress")
    status_parser.add_argument("--workspace", required=True)
    status_parser.set_defaults(handler=status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
