# Feature Specification: Model Output Observation Targeting

**Feature Branch**: `015-model-output-targeting`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Ensure evaluator rules target exactly one final model output observation per dataset item across provider logging paths so Langfuse evaluator counts are not doubled. Parent/container spans must not match model_output evaluators. Providers using native Langfuse tracing must propagate the model_output contract or expose config for the final output observation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prevent Double Evaluator Matches (Priority: P1)

As an evaluation owner, I want each dataset item run to produce exactly one evaluator-targetable final model output observation, so Langfuse evaluator counts match the number of evaluated outputs instead of double-counting parent and child observations.

**Why this priority**: Double evaluator matches inflate evaluator counts, duplicate judge execution cost, and make experiment results hard to trust.

**Independent Test**: Run a project with a 12-item dataset through two runs and confirm each evaluator reports 24 matched observations, not 48, while still producing scores for all completed outputs.

**Acceptance Scenarios**:

1. **Given** a provider path that creates both a parent/container observation and a final model generation observation, **When** the evaluator filter targets model outputs, **Then** only the final model generation observation matches.
2. **Given** a 12-item dataset and two successful experiment runs, **When** evaluator counts are reviewed in Langfuse, **Then** each evaluator count reflects 24 final outputs.
3. **Given** parent/container observations are present for trace organization, **When** evaluator rules run, **Then** parent/container observations do not trigger model-output evaluators.

---

### User Story 2 - Preserve Provider Portability (Priority: P2)

As a harness maintainer, I want the evaluator targeting contract to work across OpenAI-compatible, dry-run, Ollama, Gemini, Claude, and future provider integrations, so project evaluator configs do not depend on a provider-specific observation name.

**Why this priority**: A filter such as `OpenAI-generation` fixes one current provider path but breaks dry runs and future providers.

**Independent Test**: Validate that providers using different tracing strategies can still identify a single final model output observation without requiring DFE-specific or provider-specific evaluator config.

**Acceptance Scenarios**:

1. **Given** a provider uses harness-managed tracing, **When** a model output is logged, **Then** the final output observation carries the model-output role and the parent/container observation carries a non-model-output role.
2. **Given** a provider uses native Langfuse tracing, **When** it cannot guarantee the standard model-output metadata, **Then** the project or provider setup exposes a clear way to identify the final output observation.
3. **Given** a dry-run provider is used for local verification, **When** evaluators are synced with the standard model-output role filter, **Then** dry-run outputs remain eligible for evaluation if they produce final output traces.

---

### User Story 3 - Make Misconfiguration Visible (Priority: P3)

As a user preparing evaluator setup, I want validation or audit output to flag ambiguous model-output targeting, so I can fix duplicate or missing evaluator matches before running expensive judges.

**Why this priority**: Users need actionable feedback when provider metadata would produce zero matches or duplicate matches.

**Independent Test**: Present trace samples or simulated provider outputs with no final-output marker or multiple final-output markers and confirm the harness reports the ambiguity clearly.

**Acceptance Scenarios**:

1. **Given** a provider path marks more than one observation in a trace as the final model output, **When** targeting is validated or audited, **Then** the user sees a warning or failure explaining that evaluator counts may be duplicated.
2. **Given** no observation in a trace can be identified as the final model output, **When** targeting is validated or audited, **Then** the user sees a remediation that identifies the missing contract.
3. **Given** evaluator filters would rely on a provider-specific observation name, **When** the project is reviewed, **Then** the user is told whether that choice is portable or provider-specific.

### Edge Cases

- A trace contains multiple LLM calls, but only one is the final answer that should be judged.
- A trace contains retries or failed attempts before a successful final output.
- A provider emits native Langfuse spans with different names, span types, or metadata shapes.
- A dry-run or test provider does not create a nested generation observation.
- A project intentionally wants to evaluate a non-final observation such as retrieval relevance.
- Legacy traces created before the contract may still have duplicate model-output markers.
- Existing evaluator rules may already target broad observation filters and need resync or version bumping.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature applies to existing evaluation projects that define datasets, model configurations, evaluator definitions, score configs, and optional human review policy.
- **Dataset**: Feature MUST preserve support for CSV datasets with an `input` column and MUST NOT change dataset loading behavior.
- **Langfuse Logging**: Feature MUST define one canonical final model output observation per dataset item run for evaluator targeting, while preserving trace structure and run metadata.
- **Prompt and Evaluator Versioning**: Feature MUST preserve prompt identity and evaluator version tracking; evaluator rules may need version bumps only when targeting semantics change.
- **Baseline**: Feature MUST preserve baseline and candidate run workflows and MUST NOT change baseline selection semantics.
- **Human Review**: Feature MUST preserve Human Annotation Queue behavior and ensure scores remain comparable to automated judge scores.

### Functional Requirements

- **FR-001**: System MUST define a provider-neutral final model output observation contract.
- **FR-002**: System MUST ensure exactly one final model output observation per completed dataset item run matches standard model-output evaluator filters.
- **FR-003**: System MUST prevent parent, container, or orchestration observations from matching standard model-output evaluator filters.
- **FR-004**: System MUST preserve evaluator support for observation-level targets without requiring provider-specific observation names.
- **FR-005**: System MUST support provider integrations that use harness-managed tracing and provider integrations that use native Langfuse tracing.
- **FR-006**: System MUST provide a clear configuration or contract path when a provider cannot directly attach the standard final-output marker.
- **FR-007**: System MUST keep dry-run and local verification workflows compatible with standard model-output evaluator filters.
- **FR-008**: System MUST preserve project, project version, scenario, run type, dataset item, prompt identity, and evaluator-set metadata needed for filtering and trace review.
- **FR-009**: System MUST provide validation, audit, or diagnostic output that identifies duplicate final-output markers when detectable.
- **FR-010**: System MUST provide validation, audit, or diagnostic output that identifies missing final-output markers when detectable.
- **FR-011**: System MUST document the provider integration contract so future Gemini, Claude, Ollama, or other providers can implement it consistently.
- **FR-012**: System MUST preserve support for projects that intentionally target a specific non-final observation by using explicit evaluator configuration.
- **FR-013**: System MUST avoid silently changing historical trace data; behavior changes apply to new traces and newly synced evaluator targeting.

### Key Entities *(include if feature involves data)*

- **Final Model Output Observation**: The single observation per dataset item run that represents the output to be judged by standard model-output evaluators.
- **Parent/Container Observation**: A trace organization span that groups work for a dataset item but is not itself the final model output.
- **Provider Tracing Contract**: The required metadata or configuration a provider must supply so evaluator rules can identify the final output consistently.
- **Evaluator Targeting Profile**: The project evaluator filter intent, including target type, observation role, optional observation name, project, version, run type, and evaluator set.
- **Targeting Diagnostic**: A validation or audit result that identifies whether evaluator matching would be missing, duplicated, or correctly scoped.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a 12-item dataset run twice, each standard model-output evaluator matches 24 observations rather than 48.
- **SC-002**: 100% of completed dataset item runs in supported harness-managed provider paths have exactly one final model output observation eligible for standard evaluator targeting.
- **SC-003**: Parent/container observations trigger 0 standard model-output evaluator matches in new runs.
- **SC-004**: Dry-run verification remains evaluatable under the standard model-output targeting contract.
- **SC-005**: Users can identify from validation, audit, or documentation how a provider marks the final model output before running expensive judge evaluations.
- **SC-006**: Existing score config alignment and human annotation comparison workflows continue to work after the targeting change.

## Assumptions

- Standard content-quality judges should evaluate the final model output for each dataset item, not every intermediate LLM call.
- Some future projects may intentionally evaluate intermediate observations, so the feature must keep explicit non-final targeting possible.
- Existing historical duplicate scores may remain in Langfuse; this feature prevents new duplicate matches rather than rewriting old traces.
- Provider integrations are expected to participate in a shared metadata or configuration contract.
- The current double count is caused by both parent/container and final generation observations matching the same model-output evaluator filter.
