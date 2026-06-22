# Feature Specification: Surface Live Langfuse Failures

**Feature Branch**: `022-surface-langfuse-failures`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "TD-GRAPH-002: Surface live Langfuse partial persistence and lookup failures"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Partial Langfuse Persistence (Priority: P1)

As a harness user running live experiments, I need the run outcome to tell me when Langfuse persistence only partially succeeded, so I do not treat incomplete trace, dataset, score, or run-item linkage as a fully successful evaluation.

**Why this priority**: Silent partial persistence undermines the core value of the harness because a run can appear complete while the evidence needed for audit, comparison, and review is missing.

**Independent Test**: Can be tested by simulating a live run where primary model/evaluator work completes but one Langfuse persistence action fails; the command result and report clearly identify the partial-success condition and affected records.

**Acceptance Scenarios**:

1. **Given** a live candidate run where provider output succeeds and Langfuse dataset run item recording fails for one item, **When** the run completes, **Then** the user sees a partial-success warning naming the affected item and linkage type.
2. **Given** a live baseline run where traces are recorded but score retrieval fails, **When** the user requests comparison or export, **Then** the user sees a warning that scores could not be confirmed rather than an empty score set presented as complete.
3. **Given** multiple items have different Langfuse persistence outcomes, **When** the run summary is shown, **Then** the summary groups outcomes by success, expected not-found, and failure.

---

### User Story 2 - Distinguish Expected Not-Found From Failures (Priority: P2)

As a harness user selecting baselines, traces, dataset items, or scores, I need expected absence to be reported differently from lookup errors, so I know whether to change my selection or investigate Langfuse connectivity or permissions.

**Why this priority**: Expected not-found is a normal workflow condition, but lookup failure indicates loss of confidence in the run or comparison.

**Independent Test**: Can be tested by exercising lookup flows with one expected missing record and one simulated access or service failure; the user-facing outcome distinguishes the two cases.

**Acceptance Scenarios**:

1. **Given** a user requests a baseline selector that does not match any compatible run, **When** lookup completes without service errors, **Then** the result is reported as not found without implying persistence failure.
2. **Given** Langfuse cannot be queried because of an access, connectivity, or unexpected service error, **When** baseline lookup is attempted, **Then** the result reports lookup failure and does not silently fall back to a different source as if live lookup succeeded.
3. **Given** a dataset item is absent from a live dataset, **When** the harness attempts to link a dataset run item, **Then** the report distinguishes missing item identity from failed persistence.

---

### User Story 3 - Preserve Workflow Completion While Reporting Risk (Priority: P3)

As a harness user, I want non-critical Langfuse issues to be collected and surfaced without unnecessarily stopping all completed model work, so I can decide whether to rerun, repair, or proceed with caveats.

**Why this priority**: Some Langfuse linkage failures are operationally recoverable, and users should be able to inspect completed outputs while understanding confidence limits.

**Independent Test**: Can be tested by running a workflow with recoverable Langfuse failures and confirming the command still produces local outputs while presenting structured warnings and an appropriate overall status.

**Acceptance Scenarios**:

1. **Given** model responses are produced but some Langfuse writebacks fail, **When** the command exits, **Then** local outputs remain available and the final status identifies the run as completed with warnings.
2. **Given** a Langfuse failure prevents a required baseline or comparison input from being established, **When** the command reaches the dependent step, **Then** the command fails with a clear reason instead of producing a misleading comparison.
3. **Given** warning details include service error information, **When** they are shown or exported, **Then** secrets and credential values are not exposed.

---

### Edge Cases

- Live Langfuse is unreachable before any work starts.
- Live Langfuse becomes unavailable after some records have already been written.
- A lookup returns an empty result that is valid for the requested selector.
- A lookup returns an empty result because pagination, permissions, or service errors prevented a complete search.
- A dataset item can be identified locally but not resolved to a live Langfuse identity.
- A score lookup succeeds for some traces and fails for others.
- A fallback source contains stale data that does not match the live lookup outcome.
- Multiple warnings occur for the same run item and should not overwhelm the user with duplicate messages.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: The feature MUST preserve existing evaluation project identity, including datasets, baseline model configuration, candidate model configurations, evaluator definitions, and review policy.
- **Dataset**: The feature MUST preserve support for local CSV datasets and Langfuse-hosted datasets.
- **Langfuse Logging**: The feature MUST surface incomplete trace, observation, score, dataset, run metadata, baseline reference, comparison metadata, and annotation queue linkage when live Langfuse operations partially fail.
- **Prompt and Evaluator Versioning**: The feature MUST preserve existing prompt and evaluator version association with runs, and MUST warn when live lookup failure prevents confirmation of those associations.
- **Baseline**: The feature MUST preserve baseline create, select, reuse, and consume behavior while clearly distinguishing baseline not-found from baseline lookup failure.
- **Human Review**: The feature MUST preserve Human Annotation Queue behavior and MUST surface failures that prevent review items from being fully linked to Langfuse traces, scores, or dataset items.

### Functional Requirements

- **FR-001**: The system MUST classify live Langfuse outcomes as successful, expected not-found, partial success, or failure for each affected workflow step.
- **FR-002**: The system MUST report partial-success conditions in command summaries and exported run artifacts when model work completes but live Langfuse persistence or lookup is incomplete.
- **FR-003**: The system MUST distinguish expected not-found results from lookup or persistence failures for baseline lookup, dataset run metadata lookup, dataset item lookup, dataset run item recording, trace lookup, and score retrieval.
- **FR-004**: The system MUST avoid presenting failed live lookups as empty successful results.
- **FR-005**: The system MUST avoid silently falling back to local or cached data after a live lookup failure unless the user-facing result records that fallback and the original failure.
- **FR-006**: The system MUST include enough context in warnings for users to identify the affected project, run, dataset, item, trace, score, or baseline selector.
- **FR-007**: The system MUST redact secrets, credentials, and sensitive headers from all warnings, errors, reports, and exported artifacts.
- **FR-008**: The system MUST preserve completed local outputs when live Langfuse persistence fails after model or evaluator work has completed.
- **FR-009**: The system MUST fail the workflow when a live Langfuse failure prevents a required baseline, dataset identity, or comparison input from being established.
- **FR-010**: The system MUST aggregate repeated failures so users can see counts and representative examples without duplicate noise.
- **FR-011**: The system MUST make live failure outcomes testable without requiring real service outages.
- **FR-012**: The system MUST preserve current behavior for credential-free dry runs and non-live tests, except that simulated live failures can now produce structured warnings.

### Key Entities

- **Langfuse Operation Outcome**: A user-visible result for a live lookup or persistence action, including status, affected object identity, operation name, message, and redacted diagnostic details.
- **Partial Persistence Warning**: A warning that model or evaluator work completed but one or more Langfuse records, links, or confirmations did not complete.
- **Expected Not-Found Result**: A normal absence result where the requested baseline, dataset item, trace, or score was searched successfully and not found.
- **Live Lookup Failure**: A failed attempt to search or confirm live Langfuse data because of access, connectivity, service, pagination, malformed response, or unexpected client failure.
- **Run Completion Summary**: The final user-facing summary that combines model/evaluator success with Langfuse persistence and lookup confidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In test scenarios with simulated live persistence failure, 100% of affected runs report a partial-success warning instead of a fully successful status.
- **SC-002**: In test scenarios with expected missing baselines, traces, dataset items, or scores, 100% of outcomes are reported as not found without being classified as failures.
- **SC-003**: In test scenarios with live lookup failures, 100% of outcomes identify the failure and do not return an unqualified empty result.
- **SC-004**: Users can identify the affected run item, trace, dataset, score, or baseline selector from each warning without reading debug logs.
- **SC-005**: Secret and credential values are absent from all failure messages and exported warning artifacts in test scenarios.
- **SC-006**: Existing non-live workflows continue to complete successfully while adding no new required live credentials.

## Assumptions

- The target users are local harness users running live Langfuse-backed evaluation workflows.
- Expected not-found remains a valid outcome for user-selected baselines, empty score sets, and missing optional lookup targets when the search itself succeeds.
- Live persistence failures after model work should generally preserve local outputs and surface warnings, unless the missing live data is required for the requested command to produce a valid result.
- Existing command names, project YAML shape, dataset format, prompt references, evaluator definitions, and review policy configuration remain unchanged.
- The first implementation will focus on live Langfuse persistence and lookup visibility, not on automated repair or retry-after-run workflows.
