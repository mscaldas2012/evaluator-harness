# Quickstart: Model Output Observation Targeting

## Goal

Verify that evaluator counts reflect one final model output per dataset item run
instead of matching both parent/container and final generation observations.

## Validate Project Config

```powershell
uv run python run_experiment.py validate --project configs/projects/dfe-general-public.yaml
```

Expected:

- Project validates.
- Standard DFE evaluators target `observation/model_output`.
- No provider-specific observation name is required for normal DFE scoring.
- Runs print a `model-output-targeting` status. Local fake runs should report
  `aligned`; live SDK runs may report `unknown` because nested Langfuse
  observations are verified in Langfuse rather than local trace payloads.

## Sync Evaluators

After implementation, sync judge evaluator rules so new targeting semantics are
applied to newly created or updated evaluator definitions.

```powershell
uv run python run_experiment.py sync-judge-evaluators --project configs/projects/dfe-general-public.yaml
```

If evaluator target semantics changed for already-active rules, bump evaluator
versions before syncing so Langfuse creates clean rules for the new contract.

## Run Baseline Twice

```powershell
uv run python run_experiment.py run --project configs/projects/dfe-general-public.yaml --mode baseline
uv run python run_experiment.py run --project configs/projects/dfe-general-public.yaml --mode baseline
```

For a 12-item dataset, Langfuse evaluator counts should show 24 matches per
standard evaluator, not 48.

## What To Inspect In Langfuse

For a representative trace:

- The parent/container observation should not be marked as the final model
  output.
- Exactly one final output observation should be eligible for model-output
  evaluators.
- Automated eval scores and human annotation scores should remain under the
  same canonical score names when score config alignment is enabled.

## Regression Test Targets

Run targeted tests:

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/integration/test_model_output_targeting.py
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_progress_reporting.py tests/contract/test_cli_run_baseline.py
```

Run broader evaluator setup tests if evaluator sync behavior changes:

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_judge_setup_planner.py tests/integration/test_sync_judge_evaluators.py tests/contract/test_cli_sync_judge_evaluators.py
```

## Provider Integration Checklist

- Harness-managed tracing path: one final model output observation matches.
- Dry-run path: local output remains evaluator-targetable.
- Native Langfuse provider path: final output role is propagated or explicit
  targeting configuration is documented.
- Parent/container span: visible in trace, not evaluator-targetable as
  `model_output`.
