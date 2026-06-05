# Data Model: Model Output Observation Targeting

## FinalModelOutputObservation

Represents the single observation per completed dataset item run that standard
content-quality evaluators should judge.

**Fields**

- `trace_id`: Stable Langfuse trace identifier for the dataset item run.
- `observation_id`: Langfuse observation identifier when available.
- `observation_role`: Must be `model_output`.
- `run_id`: Baseline or candidate run identifier.
- `run_type`: Baseline or candidate.
- `project`: Project slug.
- `project_version`: Project version.
- `scenario`: Optional scenario metadata when configured.
- `dataset_item_id`: Dataset item identifier.
- `prompt_identity`: Prompt version/content identity metadata.
- `provider`: Provider name.
- `model`: Model name.
- `output`: Final model output to evaluate.

**Validation Rules**

- Exactly one final model output observation should exist per completed dataset
  item run for standard evaluator targeting.
- The observation must include enough project/run metadata for evaluator
  filters and trace review.
- Failed runs may omit the final output but should still log failure metadata.

## ParentContainerObservation

Represents trace organization around a dataset item run. It may contain the
prompt, input, trace metadata, and child observations, but it is not itself the
final output to judge.

**Fields**

- `trace_id`
- `observation_id`
- `observation_role`: Must not be `model_output`; recommended role is
  `run_item` or another explicit non-final role.
- `project`
- `project_version`
- `run_id`
- `run_type`
- `dataset_item_id`

**Validation Rules**

- Must not match standard model-output evaluator filters.
- Should preserve trace organization and reproducibility metadata.

## ProviderTracingContract

Defines what each provider adapter must guarantee for evaluator targeting.

**Fields**

- `provider_name`: Provider adapter identity.
- `tracing_strategy`: Harness-managed, native Langfuse, dry-run/synthetic, or
  manual fallback.
- `final_output_role_supported`: Whether the provider can mark one final output
  observation with the standard role.
- `requires_explicit_observation_name`: Whether project configuration must name
  the final output observation.
- `known_limitations`: Human-readable limitations for validation/audit output.

**Validation Rules**

- Harness-managed tracing providers must produce one eligible final output
  observation and one or more non-final parent/container observations.
- Native Langfuse tracing providers must either propagate the standard role or
  declare the need for explicit targeting configuration.

## EvaluatorTargetingProfile

Represents evaluator filter intent for a project evaluator.

**Fields**

- `target`: Trace or observation.
- `observation_role`: Intended role for observation targets.
- `observation_name`: Optional explicit observation name for intentional
  non-standard targeting.
- `project`
- `project_version`
- `run_types`
- `evaluator_set_id`

**Validation Rules**

- Standard model-output evaluators should target observation role
  `model_output` without requiring provider-specific names.
- Explicit observation names remain allowed for intentional non-final or
  provider-specific targeting.

## TargetingDiagnostic

Represents a validation or audit finding about evaluator targeting.

**Fields**

- `status`: Aligned, duplicate, missing, provider-specific, or unknown.
- `trace_count_checked`: Number of traces considered when sample data is
  available.
- `expected_matches`: Expected final output count.
- `actual_matches`: Observed model-output eligible observations.
- `message`: Human-readable finding.
- `remediation`: Suggested next action.

**Validation Rules**

- Duplicate status must identify that more than one observation per trace can
  match standard model-output evaluators.
- Missing status must identify that no final output observation is eligible.
