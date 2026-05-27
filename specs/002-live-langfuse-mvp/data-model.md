# Data Model: Live Langfuse MVP

## LiveLangfuseWorkspace

Represents the configured Langfuse project/workspace.

**Fields**:

- `host`: Langfuse host URL from `LANGFUSE_HOST`, with
  `LANGFUSE_BASE_URL` accepted as a compatibility alias
- `public_key`: public API key
- `secret_key`: secret API key
- `project_id`: optional project/workspace identifier if exposed by Langfuse
- `verified_at`: timestamp when connectivity was verified

**Validation rules**:

- Credentials must be present for live commands.
- Workspace access must be verified before model execution.
- Secret values must never be logged, printed, or persisted to traces.

## LiveDataset

Represents the Langfuse Dataset used as the live system of record.

**Fields**:

- `name`: Langfuse dataset name
- `id`: Langfuse dataset ID when exposed by the SDK/API
- `version`: dataset version or version-equivalent returned by Langfuse
- `compatibility_version`: Langfuse dataset version when available, otherwise a
  deterministic content hash over stable dataset item IDs and input hashes
- `metadata`: project, source path, schema version, and sync timestamp
- `item_count`: number of active synced/resolved items

**Validation rules**:

- Live baseline and candidate runs require a resolved `name` and version.
- If Langfuse does not expose a usable version, `compatibility_version` is used
  for baseline matching and stable review cohort identity.
- Sync is idempotent by stable item identity.
- Duplicate local item IDs fail before Langfuse sync.
- Stable item identity is the basis for random human-review calibration cohorts.

## LiveDatasetItem

Represents one dataset item after local loading and live sync.

**Fields**:

- `item_id`: stable explicit ID or generated hash identity
- `langfuse_item_id`: Langfuse item ID when exposed
- `input`: required project input
- `ground_truth`: optional reference value
- `metadata`: optional source row, tags, notes, and input hash

**Validation rules**:

- `input` is required and non-empty.
- `ground_truth` is optional and must be represented as unavailable when absent.
- Provider/model identity must not be included in blind evaluator payloads.
- Item identity must remain stable across baseline and compatible candidate
  runs for trace correlation, comparison, and human-review cohort selection.

## LiveRunRecord

Represents one live baseline or candidate execution command.

**Fields**:

- `run_id`: harness-generated run ID
- `langfuse_run_name`: dataset run or experiment name
- `run_type`: `baseline` or `candidate`
- `project_name`
- `project_version`
- `dataset_name`
- `dataset_version`
- `dataset_compatibility_version`
- `prompt_version`
- `evaluator_set_id`
- `model_config_name`
- `provider`
- `model`
- `parameters_hash`
- `started_at`
- `completed_at`
- `status`: `completed`, `partial`, or `failed`
- `baseline_reference`: required for candidate, present for baseline after
  creation
- `item_counts`: completed, failed, and total

**Validation rules**:

- Every baseline or candidate execution creates a distinct live run.
- Candidate runs require a compatible `baseline_reference` before any
  candidate output is generated.
- Run metadata must be written to Langfuse even when some item executions fail.

## PersistedBaselineReference

Identifies a reusable baseline stored in Langfuse.

**Fields**:

- `baseline_run_id`
- `langfuse_run_name`
- `project_name`
- `project_version`
- `dataset_name`
- `dataset_version`
- `dataset_compatibility_version`
- `prompt_version`
- `evaluator_set_id`
- `baseline_model_config_name`
- `baseline_provider`
- `baseline_model`
- `baseline_parameters_hash`
- `created_at`

**Compatibility rules**:

- `latest-compatible` may resolve only when all compatibility fields match the
  current project and candidate request.
- Explicit baseline IDs must also pass compatibility checks.
- If no compatible baseline exists, candidate execution fails before any
  candidate provider or dry-run generation.

## CompatibilityFingerprint

Canonical hash input used for baseline matching.

**Fields**:

- `project_name`
- `project_version`
- `dataset_name`
- `dataset_version`
- `prompt_version`
- `evaluator_set_id`
- `baseline_model_config_name`
- `baseline_model`
- `baseline_parameters_hash`

**Validation rules**:

- Field ordering must be deterministic.
- `dataset_compatibility_version` uses the Langfuse dataset version when
  available, otherwise the deterministic dataset content hash.
- Secrets and credential references are excluded.
- Candidate-only model settings are excluded from baseline compatibility.

## LiveTraceRecord

Represents item-level execution persisted to Langfuse.

**Fields**:

- `trace_id`
- `run_id`
- `dataset_item_id`
- `langfuse_dataset_item_id`: Langfuse item ID when exposed by SDK/API
- `dataset_run_item_id`: Langfuse dataset run item ID when exposed by SDK/API
- `item_id`
- `input`
- `output`: nullable when item failed
- `ground_truth`: optional
- `provider`
- `model`
- `model_config_name`
- `parameters`
- `prompt_version`
- `evaluator_set_id`
- `baseline_reference`: optional for baseline, required for candidate
- `latency_ms`: nullable
- `input_tokens`: nullable
- `output_tokens`: nullable
- `cost_usd`: nullable
- `error`: nullable failure context
- `timestamp`

**Validation rules**:

- Traces must include enough metadata for Langfuse filtering and comparison.
- Traces should be linked through Langfuse Dataset experiment/run mechanisms
  when available. If a lower-level trace path is required, the harness must
  persist equivalent dataset item identity metadata.
- Missing token/cost values must be explicit nulls or omitted only when the
  Langfuse SDK cannot store null values.
- Secrets must be redacted.

## StableReviewCohort

Represents the deterministic random calibration sample shared by baseline and
compatible candidate runs.

**Fields**:

- `cohort_id`: deterministic ID from project, dataset, dataset version, and
  review policy version
- `project_name`
- `dataset_name`
- `dataset_version`
- `review_policy_version`: explicit or derived from review policy fields
- `minimum_sample_percent`
- `seed_material`: non-secret canonical string used to seed deterministic
  sampling
- `selected_item_ids`: ordered list of stable dataset item IDs
- `created_at`: timestamp when materialized or first used

**Validation rules**:

- Selection is based on stable dataset item IDs, not trace IDs or run order.
- Baseline and compatible candidate runs with the same dataset version and
  review policy must resolve the same `selected_item_ids`.
- Dataset version or review policy changes intentionally produce a different
  cohort.
- Run-specific risk review items are additive and must not replace the stable
  random calibration cohort.

## ScoreConfigSyncRecord

Represents a Langfuse score config required by one evaluator.

**Fields**:

- `evaluator_name`
- `score_name`: logical unprefixed name
- `managed_by_harness`
- `managed_name`: prefixed Langfuse score config name when managed
- `langfuse_score_config_id`
- `data_type`
- `bounds`: numeric min/max when applicable
- `categories`: categorical values when applicable
- `status`: `created`, `reused`, `user_owned`, or `incompatible`

**Validation rules**:

- Managed names must use the project `score_config_prefix`.
- Missing managed configs may be created.
- Existing compatible managed configs are reused.
- Existing incompatible managed configs fail sync and require manual deletion
  or rename in Langfuse before resync.
- User-owned score configs are never created, updated, archived, or deleted by
  the harness.

## AnnotationQueueRoute

Represents one selected manual-review item routed to an existing Langfuse
Annotation Queue.

**Fields**:

- `queue_id`
- `run_id`
- `trace_id`
- `dataset_item_id`
- `input`
- `baseline_output`: optional
- `candidate_output`: optional
- `ground_truth`: optional
- `selection_reason`
- `selection_bucket`: `stable_calibration` or `run_risk`
- `dedupe_key`
- `queued_at`

**Validation rules**:

- Queue routing requires a configured existing queue ID.
- Duplicate queue items for the same queue, run, and trace are skipped.
- Stable calibration queue items must be selected by dataset item ID so
  baseline and compatible candidate runs route the same item IDs when both are
  routed for review.
- Review payloads must preserve blind-evaluator boundaries by not exposing
  provider/vendor identity as judge input.

## LiveSmokeRun

Represents an opt-in live integration test execution.

**Fields**:

- `test_run_id`
- `langfuse_dataset_name`
- `baseline_run_id`
- `candidate_run_id`
- `review_route_id`: optional annotation queue routing identifier when a live
  queue is configured
- `export_path`: optional CSV export path
- `azure_model`
- `started_at`
- `completed_at`
- `status`

**Validation rules**:

- Live tests require explicit `pytest -m live` execution.
- Tests skip when required environment variables are missing.
- Test datasets must be small and safe to re-run.
