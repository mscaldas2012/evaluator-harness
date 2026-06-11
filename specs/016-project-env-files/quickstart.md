# Quickstart: Project-Specific Environment Files

## Goal

Verify that project commands load root `.env` defaults and project-specific
`.env.<project-name>` overrides without exposing secret values.

## Setup Example

Create a shared root file:

```text
.env
```

```text
LANGFUSE_HOST=https://shared-langfuse.example
SHARED_TIMEOUT_SECONDS=60
PROJECT_ENDPOINT=https://shared-endpoint.example
```

Create a project-specific file for `gso`:

```text
.env.gso
```

```text
PROJECT_ENDPOINT=https://gso-endpoint.example
GSO_ONLY_SETTING=enabled
```

## Expected Behavior

For `configs/projects/gso.yaml`:

- `LANGFUSE_HOST` comes from root `.env` when not set in the shell.
- `PROJECT_ENDPOINT` comes from `.env.gso` when not set in the shell.
- `GSO_ONLY_SETTING` is available for the command.
- Any shell-provided value for those keys remains unchanged.

## Verification Commands

Run project validation:

```powershell
uv run python run_experiment.py validate --project configs/projects/gso.yaml
```

Run a dry-run setup command that reads project settings:

```powershell
uv run python run_experiment.py sync-dataset --project configs/projects/gso.yaml --dry-run
```

Run existing tests after implementation:

```powershell
uv run pytest -p no:cacheprovider tests/unit/test_live_settings.py tests/integration/test_project_env_files.py tests/contract/test_cli_project_env_files.py
```

## Notes

- Do not commit `.env` or `.env.<project-name>` files containing secrets.
- Missing `.env.<project-name>` files should not block existing projects.
- Missing required credentials should be reported by variable name only.
