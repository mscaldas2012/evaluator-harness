# Tasks: Surface Live Langfuse Failures

**Input**: Design documents from `specs/022-surface-langfuse-failures/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/langfuse-failure-surface.md`, `quickstart.md`

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover simulated Langfuse persistence failures, expected not-found results, lookup failures, warning aggregation, redaction, CLI output, exports, non-live compatibility, and live workflows where credentials are available.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks.
- **[Story]**: Maps to the user story from `spec.md`.
- Every task includes an exact file path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Locate existing silent fallback paths and prepare focused test surfaces.

- [x] T001 Review live fallback hotspots from `quickstart.md` and document target call sites in `specs/022-surface-langfuse-failures/quickstart.md`
- [x] T002 [P] Add shared warning fixture helpers for fake Langfuse failures in `tests/fixtures/fake_langfuse.py`
- [x] T003 [P] Add operation-outcome fixture helpers for unit tests in `tests/unit/test_langfuse_gateway_warnings.py`
- [x] T004 Confirm current CLI warning output surfaces in `src/evaluator_harness/cli.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared outcome and warning structures that every user story depends on.

**CRITICAL**: No user story work should begin until this phase is complete.

### Tests for Foundation (REQUIRED)

- [x] T005 [P] Add unit tests for `LangfuseOperationOutcome` validation and redacted details in `tests/unit/test_langfuse_gateway_warnings.py`
- [x] T006 [P] Add unit tests for `LangfuseWarning` aggregation and bounded examples in `tests/unit/test_langfuse_gateway_warnings.py`
- [x] T007 [P] Add unit tests for expected-not-found not becoming warning severity in `tests/unit/test_langfuse_gateway_warnings.py`

### Implementation for Foundation

- [x] T008 Define `LangfuseOperationOutcome`, `LangfuseWarning`, and status/severity literals in `src/evaluator_harness/langfuse_records.py`
- [x] T009 Implement warning aggregation helpers and representative example bounds in `src/evaluator_harness/langfuse_records.py`
- [x] T010 Add warning collection state and helper methods to `src/evaluator_harness/langfuse_default_gateway.py`
- [x] T011 Update `LangfuseGateway` protocol with warning collection and outcome-aware helper methods in `src/evaluator_harness/langfuse_gateways.py`
- [x] T012 Reuse existing secret redaction helpers for operation outcome details in `src/evaluator_harness/langfuse_retry.py`
- [x] T013 Run foundation tests with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_gateway_warnings.py`

**Checkpoint**: Foundation is complete when operation outcomes and warnings can be created, redacted, aggregated, and collected without touching story-specific Langfuse workflows.

---

## Phase 3: User Story 1 - See Partial Langfuse Persistence (Priority: P1) MVP

**Goal**: Users see partial-success warnings when model/evaluator work completes but live Langfuse persistence or confirmation is incomplete.

**Independent Test**: Simulate live dataset run item recording or score retrieval failure and verify the run/report surfaces warnings instead of fully successful status.

### Tests for User Story 1 (REQUIRED)

- [x] T014 [P] [US1] Add unit test for dataset run item recording failure producing a persistence warning in `tests/unit/test_langfuse_dataset_sync.py`
- [x] T015 [P] [US1] Add unit test for score retrieval failure producing a lookup warning instead of an empty successful score set in `tests/unit/test_langfuse_scores.py`
- [x] T016 [P] [US1] Add unit test for gateway warning aggregation across multiple affected run items in `tests/unit/test_langfuse_gateway_warnings.py`
- [x] T017 [P] [US1] Add integration test for candidate run partial Langfuse persistence warning in `tests/integration/test_langfuse_failure_surface.py`
- [x] T018 [P] [US1] Add CLI contract test for warning output on candidate run partial persistence in `tests/contract/test_cli_run_candidate.py`

### Implementation for User Story 1

- [x] T019 [US1] Return or collect persistence outcomes from dataset run item recording in `src/evaluator_harness/langfuse_dataset.py`
- [x] T020 [US1] Return or collect score retrieval outcomes when live score pages or trace score retrieval fail in `src/evaluator_harness/langfuse_scores.py`
- [x] T021 [US1] Merge partial persistence warnings into gateway state in `src/evaluator_harness/langfuse_default_gateway.py`
- [x] T022 [US1] Add Langfuse warning fields to `RunResult` and candidate/baseline result construction in `src/evaluator_harness/runner.py`
- [x] T023 [US1] Surface partial persistence warnings in CLI run output in `src/evaluator_harness/cli.py`
- [x] T024 [US1] Preserve partial persistence warnings in CSV/export summary metadata in `src/evaluator_harness/exports.py`
- [x] T025 [US1] Run US1 focused tests with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_dataset_sync.py tests/unit/test_langfuse_scores.py tests/unit/test_langfuse_gateway_warnings.py tests/integration/test_langfuse_failure_surface.py tests/contract/test_cli_run_candidate.py`

**Checkpoint**: User Story 1 is complete when recoverable live Langfuse persistence failures are visible in run summaries, CLI output, and exports without blocking completed model work.

---

## Phase 4: User Story 2 - Distinguish Expected Not-Found From Failures (Priority: P2)

**Goal**: Users can tell the difference between a successful lookup that found no matching object and a live lookup failure.

**Independent Test**: Simulate expected missing baseline/dataset item/trace and simulated service failure; verify not-found and failure are separately reported.

### Tests for User Story 2 (REQUIRED)

- [x] T026 [P] [US2] Add unit tests for baseline selector not-found versus live baseline lookup failure in `tests/unit/test_langfuse_baselines.py`
- [x] T027 [P] [US2] Add unit tests for dataset item expected missing versus dataset item lookup failure in `tests/unit/test_langfuse_dataset_sync.py`
- [x] T028 [P] [US2] Add unit tests for trace lookup empty result versus trace lookup failure in `tests/unit/test_langfuse_traces.py`
- [x] T029 [P] [US2] Add integration test for baseline lookup failure not silently falling back as success in `tests/integration/test_langfuse_failure_surface.py`
- [x] T030 [P] [US2] Add CLI contract test for baseline lookup failure message in `tests/contract/test_cli_run_baseline.py`

### Implementation for User Story 2

- [x] T031 [US2] Classify expected-not-found and lookup-failure outcomes in baseline lookup in `src/evaluator_harness/langfuse_baselines.py`
- [x] T032 [US2] Classify expected missing dataset items and lookup failures in `src/evaluator_harness/langfuse_dataset.py`
- [x] T033 [US2] Classify trace absence and trace lookup failures in `src/evaluator_harness/langfuse_traces.py`
- [x] T034 [US2] Preserve original live lookup failure when local fallback data is used in `src/evaluator_harness/langfuse_default_gateway.py`
- [x] T035 [US2] Surface baseline lookup failure and expected-not-found status through runner baseline selection in `src/evaluator_harness/runner.py`
- [x] T036 [US2] Run US2 focused tests with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_baselines.py tests/unit/test_langfuse_dataset_sync.py tests/unit/test_langfuse_traces.py tests/integration/test_langfuse_failure_surface.py tests/contract/test_cli_run_baseline.py`

**Checkpoint**: User Story 2 is complete when expected not-found remains non-error and live lookup failure is never returned as an unqualified empty result.

---

## Phase 5: User Story 3 - Preserve Workflow Completion While Reporting Risk (Priority: P3)

**Goal**: Recoverable Langfuse failures preserve local outputs with warnings, while required live linkage failures block misleading comparisons or reports.

**Independent Test**: Simulate recoverable late-stage persistence failure and required linkage failure; verify completed outputs are preserved only when the result remains truthful.

### Tests for User Story 3 (REQUIRED)

- [x] T037 [P] [US3] Add integration test proving candidate local outputs survive recoverable Langfuse warning in `tests/integration/test_run_candidate.py`
- [x] T038 [P] [US3] Add integration test proving required baseline linkage failure blocks misleading comparison in `tests/integration/test_run_baseline.py`
- [x] T039 [P] [US3] Add unit test proving warning details redact secrets and credentials in `tests/unit/test_langfuse_gateway_warnings.py`
- [x] T040 [P] [US3] Add contract test proving export warnings include Langfuse confidence warnings in `tests/contract/test_cli_export.py`
- [x] T041 [P] [US3] Add unit test proving exported warning metadata preserves Langfuse warning context in `tests/unit/test_exports.py`

### Implementation for User Story 3

- [x] T042 [US3] Add required-linkage failure rules for baseline, dataset identity, trace confirmation, and score confirmation in `src/evaluator_harness/runner.py`
- [x] T043 [US3] Preserve local outputs while attaching recoverable Langfuse warnings to run results in `src/evaluator_harness/runner.py`
- [x] T044 [US3] Include Langfuse confidence warnings in export result metadata in `src/evaluator_harness/exports.py`
- [x] T045 [US3] Redact all warning diagnostic details before CLI and report output in `src/evaluator_harness/langfuse_records.py`
- [x] T046 [US3] Render warning status and warning counts consistently in CLI output in `src/evaluator_harness/cli.py`
- [x] T047 [US3] Run US3 focused tests with `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_candidate.py tests/integration/test_run_baseline.py tests/unit/test_langfuse_gateway_warnings.py tests/contract/test_cli_export.py tests/unit/test_exports.py`

**Checkpoint**: User Story 3 is complete when recoverable failures keep local outputs with visible warnings and required-linkage failures stop misleading outputs.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify behavior across the project, refresh docs/graph context, and confirm quality gates.

- [x] T048 [P] Update `specs/022-surface-langfuse-failures/quickstart.md` with final verification results and any live-test caveats
- [x] T049 [P] Update `specs/Backlog.md` to mark TD-GRAPH-002 implementation status in `specs/Backlog.md`
- [x] T050 Run broad non-live suite with `uv run pytest --no-cov -p no:cacheprovider -m "not live"`
- [x] T051 Run live suite when credentials and service availability are present with `uv run pytest --no-cov -p no:cacheprovider -m live -vv`
- [x] T052 Run focused Ruff checks with `uv run ruff check src/evaluator_harness/langfuse_*.py src/evaluator_harness/runner.py src/evaluator_harness/exports.py src/evaluator_harness/cli.py tests/unit/test_langfuse_*.py tests/integration/test_langfuse_failure_surface.py --no-cache`
- [x] T053 Run focused Pyright checks with `uv run pyright src/evaluator_harness/langfuse_records.py src/evaluator_harness/langfuse_baselines.py src/evaluator_harness/langfuse_dataset.py src/evaluator_harness/langfuse_traces.py src/evaluator_harness/langfuse_scores.py src/evaluator_harness/runner.py`
- [x] T054 Run `graphify update .` after code changes
- [x] T055 Check final git status and ensure only intended source, test, spec, and graph files are staged in `.`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2 and delivers the MVP warning surface for partial persistence.
- **Phase 4 US2**: Depends on Phase 2; can proceed in parallel with US1 if shared gateway warning APIs are stable.
- **Phase 5 US3**: Depends on Phase 2 and benefits from US1/US2 warning semantics; final verification should run after US1 and US2.
- **Phase 6 Polish**: Depends on all selected user stories.

### User Story Dependencies

- **US1 See Partial Langfuse Persistence**: Start after foundational outcome/warning records exist. MVP scope.
- **US2 Distinguish Expected Not-Found From Failures**: Start after foundational outcome/warning records exist. Independent from US1 except for shared aggregation helpers.
- **US3 Preserve Workflow Completion While Reporting Risk**: Start after foundational outcome/warning records exist. Uses warning and blocking semantics established by US1/US2.

### Within Each User Story

- Write story tests first and confirm they fail for missing behavior.
- Add or update outcome classification in focused Langfuse owner modules.
- Propagate warnings through gateway and runner.
- Surface warnings through CLI/export only after core outcomes are stable.
- Run the focused story test command before moving to the next phase.

### Parallel Opportunities

- T002-T003 can run in parallel after T001.
- T005-T007 can run in parallel because they target distinct foundation behaviors in one test file with separate assertions.
- T014-T018 can run in parallel across unit, integration, and contract test files.
- T026-T030 can run in parallel across baseline, dataset, trace, integration, and CLI test files.
- T037-T041 can run in parallel across integration, unit, contract, and export test files.
- T048-T049 can run in parallel during polish after implementation behavior is known.

---

## Parallel Example: User Story 1

```text
Task: "T014 [P] [US1] Add unit test for dataset run item recording failure producing a persistence warning in tests/unit/test_langfuse_dataset_sync.py"
Task: "T015 [P] [US1] Add unit test for score retrieval failure producing a lookup warning instead of an empty successful score set in tests/unit/test_langfuse_scores.py"
Task: "T017 [P] [US1] Add integration test for candidate run partial Langfuse persistence warning in tests/integration/test_langfuse_failure_surface.py"
Task: "T018 [P] [US1] Add CLI contract test for warning output on candidate run partial persistence in tests/contract/test_cli_run_candidate.py"
```

---

## Parallel Example: User Story 2

```text
Task: "T026 [P] [US2] Add unit tests for baseline selector not-found versus live baseline lookup failure in tests/unit/test_langfuse_baselines.py"
Task: "T027 [P] [US2] Add unit tests for dataset item expected missing versus dataset item lookup failure in tests/unit/test_langfuse_dataset_sync.py"
Task: "T028 [P] [US2] Add unit tests for trace lookup empty result versus trace lookup failure in tests/unit/test_langfuse_traces.py"
Task: "T030 [P] [US2] Add CLI contract test for baseline lookup failure message in tests/contract/test_cli_run_baseline.py"
```

---

## Parallel Example: User Story 3

```text
Task: "T037 [P] [US3] Add integration test proving candidate local outputs survive recoverable Langfuse warning in tests/integration/test_run_candidate.py"
Task: "T038 [P] [US3] Add integration test proving required baseline linkage failure blocks misleading comparison in tests/integration/test_run_baseline.py"
Task: "T039 [P] [US3] Add unit test proving warning details redact secrets and credentials in tests/unit/test_langfuse_gateway_warnings.py"
Task: "T041 [P] [US3] Add unit test proving exported warning metadata preserves Langfuse warning context in tests/unit/test_exports.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational outcome and warning records.
3. Complete Phase 3 User Story 1.
4. Stop and validate with the US1 focused test command.
5. Demonstrate that recoverable live persistence failures show warnings instead of silent success.

### Incremental Delivery

1. Foundation creates typed outcome and warning aggregation.
2. US1 surfaces partial persistence warnings for completed work.
3. US2 separates expected not-found from live lookup failure.
4. US3 applies blocking versus recoverable rules to preserve truthful outputs.
5. Polish validates non-live, live, quality, docs, and graph context.

### Parallel Team Strategy

1. One developer owns `langfuse_records.py`, warning aggregation, and gateway collection.
2. One developer owns baseline/dataset expected-not-found versus failure semantics.
3. One developer owns trace/score lookup outcomes and pagination failure tests.
4. One developer owns runner/CLI/export propagation after the shared warning surface is stable.

## Notes

- `[P]` tasks touch different files or independent assertions and can run in parallel.
- `[US1]`, `[US2]`, and `[US3]` labels map directly to prioritized spec user stories.
- Do not turn expected not-found into a failure unless the lookup itself failed.
- Do not allow live lookup failures to collapse into unqualified `None`, `{}`, or `[]`.
- Do not introduce new durable local state or custom observability storage.
- Preserve local outputs when they remain truthful with warnings.

