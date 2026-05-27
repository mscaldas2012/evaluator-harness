# Tasks: LLM-as-Judges

**Input**: Design documents from `/specs/004-llm-as-judges/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation
tasks and cover validation failures, metadata correctness, score config
alignment, CLI exit behavior, and fake/live Langfuse behavior where applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or depends only on completed prerequisites
- **[Story]**: User story label from spec.md
- Every task includes an exact file path

## Phase 1: Setup

**Purpose**: Establish shared fixtures and examples needed by all stories.

- [X] T001 [P] Add LLM-as-Judge evaluator config examples to `tests/fixtures/projects/valid_rewrite_quality.yaml`
- [X] T002 [P] Add invalid evaluator config fixtures for missing target, missing output schema, broad filter, and score mismatch in `tests/fixtures/projects/`
- [X] T003 [P] Add evaluator prompt fixture variants for valid, multi-dimension, and non-blind prompts in `tests/fixtures/prompts/`
- [X] T004 [P] Update rewrite-quality clarity evaluator prompt expectations in `prompts/rewrite_quality/evaluators/clarity.md`
- [X] T005 [P] Add report ignore coverage for evaluator setup exports in `.gitignore`

---

## Phase 2: Foundational

**Purpose**: Shared model and validation primitives required before user stories can be implemented.

**CRITICAL**: No user story implementation should begin until these foundational tasks are complete.

- [X] T006 [P] Add evaluator target, run types, judging mode, blind-by-default setting, non-blind reason, required input, output schema, and filter profile models in `src/evaluator_harness/config.py`
- [X] T007 [P] Add score source fields and shared score target helpers in `src/evaluator_harness/config.py`
- [X] T008 Add project-level evaluator validation orchestration in `src/evaluator_harness/config.py`
- [X] T009 [P] Add evaluator filter profile construction helper in `src/evaluator_harness/evaluators.py`
- [X] T010 [P] Add judge prompt loading and placeholder inspection helper in `src/evaluator_harness/evaluators.py`
- [X] T011 [P] Add shared score target alignment helper for evaluator and Human Annotation Queue configs in `src/evaluator_harness/evaluators.py`
- [X] T012 Wire evaluator validation into project validation in `src/evaluator_harness/runner.py`
- [X] T013 Update imports and package exports for evaluator helpers in `src/evaluator_harness/__init__.py`

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Define Judge Evaluators for a Project (Priority: P1) MVP

**Goal**: Users can define versioned LLM-as-Judge evaluators with one dimension, required inputs, prompt reference, output schema, score target, and filter profile.

**Independent Test**: A project with a clarity judge validates successfully; invalid evaluator definitions fail with clear field-specific errors.

### Tests for User Story 1

- [X] T014 [P] [US1] Add unit tests for valid evaluator config parsing including `mode`, `run_types`, default `blind=true`, and optional non-blind reason in `tests/unit/test_evaluator_config.py`
- [X] T015 [P] [US1] Add unit tests for missing target, missing prompt reference, missing output schema, missing score target, invalid run types, and `blind=false` without reason in `tests/unit/test_evaluator_config.py`
- [X] T016 [P] [US1] Add unit tests rejecting multi-dimension evaluator prompt definitions in `tests/unit/test_evaluator_prompts.py`
- [X] T017 [P] [US1] Add contract test for `validate` output including evaluator target and score target in `tests/contract/test_cli_validate.py`
- [X] T018 [P] [US1] Add integration test for rewrite-quality evaluator validation in `tests/integration/test_validate_project.py`

### Implementation for User Story 1

- [X] T019 [US1] Extend `EvaluatorDefinition` with `dimension`, `target`, `target_observation_role`, `target_observation_name`, `run_types`, `mode`, `blind`, `non_blind_reason`, `required_inputs`, and `output_schema` in `src/evaluator_harness/config.py`
- [X] T020 [US1] Add evaluator prompt reference version validation in `src/evaluator_harness/config.py`
- [X] T021 [US1] Add single-dimension evaluator validation using prompt metadata or config fields in `src/evaluator_harness/evaluators.py`
- [X] T022 [US1] Add required input validation against dataset fields, generated output, baseline output, and ground truth in `src/evaluator_harness/evaluators.py`
- [X] T023 [US1] Update `ValidationResult` and `validate_project` to report evaluator target and score target in `src/evaluator_harness/runner.py`
- [X] T024 [US1] Update CLI `validate` output for evaluator target and score target in `src/evaluator_harness/cli.py`
- [X] T025 [US1] Update `configs/projects/rewrite_quality.yaml` with explicit clarity evaluator target, dimension, run types, judging mode, blind setting, output schema, and required inputs

**Checkpoint**: User Story 1 is independently functional.

---

## Phase 4: User Story 2 - Prepare Langfuse Evaluator Setup (Priority: P2)

**Goal**: Users can identify the correct Langfuse score configs, judge prompt text, and evaluator filter profile for manual Langfuse LLM-as-Judge setup.

**Independent Test**: A user can run setup-related CLI commands and see the clarity evaluator score target, shared Human Annotation Queue score alignment, prompt path/version, and filter profile.

### Tests for User Story 2

- [X] T026 [P] [US2] Add unit tests for canonical score target alignment and score source mapping between judge evaluator and Human Annotation Queue score configs in `tests/unit/test_evaluator_score_alignment.py`
- [X] T027 [P] [US2] Add unit tests for filter profile construction using `observation_role=model_output` and project metadata in `tests/unit/test_evaluator_filter_profiles.py`
- [X] T028 [P] [US2] Add contract tests for `render-judge-prompts` output in `tests/contract/test_cli_render_judge_prompts.py`
- [X] T029 [P] [US2] Add contract tests for `export-evaluator-setup` output path, shared score config, and score source mapping content in `tests/contract/test_cli_export_evaluator_setup.py`
- [X] T030 [P] [US2] Add fake integration test for score config sync alignment with managed annotation queue score IDs in `tests/integration/test_evaluator_score_alignment_integration.py`

### Implementation for User Story 2

- [X] T031 [US2] Implement score target alignment validation in `src/evaluator_harness/evaluators.py`
- [X] T032 [US2] Update `sync_score_configs` flow to validate Human Annotation Queue score alignment in `src/evaluator_harness/runner.py`
- [X] T033 [US2] Implement judge prompt rendering result model in `src/evaluator_harness/evaluators.py`
- [X] T034 [US2] Add `render_judge_prompts` runner method in `src/evaluator_harness/runner.py`
- [X] T035 [US2] Add `render-judge-prompts` CLI command in `src/evaluator_harness/cli.py`
- [X] T036 [US2] Implement evaluator setup markdown export in `src/evaluator_harness/evaluators.py`
- [X] T037 [US2] Add `export_evaluator_setup` runner method writing `reports/evaluator-setup-<project>-<version>.md` in `src/evaluator_harness/runner.py`
- [X] T038 [US2] Add `export-evaluator-setup` CLI command in `src/evaluator_harness/cli.py`
- [X] T039 [US2] Update README evaluator setup guidance in `README.md`

**Checkpoint**: User Story 2 is independently functional.

---

## Phase 5: User Story 3 - Run Blind and Comparable Judging (Priority: P3)

**Goal**: Judge setup produces blind, comparable evaluator inputs and metadata for baseline and candidate model-output observations.

**Independent Test**: A fake baseline/candidate run emits model-output observation metadata suitable for evaluator filters, and blind prompt/input preparation excludes provider and model identity.

### Tests for User Story 3

- [X] T040 [P] [US3] Add unit tests for blind prompt placeholder rejection in `tests/unit/test_evaluator_blindness.py`
- [X] T041 [P] [US3] Add unit tests for sanitized judge input package construction in `tests/unit/test_judge_input_package.py`
- [X] T042 [P] [US3] Add unit tests for judge result contract schema validation and score range example validation in `tests/unit/test_judge_result_schema.py`
- [X] T043 [P] [US3] Add integration test that baseline and candidate observations expose model-output filter metadata in `tests/integration/test_evaluator_observation_metadata.py`
- [X] T044 [P] [US3] Add live smoke assertion for model-output observation metadata when live tests are enabled in `tests/integration/live/test_live_azure_baseline_smoke.py`

### Implementation for User Story 3

- [X] T045 [US3] Implement blind placeholder validation for evaluator prompts in `src/evaluator_harness/evaluators.py`
- [X] T046 [US3] Implement sanitized judge input package builder in `src/evaluator_harness/evaluators.py`
- [X] T047 [US3] Implement judge result contract schema and score range example validators in `src/evaluator_harness/evaluators.py`
- [X] T048 [US3] Ensure baseline and candidate request metadata include `observation_role=model_output`, evaluator set, project version, dataset identity, and prompt version in `src/evaluator_harness/runner.py`
- [X] T049 [US3] Add score source mapping guidance for `llm_judge -> EVAL` and `human_annotation -> ANNOTATION` in `src/evaluator_harness/evaluators.py`
- [X] T050 [US3] Update `docs/user-guide.md` with blind judging, shared scores, and Langfuse filter setup steps

**Checkpoint**: User Story 3 is independently functional.

---

## Phase 6: Polish & Cross-Cutting

**Purpose**: Documentation, cleanup, and full verification.

- [X] T051 [P] Update `specs/004-llm-as-judges/quickstart.md` with final implemented CLI output examples
- [X] T052 [P] Update `docs/langfuse-automation-backlog.md` with future evaluator automation tasks
- [X] T053 Run `uv run pytest --no-cov -p no:cacheprovider` and record the verification result in `specs/004-llm-as-judges/quickstart.md`
- [X] T054 Run `uv run pytest --no-cov -p no:cacheprovider -m live -vv` with `RUN_LIVE_TESTS=1` when credentials are available and record the live verification note in `specs/004-llm-as-judges/quickstart.md`
- [X] T055 Run `uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml` and record the command example in `specs/004-llm-as-judges/quickstart.md`
- [X] T056 Run `uv run python run_experiment.py render-judge-prompts --project configs/projects/rewrite_quality.yaml` and record the command example in `specs/004-llm-as-judges/quickstart.md`
- [X] T057 Run `uv run python run_experiment.py export-evaluator-setup --project configs/projects/rewrite_quality.yaml` and record the output path example in `specs/004-llm-as-judges/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1 and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2 and is the MVP.
- **User Story 2 (Phase 4)**: Depends on Phase 2; uses evaluator config from US1 but remains testable with fixtures.
- **User Story 3 (Phase 5)**: Depends on Phase 2; can proceed after US1 validation rules exist.
- **Polish (Phase 6)**: Depends on selected user stories.

### User Story Dependencies

- **US1**: Required MVP; no dependencies after foundational work.
- **US2**: Depends on ScoreTarget and EvaluatorFilterProfile models from foundational work; integrates best after US1.
- **US3**: Depends on JudgeInputPackage and JudgeResultContract schema from foundational work; integrates best after US1.

### Parallel Opportunities

- T001-T005 can run in parallel.
- T006, T007, T009, T010, and T011 can run in parallel after setup.
- US1 tests T014-T018 can run in parallel before US1 implementation.
- US2 tests T026-T030 can run in parallel before US2 implementation.
- US3 tests T040-T044 can run in parallel before US3 implementation.
- Documentation tasks T051 and T052 can run in parallel after story implementation.

---

## Parallel Example: User Story 1

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_evaluator_config.py
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_evaluator_prompts.py
uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_validate.py
uv run pytest --no-cov -p no:cacheprovider tests/integration/test_validate_project.py
```

---

## Parallel Example: User Story 2

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_evaluator_score_alignment.py
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_evaluator_filter_profiles.py
uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_render_judge_prompts.py
uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_export_evaluator_setup.py
```

---

## Parallel Example: User Story 3

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_evaluator_blindness.py
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_judge_input_package.py
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_judge_result_schema.py
uv run pytest --no-cov -p no:cacheprovider tests/integration/test_evaluator_observation_metadata.py
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational evaluator models and helpers.
3. Complete Phase 3 User Story 1.
4. Stop and validate evaluator definitions with `validate`.

### Incremental Delivery

1. US1 delivers validated evaluator definitions.
2. US2 adds Langfuse setup outputs and shared score alignment.
3. US3 adds blind/comparable judge input and result validation.
4. Polish verifies the full local and optional live path.

### Notes

- Tests must be written before implementation tasks in each user story.
- The harness must not run LLM judges locally in this MVP.
- Langfuse owns evaluator execution, score writes, dashboards, and comparisons.
- LLM-as-Judge and Human Annotation Queue scoring must share the same score config for the same evaluator dimension, distinguished by Langfuse score source rather than score config name.
