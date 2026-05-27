# Evaluator Harness

Lightweight, headless, Langfuse-first offline evaluation harness.

The harness runs project datasets against a baseline model and candidate model
configs, logs traces and reproducibility metadata to Langfuse, and leaves
evaluators, scores, dashboards, comparisons, annotation queues, and trace
inspection in Langfuse.

## Setup

Use `uv` for environment setup and command execution.

```powershell
uv sync
```

Store credentials in `.env`, your shell, or a secret manager. Project YAML files
store only environment variable names such as `EDAV_CLIENT_SECRET`.

Required for Langfuse:

```powershell
$env:LANGFUSE_PUBLIC_KEY="pk-lf-..."
$env:LANGFUSE_SECRET_KEY="sk-lf-..."
$env:LANGFUSE_HOST="https://cloud.langfuse.com"
$env:EVALUATOR_HARNESS_LIVE="1"
```

`LANGFUSE_BASE_URL` is still accepted as a compatibility alias.

Required for the Azure OpenAI baseline adapter:

```powershell
$env:EDAV_TENANT_ID="..."
$env:EDAV_CLIENT_ID="..."
$env:EDAV_CLIENT_SECRET="..."
$env:EDAV_SCOPE_TOKEN_AUDIENCE="..."
$env:EDAV_SUBSCRIPTION_KEY="..."
$env:EDAV_AZURE_OPENAI_API_VERSION="..."
$env:EDAV_AZURE_OPENAI_ENDPOINT="..."
```

## Quickstart

```powershell
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
uv run python run_experiment.py sync-dataset --project configs/projects/rewrite_quality.yaml
uv run python run_experiment.py sync-score-configs --project configs/projects/rewrite_quality.yaml
uv run python run_experiment.py sync-annotation-queue --project configs/projects/rewrite_quality.yaml

uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline

uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate dry-run-candidate `
  --baseline latest-compatible

uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <candidate-run-id>
```

Use Langfuse to run evaluators, inspect scores, compare baseline and candidate
runs, and review selected items in Human Annotation Queues.

Trace names use a stable, scannable format:

```text
rewrite-quality/baseline/item-1
rewrite-quality/candidate/item-2
test/rewrite-quality/baseline/item-1
```

The `test/` prefix is added for pytest-driven live smoke traces. Model names,
provider names, run IDs, prompt versions, and parameters are stored in trace
metadata instead of the trace name. For Azure/OpenAI runs, the meaningful
`OpenAI-generation` observation is linked to the same parent trace ID where the
harness stores dataset input, final output, and evaluation metadata.

Managed annotation queues use the name
`EH_<project-slug>_<project-version>_review_<review-policy-version>` and store a
non-secret local reference under `.evaluator-harness/queue-references/`.
`LANGFUSE_ANNOTATION_QUEUE_ID` is only needed for an explicit user-owned queue
or temporary override.

### Langfuse Hobby Annotation Queue Limit

Langfuse Cloud Hobby currently allows only one Human Annotation Queue per
workspace. Keep `human_review.review_policy_version: default` unless you are on
a plan that supports additional queues. Changing the review policy version
changes the managed queue name and can trigger Langfuse's `Maximum number of
annotation queues reached on Hobby plan` error.

For Hobby workspaces, the harness treats the local queue reference as disposable
cache. If the local reference is stale, points to a missing queue, or has older
score config IDs, `sync-annotation-queue` rewrites the local reference and
reuses the single existing Langfuse queue instead of requiring a new queue.

### Cleaning Up Duplicate Score Configs

Older versions of the live sync path could create duplicate active score
configs with the same harness-managed name, such as
`eh_rewrite_quality_clarity`. The current sync path reuses existing compatible
score configs, but existing duplicates can be archived with the cleanup script.

Preview the cleanup plan:

```powershell
uv run python scripts/cleanup_duplicate_score_configs.py `
  --project configs/projects/rewrite_quality.yaml
```

Apply the cleanup:

```powershell
uv run python scripts/cleanup_duplicate_score_configs.py `
  --project configs/projects/rewrite_quality.yaml `
  --apply
```

The script only targets active score configs whose names start with the
project's `score_config_prefix`. It keeps the newest active config for each name
and archives the older duplicates. It does not delete score results.

Langfuse may still show archived score configs in the UI. To rename archived
duplicates so only one config keeps the active managed name:

```powershell
uv run python scripts/cleanup_duplicate_score_configs.py `
  --project configs/projects/rewrite_quality.yaml `
  --rename-archived `
  --apply
```

### Cleaning Up Invalid Annotation Queue Items

Earlier live smoke runs may have added Human Annotation Queue items that point
to local run/item IDs instead of real Langfuse trace IDs. Those items open with
`Trace Not Found. Likely Deleted` in Langfuse. Current runs use valid Langfuse
trace IDs.

Preview invalid queue items:

```powershell
uv run python scripts/cleanup_invalid_annotation_queue_items.py
```

Delete invalid queue items:

```powershell
uv run python scripts/cleanup_invalid_annotation_queue_items.py --apply
```

## Tests

Default tests use fakes or injected clients. They do not require live Langfuse,
Azure OpenAI, OpenAI, or Ollama credentials.

```powershell
uv run pytest
```

Opt-in live smoke tests hit configured Langfuse and Azure OpenAI resources:

```powershell
uv run pytest -m live
```

## Documentation

- User guide: `docs/user-guide.md`
- Langfuse automation backlog: `docs/langfuse-automation-backlog.md`
- Spec Kit feature docs: `specs/002-live-langfuse-mvp/`
