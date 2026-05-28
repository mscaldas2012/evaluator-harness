# Tasks: Langfuse Judge Setup

**Input**: Design documents from `/specs/008-langfuse-judge-setup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover success paths, validation failures, Langfuse failures, metadata correctness, local binding safety, and CLI exit behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare fixtures, example configs, and shared test scaffolding for judge evaluator setup.

- [X] T001 [P] Add judge setup defaults and custom evaluator setup fields to `tests/fixtures/projects/valid_rewrite_quality.yaml`
- [X] T002 [P] Add Langfuse catalog evaluator fixture project in `tests/fixtures/projects/valid_catalog_judge_setup.yaml`
- [X] T003 [P] Add invalid judge setup fixture projects for missing judge connection, unsafe backfill, missing binding, and user-owned mutation in `tests/fixtures/projects/`
- [X] T004 [P] Add sample evaluator binding file fixture in `tests/fixtures/langfuse/evaluator_bindings/rewrite-quality.yaml`
- [X] T005 [P] Add report and binding output ignore patterns for generated evaluator setup artifacts in `.gitignore`
- [X] T006 [P] Update `docs/langfuse-automation-backlog.md` status notes for BL-008 direct setup scope after task generation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core config, models, binding persistence, and Langfuse adapter surfaces required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundation

- [X] T007 [P] Add unit tests for judge setup config defaults, source types, judge model/connection resolution, sampling defaults, and backfill defaults in `tests/unit/test_judge_setup_config.py`
- [X] T008 [P] Add unit tests for managed evaluator display-name generation and slug validation in `tests/unit/test_judge_evaluator_naming.py`
- [X] T009 [P] Add unit tests for evaluator binding load/save, non-secret validation, key fields, and repo-local path validation in `tests/unit/test_evaluator_bindings.py`
- [X] T010 [P] Add unit tests for setup plan statuses and safe-update field detection in `tests/unit/test_judge_setup_planner.py`
- [X] T011 [P] Add fake Langfuse evaluator setup client fixtures in `tests/fixtures/langfuse_evaluators.py`

### Implementation for Foundation

- [X] T012 Add `JudgeSetupDefaults`, `EvaluatorSourceType`, `HistoricalBackfillPolicy`, and judge setup fields to `src/evaluator_harness/config.py`
- [X] T013 Extend `EvaluatorDefinition` validation for catalog/custom/user-owned evaluator setup, source-type requirements, judge model/connection overrides, sampling, backfill, and managed display-name overrides in `src/evaluator_harness/config.py`
- [X] T014 Add managed evaluator name generation and validation helpers in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T015 Add evaluator setup plan/result dataclasses and status enums in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T016 Add safe-update comparison helpers for filters, sampling, variable mappings, catalog metadata, and active state in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T017 Add evaluator binding models, load/save functions, secret-key rejection, and repo-local path checks in `src/evaluator_harness/evaluator_bindings.py`
- [X] T018 Extend `LangfuseClient` fake state with evaluator resources and binding-compatible IDs in `src/evaluator_harness/langfuse_client.py`
- [X] T019 Add Langfuse client methods for list/create/update/inactivate/audit evaluator resources with unsupported-capability errors in `src/evaluator_harness/langfuse_client.py`
- [X] T020 Add runner wiring to load judge setup config, binding records, score config sync results, and fake Langfuse evaluator state in `src/evaluator_harness/runner.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Create or Update Managed Langfuse Judge Evaluators (Priority: P1) MVP

**Goal**: Users can apply validated project config and have the harness create, reuse, safely update, inactivate superseded, and bind harness-managed Langfuse evaluators.

**Independent Test**: Run `sync-judge-evaluators --project tests/fixtures/projects/valid_rewrite_quality.yaml` with the fake Langfuse client and confirm created/reused/updated/inactivated statuses, active state, no deletes, local binding writes, and partial-success reporting.

### Tests for User Story 1

- [X] T021 [P] [US1] Add contract tests for `sync-judge-evaluators --dry-run` preview output in `tests/contract/test_cli_sync_judge_evaluators.py`
- [X] T022 [P] [US1] Add contract tests for `sync-judge-evaluators` apply output and exit codes in `tests/contract/test_cli_sync_judge_evaluators.py`
- [X] T023 [P] [US1] Add unit tests for create, reuse, safe update, blocked identity-changing update, and inactivate-old-version planning in `tests/unit/test_judge_setup_planner.py`
- [X] T024 [P] [US1] Add unit tests for local binding required before update/inactivation and display-name-not-enough behavior in `tests/unit/test_evaluator_bindings.py`
- [X] T025 [P] [US1] Add integration tests for fake Langfuse create/reuse/update/inactivate apply flow in `tests/integration/test_sync_judge_evaluators.py`
- [X] T026 [P] [US1] Add integration tests for partial success preserving successful evaluator changes without rollback in `tests/integration/test_sync_judge_evaluators.py`

### Implementation for User Story 1

- [X] T027 [US1] Implement setup planner create/reuse/update/inactivate/block/fail decisions in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T028 [US1] Implement remote compatibility checks using binding records and Langfuse evaluator state in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T029 [US1] Implement apply orchestration with per-evaluator partial-success behavior in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T030 [US1] Implement binding creation and refresh after successful create/update in `src/evaluator_harness/evaluator_bindings.py`
- [X] T031 [US1] Implement older harness-managed evaluator version detection and safe inactivation planning in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T032 [US1] Add `ExperimentRunner.sync_judge_evaluators` orchestration in `src/evaluator_harness/runner.py`
- [X] T033 [US1] Add `sync-judge-evaluators` CLI command with `--dry-run` and apply modes in `src/evaluator_harness/cli.py`
- [X] T034 [US1] Ensure CLI apply reports full success, partial success, failure, binding status, activation state, and remediation in `src/evaluator_harness/cli.py`
- [X] T035 [US1] Update project validation output with judge setup readiness, effective judge default, and binding path in `src/evaluator_harness/cli.py`
- [X] T036 [US1] Update `configs/projects/rewrite_quality.yaml` with judge setup defaults, source type, sampling, backfill, and binding path examples

**Checkpoint**: User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Bind Judge Inputs and Score Targets Safely (Priority: P2)

**Goal**: Users can rely on the harness to bind evaluator variables, score targets, catalog/custom source definitions, judge model/connection, sampling, and backfill policies safely before activation.

**Independent Test**: Run preview/apply against custom and catalog fixture projects and confirm all required variables, score configs, Human Annotation Queue alignment, source type, judge model/connection, sampling, and backfill policies are validated and reported.

### Tests for User Story 2

- [X] T037 [P] [US2] Add unit tests for catalog evaluator setup validation and catalog reference requirements in `tests/unit/test_judge_setup_config.py`
- [X] T038 [P] [US2] Add unit tests for custom evaluator prompt/result contract validation during setup in `tests/unit/test_judge_setup_config.py`
- [X] T039 [P] [US2] Add unit tests for variable mapping failures for missing input, output, baseline output, and ground truth in `tests/unit/test_judge_variable_mapping.py`
- [X] T040 [P] [US2] Add unit tests for score config and Human Annotation Queue score target alignment during judge setup in `tests/unit/test_judge_score_target_setup.py`
- [X] T041 [P] [US2] Add unit tests for project default judge model/connection and evaluator-level override resolution in `tests/unit/test_judge_setup_config.py`
- [X] T042 [P] [US2] Add unit tests for historical backfill opt-in, unsupported backfill blocking, and default disabled backfill in `tests/unit/test_judge_setup_planner.py`
- [X] T043 [P] [US2] Add integration tests for catalog and custom evaluator fake setup flows in `tests/integration/test_sync_judge_evaluators.py`

### Implementation for User Story 2

- [X] T044 [US2] Implement catalog evaluator setup source resolution in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T045 [US2] Implement custom evaluator setup source resolution using prompt path, prompt version, and output schema in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T046 [US2] Implement variable mapping construction and required-input validation in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T047 [US2] Integrate existing score config sync results and Human Annotation Queue score config alignment into evaluator setup planning in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T048 [US2] Implement effective judge model/LLM connection resolution and blocking remediation in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T049 [US2] Implement sampling policy default/override behavior and summary fields in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T050 [US2] Implement historical backfill default/opt-in/unsupported behavior in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T051 [US2] Add CLI output for source type, score target, variable mappings, judge model/connection, sampling, and backfill in `src/evaluator_harness/cli.py`
- [X] T052 [US2] Update evaluator setup export markdown to include catalog/custom source, variable mappings, judge model/connection, sampling, and backfill in `src/evaluator_harness/evaluators.py`

**Checkpoint**: User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - Preview and Audit Planned Langfuse Changes (Priority: P3)

**Goal**: Users can preview planned changes without mutation and audit existing remote evaluator setup against local project definitions and binding records.

**Independent Test**: Run `sync-judge-evaluators --dry-run` and `sync-judge-evaluators --audit` against fake remote states and confirm no mutation, clear drift reporting, unsafe filter blocking, missing binding reporting, and credential/permission errors without secret exposure.

### Tests for User Story 3

- [X] T053 [P] [US3] Add contract tests for `sync-judge-evaluators --audit` output and exit codes in `tests/contract/test_cli_sync_judge_evaluators.py`
- [X] T054 [P] [US3] Add unit tests for audit drift detection, missing remote evaluator, missing binding, and user-owned reference handling in `tests/unit/test_judge_setup_audit.py`
- [X] T055 [P] [US3] Add unit tests for unsafe broad filter blocking and project-scoped filter reporting in `tests/unit/test_judge_setup_planner.py`
- [X] T056 [P] [US3] Add integration tests proving dry-run and audit do not mutate fake Langfuse evaluator state or binding files in `tests/integration/test_sync_judge_evaluators.py`
- [X] T057 [P] [US3] Add contract tests for missing credentials, insufficient permissions, unsupported Langfuse operation, and rate-limit messages in `tests/contract/test_cli_sync_judge_evaluators.py`

### Implementation for User Story 3

- [X] T058 [US3] Implement non-mutating preview mode that resolves all setup plans without writing bindings or remote evaluator state in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T059 [US3] Implement audit mode comparing bindings, project definitions, and remote Langfuse evaluator state in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T060 [US3] Implement broad-filter blocking and remediation messages for evaluator filters in `src/evaluator_harness/langfuse_evaluator_setup.py`
- [X] T061 [US3] Add credential, permission, rate-limit, and unsupported-operation error mapping for evaluator setup in `src/evaluator_harness/langfuse_client.py`
- [X] T062 [US3] Add `--audit` behavior to `sync-judge-evaluators` CLI in `src/evaluator_harness/cli.py`
- [X] T063 [US3] Ensure preview and audit summaries include planned creates/reuses/updates/inactivations/skips/blocks, filters, binding status, and remediation in `src/evaluator_harness/cli.py`

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, live smoke coverage, cleanup, and final verification.

- [X] T064 [P] Update `README.md` with `sync-judge-evaluators` preview/apply/audit workflow and managed evaluator naming
- [X] T065 [P] Update `docs/user-guide.md` with catalog/custom evaluator setup, local bindings, sampling, backfill, and safe update policy
- [X] T066 [P] Update `specs/008-langfuse-judge-setup/quickstart.md` with final CLI output examples after implementation
- [X] T067 [P] Add optional live smoke test for disposable evaluator setup capability detection in `tests/integration/live/test_live_sync_judge_evaluators_smoke.py`
- [X] T068 Add live-test skip/remediation documentation for unsupported Langfuse evaluator CRUD surface in `tests/integration/live/test_live_sync_judge_evaluators_smoke.py`
- [X] T069 Run `uv run pytest -p no:cacheprovider tests/unit/test_judge_setup_config.py tests/unit/test_evaluator_bindings.py tests/unit/test_judge_setup_planner.py`
- [X] T070 Run `uv run pytest -p no:cacheprovider tests/contract/test_cli_sync_judge_evaluators.py tests/integration/test_sync_judge_evaluators.py`
- [X] T071 Run `uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml`
- [X] T072 Run `uv run python run_experiment.py sync-judge-evaluators --project configs/projects/rewrite_quality.yaml --dry-run`
- [X] T073 Run `uv run python run_experiment.py export-evaluator-setup --project configs/projects/rewrite_quality.yaml`
- [X] T074 Record final verification commands and results in `specs/008-langfuse-judge-setup/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion.
- **User Story 2 (Phase 4)**: Depends on Foundational completion; can be developed after US1 interfaces exist or in parallel against planner contracts.
- **User Story 3 (Phase 5)**: Depends on Foundational completion; can be developed after US1 status models exist or in parallel against planner contracts.
- **Polish (Phase 6)**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: MVP. Provides create/reuse/update/inactivate/apply and binding persistence.
- **US2 (P2)**: Builds on setup planning to complete variable, score target, source type, judge model, sampling, and backfill safety.
- **US3 (P3)**: Builds on setup planning to provide non-mutating preview/audit and operational error handling.

### Within Each User Story

- Tests must be written and fail before implementation.
- Config/models before setup planner behavior.
- Planner behavior before runner and CLI wiring.
- Fake integration before optional live smoke.

## Parallel Opportunities

- T001-T006 can run in parallel because they touch distinct fixtures/docs.
- T007-T011 can run in parallel because they create separate test files/fixtures.
- T012-T019 can be split by module after the test contracts are defined.
- T021-T026 can run in parallel before US1 implementation.
- T037-T043 can run in parallel before US2 implementation.
- T053-T057 can run in parallel before US3 implementation.
- T064-T067 can run in parallel after implementation stabilizes.

## Parallel Example: User Story 1

```text
Task: "Add contract tests for sync-judge-evaluators --dry-run preview output in tests/contract/test_cli_sync_judge_evaluators.py"
Task: "Add unit tests for create, reuse, safe update, blocked identity-changing update, and inactivate-old-version planning in tests/unit/test_judge_setup_planner.py"
Task: "Add unit tests for local binding required before update/inactivation and display-name-not-enough behavior in tests/unit/test_evaluator_bindings.py"
Task: "Add integration tests for fake Langfuse create/reuse/update/inactivate apply flow in tests/integration/test_sync_judge_evaluators.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup fixtures.
2. Complete Phase 2 foundational models, binding persistence, fake Langfuse evaluator surface, and planner skeleton.
3. Complete Phase 3 US1 tests and implementation.
4. Stop and validate `sync-judge-evaluators --dry-run` and apply behavior with fake Langfuse state.

### Incremental Delivery

1. Deliver US1 for harness-managed create/reuse/update/inactivation and local binding records.
2. Add US2 for catalog/custom source safety, variable mappings, score target alignment, judge model selection, sampling, and backfill.
3. Add US3 for audit, non-mutating preview guarantees, and operational failure handling.
4. Finish docs, live smoke, and verification.

### Notes

- Do not delete Langfuse evaluator resources in any task.
- Do not mutate user-owned evaluators.
- Do not run judge LLM calls locally.
- Use `uv run ...` for all Python commands.
- Keep binding records non-secret and reviewable.
