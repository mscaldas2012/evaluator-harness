# Langfuse Evaluator Setup Contract

## Supported Evaluator Sources

### Catalog Evaluator

Harness config references a Langfuse managed/catalog evaluator.

Required setup fields:

- Catalog evaluator reference.
- Target type.
- Project-scoped filters.
- Variable mappings.
- Canonical score config.
- Effective judge model or LLM connection.
- Sampling policy.
- Historical backfill policy.

The harness does not own catalog prompt text.

### Custom Evaluator

Harness config defines a custom evaluator prompt and result contract.

Required setup fields:

- Prompt path and prompt version.
- Result contract compatible with the score config.
- Target type.
- Project-scoped filters.
- Variable mappings.
- Canonical score config.
- Effective judge model or LLM connection.
- Sampling policy.
- Historical backfill policy.

## Managed Display Name

Harness-managed evaluator display names use:

```text
EH_<project-slug>_<project-version>_judge_<dimension>_<evaluator-version>_<source-type>_<target-type>
```

Example:

```text
EH_rewrite-quality_v1_judge_clarity_v2_custom_observation
```

Display names are lookup hints, not ownership proof.

## Ownership Proof

The harness may update or inactivate a remote evaluator only when all are true:

1. A local evaluator binding record exists.
2. The remote evaluator ID in Langfuse matches the binding.
3. The remote evaluator remains compatible with the project evaluator identity.
4. The requested mutation is update-safe.

Remote evaluator metadata may be used as additional evidence only if Langfuse
exposes metadata on evaluator resources.

## Safe Update Fields

Allowed in-place updates for harness-managed evaluators:

- Filters.
- Sampling percentage.
- Variable mappings.
- Catalog reference metadata that does not change evaluator identity.
- Enabled/active state.

Changes requiring a new evaluator identity:

- Evaluator version.
- Prompt version.
- Score target.
- Source type.
- Target type.
- Scoring semantics.
- Ownership.

## Superseded Versions

When a new harness-managed evaluator version supersedes older active
harness-managed versions for the same project, dimension, source type, and
target:

- Create the new evaluator identity.
- Inactivate older versions where Langfuse supports safe inactivation.
- Add rename or comment context indicating the superseding evaluator version
  where Langfuse supports it.
- Do not delete evaluator resources.

## Target Filters

Default target:

```text
observation
```

Required observation-level filters:

```yaml
project: rewrite-quality
project_version: v1
evaluator_set_id: clarity:v2
observation_role: model_output
run_types:
  - baseline
  - candidate
```

Provider-specific observation names, such as `OpenAI-generation`, may be used
only as optional narrowing filters.

## Variable Mapping

Required variables must map to available Langfuse data.

Common mappings:

```yaml
input: observation.input
output: observation.output
baseline_output: trace.metadata.baseline_output
ground_truth: trace.metadata.ground_truth
```

If any required mapping is unavailable, setup for that evaluator is blocked.

## Score Target

Each evaluator dimension uses one canonical score config for Human Annotation
Queue scores. Langfuse LLM-as-Judge evaluator scores may be emitted under the
evaluator name because the current evaluator rule API does not expose a
score-config binding field.

Rules:

- Reuse compatible harness-managed score configs.
- Fail on incompatible active score configs.
- Do not create separate score configs for automated judge variants.
- Compare human and automated scores by evaluator dimension, score name, and
  Langfuse score source (`ANNOTATION` versus `EVAL`).

## Judge Model or LLM Connection

Resolution order:

1. Evaluator-level judge model or LLM connection.
2. Project-level default judge model or LLM connection.
3. Block setup if neither is available and Langfuse cannot safely provide one.

The setup summary must show the effective judge model or LLM connection.

## Sampling

Default:

```yaml
sampling_percent: 100
```

Project or evaluator config may override this value. Preview, apply, and audit
summaries must show effective sampling.

## Historical Backfill

Default:

```yaml
historical_backfill: false
```

If explicitly enabled:

- Apply only when Langfuse supports backfill for the selected target.
- Block the evaluator with remediation when unsupported.
- Never silently ignore a requested backfill.

## Binding Record

Example local binding:

```yaml
bindings:
  - project: rewrite-quality
    project_version: v1
    evaluator_name: clarity
    evaluator_version: v2
    source_type: custom
    target: observation
    langfuse_evaluator_id: eval_abc123
    langfuse_display_name: EH_rewrite-quality_v1_judge_clarity_v2_custom_observation
    score_config_id: score-config-1
    score_config_name: eh_rewrite_quality_clarity
    judge_model: gpt-4.1
    llm_connection: null
    sampling_percent: 100
    historical_backfill: false
    active: true
    last_synced_at: "2026-05-27T00:00:00Z"
```

Binding records must not contain secrets.

## Partial Failure

Apply behavior is per evaluator:

- Successful evaluator operations remain in place.
- Failed evaluator operations are reported with remediation.
- No rollback, delete, or destructive cleanup is attempted.
