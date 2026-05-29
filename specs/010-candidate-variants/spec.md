# Feature Specification: Candidate Variants

**Feature Branch**: `010-candidate-variants`

**Created**: 2026-05-28

**Status**: Draft

**Input**: User description: "so far we've been focusing on comparing different models. but a candidate could have a different prompt - compare v2 to v1 - or different model params. how can we implememnt those candidates for comparisson? we still need to keep all the scores tied together in langfuse so that I can compare the baseline with candidate 1, candidate 2, etc." Follow-up decision: prompt-v2 candidates can be run against an existing compatible baseline.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare Prompt Variant Against Existing Baseline (Priority: P1)

A harness user can define a candidate that uses a different task prompt version from the baseline, run it against an existing compatible baseline, and compare its outputs and scores with the baseline in Langfuse.

**Why this priority**: Prompt iteration is a first-class evaluation workflow. Users need to compare prompt-v2 output against prompt-v1 baseline output without regenerating the baseline every time a candidate prompt changes.

**Independent Test**: Can be fully tested by configuring a prompt-v2 candidate for an existing project, running it with an existing baseline reference, and confirming Langfuse records candidate traces, observations, scores, and baseline comparison metadata for the same dataset items.

**Acceptance Scenarios**:

1. **Given** a project has a baseline generated with prompt v1 and a candidate configured with prompt v2, **When** the user runs the candidate using the existing baseline reference, **Then** the candidate outputs are compared against the baseline outputs for matching dataset items.
2. **Given** a prompt-v2 candidate run completes, **When** the user views Langfuse metadata and scores, **Then** each candidate output identifies the candidate prompt version separately from the baseline prompt version.
3. **Given** the baseline is compatible with the project, dataset, baseline model, baseline parameters, and evaluator set, **When** the candidate prompt version differs, **Then** the system still allows the candidate comparison and preserves the baseline reference.
4. **Given** a prompt-v2 candidate is scored by automated or human evaluators, **When** scores are reviewed in Langfuse, **Then** scores remain tied to the candidate run and comparable with baseline and other candidate runs for the same dataset items.

---

### User Story 2 - Compare Model Parameter Variants (Priority: P2)

A harness user can define multiple candidates that use the same provider and model but different generation parameters, then compare each candidate against the same baseline.

**Why this priority**: Users often tune temperature, token limits, sampling settings, and related generation behavior before or alongside model changes.

**Independent Test**: Can be tested by configuring two candidates with the same model and different parameters, running both against the same baseline, and confirming each run has distinct variant identity and parameter metadata while sharing the same baseline reference.

**Acceptance Scenarios**:

1. **Given** two candidates differ only by generation parameters, **When** both are run against the same compatible baseline, **Then** each produces a separate candidate run with its own parameter identity.
2. **Given** two parameter variants are viewed in Langfuse, **When** the user compares results, **Then** each score can be attributed to the correct candidate variant.
3. **Given** a candidate is run repeatedly with unchanged prompt, model, and parameters, **When** repeated runs are recorded, **Then** each run is distinct while retaining the same stable variant metadata.

---

### User Story 3 - Compare Mixed Candidate Variants (Priority: P3)

A harness user can evaluate candidates that differ by model, prompt, parameters, or a combination of these factors, while still using the same comparison and review workflow.

**Why this priority**: Real evaluation campaigns often compare several candidate ideas at once, such as prompt-v2 on the baseline model, a new model with prompt-v1, and a new model with different parameters.

**Independent Test**: Can be tested by configuring candidates that vary across prompt, model, and parameters, running them against the same baseline, and confirming all traces and scores remain grouped by project, dataset, evaluator set, baseline reference, and candidate variant.

**Acceptance Scenarios**:

1. **Given** a project contains candidates that vary by prompt, model, and parameters, **When** each candidate is run, **Then** each candidate receives a stable, human-readable variant identity.
2. **Given** Langfuse contains baseline, candidate 1, and candidate 2 runs for the same project and dataset, **When** the user filters or compares scores, **Then** the system exposes enough metadata to distinguish the variants and keep their scores comparable.
3. **Given** a candidate variant fails for some dataset items, **When** the run is recorded, **Then** successful and failed outputs retain the variant identity and baseline reference needed for review.

### Edge Cases

- A candidate references a prompt version or prompt content that is missing, empty, or incompatible with the required dataset inputs.
- A candidate prompt version differs from the baseline prompt version, but the selected baseline is otherwise compatible.
- Multiple candidates reference the same prompt version but different prompt files or content.
- Two candidates accidentally use the same candidate name while representing different prompts or parameters.
- A candidate changes prompt, model, and parameters at the same time.
- A candidate run is repeated with identical variant settings and must remain distinguishable by run while sharing stable variant metadata.
- A baseline reference cannot be resolved or is incompatible with the current project, dataset, evaluator set, baseline model, or baseline parameters.
- Scores or human review items arrive after multiple candidate runs exist for the same dataset item.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST allow project configurations to define candidates as named variants that may differ by model, prompt version, generation parameters, or any combination of those factors.
- **Dataset**: Feature MUST preserve existing dataset requirements and MUST compare baseline and candidate outputs by stable dataset item identity.
- **Langfuse Logging**: Feature MUST record variant identity, run identity, baseline reference, prompt identity, model identity, parameter identity, evaluator metadata, trace metadata, observation metadata, and score metadata so baseline and candidate scores remain comparable in Langfuse.
- **Prompt and Evaluator Versioning**: Feature MUST track the prompt version used by the baseline separately from the prompt version used by each candidate. Evaluator versions remain part of the shared evaluator set used for comparison.
- **Baseline**: Feature MUST allow a candidate prompt variant, including prompt v2, to run against an existing compatible baseline even when the baseline used a different prompt version.
- **Human Review**: Feature MUST preserve Human Annotation Queue routing and review selection behavior for all candidate variants, including prompt and parameter variants.

### Functional Requirements

- **FR-001**: Users MUST be able to define a candidate variant with an optional task prompt override that includes prompt identity and required input variables.
- **FR-002**: Users MUST be able to define candidate variants that differ only by generation parameters.
- **FR-003**: Users MUST be able to define candidate variants that differ only by model or provider, preserving the current model-comparison workflow.
- **FR-004**: Users MUST be able to define candidate variants that combine prompt, model, provider, and parameter differences.
- **FR-005**: The system MUST preserve the existing candidate run workflow for running one named candidate at a time.
- **FR-006**: The system MUST keep candidate names unique within a project and use them as stable human-readable variant identifiers.
- **FR-007**: The system MUST allow candidate prompt versions to differ from the baseline prompt version without forcing a new baseline when the selected baseline is otherwise compatible.
- **FR-008**: The system MUST reject candidate prompt references that are missing, empty, or do not support required project input variables.
- **FR-009**: The system MUST record the candidate prompt version and baseline prompt version separately in run and trace metadata when they differ.
- **FR-010**: The system MUST record enough non-secret prompt identity metadata to distinguish two candidates that have the same prompt version label but different prompt content or prompt source.
- **FR-011**: The system MUST record model identity and provider identity for each candidate variant.
- **FR-012**: The system MUST record generation parameter identity for each candidate variant.
- **FR-013**: The system MUST preserve a baseline reference on every candidate output, score payload, trace, and review payload where baseline comparison is relevant.
- **FR-014**: The system MUST keep automated evaluator scores and human annotation scores attributable to the correct candidate variant and candidate run.
- **FR-015**: The system MUST allow repeated runs of the same candidate variant while preserving both unique run identity and stable variant identity.
- **FR-016**: The system MUST keep evaluator targeting metadata consistent for baseline and candidate variants so existing evaluator filters continue to match final model-output observations.
- **FR-017**: The system MUST include variant metadata in local exports so offline reports can distinguish baseline, candidate 1, candidate 2, and repeated candidate runs.
- **FR-018**: The system MUST report validation and execution errors with candidate name, prompt identity when relevant, and non-secret diagnostic context.
- **FR-019**: The system MUST NOT store secret provider credentials in variant metadata, trace metadata, local exports, or error messages.
- **FR-020**: Documentation MUST explain how to configure prompt variants, parameter variants, model variants, and mixed variants, including a prompt-v2 candidate compared against an existing prompt-v1 baseline.

### Key Entities *(include if feature involves data)*

- **Candidate Variant**: A named candidate configuration that represents one alternative to compare against a baseline. Key attributes include variant name, model identity, provider identity, optional candidate prompt identity, generation parameters, and non-secret metadata.
- **Prompt Identity**: The prompt source, version, required variables, and content identity used to explain which prompt produced a model output without storing unnecessary prompt secrets.
- **Parameter Identity**: The non-secret generation settings and stable identity used to distinguish parameter variants.
- **Baseline Reference**: The existing baseline identity used for candidate comparison, including project, dataset, evaluator set, baseline model, baseline parameters, and baseline prompt version.
- **Variant Run**: One execution of a candidate variant over the project dataset. It has unique run identity and stable variant identity.
- **Comparison Metadata**: The non-secret metadata that ties baseline outputs, candidate outputs, evaluator scores, and review items together for Langfuse comparison.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can configure and validate a prompt-v2 candidate against an existing prompt-v1 baseline in under 5 minutes after the prompt file exists.
- **SC-002**: 100% of candidate traces for prompt variants include both candidate prompt identity and baseline reference metadata.
- **SC-003**: 100% of candidate traces for parameter variants include parameter identity metadata that differs when parameter values differ.
- **SC-004**: 100% of candidate runs remain linkable to the selected baseline reference for every attempted dataset item.
- **SC-005**: Existing model-only candidates continue to validate and run without configuration changes.
- **SC-006**: Automated and human scores for baseline, candidate 1, and candidate 2 can be grouped by project, dataset item, evaluator, baseline reference, candidate variant, and run.
- **SC-007**: Repeated runs of the same candidate variant produce distinct run identities while retaining identical stable variant identity metadata.
- **SC-008**: Invalid candidate prompt references produce actionable validation errors before model generation begins.

## Assumptions

- Candidate prompt changes are intentionally treated as candidate-side differences and do not automatically invalidate an otherwise compatible baseline.
- Baseline compatibility continues to be anchored to the baseline project, dataset, evaluator set, baseline model, baseline parameters, and baseline prompt version.
- Users run one named candidate variant at a time through the current candidate workflow.
- The feature does not require a new local score store, dashboard, evaluator engine, or batch campaign scheduler.
- Langfuse remains the system of record for traces, observations, scores, comparisons, and human review routing.
- Prompt identity can include a content-derived identity so users can distinguish different prompt content even when a human-readable version label is reused.
- Existing provider credential handling and secret redaction requirements continue to apply to all model variants.
