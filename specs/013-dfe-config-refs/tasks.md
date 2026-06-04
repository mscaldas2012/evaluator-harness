# Tasks: Shared Scenario Config References

**Input**: Design documents from `/specs/013-dfe-config-refs/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation
tasks and cover success paths, validation failures, metadata correctness, CLI
exit behavior, and compatibility with existing project configs.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature-specific test fixtures and keep existing branch state explicit.

- [x] T001 Confirm `docs/evaluator_harness_project_presentation.pptx` is unrelated and remains unstaged while working on `013-dfe-config-refs`
- [x] T002 [P] Review existing DFE config sections in `configs/projects/dfe.yaml` to identify evaluator, judge setup, and human review content to extract
- [x] T003 [P] Review existing metadata surfaces in `src/evaluator_harness/runner.py`, `src/evaluator_harness/exports.py`, and `src/evaluator_harness/langfuse_client.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish config model contracts and reusable test fixtures that all user stories depend on.

**CRITICAL**: No user story implementation should begin until these contracts and fixtures are in place.

- [x] T004 [P] Add shared config fixture files for valid and invalid `config_refs.evaluation` cases under `tests/fixtures/projects/config_refs/`
- [x] T005 [P] Add scenario metadata fixture project files under `tests/fixtures/projects/config_refs/`
- [x] T006 [P] Add DFE scenario fixture placeholders under `tests/fixtures/projects/config_refs/dfe/`
- [x] T007 Add test helper assertions for effective evaluator, judge setup, and human review equivalence in `tests/fixtures/config_refs.py`

**Checkpoint**: Fixtures and helpers are ready for user story tests.

---

## Phase 3: User Story 1 - Share Evaluation Configuration Across Scenarios (Priority: P1) MVP

**Goal**: A project config can reference one shared evaluation config and validate as a complete effective project config without duplicating evaluators, score definitions, judge setup, and human review policy.

**Independent Test**: Validate a project using `config_refs.evaluation` and confirm the effective config matches an equivalent single-file project; verify missing refs, disallowed sections, and conflicts fail before runtime.

### Tests for User Story 1 (REQUIRED)

- [x] T008 [P] [US1] Add unit tests for valid `config_refs.evaluation` resolution in `tests/unit/test_config_refs.py`
- [x] T009 [P] [US1] Add unit tests for missing shared config, unreadable shared config, and invalid YAML failures in `tests/unit/test_config_refs.py`
- [x] T010 [P] [US1] Add unit tests rejecting disallowed shared sections `project`, `dataset`, `task_prompt`, `baseline`, `candidates`, `config_refs`, and `scenario` in `tests/unit/test_config_refs.py`
- [x] T011 [P] [US1] Add unit tests rejecting local/shared conflicts for `evaluators`, `judge_setup`, and `human_review` in `tests/unit/test_config_refs.py`
- [x] T012 [P] [US1] Add contract tests for `validate --project` success and non-zero conflict output in `tests/contract/test_cli_validate_config_refs.py`
- [x] T013 [P] [US1] Add regression test proving existing single-file configs still validate without `config_refs` in `tests/unit/test_config_refs.py`

### Implementation for User Story 1

- [x] T014 [US1] Add `ConfigRefs` and raw config document parsing support in `src/evaluator_harness/config.py`
- [x] T015 [US1] Implement shared evaluation path resolution relative to the project file and repository root in `src/evaluator_harness/config.py`
- [x] T016 [US1] Implement allowed/disallowed shared evaluation section validation in `src/evaluator_harness/config.py`
- [x] T017 [US1] Implement local/shared conflict detection for `evaluators`, `judge_setup`, and `human_review` in `src/evaluator_harness/config.py`
- [x] T018 [US1] Merge allowed shared evaluation sections before constructing `ProjectConfig` in `src/evaluator_harness/config.py`
- [x] T019 [US1] Preserve current `load_project_config()` behavior for project files without `config_refs` in `src/evaluator_harness/config.py`
- [x] T020 [US1] Ensure CLI validation surfaces clear config reference errors through existing error handling in `src/evaluator_harness/cli.py`

**Checkpoint**: User Story 1 is complete when config reference projects validate and all failure modes are covered without changing runtime behavior.

---

## Phase 4: User Story 2 - Run Scenario-Specific Project Configs (Priority: P2)

**Goal**: DFE General public, Health care provider, and Public health SME project configs reuse one shared DFE readability config while keeping scenario-specific dataset identity and task prompt paths.

**Independent Test**: Validate all three DFE scenario project configs and confirm they share effective evaluator, judge setup, and human review definitions while using distinct project names, dataset names, task prompts, and scenario metadata.

### Tests for User Story 2 (REQUIRED)

- [x] T021 [P] [US2] Add integration test validating all DFE scenario project configs in `tests/integration/test_dfe_config_refs.py`
- [x] T022 [P] [US2] Add integration test comparing effective DFE scenario evaluator, judge setup, and human review definitions in `tests/integration/test_dfe_config_refs.py`
- [x] T023 [P] [US2] Add integration test confirming each DFE scenario project has distinct project name, Langfuse dataset name, task prompt path, and scenario identity in `tests/integration/test_dfe_config_refs.py`

### Implementation for User Story 2

- [x] T024 [US2] Create shared DFE readability config with evaluators, judge setup, and human review in `configs/shared/dfe_readability.yaml`
- [x] T025 [US2] Create General public DFE project config using `prompts/dfe/task_prompt_generic.md` in `configs/projects/dfe-general-public.yaml`
- [x] T026 [US2] Create Health care provider DFE project config using `prompts/dfe/task_prompt_hcp.md` in `configs/projects/dfe-healthcare-provider.yaml`
- [x] T027 [US2] Create Public health SME DFE project config using `prompts/dfe/task_prompt_php.md` in `configs/projects/dfe-public-health-sme.yaml`
- [x] T028 [US2] Ensure each DFE scenario config defines complete `scenario` metadata in `configs/projects/dfe-general-public.yaml`, `configs/projects/dfe-healthcare-provider.yaml`, and `configs/projects/dfe-public-health-sme.yaml`

**Checkpoint**: User Story 2 is complete when the three DFE scenario configs validate independently and share only the intended evaluation configuration.

---

## Phase 5: User Story 3 - Preserve Scenario Provenance In Runs (Priority: P3)

**Goal**: Scenario metadata is emitted to Langfuse traces, run metadata, exports, and annotation review payloads when present, while projects without scenario metadata remain unchanged.

**Independent Test**: Run fake baseline/candidate flows using a scenario project and verify scenario fields appear in trace metadata, CSV exports, and review payload context; verify non-scenario projects do not require scenario fields.

### Tests for User Story 3 (REQUIRED)

- [x] T029 [P] [US3] Add unit tests for complete and incomplete scenario identity validation in `tests/unit/test_scenario_metadata.py`
- [x] T030 [P] [US3] Add unit tests for baseline and candidate trace metadata scenario fields in `tests/unit/test_scenario_metadata.py`
- [x] T031 [P] [US3] Add unit tests for scenario columns in CSV exports in `tests/unit/test_exports.py`
- [x] T032 [P] [US3] Add unit tests for scenario metadata in annotation queue payload `trace_context` in `tests/unit/test_annotation_queue_payloads.py`
- [x] T033 [P] [US3] Add regression test proving non-scenario project traces and exports remain valid in `tests/unit/test_scenario_metadata.py`

### Implementation for User Story 3

- [x] T034 [US3] Add optional `ScenarioIdentity` model to `src/evaluator_harness/config.py`
- [x] T035 [US3] Add scenario metadata helper for `scenario_group`, `scenario_name`, and `scenario_display_name` in `src/evaluator_harness/config.py`
- [x] T036 [US3] Add scenario metadata to run creation metadata in `src/evaluator_harness/runner.py`
- [x] T037 [US3] Add scenario metadata to request and trace metadata in `src/evaluator_harness/runner.py`
- [x] T038 [US3] Add scenario export fields and row population in `src/evaluator_harness/exports.py`
- [x] T039 [US3] Add scenario metadata to annotation queue payload `trace_context` in `src/evaluator_harness/langfuse_client.py`

**Checkpoint**: User Story 3 is complete when scenario fields are queryable in trace metadata, visible in exports and review payloads, and optional for existing projects.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation commands, and final regression checks across all stories.

- [x] T040 [P] Document `config_refs.evaluation` and optional `scenario` metadata in `README.md`
- [x] T041 [P] Add DFE scenario quickstart commands to `docs/user-guide.md`
- [x] T042 [P] Update or add project config examples in `tests/fixtures/projects/` for future non-DFE scenario groups
- [x] T043 Run `uv run python run_experiment.py validate --project configs/projects/dfe-general-public.yaml`
- [x] T044 Run `uv run python run_experiment.py validate --project configs/projects/dfe-healthcare-provider.yaml`
- [x] T045 Run `uv run python run_experiment.py validate --project configs/projects/dfe-public-health-sme.yaml`
- [x] T046 Run `uv run pytest -p no:cacheprovider tests/unit/test_config_refs.py tests/unit/test_scenario_metadata.py tests/unit/test_exports.py tests/unit/test_annotation_queue_payloads.py tests/contract/test_cli_validate_config_refs.py tests/integration/test_dfe_config_refs.py`
- [x] T047 Review `specs/013-dfe-config-refs/quickstart.md` against implemented commands and update if paths or command names changed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks user story work.
- **User Story 1 (Phase 3)**: Depends on Foundational and is the MVP.
- **User Story 2 (Phase 4)**: Depends on User Story 1 because DFE configs require config reference resolution.
- **User Story 3 (Phase 5)**: Depends on Foundational and can proceed after scenario model design is stable; it integrates cleanly after User Story 1.
- **Polish (Phase 6)**: Depends on all desired user stories.

### User Story Dependencies

- **US1**: Required first for config reference loading and validation.
- **US2**: Requires US1 resolution and validation behavior.
- **US3**: Requires scenario identity model from US3 tasks and effective project config availability from US1.

### Within Each User Story

- Write tests first and confirm they fail.
- Implement schema/model changes before runtime metadata propagation.
- Implement runtime propagation before export/review payload changes.
- Validate each story independently at its checkpoint.

## Parallel Opportunities

- T002 and T003 can run in parallel during setup.
- T004, T005, and T006 can run in parallel because they create distinct fixture sets.
- T008 through T013 can be written in parallel before US1 implementation.
- T021 through T023 can be written in parallel before DFE config creation.
- T029 through T033 can be written in parallel because they target separate metadata surfaces.
- T040 through T042 can run in parallel during polish.

## Parallel Example: User Story 1

```text
Task: "Add unit tests for valid config_refs.evaluation resolution in tests/unit/test_config_refs.py"
Task: "Add contract tests for validate --project success and conflict output in tests/contract/test_cli_validate_config_refs.py"
Task: "Add regression test proving existing single-file configs still validate without config_refs in tests/unit/test_config_refs.py"
```

## Parallel Example: User Story 3

```text
Task: "Add unit tests for scenario columns in CSV exports in tests/unit/test_exports.py"
Task: "Add unit tests for scenario metadata in annotation queue payload trace_context in tests/unit/test_annotation_queue_payloads.py"
Task: "Add unit tests for baseline and candidate trace metadata scenario fields in tests/unit/test_scenario_metadata.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete US1 tests T008 through T013.
3. Complete US1 implementation T014 through T020.
4. Validate US1 independently with unit and contract tests.
5. Stop for review if config reference behavior needs sign-off before DFE config extraction.

### Incremental Delivery

1. US1: shared evaluation config resolution and validation.
2. US2: DFE shared config plus three scenario project configs.
3. US3: scenario metadata propagation into traces, exports, and review payloads.
4. Polish: docs and full focused validation.

### Notes

- `[P]` tasks use different files or independent fixture sections.
- `[US#]` labels map directly to the three user stories in `spec.md`.
- Keep scenario names data-driven; do not hardcode DFE audience names in runtime logic.
- Do not stage or modify `docs/evaluator_harness_project_presentation.pptx` as part of this feature.
