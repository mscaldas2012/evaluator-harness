# Contract: Provider Runtime Prompt Handling

## Rendered Prompt Payload

Provider requests must receive enough prompt structure to preserve role-based
prompts.

```text
RenderedPrompt
  shape: text | messages
  text: rendered single-text prompt
  messages:
    - role: <configured-role-label>
      content: <rendered-message-content>
```

Existing code that reads the legacy text prompt should continue to work for
single-text prompts.

## OpenAI-Compatible Providers

When the rendered prompt shape is `messages`, OpenAI-compatible chat completion
paths must send the ordered messages as chat messages without flattening.

```json
{
  "messages": [
    {"role": "system", "content": "You are a careful editor."},
    {"role": "user", "content": "Rewrite the following text..."}
  ]
}
```

Rules:

- Role labels are sent exactly when supported.
- Unsupported role labels fail validation before the provider call.
- Automatic role mapping is not performed in this feature.

## Providers Without Faithful Role Support

Providers that cannot send the configured role labels exactly must fail
validation before model calls.

Rules:

- Do not silently flatten role-based prompts.
- Do not map custom roles to `user`, `system`, or `assistant`.
- Error messages identify the provider and unsupported role labels.

## Dry Run Provider

Dry-run output remains deterministic.

Rules:

- Single-text prompts keep existing hashing semantics.
- Role-based prompts hash a deterministic representation that includes role
  labels, message order, and rendered content.
- Dry-run metadata may identify the prompt shape for tests and trace inspection.

## Observability

Trace, observation, evaluator, review, and export metadata should include:

- `prompt_shape`: `text` or `messages`.
- `prompt_roles`: ordered role labels for role-based prompts.
- `prompt_identity`: existing identity fields plus shape, roles, and variables.
- Baseline and candidate prompt identities when running candidates.
