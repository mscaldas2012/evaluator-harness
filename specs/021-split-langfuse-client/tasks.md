# Tasks: Split Langfuse Client

**Input**: Design documents from `specs/021-split-langfuse-client/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/langfuse-boundary.md`, `quickstart.md`

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover facade compatibility, mapper normalization, fallback behavior, retry/redaction behavior, in-memory/live-compatible shape parity, non-live workflows, live workflows, and quality-report acceptance.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks.
- **[Story]**: Maps to the user story from `spec.md`.
- Every task includes an exact file path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture the baseline and create the files that later phases will fill.

- [x] T001 Record current `langfuse_client.py` baseline metrics in `specs/021-split-langfuse-client/quickstart.md`
- [x] T002 [P] Create empty module scaffold for typed Langfuse records in `src/evaluator_harness/langfuse_records.py`
- [x] T003 [P] Create empty module scaffold for gateway protocols and factory in `src/evaluator_harness/langfuse_gateways.py`
- [x] T004 [P] Create empty module scaffold for object normalization in `src/evaluator_harness/langfuse_mappers.py`
- [x] T005 [P] Create empty module scaffold for retry and redaction policy in `src/evaluator_harness/langfuse_retry.py`
- [x] T006 [P] Create empty module scaffold for deterministic in-memory behavior in `src/evaluator_harness/langfuse_in_memory.py`
- [x] T007 [P] Create empty module scaffold for SDK-backed live behavior in `src/evaluator_harness/langfuse_sdk.py`
- [x] T008 [P] Create empty module scaffold for REST-compatible fallback behavior in `src/evaluator_harness/langfuse_rest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define shared contracts and low-risk extraction targets that all user stories need.

**CRITICAL**: No user story work should begin until this phase is complete.

- [x] T009 [P] Define `DatasetRecord`, `DatasetItemRecord`, `RunRecord`, `TraceRecord`, `ScoreRecord`, `ScoreConfigRecord`, `PromptRecord`, `EvaluatorRecord`, and `AnnotationQueueRecord` in `src/evaluator_harness/langfuse_records.py`
- [x] T010 [P] Define `OperationFailure` and safe metadata helper types in `src/evaluator_harness/langfuse_records.py`
- [x] T011 Define `LangfuseGateway` protocol covering dataset, run, score, prompt, trace, evaluator, annotation queue, baseline, and metadata operations in `src/evaluator_harness/langfuse_gateways.py`
- [x] T012 Define gateway construction inputs and selection helpers that preserve current `LangfuseClient` caller behavior in `src/evaluator_harness/langfuse_gateways.py`
- [x] T013 [P] Add mapper unit tests for SDK object, dictionary, partial object, and missing optional field normalization in `tests/unit/test_langfuse_mappers.py`
- [x] T014 [P] Add retry/redaction unit tests for bounded retries, retry-after parsing, operation names, and secret redaction in `tests/unit/test_langfuse_retry.py`
- [x] T015 Implement typed mapper functions for score configs, scores, prompts, evaluators, queues, traces, run metadata, and REST evaluator payloads in `src/evaluator_harness/langfuse_mappers.py`
- [x] T016 Implement bounded retry, retry-after parsing, retryability checks, operation wrapping, and redaction helpers in `src/evaluator_harness/langfuse_retry.py`
- [x] T017 Move or wrap existing helper logic for `_object_to_evaluator_dict`, `_object_to_score_dict`, `_object_to_score_config_dict`, `_object_to_queue_dict`, `_object_to_prompt_dict`, `_rest_evaluation_rule_update_payload`, `_rest_filters_to_internal`, and related mapper helpers from `src/evaluator_harness/langfuse_client.py` into `src/evaluator_harness/langfuse_mappers.py`
- [x] T018 Update imports and compatibility wrappers in `src/evaluator_harness/langfuse_client.py` so existing tests can still import any helper that remains public or test-referenced
- [x] T019 Run mapper and retry unit tests with `uv run pytest -p no:cacheprovider tests/unit/test_langfuse_mappers.py tests/unit/test_langfuse_retry.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Preserve Langfuse Workflows Behind Clear Boundaries (Priority: P1) MVP

**Goal**: Preserve current CLI, YAML, and caller behavior while moving Langfuse responsibilities behind the existing `LangfuseClient` facade.

**Independent Test**: Existing non-live tests, facade integration tests, and the full live suite pass without changing caller usage.

### Tests for User Story 1 (REQUIRED)

- [x] T020 [P] [US1] Add facade compatibility tests for public `LangfuseClient` constructor and workflow method signatures in `tests/integration/test_langfuse_client_facade.py`
- [x] T021 [P] [US1] Add facade delegation tests for dataset sync, run item recording, score config sync, prompt lookup, trace retrieval, evaluator operations, annotation queues, and baseline lookup in `tests/integration/test_langfuse_client_facade.py`
- [x] T022 [P] [US1] Add fallback capability-gap tests for live evaluator, queue, score, prompt, and trace operations in `tests/unit/test_langfuse_gateways.py`
- [x] T023 [P] [US1] Add non-live regression tests for current dataset sync and score config workflows in `tests/unit/test_langfuse_dataset_sync.py` and `tests/unit/test_langfuse_score_config_sync.py`

### Implementation for User Story 1

- [x] T024 [US1] Implement `LangfuseClient` gateway construction and dependency selection while preserving the public facade in `src/evaluator_harness/langfuse_client.py`
- [x] T025 [US1] Implement SDK-backed dataset, run item, trace, score, prompt, score config, evaluator, annotation queue, and baseline operations in `src/evaluator_harness/langfuse_sdk.py`
- [x] T026 [US1] Implement REST-compatible fallback evaluator, queue, score, prompt, trace, and payload operations in `src/evaluator_harness/langfuse_rest.py`
- [x] T027 [US1] Move live score config listing, creation, alignment, and compatibility checks behind gateway methods in `src/evaluator_harness/langfuse_sdk.py`
- [x] T028 [US1] Move live prompt version listing and prompt creation behavior behind gateway methods in `src/evaluator_harness/langfuse_sdk.py`
- [x] T029 [US1] Move live trace retrieval, dataset run metadata, dataset run item trace lookup, and score retrieval behind gateway methods in `src/evaluator_harness/langfuse_sdk.py`
- [x] T030 [US1] Move live evaluator CRUD and REST request behavior behind SDK and REST gateway methods in `src/evaluator_harness/langfuse_sdk.py` and `src/evaluator_harness/langfuse_rest.py`
- [x] T031 [US1] Move live annotation queue list, get, create, object ID lookup, item routing, and payload behavior behind gateway methods in `src/evaluator_harness/langfuse_sdk.py` and `src/evaluator_harness/langfuse_rest.py`
- [x] T032 [US1] Refactor `LangfuseClient.sync_dataset` to delegate dataset workflow steps and remove the D-ranked facade complexity block in `src/evaluator_harness/langfuse_client.py`
- [x] T033 [US1] Refactor `LangfuseClient.traces_for_run`, `LangfuseClient.lookup_baseline`, and `LangfuseClient._lookup_live_baseline` to delegate live lookup behavior in `src/evaluator_harness/langfuse_client.py`
- [x] T034 [US1] Preserve current integration points in `src/evaluator_harness/runner.py`, `src/evaluator_harness/annotation_queues.py`, `src/evaluator_harness/langfuse_evaluator_setup.py`, `scripts/reset_annotation_queue_for_project.py`, `scripts/cleanup_duplicate_score_configs.py`, and `scripts/cleanup_invalid_annotation_queue_items.py`
- [x] T035 [US1] Run non-live compatibility tests with `uv run pytest -p no:cacheprovider tests/integration/test_langfuse_client_facade.py tests/unit/test_langfuse_dataset_sync.py tests/unit/test_langfuse_score_config_sync.py tests/unit/test_langfuse_evaluator_rest.py`

**Checkpoint**: User Story 1 is complete when current callers still use `LangfuseClient`, non-live compatibility tests pass, and facade methods delegate to focused modules.

---

## Phase 4: User Story 2 - Improve Maintainability Hotspots (Priority: P2)

**Goal**: Make the quality-report improvement measurable: `langfuse_client.py` maintainability improves from `C (0.00)`, no D-ranked complexity blocks remain in the public facade, and changed files introduce no new lint/type diagnostic categories.

**Independent Test**: Regenerate local quality reports and compare `langfuse_client.py` against the documented baseline.

### Tests for User Story 2 (REQUIRED)

- [x] T036 [P] [US2] Add a quality-report regression test or script assertion for `langfuse_client.py` baseline comparison in `tests/unit/test_quality_report_langfuse_baseline.py`
- [x] T037 [P] [US2] Add unit tests for mapper edge cases that currently drive C/D Radon hotspots in `tests/unit/test_langfuse_mappers.py`
- [x] T038 [P] [US2] Add unit tests for nullable ID, optional callable, nullable dictionary, and unknown span context-manager handling in `tests/unit/test_langfuse_gateways.py`

### Implementation for User Story 2

- [x] T039 [US2] Remove remaining high-complexity object conversion logic from `src/evaluator_harness/langfuse_client.py`
- [x] T040 [US2] Remove remaining high-complexity REST payload and filter conversion logic from `src/evaluator_harness/langfuse_client.py`
- [x] T041 [US2] Replace nullable ID flows with typed record validation before facade return values in `src/evaluator_harness/langfuse_records.py` and `src/evaluator_harness/langfuse_mappers.py`
- [x] T042 [US2] Replace optional callable and object-typed span handling with typed protocol guards in `src/evaluator_harness/langfuse_sdk.py`
- [x] T043 [US2] Reduce `langfuse_client.py` to facade orchestration, compatibility result shaping, and gateway delegation in `src/evaluator_harness/langfuse_client.py`
- [x] T044 [US2] Run `uv run python scripts/quality_report.py` and inspect `reports/quality/radon-maintainability.txt`, `reports/quality/radon-complexity.txt`, `reports/quality/ruff-check.txt`, and `reports/quality/pyright.txt`
- [x] T045 [US2] Update `specs/021-split-langfuse-client/quickstart.md` with post-refactor line count, Radon, Ruff, and Pyright results
- [x] T046 [US2] Confirm no D-ranked complexity blocks remain in the public facade by documenting the Radon excerpt in `specs/021-split-langfuse-client/quickstart.md`

**Checkpoint**: User Story 2 is complete when reports show `langfuse_client.py` maintainability improved from `C (0.00)`, no facade D-ranked blocks remain, and no new Ruff or Pyright diagnostic categories appear in changed Langfuse files.

---

## Phase 5: User Story 3 - Keep Tests and Fakes Representative (Priority: P3)

**Goal**: Ensure the deterministic in-memory behavior exercises the same public contracts and record shapes as live-compatible behavior.

**Independent Test**: Focused in-memory tests pass without live credentials and shape-parity tests confirm public records match live-compatible expectations.

### Tests for User Story 3 (REQUIRED)

- [x] T047 [P] [US3] Add deterministic in-memory gateway tests for datasets, runs, traces, scores, prompts, evaluators, and annotation queues in `tests/unit/test_langfuse_in_memory.py`
- [x] T048 [P] [US3] Add shape parity tests comparing in-memory and live-compatible mapper outputs in `tests/unit/test_langfuse_gateways.py`
- [x] T049 [P] [US3] Add dry-run facade tests proving no live credentials are required in `tests/integration/test_langfuse_client_facade.py`

### Implementation for User Story 3

- [x] T050 [US3] Implement deterministic dataset, run, trace, score, prompt, evaluator, and annotation queue state in `src/evaluator_harness/langfuse_in_memory.py`
- [x] T051 [US3] Wire dry-run and test-mode facade construction to the in-memory gateway in `src/evaluator_harness/langfuse_gateways.py` and `src/evaluator_harness/langfuse_client.py`
- [x] T052 [US3] Ensure in-memory gateway returns the same typed records and facade compatibility shapes as live-compatible paths in `src/evaluator_harness/langfuse_in_memory.py`
- [x] T053 [US3] Preserve existing tests that instantiate `LangfuseClient` without live credentials by updating only their setup code where necessary in `tests/unit/test_langfuse_dataset_sync.py`, `tests/unit/test_langfuse_trace_ids.py`, and `tests/unit/test_langfuse_score_config_sync.py`
- [x] T054 [US3] Run in-memory and dry-run tests with `uv run pytest -p no:cacheprovider tests/unit/test_langfuse_in_memory.py tests/unit/test_langfuse_gateways.py tests/integration/test_langfuse_client_facade.py`

**Checkpoint**: User Story 3 is complete when deterministic tests run credential-free and in-memory outputs match the public shapes used by live-compatible workflows.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify full project behavior, update graph context, and prepare the branch.

- [x] T055 Run the full non-live test suite with `uv run pytest -p no:cacheprovider`
- [x] T056 Run the full live test suite with `uv run pytest --no-cov -p no:cacheprovider -m live -vv`
- [x] T057 Run `uv run python scripts/quality_report.py` and verify the reports in `reports/quality/`
- [x] T058 Run `graphify update .` to refresh `graphify-out/` after code changes
- [x] T059 [P] Review `src/evaluator_harness/langfuse_client.py` for compatibility-only responsibilities and remove dead facade helpers no longer referenced
- [x] T060 [P] Review new modules `src/evaluator_harness/langfuse_gateways.py`, `src/evaluator_harness/langfuse_in_memory.py`, `src/evaluator_harness/langfuse_sdk.py`, `src/evaluator_harness/langfuse_rest.py`, `src/evaluator_harness/langfuse_mappers.py`, `src/evaluator_harness/langfuse_retry.py`, and `src/evaluator_harness/langfuse_records.py` for names that match the plan and contract
- [x] T061 Update `specs/021-split-langfuse-client/quickstart.md` with final verification commands and pass/fail notes
- [x] T062 Check final git status and ensure only intended source, test, spec, and graph files are staged for commit

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2; delivers the MVP compatibility facade.
- **Phase 4 US2**: Depends on Phase 3 because quality acceptance must measure the refactored facade.
- **Phase 5 US3**: Depends on Phase 2 and can proceed alongside parts of US1 after gateway protocols exist, but final parity requires US1 facade behavior.
- **Phase 6 Polish**: Depends on all user stories selected for implementation.

### User Story Dependencies

- **US1 Preserve Langfuse Workflows**: Start after Phase 2. This is the MVP.
- **US2 Improve Maintainability Hotspots**: Start after US1 delegation is in place.
- **US3 Keep Tests and Fakes Representative**: Start after Phase 2; finalize after US1 facade delegation is stable.

### Within Each User Story

- Write story tests first and confirm they fail for the missing boundary behavior.
- Implement records and mappers before gateway behavior.
- Implement gateway behavior before facade delegation.
- Run focused story tests before broad test suites.
- Regenerate quality reports only after the facade refactor is in place.

### Parallel Opportunities

- T002-T008 can run in parallel after T001.
- T009, T010, T013, and T014 can run in parallel once module scaffolds exist.
- T020-T023 can run in parallel because they are test tasks in separate focused areas.
- T036-T038 can run in parallel because they target different quality-risk tests.
- T047-T049 can run in parallel because they cover distinct in-memory/parity surfaces.
- T059 and T060 can run in parallel during final review.

---

## Parallel Example: User Story 1

```text
Task: "T020 [P] [US1] Add facade compatibility tests for public LangfuseClient constructor and workflow method signatures in tests/integration/test_langfuse_client_facade.py"
Task: "T022 [P] [US1] Add fallback capability-gap tests for live evaluator, queue, score, prompt, and trace operations in tests/unit/test_langfuse_gateways.py"
Task: "T023 [P] [US1] Add non-live regression tests for current dataset sync and score config workflows in tests/unit/test_langfuse_dataset_sync.py and tests/unit/test_langfuse_score_config_sync.py"
```

---

## Parallel Example: User Story 2

```text
Task: "T036 [P] [US2] Add a quality-report regression test or script assertion for langfuse_client.py baseline comparison in tests/unit/test_quality_report_langfuse_baseline.py"
Task: "T037 [P] [US2] Add unit tests for mapper edge cases that currently drive C/D Radon hotspots in tests/unit/test_langfuse_mappers.py"
Task: "T038 [P] [US2] Add unit tests for nullable ID, optional callable, nullable dictionary, and unknown span context-manager handling in tests/unit/test_langfuse_gateways.py"
```

---

## Parallel Example: User Story 3

```text
Task: "T047 [P] [US3] Add deterministic in-memory gateway tests for datasets, runs, traces, scores, prompts, evaluators, and annotation queues in tests/unit/test_langfuse_in_memory.py"
Task: "T048 [P] [US3] Add shape parity tests comparing in-memory and live-compatible mapper outputs in tests/unit/test_langfuse_gateways.py"
Task: "T049 [P] [US3] Add dry-run facade tests proving no live credentials are required in tests/integration/test_langfuse_client_facade.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational records, protocols, mappers, and retry policy.
3. Complete Phase 3 User Story 1.
4. Stop and validate facade compatibility with focused non-live tests.
5. Run the full live suite before accepting the refactor as complete.

### Incremental Delivery

1. Setup and foundation create typed records, gateway protocols, mappers, and retry helpers.
2. US1 preserves behavior through facade delegation.
3. US2 measures and improves quality reports against the documented baseline.
4. US3 makes in-memory behavior representative and credential-free.
5. Polish validates non-live tests, live tests, quality reports, and graph updates.

### Parallel Team Strategy

1. One developer owns records/protocols and facade construction.
2. One developer owns mapper extraction and tests.
3. One developer owns retry/redaction and REST fallback tests.
4. After Phase 2, SDK gateway, in-memory gateway, and quality-report checks can proceed with coordination on the gateway protocol.

## Notes

- `[P]` tasks touch different files or independent test surfaces.
- `[US1]`, `[US2]`, and `[US3]` labels map directly to the spec user stories.
- Keep `LangfuseClient` as the public compatibility facade throughout.
- Do not introduce new services, databases, background workers, or a dependency injection framework.
- Acceptance requires the full live test suite, so live credentials and service availability are part of final validation.
