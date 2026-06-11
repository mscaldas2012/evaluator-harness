# Tasks: Campaign Mode

**Input**: Design documents from `specs/019-campaign-mode/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover success paths, validation failures, provider failures, Langfuse failures, metadata correctness, and CLI exit behavior where applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add test scaffolds and feature fixture locations without changing behavior.

- [X] T001 Create campaign unit test scaffold in `tests/unit/test_campaign.py`
- [X] T002 [P] Create campaign CLI contract test scaffold in `tests/contract/test_cli_campaign.py`
- [X] T003 [P] Create campaign integration test scaffold in `tests/integration/test_campaign_flow.py`
- [X] T004 [P] Add campaign project fixture scaffold in `tests/fixtures/projects/campaign_mode.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add candidate configuration support and shared campaign result structures required by all stories.

**CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundation (REQUIRED)

- [X] T005 [P] Add config tests for `exclude-from-campaign` alias parsing, omitted default false, explicit true/false, and invalid non-boolean values in `tests/unit/test_config.py`
- [X] T006 [P] Add unit tests for campaign candidate selection decisions and skipped reasons in `tests/unit/test_campaign.py`

### Implementation for Foundation

- [X] T007 Add `exclude_from_campaign: bool = False` with YAML alias `exclude-from-campaign` to `ModelConfig` in `src/evaluator_harness/config.py`
- [X] T008 Define `CampaignCandidateSelection`, `CampaignCandidateRun`, and `CampaignRunResult` dataclasses in `src/evaluator_harness/runner.py`
- [X] T009 Implement helper to select campaign candidates and skipped candidates from `ProjectConfig.candidates` in `src/evaluator_harness/runner.py`
- [X] T010 Update `tests/fixtures/projects/campaign_mode.yaml` with one explicit included candidate, one explicitly excluded candidate, and one omitted/default-included candidate

**Checkpoint**: Foundation ready - campaign candidate inclusion can be validated without running experiments.

---

## Phase 3: User Story 1 - Run Full Campaign (Priority: P1) MVP

**Goal**: A user starts one command and gets a fresh baseline, all eligible candidate runs, CSV reports, and one Excel workbook.

**Independent Test**: Use a fake provider/Langfuse setup and fake Excel writer path to run a project with two eligible candidates; verify baseline-first ordering, candidate baseline references, CSV exports, and workbook creation.

### Tests for User Story 1 (REQUIRED)

- [X] T011 [P] [US1] Add unit test for baseline-first campaign orchestration and candidate baseline selector usage in `tests/unit/test_campaign.py`
- [X] T012 [P] [US1] Add integration test for campaign success with fake Langfuse/provider, CSV exports, and Excel report orchestration in `tests/integration/test_campaign_flow.py`
- [X] T013 [P] [US1] Add contract test for `run_experiment.py campaign --project ...` success output in `tests/contract/test_cli_campaign.py`
- [X] T014 [P] [US1] Add unit test that campaign passes `skip_sync` and `skip_human_review` through to baseline and candidate runs in `tests/unit/test_campaign.py`
- [X] T015 [P] [US1] Add unit test that campaign supports workbook overwrite behavior via `overwrite=True` in `tests/unit/test_campaign.py`

### Implementation for User Story 1

- [X] T016 [US1] Implement `ExperimentRunner.campaign()` baseline-first orchestration in `src/evaluator_harness/runner.py`
- [X] T017 [US1] Call existing candidate `run()` path with the fresh baseline run ID for every included candidate in `src/evaluator_harness/runner.py`
- [X] T018 [US1] Export campaign baseline and candidate CSV reports through existing `export()` when reporting is enabled in `src/evaluator_harness/runner.py`
- [X] T019 [US1] Invoke `create_excel_report()` with `reports/<project-name>` and campaign baseline run ID after attempted runs in `src/evaluator_harness/runner.py`
- [X] T020 [US1] Add `campaign` CLI command with `--project`, `--skip-sync`, `--skip-human-review`, `--no-report`, `--overwrite`, and `--confirm-mixed-variant` options in `src/evaluator_harness/cli.py`
- [X] T021 [US1] Print campaign success output with baseline run ID, candidate run IDs, report paths, Excel report path, and Excel warnings in `src/evaluator_harness/cli.py`

**Checkpoint**: User Story 1 can run an end-to-end campaign with eligible candidates and produce CSV plus Excel artifacts.

---

## Phase 4: User Story 2 - Exclude Candidates From Campaign (Priority: P2)

**Goal**: Project YAML controls campaign participation so candidates run unless `exclude-from-campaign: true` is set.

**Independent Test**: Use a project with included, explicit-excluded, and default-included candidates; verify only explicitly excluded candidates are skipped.

### Tests for User Story 2 (REQUIRED)

- [X] T022 [P] [US2] Add integration test that all candidates except `exclude-from-campaign: true` candidates run in `tests/integration/test_campaign_flow.py`
- [X] T023 [P] [US2] Add contract test that skipped candidates and reasons are printed in campaign CLI output in `tests/contract/test_cli_campaign.py`
- [X] T024 [P] [US2] Add contract test that no eligible candidates exits without baseline run and prints `campaign: skipped` in `tests/contract/test_cli_campaign.py`

### Implementation for User Story 2

- [X] T025 [US2] Wire skipped candidate selections into `CampaignRunResult.skipped_candidates` in `src/evaluator_harness/runner.py`
- [X] T026 [US2] Prevent baseline execution and return a skipped campaign result when no candidates are eligible in `src/evaluator_harness/runner.py`
- [X] T027 [US2] Print skipped candidate names and reasons in campaign CLI output in `src/evaluator_harness/cli.py`
- [X] T028 [US2] Update `docs/user-guide.md` with candidate `exclude-from-campaign` examples and default-included behavior

**Checkpoint**: User Story 2 can be validated independently by campaign candidate selection and no-eligible-candidate behavior.

---

## Phase 5: User Story 3 - Inspect Campaign Summary (Priority: P3)

**Goal**: The command summary identifies baseline, included candidates, skipped candidates, failed candidates, reports, workbook, and warnings.

**Independent Test**: Simulate mixed campaign outcomes and assert CLI output includes every candidate status and artifact path.

### Tests for User Story 3 (REQUIRED)

- [X] T029 [P] [US3] Add unit test that candidate failures are captured without discarding successful campaign outputs in `tests/unit/test_campaign.py`
- [X] T030 [P] [US3] Add contract test for `campaign: completed-with-failures`, failed candidate messages, successful run IDs, and report paths in `tests/contract/test_cli_campaign.py`
- [X] T031 [P] [US3] Add unit test that Excel creation failure records a warning while preserving CSV report paths in `tests/unit/test_campaign.py`
- [X] T032 [P] [US3] Add contract test that campaign exits non-zero when any included candidate fails after baseline success in `tests/contract/test_cli_campaign.py`

### Implementation for User Story 3

- [X] T033 [US3] Catch per-candidate `HarnessError` failures inside campaign orchestration and append failed `CampaignCandidateRun` entries in `src/evaluator_harness/runner.py`
- [X] T034 [US3] Preserve successful baseline/candidate run IDs and CSV reports when later candidates or Excel creation fail in `src/evaluator_harness/runner.py`
- [X] T035 [US3] Print `campaign: completed-with-failures` and failed candidate messages in campaign CLI output in `src/evaluator_harness/cli.py`
- [X] T036 [US3] Set campaign CLI exit code to non-zero when baseline fails or any included candidate fails in `src/evaluator_harness/cli.py`
- [X] T037 [US3] Print Excel report warnings and Excel creation warning messages in campaign CLI output in `src/evaluator_harness/cli.py`

**Checkpoint**: User Story 3 produces a complete audit summary for successful, skipped, and failed campaign work.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, examples, regression coverage, and cleanup across all stories.

- [X] T038 [P] Update `specs/019-campaign-mode/quickstart.md` if implementation command names, options, or output differ from the plan
- [X] T039 [P] Update `configs/projects/rewrite_quality.yaml` to mark dry-run/test candidates with `exclude-from-campaign: true`
- [X] T040 [P] Update `configs/projects/gso.yaml`, `configs/projects/dfe.yaml`, and scenario DFE project YAMLs with explicit campaign exclusion choices in `configs/projects/`
- [X] T041 Run focused campaign tests with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_campaign.py tests/contract/test_cli_campaign.py tests/integration/test_campaign_flow.py tests/unit/test_config.py`
- [X] T042 Run related CLI/report regressions with `uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_run_baseline.py tests/contract/test_cli_run_candidate.py tests/contract/test_cli_export.py tests/unit/test_exports.py tests/unit/test_excel_reports.py tests/contract/test_cli_excel_comparison.py`
- [X] T043 Run quickstart smoke command in dry-run/fake-backed mode and record observed output in `specs/019-campaign-mode/quickstart.md` if needed
- [X] T044 Remove unnecessary helper abstractions or duplicated campaign output formatting from `src/evaluator_harness/runner.py` and `src/evaluator_harness/cli.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational and delivers the campaign MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational and integrates with campaign orchestration from US1.
- **User Story 3 (Phase 5)**: Depends on US1 campaign orchestration and US2 skipped-candidate result shape.
- **Polish (Phase 6)**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 Run Full Campaign**: MVP and required before CLI campaign command is useful.
- **US2 Exclude Candidates From Campaign**: Depends on foundational config flag and campaign result shape; can be tested through selection before full campaign implementation.
- **US3 Inspect Campaign Summary**: Depends on campaign result structures and CLI output from US1/US2.

### Within Each User Story

- Tests MUST be written and fail before implementation.
- Config and dataclasses before runner orchestration.
- Runner orchestration before CLI output.
- CSV/Excel report integration after baseline and candidate run sequencing.
- Story complete before moving to the next priority unless only parallel test scaffolds are being prepared.

### Parallel Opportunities

- T002, T003, and T004 can run in parallel after T001.
- T005 and T006 can run in parallel after setup.
- T011 through T015 can run in parallel after foundational tasks.
- T022 through T024 can run in parallel after foundational tasks.
- T029 through T032 can run in parallel after campaign result structures exist.
- T038 through T040 can run in parallel after behavior stabilizes.

---

## Parallel Example: User Story 1

```text
Task: "Add unit test for baseline-first campaign orchestration and candidate baseline selector usage in tests/unit/test_campaign.py"
Task: "Add integration test for campaign success with fake Langfuse/provider, CSV exports, and Excel report orchestration in tests/integration/test_campaign.py"
Task: "Add contract test for run_experiment.py campaign --project ... success output in tests/contract/test_cli_campaign.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational config flag, campaign dataclasses, and selection helper.
3. Complete Phase 3 campaign baseline-first orchestration, CSV exports, Excel report creation, and CLI command.
4. Stop and validate the campaign MVP with the focused campaign tests.

### Incremental Delivery

1. US1: Run baseline and all non-excluded candidates with reports.
2. US2: Harden opt-out candidate selection and no-eligible-candidate behavior.
3. US3: Add complete summary and partial-failure reporting.
4. Polish: Update project YAML examples/docs and run regression suites.

### Risk Controls

- Reuse existing `run()`, `export()`, and `create_excel_report()` paths to avoid metadata drift.
- Keep campaign execution sequential to avoid provider rate-limit and partial-failure complexity.
- Do not introduce campaign persistence; rely on Langfuse and local report files as existing system-of-record surfaces.
- Use fake-backed tests for most coverage; reserve live/provider tests for existing live test patterns.
