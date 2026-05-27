# Quickstart: Live Langfuse MVP

This quickstart describes the planned live MVP workflow. It assumes the
existing sample project is used as the first project.

## 1. Install Dependencies

Use `uv` for setup and command execution.

```powershell
uv sync
```

## 2. Configure Environment

Copy `.env.example` to `.env` and fill in local secrets. Do not commit `.env`.

Langfuse:

```powershell
$env:LANGFUSE_PUBLIC_KEY="pk-lf-..."
$env:LANGFUSE_SECRET_KEY="sk-lf-..."
$env:LANGFUSE_HOST="https://cloud.langfuse.com"
$env:EVALUATOR_HARNESS_LIVE="1"
```

`LANGFUSE_BASE_URL` remains accepted as a compatibility alias, but
`LANGFUSE_HOST` is the preferred variable name for new setup.

Azure OpenAI baseline:

```powershell
$env:EDAV_TENANT_ID="..."
$env:EDAV_CLIENT_ID="..."
$env:EDAV_CLIENT_SECRET="..."
$env:EDAV_SCOPE_TOKEN_AUDIENCE="https://cognitiveservices.azure.com/.default"
$env:EDAV_SUBSCRIPTION_KEY="..."
$env:EDAV_AZURE_OPENAI_API_VERSION="..."
$env:EDAV_AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
```

## 3. Validate the Project

```powershell
uv run python run_experiment.py validate `
  --project configs/projects/rewrite_quality.yaml
```

Expected result:

- project config is valid
- dataset shape is valid
- prompts and evaluator versions are present
- Langfuse credentials and workspace access are verified
- no model call is made

## 4. Sync Langfuse Assets

```powershell
uv run python run_experiment.py sync-dataset `
  --project configs/projects/rewrite_quality.yaml

uv run python run_experiment.py sync-score-configs `
  --project configs/projects/rewrite_quality.yaml

uv run python run_experiment.py sync-annotation-queue `
  --project configs/projects/rewrite_quality.yaml
```

Expected result:

- local dataset rows are present in a Langfuse Dataset
- item IDs are stable across syncs
- the command prints the dataset compatibility version used for baseline
  matching
- harness-managed score configs are created or reused
- incompatible managed score configs fail with remediation instructions
- the project-managed Human Annotation Queue is created or reused
- the queue ID is persisted in a non-secret local reference under
  `.evaluator-harness/queue-references/`

## 5. Run the Live Azure OpenAI Baseline

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

Expected result:

- Langfuse connectivity is verified before Azure OpenAI is called
- each dataset item creates a Langfuse trace
- each trace remains correlated to the originating Langfuse Dataset item
- a distinct baseline run is created
- baseline reference and compatibility metadata are stored in Langfuse
- the command prints the run ID and Langfuse identifiers or links

## 6. Run a Dry-Run Candidate Later

Run this in a separate shell or on a later day after the baseline exists.

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate dry-run-candidate `
  --baseline latest-compatible
```

Expected result:

- the harness finds the newest compatible baseline in Langfuse
- no local baseline registry file is required
- the candidate uses an explicit `dry_run` provider/config path
- a distinct candidate run is created
- candidate traces reference the selected baseline
- candidate traces preserve dataset item identity so outputs can be compared to
  baseline outputs item by item

To target a specific baseline:

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate dry-run-candidate `
  --baseline <baseline-run-id>
```

## 7. Configure Evaluators in Langfuse

High-level MVP steps:

1. Open the Langfuse project.
2. Confirm the synced score configs exist for the project evaluators.
3. Create or configure LLM-as-a-Judge evaluators in Langfuse.
4. Use evaluator prompts from the project, such as
   `prompts/rewrite_quality/evaluators/clarity.md`.
5. Map evaluator variables to trace or dataset-run fields:
   - `input`
   - `output`
   - `baseline_output` when comparing candidate context
   - `ground_truth` when present
6. Keep blind evaluator prompts neutral. Do not include provider, model, or
   vendor names in judge inputs.
7. Run evaluators over the baseline and candidate runs in Langfuse.

The harness does not implement local scoring in the MVP.

## 8. Route Human Review Items

Use the project-managed Human Annotation Queue created by
`sync-annotation-queue`. Managed queues follow this naming convention:

```text
EH_<project-slug>_<project-version>_review_<review-policy-version>
```

For the sample project, the default queue name is:

```text
EH_rewrite-quality_v1_review_default
```

```powershell
uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <candidate-run-id>
```

Expected result:

- at least the configured minimum random calibration sample is selected
- the random calibration sample uses the same dataset item IDs for baseline and
  compatible candidate runs when dataset version and review policy are unchanged
- failures and risky outputs are added as run-specific review items
- selected items are routed to the managed queue
- repeat routing skips duplicates

To use a manually maintained Langfuse queue instead, set
`human_review.queue_ownership: user_owned` and provide
`human_review.annotation_queue_id` in the project config. The optional
`LANGFUSE_ANNOTATION_QUEUE_ID` environment variable remains a temporary override
when enabled by the project policy.

## 9. Compare Runs in Langfuse

In Langfuse:

1. Open the Dataset or Experiments area.
2. Select the baseline run and one or more candidate runs.
3. Compare evaluator scores, score distributions, latency, token usage, costs,
   trace examples, and human annotations.
4. Inspect low-confidence or disputed examples before changing model defaults.

## 10. Run Tests

Default tests are credential-free:

```powershell
uv run pytest
```

Live smoke tests are explicit:

```powershell
uv run pytest -m live
```

Live tests require Langfuse and Azure OpenAI credentials. They should skip with
a clear reason when required variables are missing.
