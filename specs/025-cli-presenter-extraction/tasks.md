# Tasks: CLI Presenter Extraction

**Input**: Design documents from `/specs/025-cli-presenter-extraction/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and preserve CLI output parity and exit behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature scaffolding and test file stubs

- [X] T001 Create presenter module scaffold in `src/evaluator_harness/cli_presenters.py`
- [X] T002 [P] Create presenter unit test scaffold in `tests/unit/test_cli_presenters.py`
- [X] T003 [P] Add/confirm test fixtures for CLI result objects in `tests/fixtures/` and `tests/unit/test_cli_presenters.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define command-to-presenter boundary and self-contained payload requirements before story work

**âš ï¸ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Map each CLI command output block to a presenter function in `specs/025-cli-presenter-extraction/contracts/cli-presentation-contract.md`
- [X] T005 Define uniform presenter helper conventions (ordering, warning rendering, optional fields) in `src/evaluator_harness/cli_presenters.py`
- [X] T006 [P] Add shared test helpers for Rich console capture in `tests/unit/test_cli_presenters.py`
- [X] T007 [P] Add baseline command-output parity fixture data for run/campaign/sync flows in `tests/unit/test_cli_presenters.py`
- [X] T008 Ensure command-derived display data is represented in result payloads (no extra presenter args) by updating result-shaping call sites in `src/evaluator_harness/cli.py` and related return objects in `src/evaluator_harness/comparison_reports.py`

**Checkpoint**: Presenter boundary and payload contract established; user story implementation can proceed

---

## Phase 3: User Story 1 - Thin Command Bodies (Priority: P1) ðŸŽ¯ MVP

**Goal**: Keep Typer command bodies thin by moving post-result rendering out of command functions

**Independent Test**: Inspect `src/evaluator_harness/cli.py` and verify post-result sections call presenters instead of inline `console.print(...)`.

### Tests for User Story 1 (REQUIRED)

- [X] T009 [P] [US1] Add unit test asserting `present_run_result` output parity in `tests/unit/test_cli_presenters.py`
- [X] T010 [P] [US1] Add unit test asserting `present_campaign_result` output parity in `tests/unit/test_cli_presenters.py`
- [X] T011 [P] [US1] Add unit test asserting `present_sync_prompts_result` and `present_sync_all_result` output parity in `tests/unit/test_cli_presenters.py`
- [X] T012 [P] [US1] Add/extend contract regression coverage for CLI project env scenarios in `tests/contract/test_cli_project_env_files.py`

### Implementation for User Story 1

- [X] T013 [US1] Implement `present_run_result` in `src/evaluator_harness/cli_presenters.py`
- [X] T014 [US1] Implement `present_campaign_result` in `src/evaluator_harness/cli_presenters.py`
- [X] T015 [US1] Implement `present_sync_prompts_result` and `present_sync_all_result` in `src/evaluator_harness/cli_presenters.py`
- [X] T016 [US1] Refactor `run` command to delegate post-result output to `present_run_result` in `src/evaluator_harness/cli.py`
- [X] T017 [US1] Refactor `campaign` command to delegate post-result output to `present_campaign_result` in `src/evaluator_harness/cli.py`
- [X] T018 [US1] Refactor `sync-prompts` and `sync-all` commands to delegate output to presenters in `src/evaluator_harness/cli.py`
- [X] T019 [US1] Preserve command-owned exit decisions for `run`/`campaign`/`sync-prompts`/`sync-all` after presenter calls in `src/evaluator_harness/cli.py`

**Checkpoint**: US1 delivers thin command bodies for the largest output-heavy commands and remains independently testable

---

## Phase 4: User Story 2 - Isolated Presentation Tests (Priority: P2)

**Goal**: Make output formatting testable directly via presenter functions without invoking Typer CLI runner

**Independent Test**: Run `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_cli_presenters.py -vv` and verify presenter tests assert output lines directly.

### Tests for User Story 2 (REQUIRED)

- [X] T020 [P] [US2] Add unit tests for validate/sync-dataset/sync-score-configs presenters in `tests/unit/test_cli_presenters.py`
- [X] T021 [P] [US2] Add unit tests for sync-annotation-queue/render-judge-prompts/export presenters in `tests/unit/test_cli_presenters.py`
- [X] T022 [P] [US2] Add unit tests for select-review/sync-judge-evaluators presenters in `tests/unit/test_cli_presenters.py`
- [X] T023 [P] [US2] Add unit tests for comparison-report/excel-report presenters including warning lines in `tests/unit/test_cli_presenters.py`

### Implementation for User Story 2

- [X] T024 [US2] Implement presenters for validate/sync-dataset/sync-score-configs in `src/evaluator_harness/cli_presenters.py`
- [X] T025 [US2] Implement presenters for sync-annotation-queue/render-judge-prompts/export in `src/evaluator_harness/cli_presenters.py`
- [X] T026 [US2] Implement presenters for select-review/sync-judge-evaluators in `src/evaluator_harness/cli_presenters.py`
- [X] T027 [US2] Implement comparison report presenters replacing helper output logic in `src/evaluator_harness/cli_presenters.py`
- [X] T028 [US2] Refactor corresponding commands to call new presenters in `src/evaluator_harness/cli.py`
- [X] T029 [US2] Keep interactive prompt flow and `_handle_command` orchestration unchanged while removing inline result prints in `src/evaluator_harness/cli.py`

**Checkpoint**: US2 delivers complete presenter-level testability for command output rendering

---

## Phase 5: User Story 3 - Consistent Presenter Location (Priority: P3)

**Goal**: Centralize all CLI result presentation logic in `cli_presenters.py` with consistent naming and ownership

**Independent Test**: Verify command functions in `src/evaluator_harness/cli.py` do not contain inline post-result presentation blocks and presenter functions live in `src/evaluator_harness/cli_presenters.py`.

### Tests for User Story 3 (REQUIRED)

- [X] T030 [P] [US3] Add static assertion test for zero inline post-result `console.print(...)` usage in command functions in `tests/unit/test_cli_presenters.py`
- [X] T031 [P] [US3] Add contract test for presenter naming/signature convention `(result, console)` in `tests/unit/test_cli_presenters.py`
- [X] T032 [P] [US3] Extend integration regression coverage for run baseline flow output stability in `tests/integration/test_run_baseline.py`

### Implementation for User Story 3

- [X] T033 [US3] Move `_print_comparison_report_outputs` and `_print_judge_setup_result` responsibilities into `src/evaluator_harness/cli_presenters.py`
- [X] T034 [US3] Remove obsolete presentation helpers and consolidate presenter imports in `src/evaluator_harness/cli.py`
- [X] T035 [US3] Normalize presenter function names to `present_<command>_result` and update all call sites in `src/evaluator_harness/cli.py` and `src/evaluator_harness/cli_presenters.py`
- [X] T036 [US3] Update feature quickstart verification steps for final presenter workflow in `specs/025-cli-presenter-extraction/quickstart.md`

**Checkpoint**: US3 delivers a consistent and discoverable presentation module boundary

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and cleanup across all stories

- [X] T037 [P] Run focused presenter and CLI regression tests from quickstart in `specs/025-cli-presenter-extraction/quickstart.md`
- [X] T038 [P] Run non-live suite validation command and capture summary in implementation notes at `specs/025-cli-presenter-extraction/quickstart.md`
- [X] T039 Run lint/type checks for touched files (`src/evaluator_harness/cli.py`, `src/evaluator_harness/cli_presenters.py`, `tests/unit/test_cli_presenters.py`) using `uv run ruff` and `uv run pyright`
- [X] T040 Run `graphify update .` and verify graph artifacts refresh under `graphify-out/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies, can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1, blocks all user stories
- **Phase 3 (US1)**: Depends on Phase 2
- **Phase 4 (US2)**: Depends on Phase 2, can proceed after US1 structure is in place
- **Phase 5 (US3)**: Depends on Phase 2 and benefits from US1/US2 completion
- **Phase 6 (Polish)**: Depends on completion of selected user stories

### User Story Dependencies

- **US1 (P1)**: MVP story; no dependency on other stories
- **US2 (P2)**: Depends on presenter boundary from foundational phase and presenter scaffolding from US1
- **US3 (P3)**: Depends on presenter implementations from US1/US2 to finalize consolidation

### Within Each User Story

- Write tests first and ensure they fail before implementation
- Implement presenters before command call-site refactors
- Preserve command exit behavior after presentation delegation
- Complete story checkpoints before advancing

### Parallel Opportunities

- Setup and foundational tasks marked [P] can run concurrently
- In each story, [P] test tasks can run concurrently
- Presenter implementations touching distinct command groups can run in parallel
- US2/US3 test hardening can proceed in parallel after core presenter migration stabilizes

---

## Parallel Example: User Story 1

```bash
# Parallel US1 tests
Task: "T009 [US1] Add unit test asserting present_run_result output parity in tests/unit/test_cli_presenters.py"
Task: "T010 [US1] Add unit test asserting present_campaign_result output parity in tests/unit/test_cli_presenters.py"
Task: "T011 [US1] Add unit test asserting present_sync_prompts_result and present_sync_all_result output parity in tests/unit/test_cli_presenters.py"

# Parallel US1 implementation on different command groups
Task: "T013 [US1] Implement present_run_result in src/evaluator_harness/cli_presenters.py"
Task: "T014 [US1] Implement present_campaign_result in src/evaluator_harness/cli_presenters.py"
```

## Parallel Example: User Story 2

```bash
# Parallel US2 test batches
Task: "T020 [US2] Add unit tests for validate/sync-dataset/sync-score-configs presenters in tests/unit/test_cli_presenters.py"
Task: "T021 [US2] Add unit tests for sync-annotation-queue/render-judge-prompts/export presenters in tests/unit/test_cli_presenters.py"
Task: "T023 [US2] Add unit tests for comparison-report/excel-report presenters including warning lines in tests/unit/test_cli_presenters.py"
```

## Parallel Example: User Story 3

```bash
# Parallel US3 validation tasks
Task: "T030 [US3] Add static assertion test for zero inline post-result console.print usage in tests/unit/test_cli_presenters.py"
Task: "T031 [US3] Add contract test for presenter naming/signature convention in tests/unit/test_cli_presenters.py"
Task: "T032 [US3] Extend integration regression coverage for run baseline flow output stability in tests/integration/test_run_baseline.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup)
2. Complete Phase 2 (Foundational)
3. Complete Phase 3 (US1)
4. Validate US1 independently before expanding scope

### Incremental Delivery

1. Deliver US1 thin command bodies for largest output-heavy commands
2. Deliver US2 presenter-level test coverage for remaining commands
3. Deliver US3 boundary consolidation and naming consistency
4. Run polish validation commands and graph refresh

### Parallel Team Strategy

1. Team completes setup and foundational tasks together
2. Developer A: US1 core run/campaign/sync presenter migration
3. Developer B: US2 presenter test expansion and command migrations
4. Developer C: US3 consolidation, signature checks, and integration hardening

---

## Notes

- [P] tasks = different files, no dependency on incomplete tasks
- [USx] labels map tasks to user stories for traceability
- Keep presenter signatures uniform: `(result, console)`
- Keep command-owned `typer.Exit(...)` decisions in `src/evaluator_harness/cli.py`
- Keep output behavior parity with existing command output lines

