# Quickstart: Create Annotation Queues

This quickstart describes the planned workflow for project-managed Langfuse
Human Annotation Queues.

## 1. Configure Langfuse

Use `.env` or host environment variables:

```powershell
$env:LANGFUSE_PUBLIC_KEY="pk-lf-..."
$env:LANGFUSE_SECRET_KEY="sk-lf-..."
$env:LANGFUSE_HOST="https://us.cloud.langfuse.com"
$env:EVALUATOR_HARNESS_LIVE="1"
```

`LANGFUSE_ANNOTATION_QUEUE_ID` is optional. It is only needed when explicitly
overriding the project-managed queue.

## 2. Configure The Project Review Policy

For a project-managed queue:

```yaml
human_review:
  enabled: true
  queue_ownership: managed_by_harness
  minimum_sample_percent: 5
```

If `queue_name` is omitted, the harness creates a deterministic managed queue
name:

```text
EH_<project-slug>_<project-version>_review_<review-policy-version>
```

For the sample project this becomes:

```text
EH_rewrite-quality_v1_review_default
```

The reusable local queue reference is stored at:

```text
.evaluator-harness/queue-references/<project-slug>__<project-version>__<review-policy-version>.json
```

For the sample project this becomes:

```text
.evaluator-harness/queue-references/rewrite-quality__v1__default.json
```

Use an explicit `queue_name` only when you need a specific Langfuse display
name. Queue names must contain only letters, numbers, underscores, and hyphens.

For a user-owned existing queue:

```yaml
human_review:
  enabled: true
  queue_ownership: user_owned
  annotation_queue_id: existing-langfuse-queue-id
```

## 3. Sync Score Configs

Managed queues require score config IDs, so sync scores first:

```powershell
uv run python run_experiment.py sync-score-configs `
  --project configs/projects/rewrite_quality.yaml
```

## 4. Sync The Annotation Queue

```powershell
uv run python run_experiment.py sync-annotation-queue `
  --project configs/projects/rewrite_quality.yaml
```

Expected result:

- disabled review reports `skipped`
- user-owned queues report `user_owned`
- managed queues are created or reused
- the command prints the queue ID, queue name, ownership, status, managed score
  config IDs, and local reference path

## 5. Run Baseline And Route Review Items

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline

uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <baseline-run-id>
```

Expected result:

- selected review items are routed to the project-managed queue
- no `LANGFUSE_ANNOTATION_QUEUE_ID` is required
- rerunning review routing skips duplicates

## 6. Run Candidate Later

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate dry-run-candidate `
  --baseline latest-compatible

uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <candidate-run-id>
```

Expected result:

- baseline and candidate review items use the same queue
- the stable calibration sample uses the same dataset item IDs for compatible
  runs

## 7. Run Tests

Default tests are credential-free:

```powershell
uv run pytest
```

Live queue tests are explicit:

```powershell
uv run pytest -m live
```

Live tests should skip only when Langfuse credentials are missing or queue
automation is unavailable in the configured Langfuse workspace.
