# Tasks: Model Output Observation Targeting

**Input**: Design documents from `/specs/015-model-output-targeting/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/provider-final-output-contract.md, quickstart.md

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover metadata correctness, provider tracing paths, Langfuse fake-state behavior, and CLI validation where applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm current tracing behavior and prepare focused test surfaces.

- [x] T001 Review current trace/span role assignment in `src/evaluator_harness/runner.py`
- [x] T002 Review fake/live observation storage helpers in `src/evaluator_harness/langfuse_client.py`
- [x] T003 [P] Review provider tracing strategy flags in `src/evaluator_harness/providers/openai_compatible.py`, `src/evaluator_harness/providers/dry_run.py`, and `src/evaluator_harness/providers/ollama.py`
- [x] T004 [P] Review evaluator filter construction in `src/evaluator_harness/evaluators.py`
- [x] T005 [P] Review existing run and progress tests in `tests/unit/test_progress_reporting.py`, `tests/contract/test_cli_run_baseline.py`, and `tests/integration/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared test fixtures and constants needed by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 Define shared observation role constants or helper functions in `src/evaluator_harness/runner.py` or a focused helper module under `src/evaluator_harness/`
- [x] T007 [P] Add test fixture helpers for counting model-output eligible observations in `tests/integration/test_model_output_targeting.py`
- [x] T008 [P] Add provider tracing contract fixture cases in `tests/unit/test_provider_tracing_metadata.py`
- [x] T009 Ensure existing fake Langfuse trace state exposes enough metadata for observation targeting tests in `src/evaluator_harness/langfuse_client.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Prevent Double Evaluator Matches (Priority: P1) MVP

**Goal**: Each completed dataset item run has exactly one standard model-output observation eligible for evaluator targeting.

**Independent Test**: Run fake baseline paths for manual-generation and non-generation providers and assert one `model_output` observation per completed item, with parent/container observations not matching.

### Tests for User Story 1 (REQUIRED)

- [x] T010 [P] [US1] Add failing integration test for OpenAI-compatible manual generation path showing only the generation observation has `observation_role=model_output` in `tests/integration/test_model_output_targeting.py`
- [x] T011 [P] [US1] Add failing integration test for dry-run/non-generation path showing exactly one model-output eligible observation per item in `tests/integration/test_model_output_targeting.py`
- [x] T012 [P] [US1] Add failing unit test that parent/container request metadata uses a non-final role in `tests/unit/test_progress_reporting.py` or `tests/unit/test_model_output_metadata.py`
- [x] T013 [P] [US1] Add failing contract test proving baseline CLI fake run preserves evaluator-ready metadata without duplicate model-output roles in `tests/contract/test_cli_run_baseline.py`

### Implementation for User Story 1

- [x] T014 [US1] Split parent/container metadata from final-output metadata in `src/evaluator_harness/runner.py`
- [x] T015 [US1] Ensure manual generation spans receive final-output metadata with `observation_role=model_output` in `src/evaluator_harness/runner.py`
- [x] T016 [US1] Ensure parent/container trace spans receive a non-final observation role in `src/evaluator_harness/runner.py`
- [x] T017 [US1] Ensure non-generation provider paths still produce one model-output eligible logged observation in `src/evaluator_harness/runner.py`
- [x] T018 [US1] Preserve project, project version, scenario, run type, dataset item, prompt identity, provider, model, and evaluator-set metadata on the final model output observation in `src/evaluator_harness/runner.py`
- [x] T019 [US1] Run `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_model_output_targeting.py tests/contract/test_cli_run_baseline.py`

**Checkpoint**: User Story 1 should prevent the 2x evaluator count for new runs.

---

## Phase 4: User Story 2 - Preserve Provider Portability (Priority: P2)

**Goal**: Provider integrations can honor the final-output contract without hardcoding provider-specific observation names.

**Independent Test**: Validate provider tracing metadata cases for manual, dry-run/synthetic, Ollama/manual fallback, and future native Langfuse provider patterns.

### Tests for User Story 2 (REQUIRED)

- [x] T020 [P] [US2] Add failing unit tests for provider tracing strategy metadata in `tests/unit/test_provider_tracing_metadata.py`
- [x] T021 [P] [US2] Add failing unit test that evaluator configs do not require `target_observation_name` for standard model-output judges in `tests/unit/test_config.py`
- [x] T022 [P] [US2] Add failing integration test proving dry-run outputs remain evaluator-targetable with role-only filters in `tests/integration/test_model_output_targeting.py`
- [x] T023 [P] [US2] Add failing contract documentation check for the provider final-output contract in `tests/contract/test_provider_final_output_contract.py`

### Implementation for User Story 2

- [x] T024 [US2] Add provider tracing contract metadata or helper output for OpenAI-compatible, dry-run, and Ollama providers in `src/evaluator_harness/providers/`
- [x] T025 [US2] Ensure evaluator validation continues to allow standard role-only model-output filters in `src/evaluator_harness/evaluators.py`
- [x] T026 [US2] Add a documented configuration path for providers that require explicit final-output observation targeting in `src/evaluator_harness/config.py`
- [x] T027 [US2] Update provider integration documentation in `docs/user-guide.md`
- [x] T028 [US2] Run `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_provider_tracing_metadata.py tests/unit/test_config.py tests/integration/test_model_output_targeting.py`

**Checkpoint**: User Story 2 should preserve portability across current and future provider integrations.

---

## Phase 5: User Story 3 - Make Misconfiguration Visible (Priority: P3)

**Goal**: Users can detect missing, duplicate, or provider-specific evaluator targeting before running expensive judges.

**Independent Test**: Feed simulated trace/observation samples into diagnostics and confirm duplicate, missing, aligned, and provider-specific findings.

### Tests for User Story 3 (REQUIRED)

- [x] T029 [P] [US3] Add failing unit tests for targeting diagnostic statuses in `tests/unit/test_model_output_targeting_diagnostics.py`
- [x] T030 [P] [US3] Add failing CLI contract test for diagnostic output or validation warning in `tests/contract/test_cli_run_baseline.py`
- [x] T031 [P] [US3] Add failing integration test for duplicate model-output marker detection in `tests/integration/test_model_output_targeting.py`

### Implementation for User Story 3

- [x] T032 [US3] Implement model-output targeting diagnostic helper in `src/evaluator_harness/evaluators.py` or a focused helper module under `src/evaluator_harness/`
- [x] T033 [US3] Wire diagnostics into validation, audit, or run output without blocking valid standard configurations in `src/evaluator_harness/cli.py` and `src/evaluator_harness/runner.py`
- [x] T034 [US3] Ensure diagnostics report clear remediation for duplicate, missing, provider-specific, and unknown targeting states in `src/evaluator_harness/`
- [x] T035 [US3] Update `docs/user-guide.md` with diagnostic interpretation and remediation examples
- [x] T036 [US3] Run `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_model_output_targeting_diagnostics.py tests/contract/test_cli_run_baseline.py tests/integration/test_model_output_targeting.py`

**Checkpoint**: User Story 3 should make ambiguous targeting visible before expensive evaluator runs.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, documentation, and cleanup across all user stories.

- [x] T037 [P] Update `specs/015-model-output-targeting/quickstart.md` if implementation commands or expected counts changed
- [x] T038 [P] Update `docs/user-guide.md` to explain final-output role, parent/container role, and provider contract in user-facing language
- [x] T039 [P] Verify DFE configs still validate with `uv run python run_experiment.py validate --project configs/projects/dfe-general-public.yaml`
- [x] T040 [P] Verify healthcare and public health SME configs with `uv run python run_experiment.py validate --project configs/projects/dfe-healthcare-provider.yaml` and `uv run python run_experiment.py validate --project configs/projects/dfe-public-health-sme.yaml`
- [x] T041 Run targeted regression suite with `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_model_output_targeting.py tests/unit/test_provider_tracing_metadata.py tests/contract/test_cli_run_baseline.py`
- [x] T042 Run broader evaluator regression suite with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_judge_setup_planner.py tests/integration/test_sync_judge_evaluators.py tests/contract/test_cli_sync_judge_evaluators.py`
- [x] T043 Run `git diff --check`
- [x] T044 Review untracked generated Langfuse binding files and leave them uncommitted unless explicitly requested

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - MVP and required before final confidence
- **User Story 2 (Phase 4)**: Depends on Foundational; can be developed after or alongside US1 but should not break US1 behavior
- **User Story 3 (Phase 5)**: Depends on Foundational; diagnostics should use the contract established by US1/US2
- **Polish (Phase 6)**: Depends on desired user stories being complete

### User Story Dependencies

- **US1 Prevent Double Evaluator Matches**: MVP; no dependency on US2 or US3 after foundation
- **US2 Preserve Provider Portability**: Can start after foundation; integrates with US1 metadata contract
- **US3 Make Misconfiguration Visible**: Can start after foundation; most valuable after US1/US2 define the valid contract

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Metadata contract before runner/provider implementation
- Runner/provider implementation before CLI diagnostics
- Story checkpoint before moving to lower-priority work

## Parallel Opportunities

- T003, T004, T005 can run in parallel during setup
- T007 and T008 can run in parallel during foundation
- T010, T011, T012, T013 can be written in parallel before US1 implementation
- T020, T021, T022, T023 can be written in parallel before US2 implementation
- T029, T030, T031 can be written in parallel before US3 implementation
- T037, T038, T039, T040 can run in parallel during polish

## Parallel Example: User Story 1

```text
Task: "Add failing integration test for OpenAI-compatible manual generation path in tests/integration/test_model_output_targeting.py"
Task: "Add failing integration test for dry-run/non-generation path in tests/integration/test_model_output_targeting.py"
Task: "Add failing unit test that parent/container request metadata uses a non-final role in tests/unit/test_model_output_metadata.py"
Task: "Add failing contract test proving baseline CLI fake run preserves evaluator-ready metadata without duplicate model-output roles in tests/contract/test_cli_run_baseline.py"
```

## Parallel Example: User Story 2

```text
Task: "Add failing unit tests for provider tracing strategy metadata in tests/unit/test_provider_tracing_metadata.py"
Task: "Add failing unit test that evaluator configs do not require target_observation_name for standard model-output judges in tests/unit/test_config.py"
Task: "Add failing integration test proving dry-run outputs remain evaluator-targetable with role-only filters in tests/integration/test_model_output_targeting.py"
```

## Parallel Example: User Story 3

```text
Task: "Add failing unit tests for targeting diagnostic statuses in tests/unit/test_model_output_targeting_diagnostics.py"
Task: "Add failing CLI contract test for diagnostic output or validation warning in tests/contract/test_cli_run_baseline.py"
Task: "Add failing integration test for duplicate model-output marker detection in tests/integration/test_model_output_targeting.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate that two 12-item runs produce 24 evaluator matches, not 48
5. Demo or sync provider portability/diagnostics work later

### Incremental Delivery

1. Foundation complete
2. US1 prevents duplicate counts for current runs
3. US2 hardens the provider contract for future integrations
4. US3 adds diagnostics for ambiguous provider or trace shapes
5. Polish verifies DFE configs and evaluator regressions

### Notes

- Keep evaluator configs provider-neutral unless explicitly targeting a non-final observation.
- Do not rewrite historical traces or scores.
- Do not commit generated Langfuse binding files unless explicitly requested.
- Prefer small helper functions over broad abstractions unless duplication becomes concrete.
