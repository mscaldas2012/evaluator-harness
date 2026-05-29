# Feature Specification: Prompt Roles and Variables

**Feature Branch**: `011-prompt-roles-variables`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "need to add support for various prompt roles, like system, assistant, user. also need to support variable swapping. for now I can see {dataset.input}, where the contents of the input on the dataset being used can be embedded on the prompt. {} should suffice to demarcate a variable swap."

## Clarifications

### Session 2026-05-29

- Q: When a provider cannot faithfully send the configured generic role labels, what should the harness do? -> A: Send role labels exactly only when the provider supports them; otherwise fail validation before the model call. Explicit role mapping is deferred to a later feature.
- Q: How strict should `{dataset.<field>}` validation be? -> A: Validate placeholders against dataset columns; empty per-row values render as empty strings.
- Q: What authoring format should MVP support for role-based task prompts? -> A: Define role-based prompts in Markdown files using role headers or delimiters.
- Q: Which Markdown delimiter should identify each role message? -> A: Use level-2 Markdown headings in the form `## role: <role-label>`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Multi-Role Task Prompts (Priority: P1)

A project author can define a model prompt as an ordered conversation with role-specific messages, using role labels such as system, user, assistant, or project-specific roles, so providers receive the intended prompt structure instead of one flattened text block.

**Why this priority**: Role-aware prompts are the core feature. Without them, users cannot faithfully represent prompts exported from chat-oriented prompt sources or evaluate role-sensitive behavior.

**Independent Test**: Can be tested by defining a prompt with system, user, and a project-specific role message, validating the project, running a dry-run or live generation, and confirming the generated prompt payload preserves message order and role labels.

**Acceptance Scenarios**:

1. **Given** a project prompt with system, user, and project-specific role messages, **When** the project is validated, **Then** the prompt is accepted and each message role label is preserved.
2. **Given** a prompt with multiple messages in a specific order, **When** a baseline or candidate run renders the prompt for a dataset item, **Then** the rendered prompt preserves the configured order and role labels.
3. **Given** an existing single-text task prompt, **When** the project is validated and run, **Then** it remains valid and behaves as it did before this feature.

---

### User Story 2 - Substitute Dataset Variables in Prompts (Priority: P1)

A project author can embed dataset values into any prompt message using brace-delimited variables such as `{dataset.input}`, so each dataset row produces the right model input without manually duplicating prompts.

**Why this priority**: Prompt roles are only useful for dataset evaluation when prompt messages can include row-specific content.

**Independent Test**: Can be tested by defining a prompt message containing `{dataset.input}`, running it against a dataset row with a known `input` value, and confirming the rendered prompt contains that value exactly where the placeholder appeared.

**Acceptance Scenarios**:

1. **Given** a dataset row where `input` is "Rewrite this text", **When** a prompt contains `{dataset.input}`, **Then** the rendered message contains "Rewrite this text" in that location.
2. **Given** a prompt message with more than one variable placeholder, **When** the prompt is rendered, **Then** all placeholders with available values are replaced.
3. **Given** a prompt message with no variable placeholders, **When** the prompt is rendered, **Then** its text is unchanged.

---

### User Story 3 - Validate Invalid Variables and Role Labels (Priority: P2)

A project author receives clear validation feedback when a prompt has an invalid role label or references a dataset variable that is not available for the selected dataset.

**Why this priority**: Clear validation prevents silent prompt corruption and avoids wasting live model calls on malformed prompts.

**Independent Test**: Can be tested by defining prompts with a missing role label and an unavailable dataset variable, then confirming validation fails with actionable messages identifying the problem.

**Acceptance Scenarios**:

1. **Given** a prompt message with an empty or malformed role label, **When** the project is validated, **Then** validation fails and identifies the invalid role label.
2. **Given** a prompt message containing `{dataset.missing_field}`, **When** the selected dataset has no `missing_field` column, **Then** validation fails before the model call and identifies the missing variable.
3. **Given** a malformed placeholder with unmatched braces, **When** the project is validated, **Then** validation fails and identifies the malformed variable syntax.

---

### User Story 4 - Use Role and Variable Metadata in Evaluations (Priority: P3)

A user reviewing Langfuse traces or exports can understand which prompt roles and dataset substitutions were used for a run, without exposing secrets or unrelated local state.

**Why this priority**: The feature changes prompt structure, so reproducibility metadata must remain strong, but the primary user value is prompt execution and validation.

**Independent Test**: Can be tested by running a baseline or candidate with role-based prompts and confirming trace or export metadata identifies the prompt version and role-aware prompt shape at a level sufficient for reproducibility.

**Acceptance Scenarios**:

1. **Given** a role-based prompt run, **When** the run is logged, **Then** prompt metadata records enough information to distinguish it from a single-text prompt version.
2. **Given** a rendered prompt uses dataset variables, **When** trace or export metadata is inspected, **Then** the run remains attributable to the dataset item and prompt version that produced it.

### Edge Cases

- A dataset column exists but a row value is empty; the placeholder is replaced with an empty string and the run remains attributable to the dataset item.
- A prompt references a dataset column that is not present in the selected dataset; validation fails before any model call.
- A dataset field value contains braces; the value is treated as data, not as a second variable expression.
- A prompt references the same variable multiple times; every occurrence is replaced consistently.
- A prompt includes adjacent variables such as `{dataset.input}{dataset.ground_truth}`; both variables are replaced without adding implicit separators.
- A prompt contains empty or malformed role labels; validation fails before any live provider call.
- A role-based prompt is used for one candidate while the baseline uses an existing single-text prompt; baseline compatibility remains based on the baseline prompt identity and version.
- A candidate defines a prompt override; the override replaces the full project prompt definition for that candidate.
- A provider does not support one or more configured role labels; validation fails before the model call and explains which provider and role labels are incompatible.
- A role-based prompt file mixes role-delimited sections and unassigned content; validation fails unless all role-based content belongs to an explicit role section.
- A role-based prompt file uses a malformed role heading, such as `## role:` with no label; validation fails and identifies the malformed heading.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST preserve the project identity model, including datasets, baseline model configuration, candidate model configurations, evaluator definitions, and review policy.
- **Dataset**: Feature MUST preserve support for CSV datasets with an `input` column and allow prompt variables to reference available dataset fields.
- **Langfuse Logging**: Feature MUST preserve logging of traces, observations, scores, run metadata, evaluator metadata, baseline references, and comparison metadata to Langfuse, and MUST keep prompt identity metadata sufficient to distinguish role-based prompts from single-text prompts.
- **Prompt and Evaluator Versioning**: Feature MUST continue to associate prompt versions and evaluator versions with runs; role-based prompt changes MUST be reflected in prompt identity metadata.
- **Baseline**: Feature MUST preserve baseline creation, selection, reuse, and compatibility checks for baseline and candidate comparisons.
- **Human Review**: Feature MUST preserve Human Annotation Queue routing and review payloads, including enough prompt and dataset context for users to inspect important or disputed outputs in Langfuse.

### Functional Requirements

- **FR-001**: Users MUST be able to define task prompts as an ordered list of role-specific messages.
- **FR-002**: The system MUST support generic role labels; `system`, `user`, and `assistant` are examples, not the complete allowed set.
- **FR-003**: The system MUST preserve the order of role-specific prompt messages during validation, rendering, execution, logging, and export.
- **FR-004**: Existing single-text task prompts MUST remain valid and continue to render as before.
- **FR-005**: Role-based task prompts MUST be authored in Markdown prompt files using level-2 role headings in the form `## role: <role-label>`.
- **FR-006**: A role-based prompt file MUST define each message's role label and content in the same file.
- **FR-007**: Role-based prompt files MUST treat each `## role: <role-label>` section as one ordered prompt message.
- **FR-008**: Role-based prompt files MUST reject unassigned content outside explicit role sections.
- **FR-009**: Role-based prompt files MUST reject malformed role headings, including headings without a non-empty role label.
- **FR-010**: Users MUST be able to embed dataset field values in prompt message content using brace-delimited placeholders.
- **FR-011**: The placeholder `{dataset.input}` MUST resolve to the `input` value for the active dataset item.
- **FR-012**: The system MUST support placeholders for other available dataset fields using the same `dataset.<field>` naming pattern.
- **FR-013**: Placeholder replacement MUST be available in every supported prompt role message.
- **FR-014**: The system MUST detect and reject malformed placeholder syntax, including unmatched braces.
- **FR-015**: The system MUST validate `{dataset.<field>}` placeholders against the selected dataset columns before making a live model call.
- **FR-016**: The system MUST reject placeholders that reference dataset columns not present in the selected dataset.
- **FR-017**: Empty per-row dataset values MUST render as empty strings.
- **FR-018**: The system MUST treat braces inside substituted dataset values as literal content rather than as nested placeholders.
- **FR-019**: The system MUST preserve prompt version and prompt identity behavior for both single-text and role-based prompts.
- **FR-020**: Candidate-level prompt overrides MUST support the same role and variable behavior as project-level task prompts.
- **FR-021**: Candidate-level prompt overrides MUST replace the full project prompt definition for that candidate; partial role or message inheritance is out of scope for this feature.
- **FR-022**: Validation output MUST identify invalid role labels, malformed placeholders, and missing dataset variable references with messages specific enough for a project author to correct the prompt.
- **FR-023**: Rendered prompt previews or reports MUST make role boundaries visible when the source prompt uses roles.
- **FR-024**: Prompt rendering MUST not substitute environment variables, credentials, or non-dataset values through the `{...}` syntax.
- **FR-025**: Exports and trace metadata MUST preserve enough prompt context to compare runs that use different prompt roles or variable references.
- **FR-026**: The system MUST send configured role labels exactly when the selected provider supports them.
- **FR-027**: The system MUST fail validation before the model call when the selected provider cannot faithfully send one or more configured role labels.
- **FR-028**: The system MUST NOT automatically map custom or unsupported role labels to provider-supported role labels in this feature.

### Key Entities

- **Prompt Definition**: The project or candidate prompt configuration. It may reference a legacy single-text Markdown prompt file or a role-based Markdown prompt file, and it includes a version and expected dataset variables.
- **Prompt Message**: One ordered message within a role-based prompt. It has a role label and content that may include dataset placeholders.
- **Dataset Variable Reference**: A brace-delimited placeholder that points to a field on the active dataset item, such as `{dataset.input}`.
- **Rendered Prompt**: The prompt content after dataset variables are substituted for a specific dataset item.
- **Prompt Identity**: The reproducibility identity that distinguishes prompt content, version, roles, and variable references used for a run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project author can validate and run a prompt containing generic role labels and `{dataset.input}` without manually editing the dataset or prompt per row.
- **SC-002**: 100% of configured role labels in a prompt are preserved in the same order from project validation through rendered prompt output.
- **SC-003**: 100% of malformed placeholders and unavailable dataset variable references are rejected before a live model provider call.
- **SC-004**: Existing single-text prompt projects continue to validate and run without requiring prompt file changes.
- **SC-005**: A project author can identify from run metadata or exports whether a run used a single-text prompt or a role-based prompt.
- **SC-006**: Prompt rendering for a dataset item replaces every valid placeholder occurrence consistently, including repeated occurrences in the same message.

## Assumptions

- Role-based task prompts are needed for model generation prompts first; evaluator prompt roles are out of scope unless explicitly added in a later feature.
- The initial variable namespace is limited to dataset fields under `dataset.*`.
- Brace-delimited placeholders use single braces, such as `{dataset.input}`.
- Role-based task prompts are authored in Markdown files rather than inline structured project config for the MVP.
- Role-based prompt message boundaries use level-2 Markdown headings in the form `## role: <role-label>`.
- Candidate prompt overrides replace the full project prompt definition for that candidate in the MVP.
- Explicit role mapping for providers with narrower role support is deferred to a later feature.
- Prompt variable substitution happens before the model provider call and before judge or review payload construction.
- Existing prompt versioning conventions remain the primary way users communicate intentional prompt changes.
