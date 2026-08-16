---
name: mem0-memory
description: Use the self-hosted Mem0 MCP server for durable project and user memory.
---

# Mem0 memory workflow

Use the `mem0` MCP server at `https://mem0.codiaumx.com/mcp` for durable context.

## Scope and safety

- Always send `user_id: "mmtechstore"` and `app_id: "mem0"` unless the user explicitly provides another scope.
- Search before adding a memory to avoid duplicates and contradictions.
- Store durable preferences, decisions, constraints, task learnings, and outcomes—not passwords, API keys, tokens, or payment details.
- Never include a secret in a memory, prompt, log, or issue.

## Before work

Use `search_memories` with both scope filters to recover relevant decisions, known bugs, and user preferences before making a substantial change.

## After meaningful work

Use `add_memory` with `infer: false` for a concise factual summary after a meaningful implementation, decision, bug fix, deployment, or user preference. Include file names and the outcome in `metadata` when useful.

## Tools

Use `add_memory`, `search_memories`, `get_memories`, `get_memory`, `update_memory`, `delete_memory`, and `list_events` for the normal lifecycle. Use destructive tools only when the user explicitly asks and the scope is explicit.
