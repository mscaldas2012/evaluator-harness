# Feature Specification: Shared Run Item Execution

**Feature Branch**: `023-shared-run-execution`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "TD-GRAPH-003: Extract shared run-item execution from ExperimentRunner. Baseline and candidate execution duplicate trace creation, prompt rendering, session identity, request metadata, provider invocation, trace logging, dataset run item recording, and failure trace logging. Extract a RunExecutor or equivalent shared per-item execution path with separate baseline and candidate run plans."

## Clarifications

### Session 2026-06-22

- Q: How strict should behavior preservation be while extracting shared baseline and candidate item execution? -> A: Strict preservation, with only explicitly tested parity fixes allowed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Per-Item Run Evidence (Priority: P1)

As a harness user comparing baseline and candidate runs, I need each dataset item to produce consistent trace, metadata, prompt, session, dataset run item, and failure evidence regardless of run type, so comparison results are trustworthy and easier to audit.

**Why this priority**: Baseline and candidate execution are the core workflow. Divergent behavior between the two paths can create misleading comparisons, incomplete Langfuse evidence, or inconsistent reports.

**Independent Test**: Can be tested by running equivalent baseline and candidate items and confirming that shared evidence fields, success handling, and failure handling are present and consistent for both run types.

**Acceptance Scenarios**:

1. **Given** a baseline run and a candidate run over the same dataset item, **When** both items complete successfully, **Then** both runs record equivalent trace identity, prompt rendering, session identity, request metadata, output metadata, and dataset run item linkage for the item.
2. **Given** a provider error occurs while executing either a baseline or candidate item, **When** the item is recorded, **Then** the user can inspect a failure trace with the same required diagnostic fields and item linkage shape for both run types.
3. **Given** a run uses live Langfuse logging, **When** per-item execution completes, **Then** success and failure evidence preserves existing Langfuse warning and partial-persistence reporting behavior.

---

### User Story 2 - Preserve Run-Type Specific Behavior (Priority: P2)

As a harness user, I need shared item execution to preserve the differences between baseline and candidate runs, so baseline creation, candidate comparison, evaluator inputs, prompt identity, and baseline references remain correct.

**Why this priority**: Removing duplication must not erase meaningful behavior. Baselines and candidates share execution mechanics but differ in comparison context and evaluator payloads.

**Independent Test**: Can be tested by running a baseline workflow and a candidate workflow, then verifying that run summaries, evaluator payloads, baseline references, and comparison metadata match existing user-visible behavior.

**Acceptance Scenarios**:

1. **Given** a baseline run completes, **When** evaluator work is queued or recorded, **Then** the baseline item output, ground truth, evaluator definitions, and baseline reference information remain available as before.
2. **Given** a candidate run completes against a selected baseline, **When** evaluator work is queued or recorded, **Then** the candidate output, resolved baseline output, baseline reference, prompt identities, parameter identities, and variant identity remain available as before.
3. **Given** a candidate prompt override is configured, **When** candidate items run, **Then** prompt rendering and prompt identity reflect the candidate-specific prompt without changing baseline prompt behavior.

---

### User Story 3 - Safer Future Run Changes (Priority: P3)

As a maintainer, I need one documented per-item execution behavior shared by baseline and candidate runs, so future changes to trace logging, prompt metadata, session identity, and dataset run item recording can be made once and verified once.

**Why this priority**: The backlog item is technical debt, and its value is reducing the chance that future behavior fixes land in only one run path.

**Independent Test**: Can be tested by adding or changing a shared per-item evidence requirement and confirming that the same verification covers both baseline and candidate execution.

**Acceptance Scenarios**:

1. **Given** a shared per-item evidence field is required, **When** baseline and candidate runs are tested, **Then** the same requirement applies to both run types without duplicate acceptance criteria.
2. **Given** a run-type-specific field is required, **When** run plans are validated, **Then** the field is supplied only for the applicable run type and does not leak into the other run type.
3. **Given** a future maintainer reviews the run behavior, **When** they inspect tests and documentation, **Then** they can identify the shared per-item contract and the baseline/candidate-specific extensions.

---

### Edge Cases

- A provider rejects a prompt because the rendered prompt roles are invalid for the selected model.
- A provider call fails after trace identity, session identity, and request metadata have already been prepared.
- Live Langfuse accepts the trace but fails to record the dataset run item linkage.
- A candidate item needs a baseline output that is unavailable or cannot be resolved for the selected baseline.
- Baseline and candidate runs use different prompt references while sharing the same dataset and session identity inputs.
- Manual generation observations are enabled for one provider and not another.
- A dataset item has optional fields such as ground truth or metadata omitted.
- A run has zero eligible items or all items fail.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: The feature MUST preserve existing evaluation project identity, including datasets, baseline model configuration, candidate model configurations, evaluator definitions, and review policy.
- **Dataset**: The feature MUST preserve support for CSV datasets with an `input` column and Langfuse-hosted datasets.
- **Langfuse Logging**: The feature MUST preserve trace creation, observation linkage, run metadata, output metadata, dataset run item recording, warning reporting, and failure trace logging for baseline and candidate items.
- **Prompt and Evaluator Versioning**: The feature MUST preserve prompt identity, prompt rendering details, evaluator names, evaluator versions, score configuration references, and candidate prompt override behavior.
- **Baseline**: The feature MUST preserve baseline creation, baseline reference recording, baseline lookup, and candidate consumption of a resolved baseline.
- **Human Review**: The feature MUST preserve downstream review and annotation behavior by keeping trace, score, dataset item, and run metadata available in the same user-visible shape.

### Functional Requirements

- **FR-001**: The system MUST define a shared per-item execution contract used by both baseline and candidate runs for prompt rendering, request metadata, session identity, provider invocation, trace evidence, dataset run item linkage, completion counting, and failure counting.
- **FR-002**: The system MUST allow baseline and candidate run plans to provide run-type-specific inputs without duplicating shared item execution behavior.
- **FR-003**: The system MUST preserve the existing user-visible run summary fields for baseline and candidate runs, including completed item count, failed item count, Langfuse status, Langfuse warnings, and model output targeting diagnostics.
- **FR-004**: The system MUST preserve baseline-specific evaluator payload content, including item input, item output, ground truth, evaluator definitions, and score configuration references.
- **FR-005**: The system MUST preserve candidate-specific evaluator payload content, including candidate output, baseline output, baseline reference, prompt identities, parameter identities, variant identity, ground truth, and evaluator definitions.
- **FR-006**: The system MUST record success traces for baseline and candidate items with equivalent required evidence fields and with run-type-specific metadata only where appropriate.
- **FR-007**: The system MUST record failure traces for baseline and candidate items when item execution fails after trace preparation, including item identity, run identity, prompt evidence, session identity, and redacted error information.
- **FR-008**: The system MUST continue recording dataset run item linkage for both successful and failed items whenever item identity and trace identity are available.
- **FR-009**: The system MUST preserve live Langfuse warning and partial-persistence reporting for trace and dataset run item operations.
- **FR-010**: The system MUST preserve manual generation observation behavior for providers that require it, without changing behavior for providers that do not.
- **FR-011**: The system MUST preserve existing behavior for credential-free dry runs and non-live tests.
- **FR-012**: The system MUST make baseline and candidate item execution verifiable through shared tests plus targeted run-type-specific tests.
- **FR-013**: The system MUST avoid changing command names, project configuration shape, dataset format, report format, or required user workflow as part of this feature.
- **FR-014**: The system MUST preserve current user-visible behavior exactly unless a baseline/candidate parity fix is explicitly identified, documented, and covered by regression tests.

### Key Entities

- **Run Item Execution Contract**: The user-visible agreement for how one dataset item is prepared, invoked, traced, linked to a dataset run item, counted, and reported.
- **Run Plan**: The per-run-type description of item execution inputs, including model selection, prompt source, baseline context, evaluator payload needs, and run metadata.
- **Run Item Evidence**: The trace, observation, prompt, session, request metadata, output, error, and dataset run item information produced for a single dataset item.
- **Baseline Item Result**: The result of executing one dataset item as part of a baseline run, including output evidence and baseline evaluator context.
- **Candidate Item Result**: The result of executing one dataset item as part of a candidate run, including output evidence, resolved baseline context, and candidate comparison metadata.
- **Failure Evidence**: The item-level trace and metadata that remain available when provider invocation or related item execution fails.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In regression tests, 100% of baseline and candidate successful item runs include the same required shared evidence fields.
- **SC-002**: In regression tests with simulated provider failures, 100% of baseline and candidate item failures produce failure evidence with item identity, run identity, prompt evidence, session identity, and redacted error information.
- **SC-003**: Existing baseline and candidate workflow tests continue to pass with no required changes to command input, project configuration, dataset format, or report consumption.
- **SC-004**: Tests cover at least one baseline-specific payload requirement and at least one candidate-specific payload requirement after shared execution is introduced.
- **SC-005**: Live or simulated Langfuse partial-persistence warnings continue to appear for affected trace or dataset run item operations in both baseline and candidate paths.
- **SC-006**: Maintainers can validate shared per-item behavior for both run types with one shared test fixture or assertion path, plus targeted tests for run-type-specific differences.

## Assumptions

- The target users are local harness users and maintainers who rely on baseline and candidate run parity.
- This feature is a behavior-preserving refactor from the user perspective; changes to command syntax, project YAML, dataset schema, and report schema are out of scope.
- Baseline and candidate runs should continue to differ only where their evaluation semantics require different context or payloads.
- Any correction to accidental drift between baseline and candidate shared mechanics must be treated as an intentional parity fix rather than incidental refactor fallout.
- Existing Langfuse failure-surfacing behavior from `022-surface-langfuse-failures` remains in scope and must not regress.
- Automated retry, new queueing behavior, and new report types are out of scope unless needed to preserve existing behavior.
