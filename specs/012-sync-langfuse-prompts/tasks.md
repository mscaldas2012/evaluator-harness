# Tasks: Sync Langfuse Prompts

**Input**: Design documents from `/specs/012-sync-langfuse-prompts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation
tasks and cover success paths, validation failures, Langfuse failures, metadata
correctness, and CLI exit behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature files and reusable fixtures.

- [x] T001 Create prompt binding directory placeholder in configs/langfuse/prompt_bindings/.gitkeep
- [x] T002 [P] Add DFE prompt sync fixture project in tests/fixtures/projects/valid_prompt_sync.yaml
- [x] T003 [P] Add prompt sync fixture prompts in tests/fixtures/prompts/prompt_sync_task.md and tests/fixtures/prompts/prompt_sync_judge.md
- [x] T004 [P] Add fake Langfuse prompt storage helpers to tests fixtures in tests/fixtures/fake_langfuse.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core prompt artifact and binding primitives that all user stories require.

**CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational Primitives

- [x] T005 [P] Add prompt artifact discovery unit tests in tests/unit/test_prompt_sync.py
- [x] T006 [P] Add prompt binding load/save/validation unit tests in tests/unit/test_prompt_bindings.py
- [x] T007 [P] Add Langfuse prompt client fake behavior tests in tests/unit/test_prompt_sync.py

### Implementation for Foundational Primitives

- [x] T008 Define PromptArtifact, PromptBindingRecord, PromptSyncStatus, and PromptSyncReport models in src/evaluator_harness/prompt_sync.py
- [x] T009 Implement prompt artifact discovery from ProjectConfig task_prompt and evaluator prompt_path fields in src/evaluator_harness/prompt_sync.py
- [x] T010 Implement managed prompt naming, labels, tags, and content identity helpers in src/evaluator_harness/prompt_sync.py
- [x] T011 Implement prompt binding load/save/validation helpers for configs/langfuse/prompt_bindings/<project>.yaml in src/evaluator_harness/prompt_sync.py
- [x] T012 Add fake and live Langfuse prompt list/get/create methods to src/evaluator_harness/langfuse_client.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Publish Project Prompts (Priority: P1) MVP

**Goal**: Users can publish a project's task and evaluator prompts to Langfuse with stable names, strict prompt version labels, and duplicate protection.

**Independent Test**: Sync prompts for one configured project and confirm every configured prompt has a status, managed name, content identity, and Langfuse prompt reference when created or reused.

### Tests for User Story 1

- [x] T013 [P] [US1] Add contract test for sync-prompts CLI apply output in tests/contract/test_cli_sync_prompts.py
- [x] T014 [P] [US1] Add unit test for creating missing text and chat prompt versions in tests/unit/test_prompt_sync.py
- [x] T015 [P] [US1] Add unit test for reusing unchanged prompt versions without duplicates in tests/unit/test_prompt_sync.py
- [x] T016 [P] [US1] Add unit test for changed content under same prompt_version conflict in tests/unit/test_prompt_sync.py

### Implementation for User Story 1

- [x] T017 [US1] Implement prompt sync dry-run/apply orchestration and per-prompt statuses in src/evaluator_harness/prompt_sync.py
- [x] T018 [US1] Add ExperimentRunner.sync_prompts(project_path, dry_run=False) in src/evaluator_harness/runner.py
- [x] T019 [US1] Add sync-prompts CLI command with --project and --dry-run options in src/evaluator_harness/cli.py
- [x] T020 [US1] Save prompt binding records after successful apply sync in src/evaluator_harness/prompt_sync.py
- [x] T021 [US1] Add progress reporting across prompt artifacts during dry-run and apply in src/evaluator_harness/prompt_sync.py

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Preserve Local Source of Truth (Priority: P1)

**Goal**: Existing validation, run, evaluator setup, export, and review workflows continue to render from repository prompt files and do not require synced Langfuse prompts.

**Independent Test**: Run existing local workflows with no prompt binding file and confirm local prompt rendering and existing outputs are unchanged.

### Tests for User Story 2

- [x] T022 [P] [US2] Add unit test proving validate_project does not require prompt bindings in tests/unit/test_prompt_provenance.py
- [x] T023 [P] [US2] Add integration test proving baseline run works without prompt bindings in tests/integration/test_run_baseline.py
- [x] T024 [P] [US2] Add unit test proving remote prompt content never replaces local prompt content in tests/unit/test_prompt_provenance.py

### Implementation for User Story 2

- [x] T025 [US2] Ensure prompt binding lookup is optional and non-blocking for run paths in src/evaluator_harness/runner.py
- [x] T026 [US2] Keep ModelRequest prompt rendering sourced from local RenderedPrompt only in src/evaluator_harness/runner.py
- [x] T027 [US2] Add clear error boundaries so sync-prompts failures do not affect validate/run/export commands in src/evaluator_harness/cli.py

**Checkpoint**: User Story 2 preserves current local-first behavior independently.

---

## Phase 5: User Story 3 - Trace Prompt Provenance (Priority: P2)

**Goal**: New runs include local prompt identity metadata and, when available, synced Langfuse prompt references for task and evaluator prompt artifacts.

**Independent Test**: Run a project with and without prompt bindings and confirm traces contain local prompt identity always and Langfuse prompt references only when matching bindings exist.

### Tests for User Story 3

- [x] T028 [P] [US3] Add unit test for local task prompt provenance metadata in tests/unit/test_prompt_provenance.py
- [x] T029 [P] [US3] Add unit test for synced Langfuse prompt reference metadata when binding matches content in tests/unit/test_prompt_provenance.py
- [x] T030 [P] [US3] Add unit test for evaluator prompt provenance in judge evaluator setup payloads in tests/unit/test_judge_setup_planner.py
- [x] T031 [P] [US3] Add export field test for prompt artifact references in tests/unit/test_exports.py

### Implementation for User Story 3

- [x] T032 [US3] Add prompt provenance metadata builder in src/evaluator_harness/prompt_sync.py
- [x] T033 [US3] Attach task prompt provenance metadata to baseline and candidate trace metadata in src/evaluator_harness/runner.py
- [x] T034 [US3] Attach evaluator prompt provenance metadata to judge evaluator setup payloads in src/evaluator_harness/langfuse_evaluator_setup.py
- [x] T035 [US3] Include prompt artifact reference columns in CSV exports when metadata is present in src/evaluator_harness/exports.py

**Checkpoint**: User Story 3 makes prompt provenance visible in Langfuse metadata and exports.

---

## Phase 6: User Story 4 - Dry-Run Prompt Sync State (Priority: P3)

**Goal**: Users can preview prompt sync actions and detect missing, matching, changed, and conflicting prompt artifacts without mutating Langfuse or local bindings.

**Independent Test**: Run dry-run against fixture states for missing, matching, changed, user-owned conflict, and Langfuse failure and confirm statuses and remediation text.

### Tests for User Story 4

- [x] T036 [P] [US4] Add unit tests for dry-run statuses missing, matching, changed, conflict, and failed in tests/unit/test_prompt_sync.py
- [x] T037 [P] [US4] Add contract test for sync-prompts --dry-run CLI output and non-mutating behavior in tests/contract/test_cli_sync_prompts.py
- [x] T038 [P] [US4] Add unit test for actionable remediation messages in tests/unit/test_prompt_sync.py

### Implementation for User Story 4

- [x] T039 [US4] Implement dry-run prompt sync mode without Langfuse create calls or binding writes in src/evaluator_harness/prompt_sync.py
- [x] T040 [US4] Implement conflict detection for user-owned remote prompt names and same-version changed content in src/evaluator_harness/prompt_sync.py
- [x] T041 [US4] Print dry-run summaries, per-prompt statuses, and remediation text in src/evaluator_harness/cli.py

**Checkpoint**: User Story 4 provides safe preview and dry-run behavior.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, live smoke coverage, and final verification.

- [x] T042 [P] Add optional live Langfuse prompt sync smoke test in tests/integration/live/test_live_sync_prompts_smoke.py
- [x] T043 [P] Document sync-prompts workflow and strict prompt_version behavior in README.md
- [x] T044 [P] Update quickstart validation notes in specs/012-sync-langfuse-prompts/quickstart.md if implementation behavior differs
- [x] T045 Run focused tests with uv run pytest --no-cov -p no:cacheprovider tests/unit/test_prompt_sync.py tests/unit/test_prompt_bindings.py tests/unit/test_prompt_provenance.py tests/contract/test_cli_sync_prompts.py
- [x] T046 Run regression tests with uv run pytest --no-cov -p no:cacheprovider tests/unit/test_exports.py tests/unit/test_judge_setup_planner.py tests/integration/test_run_baseline.py
- [x] T047 Run project validation smoke with uv run python run_experiment.py validate --project configs/projects/dfe.yaml

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational and is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational; can run in parallel with US1 after shared primitives exist.
- **User Story 3 (Phase 5)**: Depends on Foundational and benefits from US1 binding records, but local provenance can be implemented independently.
- **User Story 4 (Phase 6)**: Depends on Foundational and can run in parallel with US1 because it uses the same orchestration status model.
- **Polish (Phase 7)**: Depends on selected stories being complete.

### User Story Dependencies

- **US1 Publish Project Prompts**: MVP; no dependency on other user stories after Foundational.
- **US2 Preserve Local Source of Truth**: No dependency on US1 after Foundational.
- **US3 Trace Prompt Provenance**: Local provenance has no dependency on US1; synced Langfuse references require binding lookup from Foundational/US1.
- **US4 Dry-Run Prompt Sync State**: No dependency on US1 after Foundational, but shares sync status and conflict logic.

### Parallel Opportunities

- T002, T003, and T004 can run in parallel.
- T005, T006, and T007 can run in parallel.
- Tests inside each user story marked [P] can be written in parallel.
- US2 and US4 can proceed in parallel after Phase 2.
- T042, T043, and T044 can run in parallel after implementation stabilizes.

---

## Parallel Example: User Story 1

```text
Task: "T013 [US1] Add contract test for sync-prompts CLI apply output in tests/contract/test_cli_sync_prompts.py"
Task: "T014 [US1] Add unit test for creating missing text and chat prompt versions in tests/unit/test_prompt_sync.py"
Task: "T015 [US1] Add unit test for reusing unchanged prompt versions without duplicates in tests/unit/test_prompt_sync.py"
Task: "T016 [US1] Add unit test for changed content under same prompt_version conflict in tests/unit/test_prompt_sync.py"
```

## Parallel Example: User Story 3

```text
Task: "T028 [US3] Add unit test for local task prompt provenance metadata in tests/unit/test_prompt_provenance.py"
Task: "T029 [US3] Add unit test for synced Langfuse prompt reference metadata when binding matches content in tests/unit/test_prompt_provenance.py"
Task: "T031 [US3] Add export field test for prompt artifact references in tests/unit/test_exports.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational prompt artifact, binding, and Langfuse prompt helpers.
3. Complete Phase 3 User Story 1.
4. Stop and validate sync-prompts dry-run/apply behavior with unit and contract tests.

### Incremental Delivery

1. Foundation ready: artifact discovery, binding store, Langfuse prompt helpers.
2. US1: publish and reuse project prompts.
3. US2: prove existing local-first workflows remain independent of prompt sync.
4. US3: enrich traces, judge setup, and exports with prompt provenance.
5. US4: complete conflict-focused dry-run workflows.
6. Polish: live smoke, docs, and regression tests.

### Parallel Team Strategy

After Phase 2, one developer can finish US1 apply behavior, another can harden
US2 local-source guarantees, and another can implement US4 dry-run conflict
coverage. US3 should coordinate with US1 only for the final synced-reference
metadata shape.

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps task to a specific user story for traceability.
- Tests should be written before implementation tasks in each phase.
- Keep prompt sync optional and avoid making Langfuse prompt state a runtime dependency.
- Preserve strict `prompt_version` semantics: changed content requires a version bump.
