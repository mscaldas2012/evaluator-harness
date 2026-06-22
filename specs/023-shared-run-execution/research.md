# Research: Shared Run Item Execution

## Decision: Use a shared per-item execution path with explicit run plans

**Rationale**: Baseline and candidate item execution share the same mechanics: trace identity, prompt rendering, session identity, request metadata, provider invocation, trace logging, dataset run item recording, completion/failure counting, and failure trace logging. A shared path reduces duplication while allowing run plans to carry the differences that are semantically meaningful for baseline and candidate workflows.

**Alternatives considered**:

- Keep duplicated code and add tests around both paths. Rejected because it leaves the original maintenance problem in place.
- Move all baseline/candidate execution into separate service classes. Rejected for now because it adds a larger subsystem than the feature needs.
- Normalize baseline and candidate behavior aggressively. Rejected because the clarification requires strict behavior preservation except for explicit parity fixes.

## Decision: Keep run setup and finalization in the existing run methods

**Rationale**: Baseline setup creates a baseline reference and candidate setup resolves a compatible baseline before item execution. Finalization records baseline references, targeting diagnostics, Langfuse status, and run summaries. Keeping those responsibilities in the current run methods preserves the visible workflow and limits the shared path to per-item behavior.

**Alternatives considered**:

- Create one generic run method for both baseline and candidate. Rejected because baseline creation and candidate comparison have different lifecycle requirements.
- Extract only tiny helper functions. Rejected because it would remove less duplication and leave the core item execution sequence split across both paths.

## Decision: Treat parity corrections as explicit, tested changes

**Rationale**: The feature is a behavior-preserving refactor. If the shared path reveals accidental drift in shared mechanics, such as different failure trace evidence or dataset run item behavior, the implementation may correct it only when the difference is documented and covered by regression tests.

**Alternatives considered**:

- Preserve every current difference exactly. Rejected because it can preserve accidental defects and make the shared path harder to reason about.
- Freely normalize all differences. Rejected because it increases behavior-change risk beyond the backlog item.

## Decision: Preserve Langfuse warning propagation unchanged

**Rationale**: Feature 022 added structured warning and partial-persistence behavior. Shared item execution must continue collecting and reporting Langfuse warnings through the existing gateway/run-result path, especially when trace or dataset run item operations partially fail.

**Alternatives considered**:

- Add a new warning channel specific to run-item execution. Rejected because it duplicates existing gateway warning aggregation.
- Suppress warning tests during refactor. Rejected because warning regressions would directly violate the feature spec.

## Decision: Verify shared behavior through focused regression tests

**Rationale**: Existing integration tests already exercise baseline and candidate workflows. The implementation should add or consolidate assertions for shared item evidence while preserving targeted tests for baseline-specific and candidate-specific evaluator payloads.

**Alternatives considered**:

- Rely only on broad non-live test coverage. Rejected because failures would be harder to diagnose.
- Add live-only coverage. Rejected because this feature must remain credential-free for primary verification.
