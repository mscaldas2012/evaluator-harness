# CLI Contract: Create Annotation Queues

## Command: `sync-annotation-queue`

```powershell
uv run python run_experiment.py sync-annotation-queue `
  --project configs/projects/rewrite_quality.yaml
```

**Purpose**: Create, reuse, or resolve the human annotation queue for a project.

**Preconditions**:

- Project config is valid.
- Langfuse credentials are configured for live sync.
- Score configs for project evaluators have been synced or can be resolved.

**Successful output fields**:

- `project`
- `review_policy_version`
- `queue_name`
- `queue_id`
- `ownership`
- `status`
- `score_config_ids`
- `reference_path`

Managed queue name convention:

```text
EH_<project-slug>_<project-version>_review_<review-policy-version>
```

Managed queue reference path convention:

```text
.evaluator-harness/queue-references/<project-slug>__<project-version>__<review-policy-version>.json
```

**Statuses**:

- `created`: managed queue was created
- `reused`: compatible managed queue already existed or local reference was
  resolved
- `user_owned`: project points to an existing user-owned queue
- `environment_override`: environment queue ID was used intentionally
- `skipped`: human review is disabled

**Failure cases**:

- Missing Langfuse credentials
- Missing score config IDs for managed queue creation
- Langfuse queue creation unsupported or unauthorized
- Existing local reference incompatible with current project review policy
- User-owned queue ID missing or inaccessible

## Command: `select-review`

```powershell
uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

**Queue resolution order**:

1. Explicit project user-owned queue ID
2. `LANGFUSE_ANNOTATION_QUEUE_ID` when fallback override is enabled
3. Compatible local managed queue reference
4. Automatic managed queue sync
5. Failure with manual fallback message

**Successful output fields**:

- `run_id`
- `selected_count`
- `queued_count`
- `skipped_duplicate_count`
- `queue_id`
- `queue_ownership`

## Command: `validate`

`validate` must report invalid human review queue policies, including:

- `user_owned` without `annotation_queue_id`
- unsupported queue ownership value
- invalid queue name
- disabled review with conflicting required queue fields should warn but not
  block unrelated experiment validation
