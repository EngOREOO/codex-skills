# Generated Skill Contract

Use this contract after the evidence reports have been reconciled. It is a compact target for a cheap model to follow and a checklist for a stronger model to review.

## Frontmatter

The generated `SKILL.md` must contain only:

```yaml
---
name: lower-case-kebab-name
description: What the skill does and the realistic prompts that should trigger it.
---
```

The description is the trigger. Name the capability and its boundaries there; do not hide trigger conditions in the body.

## Body structure

Use this order unless the domain requires a clear variation:

1. **Purpose and scope** — state the repeatable job and the non-goals.
2. **Inputs and preconditions** — identify required files, access, tools, and permissions.
3. **Decision tree** — choose the correct variant before editing or executing anything.
4. **Procedure** — short numbered steps, one action per step.
5. **Verification** — state the expected evidence of success after each fragile step.
6. **Failure recovery** — describe safe stopping points and how to diagnose the common failures.
7. **Security and authorization** — identify secrets, production access, destructive changes, and approval gates.
8. **Source notes** — cite the originating URL and timestamps without including the full transcript.

Keep the body below 500 lines. Move variant-specific detail to one-level `references/` files and link them directly from the skill.

## Reuse test

Before registering the skill, test three prompts:

| Test | Expected result |
|---|---|
| Normal use | The skill triggers and produces the intended procedure. |
| Boundary case | The skill asks for missing prerequisites or stops safely. |
| Non-trigger | The skill does not hijack an unrelated request. |

If the skill only works when the original transcript is present, it is not ready. Rewrite the procedure so another model can execute it from the skill and its references alone.

## Registry record

Register one record per skill with:

- the exact skill name and path;
- source URL and topic;
- short summary and searchable tags;
- creation/update time;
- limitations or required dependencies.

Update a matching record instead of creating a duplicate. The registry is an index, not a replacement for the skill's frontmatter.
