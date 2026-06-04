# Tasks: Judge Evaluator Score Config Targeting

**Input**: Design documents from `/specs/014-evaluator-score-target/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/judge-evaluator-score-targeting.md, quickstart.md

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and verify the targeted tests fail for the missing score config target before making production changes.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or does not depend on incomplete tasks
- **[Story]**: User story label for story phases only
- Every task includes exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the working branch and preserve local generated artifacts.

- [x] T001 Confirm branch `014-evaluator-score-target` and inspect pending files with `git status -sb`
- [x] T002 Verify generated local binding files remain unstaged in `configs/langfuse/evaluator_bindings/dfe-general-public.yaml` and `configs/langfuse/prompt_bindings/dfe-general-public.yaml`
- [x] T003 Review existing evaluator rule create/update payload code in `src/evaluator_harness/langfuse_client.py`
- [x] T004 Review existing evaluator setup planning and safe update comparison code in `src/evaluator_harness/langfuse_evaluator_setup.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the common target field and normalization behavior required by every user story.

**Critical**: No user story implementation should begin until the shared field naming and expected data flow are understood.

- [x] T005 Identify the current score config ID flow from `ScoreConfigSyncResult` to `_payload_from_plan` in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [x] T006 Identify current remote evaluator rule normalization for `scoreConfigId` and `score_config_id` in `src/evaluator_harness/langfuse_client.py`
- [x] T007 [P] Document the expected local field name `score_config_id` and remote field name `scoreConfigId` in a short implementation note inside `specs/014-evaluator-score-target/quickstart.md`
- [x] T008 [P] Confirm existing CLI output already displays evaluator score target name and ID in `src/evaluator_harness/cli.py`

**Checkpoint**: Foundation ready. The expected score config target field and existing data flow are known.

---

## Phase 3: User Story 1 - Sync Judge Scores To Shared Score Configs (Priority: P1) MVP

**Goal**: Newly created custom and catalog judge evaluator rules target the resolved score config ID, so judge and human scores share the same score config dimension.

**Independent Test**: Sync score configs and judge evaluators with fake clients or mocked REST transport, then verify rule creation includes the expected score config ID.

### Tests for User Story 1 (REQUIRED)

- [x] T009 [P] [US1] Add a failing REST unit assertion that custom evaluator rule creation includes `scoreConfigId` in `tests/unit/test_langfuse_evaluator_rest.py`
- [x] T010 [P] [US1] Add a failing REST unit assertion that catalog evaluator rule creation includes `scoreConfigId` in `tests/unit/test_langfuse_evaluator_rest.py`
- [x] T011 [P] [US1] Add a failing planner unit test that blocks apply when a harness-managed evaluator has an empty resolved score config ID in `tests/unit/test_judge_setup_planner.py`
- [x] T012 [P] [US1] Add or update an integration test proving applied evaluator bindings retain the same score config ID sent to `create_evaluator` in `tests/integration/test_sync_judge_evaluators.py`

### Implementation for User Story 1

- [x] T013 [US1] Add `scoreConfigId` to evaluator rule create payloads from `payload["score_config_id"]` in `src/evaluator_harness/langfuse_client.py`
- [x] T014 [US1] Ensure `_payload_from_plan` always passes `score_config_id` and `score_config_name` for create operations in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [x] T015 [US1] Block create/apply plans with a clear remediation when `score_target.score_config_id` is empty in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [x] T016 [US1] Preserve existing variable mapping, filter, sampling, target, evaluator source, model, and connection fields while adding score config targeting in `src/evaluator_harness/langfuse_client.py`
- [x] T017 [US1] Run `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_evaluator_rest.py tests/unit/test_judge_setup_planner.py tests/integration/test_sync_judge_evaluators.py`

**Checkpoint**: User Story 1 is functional when created evaluator rules carry the intended score config ID for custom and catalog evaluators.

---

## Phase 4: User Story 2 - Catch Mismatched Existing Evaluator Rules (Priority: P2)

**Goal**: Existing harness-managed evaluator rules are reused only when their remote score config target matches the expected score config, and mismatches are reported or safely updated.

**Independent Test**: Present fake remote evaluator rules with matching and mismatched score config IDs, then verify audit/sync classifies them correctly.

### Tests for User Story 2 (REQUIRED)

- [x] T018 [P] [US2] Add a failing normalization test for remote `scoreConfigId` and `score_config_id` fields in `tests/unit/test_langfuse_evaluator_rest.py`
- [x] T019 [P] [US2] Add a failing safe update diff test that includes score config target mismatch in `tests/unit/test_judge_setup_planner.py`
- [x] T020 [P] [US2] Add a failing audit test that reports expected and remote score config IDs for a mismatched bound evaluator in `tests/unit/test_judge_setup_audit.py`
- [x] T021 [P] [US2] Add a failing integration test for updating a harness-managed evaluator rule with a mismatched score config target in `tests/integration/test_sync_judge_evaluators.py`

### Implementation for User Story 2

- [x] T022 [US2] Normalize remote evaluator rule score config fields into `score_config_id` in `_object_to_evaluator_dict` in `src/evaluator_harness/langfuse_client.py`
- [x] T023 [US2] Include score config target in expected-vs-remote safe update comparisons in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [x] T024 [US2] Add score config target to evaluator rule update payloads when `score_config_id` changes in `src/evaluator_harness/langfuse_client.py`
- [x] T025 [US2] Preserve missing-binding safeguards so unbound remote evaluator rules are not silently mutated in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [x] T026 [US2] Ensure mismatch failure/remediation includes expected and remote score config IDs in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [x] T027 [US2] Run `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_evaluator_rest.py tests/unit/test_judge_setup_planner.py tests/unit/test_judge_setup_audit.py tests/integration/test_sync_judge_evaluators.py`

**Checkpoint**: User Story 2 is functional when existing evaluator rules with mismatched score config targets are detected and either safely aligned or clearly reported.

---

## Phase 5: User Story 3 - Preview Score Targeting Before Applying (Priority: P3)

**Goal**: Dry-run and audit output make score config targeting visible enough that users can review alignment before applying Langfuse changes.

**Independent Test**: Run CLI dry-run paths with fake runner/client behavior and confirm target score config name and ID are shown or a missing-ID remediation is displayed.

### Tests for User Story 3 (REQUIRED)

- [x] T028 [P] [US3] Add a CLI contract test that dry-run judge evaluator output includes score config name and ID in `tests/contract/test_cli_sync_judge_evaluators.py`
- [x] T029 [P] [US3] Add a CLI contract test that missing score config ID produces a clear blocked/remediation message in `tests/contract/test_cli_sync_judge_evaluators.py`
- [x] T030 [P] [US3] Add or update a quickstart validation assertion for score-target preview behavior in `specs/014-evaluator-score-target/quickstart.md`

### Implementation for User Story 3

- [x] T031 [US3] Update judge evaluator CLI rendering to include expected score config name and ID when missing from current output in `src/evaluator_harness/cli.py`
- [x] T032 [US3] Update blocked plan reason/remediation text for missing score config IDs in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [x] T033 [US3] Update user documentation for score-targeted judge evaluator sync in `docs/user-guide.md`
- [x] T034 [US3] Run `uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_sync_judge_evaluators.py tests/unit/test_judge_setup_planner.py`

**Checkpoint**: User Story 3 is functional when users can see score config targets in dry-run/audit output without reading code.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the full score-targeting path and keep changes scoped.

- [x] T035 [P] Validate DFE general-public config with `uv run python run_experiment.py validate --project configs/projects/dfe-general-public.yaml`
- [x] T036 [P] Validate DFE healthcare-provider config with `uv run python run_experiment.py validate --project configs/projects/dfe-healthcare-provider.yaml`
- [x] T037 [P] Validate DFE public-health-sme config with `uv run python run_experiment.py validate --project configs/projects/dfe-public-health-sme.yaml`
- [x] T038 Run targeted regression suite from `specs/014-evaluator-score-target/quickstart.md`
- [x] T039 Run `git diff --check` to catch whitespace issues
- [x] T040 Inspect `git status -sb` and confirm generated binding files in `configs/langfuse/` remain intentionally untracked unless explicitly requested
- [x] T041 Update `specs/014-evaluator-score-target/tasks.md` checkboxes as tasks are completed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1.
- **Phase 3 User Story 1**: Depends on Phase 2 and is the MVP.
- **Phase 4 User Story 2**: Depends on Phase 2. It can start after the shared expected/remote comparison shape is clear, but implementation is simpler after US1 establishes create payload targeting.
- **Phase 5 User Story 3**: Depends on Phase 2. It can proceed in parallel with US2 after plan/remediation shapes are known.
- **Phase 6 Polish**: Depends on completed desired user stories.

### User Story Dependencies

- **US1 (P1)**: Required for MVP. No dependency on US2 or US3.
- **US2 (P2)**: Depends conceptually on the same score target model as US1, but can be tested independently with fake remote rules.
- **US3 (P3)**: Can be implemented after score target fields exist in setup plans.

### Parallel Opportunities

- T007 and T008 can run in parallel during foundation.
- T009, T010, T011, and T012 can be written in parallel.
- T018, T019, T020, and T021 can be written in parallel.
- T028, T029, and T030 can be written in parallel.
- T035, T036, and T037 can be run in parallel.

## Parallel Example: User Story 1

```text
Task: "Add custom evaluator create payload test in tests/unit/test_langfuse_evaluator_rest.py"
Task: "Add catalog evaluator create payload test in tests/unit/test_langfuse_evaluator_rest.py"
Task: "Add missing score config ID planner block test in tests/unit/test_judge_setup_planner.py"
Task: "Add applied binding/create payload integration test in tests/integration/test_sync_judge_evaluators.py"
```

## Parallel Example: User Story 2

```text
Task: "Add remote scoreConfigId normalization test in tests/unit/test_langfuse_evaluator_rest.py"
Task: "Add safe update diff test in tests/unit/test_judge_setup_planner.py"
Task: "Add audit mismatch test in tests/unit/test_judge_setup_audit.py"
Task: "Add sync update integration test in tests/integration/test_sync_judge_evaluators.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Write US1 tests and verify they fail for missing score config targeting.
3. Implement score config ID in create payloads and missing-ID blocking.
4. Run US1 targeted tests.
5. Stop and validate that new evaluator rules target score configs.

### Incremental Delivery

1. Deliver US1 so new evaluator rules are correct.
2. Deliver US2 so existing evaluator rules can be audited and aligned.
3. Deliver US3 so users can preview score targeting confidently.
4. Run DFE validation and targeted regression suite.

### Notes

- Keep changes scoped to evaluator setup, Langfuse evaluator REST payloads, CLI rendering if needed, docs, and tests.
- Do not delete or recreate remote evaluator rules as a repair strategy.
- Do not stage generated Langfuse binding files unless the user explicitly asks to track shared live bindings.
