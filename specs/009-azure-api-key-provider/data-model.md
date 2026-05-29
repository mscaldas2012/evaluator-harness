# Data Model: Azure API-Key Candidate Provider

## API-Key Azure Credential References

Non-secret configuration that tells the harness which environment variables to
read for an Azure endpoint/API-key candidate.

### Fields

- `api_key_env`: required environment variable name for the API key.
- `endpoint_env`: required environment variable name for the Azure model
  endpoint.
- `api_version_env`: required environment variable name for Azure OpenAI
  deployment-style endpoints. Future endpoint shapes that do not require a
  service version must declare that explicitly in config validation.
- `subscription_key_env`: optional environment variable name for deployments
  that require an additional subscription header.

### Validation Rules

- Values must be environment variable names, not literal secret values.
- Required references must be present when a model uses API-key auth.
- `api_version_env` is required for Azure OpenAI deployment-style endpoints.
- Missing runtime environment variables fail with the variable name and without
  printing any secret value.
- API-key references must not require tenant ID, client ID, client secret, or
  token scope fields.

## Azure-Compatible Model Config

A baseline or candidate model configuration for an Azure-hosted deployment.
The provider family remains the same while `auth_mode` selects the credential
shape for that specific model.

### Fields

- `name`: project-local baseline or candidate name.
- `provider`: Azure/OpenAI-compatible provider family.
- `auth_mode`: explicit value such as `azure_client_credentials` or `api_key`.
- `model`: deployment or model identifier.
- `azure`: tenant/client credential refs when `auth_mode` is
  `azure_client_credentials`.
- `azure_api_key`: endpoint/API-key credential refs when `auth_mode` is
  `api_key`.
- `parameters`: generation parameters for this model instance.

### Validation Rules

- The auth mode is required and explicit for every model config.
- The credential group must match `auth_mode`.
- The harness must not infer auth mode by inspecting available environment
  variables.
- Each model config is instantiated independently so credentials do not leak
  between baseline and candidate providers.
- Examples should use project/model-specific environment variable names to
  avoid collisions.

## API-Key Candidate Model

A candidate model hosted in Azure and accessed with endpoint/API-key
credentials.

### Fields

- `name`: project-local candidate name used in commands, reports, and metadata.
- `provider`: provider family used by the harness.
- `auth_mode`: API-key authentication mode.
- `model`: deployment or model identifier sent to the Azure endpoint.
- `endpoint`: optional non-secret endpoint value or a pointer to endpoint
  configuration, depending on the final config shape.
- `azure_api_key` or equivalent credential reference group: API-key credential
  references, including `api_version_env` for Azure OpenAI deployment-style
  endpoints.
- `parameters`: temperature, top-p, max token limit, token limit parameter, and
  optional seed.
- `metadata`: non-secret provider metadata for trace/report context.

### Relationships

- Belongs to one project config as a candidate.
- Uses the same task prompt and dataset as the project baseline.
- Produces candidate output records with baseline references.
- Produces Langfuse traces and model-output observations consumed by evaluator
  filters and human review routing.

### Validation Rules

- Candidate names must remain stable and usable in run commands.
- API-key candidates must provide the required credential references.
- API-key candidates must not require tenant/client credential references.
- API-key candidates can coexist with tenant/client Azure baselines and other
  API-key candidates in the same project.
- Literal secret values are invalid in committed project config.

## Provider Failure

A redacted failure raised while validating or running a provider.

### Fields

- `operation`: operation that failed, such as model generation.
- `provider`: provider family.
- `candidate_name`: candidate that failed when available.
- `model`: deployment or model identifier.
- `status_category`: authentication, authorization, throttling, timeout,
  malformed response, unsupported parameter, or unknown.
- `message`: redacted diagnostic text.
- `attempts`: retry count or attempt count when available.

### Validation Rules

- Must not contain API-key values or sensitive configured values.
- Must identify the failing candidate/model enough for remediation.
- Must preserve existing provider error context shape where possible.

## Candidate Output Record

The existing run output record produced for each attempted dataset item.

### Fields Affected

- `provider`: identifies the Azure endpoint/API-key provider path.
- `model`: deployment or model identifier.
- `parameters`: non-secret generation parameters.
- `trace_id`: Langfuse trace ID.
- `observation_id`: Langfuse model-output observation ID when available.
- `baseline_reference`: existing baseline reference used for comparison.
- `latency_ms`, `input_tokens`, `output_tokens`, `cost_usd`: captured when the
  Azure response provides them.
- `error`: redacted failure text for failed items.

### Validation Rules

- Must preserve project, dataset, prompt, evaluator, run, and baseline metadata.
- Must not include provider secret values.
- Must be compatible with existing export, review selection, and evaluator
  target metadata workflows.
