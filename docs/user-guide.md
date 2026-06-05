# User Guide: Lightweight Langfuse Evaluation Harness

This harness runs evaluation projects from local configuration, logs runs to
Langfuse, and leaves trace inspection, evaluator execution, annotation queues,
scores, dashboards, and comparisons in Langfuse.

The normal workflow has three phases:

1. Create the project artifacts in the repository.
2. Sync those artifacts to Langfuse.
3. Execute baseline and candidate experiments.

## Core Concepts

- **Harness Project**: A reusable evaluation use case defined in a project YAML,
  such as `rewrite-quality` or another project slug.
- **Langfuse Project**: The Langfuse workspace/project that stores datasets,
  traces, prompts, score configs, evaluators, annotation queues, scores, and
  dashboards.
- **Dataset**: The local input rows for the experiment. CSV is the common path.
- **Task Prompt**: The prompt used by the baseline and candidates.
- **Evaluator Prompt**: A local prompt used to create an LLM-as-Judge evaluator.
- **Score Config**: The Langfuse score schema for a project metric.
- **Baseline**: The model and parameters used as the comparison anchor.
- **Candidate**: A model, prompt, or parameter variant compared to the baseline.
- **Run / Experiment**: One baseline or candidate execution over a dataset.
- **Human Annotation Queue**: A Langfuse queue for manual review and calibration.

Artifact relationships:

```text
Harness project config
  |
  |-- project metadata
  |-- dataset file
  |-- task prompt
  |-- evaluator prompts
  |-- score config definitions
  |-- baseline model config
  |-- candidate model configs
  `-- human review policy

sync-all
  |
  |-- sync-dataset
  |-- sync-prompts
  |-- sync-score-configs
  |-- sync-judge-evaluators
  `-- sync-annotation-queue

run baseline / run candidate
  |
  |-- Langfuse dataset run / experiment
  |-- trace per dataset item
  |-- model output observation
  |-- evaluator-ready metadata
  `-- automatic review selection when human_review.enabled is true
```

### Model Output Targeting

Standard LLM-as-Judge evaluators should target the final model output by role,
not by provider-specific observation name:

```yaml
target: observation
target_observation_role: model_output
```

For providers that create an inner Langfuse generation observation, the harness
marks the parent/container span as `run_item` and marks only the inner final
generation as `model_output`. For dry-run, Ollama, and other non-generation
paths, the parent span becomes the single `model_output` observation after a
successful response. This keeps evaluator rules portable across OpenAI-compatible,
Ollama, dry-run, and future providers without depending on names such as
`OpenAI-generation`.

If a provider uses native Langfuse tracing and cannot propagate the standard
role to exactly one final output observation, configure the evaluator with an
explicit `target_observation_name` for that special case. Duplicate
`model_output` markers cause evaluators to run more than once per dataset item;
missing markers prevent standard judges from scoring the run.

Boxed view:

```text
+-------------------------+          sync-all          +----------------------+
| Repository Artifacts    | -------------------------> | Langfuse Artifacts  |
| dataset, prompts, yaml  |                            | dataset, prompts,   |
| evaluator definitions   |                            | scores, judges,     |
| review policy           |                            | queues              |
+-----------+-------------+                            +----------+-----------+
            |                                                     |
            | run baseline / candidate                            |
            v                                                     v
+-------------------------+          traces            +----------------------+
| Harness Experiment Run  | -------------------------> | Langfuse Experiment |
| baseline or candidate   |                            | traces + scores     |
+-----------+-------------+                            +----------+-----------+
            |                                                     |
            | automatic or manual select-review                   |
            v                                                     v
+-------------------------+          review            +----------------------+
| Selected Review Items   | -------------------------> | Annotation Queue    |
+-------------------------+                            +----------------------+
```

## Setup

Use `uv` for Python environment management and command execution:

```bash
uv sync
```

Run commands through `uv run`:

```bash
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
```

Set `EVALUATOR_HARNESS_LIVE=1` when commands should use real Langfuse and model
provider credentials. Leave it unset or set it to `0` for local fake-backed
development and tests.

Required Langfuse environment variables:

```powershell
$env:LANGFUSE_PUBLIC_KEY="pk-lf-..."
$env:LANGFUSE_SECRET_KEY="sk-lf-..."
$env:LANGFUSE_HOST="https://cloud.langfuse.com"
$env:EVALUATOR_HARNESS_LIVE="1"
```

`LANGFUSE_BASE_URL` is still accepted as a compatibility alias, but new setup
should use `LANGFUSE_HOST`.

Credentials belong in `.env`, the shell, or a secret manager. Project YAML files
should store only environment variable names, never secret values.

## 1. Create Project Artifacts

Create and commit the local artifacts that define the harness project:

- Dataset file
- Task prompt
- Evaluator prompts
- Project YAML
- Score config definitions inside the project YAML

These files are the source of truth. Langfuse receives synchronized copies or
derived resources, but the repository owns the project definition.

### Dataset

For a local CSV dataset, create a file with an `input` column:

```csv
id,input
1,"Rewrite this paragraph in a professional tone."
2,"Simplify this technical explanation."
```

Rules:

- `input` is required.
- `id` is optional.
- If `id` is missing, the harness generates a stable item ID from row position
  and input hash.
- If explicit IDs are present, they must be unique.
- Extra columns are allowed when useful, such as `ground_truth`,
  `reference_output`, `tags`, or `notes`.
- `ground_truth` is optional. Evaluators that do not require it can still run.

Example dataset config:

```yaml
dataset:
  kind: local_csv
  path: datasets/rewrite_quality.csv
  langfuse_dataset_name: rewrite-quality/v1
  item_id_strategy: explicit_or_hash
```

Langfuse-authored datasets can be referenced by name:

```yaml
dataset:
  kind: langfuse
  langfuse_dataset_name: rewrite-quality/v1
  langfuse_dataset_version: v1
```

Use Langfuse-authored datasets only when you do not need the harness to execute
over those rows yet. Project runs currently need local CSV/JSON items so the
runner has inputs to send to the baseline and candidates.

### Task Prompt

Create the prompt that the baseline and candidates execute.

Text prompt example:

```text
Rewrite the following text according to the project instructions.

Input:
{{input}}
```

Chat-style prompt example:

```markdown
## role: system

You are a careful editor.

## role: user

Rewrite the following text:

{dataset.input}
```

Use `{dataset.<field>}` to substitute values from the active dataset row.
Candidate prompt overrides replace the full prompt; partial role inheritance is
out of scope.

Track prompt versions. If prompt content changes, bump the prompt version so
baseline reuse and comparisons remain reproducible.

### Evaluator Prompts

Evaluator prompts define what quality means for the project. Keep each prompt
focused on one metric.

Recommended pattern:

1. Evaluate one dimension only.
2. Include source input and the output being evaluated.
3. Include `baseline_output`, `ground_truth`, or reference fields only when the
   metric needs them.
4. Ask for reasoning, score, and confidence.
5. Return structured output that Langfuse can map into scores.

Example:

```text
You are evaluating one dimension: clarity.

Source input:
{{input}}

Output:
{{output}}

Ground truth, if present:
{{ground_truth}}

Return JSON:
{
  "reasoning": "short explanation",
  "score": 0.0,
  "confidence": 0.0
}
```

### Project YAML

The project YAML ties the dataset, prompts, models, evaluators, score configs,
and review policy together.

Minimal shape:

```yaml
project:
  name: rewrite-quality
  version: v1
  score_config_prefix: eh_rewrite_quality_

dataset:
  kind: local_csv
  path: datasets/rewrite_quality.csv
  langfuse_dataset_name: rewrite-quality/v1
  item_id_strategy: explicit_or_hash

prompt:
  path: prompts/rewrite_quality/task_prompt.md
  version: v1

baseline:
  name: gpt5.2-dgw-default
  provider: openai_compatible
  auth_mode: azure_client_credentials
  model: gpt5.2-dgw-default
  parameters:
    temperature: 0.2
    top_p: 1.0
    max_completion_tokens: 2048

candidates:
  - name: dry-run-candidate
    provider: dry_run
    auth_mode: none
    model: dry-run
    parameters:
      temperature: 0.0

evaluators:
  - name: clarity
    version: v1
    type: llm-as-judge
    source_type: custom
    target: observation
    prompt_path: prompts/rewrite_quality/evaluators/clarity.md
    score:
      name: clarity
      managed_by_harness: true
      data_type: NUMERIC
      min_value: 0
      max_value: 1
      description: Clarity score from 0.0 to 1.0.
    variables:
      - input
      - output

human_review:
  enabled: true
  queue_ownership: managed_by_harness
  review_policy_version: default
  minimum_sample_percent: 5
  minimum_sample_count: 1
  sample_strategy: stable
```

### Shared Evaluation Configs

Use `config_refs.evaluation` when several scenario-specific project configs
should share the same evaluators, judge setup, and human review policy:

```yaml
config_refs:
  evaluation: configs/shared/dfe_readability.yaml
```

The shared evaluation file may contain only these sections:

- `evaluators`
- `judge_setup`
- `human_review`

Keep project-owned sections in each scenario project YAML: `project`,
`dataset`, `task_prompt`, `baseline`, `candidates`, and optional `scenario`.
If a local project config and its shared evaluation config both define
`evaluators`, `judge_setup`, or `human_review`, validation fails instead of
choosing one silently.

Scenario metadata is optional. When present, all three fields are required:

```yaml
scenario:
  group: dfe
  name: general_public
  display_name: General public
```

Scenario fields are copied to Langfuse run metadata, trace metadata, CSV
exports, and Human Annotation Queue payload context as `scenario_group`,
`scenario_name`, and `scenario_display_name`. Use them for filtering scenario
runs and comparing scores across scenarios.

### Score Configs

Score config definitions live under each evaluator:

```yaml
score:
  name: clarity
  managed_by_harness: true
  data_type: NUMERIC
  min_value: 0
  max_value: 1
  description: Clarity score from 0.0 to 1.0.
```

Managed score configs use the project prefix, such as `eh_rewrite_quality_clarity`. The
harness creates or reuses compatible Langfuse score configs and fails on
incompatible active schemas.

If an evaluator intentionally uses a manually maintained Langfuse score config,
set `managed_by_harness: false` and provide the Langfuse score config ID. The
harness may validate the reference, but it will not create or modify that score
config.

Human annotations and LLM judges should share the canonical score config for
the same metric. Do not create separate score configs for automated and human
review of the same dimension.

## 2. Sync Artifacts to Langfuse

After the project artifacts exist locally, validate and sync them to Langfuse.

Validate first:

```powershell
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
```

Preview the full sync without mutating Langfuse:

```powershell
uv run python run_experiment.py sync-all --project configs/projects/rewrite_quality.yaml --dry-run
```

Apply the sync:

```powershell
uv run python run_experiment.py sync-all --project configs/projects/rewrite_quality.yaml
```

`sync-all` performs these phases:

- `sync-dataset`
- `sync-prompts`
- `sync-score-configs`
- `sync-judge-evaluators`
- `sync-annotation-queue`

It is the preferred setup command for normal use.

### DFE Scenario Projects

The DFE readability use case has three project configs with distinct datasets
and task prompts, all sharing `configs/shared/dfe_readability.yaml`:

```powershell
uv run python run_experiment.py validate --project configs/projects/dfe-general-public.yaml
uv run python run_experiment.py validate --project configs/projects/dfe-healthcare-provider.yaml
uv run python run_experiment.py validate --project configs/projects/dfe-public-health-sme.yaml
```

Preview setup for each scenario before mutating Langfuse:

```powershell
uv run python run_experiment.py sync-all --project configs/projects/dfe-general-public.yaml --dry-run
uv run python run_experiment.py sync-all --project configs/projects/dfe-healthcare-provider.yaml --dry-run
uv run python run_experiment.py sync-all --project configs/projects/dfe-public-health-sme.yaml --dry-run
```

Run baselines independently by scenario:

```powershell
uv run python run_experiment.py run --project configs/projects/dfe-general-public.yaml --mode baseline
uv run python run_experiment.py run --project configs/projects/dfe-healthcare-provider.yaml --mode baseline
uv run python run_experiment.py run --project configs/projects/dfe-public-health-sme.yaml --mode baseline
```

### Run Sync Phases Independently

Use individual sync commands for targeted repair, debugging, or partial setup.

Dataset only:

```powershell
uv run python run_experiment.py sync-dataset --project configs/projects/rewrite_quality.yaml
```

Prompts only:

```powershell
uv run python run_experiment.py sync-prompts --project configs/projects/rewrite_quality.yaml --dry-run
uv run python run_experiment.py sync-prompts --project configs/projects/rewrite_quality.yaml
```

Score configs only:

```powershell
uv run python run_experiment.py sync-score-configs --project configs/projects/rewrite_quality.yaml
```

Judge evaluators only:

```powershell
uv run python run_experiment.py sync-judge-evaluators --project configs/projects/rewrite_quality.yaml --dry-run
uv run python run_experiment.py sync-judge-evaluators --project configs/projects/rewrite_quality.yaml
```

Annotation queue only:

```powershell
uv run python run_experiment.py sync-annotation-queue --project configs/projects/rewrite_quality.yaml
```

### Prompt Sync

Repository prompt files remain the source of truth. Prompt sync publishes task
and evaluator prompts to Langfuse for review, dry-run checks, and prompt version
visibility.

`prompt.version` and evaluator `version` are strict release labels. If prompt
content changes after it has been synced, bump the relevant version before
publishing new content. Sync refuses to overwrite changed content under the same
prompt version.

### Judge Evaluator Sync

LLM-as-Judge evaluator setup supports:

- `custom` evaluators from local prompt files
- Langfuse `catalog` evaluators with `catalog_ref`
- `user_owned` evaluator references that are validated but not mutated

Harness-managed evaluator bindings are stored under:

```text
configs/langfuse/evaluator_bindings/
```

The binding file records which Langfuse evaluator and score config were created
or reused for each project evaluator key.

Judge evaluator rules target the resolved Langfuse score config ID for their
score dimension. Keep project YAML focused on score intent, such as
`score.name` and `managed_by_harness`; harness-managed remote score config IDs
are resolved during score config sync and recorded in evaluator bindings. This
lets LLM-as-Judge scores and Human Annotation Queue scores share the same score
config for comparison and calibration.

Harness-managed evaluator rule names use the canonical score config name, such
as `eh_gp_jargon_minimized`. Langfuse uses the evaluator rule name as the
automated evaluation score name, so matching the rule name to the score config
name lets automated `eval` scores and human `annotation` scores appear under the
same metric name.

### Annotation Queue Sync

Managed queues use this naming convention:

```text
EH_<project-slug>_<project-version>_review_<review-policy-version>
```

The local non-secret queue reference is stored under:

```text
.evaluator-harness/queue-references/
```

Langfuse Cloud Hobby currently allows only one Human Annotation Queue per
workspace. Keep `human_review.review_policy_version: default` unless your plan
supports additional queues. If the existing queue has incompatible score
configs, dry-run reports a conflict and asks you to delete the queue or use a
separate Langfuse project.

## 3. Execute Experiments

After artifacts are synced, run experiments.

### Run the Baseline

PowerShell one-line command:

```powershell
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode baseline
```

PowerShell multiline command:

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

The baseline run:

- Loads the project config.
- Validates the dataset.
- Runs the baseline model over every dataset item.
- Logs traces, model output observations, run metadata, prompt identity,
  parameters, latency, token usage, and cost when available.
- Records the baseline reference for compatible candidate runs.
- Automatically selects review items when `human_review.enabled: true`.

### Run a Candidate

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate dry-run-candidate `
  --baseline latest-compatible
```

The candidate run:

- Finds a compatible baseline.
- Runs the candidate over the same dataset.
- Records the baseline reference on every candidate output.
- Logs comparison metadata to Langfuse.
- Automatically selects review items when `human_review.enabled: true`.

Use `--baseline latest-compatible` for the newest matching baseline, or pass an
explicit baseline run ID when you need a specific prior run.

The harness rejects incompatible baselines instead of silently comparing against
a different project, dataset, prompt, baseline model, or baseline parameters.

### Candidate Variants

Candidates can vary by:

- Model
- Task prompt
- Generation parameters
- A mix of those axes

If a candidate changes the prompt plus another axis, the CLI asks for
confirmation. Use `--confirm-mixed-variant` for scripted runs.

Prompt variant example:

```yaml
candidates:
  - name: gpt5.2-dgw-default-prompt-v2
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt5.2-dgw-default
    task_prompt:
      path: prompts/rewrite_quality/task_prompt_v2.md
      version: v2
    parameters:
      temperature: 0.2
```

Parameter variant example:

```yaml
candidates:
  - name: gpt5.2-dgw-default-temp-high
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt5.2-dgw-default
    parameters:
      temperature: 0.8
```

### Human Review Selection

When `human_review.enabled: true`, baseline and candidate runs automatically
call review selection after generation. Run output includes:

- `review-selected`
- `review-queued`
- `review-duplicates-skipped`

Use `--skip-human-review` for generation-only runs:

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline `
  --skip-human-review
```

Use `select-review` directly for manual reruns, backfills, or sampling
overrides:

```powershell
uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run baseline-9e123c8aa836 `
  --sample-strategy random
```

Review sampling defaults to stable selection:

```yaml
human_review:
  enabled: true
  minimum_sample_percent: 5
  minimum_sample_count: 1
  sample_strategy: stable
```

`stable` makes the calibration cohort deterministic for a harness project,
dataset compatibility version, and review policy. Baseline and compatible
candidate runs therefore send the same dataset item IDs for human review;
run-specific risk items are additive.

Use `random` when repeated `select-review` runs should expand the calibration
set over time.

### Compare Runs in Langfuse

Use Langfuse for comparison, not local dashboards.

High-level comparison steps:

1. Open the project experiment or dataset run comparison view in Langfuse.
2. Select the baseline run.
3. Select candidate runs to compare.
4. Compare evaluator scores, latency, token usage, cost, trace-level examples,
   and human annotations.
5. Inspect low-confidence, failed, or disputed items.
6. Decide whether the candidate model, prompt, or parameter set is better than
   the baseline.

## Headless Workflow Summary

```powershell
# 1. Create project artifacts in the repository first.

# 2. Sync artifacts to Langfuse.
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
uv run python run_experiment.py sync-all --project configs/projects/rewrite_quality.yaml --dry-run
uv run python run_experiment.py sync-all --project configs/projects/rewrite_quality.yaml

# 3. Execute experiments.
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode baseline
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode candidate --candidate dry-run-candidate --baseline latest-compatible
```

## Live Smoke Tests

Live smoke tests are opt-in:

```bash
uv run pytest -m live
```

They skip when required Langfuse, Azure OpenAI, or annotation queue credentials
are not configured.

## References

- Langfuse datasets: https://langfuse.com/docs/evaluation/features/datasets
- Langfuse experiments via SDK: https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk
- Langfuse LLM-as-a-Judge: https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge
- Langfuse annotation queues: https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues
- Langfuse scores: https://langfuse.com/docs/evaluation/scores/overview
