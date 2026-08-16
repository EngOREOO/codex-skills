#!/usr/bin/env python3
"""Prime Architect Scraper.

Build schema-first, API-aware extraction workflows with respectful pacing,
rate-limit handling, and typed output records.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib import error, parse, request

LOGGER = logging.getLogger("prime_architect_scraper")
USER_AGENTS = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
)
CAPTCHA_MARKERS = ("captcha", "cf-challenge", "recaptcha", "hcaptcha", "verify you are human")
RATE_LIMIT_CODES = {429, 503}
API_HINT_PATTERN = re.compile(r"https?://[^\"'\s>]+|/api/[^\"'\s>]+|/graphql[^\"'\s>]*", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\+?[0-9][0-9()\-\s]{7,}[0-9]")
WHITESPACE_PATTERN = re.compile(r"\s+")


class ScraperError(Exception):
    """Base exception for scraper failures."""


class BotChallengeDetected(ScraperError):
    """Raised when a bot challenge or CAPTCHA is detected."""


class RateLimitDetected(ScraperError):
    """Raised when a target signals rate limiting."""


@dataclass(slots=True)
class ScraperConfig:
    """Configuration for extraction behavior."""

    min_delay: float = 0.5
    max_delay: float = 1.5
    max_retries: int = 3
    timeout: float = 20.0
    concurrency: int = 3
    user_agent: str = field(default_factory=lambda: random.choice(USER_AGENTS))


@dataclass(slots=True)
class ExtractionRecord:
    """Typed output record for harvested data."""

    source_url: str
    title: str | None = None
    text: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    api_hints: list[str] = field(default_factory=list)
    json_ld: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> None:
        """Validate core field types and value shapes."""
        if not self.source_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid source URL: {self.source_url}")
        for field_name in ("emails", "phones", "links", "api_hints", "json_ld"):
            value = getattr(self, field_name)
            if not isinstance(value, list):
                raise ValueError(f"{field_name} must be a list")
        if self.title is not None and not isinstance(self.title, str):
            raise ValueError("title must be a string or null")
        if self.text is not None and not isinstance(self.text, str):
            raise ValueError("text must be a string or null")


class SemanticHTMLParser(HTMLParser):
    """Extract semantic text, links, title, and JSON-LD blocks from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.in_script = False
        self.current_script_type = ""
        self.title_chunks: list[str] = []
        self.text_chunks: list[str] = []
        self.links: list[str] = []
        self.script_chunks: list[str] = []
        self.json_ld_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Track tags relevant to extraction."""
        attr_map = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "a" and attr_map.get("href"):
            self.links.append(attr_map["href"] or "")
        if tag == "script":
            self.in_script = True
            self.current_script_type = (attr_map.get("type") or "").lower()
            self.script_chunks = []

    def handle_endtag(self, tag: str) -> None:
        """Flush script buffers and stop tag tracking."""
        if tag == "title":
            self.in_title = False
        if tag == "script" and self.in_script:
            script_body = "".join(self.script_chunks).strip()
            if self.current_script_type == "application/ld+json" and script_body:
                self.json_ld_blocks.append(script_body)
            self.in_script = False
            self.current_script_type = ""
            self.script_chunks = []

    def handle_data(self, data: str) -> None:
        """Collect text content and structured script bodies."""
        if self.in_title:
            self.title_chunks.append(data)
        if self.in_script:
            self.script_chunks.append(data)
            return
        normalized = normalize_text(data)
        if normalized:
            self.text_chunks.append(normalized)


def normalize_text(value: str | None) -> str:
    """Collapse whitespace and strip surrounding noise."""
    return WHITESPACE_PATTERN.sub(" ", value or "").strip()


def dedupe(values: Iterable[str]) -> list[str]:
    """Preserve order while removing duplicates and empty values."""
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        item = normalize_text(value)
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return output


def absolutize(base_url: str, links: Iterable[str]) -> list[str]:
    """Convert relative links into absolute URLs."""
    return dedupe(parse.urljoin(base_url, link) for link in links)


def detect_challenge(content: str, status_code: int) -> None:
    """Raise explicit exceptions for challenge and rate-limit pages."""
    lowered = content.lower()
    if any(marker in lowered for marker in CAPTCHA_MARKERS):
        raise BotChallengeDetected("Bot challenge detected; stop and request human authorization.")
    if status_code in RATE_LIMIT_CODES:
        raise RateLimitDetected(f"Rate limit detected with status code {status_code}")


class PrimeArchitectScraper:
    """Coordinate discovery, fetch, parse, validation, and serialization."""

    def __init__(self, config: ScraperConfig | None = None) -> None:
        """Initialize the scraper with runtime configuration."""
        self.config = config or ScraperConfig()
        self._semaphore = asyncio.Semaphore(self.config.concurrency)

    async def scrape(self, urls: list[str]) -> list[ExtractionRecord]:
        """Scrape multiple URLs with bounded concurrency."""
        tasks = [asyncio.create_task(self._scrape_url(url)) for url in urls]
        return await asyncio.gather(*tasks)

    async def _scrape_url(self, url: str) -> ExtractionRecord:
        """Scrape a single URL end-to-end."""
        async with self._semaphore:
            await self._human_pause()
            html, final_url, status_code = await asyncio.to_thread(self._fetch_with_retries, url)
            record = self._parse_document(final_url, html, status_code)
            record.validate()
            return record

    async def _human_pause(self) -> None:
        """Apply bounded jitter to reduce burstiness."""
        await asyncio.sleep(random.uniform(self.config.min_delay, self.config.max_delay))

    def _fetch_with_retries(self, url: str) -> tuple[str, str, int]:
        """Fetch content with retry and backoff discipline."""
        last_error: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                return self._fetch_once(url)
            except RateLimitDetected as exc:
                last_error = exc
                sleep_for = min(8.0, attempt * 2.0 + random.random())
                LOGGER.warning("rate limit on %s; backing off for %.2fs", url, sleep_for)
                time.sleep(sleep_for)
            except BotChallengeDetected:
                raise
            except Exception as exc:
                last_error = exc
                LOGGER.warning("fetch failure on attempt %s for %s: %s", attempt, url, exc)
                time.sleep(attempt + random.random())
        raise ScraperError(f"Failed to fetch {url}: {last_error}")

    def _fetch_once(self, url: str) -> tuple[str, str, int]:
        """Fetch a URL once using urllib with coherent headers."""
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        req = request.Request(url, headers=headers)
        try:
            with request.urlopen(req, timeout=self.config.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                status_code = getattr(response, "status", 200)
                final_url = response.geturl()
                detect_challenge(body, status_code)
                return body, final_url, status_code
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            detect_challenge(body, exc.code)
            raise ScraperError(f"HTTP {exc.code} for {url}") from exc
        except error.URLError as exc:
            raise ScraperError(f"Network error for {url}: {exc.reason}") from exc

    def _parse_document(self, url: str, html: str, status_code: int) -> ExtractionRecord:
        """Parse HTML into a typed extraction record."""
        parser = SemanticHTMLParser()
        parser.feed(html)

        json_ld = [self._safe_json_loads(block) for block in parser.json_ld_blocks]
        json_ld = [item for item in json_ld if item is not None]

        links = absolutize(url, parser.links)
        api_hints = dedupe(parse.urljoin(url, match.group(0)) for match in API_HINT_PATTERN.finditer(html))
        text = normalize_text(" ".join(parser.text_chunks))

        metadata = {
            "status_code": status_code,
            "content_length": len(html),
            "link_count": len(links),
            "api_hint_count": len(api_hints),
        }

        return ExtractionRecord(
            source_url=url,
            title=normalize_text(" ".join(parser.title_chunks)) or None,
            text=text or None,
            emails=dedupe(EMAIL_PATTERN.findall(html)),
            phones=dedupe(PHONE_PATTERN.findall(html)),
            links=links,
            api_hints=api_hints,
            json_ld=json_ld,
            metadata=metadata,
        )

    def _safe_json_loads(self, raw_value: str) -> dict[str, Any] | list[Any] | None:
        """Parse JSON payloads defensively."""
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return None
        return parsed


def write_json(records: list[ExtractionRecord], output_path: Path) -> None:
    """Write extraction output as formatted JSON."""
    output_path.write_text(
        json.dumps([asdict(record) for record in records], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(records: list[ExtractionRecord], output_path: Path) -> None:
    """Write extraction output as normalized CSV."""
    fieldnames = [
        "source_url",
        "title",
        "text",
        "emails",
        "phones",
        "links",
        "api_hints",
        "json_ld",
        "metadata",
        "extracted_at",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            for key in ("emails", "phones", "links", "api_hints", "json_ld", "metadata"):
                row[key] = json.dumps(row[key], ensure_ascii=False)
            writer.writerow(row)


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line interface."""
    parser = argparse.ArgumentParser(description="Harvest structured data from target URLs.")
    parser.add_argument("urls", nargs="+", help="Target URL or URLs to extract.")
    parser.add_argument("--format", choices=("json", "csv"), default="json", help="Output format.")
    parser.add_argument("--output", required=True, help="Path to the output file.")
    parser.add_argument("--min-delay", type=float, default=0.5, help="Minimum delay between requests.")
    parser.add_argument("--max-delay", type=float, default=1.5, help="Maximum delay between requests.")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum fetch retries per URL.")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds.")
    parser.add_argument("--concurrency", type=int, default=3, help="Maximum concurrent fetches.")
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    return parser


async def async_main(argv: list[str]) -> int:
    """Run the CLI workflow."""
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    config = ScraperConfig(
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        max_retries=args.max_retries,
        timeout=args.timeout,
        concurrency=args.concurrency,
    )
    scraper = PrimeArchitectScraper(config)

    try:
        records = await scraper.scrape(args.urls)
    except BotChallengeDetected as exc:
        LOGGER.error("challenge detected: %s", exc)
        return 2
    except ScraperError as exc:
        LOGGER.error("scrape failed: %s", exc)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "json":
        write_json(records, output_path)
    else:
        write_csv(records, output_path)

    LOGGER.info("wrote %s record(s) to %s", len(records), output_path)
    return 0


def main() -> int:
    """Entrypoint for the scraper CLI."""
    return asyncio.run(async_main(sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
