# Quickstart: LLM-as-Judges

This guide describes the intended user workflow for setting up LLM-as-Judge
evaluators for an existing harness project.

## 1. Define Evaluators in the Project

Add or review evaluator definitions in:

```text
configs/projects/rewrite_quality.yaml
```

Each evaluator should define:

- name
- version
- single evaluation dimension
- target observation or trace
- run type eligibility
- prompt reference
- score target
- blind evaluation setting
- required inputs
- output schema
- filter profile

## 2. Write the Judge Prompt

Create or update the evaluator prompt:

```text
prompts/rewrite_quality/evaluators/clarity.md
```

The prompt should:

- evaluate one dimension only
- avoid provider/model identity
- describe required inputs
- request structured output with `reasoning`, `score`, and `confidence`

## 3. Validate the Project

```powershell
uv run python run_experiment.py validate `
  --project configs/projects/rewrite_quality.yaml
```

Validation should catch:

- missing evaluator versions
- missing score targets
- missing prompt files
- invalid blind prompts
- unscoped evaluator filters
- missing required inputs

Expected output:

```text
project: rewrite-quality/v1
dataset: local_csv (2 items)
baseline: gpt5.2-dgw-default
candidates: llama3-local, llama3-local-temp-high, dry-run-candidate
evaluators: clarity/v1
evaluator-targets: clarity=observation/model_output
score-targets: clarity=eh_rewrite_quality_clarity
```

## 4. Sync Score Configs

```powershell
uv run python run_experiment.py sync-score-configs `
  --project configs/projects/rewrite_quality.yaml
```

Harness-managed score configs are created or reused. User-owned score configs
are referenced only.

For each evaluator dimension, use the same score config for automated
LLM-as-Judge scores and Human Annotation Queue scores. For example, clarity
scores from both sources should use:

```text
eh_rewrite_quality_clarity
```

Score source mapping:

| Harness source | Langfuse source |
| -------------- | --------------- |
| `llm_judge` | `EVAL` |
| `human_annotation` | `ANNOTATION` |
| `api` | `API` |

## 4.1 Render Judge Prompt Setup

```powershell
uv run python run_experiment.py render-judge-prompts `
  --project configs/projects/rewrite_quality.yaml
```

Expected output:

```text
evaluator: clarity/v1
target: observation role=model_output
score: eh_rewrite_quality_clarity
shared_with_human_annotation_queue: true
score_sources:
  llm_judge: EVAL
  human_annotation: ANNOTATION
  api: API
filters:
  project: rewrite-quality
  project_version: v1
  evaluator_set_id: clarity:v1
  run_type: baseline,candidate
  observation_role: model_output
optional_narrowing:
  observation_name: OpenAI-generation
prompt: prompts\rewrite_quality\evaluators\clarity.md
```

## 4.2 Export Evaluator Setup

```powershell
uv run python run_experiment.py export-evaluator-setup `
  --project configs/projects/rewrite_quality.yaml
```

Expected output path:

```text
reports\rewrite-quality\evaluator-setup-rewrite-quality-v1.md
```

## 5. Run Baseline and Candidate Outputs

Run the baseline first:

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

Run a candidate later:

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate dry-run-candidate `
  --baseline latest-compatible
```

The model-output observations should expose metadata for Langfuse evaluator
filters.

## 6. Configure Langfuse Evaluator

In Langfuse, create an LLM-as-Judge evaluator using:

- target: Observation
- durable selector: `metadata.observation_role = model_output`
- score config: harness-managed or user-owned score target
- prompt: evaluator prompt text
- filters:
  - project
  - project version
  - evaluator set ID
  - observation role
  - run type

For the rewrite-quality clarity evaluator, use:

```yaml
metadata.project: rewrite-quality
metadata.project_version: v1
metadata.evaluator_set_id: clarity:v1
metadata.observation_role: model_output
metadata.run_type: baseline or candidate
optional_narrowing.observation_name: OpenAI-generation
```

`OpenAI-generation` is the current Azure/OpenAI observation name. Future
providers may use a different name, so the durable filter is
`observation_role=model_output` plus project metadata.

## 7. Review Scores in Langfuse

Use Langfuse to:

- inspect traces and observations
- view evaluator scores
- compare baseline and candidate score distributions
- inspect low-confidence or disputed scores
- route calibration samples to Human Annotation Queues

When reviewing human annotations, verify they write to the same score config as
the automated judge for that dimension. Use Langfuse's native score `source` to
distinguish automated and human scores:

| Harness source | Langfuse source |
| -------------- | --------------- |
| `llm_judge` | `EVAL` |
| `human_annotation` | `ANNOTATION` |

Do not create duplicate score configs for the same dimension.

## 8. Human Calibration

Run review selection after scored runs when calibration is needed:

```powershell
uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

Human review remains the check on LLM-as-Judge bias and scoring drift.

## 9. Verification Results

Local verification:

```text
uv run pytest --no-cov -p no:cacheprovider
150 passed, 5 skipped
```

Live verification with configured Langfuse and Azure OpenAI credentials:

```text
RUN_LIVE_TESTS=1 uv run pytest --no-cov -p no:cacheprovider -m live -vv
5 passed, 150 deselected
```
