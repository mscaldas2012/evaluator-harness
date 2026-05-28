# Data Model: Langfuse Judge Setup

## Evaluator Setup Defaults

Project-level setup defaults shared by evaluator definitions.

Fields:

- `default_judge_model`: Optional Langfuse judge model identifier.
- `default_llm_connection`: Optional Langfuse LLM connection identifier.
- `binding_path`: Optional path for local evaluator binding records. Default:
  `configs/langfuse/evaluator_bindings/<project-slug>.yaml`.
- `default_sampling_percent`: Optional percentage. If omitted, effective
  sampling is 100.
- `historical_backfill`: Optional project default. If omitted, false.

Validation:

- At least one of project-level or evaluator-level judge model/connection must
  be available before apply.
- Binding path must remain within the repository and must not contain secrets.

## Evaluator Setup Definition

Project-owned setup contract for one Langfuse LLM-as-Judge evaluator.

Fields:

- `name`: Stable evaluator name, e.g. `clarity`.
- `version`: Evaluator version, e.g. `v2`.
- `dimension`: One quality dimension measured by the evaluator.
- `source_type`: `catalog`, `custom`, or `user_owned`.
- `catalog_ref`: Required when `source_type=catalog`.
- `prompt_path`: Required when `source_type=custom`.
- `prompt_version`: Required when `source_type=custom`.
- `target`: `observation`, `trace`, or `experiment`.
- `target_observation_role`: Required for observation target; default
  `model_output`.
- `run_types`: `baseline`, `candidate`, or both.
- `score`: Canonical score config reference.
- `variables`: Variable mappings expected by the evaluator.
- `required_inputs`: Inputs that must be available before apply.
- `filter_profile`: Project-scoped Langfuse filter profile.
- `judge_model`: Optional evaluator-level judge model override.
- `llm_connection`: Optional evaluator-level connection override.
- `sampling_percent`: Optional evaluator-level sampling override.
- `historical_backfill`: Optional evaluator-level backfill opt-in.
- `managed_display_name`: Optional valid managed display name override.

Validation:

- Catalog evaluators require `catalog_ref`.
- Custom evaluators require prompt path, prompt version, and result contract.
- User-owned evaluators require a remote evaluator reference and are
  validate-only.
- Target filters must include project identity and must not match all harness
  projects by default.
- Score target must align with Human Annotation Queue score config for the same
  dimension.

## Managed Evaluator Name

Deterministic display name used for harness-managed evaluator resources.

Format:

```text
EH_<project-slug>_<project-version>_judge_<dimension>_<evaluator-version>_<source-type>_<target-type>
```

Validation:

- Slug-safe ASCII only.
- Source type is `catalog` or `custom`.
- Target type is `observation`, `trace`, or `experiment`.
- Must not encode score source such as human or automated judge.

## Evaluator Binding Record

Local non-secret repository state proving the harness created or updated a
remote evaluator.

Fields:

- `project`: Project slug.
- `project_version`: Project version.
- `evaluator_name`: Evaluator name.
- `evaluator_version`: Evaluator version.
- `source_type`: Catalog or custom.
- `target`: Observation, trace, or experiment.
- `langfuse_evaluator_id`: Remote evaluator ID.
- `langfuse_display_name`: Remote display name at last successful apply.
- `score_config_id`: Canonical score config ID.
- `score_config_name`: Canonical score config name.
- `judge_model`: Effective judge model, if configured.
- `llm_connection`: Effective LLM connection, if configured.
- `sampling_percent`: Effective sampling percent.
- `historical_backfill`: Effective backfill policy.
- `active`: Last known activation state.
- `last_synced_at`: Timestamp from the apply operation.

Validation:

- Must not store API keys, secret keys, provider credentials, or prompt
  contents.
- Update/inactivation requires a matching binding and a remote compatibility
  check.
- Remote display name alone is not ownership proof.

## Evaluator Setup Plan

Previewable planned operation for one evaluator.

Fields:

- `operation`: `create`, `reuse`, `update`, `inactivate`, `skip`, `block`, or
  `fail`.
- `reason`: Human-readable reason.
- `evaluator_identity`: Project evaluator identity.
- `remote_evaluator_id`: Optional remote ID.
- `managed_display_name`: Expected display name.
- `source_type`: Catalog, custom, or user-owned.
- `target`: Observation, trace, or experiment.
- `filters`: Effective filter profile.
- `variables`: Effective variable mappings.
- `score_target`: Score config name and ID.
- `judge_model_or_connection`: Effective judge model/connection.
- `sampling_policy`: Effective sampling.
- `backfill_policy`: Disabled, enabled, unsupported, or not applicable.
- `binding_status`: Present, missing, created, refreshed, or not applicable.
- `changes`: Operational fields to update, if any.
- `remediation`: Required user action when blocked or failed.

State transitions:

- Missing compatible remote -> `create`.
- Compatible remote + binding -> `reuse`.
- Harness-managed remote + update-safe diff -> `update`.
- New evaluator version + older harness-managed active binding -> `inactivate`
  older version where supported.
- User-owned or unbound remote requiring mutation -> `block`.
- Unsupported Langfuse operation requested -> `block`.
- Runtime service failure -> `fail`.

## Setup Result

Aggregate result for preview, apply, or audit.

Fields:

- `mode`: `preview`, `apply`, or `audit`.
- `overall_status`: `success`, `partial_success`, or `failure`.
- `project`: Project identity.
- `evaluators`: List of evaluator setup plans/results.
- `binding_path`: Local binding path.
- `warnings`: Non-blocking warnings.

Rules:

- Apply is per-evaluator, not transactional.
- Successful evaluator changes remain after partial failure.
- No rollback or deletes are attempted.
