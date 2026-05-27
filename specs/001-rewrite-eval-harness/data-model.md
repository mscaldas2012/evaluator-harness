# Data Model: Lightweight Langfuse Evaluation Harness

## EvaluationProject

Represents one reusable evaluation use case.

**Fields**:

- `name`: unique project slug, e.g. `rewrite-quality`
- `description`: human-readable purpose
- `version`: project config version
- `score_config_prefix`: project-specific prefix for score configs created by
  the harness
- `dataset`: `DatasetSource`
- `task_prompt`: `PromptRef`
- `baseline`: `ModelConfig`
- `candidates`: list of `ModelConfig`
- `evaluators`: list of `EvaluatorDefinition`
- `human_review`: optional `HumanReviewPolicy`
- `metadata`: free-form project metadata

**Validation rules**:

- Must include one dataset, one baseline, at least one candidate, and at least
  one evaluator.
- `name` must be stable across runs because it participates in baseline
  compatibility.
- `score_config_prefix` must be non-empty, slug-safe using only ASCII letters,
  numbers, `_`, and `-`, project-specific, end with `_` or `-`, and leave enough
  name length budget for evaluator score names. The prefix must be no more than
  64 characters, and the derived managed score config name should be no more
  than 128 characters unless Langfuse documents a different limit.
- Future projects must not require code changes when they only change dataset,
  prompts, evaluators, or model configs.

## DatasetSource

Represents a local or Langfuse-hosted project dataset.

**Fields**:

- `kind`: `local_csv`, `local_json`, or `langfuse`
- `path`: local path when `kind` is local
- `langfuse_dataset_name`: required after sync/resolve
- `langfuse_dataset_id`: optional if SDK exposes it
- `langfuse_dataset_version`: required for valid experiment execution
- `item_id_strategy`: `explicit_or_hash`
- `metadata`: optional dataset metadata

**Validation rules**:

- Local datasets must include `input`.
- Explicit item IDs must be unique.
- Missing item IDs generate a stable ID from row position plus input hash.
- Valid baseline/candidate runs must record Langfuse dataset identity and
  version.

## DatasetItem

Represents one project input.

**Fields**:

- `item_id`: explicit ID or generated stable ID
- `input`: required input text/object
- `metadata`: optional item-level metadata
- `reference_output`: optional expected/reference output
- `ground_truth`: optional project-defined reference value used by baseline or
  candidate evaluators
- `source_row`: local row index when authored locally
- `input_hash`: hash of input used for generated identity and drift detection

**Validation rules**:

- Empty `input` values are invalid.
- Duplicate explicit IDs fail dataset validation.
- Missing `ground_truth` values are valid and must be represented explicitly as
  unavailable when evaluator payloads include the variable.

## PromptRef

Represents the task prompt used for model generation.

**Fields**:

- `path`: local prompt file path
- `version`: prompt version string
- `template_variables`: expected variables, including `input`
- `metadata`: optional prompt metadata

**Validation rules**:

- Version is required.
- Template must support all variables required by the project dataset.

## EvaluatorDefinition

Represents a project-scoped evaluator.

**Fields**:

- `name`: evaluator slug, e.g. `clarity`
- `type`: `llm_as_judge` or `deterministic`
- `version`: evaluator version string
- `prompt_path`: required for LLM-as-a-Judge evaluators
- `score`: `ScoreConfigRef`
- `modes`: supported evaluator modes, containing `baseline`, `candidate`, or
  both
- `variables`: expected evaluator variables
- `blind`: whether provider/model identity must be hidden from judge prompt

**Validation rules**:

- Version is required.
- At least one evaluator mode is required.
- LLM-as-a-Judge evaluator prompts must evaluate one dimension only.
- Baseline-mode evaluators receive `input`, baseline `output`, optional
  `ground_truth`, and trace context.
- Candidate-mode evaluators receive `input`, candidate `output`, optional
  `baseline_output`, optional `ground_truth`, and trace context.
- Blind evaluators must not receive provider or model names.
- Evaluator score configs created by the harness must use the project score
  prefix and must not be modified by the harness after creation.

## ScoreConfigRef

Represents the Langfuse score config contract required by an evaluator.

**Fields**:

- `name`: unprefixed logical score name, e.g. `clarity`
- `managed_name`: prefixed Langfuse score config name created or resolved by the
  harness, e.g. `eh_rewrite_quality_clarity`
- `data_type`: `NUMERIC`, `CATEGORICAL`, `BOOLEAN`, or `TEXT`
- `min_value`: optional numeric lower bound
- `max_value`: optional numeric upper bound
- `categories`: optional list for categorical scores
- `description`: optional score config description
- `langfuse_score_config_id`: optional resolved Langfuse score config ID
- `managed_by_harness`: boolean, true only for score config schemas the harness
  is allowed to create or resolve. Langfuse still owns score results.

**Validation rules**:

- Harness-managed score config names must start with the configured project
  score prefix.
- The managed Langfuse name is derived from `score_config_prefix` plus `name`.
- Missing harness-managed score configs may be created by the harness.
- Existing compatible harness-managed score configs may be reused.
- Compatibility compares score name, data type, numeric min/max bounds,
  categorical labels/values, boolean/text constraints exposed by Langfuse, and
  archived status. Description differences are reported but do not fail sync.
- Existing incompatible score configs must fail sync with remediation guidance.
- Archived same-name configs are treated as conflicting unless the Langfuse API
  no longer returns or reserves that score config name.
- Score configs with `managed_by_harness: false` are user-owned Langfuse
  configuration. The harness may validate or reference them by ID/name, but must
  not create, update, archive, or delete them.
- The harness must not update, archive, or delete score configs. Users must
  manually delete or rename incompatible configs in Langfuse before resyncing;
  archiving alone is sufficient only if Langfuse no longer treats the name as
  conflicting.

## ModelConfig

Represents a baseline or candidate model configuration.

**Fields**:

- `name`: stable config name
- `role`: `baseline` or `candidate`
- `provider`: `openai_compatible` or `ollama` for MVP
- `auth_mode`: `azure_client_credentials`, `api_key`, or `none`
- `model`: provider model identifier
- `parameters`: generation settings such as temperature, top_p, max_tokens,
  seed
- `endpoint`: optional endpoint reference
- `azure`: optional Azure OpenAI settings when `auth_mode` is
  `azure_client_credentials`
- `metadata`: optional runtime metadata such as hardware

**Validation rules**:

- Baseline and candidates must declare generation parameters explicitly.
- Candidate parameter variants should use distinct names.
- Project configs do not expose tracing strategy. Provider adapters must select
  the best tracing strategy internally, preferring Langfuse-supported SDK
  integrations, instrumented clients, or compatible provider APIs when they can
  capture required generation metadata.
- Manual tracing fallback is allowed only inside provider adapters when no
  compatible Langfuse integration exists or when the integration cannot capture
  required metadata. The provider adapter must document the fallback reason in
  code and expose it through diagnostics or trace metadata when useful.
- The first OpenAI-compatible provider must support Azure OpenAI with Azure AD
  client-credentials authentication and APIM subscription-key headers.
- Project configs must store only environment variable names or secret reference
  names for provider credentials. Azure credential values must come from `.env`,
  the host environment, or a secret manager and must never be committed, logged
  to Langfuse traces, or printed in local output.
- Providers beyond OpenAI-compatible APIs and Ollama are future adapters unless
  routed through OpenAI-compatible behavior.

## Run

Represents one execution pass over a project dataset.

**Fields**:

- `run_id`: local generated run identity
- `langfuse_run_name`: Langfuse dataset run/experiment name
- `project_name`
- `project_version`
- `run_type`: `baseline` or `candidate`
- `model_config_name`
- `dataset_name`
- `dataset_version`
- `prompt_version`
- `evaluator_set_id`
- `baseline_reference`: optional for baseline, required for candidate
- `started_at`
- `completed_at`
- `status`: `pending`, `running`, `completed`, `failed`
- `metadata`

**Validation rules**:

- Candidate runs require a compatible baseline reference.
- Runs fail fast if Langfuse is unreachable.
- Run metadata must include reproducibility fields before execution starts.

## BaselineReference

Identifies a reusable baseline.

**Fields**:

- `baseline_run_id`
- `langfuse_run_name`
- `project_name`
- `project_version`
- `dataset_name`
- `dataset_version`
- `prompt_version`
- `evaluator_set_id`
- `baseline_model`
- `baseline_parameters_hash`
- `created_at`

**Compatibility rules**:

- Candidate runs may reuse a baseline only when all compatibility fields match.
- If compatibility fails, the harness must require a new baseline or explicit
  compatible baseline selection.

## OutputRecord

Represents one model output for one dataset item.

**Fields**:

- `run_id`
- `item_id`
- `trace_id`
- `observation_id`: optional
- `output`
- `provider`
- `model`
- `parameters`
- `latency_ms`
- `input_tokens`: nullable
- `output_tokens`: nullable
- `cost_usd`: nullable
- `timestamp`
- `baseline_reference`
- `error`: optional error information

**Validation rules**:

- Missing token/cost metadata must be explicit, not silently omitted.
- Output records must be linked to Langfuse trace context.

## HumanReviewPolicy

Represents project review selection.

**Fields**:

- `minimum_sample_percent`: default `5`
- `prioritize`: ordered list, default failures, low confidence, disputed
- `annotation_queue_id`: optional existing Langfuse queue
- `enabled`: boolean

**Validation rules**:

- At least 5% of evaluated outputs must be selected when automated evaluations
  are used.
- Configured queue routing requires `annotation_queue_id` for MVP.

## HumanReviewSelection

Represents one selected review item.

**Fields**:

- `item_id`
- `run_id`
- `trace_id`
- `selection_reason`: `failure`, `low_confidence`, `disputed`, or `sample`
- `annotation_queue_id`: optional
- `queued`: boolean

**Validation rules**:

- Selected items must include enough Langfuse context for manual review.
- Duplicate queue items should be avoided when queue integration is enabled.
