# Contract: Azure Endpoint/API-Key Provider Runtime

## Request Contract

For each dataset item, the provider receives the rendered task prompt and the
candidate model configuration. The provider instance is scoped to one configured
baseline or candidate model and must use that model's explicit `auth_mode`.

Runtime behavior:

- Resolve endpoint and API key from configured environment variable names.
- Resolve service version from `api_version_env` for Azure OpenAI
  deployment-style endpoints. Future endpoint shapes that do not require a
  service version must declare that explicitly before provider execution.
- Build a chat-generation request using the configured deployment/model
  identifier and generation parameters.
- Authenticate with API-key credentials only.
- Do not attempt tenant/client token acquisition for API-key candidates.
- Do not infer auth mode from available environment variables.
- Do not reuse resolved credentials across provider instances.
- Preserve existing retry behavior and token-limit fallback behavior where
  applicable.
- Prefer Langfuse SDK/provider instrumentation only when it can attach the
  generation to the existing trace/span and preserve the metadata contract. Use
  the manual Langfuse generation path when SDK instrumentation would create an
  unrelated trace or omit required observation metadata.

## Response Contract

Successful responses produce a model response with:

- output text
- input token count when available
- output token count when available
- latency when available from the harness timing path
- cost when available
- raw non-secret provider metadata

The runner then records the existing candidate output record and Langfuse
trace/observation metadata.

## Trace Structure Contract

API-key candidate execution must preserve the existing trace shape:

- one deterministic Langfuse trace ID per run/item
- a stable trace name scoped to project, run type, and dataset item
- one parent workflow span for the run/item
- one nested generation observation for the final model output
- the generation observation attached to the parent trace/span, not emitted as
  an unrelated top-level trace
- parent observation ID captured in request metadata when Langfuse exposes it

Provider/model/deployment names must live in metadata, not as the only way to
target traces or evaluator rules.

## Error Contract

Failures must include:

- operation
- provider
- model/deployment identifier
- candidate name when available
- attempt count when available
- redacted diagnostic message

Failures must not include:

- API key values
- subscription key values
- tenant/client secret values from other configured providers
- sensitive endpoint values when they are configured as secret references

## Langfuse Metadata Contract

API-key candidate traces and model-output observations must include the same
metadata classes as other live candidates:

- project name and version
- dataset identity and item identity
- run ID and run type
- provider and model/deployment identifier
- prompt version
- baseline reference for candidate runs
- evaluator set ID
- observation role `model_output`
- trace ID and trace name
- parent observation ID when available
- non-secret generation parameters

The evaluator filter profile created for the rewrite-quality judge must be able
to match API-key candidate model-output observations using project metadata and
observation role metadata, without relying on a provider-specific observation
name.

Evaluator filters for this candidate must not include empty environment filters
or provider-specific generation-name filters that would exclude otherwise valid
candidate observations.
