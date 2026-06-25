# Tasks: Automatic Evaluator Calibration Support

**Input**: Design documents from `/specs/026-evaluator-calibration/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover success paths, validation failures, provider failures, Langfuse failures, metadata correctness, and CLI exit behavior where applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create calibration feature scaffolding in `src/evaluator_harness/calibration.py`, `tests/unit/test_calibration.py`, `tests/integration/test_calibration_capture.py`, and `tests/contract/test_cli_calibration.py`
- [X] T002 Add the calibration CLI contract document in `specs/026-evaluator-calibration/contracts/calibration-cli.md` and align the quickstart workflow in `specs/026-evaluator-calibration/quickstart.md`
- [X] T003 [P] Update the implementation plan references and shared docs in `specs/026-evaluator-calibration/plan.md`, `specs/026-evaluator-calibration/research.md`, and `specs/026-evaluator-calibration/data-model.md` to support calibration snapshot, summary, and drift entities

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Define calibration snapshot, record, summary, and drift result models in `src/evaluator_harness/calibration.py`
- [X] T005 [P] Extend the Langfuse gateway protocol in `src/evaluator_harness/langfuse_gateways.py` for calibration-specific trace, score, and annotation retrieval
- [X] T006 [P] Implement Langfuse score and annotation retrieval support in `src/evaluator_harness/langfuse_default_gateway.py` and `src/evaluator_harness/langfuse_scores.py`
- [X] T007 Add in-memory gateway support for calibration retrieval in `src/evaluator_harness/langfuse_in_memory.py` and calibration payload creation in `src/evaluator_harness/langfuse_annotation_ops.py`
- [ ] T008 Add calibration fixture data and run/snapshot helpers in `tests/fixtures/calibration/` for stable review selection, paired scores, and pending annotations
- [X] T009 Add shared calibration file-path helpers and report directory resolution in `src/evaluator_harness/run_exports.py` or `src/evaluator_harness/calibration.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Capture Calibration Evidence (Priority: P1) 🎯 MVP

**Goal**: Capture a run-scoped calibration snapshot with review metadata, automated evaluator outputs, and human annotation labels.

**Independent Test**: Verify that a completed run can produce calibration artifacts with one record per eligible review item, including pending-label handling when human review is incomplete.

### Tests for User Story 1 (REQUIRED)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Unit test calibration snapshot record assembly and pending-label handling in `tests/unit/test_calibration.py`
- [X] T011 [P] [US1] Contract test the `calibration-capture` CLI output and exit behavior in `tests/contract/test_cli_calibration.py`
- [X] T012 [P] [US1] Integration test capture of a completed run into calibration artifacts in `tests/integration/test_calibration_capture.py`

### Implementation for User Story 1

- [X] T013 [P] [US1] Implement calibration record assembly and snapshot writing in `src/evaluator_harness/calibration.py`
- [X] T014 [P] [US1] Add run-level calibration orchestration to `src/evaluator_harness/runner.py` so the runner can capture calibration snapshots from a completed run
- [X] T015 [US1] Add `calibration-capture` command handling to `src/evaluator_harness/cli.py` and result presentation to `src/evaluator_harness/cli_presenters.py`
- [X] T016 [US1] Preserve selection reason, selection bucket, evaluator version, prompt version, and score-source metadata in `src/evaluator_harness/calibration.py`
- [X] T017 [US1] Write calibration snapshot and row-level artifact outputs under `reports/<project>/calibration/` using `src/evaluator_harness/run_exports.py` or `src/evaluator_harness/calibration.py`
- [X] T018 [US1] Surface warnings for incomplete score or annotation retrieval in `src/evaluator_harness/calibration.py` and `src/evaluator_harness/cli_presenters.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Summarize Disagreement and Bias (Priority: P2)

**Goal**: Generate evaluator-level summaries showing paired coverage, disagreement rate, mean absolute score delta, and directional bias.

**Independent Test**: Verify that a calibration snapshot can produce deterministic per-evaluator summary metrics, including zero-coverage warnings when paired scores are unavailable.

### Tests for User Story 2 (REQUIRED)

- [X] T019 [P] [US2] Unit test summary metric calculations and zero-coverage warnings in `tests/unit/test_calibration.py`
- [X] T020 [P] [US2] Contract test the `calibration-summary` CLI output and exit behavior in `tests/contract/test_cli_calibration.py`
- [X] T021 [P] [US2] Integration test summary generation from a captured calibration snapshot in `tests/integration/test_calibration_capture.py`

### Implementation for User Story 2

- [X] T022 [P] [US2] Implement calibration summary aggregation in `src/evaluator_harness/calibration.py`
- [X] T023 [US2] Add `calibration-summary` command handling to `src/evaluator_harness/cli.py` and result presentation to `src/evaluator_harness/cli_presenters.py`
- [X] T024 [US2] Add deterministic pairing and summary warnings for missing human labels in `src/evaluator_harness/calibration.py`
- [X] T025 [US2] Persist summary artifacts beside calibration snapshots under `reports/<project>/calibration/` in `src/evaluator_harness/calibration.py`
- [X] T026 [US2] Ensure evaluator identity, score target, and run identity remain present in summary outputs in `src/evaluator_harness/calibration.py`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Backlog: User Story 3 - Track Calibration Drift Over Time (Priority: P3)

**Goal**: Compare calibration summaries across snapshots to detect drift in evaluator alignment over time.

**Independent Test**: Verify that two comparable calibration snapshots produce a drift artifact with metric deltas, while a single snapshot yields a clear insufficiency warning.

### Tests for User Story 3 (REQUIRED)

- [ ] T027 [P] [US3] Unit test drift delta calculations and insufficient-history warnings in `tests/unit/test_calibration.py`
- [ ] T028 [P] [US3] Contract test the `calibration-drift` CLI output and exit behavior in `tests/contract/test_cli_calibration.py`
- [ ] T029 [P] [US3] Integration test drift comparison across two calibration snapshots in `tests/integration/test_calibration_capture.py`

### Implementation for User Story 3

- [ ] T030 [P] [US3] Implement drift comparison logic in `src/evaluator_harness/calibration.py`
- [ ] T031 [US3] Add `calibration-drift` command handling to `src/evaluator_harness/cli.py` and result presentation to `src/evaluator_harness/cli_presenters.py`
- [ ] T032 [US3] Add snapshot compatibility checks for project version, evaluator dimension, and run identity in `src/evaluator_harness/calibration.py`
- [ ] T033 [US3] Persist drift artifacts alongside the corresponding calibration snapshots in `src/evaluator_harness/calibration.py`
- [ ] T034 [US3] Ensure drift output preserves baseline and current snapshot references in `src/evaluator_harness/calibration.py`

**Backlog note**: Drift comparison is intentionally deferred. Capture and
summary remain the active implemented workflow.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T035 [P] Update user-facing docs in `specs/026-evaluator-calibration/quickstart.md` and `README.md` if needed to reflect the calibration commands and artifact locations
- [X] T036 [P] Add or update regression coverage for calibration warnings, missing-label handling, and deterministic outputs in `tests/unit/test_calibration.py`
- [X] T037 Clean up calibration helper boundaries and remove duplicated serialization logic in `src/evaluator_harness/calibration.py` and `src/evaluator_harness/run_exports.py`
- [X] T038 Verify calibration commands preserve Langfuse trace links, evaluator versions, prompt versions, and score source metadata across `src/evaluator_harness/calibration.py` and `src/evaluator_harness/runner.py`
- [X] T039 Run `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_calibration.py tests/contract/test_cli_calibration.py tests/integration/test_calibration_capture.py -vv` and fix any regression in touched calibration paths
- [X] T040 Refresh code graph context with `graphify update .`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- Setup tasks marked [P] can run in parallel once the feature folder exists
- Foundational tasks marked [P] can run in parallel because they touch different calibration surfaces
- Once Foundational completes, US1/US2/US3 can proceed independently
- Within each story, the unit, contract, and integration tests marked [P] can be prepared in parallel before implementation
- Calibration snapshot, summary, and drift helpers can be split across different files if a future refactor separates them further

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test calibration snapshot record assembly and pending-label handling in tests/unit/test_calibration.py"
Task: "Contract test the calibration-capture CLI output and exit behavior in tests/contract/test_cli_calibration.py"
Task: "Integration test capture of a completed run into calibration artifacts in tests/integration/test_calibration_capture.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
