# Contract: sync-prompts CLI

## Command

```text
uv run python run_experiment.py sync-prompts --project <project-yaml> [--dry-run]
```

## Inputs

- `--project`: path to a project YAML file.
- `--dry-run`: when present, inspect local and Langfuse prompt state without
  modifying Langfuse or local prompt bindings.
- `--audit`: accepted as a backward-compatible alias for `--dry-run`.

## Behavior

1. Load and validate the project configuration.
2. Discover the task prompt and evaluator prompts that reference local prompt
   files.
3. Parse each prompt as text or chat according to the existing prompt format.
4. Compute managed names and content identities.
5. Check local prompt binding records and Langfuse prompt state.
6. In dry-run mode, report planned operations only.
7. In apply mode, create missing prompt versions, reuse matching prompt
   versions, reject changed content under the same configured prompt version,
   and save binding records for successful prompt artifacts.

## Output

The command prints a summary:

```text
project: <project>/<version>
mode: dry-run|apply
binding-file: configs/langfuse/prompt_bindings/<project>.yaml
prompts: <total>
created: <count>
reused: <count>
conflicts: <count>
failed: <count>
```

Then it prints one block per prompt:

```text
prompt: <artifact_type>/<artifact_name>/<artifact_version>
managed-name: <langfuse prompt name>
shape: text|chat
status: created|reused|changed|skipped|conflict|failed
langfuse-version: <version or none>
remediation: <action when applicable>
```

## Status Semantics

- `created`: apply mode created a new Langfuse prompt version.
- `reused`: local content identity matches an existing managed prompt version.
- `changed`: dry-run mode found local content differs from the existing version.
- `skipped`: prompt artifact is intentionally not syncable.
- `conflict`: remote prompt exists but is not safely harness-managed, or the
  same configured prompt version has different content.
- `failed`: sync could not complete because of validation, filesystem, or
  Langfuse errors.

## Exit Behavior

- Success exits with code 0 when all prompt artifacts are created, reused, or
  skipped.
- Configuration and sync conflicts exit with code 1.
- Unsupported live Langfuse operation exits with code 2.

## Progress

The command displays progress across prompt artifacts in both dry-run and apply
mode when using the normal CLI runner.
