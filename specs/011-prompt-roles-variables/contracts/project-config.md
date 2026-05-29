# Contract: Project Config Prompt References

## Existing Single-Text Prompt

Existing prompt references remain valid.

```yaml
task_prompt:
  path: prompts/rewrite_quality/task_prompt.md
  version: v1
  template_variables:
    - input
```

If the referenced file has no `## role: <role-label>` headings, it is treated as
a legacy single-text prompt.

## Role-Based Prompt

Role-based prompts use the same project config shape. The file content
determines whether the prompt is role-based.

```yaml
task_prompt:
  path: prompts/dfe/task_prompt.md
  version: v1
  template_variables:
    - dataset.input
```

The prompt file must use the role heading contract in
[prompt-file-format.md](./prompt-file-format.md).

## Candidate Prompt Override

Candidate prompt overrides keep the existing full-override behavior.

```yaml
candidates:
  - name: dfe-role-prompt-v2
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt-4.1
    task_prompt:
      path: prompts/dfe/task_prompt_v2.md
      version: v2
      template_variables:
        - dataset.input
```

Rules:

- The candidate override replaces the full project prompt definition.
- Partial role or message inheritance is not supported.
- The override may be legacy single-text or role-based.
- Baseline prompt identity and candidate prompt identity remain separate.

## Validation Outcomes

Project validation must fail before live model calls when:

- A role-based prompt file has unassigned content outside role sections.
- A role heading is malformed or has an empty role label.
- A placeholder has malformed brace syntax.
- A placeholder references a non-`dataset.*` namespace.
- A `dataset.*` placeholder references a column missing from the selected
  dataset.
- The selected provider cannot send one or more configured role labels exactly.
