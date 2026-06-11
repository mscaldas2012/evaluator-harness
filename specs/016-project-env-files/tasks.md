# Tasks: Project-Specific Environment Files

**Input**: Design documents from `specs/016-project-env-files/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover precedence, missing-file fallback, CLI behavior, and secret-safe errors.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Python CLI source lives under `src/evaluator_harness/`
- Unit tests live under `tests/unit/`
- Integration tests live under `tests/integration/`
- Contract tests live under `tests/contract/`
- Use `uv run ...` for Python commands and tests

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm current env loading surface and create fixture files needed by later tests.

- [X] T001 Inspect current root env loading behavior in `src/evaluator_harness/config.py`, `src/evaluator_harness/runner.py`, and `src/evaluator_harness/langfuse_client.py`
- [X] T002 [P] Add root/project env fixture files for precedence tests under `tests/fixtures/env/`
- [X] T003 [P] Add a minimal project fixture with a slug-safe project name under `tests/fixtures/projects/project_env_files.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add reusable env-resolution primitives before story-specific command behavior.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Add unit tests for parsing multiple env files without leaking values in `tests/unit/test_live_settings.py`
- [X] T005 [P] Add unit tests for shell > project > root precedence in `tests/unit/test_live_settings.py`
- [X] T006 Add project env resolution helper contract in `src/evaluator_harness/config.py`
- [X] T007 Update `load_env_file` or add a companion helper in `src/evaluator_harness/config.py` so file-level overrides can replace root-loaded values without replacing pre-existing shell values
- [X] T008 Add a helper in `src/evaluator_harness/config.py` that derives `.env.<project-name>` from an active project config
- [X] T009 Ensure `LiveSettings.from_env` in `src/evaluator_harness/config.py` can use the new layered env behavior without changing existing `load_file=False` behavior

**Checkpoint**: Env resolution primitives are testable without CLI commands.

---

## Phase 3: User Story 1 - Use Project-Specific Credentials (Priority: P1) MVP

**Goal**: Project commands use `.env.<project-name>` values over root `.env` values while preserving shell overrides.

**Independent Test**: Define duplicate keys in root and project env fixtures, run a project command that reads environment values, and confirm the project-specific value wins unless a shell value is already set.

### Tests for User Story 1 (REQUIRED)

- [X] T010 [P] [US1] Add integration test for root `.env` value overridden by `.env.<project>` in `tests/integration/test_project_env_files.py`
- [X] T011 [P] [US1] Add integration test for project-only env value availability in `tests/integration/test_project_env_files.py`
- [X] T012 [P] [US1] Add contract test proving CLI project commands resolve project env before credential use in `tests/contract/test_cli_project_env_files.py`

### Implementation for User Story 1

- [X] T013 [US1] Update project-scoped runner command paths in `src/evaluator_harness/runner.py` to load root and project env files after reading active project identity
- [X] T014 [US1] Update `LangfuseClient.from_env` or runner construction flow in `src/evaluator_harness/langfuse_client.py` and `src/evaluator_harness/runner.py` so live project commands see project-specific Langfuse settings
- [X] T015 [US1] Update CLI command construction in `src/evaluator_harness/cli.py` where commands instantiate `ExperimentRunner()` directly so project env loading is consistently applied
- [X] T016 [US1] Verify US1 with `uv run pytest -p no:cacheprovider tests/unit/test_live_settings.py tests/integration/test_project_env_files.py tests/contract/test_cli_project_env_files.py`

**Checkpoint**: User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Keep Existing Projects Working (Priority: P2)

**Goal**: Projects without `.env.<project-name>` retain current root `.env` behavior.

**Independent Test**: Run an existing project fixture with only root env values and confirm behavior matches the current single-env-file flow.

### Tests for User Story 2 (REQUIRED)

- [X] T017 [P] [US2] Add integration test for missing `.env.<project>` fallback to root `.env` in `tests/integration/test_project_env_files.py`
- [X] T018 [P] [US2] Add unit test that missing project env files are ignored in `tests/unit/test_live_settings.py`
- [X] T019 [P] [US2] Add regression test for non-project/root-only env loading in `tests/unit/test_live_settings.py`

### Implementation for User Story 2

- [X] T020 [US2] Ensure project env loading in `src/evaluator_harness/config.py` treats absent `.env.<project-name>` files as non-fatal
- [X] T021 [US2] Preserve existing root-only loading behavior for non-project paths in `src/evaluator_harness/runner.py` and `src/evaluator_harness/langfuse_client.py`
- [X] T022 [US2] Verify US2 with `uv run pytest -p no:cacheprovider tests/unit/test_live_settings.py tests/integration/test_project_env_files.py`

**Checkpoint**: Existing projects without project-specific env files remain compatible.

---

## Phase 5: User Story 3 - Make Environment Source Predictable (Priority: P3)

**Goal**: Users can predict considered file names and diagnose missing variables without exposing secret values.

**Independent Test**: Run command scenarios with present, missing, and partial env files and confirm missing variable names are reported without printing secret values.

### Tests for User Story 3 (REQUIRED)

- [X] T023 [P] [US3] Add test for `.env.dfe-general-public` file name derivation in `tests/unit/test_live_settings.py`
- [X] T024 [P] [US3] Add contract test for missing credential output redaction in `tests/contract/test_cli_project_env_files.py`
- [X] T025 [P] [US3] Add integration test for malformed env lines and invalid variable names being ignored in `tests/integration/test_project_env_files.py`

### Implementation for User Story 3

- [X] T026 [US3] Ensure env file diagnostics in `src/evaluator_harness/config.py` never include secret values
- [X] T027 [US3] Update user-facing docs for env precedence and project file naming in `README.md`
- [X] T028 [US3] Update detailed user guidance for project env files in `docs/user-guide.md`
- [X] T029 [US3] Verify US3 with `uv run pytest -p no:cacheprovider tests/unit/test_live_settings.py tests/integration/test_project_env_files.py tests/contract/test_cli_project_env_files.py`

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup across the feature.

- [X] T030 [P] Review `specs/016-project-env-files/quickstart.md` against final command behavior
- [X] T031 Run targeted project validation with `uv run python run_experiment.py validate --project configs/projects/gso.yaml`
- [X] T032 Run targeted regression suite with `uv run pytest -p no:cacheprovider tests/unit/test_live_settings.py tests/integration/test_project_env_files.py tests/contract/test_cli_project_env_files.py`
- [X] T033 Run broader smoke tests with `uv run pytest -p no:cacheprovider tests/unit/test_live_settings.py tests/contract/test_cli_sync_dataset.py tests/contract/test_cli_live_sync_assets.py`
- [X] T034 Confirm no `.env.<project>` files or secret values are staged with `git status --short` and a staged secret scan before commit

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational; MVP scope
- **User Story 2 (Phase 4)**: Depends on Foundational and should be validated after US1 because it protects compatibility
- **User Story 3 (Phase 5)**: Depends on Foundational and can proceed after US1 behavior exists
- **Polish (Phase 6)**: Depends on desired user stories being complete

### User Story Dependencies

- **US1**: No dependency on other user stories after Foundational
- **US2**: Can be implemented after Foundational, but final compatibility validation should run after US1 changes
- **US3**: Can be implemented after Foundational, with CLI redaction tests depending on command behavior from US1

### Within Each User Story

- Write tests first and verify they fail for the expected missing behavior
- Implement the smallest code change to pass the story tests
- Run the story-specific verification command before moving on

## Parallel Opportunities

- T002 and T003 can run in parallel after T001
- T004 and T005 can run in parallel
- T010, T011, and T012 can run in parallel after Foundational
- T017, T018, and T019 can run in parallel after Foundational
- T023, T024, and T025 can run in parallel after Foundational
- Documentation tasks T027 and T028 can run in parallel after behavior stabilizes

## Parallel Example: User Story 1

```text
Task: "T010 [US1] Add integration test for root `.env` value overridden by `.env.<project>` in tests/integration/test_project_env_files.py"
Task: "T011 [US1] Add integration test for project-only env value availability in tests/integration/test_project_env_files.py"
Task: "T012 [US1] Add contract test proving CLI project commands resolve project env before credential use in tests/contract/test_cli_project_env_files.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 only.
3. Verify shell > project > root precedence with targeted tests.
4. Stop and demo project-specific env override behavior.

### Incremental Delivery

1. Deliver US1 to enable project-specific credentials.
2. Deliver US2 to prove existing root-only projects are not broken.
3. Deliver US3 to improve predictability, docs, and redaction coverage.
4. Run Phase 6 verification before committing.

### Notes

- Do not commit real `.env` or `.env.<project>` files.
- Keep secret values out of test failure output and command output.
- Preserve `load_file=False` behavior for tests and callers that explicitly manage their environment.
