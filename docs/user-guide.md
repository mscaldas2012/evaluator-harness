# User Guide: Lightweight Langfuse Evaluation Harness

This harness is intended to run headless. The local tool should be a CLI that
executes evaluation projects and logs complete run metadata to Langfuse.
Langfuse provides the UI for traces, evaluators, annotation queues, dashboards,
and comparisons.

No local UI is required for the MVP. A local UI would only be justified later if
non-technical users need guided project setup or if repeated project
configuration becomes error-prone in files.

## Core Concepts

- **Project**: A reusable evaluation use case, such as `rewrite-quality`,
  `support-answer-helpfulness`, or `rag-groundedness`.
- **Dataset**: Inputs to evaluate. The default format is CSV with an `input`
  column.
- **Baseline**: The model and parameter set used as the comparison anchor for a
  project.
- **Candidate**: A model or model-parameter variant compared against the
  baseline.
- **Evaluator**: A Langfuse-owned scoring method, usually an LLM-as-a-Judge
  prompt or a deterministic metric.
- **Run**: One execution of a baseline or candidate over a project dataset.
- **Human Annotation Queue**: A Langfuse review queue for manual inspection and
  calibration.

## 1. Set Up Local Python Environment

Use `uv` for Python environment management, dependency setup, and command
execution.

```bash
uv sync
```

Run the harness and tests through `uv run`, for example
`uv run python run_experiment.py ...` and `uv run pytest`.

Set `EVALUATOR_HARNESS_LIVE=1` when you want commands to use the real
Langfuse SDK and provider credentials. Leave it unset or `0` for credential-free
offline tests and fake-backed local development.

## 2. Prepare Langfuse

In Langfuse, set up the workspace that will store experiments:

1. Create or select a Langfuse project.
2. Create API credentials for the harness.
3. Decide where datasets are authored:
   - Prefer local CSV/JSON committed with the project. This is the normal path
     today.
   - Langfuse Datasets managed directly in the Langfuse UI are useful for
     review and comparison, but the harness does not yet fetch Langfuse-authored
     dataset rows for execution.
4. Let the harness import local datasets as Langfuse Datasets before valid
   experiment execution.
5. Optionally sync task and LLM judge prompts to Langfuse for review and prompt
   version visibility.
6. Let the harness create or resolve harness-managed evaluator score configs
   with the project score prefix.
7. Let the harness create or resolve a project-managed Human Annotation Queue,
   or configure a user-owned queue ID when you want to manage the queue
   manually.

The harness should fail fast if Langfuse is unreachable. Runs without Langfuse
logging are not considered valid experiment runs.

Use `LANGFUSE_HOST` for new setup. `LANGFUSE_BASE_URL` remains accepted as a
compatibility alias.

## 3. Create a Harness Project

Create a project config that defines the evaluation use case.

Project configs are intended to be committed. They must contain only stable
project settings and environment variable names such as `EDAV_CLIENT_SECRET`.
Actual credential values belong in `.env`, the host environment, or a secret
manager, and must not be checked in.

Azure-hosted models use one Azure/OpenAI-compatible provider family with an
explicit `auth_mode` per baseline or candidate. Use
`azure_client_credentials` for tenant/client auth and `api_key` for
endpoint/API-key auth. The harness must not auto-detect auth mode from
environment variables, because a shell may contain credentials for several
baselines and candidates at once. Prefer project/model-specific variable names
such as `REWRITE_QUALITY_BASELINE_AZURE_ENDPOINT` and
`REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY`.

Example:

```yaml
project:
  name: rewrite-quality
  description: Compare model outputs for a rewrite task.
  version: v1
  score_config_prefix: eh_rewrite_quality_

dataset:
  path: datasets/rewrite_quality.csv
  version: v1

prompt:
  path: prompts/rewrite_quality/task_prompt.md
  version: v1

baseline:
  name: gpt-4.1-baseline
  provider: openai-compatible
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
  - name: dry-run-candidate
    provider: dry_run
    auth_mode: none
    model: dry-run
    parameters:
      temperature: 0.0
      top_p: 1.0
      max_tokens: 2048
  - name: azure-mistral-large-3
    provider: openai_compatible
    auth_mode: api_key
    model: mistral-large-3
    azure_api_key:
      api_key_env: REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY
      endpoint_env: REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT
      api_version_env: REWRITE_QUALITY_MISTRAL_LARGE_3_API_VERSION
    parameters:
      temperature: 0.2
      top_p: 1.0
      max_tokens: 2048
      token_limit_parameter: max_completion_tokens

evaluators:
  - name: clarity
    type: llm-as-judge
    prompt_path: prompts/rewrite_quality/evaluators/clarity.md
    version: v1
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
  queue_ownership: managed_by_harness
  review_policy_version: default
  minimum_sample_percent: 5
  prioritize:
    - failures
    - low_confidence
    - disputed
```

The Azure `*_env` fields are references to environment variables, not the secret
values themselves. For example, `client_secret_env: EDAV_CLIENT_SECRET` tells the
harness to read the client secret from an environment variable named
`EDAV_CLIENT_SECRET`. For API-key candidates, `api_key_env` and `endpoint_env`
are also environment variable names; do not place API keys or endpoint values
directly in project YAML.

Rewrite quality is only one project. Future projects should define their own
datasets, prompts, baseline, candidates, and evaluator prompts.

The project config does not include a tracing mode. Provider adapters choose the
best tracing strategy internally: Azure OpenAI should use the Langfuse-wrapped
client, while providers without a compatible Langfuse integration can use an
adapter-owned manual tracing fallback.

The `dry_run` provider is a first-class candidate path for smoke testing live
Langfuse baseline reuse without calling a second live model provider.

## 4. Create the Dataset

For the simplest local dataset, create a CSV with an `input` column.

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
- Extra columns are allowed when they are useful for the project, such as
  `tags`, `notes`, `expected_tone`, `reference_output`, or `ground_truth`.
- `ground_truth` is optional. When present, baseline and candidate evaluators
  can use it as a reference value. When absent, baseline and candidate runs
  should still proceed; evaluators that do not require ground truth can still
  run.
- Before a valid experiment run, the harness should create or update a matching
  Langfuse Dataset from the local file and record the Langfuse dataset identity
  and version.
- If Langfuse does not expose a dataset version, the harness derives a dataset
  compatibility version from stable item IDs and input hashes for baseline
  matching.

For example, DFE uses a committed CSV as the source of truth:

```yaml
dataset:
  kind: local_csv
  path: datasets/DFE.csv
  langfuse_dataset_name: dfe/v1
  item_id_strategy: explicit_or_hash
```

Run `sync-dataset` to upload or update the rows in Langfuse:

```bash
uv run python run_experiment.py sync-dataset \
  --project configs/projects/dfe.yaml
```

The harness still executes from `datasets/DFE.csv`. Langfuse receives the
dataset items so traces can be attached to dataset runs, compared in the UI,
and routed to review workflows.

Langfuse-authored datasets can be referenced by name:

```yaml
dataset:
  kind: langfuse
  langfuse_dataset_name: dfe/v1
  langfuse_dataset_version: v1
```

Use this only when you do not need the harness to execute over those rows yet.
At the moment, project runs need local CSV/JSON items so the runner has inputs
to send to the baseline and candidates.

## 5. Write the Task Prompt

Create the prompt that candidate models will execute.

Example `prompts/rewrite_quality/task_prompt.md`:

```text
Rewrite the following text according to the project instructions.

Input:
{{input}}
```

For chat-style prompts, use role sections in the same Markdown prompt file.
Each message starts with a level-2 heading in the form
`## role: <role-label>`. Role labels are generic; `system`, `user`, and
`assistant` are common examples.

Example `prompts/dfe/task_prompt.md`:

```markdown
## role: system

You are a careful editor.

## role: user

Rewrite the following text:

{dataset.input}
```

Use `{dataset.<field>}` to substitute values from the active dataset row.
`{dataset.input}` resolves to the dataset `input` column. Other dataset columns
can be referenced the same way, as long as the column exists. Empty row values
render as empty strings. If the selected provider cannot send the configured
role labels exactly, validation fails before any model call. Candidate prompt
overrides replace the full prompt; partial role inheritance is out of scope.

Track prompt versions. If the prompt changes, treat it as a new version so
baseline reuse rules remain clear.

## 6. Create LLM-as-a-Judge Evaluator Prompts

Evaluator prompts belong to the project. They define what quality means for that
project. The harness should not hard-code rewrite quality or any other scoring
dimension.

Recommended evaluator prompt pattern:

1. Evaluate one dimension only.
2. Keep `blind: true` for model-quality and baseline/candidate comparisons.
   Non-blind evaluators are diagnostic only and must set `blind: false` with
   `non_blind_reason`.
3. Include the source input, the output being evaluated, optional
   `baseline_output`, optional `ground_truth`, and any reference fields needed
   for the evaluator.
4. Ask for reasoning, score, and confidence.
5. Return structured output that Langfuse can map into scores.

Example `prompts/rewrite_quality/evaluators/clarity.md`:

```text
You are evaluating one dimension: clarity.

Source input:
{{input}}

Output:
{{output}}

Ground truth, if present:
{{ground_truth}}

Instructions:
- Judge whether the candidate is clear and easy to understand.
- Ignore provider identity, model identity, cost, and latency.
- Do not evaluate tone, factuality, or brevity unless they affect clarity.
- Explain the reasoning before assigning the score.

Return JSON:
{
  "reasoning": "short explanation",
  "score": 0.0,
  "confidence": 0.0
}
```

In Langfuse, configure an LLM-as-a-Judge evaluator that uses this prompt and maps
the run fields into the prompt variables. Langfuse should own evaluator
execution and score storage.

Before running evaluators, sync the harness-managed score configs:

```bash
uv run python run_experiment.py sync-score-configs \
  --project configs/projects/rewrite_quality.yaml
```

The harness only creates or resolves score configs it manages. Managed score
configs use the project prefix, for example `eh_rewrite_quality_clarity`, so
they are distinguishable from manually maintained Langfuse score configs. If a
managed score config already exists with incompatible schema, the harness should
fail instead of updating it. The user must delete or rename the existing score
config in Langfuse before running the sync again. Archiving alone is accepted
only if Langfuse no longer treats that score config name as conflicting.

If an evaluator intentionally uses a manually maintained Langfuse score config,
set `managed_by_harness: false` and provide the Langfuse score config ID. The
harness may validate the reference, but it should not create or modify that
config. Langfuse still owns the score results in both cases; this flag controls
only whether the harness may create or resolve the score config schema.

When `blind: true`, the harness should prepare judge inputs with neutral labels
such as `baseline` and `candidate` or `output A` and `output B`. Provider,
model, vendor, latency, and cost metadata remain available in Langfuse trace
metadata, but they should not be included in the judge prompt.

Human Annotation Queue scores for a dimension use the canonical Langfuse score
config, such as `eh_rewrite_quality_clarity`. Langfuse LLM-as-Judge evaluator
scores are emitted under the evaluator name, with Langfuse score source `EVAL`.
Compare automated and human scores by evaluator dimension, score name, and
Langfuse score source:

| Harness source | Langfuse source |
| -------------- | --------------- |
| `llm_judge` | `EVAL` |
| `human_annotation` | `ANNOTATION` |

Do not create separate clarity score configs for automated and human review.
The score config remains the canonical human annotation schema; the evaluator
name identifies the automated judge score in Langfuse dashboards.

Evaluator definitions can support baseline mode, candidate mode, or both.
Baseline-mode evaluator payloads use the baseline output as `output` and include
`ground_truth` when the dataset item provides it. Candidate-mode payloads use the
candidate output as `output` and can also include `baseline_output` and
`ground_truth`.

## 7. Run the Baseline

Run the baseline first for the project.

Example command shape:

```bash
uv run python run_experiment.py \
  --project configs/projects/rewrite_quality.yaml \
  --mode baseline
```

Expected behavior:

- The harness loads the project config.
- It validates the dataset.
- It runs the baseline model over all dataset items.
- It logs traces, run metadata, prompt version, model parameters, latency,
  tokens, costs where available, and dataset item IDs to Langfuse.
- It creates evaluator-ready baseline records so Langfuse evaluators can score
  the baseline itself, with or without `ground_truth`.
- It records the baseline run identity for later candidate runs.

## 8. Run One Candidate Model

Run a candidate against the existing compatible baseline.

```bash
uv run python run_experiment.py \
  --project configs/projects/rewrite_quality.yaml \
  --mode candidate \
  --candidate llama3-local \
  --baseline latest-compatible
```

Expected behavior:

- The harness finds a compatible baseline run.
- It does not rerun the baseline if one already exists.
- It runs the candidate model over the same project dataset.
- It records the baseline reference on every candidate output.
- It logs all traces and metadata to Langfuse.

Later, you can run more candidates against the same baseline:

```bash
uv run python run_experiment.py \
  --project configs/projects/rewrite_quality.yaml \
  --mode candidate \
  --candidate mistral-local \
  --baseline latest-compatible
```

Baseline reuse is valid only when the project, dataset version, baseline task
prompt version, evaluator set, and baseline model parameters are compatible.
Use `--baseline latest-compatible` for the newest matching baseline, or pass an
explicit baseline run ID such as `--baseline baseline-abc123` when you want a
specific prior run. The harness rejects incompatible baselines instead of
silently comparing against a different project, dataset, prompt, or baseline
parameter set.

Candidates may intentionally vary the model, task prompt, generation
parameters, or a mix of those axes. The baseline reference stays tied to the
baseline configuration, while candidate trace metadata records the active
candidate identity for comparison in Langfuse.

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
      template_variables:
        - input
    parameters:
      temperature: 0.2
      top_p: 1.0
      max_tokens: 2048
      token_limit_parameter: max_completion_tokens
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
      top_p: 1.0
      max_tokens: 2048
      token_limit_parameter: max_completion_tokens
```

Prompt and parameter metadata is stored on runs, traces, evaluator payloads,
annotation queue payloads, and CSV exports. Use `candidate_prompt_identity`,
`baseline_prompt_identity`, `generation_parameter_hash`, `parameter_identity`,
and `variant_identity` in Langfuse filters or exports when comparing variants.
If a candidate changes more than one axis, the CLI prompts for confirmation;
type `Y` or `y`, or pass `--confirm-mixed-variant` for scripted runs.

## 8.1 Add Another Model Configuration

Most model additions should be config-only. Add a new entry under `candidates`
with a unique `name`, a supported `provider`, explicit generation parameters,
and only environment variable names for credentials.

OpenAI-compatible Azure candidate example:

```yaml
candidates:
  - name: azure-gpt41-mini-low-temp
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt-4.1-mini
    azure:
      tenant_id_env: EDAV_TENANT_ID
      client_id_env: EDAV_CLIENT_ID
      client_secret_env: EDAV_CLIENT_SECRET
      scope_env: EDAV_SCOPE_TOKEN_AUDIENCE
      subscription_key_env: EDAV_SUBSCRIPTION_KEY
      api_version_env: EDAV_AZURE_OPENAI_API_VERSION
      endpoint_env: EDAV_AZURE_OPENAI_ENDPOINT
    parameters:
      temperature: 0.1
      top_p: 1.0
      max_tokens: 1024
```

Azure endpoint/API-key candidate example:

```yaml
candidates:
  - name: azure-mistral-large-3
    provider: openai_compatible
    auth_mode: api_key
    model: mistral-large-3
    azure_api_key:
      api_key_env: REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY
      endpoint_env: REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT
      api_version_env: REWRITE_QUALITY_MISTRAL_LARGE_3_API_VERSION
    parameters:
      temperature: 0.2
      top_p: 1.0
      max_tokens: 2048
      token_limit_parameter: max_completion_tokens
```

Ollama local candidate example:

```yaml
candidates:
  - name: llama3-local-fast
    provider: ollama
    auth_mode: none
    model: llama3
    endpoint: http://localhost:11434
    parameters:
      temperature: 0.2
      top_p: 1.0
      max_tokens: 2048
```

Run the new model with the same CLI shape:

```bash
uv run python run_experiment.py run \
  --project configs/projects/rewrite_quality.yaml \
  --mode candidate \
  --candidate azure-mistral-large-3 \
  --baseline latest-compatible
```

The provider factory is driven by `provider`. `openai_compatible` uses the
Langfuse-wrapped Azure OpenAI path when available for tenant/client auth. The
API-key path currently uses the harness manual generation span so it can attach
the generation to the existing parent trace and preserve evaluator metadata.
`ollama` uses manual tracing metadata because there is no compatible
Langfuse-wrapped Ollama client in the MVP. Project configs should not include a
tracing mode; adapters choose and record the tracing strategy internally.

If a provider is not `openai_compatible` or `ollama`, add a small adapter under
`src/evaluator_harness/providers/` and register it in the provider factory.
Avoid plugin systems or workflow changes unless a provider cannot fit the
existing `ModelProvider.generate()` shape.

## 9. Configure Langfuse Evaluators

The harness can now set up Langfuse LLM-as-Judge evaluators directly from
project configuration.

Preview setup first:

```powershell
uv run python run_experiment.py sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml `
  --dry-run
```

Apply setup:

```powershell
uv run python run_experiment.py sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml
```

Audit existing setup without mutation:

```powershell
uv run python run_experiment.py sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml `
  --audit
```

Evaluator setup supports `custom` evaluators with local prompt/version
contracts, Langfuse `catalog` evaluators with `catalog_ref`, and `user_owned`
evaluator references that are validated but not mutated. Harness-managed
evaluator bindings are stored as non-secret YAML under
`configs/langfuse/evaluator_bindings/` and are required before updates or
inactivation. Sampling defaults to `100`; historical backfill is disabled
unless explicitly enabled and supported by the selected Langfuse target.

The project config is the source of truth for the evaluator definition. It
declares what evaluator should exist, including its `name`, `version`,
`source_type`, target, prompt path, output schema, filters, judge model, and
score configuration. The evaluator binding file is sync state. It records which
Langfuse evaluator and score config were created or reused for that project
evaluator key.

For example, `configs/projects/rewrite_quality.yaml` declares the desired
`clarity` evaluator and points at the binding file:

```yaml
judge_setup:
  binding_path: configs/langfuse/evaluator_bindings/rewrite-quality.yaml

evaluators:
  - name: clarity
    version: v1
    source_type: custom
    target: observation
    prompt_path: prompts/rewrite_quality/evaluators/clarity.md
    score:
      name: clarity
      managed_by_harness: true
```

After `sync-judge-evaluators` runs, the binding file records the remote
Langfuse resources for the same key:

```yaml
bindings:
  - project: rewrite-quality
    project_version: v1
    evaluator_name: clarity
    evaluator_version: v1
    source_type: custom
    target: observation
    langfuse_evaluator_id: cmpokarfl00lmad0e8ko1tlz4
    langfuse_display_name: EH_rewrite-quality_v1_judge_clarity_v1_custom_observation
    score_config_id: cb709a27-8a26-4923-8828-f1ea9df2182d
    score_config_name: eh_rewrite_quality_clarity
```

The binding key is `project`, `project_version`, `evaluator_name`,
`evaluator_version`, `source_type`, and `target`. Changing one of those fields
creates a different binding identity. Changing implementation details such as
prompt text while keeping the same key lets the sync planner update or reuse the
existing harness-managed Langfuse evaluator. Edit the project config for normal
evaluator changes; edit the binding file only when intentionally repairing or
re-pointing local sync state to existing Langfuse resources.

Manual Langfuse checks remain useful:

1. Open the Langfuse project.
2. Confirm the baseline and candidate runs appear as dataset or experiment runs.
3. Confirm the Human Annotation Queue uses the harness-managed score config
   created by `sync-score-configs`.
4. Create LLM-as-a-Judge evaluators for the project dimensions.
5. Use the project evaluator prompts and map variables such as:
   - `input`
   - `baseline_output`
   - `candidate_output`
   - `reference_output`, if present
   - project metadata, if needed
6. Scope evaluators to the relevant model-output observations using project
   metadata such as `project`, `project_version`, `evaluator_set_id`,
   `run_type`, and `observation_role=model_output`.
7. Run evaluators in Langfuse.
8. Inspect generated scores and judge traces in Langfuse.

Evaluator prompts should be versioned. If an evaluator prompt changes, record a
new evaluator version so future comparisons remain reproducible.

## 10. Perform Human Annotation

Human review is used for calibration and disputed outputs. Automated scores are
decision support, not objective truth.

MVP behavior:

1. The project can use a harness-managed Langfuse Human Annotation Queue.
2. The harness creates or reuses the managed queue with this naming convention:

```text
EH_<project-slug>_<project-version>_review_<review-policy-version>
```

For example:

```text
EH_rewrite-quality_v1_review_default
```

3. The reusable non-secret local queue reference is stored under:

```text
.evaluator-harness/queue-references/<project-slug>__<project-version>__<review-policy-version>.json
```

4. The harness selects at least 5% of evaluated outputs for review.
5. Selection prioritizes:
   - a stable random calibration cohort based on dataset item IDs
   - failed outputs
   - low-confidence evaluator outputs
   - disputed outputs
6. Selected items should include:
   - source input
   - baseline output
   - candidate output
   - evaluator output
   - trace context

Managed queue setup:

```bash
uv run python run_experiment.py sync-score-configs \
  --project configs/projects/rewrite_quality.yaml

uv run python run_experiment.py sync-annotation-queue \
  --project configs/projects/rewrite_quality.yaml
```

Queue routing no longer requires `LANGFUSE_ANNOTATION_QUEUE_ID` for managed
queues. Duplicate selected items for the same queue are skipped when selection
is rerun.

To use a manually managed queue instead, configure:

```yaml
human_review:
  enabled: true
  queue_ownership: user_owned
  annotation_queue_id: existing-langfuse-queue-id
```

The optional `LANGFUSE_ANNOTATION_QUEUE_ID` environment variable remains
available as a temporary override when `fallback_to_env: true`.

The random calibration cohort is deterministic for a project, dataset
compatibility version, and review policy. Baseline and compatible candidate runs
therefore send the same dataset item IDs for human review; run-specific risk
items are additive.

## 11. Compare Runs in Langfuse

Use Langfuse for comparison, not local dashboards.

High-level comparison steps:

1. Open the project experiment or dataset run comparison view in Langfuse.
2. Select the baseline run.
3. Select candidate runs to compare.
4. Compare:
   - evaluator scores
   - latency
   - token usage
   - cost, when available
   - trace-level examples
   - human annotations
5. Inspect low-confidence, failed, or disputed items.
6. Decide whether the candidate model or parameter set is better than the
   baseline for the project.

## 12. Expected Headless Workflow

A typical headless workflow looks like this:

```bash
# Validate project configuration and sync required Langfuse assets
uv run python run_experiment.py validate \
  --project configs/projects/rewrite_quality.yaml

uv run python run_experiment.py sync-dataset \
  --project configs/projects/rewrite_quality.yaml

uv run python run_experiment.py sync-score-configs \
  --project configs/projects/rewrite_quality.yaml

# Optional: publish task and LLM judge prompts to Langfuse
uv run python run_experiment.py sync-prompts \
  --project configs/projects/rewrite_quality.yaml \
  --dry-run

uv run python run_experiment.py sync-prompts \
  --project configs/projects/rewrite_quality.yaml

uv run python run_experiment.py sync-annotation-queue \
  --project configs/projects/rewrite_quality.yaml

# Run or create the baseline
uv run python run_experiment.py run \
  --project configs/projects/rewrite_quality.yaml \
  --mode baseline

# Run one candidate against the compatible baseline
uv run python run_experiment.py run \
  --project configs/projects/rewrite_quality.yaml \
  --mode candidate \
  --candidate llama3-local \
  --baseline latest-compatible
```

Then use Langfuse for evaluator execution, annotation, and comparison.

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
