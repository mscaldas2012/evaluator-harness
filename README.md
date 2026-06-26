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
For project-scoped commands, the harness loads root `.env` first and then
`.env.<project-name>` for the active project. Values already present in the
shell remain highest priority, project-specific file values override root `.env`
values, and missing `.env.<project-name>` files are ignored. For example,
`configs/projects/gso.yaml` with `project.name: gso` can use `.env.gso` for
GSO-specific credentials while shared values stay in `.env`.

Azure-hosted model configs use one Azure/OpenAI-compatible provider family with
explicit auth per baseline or candidate. A baseline can use
`auth_mode: azure_client_credentials` while a candidate uses `auth_mode:
api_key`; the harness builds provider behavior from each model config and does
not infer auth from whichever environment variables are set. Prefer
project/model-specific names such as `REWRITE_QUALITY_BASELINE_AZURE_ENDPOINT`
and `REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY` to avoid credential collisions.

Required for Langfuse:

```powershell
$env:LANGFUSE_PUBLIC_KEY="pk-lf-..."
$env:LANGFUSE_SECRET_KEY="sk-lf-..."
$env:LANGFUSE_HOST="https://cloud.langfuse.com"
$env:EVALUATOR_HARNESS_LIVE="1"
```

`LANGFUSE_BASE_URL` is still accepted as a compatibility alias.

## Codex Skills

This repository includes project-local Codex skills under `.agents/skills/`.
Use `$evaluator-harness-project-yaml` when creating a new harness project from a
dataset and prompt files. The skill guides Codex to inspect local artifacts, ask
for missing baseline/candidate/evaluator/review-policy choices, create
`configs/projects/<project>.yaml`, and run local validation.

Invoke it from this repository with:

```text
Use $evaluator-harness-project-yaml to create a project YAML from my dataset and prompts.
```

To make the skill available globally outside this repository, copy it into your
Codex skills folder:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force `
  .\.agents\skills\evaluator-harness-project-yaml `
  "$env:USERPROFILE\.codex\skills\"
```

## Prompt Sync

Repository prompt files remain the source of truth for task and LLM judge
execution. `sync-prompts` optionally publishes the project task prompt and local
LLM judge prompt files to Langfuse for review, dry-run checks, and prompt version
visibility.

Run dry-run mode first to preview changes:

```powershell
eval sync-prompts --project configs/projects/rewrite_quality.yaml --dry-run
```

Apply mode creates or reuses harness-managed Langfuse prompt versions and writes
local prompt binding references under `configs/langfuse/prompt_bindings/`:

```powershell
eval sync-prompts --project configs/projects/rewrite_quality.yaml
```

`prompt_version` is a strict release label. If prompt content changes after it
has been synced, bump the relevant `prompt_version` before publishing the new
content. Sync refuses to overwrite changed content under the same prompt version.

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

Required for the sample Azure endpoint/API-key candidate:

```powershell
$env:REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY="..."
$env:REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT="https://example.openai.azure.com"
$env:REWRITE_QUALITY_MISTRAL_LARGE_3_API_VERSION="2024-12-01-preview"
```

## Quickstart

```powershell
eval validate --project configs/projects/rewrite_quality.yaml
eval sync-all --project configs/projects/rewrite_quality.yaml --dry-run
eval sync-all --project configs/projects/rewrite_quality.yaml

eval run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline

eval run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate dry-run-candidate `
  --baseline latest-compatible

eval run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate gpt5.2-dgw-default-prompt-v2 `
  --baseline latest-compatible

eval run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate gpt5.2-dgw-default-temp-high `
  --baseline latest-compatible

eval run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate azure-mistral-large-3 `
  --baseline latest-compatible `
  --confirm-mixed-variant

eval comparison-report `
  --project rewrite-quality `
  --baseline <baseline-run-id> `
  --format html

eval campaign `
  --project configs/projects/rewrite_quality.yaml `
  --report-format both
```

Use Langfuse to run evaluators, inspect scores, compare baseline and candidate
runs, and review selected items in Human Annotation Queues. For local artifacts,
`comparison-report` can create Excel, HTML, or both from existing CSV exports;
campaign mode uses `--report-format excel|html|both` for the final comparison
artifact and defaults to Excel for compatibility.

### Evaluator Calibration

After a run has automated evaluator scores and completed human annotations in
Langfuse, capture the paired calibration evidence:

```powershell
eval calibration-capture `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

Calibration capture writes JSON and CSV artifacts under
`reports/<project>/calibration/`. Completed Langfuse annotation queue items are
the primary calibration cohort for a run: the harness matches completed queue
item trace IDs to traces from the run, then pairs automated `EVAL` scores with
human `ANNOTATION` scores for each evaluator. If live Langfuse trace lookup is
partial, capture can use the local run export CSV to complete the run context.

Summarize a captured snapshot with:

```powershell
eval calibration-summary `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

Summary artifacts report paired coverage, disagreement rate, mean absolute
score delta, and directional bias per evaluator. `directional_bias` is
`human_score - automated_score`, so negative values mean the human reviewer
scored lower than the automated evaluator.

### Shared Evaluation Configs And Scenarios

When one use case has multiple scenario-specific project configs, keep the
dataset, task prompt, baseline, candidates, and project identity in each project
YAML, and share only the evaluation setup:

```yaml
config_refs:
  evaluation: configs/shared/dfe_readability.yaml

scenario:
  group: dfe
  name: general_public
  display_name: General public
```

The referenced shared file may define `evaluators`, `judge_setup`, and
`human_review`. Scenario-owned sections such as `project`, `dataset`,
`task_prompt`, `baseline`, and `candidates` stay local to each project config.
If `scenario` is present, traces, exports, run metadata, and annotation queue
payloads include `scenario_group`, `scenario_name`, and
`scenario_display_name` for filtering and review context. Projects that do not
use scenarios do not need those fields.

DFE readability is split into three scenario project configs that reuse the
same shared evaluation setup:

```powershell
eval validate --project configs/projects/dfe-general-public.yaml
eval validate --project configs/projects/dfe-healthcare-provider.yaml
eval validate --project configs/projects/dfe-public-health-sme.yaml
```

When `human_review.enabled: true`, baseline and candidate runs automatically
select completed outputs for human review after the model run finishes. Pass
`--skip-human-review` on `run` when you need generation only. The
`select-review` command remains available for manual reruns, backfills, or
one-off sampling overrides.

Candidates can vary by model, task prompt, generation parameters, or a mix of
those axes. Add `task_prompt` under a candidate to test prompt-v2 against an
existing compatible prompt-v1 baseline; the harness records both prompt
identities on runs, traces, evaluator payloads, and review payloads. Parameter
variants are separate candidates with distinct `parameters`; traces and exports
include `generation_parameter_hash`, `parameter_identity`, and
`variant_identity`. If a candidate changes more than one axis, the CLI asks for
`Y`/`y` confirmation unless `--confirm-mixed-variant` is supplied.

## LLM-as-Judge Setup

Evaluator definitions live in the project YAML. Each LLM-as-Judge evaluator is
validated locally for target, run types, judging mode, blind defaults, prompt
reference, result contract, score target, and Langfuse filter profile.

Render the Langfuse-ready setup values:

```powershell
eval render-judge-prompts `
  --project configs/projects/rewrite_quality.yaml
```

Export a lightweight setup document:

```powershell
eval export-evaluator-setup `
  --project configs/projects/rewrite_quality.yaml
```

Preview direct Langfuse evaluator setup without mutation:

```powershell
eval sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml `
  --dry-run
```

Apply creates missing harness-managed evaluators, reuses compatible remote
evaluators, updates only safe operational fields, writes non-secret binding
records, and inactivates superseded harness-managed versions where Langfuse
supports it:

```powershell
eval sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml
```

Technical Debt: evaluator setup currently keeps two Langfuse adapter paths. The
SDK implementation remains in place for the future stable SDK evaluator
resource, while the live fallback calls Langfuse's unstable
`/api/public/unstable/evaluation-rules` REST API so create, list, lookup, and
safe update/inactivation work today. The fallback must be retired when Langfuse
ships stable SDK support for LLM-as-Judge evaluator CRUD. Deletes remain out of
scope.

Audit compares project definitions, local bindings, and remote evaluator state
without mutation:

```powershell
eval sync-judge-evaluators `
  --project configs/projects/rewrite_quality.yaml `
  --audit
```

Managed evaluator names use:

```text
EH_<project>_<version>_judge_<dimension>_<evaluator-version>_<source-type>_<target>
```

Human Annotation Queue scores use the harness-managed Langfuse score config for
the evaluator dimension, such as `eh_rewrite_quality_clarity`. Langfuse
LLM-as-Judge evaluator scores are emitted under the evaluator name, such as
`EH_rewrite-quality_v1_judge_clarity_v1_custom_observation`, with score source
`EVAL`. Compare automated and human scores by dimension, score source, and
dashboard grouping:

| Harness source | Langfuse source |
| -------------- | --------------- |
| `llm_judge` | `EVAL` |
| `human_annotation` | `ANNOTATION` |

Do not create source-specific score configs such as
`eh_rewrite_quality_clarity_llm_judge` or
`eh_rewrite_quality_clarity_human`.

Trace names use a stable, scannable format:

```text
rewrite-quality/baseline-gpt5.2-dgw-default
rewrite-quality/gpt5.2-dgw-default-prompt-v2
test/rewrite-quality/baseline-gpt5.2-dgw-default
```

The `test/` prefix is added for pytest-driven live smoke traces. Candidate
trace names use the candidate config name, baseline trace names use
`baseline-<baseline config name>`, and item IDs, model names, provider names,
run IDs, prompt versions, and parameters are stored in trace metadata instead
of the trace name. For Azure/OpenAI runs, the meaningful
`OpenAI-generation` observation is linked to the same parent trace ID where the
harness stores dataset input, final output, and evaluation metadata.

Managed annotation queues use the name
`EH_<project-slug>_<project-version>_review_<review-policy-version>` and store a
non-secret local reference under `.evaluator-harness/queue-references/`.
`LANGFUSE_ANNOTATION_QUEUE_ID` is only needed for an explicit user-owned queue
or temporary override.

`sync-all` is the preferred setup command for a project. It synchronizes the
Langfuse dataset, prompt versions, score configs, LLM judge evaluators, and
annotation queue in one run. Use `--dry-run` first to preview the planned
dataset, prompt, score config, judge, and queue changes without mutating
Langfuse. The individual commands remain available for targeted repair or
debugging: `sync-dataset`, `sync-prompts`, `sync-score-configs`,
`sync-judge-evaluators`, and `sync-annotation-queue`.

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

For local code quality reporting, run Ruff, Pyright, Import Linter, Radon, pytest
coverage, and Vulture together:

```powershell
uv run python scripts/quality_report.py
```

The report command writes tool output, JUnit XML, coverage XML, a coverage
summary, and HTML coverage files under `reports/quality/`. Vulture findings are
reported as warning-only because dynamic CLI and fixture code can produce false
positives.

Opt-in live smoke tests hit configured Langfuse and Azure OpenAI resources:

```powershell
uv run pytest -m live
```

## Documentation

- User guide: `docs/user-guide.md`
- Langfuse automation backlog: `docs/langfuse-automation-backlog.md`
- Spec Kit feature docs: `specs/002-live-langfuse-mvp/`

