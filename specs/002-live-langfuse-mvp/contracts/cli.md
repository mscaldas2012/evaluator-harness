# CLI Contract: Live Langfuse MVP

The live MVP extends the existing headless CLI. Commands may be implemented as
Typer subcommands or through `run_experiment.py`, but user-visible behavior
must satisfy this contract.

## Global Requirements

- Commands read project configuration from YAML.
- Live execution commands load secrets from `.env`, host environment, or a
  secret manager, never from committed project configs.
- `LANGFUSE_HOST` is the canonical Langfuse URL variable. `LANGFUSE_BASE_URL`
  is accepted as a backward-compatible alias.
- Commands that execute models must verify Langfuse connectivity and workspace
  access before provider token acquisition or model calls.
- Successful commands print the project name, dataset name/version, run IDs,
  item counts, and Langfuse identifiers or URLs when available.
- Failures return non-zero exit codes and actionable remediation.

## Validate Project

```powershell
uv run python run_experiment.py validate `
  --project configs/projects/rewrite_quality.yaml
```

**Behavior**:

- Validates project config, local dataset shape, prompt versions, evaluator
  definitions, score config ownership, provider declarations, and required
  environment variable names.
- For live validation, verifies Langfuse credentials and workspace access.
- Does not call Azure OpenAI or any candidate provider.

**Failure examples**:

- Missing Langfuse credentials.
- Invalid project config.
- Required Azure credential environment variable is not configured.
- Dataset lacks `input` or contains duplicate IDs.

## Sync Dataset

```powershell
uv run python run_experiment.py sync-dataset `
  --project configs/projects/rewrite_quality.yaml
```

**Behavior**:

- Verifies Langfuse workspace access.
- Loads the configured local CSV/JSON dataset or resolves an existing Langfuse
  Dataset.
- Creates or updates Langfuse Dataset items by stable item identity.
- Prints dataset name, version or version-equivalent, item count, and rejected
  item count.
- Preserves item identity needed for trace correlation and stable human-review
  calibration cohorts.
- Prints the dataset compatibility version used for baseline matching. This is
  the Langfuse dataset version when available, otherwise a deterministic hash
  from stable item IDs and input hashes.

**Idempotency**:

- Re-running the command must not create duplicate dataset items for unchanged
  logical item IDs.

## Sync Score Configs

```powershell
uv run python run_experiment.py sync-score-configs `
  --project configs/projects/rewrite_quality.yaml
```

**Behavior**:

- Verifies Langfuse workspace access.
- Creates missing harness-managed score configs using the project prefix.
- Reuses compatible harness-managed score configs.
- Validates user-owned score config references without creating or modifying
  them.
- Fails on incompatible managed score configs and instructs the user to delete
  or rename the Langfuse score config before resync.

**Must not**:

- Update, archive, delete, or overwrite existing Langfuse score configs.
- Create user-owned score configs.

## Run Live Baseline

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

**Behavior**:

- Verifies Langfuse workspace access before any Azure token or model call.
- Resolves/syncs the Langfuse Dataset.
- Resolves/syncs required harness-managed score configs.
- Acquires Azure AD token with tenant ID, client ID, client secret, and scope.
- Calls Azure OpenAI with APIM subscription key and configured API version.
- Persists one Langfuse trace per dataset item.
- Links each trace to the originating Langfuse Dataset item through the
  dataset/experiment run mechanism when available, or persists equivalent
  dataset item identity metadata when a lower-level trace path is required.
- Creates a distinct live baseline run every time the command is executed.
- Persists a baseline reference and compatibility fingerprint in Langfuse.

**Success output includes**:

- baseline run ID
- Langfuse dataset name/version
- baseline model config name
- item counts by completed/failed
- baseline compatibility fingerprint
- Langfuse trace/run identifiers or URLs when available

## Run Dry-Run Candidate Against Persisted Baseline

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate dry-run-candidate `
  --baseline latest-compatible
```

**Behavior**:

- Verifies Langfuse workspace access.
- Resolves/syncs the Langfuse Dataset.
- Resolves the requested baseline from Langfuse only.
- Fails before candidate output generation if no compatible baseline exists.
- Generates fake or dry-run candidate output for this MVP.
- Requires dry-run candidates to use the explicit `dry_run` provider/config
  path.
- Persists a distinct candidate run and traces linked to the selected baseline.
- Preserves the originating dataset item identity on every candidate trace so
  candidate outputs can be compared to baseline outputs item by item.

**`--baseline` values**:

- `latest-compatible`: find the newest Langfuse baseline whose compatibility
  fingerprint matches the current project, dataset version, prompt version,
  evaluator set, baseline model, and baseline parameters.
- `<baseline-run-id>`: use the explicit baseline only if it exists in Langfuse
  and passes compatibility checks.

## Select Review Items

```powershell
uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <candidate-run-id>
```

**Behavior**:

- Selects at least the configured minimum sample, defaulting to 5%.
- Selects the random calibration sample deterministically from stable dataset
  item IDs so baseline and compatible candidate runs use the same sampled item
  IDs when dataset version and review policy are unchanged.
- Adds run-specific risk review items for failures, low-confidence outputs, and
  disputed outputs without replacing the stable calibration sample.
- Routes selected items to the configured existing Langfuse Annotation Queue
  when `annotation_queue_id` is present.
- Skips duplicate queue items for the same queue, run, and trace.
- Does not create annotation queues in the MVP.

## Export Summary

```powershell
uv run python run_experiment.py export `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id> `
  --format csv
```

**Behavior**:

- Exports a lightweight local summary for sharing or archival.
- Includes run IDs, item IDs, outputs/failures, baseline reference, and
  Langfuse trace identifiers.
- Does not calculate replacement aggregate scores or dashboards.

## Live Integration Tests

```powershell
uv run pytest -m live
```

**Behavior**:

- Runs only tests marked `live`.
- Requires Langfuse and Azure OpenAI environment variables.
- Skips with a clear reason when credentials are missing.
- Exercises real Langfuse dataset sync, score config sync, Azure OpenAI
  baseline execution, dry-run candidate execution, and export.
