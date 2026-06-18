# Feature Specification: Split Langfuse Client

**Feature Branch**: `021-split-langfuse-client`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "implement backlog item TD-GRAPH-001. Review the quality reports by ruff, pyright and randon-* so that we can implement a good solution for langufse_client that will improve randon scores. Make sure you use good Design Patterns and delegate functionality appropriately"

**Scope Update**: User description: "update the current specification to go ahead and deprecate langfuse_client completely and use the new langfuse_gateway and its classes across the project"

## Clarifications

### Session 2026-06-18

- Q: What quality-report threshold should define success for the Langfuse client refactor? -> A: Improve `langfuse_client.py` maintainability from `C (0.00)` and remove all D-ranked complexity blocks from the facade. Superseded by the scope update: `langfuse_client.py` should no longer be an active runtime workflow hotspot.
- Q: Should existing callers migrate to new focused boundaries or keep using the current public facade? -> A: Superseded. Existing internal callers should now migrate to the Langfuse gateway boundary and focused owner modules instead of keeping `LangfuseClient` as the public facade.
- Q: What live-test scope is required before accepting this refactor? -> A: The full live test suite must pass before acceptance.
- Scope update: The original facade-preservation decision is superseded. Internal project callers should migrate from `LangfuseClient` to the Langfuse gateway boundary and concrete gateway classes. `LangfuseClient` should no longer be an active runtime facade for project workflows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Langfuse Workflows Through Gateway Boundaries (Priority: P1)

As a harness maintainer, I need Langfuse dataset, run, score, prompt, evaluator, annotation queue, and trace behavior to remain available through the existing harness workflows while current callers move from the oversized client facade to the shared Langfuse gateway boundary.

**Why this priority**: The refactor only has value if users keep the same CLI, configuration, and runtime behavior while maintainers eliminate the legacy facade as an active dependency.

**Independent Test**: Run the existing non-live test suite, targeted Langfuse workflow tests, and the full live test suite against gateway-backed workflows without changing project YAML or command-line usage.

**Acceptance Scenarios**:

1. **Given** an existing project configuration, **When** a user validates, syncs datasets, syncs score configs, records runs, exports results, or routes review items, **Then** the user-facing behavior and persisted Langfuse metadata match the pre-refactor behavior without requiring `LangfuseClient` as the runtime entry point.
2. **Given** live Langfuse access is unavailable, **When** tests or dry-run workflows use the in-memory behavior, **Then** they complete without requiring live credentials or network access.
3. **Given** a Langfuse capability is only available through a fallback path, **When** the workflow needs that capability, **Then** the system uses the appropriate fallback while preserving current error messages and redaction behavior.
4. **Given** maintainers inspect production source, **When** they search for internal runtime imports, **Then** project workflows depend on the gateway boundary or focused modules rather than `LangfuseClient`.

---

### User Story 2 - Improve Maintainability Hotspots (Priority: P2)

As a maintainer reviewing local quality reports, I need the Langfuse client responsibilities to show lower complexity and clearer ownership so that future fixes are localized and easier to review.

**Why this priority**: TD-GRAPH-001 exists because the current client is a central hotspot with mixed responsibilities and poor maintainability scores.

**Independent Test**: Regenerate local quality reports and compare the Langfuse-related findings against the current baseline under `reports/quality/`.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** local complexity and maintainability reports are regenerated, **Then** no active runtime client facade contains the current high-risk behavior clusters for object mapping, dataset sync, baseline lookup, prompt version lookup, trace retrieval, score loading, evaluator payload shaping, and queue conversion.
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

As a maintainer continuing the Langfuse refactor, I need mixed query workflow ownership to live in focused modules for baselines, prompts, traces, scores, and settings so query workflow changes are localized to the responsible Langfuse area.

**Why this priority**: The public facade split improved the original hotspot, but mixed query workflow buckets recreate the same ownership problem at a smaller scale.

**Independent Test**: Move query workflow functions behind owner modules while preserving gateway-backed workflow behavior, then run the focused Langfuse gateway tests and Radon checks for `src/evaluator_harness/langfuse_*.py`.

**Acceptance Scenarios**:

1. **Given** a maintainer needs to change baseline lookup behavior, **When** they inspect the Langfuse modules, **Then** baseline matching, metadata comparison, and baseline sort behavior are owned by a baseline-focused module.
2. **Given** a maintainer needs to change prompt version, trace retrieval, or score retrieval behavior, **When** they inspect the Langfuse modules, **Then** each workflow is located in a corresponding prompt, trace, or score-focused module rather than in a mixed query bucket.
3. **Given** project callers have migrated to the gateway boundary, **When** query workflows are moved, **Then** caller behavior remains unchanged and no active workflow imports the legacy client facade.

---

### Edge Cases

- Live SDK support may be incomplete for some evaluator, queue, score, prompt, or trace operations and must continue to use the existing REST-compatible fallback behavior.
- Langfuse workspace verification, listing, and sync operations can fail with authentication, permission, network, or API-shape errors; the refactor must keep existing contextual errors and secret redaction.
- Existing tests rely on deterministic in-memory state and must not become dependent on live credentials.
- Dataset runs may contain missing metadata, missing baseline references, or no matching traces; current fallback semantics must be preserved.
- Score config, prompt, evaluator, and annotation queue objects may arrive as SDK objects, dictionaries, or partially populated records; normalization must remain defensive and explicit.
- Long-running retry or pagination behavior must stay bounded and observable enough for failures to be diagnosed.
- Temporary compatibility re-exports are not a target end state; once direct imports are updated, mixed query modules should be removed from active implementation.
- Legacy `LangfuseClient` imports may exist in downstream or external code; this feature only guarantees migration of this repository's active workflows and tests unless a separate public-API compatibility requirement is added.

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
- **FR-003**: Active project callers MUST migrate from `LangfuseClient` to the Langfuse gateway boundary, gateway factory, focused workflow modules, or concrete gateway classes as appropriate.
- **FR-004**: The system MUST preserve current in-memory behavior for tests, dry runs, and local development without live credentials.
- **FR-005**: The system MUST normalize external Langfuse objects into stable internal records before downstream harness code consumes them.
- **FR-006**: The system MUST preserve existing error semantics, contextual operation names, and secret redaction for Langfuse failures.
- **FR-007**: The system MUST remove active workflow responsibility from the current Langfuse client facade so that dataset sync, trace retrieval, score handling, prompt/version lookup, evaluator setup, annotation queues, and object mapping are maintained independently.
- **FR-008**: The system MUST add or update tests that prove the shared Langfuse boundary behaves consistently for in-memory and live-compatible workflows.
- **FR-009**: The system MUST introduce no new lint or type-checking diagnostic categories in changed files and SHOULD reduce existing type uncertainty around optional values and external object attributes in Langfuse-related code.
- **FR-010**: The system MUST regenerate local quality reports after implementation so maintainers can compare the new Langfuse hotspots against the current baseline.
- **FR-011**: The refactor MUST eliminate `langfuse_client.py` as an active maintainability hotspot by removing it from internal runtime usage or reducing it to a non-runtime deprecation surface with no workflow logic.
- **FR-012**: The full live test suite MUST pass before the refactor is accepted.
- **FR-013**: The system MUST split mixed query workflow functions into focused baseline, prompt, trace, score, and settings owner modules while preserving gateway-backed workflow behavior.
- **FR-014**: The query split MUST eliminate mixed query modules as active implementation modules once direct imports are updated.
- **FR-015**: Internal source and test code MUST have no active dependency on `LangfuseClient` for Langfuse workflow execution once migration is complete.
- **FR-016**: If any legacy `LangfuseClient` symbol remains, it MUST be explicitly documented as deprecated and MUST NOT contain dataset, run, score, prompt, evaluator, annotation queue, trace, retry, or mapping workflow logic.

### Key Entities *(include if feature involves data)*

- **Legacy Langfuse Client Facade**: The deprecated former entry point that must no longer be used by active project workflows.
- **Langfuse Gateway Boundary**: The contract that defines dataset, run, trace, score, prompt, evaluator, and annotation queue operations without exposing the backing implementation.
- **Langfuse Gateway Factory**: The construction path that selects in-memory, live, and fallback-capable gateway behavior for project workflows.
- **In-Memory Langfuse Behavior**: Deterministic local behavior used by tests, dry runs, and developer workflows without live credentials.
- **Live Langfuse Behavior**: Behavior that communicates with Langfuse through supported live service capabilities.
- **Fallback Langfuse Behavior**: Behavior that handles live operations not covered by the primary live interface while preserving current compatibility.
- **Langfuse Record Mapper**: The normalization layer that converts external objects or dictionaries into stable harness records.
- **Retry and Error Policy**: The rules for retrying, contextualizing, redacting, and surfacing Langfuse operation failures.
- **Query Workflow Owner Module**: A focused module that owns one Langfuse query workflow area, such as baselines, prompts, traces, scores, or Langfuse polling settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Existing non-live tests pass without requiring changes to project YAML, CLI commands, or user-facing workflow names after project callers migrate away from `LangfuseClient`.
- **SC-002**: Local quality reports show no active `langfuse_client.py` workflow hotspot, and internal source search shows no runtime workflow imports of `LangfuseClient`.
- **SC-003**: Maintainers can identify the owner module for dataset sync, trace retrieval, score handling, prompt/version lookup, evaluator setup, annotation queues, object mapping, and retry/error policy from module names and public boundaries alone.
- **SC-004**: In-memory tests cover the same public Langfuse data shapes used by live-compatible workflows for datasets, runs, traces, scores, prompts, evaluators, and review queues.
- **SC-005**: Changed Langfuse-related files introduce no new lint or type-checking diagnostic categories compared with the current local quality-report baseline.
- **SC-006**: The full live test suite passes with the configured live environment before acceptance.
- **SC-007**: Local Radon maintainability confirms query workflow ownership is split into focused modules and no mixed query module remains as an active implementation hotspot.
- **SC-008**: A source and test search confirms `LangfuseClient` is absent from active project workflow code, except for explicit deprecation tests or documentation if a compatibility shim remains.

## Assumptions

- The current quality-report baseline is the set of local reports under `reports/quality/`, including Ruff, Pyright, and Radon output.
- This work is a behavior-preserving architectural refactor, not a request to add new Langfuse features or change existing CLI behavior.
- The updated scope supersedes the earlier facade-preservation approach. Internal project callers will migrate to gateway-backed workflows even if that requires broader internal changes.
- External code that imports `LangfuseClient` is not guaranteed by this feature unless a separate compatibility requirement is added.
- Live tests depend on valid external credentials and service availability and are required for acceptance; non-live tests must remain deterministic and credential-free.
