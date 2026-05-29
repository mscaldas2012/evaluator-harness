# Tasks: Prompt Roles and Variables

**Input**: Design documents from `/specs/011-prompt-roles-variables/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover success paths, validation failures, provider failures, metadata correctness, and CLI exit behavior where applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish fixtures and shared test scaffolding for prompt role work.

- [X] T001 [P] Add role-based prompt fixture with `## role: system`, `## role: user`, and custom role sections in `tests/fixtures/prompts/role_based_task_prompt.md`
- [X] T002 [P] Add malformed role prompt fixtures for unassigned content, empty role heading, and unmatched braces in `tests/fixtures/prompts/`
- [X] T003 [P] Add dataset fixture with `input`, `ground_truth`, and optional empty values in `tests/fixtures/datasets/prompt_variables.csv`
- [X] T004 [P] Add valid role-based project fixture in `tests/fixtures/projects/valid_role_prompt_project.yaml`
- [X] T005 [P] Add invalid role-based project fixtures for missing dataset column and unsupported provider roles in `tests/fixtures/projects/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared prompt parsing and rendering primitives required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational Prompt Primitives

- [X] T006 [P] Add unit tests for parsing legacy single-text prompt files in `tests/unit/test_prompt_roles.py`
- [X] T007 [P] Add unit tests for parsing `## role: <role-label>` Markdown message sections in `tests/unit/test_prompt_roles.py`
- [X] T008 [P] Add unit tests for malformed role headings and unassigned role content in `tests/unit/test_prompt_roles.py`
- [X] T009 [P] Add unit tests for `{dataset.<field>}` placeholder extraction and malformed brace syntax in `tests/unit/test_prompt_roles.py`
- [X] T010 [P] Add unit tests for prompt identity shape, role order, and variable references in `tests/unit/test_prompt_roles.py`

### Implementation for Foundational Prompt Primitives

- [X] T011 Add PromptDefinition, PromptMessage, DatasetVariableReference, RenderedPrompt, and parser functions in `src/evaluator_harness/prompts.py`
- [X] T012 Implement Markdown role heading parsing and legacy single-text detection in `src/evaluator_harness/prompts.py`
- [X] T013 Implement dataset placeholder extraction and malformed brace validation in `src/evaluator_harness/prompts.py`
- [X] T014 Implement RenderedPrompt display text and stable hashing helpers in `src/evaluator_harness/prompts.py`
- [X] T015 Update prompt_identity and prompt_identity_for_model to include prompt shape, roles, and variable references in `src/evaluator_harness/runner.py`

**Checkpoint**: Prompt files can be parsed and identified independently of project validation or provider calls.

---

## Phase 3: User Story 1 - Define Multi-Role Task Prompts (Priority: P1) MVP

**Goal**: Project authors can define ordered role-labeled task prompts in Markdown and preserve message order and role labels through validation, rendering, and provider request preparation.

**Independent Test**: Validate and run a project using a role-based task prompt and confirm ordered roles are preserved in the rendered prompt payload.

### Tests for User Story 1

- [X] T016 [P] [US1] Add contract test that CLI validate accepts a role-based prompt project in `tests/contract/test_cli_validate.py`
- [X] T017 [P] [US1] Add integration test for baseline run preserving role order in rendered provider request in `tests/integration/test_run_baseline.py`
- [X] T018 [P] [US1] Add provider unit tests for OpenAI-compatible REST role message payloads in `tests/unit/test_openai_compatible_provider.py`
- [X] T019 [P] [US1] Add provider unit tests for OpenAI-compatible SDK role message payloads in `tests/unit/test_openai_compatible_provider.py`
- [X] T020 [P] [US1] Add dry-run provider unit test for deterministic hashing of role messages in `tests/unit/test_dry_run_provider.py`

### Implementation for User Story 1

- [X] T021 [US1] Extend ModelRequest with optional rendered prompt payload while preserving legacy prompt text in `src/evaluator_harness/providers/base.py`
- [X] T022 [US1] Replace runner single-string prompt rendering with PromptDefinition rendering in baseline flow in `src/evaluator_harness/runner.py`
- [X] T023 [US1] Update OpenAI-compatible completion payload construction to send role messages when rendered prompt shape is messages in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T024 [US1] Update DryRunProvider hashing and output generation to include rendered role messages when present in `src/evaluator_harness/providers/dry_run.py`
- [X] T025 [US1] Add provider role capability validation for OpenAI-compatible, dry-run, and unsupported role-message providers in `src/evaluator_harness/providers/base.py`
- [X] T026 [US1] Integrate provider role capability validation before baseline model calls in `src/evaluator_harness/runner.py`
- [X] T027 [US1] Preserve legacy single-text prompt behavior in baseline flow in `src/evaluator_harness/runner.py`

**Checkpoint**: User Story 1 is complete when role-based baseline prompts validate, render as ordered messages, and OpenAI-compatible providers receive message payloads.

---

## Phase 4: User Story 2 - Substitute Dataset Variables in Prompts (Priority: P1)

**Goal**: Project authors can use `{dataset.<field>}` placeholders in any prompt message, with column validation and deterministic row rendering.

**Independent Test**: Render a role-based prompt containing `{dataset.input}` and another dataset column for a known dataset row and confirm all placeholders are replaced correctly.

### Tests for User Story 2

- [X] T028 [P] [US2] Add unit tests for rendering `{dataset.input}` and repeated placeholders in `tests/unit/test_prompt_roles.py`
- [X] T029 [P] [US2] Add unit tests for empty row values rendering as empty strings in `tests/unit/test_prompt_roles.py`
- [X] T030 [P] [US2] Add unit tests proving braces inside dataset values are literal data in `tests/unit/test_prompt_roles.py`
- [X] T031 [P] [US2] Add contract test rejecting `{dataset.missing_field}` during CLI validate in `tests/contract/test_cli_validate.py`
- [X] T032 [P] [US2] Add integration test for candidate run rendering dataset variables in role messages in `tests/integration/test_run_candidate.py`

### Implementation for User Story 2

- [X] T033 [US2] Implement dataset column validation for prompt variable references in `src/evaluator_harness/prompts.py`
- [X] T034 [US2] Update project validation to validate project and candidate prompt variables against selected dataset columns in `src/evaluator_harness/config.py`
- [X] T035 [US2] Update runner dataset item rendering to pass full dataset row context instead of only `input` in `src/evaluator_harness/runner.py`
- [X] T036 [US2] Implement row rendering for legacy text and role message prompts with empty string handling in `src/evaluator_harness/prompts.py`
- [X] T037 [US2] Preserve existing `{{input}}` legacy rendering behavior while adding `{dataset.input}` support in `src/evaluator_harness/runner.py`

**Checkpoint**: User Story 2 is complete when dataset placeholders validate against columns and render correctly for baseline and candidate runs.

---

## Phase 5: User Story 3 - Validate Invalid Variables and Role Labels (Priority: P2)

**Goal**: Project authors receive clear validation errors for malformed role labels, malformed placeholders, unavailable dataset columns, and provider role incompatibility before live model calls.

**Independent Test**: Run CLI validation against invalid fixtures and confirm failures name the prompt path, problematic role or variable, and provider where applicable.

### Tests for User Story 3

- [X] T038 [P] [US3] Add contract tests for malformed role heading and unassigned content CLI failures in `tests/contract/test_prompt_file_format.py`
- [X] T039 [P] [US3] Add contract test for unsupported provider role labels failing before model calls in `tests/contract/test_prompt_file_format.py`
- [X] T040 [P] [US3] Add unit tests for provider role capability error messages in `tests/unit/test_provider_role_support.py`
- [X] T041 [P] [US3] Add integration test proving unsupported role validation prevents provider.generate calls in `tests/integration/test_run_baseline.py`

### Implementation for User Story 3

- [X] T042 [US3] Add ConfigError messages for malformed role files and placeholders with prompt path context in `src/evaluator_harness/prompts.py`
- [X] T043 [US3] Add provider capability declarations and unsupported role reporting in `src/evaluator_harness/providers/base.py`
- [X] T044 [US3] Wire provider role validation into candidate flow before provider.generate in `src/evaluator_harness/runner.py`
- [X] T045 [US3] Update CLI validation flow to surface prompt parsing and provider role validation errors in `src/evaluator_harness/cli.py`
- [X] T046 [US3] Add invalid fixture documentation comments or names for role and variable failures in `tests/fixtures/projects/`

**Checkpoint**: User Story 3 is complete when invalid role/variable/provider cases fail early with actionable CLI errors.

---

## Phase 6: User Story 4 - Use Role and Variable Metadata in Evaluations (Priority: P3)

**Goal**: Langfuse traces, exports, evaluator payloads, and review payloads expose enough prompt shape metadata to compare role-based and single-text runs.

**Independent Test**: Run a fake baseline or candidate with role-based prompts and confirm trace metadata and CSV exports identify prompt shape, ordered roles, prompt identity, and dataset variable references.

### Tests for User Story 4

- [X] T047 [P] [US4] Add integration test for trace metadata prompt_shape and prompt_roles in `tests/integration/test_evaluator_observation_metadata.py`
- [X] T048 [P] [US4] Add integration test for evaluator payload prompt identity with role messages in `tests/integration/test_run_candidate.py`
- [X] T049 [P] [US4] Add unit test for export rows containing prompt shape and roles in `tests/unit/test_exports.py`
- [X] T050 [P] [US4] Add unit test for annotation queue payload prompt metadata in `tests/unit/test_annotation_queue_payloads.py`

### Implementation for User Story 4

- [X] T051 [US4] Add prompt_shape, prompt_roles, and variable reference metadata to run trace metadata in `src/evaluator_harness/runner.py`
- [X] T052 [US4] Add prompt shape and role metadata to evaluator payload construction in `src/evaluator_harness/runner.py`
- [X] T053 [US4] Add prompt metadata to annotation queue payloads in `src/evaluator_harness/runner.py`
- [X] T054 [US4] Extend export field list and row mapping with prompt shape and roles in `src/evaluator_harness/exports.py`
- [X] T055 [US4] Ensure baseline_prompt_identity and candidate_prompt_identity include role-aware fields in `src/evaluator_harness/runner.py`

**Checkpoint**: User Story 4 is complete when prompt role metadata is visible in traces, evaluator payloads, review payloads, and exports.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, examples, full-suite validation, and cleanup.

- [X] T056 [P] Add user guide section for role-based prompt Markdown files and `{dataset.<field>}` variables in `docs/user-guide.md`
- [X] T057 [P] Add role-based DFE prompt example using `## role: <role-label>` and `{dataset.input}` in `prompts/dfe/task_prompt.md`
- [X] T058 [P] Add quickstart fixture project or update rewrite-quality example for role prompt validation in `configs/projects/rewrite_quality.yaml`
- [X] T059 [P] Update prompt role quickstart examples if implementation decisions differ from plan in `specs/011-prompt-roles-variables/quickstart.md`
- [X] T060 Run focused prompt role test suite with `uv run pytest -p no:cacheprovider tests/unit/test_prompt_roles.py tests/unit/test_provider_role_support.py tests/contract/test_prompt_file_format.py`
- [X] T061 Run integration and export coverage with `uv run pytest -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py tests/integration/test_evaluator_observation_metadata.py tests/unit/test_exports.py`
- [ ] T062 Run default suite with `uv run pytest -p no:cacheprovider`
- [X] T063 Review prompt role implementation for unnecessary abstractions and keep local state limited to existing files in `src/evaluator_harness/prompts.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational; MVP scope.
- **User Story 2 (Phase 4)**: Depends on Foundational and can be developed alongside US1 after shared rendering interfaces are stable.
- **User Story 3 (Phase 5)**: Depends on Foundational and provider capability shape from US1.
- **User Story 4 (Phase 6)**: Depends on US1 and US2 rendered prompt metadata.
- **Polish (Phase 7)**: Depends on selected user stories being complete.

### User Story Dependencies

- **US1 Define Multi-Role Task Prompts**: No dependency on other stories after Foundation.
- **US2 Substitute Dataset Variables in Prompts**: No dependency on US3 or US4 after Foundation; integrates with US1 rendering payloads.
- **US3 Validate Invalid Variables and Role Labels**: Depends on parser and provider capability primitives; can be completed before US4.
- **US4 Use Role and Variable Metadata in Evaluations**: Depends on rendered prompt and identity data from US1 and US2.

### Within Each User Story

- Write tests first and confirm they fail.
- Implement parser/model changes before runner/provider integration.
- Implement provider/runtime changes before integration tests are expected to pass.
- Complete story checkpoint before moving to broader polish.

---

## Parallel Opportunities

- Setup fixture tasks T001-T005 can run in parallel.
- Foundational test tasks T006-T010 can run in parallel before shared implementation begins.
- US1 provider tests T018-T020 can run in parallel with CLI/integration tests T016-T017.
- US2 rendering tests T028-T030 can run in parallel with CLI/integration tests T031-T032.
- US3 contract and unit tests T038-T040 can run in parallel.
- US4 metadata tests T047-T050 can run in parallel.
- Documentation and example tasks T056-T059 can run in parallel after behavior stabilizes.

## Parallel Example: User Story 1

```text
Task: "T016 [US1] Add contract test that CLI validate accepts a role-based prompt project in tests/contract/test_cli_validate.py"
Task: "T018 [US1] Add provider unit tests for OpenAI-compatible REST role message payloads in tests/unit/test_openai_compatible_provider.py"
Task: "T020 [US1] Add dry-run provider unit test for deterministic hashing of role messages in tests/unit/test_dry_run_provider.py"
```

## Parallel Example: User Story 2

```text
Task: "T028 [US2] Add unit tests for rendering {dataset.input} and repeated placeholders in tests/unit/test_prompt_roles.py"
Task: "T031 [US2] Add contract test rejecting {dataset.missing_field} during CLI validate in tests/contract/test_cli_validate.py"
Task: "T032 [US2] Add integration test for candidate run rendering dataset variables in role messages in tests/integration/test_run_candidate.py"
```

## Parallel Example: User Story 4

```text
Task: "T047 [US4] Add integration test for trace metadata prompt_shape and prompt_roles in tests/integration/test_evaluator_observation_metadata.py"
Task: "T049 [US4] Add unit test for export rows containing prompt shape and roles in tests/unit/test_exports.py"
Task: "T050 [US4] Add unit test for annotation queue payload prompt metadata in tests/unit/test_annotation_queue_payloads.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 setup fixtures.
2. Complete Phase 2 prompt parser and identity foundation.
3. Complete Phase 3 User Story 1 for role-based prompt execution.
4. Stop and validate with focused US1 tests before expanding variable validation and metadata.

### Incremental Delivery

1. Deliver US1 to support role-based prompt structure.
2. Deliver US2 to make role prompts dataset-aware with `{dataset.<field>}`.
3. Deliver US3 to harden validation and provider failure behavior.
4. Deliver US4 to complete metadata, exports, evaluator payloads, and review payloads.
5. Finish docs, examples, and full-suite validation.

### Validation Commands

```powershell
uv run pytest -p no:cacheprovider tests/unit/test_prompt_roles.py tests/unit/test_provider_role_support.py tests/contract/test_prompt_file_format.py
uv run pytest -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py tests/integration/test_evaluator_observation_metadata.py tests/unit/test_exports.py
uv run pytest -p no:cacheprovider
```

## Notes

- [P] tasks touch different files or isolated fixtures and can run in parallel.
- [US1]-[US4] labels map to the user stories in [spec.md](./spec.md).
- Do not add provider role mapping in this feature; unsupported exact roles fail before model calls.
- Do not add local databases, services, prompt registries, or dashboards.
