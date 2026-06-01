# Quickstart: Sync Langfuse Prompts

## Prerequisites

- Project configuration points to local task and evaluator prompt files.
- Langfuse environment variables are configured for live operations.
- Python commands are run with `uv`.

## Dry-Run Prompt Sync

Preview prompt sync actions without changing Langfuse or local bindings:

```powershell
uv run python run_experiment.py sync-prompts --project configs/projects/dfe.yaml --dry-run
```

Expected output:

```text
project: dfe/v1
mode: dry-run
binding-file: configs/langfuse/prompt_bindings/dfe.yaml
prompts: 11
created: 0
reused: 0
conflicts: 0
failed: 0
```

Each prompt also reports its managed name, shape, status, and remediation when
needed.

## Apply Prompt Sync

Publish missing prompt versions and save local prompt binding references:

```powershell
uv run python run_experiment.py sync-prompts --project configs/projects/dfe.yaml
```

Successful sync creates or reuses Langfuse prompt versions for the task prompt
and evaluator prompts.

## Handle Changed Prompt Content

If a prompt file changes after it has already been synced with `prompt_version:
v1`, sync fails for that prompt until the configured prompt version is bumped:

```yaml
prompt_path: prompts/dfe/evaluators/formatting_essence_maintained.md
prompt_version: v2
```

After bumping the relevant prompt version, rerun dry-run and apply:

```powershell
uv run python run_experiment.py sync-prompts --project configs/projects/dfe.yaml --dry-run
uv run python run_experiment.py sync-prompts --project configs/projects/dfe.yaml
```

## Run Without Prompt Sync

Prompt sync is optional. Existing local workflows continue to use repository
prompt files:

```powershell
uv run python run_experiment.py validate --project configs/projects/dfe.yaml
uv run python run_experiment.py run --project configs/projects/dfe.yaml --mode baseline
```

Runs include local prompt identity metadata whether or not prompt sync has been
performed. When a matching synced prompt binding exists, runs also include the
Langfuse prompt reference.
