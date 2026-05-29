# Data Model: Prompt Roles and Variables

## PromptRef

Existing project or candidate prompt reference.

**Fields**:

- `path`: Markdown prompt file path.
- `version`: prompt version associated with runs.
- `template_variables`: existing declared variables, retained for backward
  compatibility.
- `metadata`: non-secret prompt metadata.

**Validation rules**:

- `path` must point to a non-empty Markdown prompt file.
- `version` must be present.
- Existing single-text prompt projects remain valid.
- Role-based prompt files must pass the PromptDefinition rules below.

## PromptDefinition

Parsed representation of a prompt file.

**Fields**:

- `path`: source prompt path.
- `version`: prompt version from `PromptRef`.
- `shape`: `text` or `messages`.
- `text`: raw single-text prompt content when `shape` is `text`.
- `messages`: ordered list of PromptMessage entries when `shape` is `messages`.
- `variable_references`: sorted or stable ordered list of DatasetVariableReference
  entries found in the prompt.

**Validation rules**:

- A file with no `## role: <role-label>` headings is a legacy single-text
  prompt.
- A file with one or more `## role: <role-label>` headings is a role-based
  prompt.
- Role-based files must not contain non-empty unassigned content before the
  first role heading.
- Role-based files must reject malformed role headings.
- Role-based files preserve message order exactly as authored.

## PromptMessage

One message in a role-based prompt.

**Fields**:

- `role`: generic role label from the heading.
- `content`: Markdown content under the role heading until the next role heading.
- `index`: zero-based order in the prompt.
- `variable_references`: variables used in the message content.

**Validation rules**:

- `role` must be non-empty after trimming.
- `content` may be empty only when that is intentionally authored; validation
  should not invent content.
- Role labels are not limited to `system`, `user`, and `assistant`.

## DatasetVariableReference

A placeholder in prompt content.

**Fields**:

- `raw`: placeholder text, such as `{dataset.input}`.
- `namespace`: must be `dataset` for this feature.
- `field`: dataset column name, such as `input`.

**Validation rules**:

- Placeholder syntax uses single braces.
- Unmatched braces are invalid.
- Only `dataset.<field>` references are valid.
- Referenced fields must exist in the selected dataset columns before live model
  calls.
- Empty row values are allowed and render as empty strings.
- Braces inside substituted dataset values are literal data.

## RenderedPrompt

Prompt content rendered for one dataset item.

**Fields**:

- `shape`: `text` or `messages`.
- `text`: rendered text for legacy prompts.
- `messages`: ordered rendered messages for role-based prompts.
- `display_text`: deterministic readable representation for previews,
  fallback hashing, and reports.
- `variable_values`: non-secret references to dataset fields used; values may be
  omitted from metadata when traces already contain rendered prompt payloads.

**Relationships**:

- Created from one PromptDefinition and one dataset item.
- Passed to ModelRequest.
- Used by trace metadata, evaluator payload metadata, review payload metadata,
  and exports.

## ModelRequest

Provider generation request.

**Fields**:

- `prompt`: legacy text prompt kept for compatibility.
- `rendered_prompt`: optional RenderedPrompt payload.
- `params`: model generation parameters.
- `metadata`: run and dataset metadata.

**Validation rules**:

- Legacy providers and tests may continue to read `prompt`.
- Role-aware providers should use `rendered_prompt.messages` when present.
- Provider capability validation must happen before live model calls.

## PromptIdentity

Reproducibility metadata for a prompt.

**Fields**:

- `path`: source prompt path.
- `version`: prompt version.
- `shape`: `text` or `messages`.
- `content_hash`: stable hash over normalized prompt definition content.
- `roles`: ordered role labels for role-based prompts.
- `variable_references`: dataset variable references used by the prompt.

**Validation rules**:

- Role order affects identity.
- Candidate prompt overrides produce a separate identity from the baseline
  prompt.
- Existing identity consumers must continue to receive `path`, `version`, and
  `content_hash`.

## ProviderRoleCapability

Provider-specific declaration of which role labels can be sent faithfully.

**Fields**:

- `provider`: provider name.
- `supports_messages`: whether provider can accept role messages.
- `supported_roles`: exact role labels supported, or provider-specific
  capability policy.
- `failure_reason`: validation message when unsupported.

**Validation rules**:

- OpenAI-compatible chat completion paths support message payloads for supported
  role labels.
- Providers that cannot send role messages exactly must fail validation before
  model calls.
- Automatic role mapping is out of scope.
