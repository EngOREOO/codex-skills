#!/usr/bin/env python3
"""Collect captions and turn them into bounded, timestamped evidence chunks.

The collector is the only network-facing operation in this skill. The chunker is
deliberately offline and uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, NoReturn


TIME_RE = re.compile(
    r"^(?P<start>\d{1,2}:\d{2}(?::\d{2})?[\.,]\d{1,3})\s+-->\s+"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?[\.,]\d{1,3})"
)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Cue:
    start: float | None
    end: float | None
    text: str


def fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def parse_time(raw: str) -> float:
    value = raw.replace(",", ".")
    pieces = value.split(":")
    if len(pieces) == 2:
        hours = 0.0
        minutes, seconds = pieces
    elif len(pieces) == 3:
        hours, minutes, seconds = pieces
    else:
        raise ValueError(f"invalid timestamp: {raw}")
    return float(hours) * 3600 + float(minutes) * 60 + float(seconds)


def format_time(seconds: float | None) -> str:
    if seconds is None:
        return "untimed"
    millis = max(0, int(round(seconds * 1000)))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def clean_text(lines: Iterable[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip())
    text = TAG_RE.sub("", text)
    return SPACE_RE.sub(" ", html.unescape(text)).strip()


def parse_captions(text: str) -> list[Cue]:
    """Parse WebVTT or SRT captions without requiring a third-party package."""

    cues: list[Cue] = []
    seen: set[tuple[float, float, str]] = set()
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = [line.strip("\ufeff") for line in block.split("\n")]
        timing_index = next(
            (index for index, line in enumerate(lines) if "-->" in line), None
        )
        if timing_index is None:
            continue
        match = TIME_RE.match(lines[timing_index])
        if match is None:
            continue
        try:
            start = parse_time(match.group("start"))
            end = parse_time(match.group("end"))
        except ValueError:
            continue
        cue_text = clean_text(lines[timing_index + 1 :])
        if not cue_text:
            continue
        key = (start, end, cue_text)
        if key not in seen:
            cues.append(Cue(start, end, cue_text))
            seen.add(key)
    return cues


def load_cues(input_path: Path) -> list[Cue]:
    try:
        text = input_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        fail(f"cannot read {input_path}: {exc}")
    if input_path.suffix.lower() in {".vtt", ".srt", ".ttml"}:
        cues = parse_captions(text)
        if not cues:
            fail(f"no timed captions found in {input_path}")
        return cues
    plain = clean_text(text.splitlines())
    if not plain:
        fail(f"input is empty: {input_path}")
    return [Cue(None, None, plain)]


def word_count(text: str) -> int:
    return len(text.split())


def expand_long_cues(cues: list[Cue], max_words: int) -> list[Cue]:
    expanded: list[Cue] = []
    for cue in cues:
        words = cue.text.split()
        if len(words) <= max_words:
            expanded.append(cue)
            continue
        for offset in range(0, len(words), max_words):
            expanded.append(Cue(cue.start, cue.end, " ".join(words[offset : offset + max_words])))
    return expanded


def build_chunks(
    cues: list[Cue], max_words: int, overlap_words: int
) -> list[dict[str, object]]:
    if max_words < 50:
        fail("--max-words must be at least 50")
    if overlap_words < 0 or overlap_words >= max_words:
        fail("--overlap-words must be non-negative and smaller than --max-words")

    if all(cue.start is None for cue in cues):
        words = cues[0].text.split()
        chunks: list[dict[str, object]] = []
        stride = max_words - overlap_words
        for offset in range(0, len(words), stride):
            part = words[offset : offset + max_words]
            if not part:
                break
            chunks.append(
                {
                    "start": None,
                    "end": None,
                    "text": " ".join(part),
                    "word_count": len(part),
                }
            )
            if offset + max_words >= len(words):
                break
        return chunks

    cues = expand_long_cues(cues, max_words)
    chunks = []
    start_index = 0
    while start_index < len(cues):
        end_index = start_index
        words = 0
        while end_index < len(cues):
            next_words = word_count(cues[end_index].text)
            if end_index > start_index and words + next_words > max_words:
                break
            words += next_words
            end_index += 1

        selected = cues[start_index:end_index]
        chunks.append(
            {
                "start": selected[0].start,
                "end": selected[-1].end,
                "text": " ".join(cue.text for cue in selected),
                "word_count": words,
            }
        )
        if end_index >= len(cues):
            break

        next_start = end_index
        overlap = 0
        while next_start > start_index:
            candidate = word_count(cues[next_start - 1].text)
            if overlap + candidate > overlap_words:
                break
            next_start -= 1
            overlap += candidate
        start_index = next_start if next_start > start_index else end_index
    return chunks


def write_chunk_output(
    chunks: list[dict[str, object]],
    output_dir: Path,
    input_path: Path,
    source_url: str | None,
    max_words: int,
    overlap_words: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    manifest_chunks: list[dict[str, object]] = []

    for index, chunk in enumerate(chunks, start=1):
        chunk_id = f"{index:04d}"
        start = format_time(chunk["start"])  # type: ignore[arg-type]
        end = format_time(chunk["end"])  # type: ignore[arg-type]
        path = chunks_dir / f"{chunk_id}.md"
        source_line = source_url or input_path.name
        content = (
            f"---\nchunk_id: {chunk_id}\nsource: {source_line}\n"
            f"start: {start}\nend: {end}\n---\n\n"
            f"# Evidence chunk {chunk_id}\n\n"
            f"Source: `{source_line}`\n"
            f"Time: `{start}` → `{end}`\n\n"
            f"## Transcript\n\n{chunk['text']}\n"
        )
        path.write_text(content, encoding="utf-8")
        manifest_chunks.append(
            {
                "chunk_id": chunk_id,
                "path": str(path.relative_to(output_dir)),
                "start": start,
                "end": end,
                "word_count": chunk["word_count"],
            }
        )

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": input_path.name,
        "source_url": source_url,
        "max_words": max_words,
        "overlap_words": overlap_words,
        "chunk_count": len(manifest_chunks),
        "chunks": manifest_chunks,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"manifest": str(output_dir / "manifest.json"), "chunks": len(chunks)}))


def choose_caption(files: list[Path], languages: str) -> Path | None:
    if not files:
        return None
    preferences = [part.split(".")[0] for part in languages.split(",")]
    for language in preferences:
        for path in files:
            if f".{language}." in path.name:
                return path
    return sorted(files)[0]


def collect(args: argparse.Namespace) -> None:
    output_dir = Path(args.out).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    executable = shutil.which("yt-dlp")
    if executable is None:
        fail("yt-dlp is required for URL collection; install it or provide a transcript")

    command = [
        executable,
        "--no-playlist",
        "--skip-download",
        "--write-info-json",
        "--write-auto-subs",
        "--write-subs",
        "--sub-langs",
        args.languages,
        "--sub-format",
        "vtt",
        "--output",
        str(output_dir / "video.%(ext)s"),
        "--",
        args.url,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        tail = "\n".join(detail[-8:])
        fail(f"yt-dlp could not collect the source\n{tail}")

    info_files = sorted(output_dir.glob("video*.info.json"))
    caption = choose_caption(sorted(output_dir.glob("*.vtt")), args.languages)
    metadata: dict[str, object] = {
        "schema_version": 1,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "url": args.url,
        "languages_requested": args.languages,
        "metadata_file": info_files[0].name if info_files else None,
        "caption_file": caption.name if caption else None,
    }
    if info_files:
        try:
            raw = json.loads(info_files[0].read_text(encoding="utf-8"))
            for key in ("id", "title", "channel", "uploader", "duration", "chapters"):
                if key in raw:
                    metadata[key] = raw[key]
        except (OSError, json.JSONDecodeError):
            metadata["metadata_warning"] = "yt-dlp metadata could not be parsed"
    (output_dir / "source.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"source": str(output_dir / "source.json"), "caption": str(caption) if caption else None}))
    if caption is None:
        fail("the source has no usable VTT captions; provide a transcript or local media")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="collect metadata and captions from a URL")
    collect_parser.add_argument("--url", required=True)
    collect_parser.add_argument("--out", required=True)
    collect_parser.add_argument("--languages", default="en.*,ar.*")
    collect_parser.set_defaults(handler=collect)

    chunk_parser = subparsers.add_parser("chunk", help="create bounded evidence chunks offline")
    chunk_parser.add_argument("--input", required=True)
    chunk_parser.add_argument("--out", required=True)
    chunk_parser.add_argument("--source-url")
    chunk_parser.add_argument("--max-words", type=int, default=750)
    chunk_parser.add_argument("--overlap-words", type=int, default=90)
    chunk_parser.set_defaults(
        handler=lambda args: write_chunk_output(
            build_chunks(
                load_cues(Path(args.input).expanduser()),
                args.max_words,
                args.overlap_words,
            ),
            Path(args.out).expanduser(),
            Path(args.input).expanduser(),
            args.source_url,
            args.max_words,
            args.overlap_words,
        )
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
