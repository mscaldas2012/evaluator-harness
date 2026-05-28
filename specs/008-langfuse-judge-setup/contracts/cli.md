# CLI Contract: Langfuse Judge Setup

## New Command: `sync-judge-evaluators`

Preview, apply, or audit Langfuse LLM-as-Judge evaluator setup for one project.

### Preview

```powershell
uv run python run_experiment.py sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml `
  --dry-run
```

Expected behavior:

- Validate project config, evaluator definitions, score targets, filters,
  variables, judge model/connection, sampling, backfill, and binding records.
- Resolve planned Langfuse operations without mutating Langfuse.
- Report newly created evaluators would be active after apply.
- Report effective sampling and backfill policy.

Success output shape:

```text
project: rewrite-quality/v1
mode: preview
status: success
binding-file: configs/langfuse/evaluator_bindings/rewrite-quality.yaml

evaluator: clarity/v2
source: custom
target: observation
operation: create
display-name: EH_rewrite-quality_v1_judge_clarity_v2_custom_observation
score-config: eh_rewrite_quality_clarity (score-config-1)
judge-model: gpt-4.1
activation: active-on-apply
sampling: 100
historical-backfill: disabled
binding: will-create
filters:
  project: rewrite-quality
  project_version: v1
  evaluator_set_id: clarity:v2
  observation_role: model_output
variables:
  input: observation.input
  output: observation.output
  baseline_output: trace.metadata.baseline_output
```

Exit codes:

- `0`: preview produced valid setup plan.
- `1`: validation or compatibility failure.
- `2`: requested Langfuse evaluator operation is unsupported by current
  installed Langfuse surface.

### Apply

```powershell
uv run python run_experiment.py sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml
```

Expected behavior:

- Apply each evaluator independently.
- Create missing harness-managed evaluators.
- Reuse compatible evaluators.
- Update only safe operational fields for harness-managed evaluators with
  matching local binding and remote compatibility.
- Inactivate older harness-managed evaluator versions when superseded and
  supported by Langfuse.
- Persist or refresh non-secret local binding records after successful create
  or update.
- Report full success, partial success, or failure.

Exit codes:

- `0`: all evaluator operations succeeded or were reused/skipped cleanly.
- `1`: one or more evaluator operations failed or were blocked.
- `2`: the requested live Langfuse operation is not exposed by the current
  Langfuse SDK/API surface.

### Audit

```powershell
uv run python run_experiment.py sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml `
  --audit
```

Expected behavior:

- Read local binding records.
- Fetch or resolve remote evaluator state when possible.
- Compare remote evaluator state to current project definition.
- Report matches, drift, missing remote resources, missing bindings, unsupported
  remote fields, and user-owned resources.
- Do not mutate Langfuse or local bindings.

## Existing Command Updates

### `validate`

Additional output:

```text
judge-setup: ready
judge-default: gpt-4.1
binding-file: configs/langfuse/evaluator_bindings/rewrite-quality.yaml
```

Validation additions:

- Catalog evaluators require catalog reference.
- Custom evaluators require prompt and result contract.
- Effective judge model/LLM connection must be resolvable from evaluator
  override or project default.
- Sampling defaults to 100 when omitted.
- Historical backfill defaults to disabled when omitted.
- Binding path must be repo-local and non-secret.

### `export-evaluator-setup`

Additional report sections:

- Managed evaluator display name.
- Source type: catalog/custom/user-owned.
- Effective judge model/LLM connection.
- Sampling policy.
- Historical backfill policy.
- Binding path and binding status.
- Safe update/inactivation policy.

## Error Message Requirements

Errors must identify:

- Evaluator name and version.
- Invalid or missing field.
- Whether the issue is local config, binding state, remote compatibility, or
  unsupported Langfuse capability.
- Remediation step.

Example:

```text
Evaluator clarity/v2 blocked: remote evaluator has managed display name but no
local binding record. Treating it as user-owned. Add a user-owned reference or
create a new harness-managed evaluator version.
```
