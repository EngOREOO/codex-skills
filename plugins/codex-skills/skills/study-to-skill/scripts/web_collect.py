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
from dataclasses import dataclass, field
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


def normalize_url(raw_url: str) -> str:
    defragmented_url, _ = urldefrag(raw_url.strip())
    parsed_url = urlparse(defragmented_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError(f"only public HTTP(S) URLs are supported: {defragmented_url}")
    normalized_url = parsed_url._replace(
        scheme=parsed_url.scheme.lower(), netloc=parsed_url.netloc.lower()
    )
    return urlunparse(normalized_url)


def same_origin(left_url: str, right_url: str) -> bool:
    left_parts = urlparse(left_url)
    right_parts = urlparse(right_url)
    return (left_parts.scheme.lower(), left_parts.netloc.lower()) == (
        right_parts.scheme.lower(), right_parts.netloc.lower()
    )


def default_path_prefix(url: str) -> str:
    path = urlparse(url).path or "/"
    if path.endswith("/"):
        return path
    parent = path.rsplit("/", 1)[0]
    return f"{parent}/" if parent else "/"


def normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip() + "\n"


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

    def handle_data(self, page_text: str) -> None:
        if self.in_title and page_text.strip():
            self.title_parts.append(page_text.strip())
        if self.hidden_depth == 0 and page_text.strip():
            self.parts.append(page_text)

    @property
    def title(self) -> str:
        return normalize_text(" ".join(self.title_parts)).strip()

    @property
    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


@dataclass(frozen=True)
class CrawlItem:
    url: str
    depth: int
    parent_url: str | None


@dataclass(frozen=True)
class FetchedPage:
    final_url: str
    status: int
    content_type: str
    body: bytes


@dataclass(frozen=True)
class CrawlConfig:
    start_url: str
    output_dir: Path
    path_prefix: str
    whole_origin: bool
    user_agent: str
    timeout: float
    max_bytes: int
    max_pages: int
    max_depth: int
    delay: float
    robots: RobotFileParser
    robots_metadata: dict[str, Any]


@dataclass
class CrawlState:
    queue: deque[CrawlItem]
    queued_urls: set[str]
    visited_urls: set[str] = field(default_factory=set)
    pages: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    content_origins: dict[str, str] = field(default_factory=dict)
    last_request_at: float = 0.0


def load_robots(
    start_url: str, user_agent: str, timeout: float
) -> tuple[RobotFileParser, dict[str, Any]]:
    parsed_url = urlparse(start_url)
    robots_url = urlunparse((parsed_url.scheme, parsed_url.netloc, "/robots.txt", "", "", ""))
    robots = RobotFileParser()
    robots.set_url(robots_url)
    robots_metadata: dict[str, Any] = {"url": robots_url, "status": "unknown"}
    request = Request(robots_url, headers={"User-Agent": user_agent, "Accept": "text/plain"})
    try:
        with urlopen(request, timeout=timeout) as response:
            robots_body = response.read(1024 * 1024 + 1)
            if len(robots_body) > 1024 * 1024:
                fail("robots.txt exceeds 1 MiB")
            robots.parse(robots_body.decode("utf-8", errors="replace").splitlines())
            robots_metadata.update({
                "status": int(getattr(response, "status", 200)),
                "sha256": hashlib.sha256(robots_body).hexdigest(),
            })
    except HTTPError as exc:
        if exc.code != 404:
            fail(f"cannot verify robots policy ({exc.code}) at {robots_url}")
        robots.parse([])
        robots_metadata["status"] = 404
    except URLError as exc:
        fail(f"cannot verify robots policy at {robots_url}: {exc.reason}")
    return robots, robots_metadata


def allowed_url(
    candidate_url: str, start_url: str, path_prefix: str, whole_origin: bool
) -> str | None:
    try:
        normalized_url = normalize_url(candidate_url)
    except ValueError:
        return None
    if not same_origin(normalized_url, start_url):
        return None
    if not whole_origin and not (urlparse(normalized_url).path or "/").startswith(path_prefix):
        return None
    return normalized_url


def fetch_page(url: str, user_agent: str, timeout: float, max_bytes: int) -> FetchedPage:
    request = Request(url, headers={
        "User-Agent": user_agent,
        "Accept": "text/html, text/plain, application/json, application/xml;q=0.9",
    })
    with urlopen(request, timeout=timeout) as response:
        response_body = response.read(max_bytes + 1)
        if len(response_body) > max_bytes:
            raise ValueError(f"response exceeds --max-bytes: {url}")
        return FetchedPage(
            final_url=normalize_url(response.geturl()),
            status=int(getattr(response, "status", 200)),
            content_type=response.headers.get_content_type().lower(),
            body=response_body,
        )


def validate_options(options: argparse.Namespace) -> None:
    if not 1 <= options.max_pages <= 100:
        fail("--max-pages must be between 1 and 100")
    if not 0 <= options.max_depth <= 4:
        fail("--max-depth must be between 0 and 4")
    if not 0.25 <= options.delay <= 30:
        fail("--delay must be between 0.25 and 30 seconds")
    if not 1024 <= options.max_bytes <= 50 * 1024 * 1024:
        fail("--max-bytes must be between 1 KiB and 50 MiB")


def build_config(options: argparse.Namespace) -> CrawlConfig:
    validate_options(options)
    try:
        start_url = normalize_url(options.url)
    except ValueError as exc:
        fail(str(exc))
    output_dir = options.out.expanduser().resolve()
    (output_dir / "raw").mkdir(parents=True, exist_ok=True)
    (output_dir / "text").mkdir(parents=True, exist_ok=True)
    robots, robots_metadata = load_robots(start_url, options.user_agent, options.timeout)
    crawl_delay = robots.crawl_delay(options.user_agent) or robots.crawl_delay("*") or 0
    return CrawlConfig(
        start_url=start_url,
        output_dir=output_dir,
        path_prefix=default_path_prefix(start_url),
        whole_origin=options.whole_origin,
        user_agent=options.user_agent,
        timeout=options.timeout,
        max_bytes=options.max_bytes,
        max_pages=options.max_pages,
        max_depth=options.max_depth,
        delay=max(options.delay, float(crawl_delay)),
        robots=robots,
        robots_metadata=robots_metadata,
    )


def initial_state(start_url: str) -> CrawlState:
    start_item = CrawlItem(url=start_url, depth=0, parent_url=None)
    return CrawlState(queue=deque([start_item]), queued_urls={start_url})


def manifest_payload(config: CrawlConfig, state: CrawlState) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "start_url": config.start_url,
        "path_prefix": config.path_prefix,
        "whole_origin": config.whole_origin,
        "robots": config.robots_metadata,
        "pages": state.pages,
        "failures": state.failures,
    }


def write_manifest(config: CrawlConfig, state: CrawlState) -> None:
    manifest_text = json.dumps(manifest_payload(config, state), ensure_ascii=False, indent=2) + "\n"
    atomic_write(config.output_dir / "manifest.json", manifest_text)


def wait_for_rate_limit(config: CrawlConfig, state: CrawlState) -> None:
    elapsed = time.monotonic() - state.last_request_at
    if elapsed < config.delay:
        time.sleep(config.delay - elapsed)


def extract_page(fetched_page: FetchedPage) -> tuple[str, str, str, list[str]] | None:
    if fetched_page.content_type == "text/html":
        page_parser = PageParser(fetched_page.final_url)
        page_parser.feed(fetched_page.body.decode("utf-8", errors="replace"))
        return ".html", page_parser.title, page_parser.text, page_parser.links
    if fetched_page.content_type.startswith("text/") or fetched_page.content_type in {
        "application/json", "application/xml"
    }:
        page_text = normalize_text(fetched_page.body.decode("utf-8", errors="replace"))
        return ".txt", "", page_text, []
    return None


def store_page(
    config: CrawlConfig, state: CrawlState, crawl_item: CrawlItem, fetched_page: FetchedPage
) -> list[str] | None:
    extracted_page = extract_page(fetched_page)
    if not extracted_page:
        state.failures.append({
            "url": fetched_page.final_url,
            "reason": f"unsupported-content-type:{fetched_page.content_type}",
        })
        return None
    extension, page_title, page_text, links = extracted_page
    page_id = f"W{len(state.pages) + 1:03d}"
    raw_path = config.output_dir / "raw" / f"{page_id}{extension}"
    text_path = config.output_dir / "text" / f"{page_id}.txt"
    raw_path.write_bytes(fetched_page.body)
    atomic_write(text_path, page_text)
    page_record = {
        "schema_version": 1,
        "page_id": page_id,
        "url": fetched_page.final_url,
        "requested_url": crawl_item.url,
        "parent_url": crawl_item.parent_url,
        "depth": crawl_item.depth,
        "title": page_title,
        "retrieved_at": utc_now(),
        "status": fetched_page.status,
        "content_type": fetched_page.content_type,
        "encoding": "utf-8",
        "bytes": len(fetched_page.body),
        "sha256": hashlib.sha256(fetched_page.body).hexdigest(),
        "raw_path": str(raw_path.relative_to(config.output_dir)),
        "text_path": str(text_path.relative_to(config.output_dir)),
    }
    state.pages.append(page_record)
    state.content_origins[page_record["sha256"]] = fetched_page.final_url
    return links


def enqueue_links(
    config: CrawlConfig, state: CrawlState, crawl_item: CrawlItem, links: list[str]
) -> None:
    if crawl_item.depth >= config.max_depth:
        return
    for link in links:
        candidate_url = allowed_url(link, config.start_url, config.path_prefix, config.whole_origin)
        if candidate_url and candidate_url not in state.queued_urls and len(state.queued_urls) < config.max_pages * 25:
            state.queued_urls.add(candidate_url)
            state.queue.append(CrawlItem(candidate_url, crawl_item.depth + 1, crawl_item.url))


def collect_item(config: CrawlConfig, state: CrawlState, crawl_item: CrawlItem) -> None:
    if crawl_item.url in state.visited_urls:
        return
    state.visited_urls.add(crawl_item.url)
    if not config.robots.can_fetch(config.user_agent, crawl_item.url):
        state.failures.append({"url": crawl_item.url, "reason": "blocked-by-robots"})
        return
    wait_for_rate_limit(config, state)
    try:
        fetched_page = fetch_page(
            crawl_item.url, config.user_agent, config.timeout, config.max_bytes
        )
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        state.failures.append({"url": crawl_item.url, "reason": str(exc)})
        return
    state.last_request_at = time.monotonic()
    if not allowed_url(
        fetched_page.final_url, config.start_url, config.path_prefix, config.whole_origin
    ):
        state.failures.append({
            "url": crawl_item.url,
            "reason": f"redirected-out-of-scope:{fetched_page.final_url}",
        })
        return
    page_hash = hashlib.sha256(fetched_page.body).hexdigest()
    if page_hash in state.content_origins:
        state.failures.append({
            "url": fetched_page.final_url,
            "reason": f"duplicate-content:{state.content_origins[page_hash]}",
        })
        return
    links = store_page(config, state, crawl_item, fetched_page)
    if links is not None:
        resolved_item = CrawlItem(
            fetched_page.final_url, crawl_item.depth, crawl_item.parent_url
        )
        enqueue_links(config, state, resolved_item, links)
        write_manifest(config, state)


def crawl(config: CrawlConfig) -> CrawlState:
    state = initial_state(config.start_url)
    while state.queue and len(state.pages) < config.max_pages:
        collect_item(config, state, state.queue.popleft())
    write_manifest(config, state)
    return state


def build_parser() -> argparse.ArgumentParser:
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
    return parser


def main() -> int:
    config = build_config(build_parser().parse_args())
    crawl_state = crawl(config)
    summary = {
        "out": str(config.output_dir),
        "start_url": config.start_url,
        "pages_collected": len(crawl_state.pages),
        "failures": crawl_state.failures,
        "robots": config.robots_metadata,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if crawl_state.pages else 1


if __name__ == "__main__":
    raise SystemExit(main())
