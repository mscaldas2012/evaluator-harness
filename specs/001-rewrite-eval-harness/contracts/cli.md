# CLI Contract: Lightweight Langfuse Evaluation Harness

The MVP exposes a headless CLI. Command names may be implemented as Typer
subcommands or as options on `run_experiment.py`, but the user-facing behavior
must satisfy this contract.

## Global Requirements

- Commands must read project configuration from YAML.
- Commands must fail fast when Langfuse is unreachable.
- Commands must print the resolved project, dataset identity/version, run ID,
  and Langfuse run/trace links when available.
- Commands must return non-zero exit codes for validation, provider, or
  Langfuse failures.

## Validate Project

```bash
uv run python run_experiment.py validate \
  --project configs/projects/rewrite_quality.yaml
```

**Behavior**:

- Validates project config, dataset shape, prompt versions, evaluator versions,
  provider configuration, and baseline/candidate declarations.
- Does not call models.
- May call Langfuse to validate credentials and resolve configured datasets or
  queues.

**Success output includes**:

- project name/version
- dataset source
- required provider configs
- baseline config name
- candidate config names
- evaluator names/versions

## Sync Dataset

```bash
uv run python run_experiment.py sync-dataset \
  --project configs/projects/rewrite_quality.yaml
```

**Behavior**:

- Loads local CSV/JSON dataset or resolves a configured Langfuse Dataset.
- Creates or updates the Langfuse Dataset as needed.
- Records or prints the Langfuse dataset identity and version.

**Success output includes**:

- Langfuse dataset name or ID
- dataset version
- item count
- rejected/invalid item count, if any

## Sync Score Configs

```bash
uv run python run_experiment.py sync-score-configs \
  --project configs/projects/rewrite_quality.yaml
```

`managed_by_harness` means the harness may create or resolve the Langfuse score
config schema for that evaluator. It does not mean the harness owns score
results; Langfuse remains the owner of scores produced by evaluators,
annotations, or API calls.

**Behavior**:

- Reads evaluator score config contracts from project YAML.
- Applies the project `score_config_prefix` to harness-managed score config
  names.
- Rejects invalid prefixes. Prefixes must be non-empty, project-specific,
  slug-safe using ASCII letters, numbers, `_`, and `-`, end with `_` or `-`,
  be no more than 64 characters, and produce derived managed score config names
  no longer than 128 characters unless Langfuse documents a different limit.
- Creates missing harness-managed Langfuse score configs.
- Reuses existing compatible harness-managed Langfuse score configs.
- Validates or reports user-owned score config references without creating them.
- Fails when an existing score config with the managed name has incompatible
  schema.
- Treats archived same-name configs as conflicting unless Langfuse no longer
  returns or reserves that name.
- Does not update, archive, or delete Langfuse score configs.
- Compares compatibility using score name, data type, numeric min/max bounds,
  categorical labels/values, boolean/text constraints exposed by Langfuse, and
  archived status. Description differences are reported but do not fail sync.

**Success output includes**:

- evaluator name
- score config ownership: `managed_by_harness` or `user_owned`
- managed score config name, when `managed_by_harness` is true
- user-owned Langfuse score config ID/name, when `managed_by_harness` is false
- Langfuse score config ID
- created or reused status

**Failure output includes**:

- evaluator name
- score config ownership
- managed score config name or user-owned score config ID/name
- incompatible, missing, invalid-prefix, or archived-name-conflict fields
- instruction to manually delete or rename an incompatible harness-managed
  Langfuse score config before resyncing; archiving alone is accepted only if
  Langfuse no longer treats the name as conflicting

## Run Baseline

```bash
uv run python run_experiment.py run \
  --project configs/projects/rewrite_quality.yaml \
  --mode baseline
```

**Behavior**:

- Validates project config.
- Syncs/resolves Langfuse Dataset.
- Runs the baseline model over dataset items.
- Logs traces, outputs, and metadata to Langfuse.
- Creates evaluator-ready baseline records with `input`, baseline `output`,
  optional `ground_truth`, evaluator versions, and trace context.
- Triggers or queues Langfuse-owned baseline evaluator execution when evaluator
  automation is configured and available. Does not perform local scoring.
- Records a reusable baseline reference.

**Success output includes**:

- run ID
- Langfuse dataset identity/version
- baseline model config
- baseline reference
- item counts by completed/failed

## Run Candidate

```bash
uv run python run_experiment.py run \
  --project configs/projects/rewrite_quality.yaml \
  --mode candidate \
  --candidate llama3-local \
  --baseline latest-compatible
```

**Behavior**:

- Validates project config.
- Syncs/resolves Langfuse Dataset.
- Resolves the requested compatible baseline.
- Runs the candidate model over dataset items.
- Logs traces, outputs, baseline reference, and metadata to Langfuse.

**Success output includes**:

- run ID
- candidate model config
- baseline reference used
- Langfuse dataset identity/version
- item counts by completed/failed

## Select Human Review Items

```bash
uv run python run_experiment.py select-review \
  --project configs/projects/rewrite_quality.yaml \
  --run <candidate-run-id>
```

**Behavior**:

- Selects at least 5% of evaluated outputs for review.
- Prioritizes failures, low-confidence outputs, and disputed outputs before
  random sampling.
- If an annotation queue ID is configured, routes selected items to Langfuse.
- Does not create annotation queues in MVP.

**Success output includes**:

- selected count
- selection reasons
- annotation queue ID, if used
- skipped/duplicate count, if any

## Export Summary

```bash
uv run python run_experiment.py export \
  --project configs/projects/rewrite_quality.yaml \
  --run <run-id> \
  --format csv
```

**Behavior**:

- Exports a lightweight local summary for sharing or archival.
- Must not replace Langfuse as the system of record.
- Must not compute custom aggregate scores in MVP.
