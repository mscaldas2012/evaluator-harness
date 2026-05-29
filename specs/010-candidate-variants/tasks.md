# Tasks: Candidate Variants

**Input**: Design documents from `/specs/010-candidate-variants/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover success paths, validation failures, Langfuse metadata correctness, export metadata, baseline reference behavior, and CLI exit behavior.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish fixtures, prompt artifacts, and inspection context needed for all candidate-variant stories.

- [X] T001 Inspect existing candidate config, prompt rendering, baseline lookup, trace metadata, and export behavior in `src/evaluator_harness/config.py`, `src/evaluator_harness/runner.py`, and `src/evaluator_harness/exports.py`
- [X] T002 Inspect existing CLI candidate command behavior and tests in `src/evaluator_harness/cli.py` and `tests/contract/test_cli_run_candidate.py`
- [X] T003 [P] Add prompt-v2 fixture prompt with required `{{input}}` variable in `tests/fixtures/prompts/rewrite_quality_task_prompt_v2.md`
- [X] T004 [P] Add valid prompt-variant project fixture in `tests/fixtures/projects/valid_prompt_variant_candidate.yaml`
- [X] T005 [P] Add invalid prompt-variant missing prompt fixture in `tests/fixtures/projects/invalid_prompt_variant_missing_prompt.yaml`
- [X] T006 [P] Add invalid prompt-variant missing input variable fixture in `tests/fixtures/projects/invalid_prompt_variant_missing_input.yaml`
- [X] T007 [P] Add parameter-variant project fixture in `tests/fixtures/projects/valid_parameter_variants.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared config and identity capabilities required before user stories can be completed.

**CRITICAL**: No user story runtime implementation should begin until this phase is complete.

### Tests for Foundation

- [X] T008 [P] Add config test for unique candidate names in `tests/unit/test_config.py`
- [X] T009 [P] Add config test accepting candidate-level task prompt overrides in `tests/unit/test_config.py`
- [X] T010 [P] Add config tests rejecting invalid candidate prompt overrides in `tests/unit/test_config.py`
- [X] T011 [P] Add prompt identity hashing tests in `tests/unit/test_prompt_refs.py`
- [X] T012 [P] Add parameter identity hashing tests in `tests/unit/test_config.py`
- [X] T013 [P] Add variant identity helper tests in `tests/integration/test_parameter_variants.py`

### Implementation for Foundation

- [X] T014 Add optional `task_prompt` field to candidate model config in `src/evaluator_harness/config.py`
- [X] T015 Add candidate-name uniqueness validation in `src/evaluator_harness/config.py`
- [X] T016 Extend project validation to validate candidate prompt overrides in `src/evaluator_harness/config.py`
- [X] T017 Add reusable prompt identity and prompt content hash helper in `src/evaluator_harness/runner.py`
- [X] T018 Add reusable model, parameter, and variant identity helpers in `src/evaluator_harness/runner.py`

**Checkpoint**: Foundation ready. Project configs can represent model, prompt, and parameter variants with stable non-secret identities.

---

## Phase 3: User Story 1 - Compare Prompt Variant Against Existing Baseline (Priority: P1) MVP

**Goal**: A prompt-v2 candidate can run against an existing compatible prompt-v1 baseline and preserve comparison metadata in Langfuse.

**Independent Test**: Configure a prompt-v2 candidate, run baseline then candidate with fake providers, and confirm candidate outputs compare against baseline outputs for the same dataset items while recording separate baseline and candidate prompt identities.

### Tests for User Story 1

- [X] T019 [P] [US1] Add integration test for prompt-v2 candidate reusing prompt-v1 baseline in `tests/integration/test_run_candidate.py`
- [X] T020 [P] [US1] Add integration test for candidate prompt rendering from override in `tests/integration/test_run_candidate.py`
- [X] T021 [P] [US1] Add trace metadata test for baseline prompt identity and candidate prompt identity in `tests/integration/test_evaluator_observation_metadata.py`
- [X] T022 [P] [US1] Add evaluator payload test preserving baseline output for prompt variants in `tests/integration/test_run_candidate.py`
- [X] T023 [P] [US1] Add CLI validation contract test for prompt-variant project config in `tests/contract/test_cli_validate.py`

### Implementation for User Story 1

- [X] T024 [US1] Update candidate prompt selection to use candidate override when present in `src/evaluator_harness/runner.py`
- [X] T025 [US1] Preserve baseline prompt rendering from project-level task prompt in `src/evaluator_harness/runner.py`
- [X] T026 [US1] Add baseline and candidate prompt identity metadata to candidate run creation in `src/evaluator_harness/runner.py`
- [X] T027 [US1] Add baseline and candidate prompt identity metadata to trace payloads in `src/evaluator_harness/runner.py`
- [X] T028 [US1] Add prompt identity metadata to candidate evaluator payloads in `src/evaluator_harness/runner.py`
- [X] T029 [US1] Add prompt identity metadata to review payload construction in `src/evaluator_harness/langfuse_client.py`
- [X] T030 [US1] Add prompt-v2 candidate example to `configs/projects/rewrite_quality.yaml`
- [X] T031 [US1] Add or update prompt-v2 project prompt file in `prompts/rewrite_quality/task_prompt_v2.md`

**Checkpoint**: User Story 1 is functional. Prompt-v2 candidates can compare against existing prompt-v1 baselines and are traceable in Langfuse metadata.

---

## Phase 4: User Story 2 - Compare Model Parameter Variants (Priority: P2)

**Goal**: Multiple candidates that differ only by generation parameters can compare against the same baseline with distinct parameter metadata.

**Independent Test**: Configure two same-model candidates with different parameters, run both against the same baseline, and confirm each run has distinct parameter identity while sharing the same baseline reference.

### Tests for User Story 2

- [X] T032 [P] [US2] Add integration test for parameter-only variants sharing baseline reference in `tests/integration/test_parameter_variants.py`
- [X] T033 [P] [US2] Add integration test for repeated parameter-variant runs preserving stable variant identity in `tests/integration/test_parameter_variants.py`
- [X] T034 [P] [US2] Add trace metadata test for parameter identity and generation parameter hash in `tests/integration/test_evaluator_observation_metadata.py`
- [X] T035 [P] [US2] Add export test for parameter variant metadata in `tests/unit/test_exports.py`

### Implementation for User Story 2

- [X] T036 [US2] Add generation-parameter-only identity metadata to candidate run creation in `src/evaluator_harness/runner.py`
- [X] T037 [US2] Add parameter identity metadata to trace payloads in `src/evaluator_harness/runner.py`
- [X] T038 [US2] Add parameter identity metadata to candidate evaluator payloads in `src/evaluator_harness/runner.py`
- [X] T039 [US2] Add parameter identity and variant identity columns to exports in `src/evaluator_harness/exports.py`
- [X] T040 [US2] Add parameter variant examples to `configs/projects/rewrite_quality.yaml`

**Checkpoint**: User Story 2 is functional. Parameter variants remain independently comparable and exportable without changing the baseline workflow.

---

## Phase 5: User Story 3 - Compare Mixed Candidate Variants (Priority: P3)

**Goal**: Candidates that combine model, prompt, and parameter changes can run with explicit user confirmation while preserving comparison and review metadata.

**Independent Test**: Configure a candidate that changes multiple axes, verify the CLI prompts and only proceeds on `Y` or `y`, verify `--confirm-mixed-variant` bypasses the prompt, and confirm mixed-variant traces remain evaluator-filterable.

### Tests for User Story 3

- [X] T041 [P] [US3] Add contract test prompting for mixed model and parameter variant in `tests/contract/test_cli_run_candidate.py`
- [X] T042 [P] [US3] Add contract test accepting lowercase `y` for mixed variant confirmation in `tests/contract/test_cli_run_candidate.py`
- [X] T043 [P] [US3] Add contract test cancelling mixed variant when input is not `Y` or `y` in `tests/contract/test_cli_run_candidate.py`
- [X] T044 [P] [US3] Add contract test bypassing mixed variant prompt with `--confirm-mixed-variant` in `tests/contract/test_cli_run_candidate.py`
- [X] T045 [P] [US3] Add integration test detecting changed axes for model, prompt, and params in `tests/integration/test_parameter_variants.py`
- [X] T046 [P] [US3] Add trace metadata test for mixed-variant evaluator filter compatibility in `tests/integration/test_evaluator_observation_metadata.py`

### Implementation for User Story 3

- [X] T047 [US3] Implement mixed-variant changed-axis detection in `src/evaluator_harness/runner.py`
- [X] T048 [US3] Add `--confirm-mixed-variant` option to candidate run command in `src/evaluator_harness/cli.py`
- [X] T049 [US3] Add interactive `Y` or `y` confirmation before mixed candidate execution in `src/evaluator_harness/cli.py`
- [X] T050 [US3] Preserve variant identity and baseline reference metadata for mixed candidates in `src/evaluator_harness/runner.py`

**Checkpoint**: User Story 3 is functional. Mixed variants are allowed only after explicit confirmation or script flag and remain comparable in Langfuse.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, examples, live checks, and consistency verification across all variant types.

- [X] T051 [P] Update candidate variant documentation in `README.md`
- [X] T052 [P] Update candidate variant setup and troubleshooting guidance in `docs/user-guide.md`
- [X] T053 Update 010 quickstart with final command outputs and verification notes in `specs/010-candidate-variants/quickstart.md`
- [X] T054 Verify rewrite-quality evaluator filters remain based on project metadata and `observation_role=model_output` in `configs/projects/rewrite_quality.yaml`
- [X] T055 Run `uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml` and record result in `specs/010-candidate-variants/quickstart.md`
- [X] T056 Run `uv run pytest -p no:cacheprovider` and record result in `specs/010-candidate-variants/quickstart.md`
- [X] T057 Run optional live baseline smoke when credentials are available and record result in `specs/010-candidate-variants/quickstart.md`
- [X] T058 Run optional live prompt/model/parameter variant smoke when credentials are available and record result in `specs/010-candidate-variants/quickstart.md`
- [X] T059 Inspect Langfuse traces for variant metadata, baseline reference, prompt identity, parameter identity, and secret absence; record result in `specs/010-candidate-variants/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks user story implementation.
- **User Story 1 (Phase 3)**: Depends on Foundational; delivers the MVP prompt-variant workflow.
- **User Story 2 (Phase 4)**: Depends on Foundational; can run after or alongside US1 because it focuses on parameter metadata.
- **User Story 3 (Phase 5)**: Depends on Foundational; can run after or alongside US1/US2 but should integrate with their identity helpers.
- **Polish (Phase 6)**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 Compare Prompt Variant Against Existing Baseline**: MVP. Requires shared prompt/variant identity foundation.
- **US2 Compare Model Parameter Variants**: Independent after foundation. Uses shared parameter identity helpers.
- **US3 Compare Mixed Candidate Variants**: Independent after foundation for CLI guardrails, but full mixed prompt detection benefits from US1 prompt identity helpers.

### Within Each User Story

- Tests must be written and observed failing before implementation.
- Config validation changes before runtime prompt rendering.
- Identity helper changes before Langfuse metadata changes.
- Trace/evaluator metadata changes before export and review payload changes.
- Fake integration verification before optional live verification.

## Parallel Opportunities

- Setup fixture tasks T003-T007 can run in parallel.
- Foundational tests T008-T013 can run in parallel.
- US1 tests T019-T023 can run in parallel before implementation.
- US2 tests T032-T035 can run in parallel before implementation.
- US3 tests T041-T046 can run in parallel before implementation.
- Documentation tasks T051-T052 can run in parallel after behavior stabilizes.

## Parallel Example: User Story 1

```text
Task: "Add integration test for prompt-v2 candidate reusing prompt-v1 baseline in tests/integration/test_run_candidate.py"
Task: "Add trace metadata test for baseline prompt identity and candidate prompt identity in tests/integration/test_evaluator_observation_metadata.py"
Task: "Add CLI validation contract test for prompt-variant project config in tests/contract/test_cli_validate.py"
```

## Parallel Example: User Story 2

```text
Task: "Add integration test for parameter-only variants sharing baseline reference in tests/integration/test_parameter_variants.py"
Task: "Add trace metadata test for parameter identity and generation parameter hash in tests/integration/test_evaluator_observation_metadata.py"
Task: "Add export test for parameter variant metadata in tests/unit/test_exports.py"
```

## Parallel Example: User Story 3

```text
Task: "Add contract test prompting for mixed model and parameter variant in tests/contract/test_cli_run_candidate.py"
Task: "Add contract test bypassing mixed variant prompt with --confirm-mixed-variant in tests/contract/test_cli_run_candidate.py"
Task: "Add integration test detecting changed axes for model, prompt, and params in tests/integration/test_parameter_variants.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup fixtures.
2. Complete Phase 2 shared config and identity foundation.
3. Write and fail US1 prompt-variant tests.
4. Implement candidate prompt override rendering and metadata.
5. Validate prompt-v2 candidate against existing prompt-v1 baseline with fake integration tests.

### Incremental Delivery

1. Deliver US1 so prompt variants compare against existing baselines.
2. Deliver US2 so parameter variants have stable identity and exports.
3. Deliver US3 so mixed variants require explicit confirmation and remain traceable.
4. Complete docs, quickstart, default tests, and optional live verification.

### Required Final Verification

```powershell
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
uv run pytest -p no:cacheprovider
```

Optional live verification requires configured Langfuse and provider credentials:

```powershell
$env:RUN_LIVE_TESTS='1'
uv run pytest --no-cov -m live -vv
```

## Notes

- `[P]` tasks touch different files or can be completed without depending on incomplete tasks.
- `[US1]`, `[US2]`, and `[US3]` labels map to the user stories in [spec.md](./spec.md).
- Keep Langfuse as the system of record for comparison and scoring.
- Do not add a local campaign scheduler or dashboard.
- Do not include provider credential values in variant metadata, exports, traces, errors, or docs.
