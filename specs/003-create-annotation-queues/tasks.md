# Tasks: Create Annotation Queues

**Input**: Design documents from `/specs/003-create-annotation-queues/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation
tasks and cover success paths, validation failures, provider failures, Langfuse
failures, metadata correctness, and CLI exit behavior where applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Python CLI source lives under `src/evaluator_harness/`.
- CLI entry point is `run_experiment.py` and command wiring is in `src/evaluator_harness/cli.py`.
- Tests live under `tests/unit/`, `tests/contract/`, and `tests/integration/`.
- Generated queue reference state lives under `.evaluator-harness/queue-references/` and must be git-ignored.
- Use `uv run ...` for all Python commands and tests.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare docs, fixtures, and ignored local state paths used by all stories.

- [X] T001 Add `.evaluator-harness/queue-references/` generated state ignore rule to `.gitignore`
- [X] T002 [P] Add queue reference fixture data for managed and user-owned queues in `tests/fixtures/annotation_queues.py`
- [X] T003 [P] Add project config fixtures for managed, disabled, and user-owned queue policies in `tests/fixtures/projects/`
- [X] T004 [P] Update `.env.example` comments to mark `LANGFUSE_ANNOTATION_QUEUE_ID` as optional override in `.env.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared config, models, fake Langfuse support, and local reference storage required before any user story can work.

**CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational Behavior

- [X] T005 [P] Add review queue policy validation tests in `tests/unit/test_annotation_queue_policy.py`
- [X] T006 [P] Add queue reference serialization and secret-exclusion tests in `tests/unit/test_annotation_queue_store.py`
- [X] T007 [P] Add fake Langfuse annotation queue operation tests in `tests/unit/test_langfuse_annotation_queues.py`

### Implementation for Foundational Behavior

- [X] T008 Add `queue_ownership`, `queue_name`, and `fallback_to_env` fields to `HumanReviewPolicy` in `src/evaluator_harness/config.py`
- [X] T009 Create annotation queue data models and reference-store helpers in `src/evaluator_harness/annotation_queues.py`
- [X] T010 Extend `LangfuseClient` fake state and methods for queue create, list, get, and item routing in `src/evaluator_harness/langfuse_client.py`
- [X] T011 Add real Langfuse SDK wrappers for `annotation_queues.create_queue`, `list_queues`, `get_queue`, and `create_queue_item` in `src/evaluator_harness/langfuse_client.py`
- [X] T012 Wire queue policy validation into project validation in `src/evaluator_harness/config.py`
- [X] T013 Run foundational tests with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_annotation_queue_policy.py tests/unit/test_annotation_queue_store.py tests/unit/test_langfuse_annotation_queues.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Sync Project Review Queue (Priority: P1) MVP

**Goal**: Create or reuse a project-managed Langfuse Human Annotation Queue from project configuration and persist a reusable local queue reference.

**Independent Test**: Run queue sync for a project with human review enabled and no queue ID, then verify a queue reference exists and repeated sync reuses it without duplicates.

### Tests for User Story 1

- [X] T014 [P] [US1] Add contract tests for `sync-annotation-queue` created, reused, skipped, and failure statuses in `tests/contract/test_cli_sync_annotation_queue.py`
- [X] T015 [P] [US1] Add unit tests for managed queue name derivation and compatibility checks in `tests/unit/test_annotation_queue_sync.py`
- [X] T016 [P] [US1] Add fake integration test for idempotent managed queue sync in `tests/integration/test_sync_annotation_queue.py`

### Implementation for User Story 1

- [X] T017 [US1] Implement annotation queue sync orchestration in `src/evaluator_harness/annotation_queues.py`
- [X] T018 [US1] Add `sync_annotation_queue` runner method in `src/evaluator_harness/runner.py`
- [X] T019 [US1] Add `sync-annotation-queue` CLI command and output formatting in `src/evaluator_harness/cli.py`
- [X] T020 [US1] Update sample project to use managed queue policy in `configs/projects/rewrite_quality.yaml`
- [X] T021 [US1] Ensure score config sync results feed queue creation score config IDs in `src/evaluator_harness/runner.py`
- [X] T022 [US1] Run US1 tests with `uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_sync_annotation_queue.py tests/unit/test_annotation_queue_sync.py tests/integration/test_sync_annotation_queue.py`

**Checkpoint**: User Story 1 is fully functional and can be demoed as the MVP.

---

## Phase 4: User Story 2 - Route Review Items Without Manual Queue Environment (Priority: P2)

**Goal**: Make review selection resolve the project-managed queue automatically and route baseline and candidate review items to the same queue without `LANGFUSE_ANNOTATION_QUEUE_ID`.

**Independent Test**: Run baseline or fake candidate review selection without `LANGFUSE_ANNOTATION_QUEUE_ID` and verify selected items are routed to the resolved project queue.

### Tests for User Story 2

- [X] T023 [P] [US2] Add unit tests for queue resolution order in `tests/unit/test_annotation_queue_resolution.py`
- [X] T024 [P] [US2] Add fake integration test for `select-review` auto-syncing or resolving a managed queue in `tests/integration/test_select_review_managed_queue.py`
- [X] T025 [P] [US2] Add live smoke test update for review routing without `LANGFUSE_ANNOTATION_QUEUE_ID` in `tests/integration/live/test_live_review_routing_smoke.py`

### Implementation for User Story 2

- [X] T026 [US2] Implement queue resolution order in `src/evaluator_harness/annotation_queues.py`
- [X] T027 [US2] Update `select_review` flow to resolve or sync the queue before routing in `src/evaluator_harness/runner.py`
- [X] T028 [US2] Update annotation routing to call Langfuse queue item creation with trace object IDs in `src/evaluator_harness/langfuse_client.py`
- [X] T029 [US2] Update CLI review output to include queue ownership and queue ID in `src/evaluator_harness/cli.py`
- [X] T030 [US2] Run US2 tests with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_annotation_queue_resolution.py tests/integration/test_select_review_managed_queue.py tests/integration/live/test_live_review_routing_smoke.py`

**Checkpoint**: User Stories 1 and 2 work independently and together.

---

## Phase 5: User Story 3 - Keep Manual Queue Override Available (Priority: P3)

**Goal**: Preserve support for user-owned existing queues and optional environment overrides without letting the harness modify those queues.

**Independent Test**: Configure a user-owned queue reference and verify sync reports `user_owned`, routing uses that queue, and no managed queue is created.

### Tests for User Story 3

- [X] T031 [P] [US3] Add unit tests for user-owned queue validation and read-only behavior in `tests/unit/test_user_owned_annotation_queue.py`
- [X] T032 [P] [US3] Add contract tests for invalid user-owned queue CLI failures in `tests/contract/test_cli_user_owned_annotation_queue.py`
- [X] T033 [P] [US3] Add fake integration test for environment override routing in `tests/integration/test_annotation_queue_env_override.py`

### Implementation for User Story 3

- [X] T034 [US3] Implement user-owned queue validation and lookup in `src/evaluator_harness/annotation_queues.py`
- [X] T035 [US3] Implement optional `LANGFUSE_ANNOTATION_QUEUE_ID` override handling in `src/evaluator_harness/annotation_queues.py`
- [X] T036 [US3] Ensure user-owned queue sync never creates, updates, deletes, or rewrites queue references in `src/evaluator_harness/langfuse_client.py`
- [X] T037 [US3] Run US3 tests with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_user_owned_annotation_queue.py tests/contract/test_cli_user_owned_annotation_queue.py tests/integration/test_annotation_queue_env_override.py`

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, full verification, and cleanup across all stories.

- [X] T038 [P] Update annotation queue setup instructions in `docs/user-guide.md`
- [X] T039 [P] Update annotation queue workflow in `README.md`
- [X] T040 [P] Update live workflow docs in `specs/002-live-langfuse-mvp/quickstart.md`
- [X] T041 [P] Update generated feature quickstart if implementation command output differs in `specs/003-create-annotation-queues/quickstart.md`
- [X] T042 Run focused offline queue test suite with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_annotation_queue_policy.py tests/unit/test_annotation_queue_store.py tests/unit/test_langfuse_annotation_queues.py tests/unit/test_annotation_queue_sync.py tests/unit/test_annotation_queue_resolution.py tests/unit/test_user_owned_annotation_queue.py tests/contract/test_cli_sync_annotation_queue.py tests/contract/test_cli_user_owned_annotation_queue.py tests/integration/test_sync_annotation_queue.py tests/integration/test_select_review_managed_queue.py tests/integration/test_annotation_queue_env_override.py`
- [X] T043 Run full default suite with `uv run pytest -p no:cacheprovider`
- [X] T044 Run live queue smoke tests with `RUN_LIVE_TESTS=1 uv run pytest --no-cov -m live`
- [X] T045 Inspect generated `.evaluator-harness/queue-references/` files to confirm no secrets are stored

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational and integrates with US1 queue sync behavior.
- **User Story 3 (Phase 5)**: Depends on Foundational. Can be implemented after or alongside US2 once US1 queue concepts exist.
- **Polish (Phase 6)**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 Sync Project Review Queue**: Required for managed queue creation MVP.
- **US2 Route Review Items Without Manual Queue Environment**: Depends on US1 for managed queue sync and reference persistence.
- **US3 Keep Manual Queue Override Available**: Can proceed after Foundational and should preserve existing behavior while US1/US2 add managed behavior.

### Within Each User Story

- Tests MUST be written and fail before implementation.
- Config/data models before orchestration.
- Langfuse client wrapper before runner integration.
- Runner integration before CLI command/output.
- Story complete before moving to the next priority.

### Parallel Opportunities

- T002, T003, and T004 can run in parallel.
- T005, T006, and T007 can run in parallel.
- Tests within each user story can be written in parallel.
- Documentation tasks T038 through T041 can run in parallel.

---

## Parallel Example: User Story 1

```bash
Task: "Add contract tests for sync-annotation-queue in tests/contract/test_cli_sync_annotation_queue.py"
Task: "Add unit tests for managed queue sync in tests/unit/test_annotation_queue_sync.py"
Task: "Add fake integration test in tests/integration/test_sync_annotation_queue.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational queue policy, store, and Langfuse wrapper support.
3. Complete Phase 3 User Story 1.
4. Validate `sync-annotation-queue` independently with fakes and the sample project.

### Incremental Delivery

1. US1 creates/reuses project-managed queues and persists references.
2. US2 routes selected review items to the resolved queue without manual env config.
3. US3 preserves and verifies user-owned and environment override paths.
4. Polish updates docs and runs offline plus live smoke verification.

### Verification Commands

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_annotation_queue_policy.py tests/unit/test_annotation_queue_store.py tests/unit/test_langfuse_annotation_queues.py
uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_sync_annotation_queue.py tests/unit/test_annotation_queue_sync.py tests/integration/test_sync_annotation_queue.py
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_annotation_queue_resolution.py tests/integration/test_select_review_managed_queue.py
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_user_owned_annotation_queue.py tests/contract/test_cli_user_owned_annotation_queue.py tests/integration/test_annotation_queue_env_override.py
uv run pytest -p no:cacheprovider
```

Live verification:

```powershell
$env:RUN_LIVE_TESTS='1'
uv run pytest --no-cov -m live
```
