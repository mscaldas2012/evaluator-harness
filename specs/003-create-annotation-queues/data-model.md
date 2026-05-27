# Data Model: Create Annotation Queues

## ReviewQueuePolicy

Represents how a project wants human annotation queues managed.

**Fields**:

- `enabled`: whether human review is active for the project
- `ownership`: `managed_by_harness` or `user_owned`
- `queue_name`: optional explicit display name for managed queues
- `annotation_queue_id`: optional existing queue ID for user-owned queues
- `review_policy_version`: explicit or derived version for stable cohort and
  queue reference identity
- `fallback_to_env`: whether `LANGFUSE_ANNOTATION_QUEUE_ID` may override local
  queue resolution for ad hoc runs

**Validation rules**:

- Disabled review requires no queue.
- User-owned queues require `annotation_queue_id`.
- Managed queues must derive a deterministic queue name when none is provided:
  `EH_<project-slug>_<project-version>_review_<review-policy-version>`.
- Generated and configured queue names must be slug-safe and may contain only
  letters, numbers, underscores, and hyphens.
- Queue policy values must not include secrets.

## AnnotationQueueReference

Represents the resolved queue used by a project.

**Fields**:

- `project_name`
- `project_version`
- `review_policy_version`
- `queue_id`
- `queue_name`
- `ownership`: `managed_by_harness`, `user_owned`, or `environment_override`
- `score_config_ids`
- `status`: `created`, `reused`, `resolved`, or `skipped`
- `created_at`: optional queue creation timestamp when known
- `synced_at`: timestamp for the latest local sync

**Validation rules**:

- Queue references must not contain Langfuse API keys or provider secrets.
- Managed references are compatible only when project identity, review policy
  version, and score config IDs match.
- Repeated syncs for the same compatible reference must not create duplicates.
- Incompatible existing references must fail with remediation instructions.

## AnnotationQueueReferenceStore

Represents the generated local state used to find queues across commands.

**Fields**:

- `path`: local generated reference path
- `schema_version`
- `references`: one or more annotation queue references

**Validation rules**:

- Store path lives under `.evaluator-harness/queue-references/`.
- Managed queue reference files use
  `<project-slug>__<project-version>__<review-policy-version>.json`.
- Files are local generated state and should be ignored by git.
- Writes must be atomic enough to avoid corrupting the reference on command
  failure.

## AnnotationQueueSyncResult

Represents the result printed by queue sync.

**Fields**:

- `queue_id`
- `queue_name`
- `ownership`
- `status`
- `score_config_ids`
- `message`
- `manual_fallback_reason`: optional reason when automation cannot create a
  queue

**Validation rules**:

- Successful managed sync returns a queue ID.
- Disabled review returns `skipped` without requiring credentials beyond normal
  project validation.
- Unsupported automation returns a clear fallback reason.

## AnnotationQueueItemRoute

Represents one selected review item routed to Langfuse.

**Fields**:

- `queue_id`
- `object_id`: trace ID or observation ID used by Langfuse queue item routing
- `object_type`
- `run_id`
- `trace_id`
- `dataset_item_id`
- `selection_reason`
- `selection_bucket`
- `status`: `queued`, `duplicate`, or `failed`

**Validation rules**:

- Duplicate route attempts for the same queue and trace should be skipped or
  reported as duplicate.
- Routed baseline and candidate items for the same compatible project use the
  same resolved queue.
- Blind evaluator boundaries are preserved in any companion metadata shown for
  review.
