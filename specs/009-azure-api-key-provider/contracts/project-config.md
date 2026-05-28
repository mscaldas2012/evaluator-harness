# Contract: Project Config for Azure Endpoint/API-Key Candidates

This contract describes the user-facing project configuration expectations.
Exact field names may be finalized during implementation, but the behavior must
remain compatible with this contract. Azure tenant/client credentials and Azure
endpoint/API-key credentials are authentication variants of one Azure-compatible
provider family. The harness selects the variant from each model's explicit
`auth_mode`; it must not auto-detect auth mode from available environment
variables.

## Valid Mixed Azure Shape

```yaml
baseline:
  name: gpt5.2-dgw-default
  provider: openai_compatible
  auth_mode: azure_client_credentials
  model: gpt5.2-dgw-default
  azure:
    tenant_id_env: REWRITE_QUALITY_BASELINE_AZURE_TENANT_ID
    client_id_env: REWRITE_QUALITY_BASELINE_AZURE_CLIENT_ID
    client_secret_env: REWRITE_QUALITY_BASELINE_AZURE_CLIENT_SECRET
    scope_env: REWRITE_QUALITY_BASELINE_AZURE_SCOPE
    subscription_key_env: REWRITE_QUALITY_BASELINE_AZURE_SUBSCRIPTION_KEY
    api_version_env: REWRITE_QUALITY_BASELINE_AZURE_API_VERSION
    endpoint_env: REWRITE_QUALITY_BASELINE_AZURE_ENDPOINT

candidates:
  - name: azure-mistral-large-3
    provider: openai_compatible
    auth_mode: api_key
    model: mistral-large-3
    azure_api_key:
      api_key_env: REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY
      endpoint_env: REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT
      api_version_env: REWRITE_QUALITY_MISTRAL_LARGE_3_API_VERSION
```

Each baseline or candidate receives its own provider instance and its own
credential references.

## Valid Candidate Shape

```yaml
candidates:
  - name: azure-api-key-candidate
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

`mistral-large-3` is an example deployment identifier only. Any compatible
Azure-hosted model deployment should be configurable with the same shape.

## Required Behavior

- `auth_mode: api_key` must not require tenant ID, client ID, client secret, or
  token scope fields.
- Credential fields must be environment variable names.
- `api_version_env` is required for Azure OpenAI deployment-style endpoint
  configs. Future endpoint shapes that do not require a service version must
  declare that explicitly.
- Missing required credential references must fail validation.
- Missing runtime environment variables must fail execution with an actionable
  redacted error.
- Existing `auth_mode: azure_client_credentials` configs must remain valid and
  keep their current behavior.
- The candidate must be runnable through the existing candidate command rather
  than a new command.
- Provider instances must be model-scoped, so a baseline and candidate can use
  different Azure accounts and auth modes in the same project.
- Auth mode must not be inferred from environment variable availability.
- Documentation examples should use project/model-specific environment variable
  names.

## Invalid Config Examples

Literal API key values are invalid:

```yaml
azure_api_key:
  api_key_env: sk-real-secret-value
```

Missing endpoint reference is invalid:

```yaml
azure_api_key:
  api_key_env: REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY
```

Missing API/service version is invalid for Azure OpenAI deployment-style
endpoints:

```yaml
azure_api_key:
  api_key_env: REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY
  endpoint_env: REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT
```

Mixed auth requirements are invalid for API-key candidates:

```yaml
auth_mode: api_key
azure:
  tenant_id_env: EDAV_TENANT_ID
```

## Rewrite Quality Requirement

The `configs/projects/rewrite_quality.yaml` project must include either:

- a documented Azure endpoint/API-key candidate example that can be enabled for
  live runs, or
- an active candidate entry when the required environment variables are
  available.

The plan and tasks must include validation and live smoke coverage for:

```powershell
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode baseline
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode candidate --candidate <azure-api-key-candidate>
```
