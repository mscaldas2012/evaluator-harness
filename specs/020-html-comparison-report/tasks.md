# Tasks: HTML Comparison Report

**Input**: Design documents from `specs/020-html-comparison-report/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover shared report payload behavior, output validation, HTML rendering, campaign format selection, CLI exit behavior, documentation examples, and visual verification expectations.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to, such as `[US1]`
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare fixtures and orientation for the comparison report refactor.

- [X] T001 Review existing Excel report discovery, payload, and writer behavior in `src/evaluator_harness/excel_reports.py`
- [X] T002 [P] Review existing campaign report generation path in `src/evaluator_harness/runner.py`
- [X] T003 [P] Review existing CLI report commands in `src/evaluator_harness/cli.py`
- [X] T004 [P] Add reusable CSV report fixture helpers for comparison report tests in `tests/unit/test_comparison_reports.py`
- [X] T005 [P] Add reusable HTML assertion helpers for generated static report markup in `tests/unit/test_html_reports.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the shared comparison-report layer that every story depends on.

**CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational Layer

- [X] T006 [P] Add failing tests for baseline selection, candidate selection, malformed CSV errors, and existing output validation in `tests/unit/test_comparison_reports.py`
- [X] T007 [P] Add failing tests for score observation extraction, score aggregate averages, missing score combinations, and warning construction in `tests/unit/test_comparison_reports.py`
- [X] T008 [P] Add failing tests proving Excel compatibility output still receives the same payload fields in `tests/unit/test_excel_reports.py`

### Implementation for Foundational Layer

- [X] T009 Create shared dataclasses and format enum for `BaselineRunSelection`, `CsvReportInput`, `RunSummary`, `CombinedReportRow`, `ScoreObservation`, `ScoreAggregate`, `ComparisonReportPayload`, and `ComparisonReportOutput` in `src/evaluator_harness/comparison_reports.py`
- [X] T010 Move CSV discovery, baseline/candidate report selection, CSV parsing, run summary construction, combined row construction, score observation extraction, score aggregate calculation, and warning construction from `src/evaluator_harness/excel_reports.py` into `src/evaluator_harness/comparison_reports.py`
- [X] T011 Implement shared output path validation for `.xlsx`, `.html`, `--output`, `--output-dir`, `--format both`, missing directories, and overwrite conflicts in `src/evaluator_harness/comparison_reports.py`
- [X] T012 Refactor `src/evaluator_harness/excel_reports.py` to import and consume `ComparisonReportPayload` while preserving `create_excel_report()` behavior and public return fields
- [X] T013 Run focused foundational tests with `uv run pytest -p no:cacheprovider tests/unit/test_comparison_reports.py tests/unit/test_excel_reports.py`

**Checkpoint**: Shared report payload behavior is complete and Excel behavior is still compatible.

---

## Phase 3: User Story 1 - Generate Shareable HTML Comparison Report (Priority: P1) MVP

**Goal**: Generate a self-contained HTML comparison report from existing baseline and candidate CSV reports.

**Independent Test**: Provide a baseline run ID with a matching baseline CSV and candidate CSV, generate HTML, and verify the file contains run summary, pivot-style score table, chart markup, warnings, and no external asset references.

### Tests for User Story 1

- [X] T014 [P] [US1] Add failing unit tests for successful HTML rendering with run summary, score table, chart, and escaped CSV values in `tests/unit/test_html_reports.py`
- [X] T015 [P] [US1] Add failing unit tests for no-candidate and no-numeric-score HTML states in `tests/unit/test_html_reports.py`
- [X] T016 [P] [US1] Add failing integration test that writes CSV fixtures, calls HTML report generation, and verifies the generated `.html` file in `tests/integration/test_html_comparison_report.py`

### Implementation for User Story 1

- [X] T017 [US1] Apply `frontend-design` guidance before coding `src/evaluator_harness/html_reports.py`, documenting the chosen refined editorial dashboard direction in a brief module comment or test fixture note
- [X] T018 [US1] Implement `HtmlReportOutput` and `create_html_report()` facade in `src/evaluator_harness/html_reports.py`
- [X] T019 [US1] Implement self-contained HTML document generation with embedded CSS variables, semantic sections, first-view context, run summary table, pivot-style score table, warnings, and no-score/no-candidate states in `src/evaluator_harness/html_reports.py`
- [X] T020 [US1] Implement deterministic inline SVG grouped score chart with accessible labels and blank handling for missing score combinations in `src/evaluator_harness/html_reports.py`
- [X] T021 [US1] Ensure all dynamic report values are HTML-escaped and no external CSS, font, image, script, or CDN references are emitted in `src/evaluator_harness/html_reports.py`
- [X] T022 [US1] Run focused HTML tests with `uv run pytest -p no:cacheprovider tests/unit/test_html_reports.py tests/integration/test_html_comparison_report.py`

**Checkpoint**: User Story 1 is independently functional as the MVP.

---

## Phase 4: User Story 2 - Choose Report Format During Campaign (Priority: P2)

**Goal**: Campaign mode generates Excel, HTML, or both final artifacts, defaulting to Excel only.

**Independent Test**: Run campaign mode with each supported `--report-format` value using fakes and verify the final summary contains exactly the requested final artifacts.

### Tests for User Story 2

- [X] T023 [P] [US2] Add failing unit tests for campaign `report_format` default `excel`, explicit `html`, explicit `both`, and `no_report` behavior in `tests/unit/test_campaign.py`
- [X] T024 [P] [US2] Add failing contract tests for campaign CLI `--report-format html`, `--report-format both`, default Excel output, unsupported format failure, and summary output in `tests/contract/test_cli_campaign.py`

### Implementation for User Story 2

- [X] T025 [US2] Extend `CampaignRunResult` in `src/evaluator_harness/runner.py` to carry a list of final comparison report outputs while preserving `excel_report` compatibility
- [X] T026 [US2] Add campaign `report_format` handling in `ExperimentRunner.campaign()` in `src/evaluator_harness/runner.py`, using shared comparison report orchestration to generate Excel, HTML, or both from the campaign baseline CSV reports
- [X] T027 [US2] Add `--report-format` option to the `campaign` command in `src/evaluator_harness/cli.py`, validate supported values before running, and keep default behavior as Excel only
- [X] T028 [US2] Update campaign CLI summary printing in `src/evaluator_harness/cli.py` to print `excel-report:` and `html-report:` paths according to generated final artifacts
- [X] T029 [US2] Run focused campaign tests with `uv run pytest -p no:cacheprovider tests/unit/test_campaign.py tests/contract/test_cli_campaign.py`

**Checkpoint**: Campaign format selection works independently of standalone report command changes.

---

## Phase 5: User Story 3 - Review a Polished Browser Report (Priority: P3)

**Goal**: The generated HTML report is presentation-ready, visually polished, readable, and verified in browser-like review.

**Independent Test**: Open or inspect a generated HTML report at desktop and narrow widths and verify first-view context, table legibility, chart clarity, warning/no-score states, and absence of overlap or clipped text.

### Tests for User Story 3

- [X] T030 [P] [US3] Add failing markup quality tests for CSS variables, responsive layout rules, baseline/candidate visual distinction, warning state styling, and chart accessibility labels in `tests/unit/test_html_reports.py`
- [X] T031 [P] [US3] Add generated HTML snapshot-style assertions for desktop and narrow-width critical content containers in `tests/integration/test_html_comparison_report.py`

### Implementation for User Story 3

- [X] T032 [US3] Refine `src/evaluator_harness/html_reports.py` styling using `frontend-design` guidance: distinctive typography stack, cohesive colors, clear hierarchy, dense readable tables, polished warnings, and responsive constraints
- [X] T033 [US3] Add a representative sample HTML generation fixture or documented command for design review in `tests/fixtures/reports/html_design_review/README.md`
- [ ] T034 [US3] Perform browser/screenshot inspection of a generated HTML report at desktop and narrow widths and record accepted visual checks in `specs/020-html-comparison-report/quickstart.md`
- [X] T035 [US3] Run HTML design-focused tests with `uv run pytest -p no:cacheprovider tests/unit/test_html_reports.py tests/integration/test_html_comparison_report.py`

**Checkpoint**: HTML report satisfies the visual acceptance criteria and frontend-design guidance.

---

## Phase 6: User Story 4 - Use a Consistent Report Command (Priority: P4)

**Goal**: Provide a predictable standalone comparison report command for Excel, HTML, or both, while preserving existing Excel workflow compatibility.

**Independent Test**: Follow docs to generate Excel only, HTML only, and both from existing CSV reports, and verify unsupported formats fail with a clear message.

### Tests for User Story 4

- [X] T036 [P] [US4] Add failing contract tests for `comparison-report --format excel`, `--format html`, `--format both`, `--output`, `--output-dir`, unsupported format, and warning output in `tests/contract/test_cli_comparison_report.py`
- [X] T037 [P] [US4] Add failing compatibility tests proving `excel-report` delegates to the Excel path and preserves existing output in `tests/contract/test_cli_excel_comparison.py`
- [X] T038 [P] [US4] Add failing unit tests for multi-format output orchestration and output-path validation in `tests/unit/test_comparison_reports.py`

### Implementation for User Story 4

- [X] T039 [US4] Implement multi-format `create_comparison_reports()` orchestration in `src/evaluator_harness/comparison_reports.py`
- [X] T040 [US4] Add `comparison-report` Typer command with `--format`, `--project`, `--reports-dir`, `--output`, `--output-dir`, and `--overwrite` options in `src/evaluator_harness/cli.py`
- [X] T041 [US4] Update existing `excel-report` command in `src/evaluator_harness/cli.py` to delegate through the shared Excel path without changing existing CLI behavior
- [X] T042 [US4] Print standalone report summaries and warnings for Excel, HTML, and both formats in `src/evaluator_harness/cli.py`
- [X] T043 [US4] Run standalone CLI tests with `uv run pytest -p no:cacheprovider tests/contract/test_cli_comparison_report.py tests/contract/test_cli_excel_comparison.py tests/unit/test_comparison_reports.py`

**Checkpoint**: Users have one documented standalone command for all formats and existing Excel command still works.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression coverage, and final verification across all stories.

- [X] T044 [P] Update report workflow documentation for `comparison-report`, `excel-report`, `--report-format`, HTML design expectations, overwrite behavior, no-score behavior, and examples in `docs/user-guide.md`
- [X] T045 [P] Update project README report references if needed in `README.md`
- [X] T046 [P] Update quickstart examples if implementation command names or outputs differ in `specs/020-html-comparison-report/quickstart.md`
- [X] T047 Review `src/evaluator_harness/comparison_reports.py`, `src/evaluator_harness/excel_reports.py`, and `src/evaluator_harness/html_reports.py` for unnecessary duplication and simplify while preserving separate renderers
- [X] T048 Run focused feature suite with `uv run pytest -p no:cacheprovider tests/unit/test_comparison_reports.py tests/unit/test_html_reports.py tests/unit/test_excel_reports.py tests/unit/test_campaign.py tests/contract/test_cli_comparison_report.py tests/contract/test_cli_campaign.py tests/contract/test_cli_excel_comparison.py tests/integration/test_html_comparison_report.py`
- [ ] T049 Run full test suite with `uv run pytest -p no:cacheprovider`
- [X] T050 Check `git diff --check` and review generated HTML artifacts are not accidentally committed unless intentionally added as fixtures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **US1 Generate HTML (Phase 3)**: Depends on Foundational. This is the MVP.
- **US2 Campaign Format (Phase 4)**: Depends on Foundational and benefits from US1 for actual HTML rendering, but can be tested with fakes.
- **US3 Polished Browser Report (Phase 5)**: Depends on US1 because it refines the HTML renderer.
- **US4 Consistent Report Command (Phase 6)**: Depends on Foundational and US1 for HTML output; can proceed after US1.
- **Polish (Phase 7)**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependency on other user stories; delivers standalone HTML generation.
- **US2 (P2)**: Can be implemented after Foundational with fake renderers, then integrated with US1 output.
- **US3 (P3)**: Depends on US1 HTML renderer.
- **US4 (P4)**: Depends on Foundational and should integrate US1 HTML renderer plus existing Excel compatibility.

### Parallel Opportunities

- T002, T003, T004, and T005 can run in parallel.
- T006, T007, and T008 can run in parallel.
- US1 tests T014, T015, and T016 can run in parallel.
- US2 tests T023 and T024 can run in parallel.
- US3 tests T030 and T031 can run in parallel.
- US4 tests T036, T037, and T038 can run in parallel.
- Documentation tasks T044, T045, and T046 can run in parallel after command behavior stabilizes.

## Parallel Example: User Story 1

```text
Task: "T014 Add failing unit tests for successful HTML rendering in tests/unit/test_html_reports.py"
Task: "T015 Add failing unit tests for no-candidate and no-numeric-score HTML states in tests/unit/test_html_reports.py"
Task: "T016 Add failing integration test for generated HTML file in tests/integration/test_html_comparison_report.py"
```

## Parallel Example: User Story 4

```text
Task: "T036 Add failing comparison-report contract tests in tests/contract/test_cli_comparison_report.py"
Task: "T037 Add failing excel-report compatibility tests in tests/contract/test_cli_excel_comparison.py"
Task: "T038 Add failing multi-format orchestration tests in tests/unit/test_comparison_reports.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 shared comparison-report foundation.
3. Complete Phase 3 HTML report generation.
4. Stop and validate with `uv run pytest -p no:cacheprovider tests/unit/test_comparison_reports.py tests/unit/test_html_reports.py tests/integration/test_html_comparison_report.py`.
5. Open a generated HTML report and verify the core report sections are present.

### Incremental Delivery

1. Deliver shared payload foundation.
2. Deliver standalone HTML generation (US1).
3. Add campaign report format selection (US2).
4. Refine visual polish and browser verification (US3).
5. Add unified standalone comparison command and Excel compatibility coverage (US4).
6. Update documentation and run full verification.

### Parallel Team Strategy

1. One developer owns shared comparison payload and Excel compatibility.
2. One developer owns HTML renderer and frontend-design visual quality.
3. One developer owns CLI/campaign integration.
4. Coordinate through shared dataclasses in `src/evaluator_harness/comparison_reports.py`.

## Notes

- Tasks marked `[P]` touch different files or can be completed without depending on incomplete implementation tasks.
- Write tests before implementation and confirm they fail for the missing behavior.
- Preserve existing `excel-report` behavior for current users.
- Keep HTML self-contained and avoid external assets, CDNs, or hosted web app behavior.
- Use `frontend-design` before and during HTML renderer work; the HTML report should be intentionally designed, not a raw table dump.

