# Learned Artifact Contract

## Output decision

Choose one output:

| Evidence result | Output |
| --- | --- |
| One-off question, weak coverage, or unresolved conflicts | Study report |
| One focused repeatable capability | Skill |
| Several coordinated capabilities or packaged MCP/app/hook integration | Plugin |
| Existing artifact has the same trigger and scope | Update existing artifact |

Do not create a plugin merely to appear more complete. Start with a skill unless packaging or runtime integration is necessary.

## Evidence threshold

Before generating an artifact, require:

- explicit scope, inputs, prerequisites, and non-goals;
- validated reports for every source chunk used;
- source pointers for every normative rule and procedure step;
- contradictions and version boundaries resolved or preserved as limitations;
- explain, apply, challenge, and recover tests passing;
- no raw source dump, secret, personal data, or inaccessible dependency embedded.

## Skill contract

Use `$skill-creator` and its initializer. The generated skill must have:

1. frontmatter containing only `name` and a realistic trigger `description`;
2. purpose, scope, and non-goals;
3. inputs and prerequisites;
4. a short decision tree;
5. executable steps with verification and safe stopping points;
6. failure recovery and security/authorization boundaries;
7. concise source notes in a one-level reference file;
8. `agents/openai.yaml` with a prompt naming `$skill-name`;
9. successful `quick_validate.py` output;
10. normal, boundary, and non-trigger tests.

Keep `SKILL.md` under 500 lines. Store only distilled reusable knowledge, not the study workspace.

## Plugin contract

Use `$plugin-creator` when the capability requires multiple skills, MCP servers, apps, hooks, shared scripts, or marketplace installation. The generated plugin must have:

- normalized matching folder and manifest names;
- `.codex-plugin/plugin.json` with no placeholders;
- only companion fields whose files actually exist;
- required marketplace policy/category metadata when a marketplace entry is requested;
- validation through `validate_plugin.py`;
- explicit dependency, authentication, installation, and update behavior;
- a threat review for external tools, network calls, credentials, and data retention.

Do not create or modify marketplace entries unless the user requested that installation scope.

## Source notes

For each generated artifact, store a concise reference containing:

- study topic and objective;
- source IDs, titles, URLs/paths, versions, and retrieval dates;
- source-manifest hash;
- claim/procedure IDs used;
- unresolved conflicts and freshness assumptions;
- excluded material and rights/privacy notes.

Do not include full articles, transcripts, private documents, or bulk copied code.

## Reuse and update

Register the artifact after validation. Before creating a near-duplicate:

1. search registry and installed skill/plugin roots;
2. compare trigger, scope, version, and dependencies;
3. update when the new evidence extends the same capability;
4. create a new artifact only when the trigger or operational boundary is materially different;
5. preserve provenance and note superseded claims.

An artifact is ready only when another model can use it without the raw study pack and can identify when not to use it.
