---
name: prime-architect-scraper
description: Design resilient, schema-first web extraction workflows and reusable scraper implementations for messy, dynamic, or partially protected websites. Use when Codex needs to turn unstructured site content into validated JSON or CSV, choose between API-first harvesting and DOM fallback extraction, inspect SPA behavior, map fields into typed records, or build professional Python scraping engines with robust retries, logging, and respectful anti-bot handling.
---

# Prime Architect Scraper

Treat the target as a system, not a page. Start with the site's data flows, rendering model, and failure modes before writing selectors.

## Workflow

1. Define the extraction contract.
   Capture the target URL, required fields, cardinality, output format, freshness requirements, and stop conditions. Write the schema first.

2. Inspect the logic path before the DOM.
   Check for internal JSON endpoints, GraphQL operations, embedded hydration blobs, `application/ld+json`, and XHR/fetch patterns. Prefer stable data contracts over brittle visual selectors.

3. Choose the lowest-friction execution layer.
   Use plain HTTP for public APIs and server-rendered pages. Use browser automation only when critical data is rendered client-side or interaction-gated.

4. Design resilience explicitly.
   Use semantic selectors, ARIA labels, `data-*` attributes, pagination cursors, and structured script payloads. Expect selectors, layouts, and load timing to drift.

5. Validate output as data, not text.
   Normalize whitespace, URLs, dates, and numbers. Enforce typed records before writing JSON or CSV.

## Decision Rules

- Prefer API-first extraction when the Network tab reveals a stable endpoint.
- Prefer static HTTP parsing when the first response already contains the needed content.
- Escalate to Playwright only for SPA hydration, gated interactions, infinite scroll, or content that appears after user events.
- Stop and surface the issue when the site presents a CAPTCHA, login wall, or explicit anti-bot challenge that requires human authorization.

## Implementation Guidance

- Keep extraction code modular: discovery, fetch, parse, validate, serialize.
- Use comprehensive logging with enough structure to debug retries, parser misses, and schema failures.
- Build selectors around intent: landmarks, labels, attributes, and embedded data. Avoid deep CSS paths unless there is no better anchor.
- Introduce jittered delays, bounded concurrency, and session reuse to reduce unnecessary pressure on the site.
- Treat rate limits as feedback. Back off, record the event, and resume only within safe limits.

## Resources

- Read [references/extraction-philosophy.md](./references/extraction-philosophy.md) when you need the deeper operating model for resilience, purity, and silent execution.
- Use [scripts/prime_architect_scraper.py](./scripts/prime_architect_scraper.py) as the starting engine. Extend it per target instead of rewriting the entire stack.

## Output Standard

Produce extraction artifacts that look like they came from the site's own data layer: typed, normalized, reproducible, and easy to audit.
