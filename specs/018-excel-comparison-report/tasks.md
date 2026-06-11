# Tasks: Excel Comparison Report

**Input**: Design documents from `specs/018-excel-comparison-report/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover success paths, validation failures, metadata correctness, workbook adapter behavior, and CLI exit behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add dependencies and module placeholders required by all stories.

- [X] T001 Add Windows Excel automation dependency and any platform marker notes in `pyproject.toml`
- [X] T002 Create Excel report module scaffold in `src/evaluator_harness/excel_reports.py`
- [X] T003 [P] Create unit test scaffold in `tests/unit/test_excel_reports.py`
- [X] T004 [P] Create CLI contract test scaffold in `tests/contract/test_cli_excel_comparison.py`
- [X] T005 [P] Create workbook integration test scaffold in `tests/integration/test_excel_comparison_workbook.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define core data structures, errors, and adapter boundaries that all user stories use.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Define dataclasses or typed result objects for `BaselineRunSelection`, `CsvReportInput`, `RunSummary`, `CombinedReportRow`, `ScoreObservation`, and `WorkbookOutput` in `src/evaluator_harness/excel_reports.py`
- [X] T007 Define file-specific validation error classes or reusable error helpers in `src/evaluator_harness/excel_reports.py`
- [X] T008 Define an `ExcelWorkbookWriter` protocol/interface and a fake writer test helper in `src/evaluator_harness/excel_reports.py` and `tests/unit/test_excel_reports.py`
- [X] T009 Implement default output path derivation and overwrite validation in `src/evaluator_harness/excel_reports.py`
- [X] T010 [P] Add unit tests for blank baseline ID, missing reports directory, invalid workbook extension, and existing output without overwrite in `tests/unit/test_excel_reports.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Build Workbook From Existing Reports (Priority: P1) MVP

**Goal**: A user passes a baseline run ID and receives a workbook generated from the baseline CSV plus all associated candidate CSV reports found locally.

**Independent Test**: Provide fixture CSV reports with one baseline and one associated candidate; run the CLI target and verify a workbook result is produced using the fake writer.

### Tests for User Story 1 (REQUIRED)

- [X] T011 [P] [US1] Add unit tests for discovering the baseline CSV by `run_id` and associated candidate CSVs by `baseline_run_id` in `tests/unit/test_excel_reports.py`
- [X] T012 [P] [US1] Add unit tests for ignoring unrelated CSV reports and sorting included reports baseline-first in `tests/unit/test_excel_reports.py`
- [X] T013 [P] [US1] Add contract test for `run_experiment.py excel-report --baseline ... --reports-dir ... --output ...` success output in `tests/contract/test_cli_excel_comparison.py`
- [X] T014 [P] [US1] Add contract tests for missing baseline report, malformed CSV, and existing output without `--overwrite` in `tests/contract/test_cli_excel_comparison.py`
- [X] T015 [P] [US1] Add integration test with fixture reports and fake writer for end-to-end report discovery and workbook orchestration in `tests/integration/test_excel_comparison_workbook.py`

### Implementation for User Story 1

- [X] T016 [US1] Implement CSV scanning and parsing for `*.csv` report files in `src/evaluator_harness/excel_reports.py`
- [X] T017 [US1] Implement baseline report matching by requested `baseline_run_id` in `src/evaluator_harness/excel_reports.py`
- [X] T018 [US1] Implement candidate report matching by `baseline_run_id` in `src/evaluator_harness/excel_reports.py`
- [X] T019 [US1] Implement combined row construction with `source_report`, `included_run_id`, and `included_run_type` in `src/evaluator_harness/excel_reports.py`
- [X] T020 [US1] Implement workbook orchestration result with report count, combined row count, numeric score count, and warnings in `src/evaluator_harness/excel_reports.py`
- [X] T021 [US1] Add `excel-report` CLI command wiring and output formatting in `src/evaluator_harness/cli.py`
- [X] T022 [US1] Ensure CLI errors use existing `HarnessError`/`ConfigError` handling patterns in `src/evaluator_harness/cli.py` and `src/evaluator_harness/excel_reports.py`

**Checkpoint**: User Story 1 can generate a workbook from a baseline ID and associated candidate CSVs through the CLI using a fake writer.

---

## Phase 4: User Story 2 - Review Run Metadata First (Priority: P2)

**Goal**: The workbook first tab contains one run-summary row per included report with model, parameter, prompt, dataset, scenario, baseline, candidate, source report, and row-count context.

**Independent Test**: Use fixture CSVs containing run metadata and verify extracted run summaries exactly match expected fields, including missing metadata and mismatch warnings.

### Tests for User Story 2 (REQUIRED)

- [X] T023 [P] [US2] Add unit tests for extracting run summary metadata from baseline and candidate CSV rows in `tests/unit/test_excel_reports.py`
- [X] T024 [P] [US2] Add unit tests for blank metadata fallback and included row counts in `tests/unit/test_excel_reports.py`
- [X] T025 [P] [US2] Add unit tests for comparison warnings when candidate project, dataset, prompt, or evaluator context differs from baseline in `tests/unit/test_excel_reports.py`
- [X] T026 [P] [US2] Add integration test asserting fake writer receives `Run Summary` as the first worksheet payload in `tests/integration/test_excel_comparison_workbook.py`

### Implementation for User Story 2

- [X] T027 [US2] Implement first-non-empty run metadata extraction in `src/evaluator_harness/excel_reports.py`
- [X] T028 [US2] Implement `RunSummary` construction for baseline and candidate reports in `src/evaluator_harness/excel_reports.py`
- [X] T029 [US2] Implement comparison warning detection against baseline summary in `src/evaluator_harness/excel_reports.py`
- [X] T030 [US2] Pass ordered run summary payload as the first worksheet input to the workbook writer in `src/evaluator_harness/excel_reports.py`

**Checkpoint**: User Story 2 can be validated independently by checking run summary extraction and writer payload order.

---

## Phase 5: User Story 3 - Compare Average Evaluator Scores Visually (Priority: P3)

**Goal**: The workbook contains score data, a native Excel PivotTable averaging scores by evaluator and run, and a clustered column chart based on that PivotTable.

**Independent Test**: Use fixture CSVs with numeric score columns and comments; verify normalized score observations, PivotTable writer calls, chart writer calls, and no-score warnings.

### Tests for User Story 3 (REQUIRED)

- [X] T031 [P] [US3] Add unit tests for identifying numeric `score_<name>` columns and excluding `_comment` columns in `tests/unit/test_excel_reports.py`
- [X] T032 [P] [US3] Add unit tests for normalizing wide score columns into `ScoreObservation` rows in `tests/unit/test_excel_reports.py`
- [X] T033 [P] [US3] Add unit tests for omitting blank and non-numeric score values without converting them to zero in `tests/unit/test_excel_reports.py`
- [X] T034 [P] [US3] Add integration test asserting fake writer receives score data, native PivotTable request, and clustered column chart request in `tests/integration/test_excel_comparison_workbook.py`
- [X] T035 [P] [US3] Add integration test for no numeric scores producing warnings and no PivotTable/chart request in `tests/integration/test_excel_comparison_workbook.py`

### Implementation for User Story 3

- [X] T036 [US3] Implement score column detection and numeric parsing in `src/evaluator_harness/excel_reports.py`
- [X] T037 [US3] Implement long-form `ScoreObservation` generation in `src/evaluator_harness/excel_reports.py`
- [X] T038 [US3] Implement Windows Excel writer adapter that writes `Run Summary`, `Combined Data`, and `Score Data` worksheets in `src/evaluator_harness/excel_reports.py`
- [X] T039 [US3] Implement native Excel PivotCache/PivotTable creation for average score by `score_name` and `run_label` in `src/evaluator_harness/excel_reports.py`
- [X] T040 [US3] Implement clustered column chart creation based on the native PivotTable in `src/evaluator_harness/excel_reports.py`
- [X] T041 [US3] Implement clear native Excel automation unavailable error path in `src/evaluator_harness/excel_reports.py`
- [X] T042 [US3] Surface score-observation counts and no-score warnings in CLI output in `src/evaluator_harness/cli.py`

**Checkpoint**: User Story 3 produces the required native PivotTable/chart workflow when Excel automation is available and clear warnings/errors otherwise.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and cleanup across all stories.

- [X] T043 [P] Update user guide with `excel-report` examples, baseline run ID discovery behavior, overwrite behavior, and Excel prerequisite in `docs/user-guide.md`
- [X] T044 [P] Add quickstart command coverage notes to `specs/018-excel-comparison-report/quickstart.md` if implementation diverges from the plan
- [X] T045 Run focused tests with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_excel_reports.py tests/contract/test_cli_excel_comparison.py tests/integration/test_excel_comparison_workbook.py`
- [X] T046 Run related export/CLI regression tests with `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_exports.py tests/contract/test_cli_export.py tests/contract/test_cli_run_baseline.py tests/contract/test_cli_run_candidate.py`
- [ ] T047 Review generated workbook manually on a Windows machine with Excel installed and confirm native PivotTable and clustered column chart are present
- [X] T048 Remove unnecessary abstractions or unused helper code introduced during implementation in `src/evaluator_harness/excel_reports.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational
- **User Story 2 (Phase 4)**: Depends on Foundational and uses US1 report-loading payloads
- **User Story 3 (Phase 5)**: Depends on Foundational and uses US1/US2 workbook payloads
- **Polish (Phase 6)**: Depends on implemented user stories

### User Story Dependencies

- **US1 Build Workbook From Existing Reports**: MVP. Required before the command is useful.
- **US2 Review Run Metadata First**: Builds on discovered reports from US1 but summary extraction is testable independently.
- **US3 Compare Average Evaluator Scores Visually**: Builds on discovered reports and summaries; score normalization is testable independently.

### Within Each User Story

- Tests MUST be written and fail before implementation.
- Data structures and pure functions before CLI wiring.
- Workbook writer protocol/fake before native Excel adapter.
- Native Excel adapter after pure discovery/normalization behavior is covered.

## Parallel Opportunities

- T003, T004, and T005 can run in parallel after T002.
- T011, T012, T013, T014, and T015 can run in parallel after foundational tasks.
- T023, T024, T025, and T026 can run in parallel after US1 report payloads exist.
- T031, T032, T033, T034, and T035 can run in parallel after foundational tasks.
- Documentation task T043 can run in parallel with final cleanup after CLI behavior stabilizes.

## Parallel Example: User Story 1

```text
Task: "Add unit tests for discovering the baseline CSV by run_id and associated candidate CSVs by baseline_run_id in tests/unit/test_excel_reports.py"
Task: "Add contract test for run_experiment.py excel-report --baseline ... --reports-dir ... --output ... success output in tests/contract/test_cli_excel_comparison.py"
Task: "Add integration test with fixture reports and fake writer for end-to-end report discovery and workbook orchestration in tests/integration/test_excel_comparison_workbook.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational data structures and writer protocol.
3. Complete Phase 3 report discovery, combined data payload, and CLI target with fake writer tests.
4. Stop and validate that a baseline run ID selects the right local CSV reports.

### Incremental Delivery

1. US1: Discover baseline/candidates and create a workbook shell.
2. US2: Add run-summary-first metadata worksheet.
3. US3: Add score normalization, native PivotTable, and clustered column chart.
4. Polish: Update docs and verify with a real Excel workbook locally.

### Risk Controls

- Keep native Excel automation isolated so most tests run without Excel installed.
- Fail clearly rather than creating a non-native substitute when Excel automation is unavailable.
- Preserve all source CSV rows in `Combined Data` so workbook summaries remain auditable.
