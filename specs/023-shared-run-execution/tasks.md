# Tasks: Shared Run Item Execution

**Input**: Design documents from `specs/023-shared-run-execution/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/run-item-execution.md`, `quickstart.md`

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover successful item evidence, provider failures, run-type-specific payloads, Langfuse warnings, and CLI behavior preservation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or has no dependency on incomplete tasks
- **[Story]**: User story label for story-specific tasks
- Every task includes exact file paths

## Phase 1: Setup

**Purpose**: Establish the current behavior baseline and identify the extraction targets.

- [X] T001 Run current baseline/candidate workflow tests with `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py -vv`
- [X] T002 Run current CLI contract tests with `uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_run_baseline.py tests/contract/test_cli_run_candidate.py -vv`
- [X] T003 [P] Inspect duplicated baseline and candidate item execution blocks in `src/evaluator_harness/runner.py`
- [X] T004 [P] Inspect existing baseline and candidate regression coverage in `tests/integration/test_run_baseline.py` and `tests/integration/test_run_candidate.py`
- [X] T005 [P] Inspect Langfuse warning regression coverage in `tests/unit/test_langfuse_gateway_warnings.py`

---

## Phase 2: Foundational

**Purpose**: Add shared test helpers and plan/result structures that block safe extraction.

**CRITICAL**: No user story implementation should begin until this phase is complete.

- [X] T006 [P] Add shared assertion helpers for per-item trace evidence in `tests/integration/test_run_baseline.py`
- [X] T007 [P] Add shared assertion helpers for per-item trace evidence in `tests/integration/test_run_candidate.py`
- [X] T008 Add failing regression coverage that compares baseline and candidate shared evidence fields in `tests/integration/test_run_candidate.py`
- [X] T009 Add failing regression coverage for shared failure trace evidence across run types in `tests/integration/test_run_baseline.py` and `tests/integration/test_run_candidate.py`
- [X] T010 Define internal `RunItemExecutionPlan` and `RunItemExecutionResult` records near `ExperimentRunner` in `src/evaluator_harness/runner.py`
- [X] T011 Define internal helper methods for run-type-specific evaluator payload construction in `src/evaluator_harness/runner.py`
- [X] T012 Run foundation tests with `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py -vv`

**Checkpoint**: Shared evidence expectations and internal extraction records are ready.

---

## Phase 3: User Story 1 - Consistent Per-Item Run Evidence (Priority: P1) MVP

**Goal**: Baseline and candidate items use one shared execution path for prompt rendering, session identity, request metadata, provider invocation, trace logging, dataset run item linkage, and failure evidence.

**Independent Test**: Run equivalent baseline and candidate items and confirm shared evidence fields, success handling, failure handling, and warning behavior are consistent for both run types.

### Tests for User Story 1

- [X] T013 [P] [US1] Add failing success-path shared evidence assertions in `tests/integration/test_run_baseline.py`
- [X] T014 [P] [US1] Add failing success-path shared evidence assertions in `tests/integration/test_run_candidate.py`
- [X] T015 [P] [US1] Add failing provider-error evidence assertions for baseline items in `tests/integration/test_run_baseline.py`
- [X] T016 [P] [US1] Add failing provider-error evidence assertions for candidate items in `tests/integration/test_run_candidate.py`
- [X] T017 [P] [US1] Add failing Langfuse warning preservation assertions for dataset run item recording failures in `tests/integration/test_run_candidate.py`

### Implementation for User Story 1

- [X] T018 [US1] Extract shared trace id, trace name, prompt rendering, session identity, and request metadata preparation into `_execute_run_item` support code in `src/evaluator_harness/runner.py`
- [X] T019 [US1] Move shared provider role validation and provider invocation into `_execute_run_item` in `src/evaluator_harness/runner.py`
- [X] T020 [US1] Move shared success trace logging and dataset run item recording into `_execute_run_item` in `src/evaluator_harness/runner.py`
- [X] T021 [US1] Move shared failure trace logging and failed dataset run item recording into `_execute_run_item` in `src/evaluator_harness/runner.py`
- [X] T022 [US1] Update baseline item loop to call `_execute_run_item` while preserving current run setup and finalization in `src/evaluator_harness/runner.py`
- [X] T023 [US1] Update candidate item loop to call `_execute_run_item` while preserving current run setup and finalization in `src/evaluator_harness/runner.py`
- [X] T024 [US1] Run US1 tests with `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py tests/unit/test_langfuse_gateway_warnings.py -vv`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Preserve Run-Type Specific Behavior (Priority: P2)

**Goal**: Baseline and candidate run-specific semantics remain correct after shared execution is introduced.

**Independent Test**: Run baseline and candidate workflows and verify run summaries, evaluator payloads, baseline references, prompt overrides, and comparison metadata match existing behavior.

### Tests for User Story 2

- [X] T025 [P] [US2] Add failing baseline evaluator payload preservation assertions in `tests/integration/test_run_baseline.py`
- [X] T026 [P] [US2] Add failing candidate evaluator payload preservation assertions in `tests/integration/test_run_candidate.py`
- [X] T027 [P] [US2] Add failing candidate prompt override preservation assertions in `tests/integration/test_run_candidate.py`
- [X] T028 [P] [US2] Add CLI behavior preservation assertions for baseline output in `tests/contract/test_cli_run_baseline.py`
- [X] T029 [P] [US2] Add CLI behavior preservation assertions for candidate output in `tests/contract/test_cli_run_candidate.py`

### Implementation for User Story 2

- [X] T030 [US2] Route baseline-specific evaluator payload construction through baseline plan fields in `src/evaluator_harness/runner.py`
- [X] T031 [US2] Route candidate-specific evaluator payload construction through candidate plan fields in `src/evaluator_harness/runner.py`
- [X] T032 [US2] Preserve candidate prompt override and prompt identity behavior in shared execution metadata in `src/evaluator_harness/runner.py`
- [X] T033 [US2] Preserve candidate baseline output lookup and baseline reference metadata in `src/evaluator_harness/runner.py`
- [X] T034 [US2] Run US2 tests with `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py tests/contract/test_cli_run_baseline.py tests/contract/test_cli_run_candidate.py -vv`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Safer Future Run Changes (Priority: P3)

**Goal**: Maintainers can identify and verify one shared per-item execution contract plus explicit baseline/candidate extensions.

**Independent Test**: Inspect tests and implementation notes to confirm shared requirements are asserted once for both run types and run-type-specific fields are targeted.

### Tests for User Story 3

- [X] T035 [P] [US3] Consolidate shared evidence assertions into reusable helpers in `tests/integration/test_run_baseline.py`
- [X] T036 [P] [US3] Reuse shared evidence assertions from candidate tests in `tests/integration/test_run_candidate.py`
- [X] T037 [P] [US3] Add regression assertions that baseline-only metadata does not leak into candidate-only assertions in `tests/integration/test_run_candidate.py`

### Implementation for User Story 3

- [X] T038 [US3] Add concise implementation comments for `RunItemExecutionPlan`, `RunItemExecutionResult`, and `_execute_run_item` in `src/evaluator_harness/runner.py`
- [X] T039 [US3] Remove obsolete duplicated baseline/candidate item execution branches from `src/evaluator_harness/runner.py`
- [X] T040 [US3] Run US3 tests with `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py -vv`

**Checkpoint**: Shared execution behavior is documented in code and covered by reusable assertions.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the complete refactor and update project traceability.

- [X] T041 Run broader non-live tests with `uv run pytest --no-cov -p no:cacheprovider -m "not live"`
- [X] T042 Run focused Ruff checks with `uv run ruff check src/evaluator_harness/runner.py tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py --no-cache`
- [X] T043 Run focused Pyright checks with `uv run pyright src/evaluator_harness/runner.py`
- [X] T044 [P] Update implementation notes in `specs/023-shared-run-execution/quickstart.md` if any explicit parity fix is introduced
- [X] T045 [P] Update TD-GRAPH-003 status in `specs/Backlog.md`
- [X] T046 Run `graphify update .`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 behavior-baseline inspection.
- **Phase 3 US1**: Depends on Phase 2 and delivers the MVP shared execution path.
- **Phase 4 US2**: Depends on US1 shared execution being in place.
- **Phase 5 US3**: Depends on US1 and US2 implementation shape.
- **Phase 6 Polish**: Depends on all selected user stories.

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2. No dependency on other stories.
- **US2 (P2)**: Depends on US1 because run-type-specific behavior must be routed through the shared execution result.
- **US3 (P3)**: Depends on US1 and US2 because it documents and consolidates the final shared contract.

### Within Each User Story

- Write tests first and confirm they fail before implementation.
- Add or update shared records before moving logic into the shared executor.
- Preserve existing run setup and finalization before changing item loops.
- Validate each story with its focused command before proceeding.

## Parallel Opportunities

- T003, T004, and T005 can run in parallel during setup.
- T006 and T007 can run in parallel once current behavior is understood.
- T013 through T017 can be written in parallel because they cover separate assertions.
- T025 through T029 can be written in parallel because they touch separate run-type and CLI behavior.
- T035 through T037 can be handled in parallel if coordinated around helper names.
- T044 and T045 can be done in parallel during polish.

## Parallel Example: User Story 1

```text
Task: "T013 [P] [US1] Add failing success-path shared evidence assertions in tests/integration/test_run_baseline.py"
Task: "T014 [P] [US1] Add failing success-path shared evidence assertions in tests/integration/test_run_candidate.py"
Task: "T015 [P] [US1] Add failing provider-error evidence assertions for baseline items in tests/integration/test_run_baseline.py"
Task: "T016 [P] [US1] Add failing provider-error evidence assertions for candidate items in tests/integration/test_run_candidate.py"
```

## Parallel Example: User Story 2

```text
Task: "T025 [P] [US2] Add failing baseline evaluator payload preservation assertions in tests/integration/test_run_baseline.py"
Task: "T026 [P] [US2] Add failing candidate evaluator payload preservation assertions in tests/integration/test_run_candidate.py"
Task: "T028 [P] [US2] Add CLI behavior preservation assertions for baseline output in tests/contract/test_cli_run_baseline.py"
Task: "T029 [P] [US2] Add CLI behavior preservation assertions for candidate output in tests/contract/test_cli_run_candidate.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup and Phase 2 foundational records/assertions.
2. Complete Phase 3 User Story 1.
3. Stop and validate shared success/failure evidence for baseline and candidate paths.

### Incremental Delivery

1. Deliver US1 to remove the core duplicate item execution mechanics.
2. Deliver US2 to prove baseline and candidate semantics remain distinct and correct.
3. Deliver US3 to make the shared behavior maintainable for future changes.
4. Complete polish verification and graph update.

### Validation Gate

Before considering the feature complete, run:

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py -vv
uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_run_baseline.py tests/contract/test_cli_run_candidate.py -vv
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_gateway_warnings.py -vv
uv run pytest --no-cov -p no:cacheprovider -m "not live"
uv run ruff check src/evaluator_harness/runner.py tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py --no-cache
uv run pyright src/evaluator_harness/runner.py
graphify update .
```

## Notes

- Keep `ExperimentRunner.run()` command inputs and user-visible outputs unchanged.
- Keep baseline setup/finalization and candidate baseline resolution outside the shared item executor.
- Treat any behavior normalization as an explicit parity fix with regression coverage.
- Preserve Langfuse warning aggregation from `022-surface-langfuse-failures`.
