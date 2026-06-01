# Contract: Prompt Binding File

## Path

```text
configs/langfuse/prompt_bindings/<project>.yaml
```

## Purpose

The prompt binding file records last-known Langfuse prompt references for
harness-managed prompt artifacts. It is optional local state used for audit,
conflict detection, and prompt provenance metadata enrichment. Missing binding
files must not block validation or runs.

## Shape

```yaml
bindings:
  - project: dfe
    project_version: v1
    artifact_type: task
    artifact_name: task_prompt
    artifact_version: v1
    managed_name: EH_dfe_v1_prompt_task_task_prompt_v1
    langfuse_prompt_version: 3
    langfuse_labels:
      - dfe
      - v1
      - task
      - prompt-v1
    content_identity: sha256:...
    prompt_shape: chat
    roles:
      - system
      - user
    active: true
    last_synced_at: "2026-06-01T12:00:00+00:00"
```

## Required Fields

- `project`
- `project_version`
- `artifact_type`
- `artifact_name`
- `artifact_version`
- `managed_name`
- `content_identity`
- `prompt_shape`
- `active`
- `last_synced_at`

## Optional Fields

- `langfuse_prompt_version`
- `langfuse_labels`
- `roles`

## Validation Rules

- `artifact_type` must be `task` or `evaluator`.
- `prompt_shape` must be `text` or `chat`.
- `managed_name` must be slug-safe ASCII.
- Active bindings must be unique by project, project version, artifact type,
  artifact name, and artifact version.
- A binding with matching artifact key and different content identity is a
  conflict unless the configured prompt version has changed.
- Bindings without matching current prompt artifacts are retained but ignored by
  sync unless superseded by a newer artifact version.
