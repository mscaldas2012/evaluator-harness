# Quickstart: Shared Scenario Config References

## Validate The Shared DFE Scenario Projects

```powershell
uv run python run_experiment.py validate --project configs/projects/dfe-general-public.yaml
uv run python run_experiment.py validate --project configs/projects/dfe-healthcare-provider.yaml
uv run python run_experiment.py validate --project configs/projects/dfe-public-health-sme.yaml
```

Each project should resolve:

```yaml
config_refs:
  evaluation: configs/shared/dfe_readability.yaml
```

## Preview Langfuse Setup

Run dry-run setup before mutating Langfuse:

```powershell
uv run python run_experiment.py sync-all --project configs/projects/dfe-general-public.yaml --dry-run
uv run python run_experiment.py sync-all --project configs/projects/dfe-healthcare-provider.yaml --dry-run
uv run python run_experiment.py sync-all --project configs/projects/dfe-public-health-sme.yaml --dry-run
```

## Apply Langfuse Setup

```powershell
uv run python run_experiment.py sync-all --project configs/projects/dfe-general-public.yaml
uv run python run_experiment.py sync-all --project configs/projects/dfe-healthcare-provider.yaml
uv run python run_experiment.py sync-all --project configs/projects/dfe-public-health-sme.yaml
```

## Run Baselines

```powershell
uv run python run_experiment.py run --project configs/projects/dfe-general-public.yaml --mode baseline
uv run python run_experiment.py run --project configs/projects/dfe-healthcare-provider.yaml --mode baseline
uv run python run_experiment.py run --project configs/projects/dfe-public-health-sme.yaml --mode baseline
```

## Inspect Scenario Metadata

For scenario projects, traces and exports should include:

```text
scenario_group
scenario_name
scenario_display_name
```

Use these fields in Langfuse trace filtering, score comparison dashboards, CSV
exports, and human review inspection.

## Create Another Scenario Group

For a future non-DFE scenario group:

1. Create one shared evaluation config under `configs/shared/`.
2. Create one project YAML per scenario under `configs/projects/`.
3. Add optional complete `scenario` metadata to each scenario project.
4. Add `config_refs.evaluation` pointing to the shared evaluation config.
5. Validate each project independently.
