# Contract: Project Config for Candidate Variants

This contract describes the user-facing project YAML behavior for model,
prompt, parameter, and mixed candidate variants.

## Existing Model Variant Shape

Existing model-only candidates remain valid:

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

## Prompt Variant Shape

A candidate may override the project-level task prompt:

```yaml
candidates:
  - name: gpt5-prompt-v2
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt5.2-dgw-default
    azure:
      tenant_id_env: EDAV_TENANT_ID
      client_id_env: EDAV_CLIENT_ID
      client_secret_env: EDAV_CLIENT_SECRET
      scope_env: EDAV_SCOPE_TOKEN_AUDIENCE
      subscription_key_env: EDAV_SUBSCRIPTION_KEY
      api_version_env: EDAV_AZURE_OPENAI_API_VERSION
      endpoint_env: EDAV_AZURE_OPENAI_ENDPOINT
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

The baseline continues to use the project-level `task_prompt` unless a later
feature explicitly adds baseline prompt overrides.

## Parameter Variant Shape

Parameter-only variants use separate candidate names:

```yaml
candidates:
  - name: gpt5-temp-02
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt5.2-dgw-default
    parameters:
      temperature: 0.2
      top_p: 1.0
      max_tokens: 2048
  - name: gpt5-temp-08
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt5.2-dgw-default
    parameters:
      temperature: 0.8
      top_p: 1.0
      max_tokens: 2048
```

Credential blocks are omitted here for brevity but remain required according to
provider/auth mode.

## Required Behavior

- Candidate names must be unique within the project.
- `task_prompt` is optional on candidates. When omitted, the project-level task
  prompt is used.
- Candidate prompt files must exist, be non-empty, and include required project
  variables.
- Candidate prompt version and baseline prompt version must be recorded
  separately.
- Prompt content identity must be recorded in non-secret metadata so reused
  version labels can be detected.
- Parameter identity must change when generation parameter values change.
- Existing model-only candidates must validate without config changes.
- Provider credential validation and secret redaction behavior remain unchanged.

## Invalid Config Examples

Duplicate candidate names are invalid:

```yaml
candidates:
  - name: gpt5-temp-02
    model: gpt5.2-dgw-default
  - name: gpt5-temp-02
    model: gpt5.2-dgw-default
```

Missing prompt file is invalid:

```yaml
candidates:
  - name: gpt5-prompt-v2
    task_prompt:
      path: prompts/rewrite_quality/missing.md
      version: v2
```

Prompt override without the required `input` variable is invalid:

```yaml
candidates:
  - name: gpt5-prompt-v2
    task_prompt:
      path: prompts/rewrite_quality/task_prompt_v2.md
      version: v2
      template_variables:
        - topic
```
