# Data Model: Shared Run Item Execution

## Run Item Execution Plan

Represents the information needed to execute one dataset item through the shared path.

**Fields**

- `run_id`: Unique run identifier for the current baseline or candidate run.
- `run_type`: Either baseline or candidate.
- `run_name`: User-visible Langfuse run name.
- `model_config`: Model configuration used for provider invocation.
- `provider`: Provider selected for the model configuration.
- `prompt_ref`: Prompt reference used to render the item prompt.
- `dataset_sync`: Resolved dataset identity and compatibility information.
- `fingerprint`: Baseline compatibility fingerprint for the project/dataset/evaluator set.
- `baseline_anchor`: Session identity anchor; the new baseline run id for baseline runs and the resolved baseline run id for candidate runs.
- `baseline_reference`: Present for candidate runs and absent for baseline runs.
- `parameter_hash`: Candidate parameter hash when needed for candidate metadata.
- `evaluator_payload_kind`: Baseline or candidate payload behavior.

**Validation Rules**

- Candidate plans must include a resolved baseline reference before any item execution starts.
- Baseline plans must not require a pre-existing baseline reference.
- Prompt reference, dataset identity, run id, run type, model config, and provider must be available before item execution.
- Existing command inputs and project configuration shape must not change.

## Run Item Execution Result

Represents the outcome of executing one dataset item through the shared path.

**Fields**

- `item_id`: Dataset item identity.
- `trace_id`: Trace identity created for the item.
- `trace_name`: User-visible trace name.
- `session_id`: Item comparison session identity.
- `rendered_prompt`: Prompt payload used for provider invocation.
- `response`: Provider response when execution succeeds.
- `error`: Redacted failure information when execution fails.
- `retry_count`: Provider retry count when available.
- `completed`: True when provider invocation succeeds.
- `failed`: True when provider invocation fails or prompt validation fails.
- `trace_metadata`: Metadata logged with the item trace.
- `dataset_run_item_recorded`: Whether recording was attempted with available item and trace identity.

**Validation Rules**

- Success results must include provider output.
- Failure results must include error information and preserve trace/session/prompt evidence when prepared.
- Dataset run item linkage must be attempted for success and failure results whenever item identity and trace identity exist.
- Langfuse warnings remain represented by existing gateway warning aggregation, not by a new result channel.

## Run Item Evidence

Represents the user-visible evidence produced for one item.

**Fields**

- Trace identity and trace name.
- Run identity and run type.
- Dataset name, version, compatibility version, and item identity.
- Prompt identity, prompt version, prompt shape, prompt roles, and rendered prompt details.
- Session identity and session input metadata.
- Model/provider identity, parameters, latency, tokens, cost, retry count, and output when available.
- Baseline reference and candidate identity fields where applicable.
- Observation role and live observation linkage marker where applicable.
- Redacted error details when execution fails.

**Relationships**

- One run item execution result produces one trace payload.
- One result may produce one dataset run item record.
- One successful result may produce one evaluator payload.
- Candidate item evidence references one compatible baseline reference.

## Baseline Evaluator Payload

Represents evaluator input for a successful baseline item.

**Fields**

- Run id, trace id, item id, input, output, ground truth.
- Evaluator names and versions.
- Score configuration reference for managed or externally configured scores.

**Validation Rules**

- Must preserve current baseline evaluator payload shape.
- Must be produced only after successful baseline provider invocation.

## Candidate Evaluator Payload

Represents evaluator input for a successful candidate item.

**Fields**

- Run id, trace id, item id, input, output, baseline output, ground truth.
- Baseline reference.
- Prompt identity, baseline prompt identity, candidate prompt identity.
- Parameter identity, generation parameter hash, variant identity.
- Evaluator names and versions.

**Validation Rules**

- Must preserve current candidate evaluator payload shape.
- Must be produced only after successful candidate provider invocation.
- Must include baseline output resolved from the compatible baseline run.

## State Transitions

```text
planned -> prepared -> invoked -> recorded -> summarized
planned -> prepared -> failed -> recorded -> summarized
```

- `planned`: Run-level setup has selected provider, prompt, dataset identity, and baseline context.
- `prepared`: Item trace id, trace name, rendered prompt, request metadata, and session identity are available.
- `invoked`: Provider returned a successful response.
- `failed`: Prompt validation or provider invocation failed after preparation.
- `recorded`: Trace logging and dataset run item recording have been attempted.
- `summarized`: Run completed/failed counts and warnings are reflected in the run result.
