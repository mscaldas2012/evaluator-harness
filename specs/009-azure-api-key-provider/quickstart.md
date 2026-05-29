# Quickstart: Azure Endpoint/API-Key Candidate Provider

This guide describes the intended workflow for adding an Azure-hosted
endpoint/API-key model deployment as a candidate.

## 1. Set Environment Variables

Use environment variables or `.env` for secret values. Do not commit secret
values to project YAML.

```powershell
$env:REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY="..."
$env:REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT="https://example.openai.azure.com"
$env:REWRITE_QUALITY_MISTRAL_LARGE_3_API_VERSION="2024-12-01-preview"
```

Use project/model-specific names for real deployments, especially when the
baseline and candidates use different Azure accounts:

```powershell
$env:REWRITE_QUALITY_BASELINE_AZURE_ENDPOINT="https://..."
$env:REWRITE_QUALITY_BASELINE_AZURE_API_VERSION="..."
$env:REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY="..."
$env:REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT="https://..."
$env:REWRITE_QUALITY_MISTRAL_LARGE_3_API_VERSION="..."
```

The examples below use `REWRITE_QUALITY_MISTRAL_LARGE_3_*` names to avoid
credential collisions with the baseline.

## 2. Configure a Candidate

Example candidate shape:

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

The model name is only an example. The same pattern should work for any
compatible Azure-hosted model deployment that accepts endpoint/API-key access.
The provider family stays the same as other Azure-compatible deployments;
`auth_mode` selects API-key behavior for this candidate. The harness must not
auto-detect auth mode based on environment variables.

## 3. Validate Rewrite Quality

```powershell
uv run python run_experiment.py validate `
  --project configs/projects/rewrite_quality.yaml
```

Expected result: validation succeeds when the project contains valid
environment variable references. Runtime commands report missing variables by
name without printing secret values.

## 4. Run the Baseline

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

Expected result: the existing baseline runs with its tenant/client Azure
credentials and records Langfuse traces and baseline references.

## 5. Run the Azure API-Key Candidate

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate azure-mistral-large-3
```

Expected result: the candidate runs with endpoint/API-key authentication,
records model-output observations in Langfuse, and includes metadata needed by
LLM-as-Judge evaluator filters.

## 6. Verify Downstream Evaluation Metadata

After baseline and candidate runs:

- Confirm the baseline and candidate traces are present in Langfuse.
- Confirm each dataset item has a single run/item trace with the model
  generation nested under that trace, rather than a separate unrelated provider
  trace.
- Confirm the candidate model-output observation has `observation_role:
  model_output`.
- Confirm project name, project version, evaluator set ID, and baseline
  reference metadata are present.
- Confirm evaluator filters are scoped by project metadata and
  `observation_role=model_output`, not by a provider-specific generation name.
- Confirm no API-key values appear in traces, reports, or command output.

## 7. Test Commands

Default non-live verification:

```powershell
uv run pytest -p no:cacheprovider
```

Optional live verification:

```powershell
$env:RUN_LIVE_TESTS="1"
uv run pytest --no-cov -m live -vv
```

## Verification Results

Recorded on 2026-05-28:

- `uv run pytest --no-cov -p no:cacheprovider`: passed, 206 passed and 8 live
  tests skipped because `RUN_LIVE_TESTS` was not set.
- `uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml`:
  passed. Output listed baseline `gpt5.2-dgw-default` and candidates
  `llama3-local`, `llama3-local-temp-high`, `dry-run-candidate`, and
  `azure-mistral-large-3`.
- Live baseline run was not executed in this environment because Langfuse and
  EDAV Azure environment variables were not configured.
- Live Azure API-key candidate run was not executed in this environment because
  `REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY`,
  `REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT`, and
  `REWRITE_QUALITY_MISTRAL_LARGE_3_API_VERSION` were not configured.
- Langfuse trace inspection was not performed because the live runs were
  skipped. Fake integration coverage verifies candidate metadata includes the
  baseline reference, trace ID/name, evaluator set ID, project identity, and
  `observation_role: model_output`; rewrite-quality evaluator filters no longer
  include a provider-specific observation name or empty environment filter.
