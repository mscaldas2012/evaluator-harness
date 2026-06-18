# Feature Specification: Split Langfuse Client

**Feature Branch**: `021-split-langfuse-client`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "implement backlog item TD-GRAPH-001. Review the quality reports by ruff, pyright and randon-* so that we can implement a good solution for langufse_client that will improve randon scores. Make sure you use good Design Patterns and delegate functionality appropriately"

## Clarifications

### Session 2026-06-18

- Q: What quality-report threshold should define success for the Langfuse client refactor? -> A: Improve `langfuse_client.py` maintainability from `C (0.00)` and remove all D-ranked complexity blocks from the facade.
- Q: Should existing callers migrate to new focused boundaries or keep using the current public facade? -> A: Keep the existing `LangfuseClient` public facade and move responsibilities behind it.
- Q: What live-test scope is required before accepting this refactor? -> A: The full live test suite must pass before acceptance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Langfuse Workflows Behind Clear Boundaries (Priority: P1)

As a harness maintainer, I need Langfuse dataset, run, score, prompt, evaluator, annotation queue, and trace behavior to remain available through the existing harness workflows while the current oversized client is split into focused responsibilities behind the existing public facade.

**Why this priority**: The refactor only has value if existing users keep the same CLI, configuration, and runtime behavior while maintainers gain safer boundaries for future changes.

**Independent Test**: Run the existing non-live test suite, targeted Langfuse workflow tests, and the full live test suite against the refactored code without changing project YAML or command-line usage.

**Acceptance Scenarios**:

1. **Given** an existing project configuration, **When** a user validates, syncs datasets, syncs score configs, records runs, exports results, or routes review items, **Then** the user-facing behavior and persisted Langfuse metadata match the pre-refactor behavior.
2. **Given** live Langfuse access is unavailable, **When** tests or dry-run workflows use the in-memory behavior, **Then** they complete without requiring live credentials or network access.
3. **Given** a Langfuse capability is only available through a fallback path, **When** the workflow needs that capability, **Then** the system uses the appropriate fallback while preserving current error messages and redaction behavior.

---

### User Story 2 - Improve Maintainability Hotspots (Priority: P2)

As a maintainer reviewing local quality reports, I need the Langfuse client responsibilities to show lower complexity and clearer ownership so that future fixes are localized and easier to review.

**Why this priority**: TD-GRAPH-001 exists because the current client is a central hotspot with mixed responsibilities and poor maintainability scores.

**Independent Test**: Regenerate local quality reports and compare the Langfuse-related findings against the current baseline under `reports/quality/`.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** local complexity and maintainability reports are regenerated, **Then** the public client facade no longer contains the current high-risk behavior clusters for object mapping, dataset sync, baseline lookup, prompt version lookup, trace retrieval, score loading, evaluator payload shaping, and queue conversion.
2. **Given** a maintainer needs to change one Langfuse responsibility, **When** they inspect the module layout, **Then** they can identify a focused location for that responsibility without reading unrelated fake-state, SDK, REST, retry, and mapping code.
3. **Given** static analysis is run on changed files, **When** diagnostics are reviewed, **Then** the refactor introduces no new lint or type-checking categories in those files.

---

### User Story 3 - Keep Tests and Fakes Representative (Priority: P3)

As a developer adding or debugging Langfuse behavior, I need the in-memory behavior used by tests to exercise the same public contracts as live behavior, so that unit and integration tests catch contract drift.

**Why this priority**: The current in-memory fake behavior is useful, but mixing it into the live client makes ownership unclear and weakens the confidence of tests.

**Independent Test**: Run focused tests that exercise the shared Langfuse boundary with both in-memory and live-compatible paths, using deterministic data and without live credentials where possible.

**Acceptance Scenarios**:

1. **Given** a test uses the in-memory Langfuse behavior, **When** it creates datasets, records runs, records scores, retrieves traces, or queues review items, **Then** it observes the same public data shape expected from live-compatible behavior.
2. **Given** live behavior returns partial or missing objects, **When** the system normalizes those results, **Then** downstream code receives stable typed records or explicit harness errors.

---

### User Story 4 - Split Query Workflows Into Owner Modules (Priority: P3)

As a maintainer continuing the Langfuse refactor, I need the temporary `langfuse_queries.py` extraction bucket to be split into owner modules for baselines, prompts, traces, scores, and settings so query workflow changes are localized to the responsible Langfuse area.

**Why this priority**: The public facade improved, but the current quality report still shows `langfuse_queries.py - C (0.00)`. Leaving mixed query workflows in one module recreates the same ownership problem at a smaller scale.

**Independent Test**: Move query workflow functions behind owner modules while preserving facade behavior, then run the focused Langfuse facade/gateway tests and Radon checks for `src/evaluator_harness/langfuse_*.py`.

**Acceptance Scenarios**:

1. **Given** a maintainer needs to change baseline lookup behavior, **When** they inspect the Langfuse modules, **Then** baseline matching, metadata comparison, and baseline sort behavior are owned by a baseline-focused module.
2. **Given** a maintainer needs to change prompt version, trace retrieval, or score retrieval behavior, **When** they inspect the Langfuse modules, **Then** each workflow is located in a corresponding prompt, trace, or score-focused module rather than in a mixed query bucket.
3. **Given** existing callers still use `LangfuseClient`, **When** query workflows are moved, **Then** caller behavior and public facade signatures remain unchanged.

---

### Edge Cases

- Live SDK support may be incomplete for some evaluator, queue, score, prompt, or trace operations and must continue to use the existing REST-compatible fallback behavior.
- Langfuse workspace verification, listing, and sync operations can fail with authentication, permission, network, or API-shape errors; the refactor must keep existing contextual errors and secret redaction.
- Existing tests rely on deterministic in-memory state and must not become dependent on live credentials.
- Dataset runs may contain missing metadata, missing baseline references, or no matching traces; current fallback semantics must be preserved.
- Score config, prompt, evaluator, and annotation queue objects may arrive as SDK objects, dictionaries, or partially populated records; normalization must remain defensive and explicit.
- Long-running retry or pagination behavior must stay bounded and observable enough for failures to be diagnosed.
- Temporary compatibility re-exports may be needed while `langfuse_queries.py` is drained; those re-exports must be removed once direct imports are updated.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project Compatibility**: Feature MUST preserve existing project YAML semantics for datasets, baseline model configuration, candidate model configurations, evaluator definitions, Langfuse logging, and review policy.
- **Dataset Compatibility**: Feature MUST preserve support for current dataset sync and run recording workflows, including dataset items, run metadata, baseline references, candidate outputs, and exported comparison data.
- **Langfuse Logging Compatibility**: Feature MUST preserve current trace, observation, score, run metadata, evaluator metadata, baseline reference, annotation queue, and comparison metadata behavior.
- **Prompt and Evaluator Versioning**: Feature MUST preserve current prompt version lookup and evaluator configuration synchronization behavior, including fallback behavior when live capabilities are limited.
- **Baseline Compatibility**: Feature MUST preserve current baseline lookup, reuse, and candidate comparison behavior.
- **Human Review Compatibility**: Feature MUST preserve current annotation queue routing and review item behavior for workflows that use Langfuse human review.

### Functional Requirements

- **FR-001**: The system MUST keep the existing public harness workflows and CLI commands compatible for Langfuse-backed validation, sync, run, export, and review operations.
- **FR-002**: The system MUST separate Langfuse responsibilities into focused boundaries for in-memory behavior, live service interaction, fallback service interaction, object normalization, retry handling, and public workflow orchestration.
- **FR-003**: The existing `LangfuseClient` public facade MUST remain the compatibility layer for current callers and MUST hide whether a workflow uses in-memory behavior, SDK-backed behavior, or REST-compatible fallback behavior.
- **FR-004**: The system MUST preserve current in-memory behavior for tests, dry runs, and local development without live credentials.
- **FR-005**: The system MUST normalize external Langfuse objects into stable internal records before downstream harness code consumes them.
- **FR-006**: The system MUST preserve existing error semantics, contextual operation names, and secret redaction for Langfuse failures.
- **FR-007**: The system MUST reduce the concentration of unrelated responsibilities in the current Langfuse client facade so that dataset sync, trace retrieval, score handling, prompt/version lookup, evaluator setup, annotation queues, and object mapping can be maintained independently.
- **FR-008**: The system MUST add or update tests that prove the shared Langfuse boundary behaves consistently for in-memory and live-compatible workflows.
- **FR-009**: The system MUST introduce no new lint or type-checking diagnostic categories in changed files and SHOULD reduce existing type uncertainty around optional values and external object attributes in Langfuse-related code.
- **FR-010**: The system MUST regenerate local quality reports after implementation so maintainers can compare the new Langfuse hotspots against the current baseline.
- **FR-011**: The refactor MUST improve `langfuse_client.py` maintainability from the current `C (0.00)` baseline and remove all D-ranked complexity blocks from the public client facade.
- **FR-012**: The full live test suite MUST pass before the refactor is accepted.
- **FR-013**: The system MUST split mixed query workflow functions out of `langfuse_queries.py` into focused baseline, prompt, trace, score, and settings owner modules while preserving facade behavior.
- **FR-014**: The query split SHOULD eliminate `langfuse_queries.py` as an implementation module or reduce it to a temporary compatibility re-export layer with no business logic.

### Key Entities *(include if feature involves data)*

- **Langfuse Client Facade**: The stable entry point used by the rest of the harness for Langfuse-backed workflows.
- **Langfuse Boundary**: The contract that defines dataset, run, trace, score, prompt, evaluator, and annotation queue operations without exposing the backing implementation.
- **In-Memory Langfuse Behavior**: Deterministic local behavior used by tests, dry runs, and developer workflows without live credentials.
- **Live Langfuse Behavior**: Behavior that communicates with Langfuse through supported live service capabilities.
- **Fallback Langfuse Behavior**: Behavior that handles live operations not covered by the primary live interface while preserving current compatibility.
- **Langfuse Record Mapper**: The normalization layer that converts external objects or dictionaries into stable harness records.
- **Retry and Error Policy**: The rules for retrying, contextualizing, redacting, and surfacing Langfuse operation failures.
- **Query Workflow Owner Module**: A focused module that owns one Langfuse query workflow area, such as baselines, prompts, traces, scores, or Langfuse polling settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Existing non-live tests pass without requiring changes to project YAML, CLI commands, user-facing workflow names, or current `LangfuseClient` caller usage.
- **SC-002**: Local quality reports show `langfuse_client.py` maintainability improved from `C (0.00)` and no D-ranked complexity blocks remaining in the public client facade.
- **SC-003**: Maintainers can identify the owner module for dataset sync, trace retrieval, score handling, prompt/version lookup, evaluator setup, annotation queues, object mapping, and retry/error policy from module names and public boundaries alone.
- **SC-004**: In-memory tests cover the same public Langfuse data shapes used by live-compatible workflows for datasets, runs, traces, scores, prompts, evaluators, and review queues.
- **SC-005**: Changed Langfuse-related files introduce no new lint or type-checking diagnostic categories compared with the current local quality-report baseline.
- **SC-006**: The full live test suite passes with the configured live environment before acceptance.
- **SC-007**: Local Radon maintainability no longer reports `src\evaluator_harness\langfuse_queries.py - C (0.00)` after query workflow ownership is split into focused modules.

## Assumptions

- The current quality-report baseline is the set of local reports under `reports/quality/`, including Ruff, Pyright, and Radon output.
- This work is a behavior-preserving architectural refactor, not a request to add new Langfuse features or change existing CLI behavior.
- The refactor will proceed behind the existing `LangfuseClient` public facade so callers outside the Langfuse integration do not need broad changes.
- Live tests depend on valid external credentials and service availability and are required for acceptance; non-live tests must remain deterministic and credential-free.
