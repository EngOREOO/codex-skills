#!/usr/bin/env python3
"""Collect a small public same-origin web corpus with conservative controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser


HIDDEN_TAGS = {"script", "style", "noscript", "svg", "canvas", "template"}
BLOCK_TAGS = {
    "p", "br", "div", "section", "article", "main", "aside", "nav", "li",
    "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th", "pre", "code",
}


def fail(message: str, code: int = 2) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def normalize_url(value: str) -> str:
    value, _ = urldefrag(value.strip())
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"only public HTTP(S) URLs are supported: {value}")
    normalized = parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower())
    return urlunparse(normalized)


def same_origin(left: str, right: str) -> bool:
    left_parsed = urlparse(left)
    right_parsed = urlparse(right)
    return (left_parsed.scheme.lower(), left_parsed.netloc.lower()) == (
        right_parsed.scheme.lower(), right_parsed.netloc.lower()
    )


def default_path_prefix(url: str) -> str:
    path = urlparse(url).path or "/"
    if path.endswith("/"):
        return path
    parent = path.rsplit("/", 1)[0]
    return f"{parent}/" if parent else "/"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


class PageParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.parts: list[str] = []
        self.links: list[str] = []
        self.title_parts: list[str] = []
        self.hidden_depth = 0
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in HIDDEN_TAGS:
            self.hidden_depth += 1
        elif lowered == "title":
            self.in_title = True
        elif lowered in BLOCK_TAGS:
            self.parts.append("\n")
        if lowered == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(urljoin(self.base_url, href))

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in HIDDEN_TAGS:
            self.hidden_depth = max(0, self.hidden_depth - 1)
        elif lowered == "title":
            self.in_title = False
        elif lowered in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.in_title and data.strip():
            self.title_parts.append(data.strip())
        if self.hidden_depth == 0 and data.strip():
            self.parts.append(data)

    @property
    def title(self) -> str:
        return normalize_text(" ".join(self.title_parts)).strip()

    @property
    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


def load_robots(start_url: str, user_agent: str, timeout: float) -> tuple[RobotFileParser, dict[str, Any]]:
    parsed = urlparse(start_url)
    robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    parser = RobotFileParser()
    parser.set_url(robots_url)
    metadata: dict[str, Any] = {"url": robots_url, "status": "unknown"}
    request = Request(robots_url, headers={"User-Agent": user_agent, "Accept": "text/plain"})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                fail("robots.txt exceeds 1 MiB")
            text = data.decode("utf-8", errors="replace")
            parser.parse(text.splitlines())
            metadata.update({"status": int(getattr(response, "status", 200)), "sha256": hashlib.sha256(data).hexdigest()})
    except HTTPError as exc:
        if exc.code == 404:
            parser.parse([])
            metadata["status"] = 404
        else:
            fail(f"cannot verify robots policy ({exc.code}) at {robots_url}")
    except URLError as exc:
        fail(f"cannot verify robots policy at {robots_url}: {exc.reason}")
    return parser, metadata


def allowed_url(candidate: str, start_url: str, path_prefix: str, whole_origin: bool) -> str | None:
    try:
        normalized = normalize_url(candidate)
    except ValueError:
        return None
    if not same_origin(normalized, start_url):
        return None
    if not whole_origin and not (urlparse(normalized).path or "/").startswith(path_prefix):
        return None
    return normalized


def fetch_page(url: str, user_agent: str, timeout: float, max_bytes: int) -> tuple[str, int, str, bytes]:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html, text/plain, application/json, application/xml;q=0.9",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        final_url = normalize_url(response.geturl())
        status = int(getattr(response, "status", 200))
        content_type = response.headers.get_content_type().lower()
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            fail(f"response exceeds --max-bytes: {url}")
        return final_url, status, content_type, data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-pages", type=int, default=12)
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument("--max-bytes", type=int, default=5 * 1024 * 1024)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--whole-origin", action="store_true", help="allow paths outside the starting directory")
    parser.add_argument("--user-agent", default="StudyToSkill/1.0 (+local evidence collection)")
    args = parser.parse_args()

    if not 1 <= args.max_pages <= 100:
        fail("--max-pages must be between 1 and 100")
    if not 0 <= args.max_depth <= 4:
        fail("--max-depth must be between 0 and 4")
    if not 0.25 <= args.delay <= 30:
        fail("--delay must be between 0.25 and 30 seconds")
    if not 1024 <= args.max_bytes <= 50 * 1024 * 1024:
        fail("--max-bytes must be between 1 KiB and 50 MiB")

    try:
        start_url = normalize_url(args.url)
    except ValueError as exc:
        fail(str(exc))
    out = args.out.expanduser().resolve()
    raw_dir = out / "raw"
    text_dir = out / "text"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    path_prefix = default_path_prefix(start_url)
    robots, robots_metadata = load_robots(start_url, args.user_agent, args.timeout)
    crawl_delay = robots.crawl_delay(args.user_agent) or robots.crawl_delay("*") or 0
    delay = max(args.delay, float(crawl_delay))

    queue: deque[tuple[str, int, str | None]] = deque([(start_url, 0, None)])
    queued = {start_url}
    visited: set[str] = set()
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    content_hashes: dict[str, str] = {}
    last_request_at = 0.0

    while queue and len(records) < args.max_pages:
        url, depth, parent = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        if not robots.can_fetch(args.user_agent, url):
            failures.append({"url": url, "reason": "blocked-by-robots"})
            continue

        elapsed = time.monotonic() - last_request_at
        if elapsed < delay:
            time.sleep(delay - elapsed)
        try:
            final_url, status, content_type, data = fetch_page(url, args.user_agent, args.timeout, args.max_bytes)
        except (HTTPError, URLError, TimeoutError, ValueError, SystemExit) as exc:
            failures.append({"url": url, "reason": str(exc)})
            continue
        last_request_at = time.monotonic()

        allowed_final = allowed_url(final_url, start_url, path_prefix, args.whole_origin)
        if not allowed_final:
            failures.append({"url": url, "reason": f"redirected-out-of-scope:{final_url}"})
            continue

        digest = hashlib.sha256(data).hexdigest()
        if digest in content_hashes:
            failures.append({"url": final_url, "reason": f"duplicate-content:{content_hashes[digest]}"})
            continue

        page_id = f"W{len(records) + 1:03d}"
        title = ""
        links: list[str] = []
        encoding = "utf-8"
        extension = ".bin"
        normalized = ""
        if content_type == "text/html":
            extension = ".html"
            decoded = data.decode("utf-8", errors="replace")
            parser_instance = PageParser(final_url)
            parser_instance.feed(decoded)
            title = parser_instance.title
            normalized = parser_instance.text
            links = parser_instance.links
        elif content_type.startswith("text/") or content_type in {"application/json", "application/xml"}:
            extension = ".txt"
            normalized = normalize_text(data.decode("utf-8", errors="replace"))
        else:
            failures.append({"url": final_url, "reason": f"unsupported-content-type:{content_type}"})
            continue

        raw_path = raw_dir / f"{page_id}{extension}"
        raw_path.write_bytes(data)
        text_path = text_dir / f"{page_id}.txt"
        atomic_write(text_path, normalized)
        record = {
            "schema_version": 1,
            "page_id": page_id,
            "url": final_url,
            "requested_url": url,
            "parent_url": parent,
            "depth": depth,
            "title": title,
            "retrieved_at": utc_now(),
            "status": status,
            "content_type": content_type,
            "encoding": encoding,
            "bytes": len(data),
            "sha256": digest,
            "raw_path": str(raw_path.relative_to(out)),
            "text_path": str(text_path.relative_to(out)),
        }
        records.append(record)
        content_hashes[digest] = final_url
        atomic_write(out / "manifest.json", json.dumps({
            "schema_version": 1,
            "start_url": start_url,
            "path_prefix": path_prefix,
            "whole_origin": args.whole_origin,
            "robots": robots_metadata,
            "pages": records,
            "failures": failures,
        }, ensure_ascii=False, indent=2) + "\n")

        if depth >= args.max_depth:
            continue
        for link in links:
            candidate = allowed_url(link, start_url, path_prefix, args.whole_origin)
            if candidate and candidate not in queued and len(queued) < args.max_pages * 25:
                queued.add(candidate)
                queue.append((candidate, depth + 1, final_url))

    atomic_write(out / "manifest.json", json.dumps({
        "schema_version": 1,
        "start_url": start_url,
        "path_prefix": path_prefix,
        "whole_origin": args.whole_origin,
        "robots": robots_metadata,
        "pages": records,
        "failures": failures,
    }, ensure_ascii=False, indent=2) + "\n")

    result = {
        "out": str(out),
        "start_url": start_url,
        "pages_collected": len(records),
        "failures": failures,
        "robots": robots_metadata,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
