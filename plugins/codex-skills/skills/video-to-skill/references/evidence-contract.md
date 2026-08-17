# Evidence Contract

Use this contract for every `reports/<chunk-id>.json` file. The contract keeps a weak model from converting a plausible sentence into an unsupported rule.

## Required shape

```json
{
  "schema_version": 1,
  "chunk_id": "0003",
  "source": {
    "url": "https://example.com/video",
    "start": "00:12:40.000",
    "end": "00:17:05.000"
  },
  "summary": "One sentence describing only this chunk.",
  "facts": [
    {
      "id": "F-0003-01",
      "statement": "A worker timeout can be reproduced by ...",
      "status": "verified",
      "confidence": "high",
      "evidence": "Short paraphrase or a short quote.",
      "pointers": ["0003@00:13:02"]
    }
  ],
  "procedures": [
    {
      "id": "P-0003-01",
      "name": "Diagnose the timeout",
      "preconditions": ["Access to the worker logs"],
      "steps": [
        {
          "number": 1,
          "action": "Inspect the worker timeout setting.",
          "expected": "The configured value is visible.",
          "verify": "Compare it with the observed job duration.",
          "pointers": ["0003@00:14:10"]
        }
      ],
      "stop_conditions": ["Do not change production settings without approval."],
      "pointers": ["0003@00:13:40"]
    }
  ],
  "definitions": [],
  "warnings": [],
  "unknowns": [],
  "conflicts": [],
  "terms_to_clarify": []
}
```

## Allowed values

- `status`: `verified`, `inferred`, or `unknown`.
- `confidence`: `high`, `medium`, or `low`.
- Use `verified` only for information explicitly established by the chunk. Use `inferred` for a reasonable interpretation, and attach the supporting evidence. Use `unknown` when the chunk does not establish the answer.

## Evidence rules

1. Use the exact chunk ID and the nearest available timestamp in every pointer. For plain text without timestamps, use `chunk-id@untimed`.
2. Keep quotes short and necessary. Prefer paraphrase; never copy a full transcript or a long passage into the report.
3. Do not turn a speaker's claim into a verified fact merely because it sounds authoritative. Record “the speaker claims ...” if independent verification is unavailable.
4. Put missing prerequisites, omitted commands, unavailable credentials, and unclear screenshots in `unknowns`.
5. Put incompatible instructions in `conflicts` with both pointers. Do not resolve a conflict by majority vote.
6. Put dangerous, irreversible, credential-sensitive, or production-affecting actions in `warnings` and add a human-confirmation stop condition to any procedure.
7. Keep IDs stable within a report. During consolidation, preserve the original IDs in a `source_ids` field.

## Consolidated claims

`claims.json` may combine reports into this smaller shape:

```json
{
  "schema_version": 1,
  "source": {"url": "https://example.com/video"},
  "claims": [
    {
      "id": "C-001",
      "statement": "...",
      "type": "fact",
      "status": "verified",
      "confidence": "medium",
      "source_ids": ["F-0003-01", "F-0005-02"],
      "pointers": ["0003@00:13:02", "0005@00:22:11"]
    }
  ],
  "procedures": [],
  "unknowns": [],
  "conflicts": []
}
```

Only `verified` or carefully labeled `inferred` claims should become normative instructions in a generated skill. Preserve unresolved material as limitations.
