# Feature Specification: Judge Evaluator Score Config Targeting

**Feature Branch**: `014-evaluator-score-target`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Fix Langfuse judge evaluator rule setup so each evaluator rule explicitly points its output to the resolved score config used by both LLM-as-judge and human annotation scores."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sync Judge Scores To Shared Score Configs (Priority: P1)

As an evaluation owner, I want every synced LLM-as-Judge evaluator rule to write its score into the intended project score config, so I can compare judge scores and human annotation scores for the same evaluation dimension.

**Why this priority**: Without an explicit score config target, automated judge scores can land outside the score config used by human annotation, breaking the core calibration workflow.

**Independent Test**: Can be fully tested by syncing score configs and judge evaluators for a project, then confirming each created evaluator rule is associated with the resolved score config for its evaluator dimension.

**Acceptance Scenarios**:

1. **Given** a project evaluator with a harness-managed score config, **When** the user syncs score configs and judge evaluators, **Then** the resulting evaluator rule targets the resolved score config ID for that evaluator.
2. **Given** a project evaluator with a user-owned score config ID, **When** the user syncs judge evaluators, **Then** the resulting evaluator rule targets that configured score config ID.
3. **Given** a human annotation queue using the same score config, **When** judge and human scores exist for the same observation, **Then** users can compare both score sources under the same evaluation dimension.

---

### User Story 2 - Catch Mismatched Existing Evaluator Rules (Priority: P2)

As an evaluation maintainer, I want sync and audit output to identify existing evaluator rules that point at the wrong score config, so I can fix stale or misconfigured Langfuse evaluator setup before running comparisons.

**Why this priority**: Existing projects may already have evaluator rules created before score config targeting was enforced. Users need clear feedback before trusting score comparisons.

**Independent Test**: Can be tested by presenting an existing evaluator rule whose score target differs from the project configuration and verifying sync or audit reports the mismatch clearly.

**Acceptance Scenarios**:

1. **Given** an existing harness-managed evaluator rule with a mismatched score config, **When** the user audits judge evaluator setup, **Then** the result identifies the expected score config and the current mismatched score config.
2. **Given** an existing harness-managed evaluator rule with a safely updateable score config mismatch, **When** the user applies judge evaluator sync, **Then** the rule is aligned to the expected score config or the user receives a clear remediation if alignment is not supported.
3. **Given** an existing evaluator rule without a local binding, **When** the user syncs judge evaluators, **Then** the system does not silently claim score alignment and instead keeps the existing missing-binding warning behavior.

---

### User Story 3 - Preview Score Targeting Before Applying (Priority: P3)

As a user preparing a sync, I want dry-run output to show which score config each judge evaluator will target, so I can review score alignment before changing Langfuse.

**Why this priority**: Previewing the target score config reduces mistakes in projects with many evaluators and makes the sync behavior easier to trust.

**Independent Test**: Can be tested by running judge evaluator sync in dry-run mode and verifying each planned evaluator includes the intended score config name and ID when known.

**Acceptance Scenarios**:

1. **Given** score configs have already been synced, **When** the user runs judge evaluator sync in dry-run mode, **Then** each planned evaluator shows its target score config name and ID.
2. **Given** score configs have not yet been synced and no score config ID is available, **When** the user runs judge evaluator sync in dry-run mode, **Then** the preview clearly indicates that score config sync is required before applying judge evaluator setup.

### Edge Cases

- Score config sync returns no ID because the user ran a dry-run only.
- A project uses a user-owned score config that is missing or invalid.
- A harness-managed evaluator rule already exists with the correct score config target.
- A harness-managed evaluator rule already exists with a different score config target.
- A catalog evaluator and a custom evaluator both need score config targeting.
- Langfuse returns evaluator rule data with different field naming for score config IDs.
- The remote evaluator rule cannot be updated to change the score config target.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature applies to existing evaluation projects that define datasets, baseline model configuration, candidate model configurations, evaluator definitions, score configs, and human review policy.
- **Dataset**: Feature MUST preserve support for CSV datasets with an `input` column and MUST NOT change dataset loading behavior.
- **Langfuse Logging**: Feature MUST ensure Langfuse judge evaluator rules are associated with the score config intended for the evaluator dimension, enabling judge scores and human annotation scores to be compared under the same score definition.
- **Prompt and Evaluator Versioning**: Feature MUST preserve existing prompt and evaluator version tracking and MUST NOT require users to bump evaluator versions solely to gain score config targeting for unchanged evaluator definitions.
- **Baseline**: Feature MUST preserve the existing baseline-first workflow and MUST NOT change how baseline or candidate runs are selected.
- **Human Review**: Feature MUST preserve Human Annotation Queue score config selection and ensure judge evaluator score targeting aligns with the same score configs used by human review.

### Functional Requirements

- **FR-001**: System MUST include the resolved score config target when creating a judge evaluator rule.
- **FR-002**: System MUST use the score config ID resolved during score config sync for harness-managed score configs.
- **FR-003**: System MUST use the configured score config ID for user-owned score configs.
- **FR-004**: System MUST support score config targeting for both custom judge evaluators and Langfuse managed catalog evaluators.
- **FR-005**: System MUST preserve existing variable mapping, filtering, sampling, evaluator source, model connection, and activation behavior when adding score config targeting.
- **FR-006**: System MUST surface an actionable error or blocked plan when an evaluator rule cannot be created with a required score config target.
- **FR-007**: System MUST detect whether an existing evaluator rule is already associated with the expected score config.
- **FR-008**: System MUST report a mismatch when an existing evaluator rule is associated with a different score config than the project expects.
- **FR-009**: System MUST align an existing harness-managed evaluator rule to the expected score config when that change can be applied safely.
- **FR-010**: System MUST avoid silently changing evaluator rules that are not proven to be harness-managed by local binding or equivalent harness ownership evidence.
- **FR-011**: Dry-run output MUST show the intended score config name and ID for each planned judge evaluator when the ID is available.
- **FR-012**: Dry-run output MUST clearly identify when score config sync must be applied before judge evaluator setup can be applied.
- **FR-013**: Local evaluator bindings MUST record the score config ID and name associated with the applied evaluator rule.
- **FR-014**: Existing projects that already sync judge evaluators successfully MUST continue to sync successfully, with the added score config target.
- **FR-015**: Existing tests and examples for LLM-as-Judge setup MUST be updated so they assert score config targeting rather than only storing score config details locally.

### Key Entities *(include if feature involves data)*

- **Judge Evaluator Rule**: A Langfuse evaluator configuration that runs a judge evaluator over matching traces or observations and produces scores.
- **Score Config Target**: The score config name and ID that define where a judge evaluator's produced scores should be recorded.
- **Evaluator Setup Plan**: The planned create, update, reuse, block, or fail operation for each judge evaluator, including the expected score config target.
- **Evaluator Binding**: The local record connecting a project evaluator definition to the remote evaluator rule and associated score config.
- **Score Source Pairing**: The relationship between automated LLM-as-Judge scores and human annotation scores that share the same score config.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of newly created harness-managed judge evaluator rules include a score config target.
- **SC-002**: 100% of judge evaluator rules created for the DFE general-public project target the same score configs used by the human annotation queue for matching evaluator dimensions.
- **SC-003**: Existing evaluator setup tests fail when score config targeting is omitted from evaluator rule creation.
- **SC-004**: Users can identify the target score config for every planned judge evaluator from dry-run output without inspecting source code or remote setup details.
- **SC-005**: Audit output identifies score config mismatches for existing evaluator rules with enough detail for a user to know the expected and current score config.
- **SC-006**: The targeted regression test suite for judge evaluator setup, score config sync, and annotation queue alignment completes successfully before implementation is considered ready.

## Assumptions

- Langfuse evaluator rules support associating evaluator output with a score config by score config ID.
- Score config sync remains the source of truth for resolving harness-managed score config IDs before applying judge evaluator setup.
- Human annotation queues already use the intended score config IDs and do not need behavior changes for this feature.
- Existing evaluator bindings are trusted only as local evidence of harness-managed evaluator ownership; missing bindings remain a warning or blocker rather than an automatic takeover.
- If a remote evaluator rule cannot safely update its score config target, the system should block or fail with clear remediation rather than deleting or recreating the rule silently.
