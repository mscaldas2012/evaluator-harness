# Quickstart: Lightweight Langfuse Evaluation Harness

This quickstart describes the MVP user flow. Command names are the planned CLI
contract and may be implemented by `run_experiment.py` or an installed console
script.

## 1. Set Up Python Environment

Use `uv` for Python environment management, dependency setup, and command
execution.

```powershell
uv sync
```

## 2. Configure Environment

Set Langfuse credentials and provider credentials in your shell, `.env`, or a
secret manager. Do not put secret values in project configs. The project config
stores names like `EDAV_CLIENT_SECRET`; the actual value lives outside the repo.

```powershell
$env:LANGFUSE_PUBLIC_KEY="pk-lf-..."
$env:LANGFUSE_SECRET_KEY="sk-lf-..."
$env:LANGFUSE_BASE_URL="https://cloud.langfuse.com"
$env:EDAV_TENANT_ID="..."
$env:EDAV_CLIENT_ID="..."
$env:EDAV_CLIENT_SECRET="..."
$env:EDAV_SCOPE_TOKEN_AUDIENCE="..."
$env:EDAV_SUBSCRIPTION_KEY="..."
$env:EDAV_AZURE_OPENAI_API_VERSION="..."
$env:EDAV_AZURE_OPENAI_ENDPOINT="..."
```

For Ollama, ensure the local Ollama service is running and the model is
available.

## 3. Create a Dataset

Create `datasets/rewrite_quality.csv`.

```csv
id,input,ground_truth
1,"Rewrite this paragraph in a professional tone.","A professional rewrite that preserves the original meaning."
2,"Simplify this technical explanation.","A simpler explanation that remains technically accurate."
```

Only `input` is required. If `id` is missing, the harness generates stable item
IDs from row position and input hash. `ground_truth` is optional and can be used
by baseline or candidate evaluators as a reference value.

## 4. Create Project Prompts

Create `prompts/rewrite_quality/task_prompt.md`.

```text
Rewrite the following text according to the project instructions.

Input:
{{input}}
```

Create `prompts/rewrite_quality/evaluators/clarity.md`.

```text
You are evaluating one dimension: clarity.

Source input:
{{input}}

Output:
{{output}}

Ground truth, if present:
{{ground_truth}}

Return JSON with reasoning, score from 0.0 to 1.0, and confidence from 0.0 to
1.0.
```

Configure this evaluator in Langfuse as an LLM-as-a-Judge evaluator and map the
variables to run fields. Langfuse owns evaluator execution and score storage.
Because project config sets `blind: true`, judge inputs should use neutral
labels and must not expose provider or model identity.

## 5. Create a Project Config

Create `configs/projects/rewrite_quality.yaml`.

```yaml
project:
  name: rewrite-quality
  description: Compare model outputs for a rewrite task.
  version: v1
  score_config_prefix: eh_rewrite_quality_

dataset:
  kind: local_csv
  path: datasets/rewrite_quality.csv
  langfuse_dataset_name: rewrite-quality/v1
  item_id_strategy: explicit_or_hash

task_prompt:
  path: prompts/rewrite_quality/task_prompt.md
  version: v1
  template_variables:
    - input

baseline:
  name: gpt-4.1-baseline
  provider: openai_compatible
  auth_mode: azure_client_credentials
  model: gpt-4.1
  azure:
    tenant_id_env: EDAV_TENANT_ID
    client_id_env: EDAV_CLIENT_ID
    client_secret_env: EDAV_CLIENT_SECRET
    scope_env: EDAV_SCOPE_TOKEN_AUDIENCE
    subscription_key_env: EDAV_SUBSCRIPTION_KEY
    api_version_env: EDAV_AZURE_OPENAI_API_VERSION
    endpoint_env: EDAV_AZURE_OPENAI_ENDPOINT
  parameters:
    temperature: 0.2
    top_p: 1.0
    max_tokens: 2048

candidates:
  - name: llama3-local
    provider: ollama
    auth_mode: none
    model: llama3
    parameters:
      temperature: 0.2
      top_p: 1.0
      max_tokens: 2048

evaluators:
  - name: clarity
    type: llm_as_judge
    version: v1
    prompt_path: prompts/rewrite_quality/evaluators/clarity.md
    score:
      name: clarity
      managed_by_harness: true
      data_type: NUMERIC
      min_value: 0
      max_value: 1
      description: Clarity score from 0.0 to 1.0.
    blind: true
    modes:
      - baseline
      - candidate
    variables:
      - input
      - output
      - baseline_output
      - ground_truth

human_review:
  enabled: true
  minimum_sample_percent: 5
  prioritize:
    - failures
    - low_confidence
    - disputed
  annotation_queue_id: optional-existing-langfuse-queue-id
```

The `*_env` values above are environment variable names, not credentials. This
project file is safe to commit when it contains only references like
`EDAV_CLIENT_SECRET`; the real values belong in `.env`, your shell environment,
or a secret manager. `.env` is ignored by git.

The project config does not include a tracing mode. Provider adapters choose the
best tracing path internally, preferring Langfuse-supported integrations and
using manual trace logging only as an adapter-owned fallback.

## 6. Validate and Sync Dataset

```powershell
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
uv run python run_experiment.py sync-dataset --project configs/projects/rewrite_quality.yaml
uv run python run_experiment.py sync-score-configs --project configs/projects/rewrite_quality.yaml
```

The sync step creates, updates, or resolves the Langfuse Dataset and records the
dataset identity/version used for experiment runs. Score config sync creates
missing harness-managed score configs using the configured prefix, such as
`eh_rewrite_quality_clarity`, or reuses an existing compatible config. If the
prefixed config exists with incompatible schema, the harness fails and asks the
user to delete or rename it in Langfuse before resyncing. Archiving alone is
accepted only if Langfuse no longer treats that score config name as
conflicting.

## 7. Run Baseline

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

Expected result:

- baseline model executes for each dataset item
- Langfuse traces are created
- Langfuse dataset run is created
- baseline evaluator-ready records include `input`, baseline `output`, optional
  `ground_truth`, evaluator versions, and trace context
- Langfuse-owned baseline evaluators can run for baseline-supported evaluator
  modes, whether or not `ground_truth` is present
- baseline run identity is recorded for reuse

## 8. Run Candidate Against Existing Baseline

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate llama3-local `
  --baseline latest-compatible
```

The harness reuses the existing baseline when project, dataset version, prompt
version, evaluator set, baseline model, and baseline parameters are compatible.

## 9. Run Evaluators in Langfuse

In Langfuse:

1. Open the project/dataset run.
2. Confirm baseline and candidate traces are present.
3. Confirm each evaluator references the harness-managed score config created
   by `sync-score-configs`.
4. Configure the LLM-as-a-Judge evaluator using the project evaluator prompt.
5. Run the evaluator over the relevant experiment or dataset run.
6. Inspect scores, judge reasoning, and confidence values.

## 10. Select Human Review Items

```powershell
uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <candidate-run-id>
```

The harness selects at least 5% of evaluated outputs for review, prioritizing
failures, low-confidence outputs, and disputed outputs before random sampling.
If `annotation_queue_id` is configured, selected items are routed to that
Langfuse Human Annotation Queue.

## 11. Compare Runs in Langfuse

In Langfuse:

1. Open the dataset or experiment comparison view.
2. Select the baseline run.
3. Select one or more candidate runs.
4. Compare evaluator scores, latency, token usage, cost, trace examples, and
   human annotations.
5. Inspect disputed or low-confidence examples before making model decisions.

## 12. Run Automated Tests

Every feature slice should have automated tests. Normal test runs should use
fakes, mocks, or HTTP contracts for Langfuse and provider calls so credentials
are not required.

```powershell
uv run pytest
```

Expected coverage areas:

- project config validation
- dataset identity generation and duplicate ID rejection
- Langfuse Dataset sync/resolve request handling
- baseline compatibility and reuse
- candidate execution with baseline reference
- provider tracing mode selection
- Langfuse unreachable fail-fast behavior
- human review sample selection
- CLI exit codes for success and failure paths
