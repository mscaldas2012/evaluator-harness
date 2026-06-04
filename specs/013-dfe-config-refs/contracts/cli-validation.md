# Contract: CLI Validation And Existing Workflows

## Existing Commands

No new CLI command is required. Existing project-based commands accept scenario
project configs after reference resolution:

```text
uv run python run_experiment.py validate --project configs/projects/dfe-general-public.yaml
uv run python run_experiment.py sync-all --project configs/projects/dfe-general-public.yaml --dry-run
uv run python run_experiment.py run --project configs/projects/dfe-general-public.yaml --mode baseline
uv run python run_experiment.py export --project configs/projects/dfe-general-public.yaml --run-id <run-id> --format csv
```

The same command shape applies to any future scenario project config.

## Validation Behavior

`validate --project` must report the fully resolved project as valid when:

- The project config is valid without `config_refs`, or
- `config_refs.evaluation` resolves to an allowed shared evaluation config and
  the merged effective project is valid.

`validate --project` exits non-zero when:

- The shared evaluation reference is missing.
- The shared file contains disallowed sections.
- Local and shared evaluation fields conflict.
- Scenario identity is incomplete.
- Existing project validation fails after reference resolution.

## Backward Compatibility

Existing project configs without `config_refs` and without `scenario` must
continue to validate and run unchanged.

## DFE Example Validation

The initial DFE scenario project configs must validate:

```text
uv run python run_experiment.py validate --project configs/projects/dfe-general-public.yaml
uv run python run_experiment.py validate --project configs/projects/dfe-healthcare-provider.yaml
uv run python run_experiment.py validate --project configs/projects/dfe-public-health-sme.yaml
```

Expected behavior:

- Each project resolves `configs/shared/dfe_readability.yaml`.
- Each project has distinct project and Langfuse dataset names.
- Each project has complete scenario metadata.
- Each project uses its own configured task prompt.
- All three projects share the same effective evaluator, judge setup, and human
  review definitions.
