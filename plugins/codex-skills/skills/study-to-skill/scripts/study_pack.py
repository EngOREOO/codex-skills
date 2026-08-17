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
from dataclasses import dataclass
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


@dataclass(frozen=True)
class SourceFile:
    path: Path
    body: bytes
    size: int
    sha256: str
    media_type: str


@dataclass(frozen=True)
class StoredSource:
    raw_path: str
    normalized_path: str | None
    encoding: str | None
    status: str


def fail(message: str, code: int = 2) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


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


def decode_text(raw_bytes: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            return raw_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace"), "utf-8-replacement"


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


def read_source_file(args: argparse.Namespace) -> SourceFile:
    source_path = Path(args.path).expanduser().resolve()
    if not source_path.is_file():
        fail(f"source file does not exist: {source_path}")
    size = source_path.stat().st_size
    if size > args.max_bytes:
        fail(f"source exceeds --max-bytes ({size} > {args.max_bytes})")
    source_body = source_path.read_bytes()
    return SourceFile(
        path=source_path,
        body=source_body,
        size=size,
        sha256=sha256_bytes(source_body),
        media_type=mimetypes.guess_type(source_path.name)[0] or "application/octet-stream",
    )


def duplicate_source(records: list[dict[str, Any]], digest: str) -> dict[str, Any] | None:
    return next((record for record in records if record.get("sha256") == digest), None)


def validate_source_id(source_id: str, records: list[dict[str, Any]]) -> None:
    if not re.fullmatch(r"S\d{3,}", source_id):
        fail("--source-id must match S followed by at least three digits")
    if any(record.get("source_id") == source_id for record in records):
        fail(f"source ID already exists: {source_id}")


def store_source(workspace: Path, source_id: str, source_file: SourceFile) -> StoredSource:
    raw_name = f"{source_id}-{safe_filename(source_file.path.name)}"
    raw_path = workspace / "sources" / "raw" / raw_name
    if source_file.path != raw_path.resolve():
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file.path, raw_path)

    is_html = source_file.path.suffix.lower() in {".html", ".htm"} or source_file.media_type == "text/html"
    is_text = source_file.path.suffix.lower() in TEXT_SUFFIXES or source_file.media_type.startswith("text/")
    is_text = is_text or source_file.media_type in {
        "application/json", "application/xml", "application/javascript"
    }
    if not is_text:
        return StoredSource(str(raw_path.relative_to(workspace)), None, None, "needs-extraction")
    decoded_text, encoding = decode_text(source_file.body)
    if is_html:
        html_parser = VisibleTextParser()
        html_parser.feed(decoded_text)
        decoded_text = html_parser.text()
    normalized_text = normalize_text(decoded_text)
    normalized_path = workspace / "sources" / "normalized" / f"{source_id}.txt"
    atomic_write_text(normalized_path, normalized_text)
    status = "normalized" if normalized_text.strip() else "empty"
    return StoredSource(
        str(raw_path.relative_to(workspace)),
        str(normalized_path.relative_to(workspace)),
        encoding,
        status,
    )


def build_source_record(
    args: argparse.Namespace, source_id: str, source_file: SourceFile,
    stored_source: StoredSource,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source_id": source_id,
        "title": args.title or source_file.path.name,
        "origin": args.origin,
        "original_path": str(source_file.path),
        "collected_at": utc_now(),
        "sha256": source_file.sha256,
        "bytes": source_file.size,
        "media_type": source_file.media_type,
        "encoding": stored_source.encoding,
        "raw_path": stored_source.raw_path,
        "normalized_path": stored_source.normalized_path,
        "status": stored_source.status,
        "rights": args.rights,
        "notes": args.notes,
    }


def emit_ingest_result(args: argparse.Namespace, status: str, source: dict[str, Any]) -> dict[str, Any]:
    ingest_result = {"status": status, "source": source}
    if not getattr(args, "quiet", False):
        print(json.dumps(ingest_result, ensure_ascii=False))
    return ingest_result


def add_file(args: argparse.Namespace) -> dict[str, Any]:
    workspace = workspace_path(args.workspace)
    require_workspace(workspace)
    source_file = read_source_file(args)
    source_records = read_sources(workspace)
    existing_source = duplicate_source(source_records, source_file.sha256)
    if existing_source:
        return emit_ingest_result(args, "duplicate", existing_source)
    source_id = args.source_id or next_source_id(source_records)
    validate_source_id(source_id, source_records)
    stored_source = store_source(workspace, source_id, source_file)
    source_record = build_source_record(args, source_id, source_file, stored_source)
    source_records.append(source_record)
    write_sources(workspace, source_records)
    return emit_ingest_result(args, "added", source_record)


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


def validate_chunk_options(args: argparse.Namespace) -> None:
    if args.max_words < 100:
        fail("--max-words must be at least 100")
    if args.overlap_words < 0 or args.overlap_words >= args.max_words:
        fail("--overlap-words must be >= 0 and smaller than --max-words")


def source_chunks(
    workspace: Path, source_record: dict[str, Any], args: argparse.Namespace
) -> list[dict[str, Any]]:
    normalized_location = source_record.get("normalized_path")
    if not normalized_location:
        return []
    normalized_path = workspace / str(normalized_location)
    if not normalized_path.is_file():
        fail(f"normalized source is missing: {normalized_path}")
    source_text = normalized_path.read_text(encoding="utf-8")
    word_matches = list(re.finditer(r"\S+", source_text))
    if not word_matches:
        return []
    chunk_records: list[dict[str, Any]] = []
    chunk_step = args.max_words - args.overlap_words
    for chunk_number, word_start in enumerate(range(0, len(word_matches), chunk_step), start=1):
        word_end = min(word_start + args.max_words, len(word_matches))
        chunk_id = f"{source_record['source_id']}-C{chunk_number:04d}"
        start_character = word_matches[word_start].start()
        end_character = word_matches[word_end - 1].end()
        chunk_text = source_text[start_character:end_character].strip() + "\n"
        chunk_path = workspace / "chunks" / f"{chunk_id}.txt"
        atomic_write_text(chunk_path, chunk_text)
        chunk_records.append({
            "chunk_id": chunk_id,
            "source_id": source_record["source_id"],
            "source_title": source_record.get("title"),
            "origin": source_record.get("origin"),
            "path": str(chunk_path.relative_to(workspace)),
            "word_start": word_start + 1,
            "word_end": word_end,
            "word_count": word_end - word_start,
            "sha256": sha256_bytes(chunk_text.encode("utf-8")),
        })
        if word_end == len(word_matches):
            break
    return chunk_records


def chunk_sources(args: argparse.Namespace) -> None:
    workspace = workspace_path(args.workspace)
    require_workspace(workspace)
    validate_chunk_options(args)
    chunk_records = [
        chunk_record
        for source_record in read_sources(workspace)
        for chunk_record in source_chunks(workspace, source_record, args)
    ]

    manifest = {
        "schema_version": 1,
        "created_at": utc_now(),
        "max_words": args.max_words,
        "overlap_words": args.overlap_words,
        "chunks": chunk_records,
    }
    atomic_write_json(workspace / "chunks" / "manifest.json", manifest)
    print(json.dumps({"workspace": str(workspace), "chunks": len(chunk_records)}, ensure_ascii=False))


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


def validate_report_header(
    report: dict[str, Any], expected_chunk: dict[str, Any], errors: list[str]
) -> None:
    expected_fields = (
        ("schema_version", 1, "schema_version must be 1"),
        ("chunk_id", expected_chunk.get("chunk_id"), "chunk_id does not match manifest"),
        ("source_id", expected_chunk.get("source_id"), "source_id does not match manifest"),
    )
    for field, expected_value, message in expected_fields:
        if report.get(field) != expected_value:
            errors.append(message)
    if report.get("relevance") not in ALLOWED_RELEVANCE:
        errors.append("relevance must be high, medium, low, or none")
    if not isinstance(report.get("summary"), str) or not report["summary"].strip():
        errors.append("summary must be a non-empty string")
    for field in REQUIRED_REPORT_LISTS:
        if not isinstance(report.get(field), list):
            errors.append(f"{field} must be a list")


def validate_fact(fact: Any, fact_index: int) -> list[str]:
    prefix = f"facts[{fact_index}]"
    if not isinstance(fact, dict):
        return [f"{prefix} must be an object"]
    errors: list[str] = []
    if not fact.get("id") or not fact.get("statement"):
        errors.append(f"{prefix} needs id and statement")
    if fact.get("status") not in ALLOWED_STATUS:
        errors.append(f"{prefix}.status is invalid")
    if fact.get("confidence") not in ALLOWED_CONFIDENCE:
        errors.append(f"{prefix}.confidence is invalid")
    if not isinstance(fact.get("pointers"), list) or not fact.get("pointers"):
        errors.append(f"{prefix}.pointers must be a non-empty list")
    return errors


def validate_step(step: Any, step_prefix: str) -> list[str]:
    if not isinstance(step, dict):
        return [f"{step_prefix} must be an object"]
    errors: list[str] = []
    for field in ("number", "action", "expected", "verify"):
        if field not in step or step[field] in (None, ""):
            errors.append(f"{step_prefix}.{field} is required")
    if not isinstance(step.get("pointers"), list) or not step.get("pointers"):
        errors.append(f"{step_prefix}.pointers must be a non-empty list")
    return errors


def validate_procedure(procedure: Any, procedure_index: int) -> list[str]:
    prefix = f"procedures[{procedure_index}]"
    if not isinstance(procedure, dict):
        return [f"{prefix} must be an object"]
    errors: list[str] = []
    if not procedure.get("id") or not procedure.get("name"):
        errors.append(f"{prefix} needs id and name")
    for field in ("preconditions", "stop_conditions"):
        if not isinstance(procedure.get(field), list):
            errors.append(f"{prefix}.{field} must be a list")
    if not isinstance(procedure.get("pointers"), list) or not procedure.get("pointers"):
        errors.append(f"{prefix}.pointers must be a non-empty list")
    steps = procedure.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(f"{prefix}.steps must be a non-empty list")
        return errors
    for step_index, step in enumerate(steps):
        errors.extend(validate_step(step, f"{prefix}.steps[{step_index}]"))
    return errors


def validate_report(report: Any, expected_chunk: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be a JSON object"]
    validate_report_header(report, expected_chunk, errors)
    if isinstance(report.get("facts"), list):
        for fact_index, fact in enumerate(report["facts"]):
            errors.extend(validate_fact(fact, fact_index))
    if isinstance(report.get("procedures"), list):
        for procedure_index, procedure in enumerate(report["procedures"]):
            errors.extend(validate_procedure(procedure, procedure_index))
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
