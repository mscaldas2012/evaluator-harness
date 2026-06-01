# Data Model: Sync Langfuse Prompts

## PromptArtifact

Represents one local prompt declared by a project configuration.

Fields:

- `project`: project name.
- `project_version`: project version.
- `artifact_type`: `task` or `evaluator`.
- `artifact_name`: task prompt name or evaluator name.
- `artifact_version`: configured prompt version.
- `local_path`: repository-relative prompt file path.
- `prompt_shape`: `text` or `chat`.
- `roles`: ordered role labels for chat prompts, empty for text prompts.
- `content_identity`: stable hash of normalized content, prompt shape, and
  roles.
- `managed_name`: stable Langfuse prompt name.
- `labels`: labels to apply to the synced Langfuse prompt version.
- `tags`: tags to apply to the synced Langfuse prompt.

Validation rules:

- `managed_name` must be slug-safe and unique within a project sync run.
- `artifact_version` must be present.
- `local_path` must exist and parse successfully.
- `prompt_shape` must match parsed content.
- `content_identity` must change when prompt text, role order, or role content
  changes.

Relationships:

- A project has one task `PromptArtifact`.
- A project has zero or more evaluator `PromptArtifact` records.
- A `PromptArtifact` may have zero or one matching `PromptBindingRecord`.

## PromptBindingRecord

Represents a local last-known reference to a harness-managed Langfuse prompt
version.

Fields:

- `project`: project name.
- `project_version`: project version.
- `artifact_type`: `task` or `evaluator`.
- `artifact_name`: task prompt name or evaluator name.
- `artifact_version`: configured prompt version.
- `managed_name`: Langfuse prompt name.
- `langfuse_prompt_version`: numeric Langfuse prompt version when available.
- `langfuse_labels`: labels assigned to the Langfuse prompt version.
- `content_identity`: content identity that was synced.
- `prompt_shape`: `text` or `chat`.
- `roles`: ordered role labels for chat prompts.
- `active`: whether this binding is the current harness-managed reference.
- `last_synced_at`: timestamp of the last successful sync.

Validation rules:

- A binding must match exactly one `PromptArtifact` key.
- A binding with the same artifact key but different content identity indicates
  a version conflict unless the configured prompt version has changed.
- Bindings are advisory for local metadata enrichment; missing bindings must not
  block runs.

State transitions:

- `missing` -> `created`: remote prompt version is created and binding written.
- `created` or `reused` -> `reused`: local content identity still matches.
- `created` or `reused` -> `conflict`: same configured version points to
  different content.
- `active` -> `inactive`: superseded by a newer configured prompt version for
  the same artifact.

## PromptSyncStatus

Represents one prompt's dry-run or sync outcome.

Fields:

- `artifact`: prompt artifact key.
- `operation`: `create`, `reuse`, `skip`, `conflict`, or `fail`.
- `status`: `created`, `reused`, `changed`, `skipped`, `conflict`, or `failed`.
- `managed_name`: Langfuse prompt name.
- `content_identity`: local content identity.
- `langfuse_prompt_version`: remote prompt version when known.
- `message`: user-facing summary.
- `remediation`: optional user action.

Validation rules:

- Audit mode must not produce `created`.
- Conflict and failed statuses must include remediation.
- Reused status requires matching content identity.

## PromptSyncReport

Represents the result of auditing or syncing all project prompt artifacts.

Fields:

- `project`: project name.
- `project_version`: project version.
- `mode`: `dry-run` or `apply`.
- `binding_path`: prompt binding file path.
- `total_count`: number of prompt artifacts considered.
- `created_count`: count of created prompt versions.
- `reused_count`: count of reused prompt versions.
- `conflict_count`: count of conflicts.
- `failed_count`: count of failures.
- `items`: list of `PromptSyncStatus`.

Validation rules:

- `total_count` equals the length of `items`.
- Apply mode should write bindings only for successful created/reused outcomes.
- Any conflict or failure makes the overall status non-success.

## PromptProvenanceMetadata

Metadata attached to traces and exported reports.

Fields:

- `prompt_artifact_type`
- `prompt_artifact_name`
- `prompt_local_path`
- `prompt_version`
- `prompt_shape`
- `prompt_roles`
- `prompt_content_identity`
- `langfuse_prompt_name` when known.
- `langfuse_prompt_version` when known.
- `langfuse_prompt_labels` when known.

Validation rules:

- Local prompt identity fields are required for new runs.
- Langfuse prompt fields are optional and may be absent when prompts were not
  synced.
