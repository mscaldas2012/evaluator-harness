# Langfuse Live Persistence Contract

This contract defines what the harness must persist or resolve in Langfuse for
the live MVP.

## Connectivity Verification

Before any live model call, the harness must:

- instantiate a Langfuse client from environment settings
- verify credentials and workspace/project access with a low-cost API call
- fail with a non-zero exit code when verification fails
- avoid provider token acquisition and model calls on verification failure

## Dataset Sync

For local CSV/JSON datasets, the harness must create or resolve:

- Langfuse Dataset name from project config
- Langfuse Dataset metadata:
  - `harness_project_name`
  - `harness_project_version`
  - `source_kind`
  - `source_path`
  - `synced_by`
- Langfuse Dataset items with stable item IDs and input payloads
- optional expected output or metadata containing `ground_truth` when present
- stable item metadata needed to correlate future traces and review cohorts
- dataset compatibility version metadata derived from Langfuse dataset version
  or stable item IDs and input hashes when no version is exposed

Re-running sync with unchanged item IDs must be idempotent.

## Dataset Runs and Experiments

Each baseline or candidate command creates a new run with:

- unique `run_id`
- `run_type`: `baseline` or `candidate`
- `harness_project_name`
- `harness_project_version`
- `dataset_name`
- `dataset_version`
- `dataset_compatibility_version`
- `prompt_version`
- `evaluator_set_id`
- `model_config_name`
- `provider`
- `model`
- `parameters_hash`
- `compatibility_fingerprint`
- `started_at`
- `completed_at`
- `status`

Candidate runs additionally include:

- `baseline_run_id`
- `baseline_langfuse_run_name`
- `baseline_compatibility_fingerprint`

Dataset runs should be created through the Langfuse Dataset experiment/run
mechanism when available so each item execution can be linked to the
originating dataset item.

## Trace Metadata

Every item trace must include:

- `run_id`
- `run_type`
- `dataset_item_id`
- `langfuse_dataset_item_id` when exposed by the SDK/API
- `dataset_run_item_id` when exposed by the SDK/API
- `item_id`
- `harness_project_name`
- `harness_project_version`
- `dataset_name`
- `dataset_version`
- `dataset_compatibility_version`
- `prompt_version`
- `evaluator_set_id`
- `model_config_name`
- `provider`
- `model`
- `parameters`
- `latency_ms` when available
- `input_tokens` when available
- `output_tokens` when available
- `cost_usd` when available
- `baseline_run_id` for candidates
- `error` failure context when applicable

Trace input/output payloads may include:

- `input`
- `output`
- `ground_truth`
- `baseline_output` for candidate evaluator context when available

Trace payloads and metadata must not contain credential values.

When the Langfuse SDK experiment runner is used, trace-to-dataset-item linkage
should be provided by the SDK. If the harness must use lower-level tracing for a
provider path, it must store equivalent dataset item identity fields so runs can
still be correlated item by item.

## Baseline Reference Resolution

The harness resolves baselines by querying Langfuse records tagged or metadated
as harness baseline runs.

Resolution rules:

- `latest-compatible` selects the newest completed baseline matching the
  current compatibility fingerprint.
- explicit baseline run IDs must exist and match the compatibility fingerprint.
- partial or failed baseline runs are not reusable unless future requirements
  explicitly allow them.
- no local baseline registry file participates in resolution.

## Score Config Sync

For each evaluator score:

- if `managed_by_harness: true`, derive the Langfuse score config name from
  project prefix plus logical score name
- create the score config if missing
- reuse it if compatible
- fail if the same managed name exists with incompatible schema
- never update, delete, archive, or overwrite existing score configs
- never create or modify `managed_by_harness: false` score configs

Compatibility compares data type, numeric bounds, categorical values, boolean
or text constraints exposed by Langfuse, and archived status. Description
differences may be reported but must not fail sync.

## Annotation Queue Routing

When a project has `human_review.annotation_queue_id`:

- selected items are added to that existing Langfuse Annotation Queue
- queue creation is out of MVP scope
- the random calibration subset is deterministic by dataset item identity
- baseline and compatible candidate runs use the same random calibration item
  IDs when dataset version and review policy are unchanged
- run-specific risk items may be added separately for failures, low confidence,
  or disputed outputs
- payloads include source input, candidate output, baseline output when
  available, ground truth when available, selection reason, trace ID, and run ID
- duplicate queue items for the same queue, run, and trace are skipped

## Scores and Evaluators

Langfuse owns evaluator execution and score storage for the live MVP. The
harness may sync score configs and prepare evaluator-ready trace context, but it
does not implement local scoring or custom aggregate dashboards.

If future work adds direct score creation through the Langfuse SDK/API, it must
write only scores that the harness explicitly owns and must not overwrite
Langfuse-created evaluator or human annotation scores.
