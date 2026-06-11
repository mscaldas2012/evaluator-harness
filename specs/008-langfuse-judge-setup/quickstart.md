# Quickstart: Langfuse Judge Setup

This guide describes the intended workflow for direct Langfuse LLM-as-Judge
evaluator setup.

## 1. Configure Judge Setup Defaults

Example project-level setup:

```yaml
judge_setup:
  default_judge_model: gpt-4.1
  binding_path: configs/langfuse/evaluator_bindings/rewrite-quality.yaml
  default_sampling_percent: 100
  historical_backfill: disabled
```

Evaluator-level values may override project defaults.

## 2. Configure a Custom Evaluator

```yaml
evaluators:
  - name: clarity
    type: llm_as_judge
    source_type: custom
    version: v2
    dimension: clarity
    target: observation
    prompt_path: prompts/rewrite_quality/evaluators/clarity.md
    prompt_version: v2
    judge_model: gpt-4.1
    sampling_percent: 100
    historical_backfill: disabled
```

## 3. Configure a Langfuse Catalog Evaluator

```yaml
evaluators:
  - name: helpfulness
    type: llm_as_judge
    source_type: catalog
    catalog_ref: langfuse/helpfulness
    version: v1
    dimension: helpfulness
    target: observation
    sampling_percent: 100
```

## 4. Preview Setup

```powershell
uv run python run_experiment.py sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml `
  --dry-run
```

Expected preview includes:

- Operation: create, reuse, update, inactivate, skip, block, or fail.
- Managed display name.
- Effective judge model or LLM connection.
- Score config name and ID.
- Target filters.
- Variable mappings.
- Sampling policy.
- Historical backfill policy.
- Binding status.
- Activation state after apply.

## 5. Apply Setup

```powershell
uv run python run_experiment.py sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml
```

Apply creates new evaluators as active immediately. It applies each evaluator
independently, so partial success is possible. Successful changes remain in
place; failed evaluator setup is reported with remediation.

## 6. Audit Setup

```powershell
uv run python run_experiment.py sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml `
  --audit
```

Audit compares local project definitions and binding records to remote
Langfuse evaluator state without mutating anything.

## 7. Binding Records

After successful apply, the harness writes a non-secret local binding record:

```text
configs/langfuse/evaluator_bindings/rewrite-quality.yaml
```

The binding proves that the harness created or updated a remote evaluator and
is required before future update or inactivation. A matching display name alone
is not enough.

## 8. Historical Backfill

Historical backfill is disabled by default. To request it:

```yaml
historical_backfill: enabled
```

If Langfuse does not support backfill for the selected evaluator target, setup
blocks that evaluator with a remediation message. The harness does not run
judge models locally for backfill.

## 9. Verify Existing Commands

```powershell
uv run python run_experiment.py validate `
  --project configs/projects/rewrite_quality.yaml
```

Validation should show judge setup readiness, score targets, evaluator targets,
and binding path.

```powershell
uv run python run_experiment.py export-evaluator-setup `
  --project configs/projects/rewrite_quality.yaml
```

The exported setup report should include the same setup details shown in dry
run.

## 10. Verification Results

Recorded on 2026-05-27:

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit tests/contract tests/integration -m "not live"
```

Result: 179 passed, 7 live tests deselected.

```powershell
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
```

Result: exit 0; output included `judge-setup: ready`,
`judge-default: gpt-4.1`, and the evaluator binding path.

```powershell
uv run python run_experiment.py sync-judge-evaluators --project configs/projects/rewrite_quality.yaml --dry-run
```

Result: exit 0; output included `mode: preview`, `operation: create`,
`source: custom`, `sampling: 100`, and `historical-backfill: disabled`.

```powershell
uv run python run_experiment.py export-evaluator-setup --project configs/projects/rewrite_quality.yaml
```

Result: exit 0; output path `reports/rewrite-quality/evaluator-setup-rewrite-quality-v1.md`.
