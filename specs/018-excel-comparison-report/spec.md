# Feature Specification: Excel Comparison Report

**Feature Branch**: `018-excel-comparison-report`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "At the end of all the runs, the user should be able to call a target to combine the csv reports into a single excel; create a pivot table comparing the scores and build a chart diagram. The first tab should have information about the baseline and candidates run - the model used, parameters, prompt version, etc. The excel creation should be it's own target of run_experiment.py so the user can recreate the excel after runs as long as the csv reports exists"

## Clarifications

### Session 2026-06-11

- Q: Should the score comparison be a native Excel PivotTable or a generated pivot-style summary table? -> A: Native Excel PivotTable, with a separate combined-data tab containing all report rows.
- Q: What chart type should visualize score averages by evaluator and run? -> A: Clustered column chart with evaluator scores on the category axis and one series per run.
- Q: How should users identify which CSV reports to combine? -> A: User passes the baseline run ID; the target finds the baseline CSV and all candidate CSV reports associated with that baseline.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build Workbook From Existing Reports (Priority: P1)

An evaluator operator has already run a baseline and one or more candidates and has CSV report files on disk. They need to provide the baseline run ID and receive a single Excel workbook that finds the baseline report plus associated candidate reports, summarizes each run, compares evaluator scores, and includes a visual chart so the result can be shared without rerunning models or evaluators.

**Why this priority**: This is the core requested workflow and removes manual spreadsheet assembly after every evaluation round.

**Independent Test**: Can be fully tested by providing a baseline run ID where matching baseline and candidate CSV reports exist locally and verifying that a workbook is created with a run-summary first tab, combined-data tab, native Excel PivotTable, and chart.

**Acceptance Scenarios**:

1. **Given** a baseline CSV report and a candidate CSV report from the harness, **When** the user runs the Excel report target with the baseline run ID, **Then** the system creates one Excel workbook containing the baseline report and the associated candidate report.
2. **Given** multiple candidate CSV reports associated with one baseline CSV report, **When** the user runs the Excel report target with the baseline run ID, **Then** the workbook includes every associated report row in a combined-data tab and compares all available runs side by side.
3. **Given** the original CSV reports remain on disk, **When** the user reruns the Excel report target later with the same inputs, **Then** the workbook is recreated without requiring any model run, evaluator run, or Langfuse sync.

---

### User Story 2 - Review Run Metadata First (Priority: P2)

An evaluator reviewer opens the workbook and needs immediate context about what was compared before reviewing scores. The first tab should list the baseline and candidate runs with model identity, model parameters, prompt version, dataset/scenario context, report file, and row counts.

**Why this priority**: Score comparisons are not meaningful unless reviewers can verify the baseline and candidate configuration context.

**Independent Test**: Can be tested by opening the first workbook tab and verifying that each input CSV contributes exactly one run-summary row with the expected run metadata.

**Acceptance Scenarios**:

1. **Given** CSV reports that include run metadata columns, **When** the workbook is created, **Then** the first tab lists each run with run ID, run type, project, project version, dataset, prompt version, model, parameters, candidate identity when present, baseline reference when present, source report path, and included row count.
2. **Given** a metadata value is missing from a CSV, **When** the workbook is created, **Then** the first tab still includes that run and clearly marks the missing value without blocking the workbook.

---

### User Story 3 - Compare Average Evaluator Scores Visually (Priority: P3)

An evaluator analyst wants to quickly see which candidate improved or regressed across evaluator dimensions. The workbook should include a native Excel PivotTable and clustered column chart comparing average scores by evaluator and run.

**Why this priority**: The workbook becomes useful for decision-making, not only archival export.

**Independent Test**: Can be tested by using CSVs with several score columns and verifying that a native Excel PivotTable groups averages by score/evaluator and run, with a chart based on the same comparison data.

**Acceptance Scenarios**:

1. **Given** input CSV reports with score columns, **When** the workbook is created, **Then** the workbook includes a native Excel PivotTable with average score per evaluator per run.
2. **Given** score comparison data exists, **When** the workbook is created, **Then** the workbook includes a clustered column chart with evaluator scores on the category axis and one series per run.
3. **Given** score comment columns are present, **When** averages are calculated, **Then** non-numeric comment fields are excluded from score averages.

### Edge Cases

- If the baseline run ID has no associated candidate CSV reports, the system still creates a workbook for the baseline report but clearly indicates that comparison requires at least one associated candidate run.
- If a CSV file does not exist or cannot be read, the system reports which file failed and does not create a misleading partial workbook.
- If report rows use different evaluator score columns, the workbook includes all discovered evaluator score columns and leaves missing run/evaluator combinations blank.
- If no numeric score columns are found, the workbook still includes run summary and combined data tabs and clearly indicates that score comparison and chart data are unavailable.
- If an output workbook path already exists, the user can recreate the workbook by overwriting it through the same Excel report target.
- If baseline and candidate reports reference different projects or datasets, the workbook is still generated but the run summary highlights the mismatch so users can spot invalid comparisons.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature consumes existing harness CSV reports that already contain project identity, dataset, baseline, candidate, evaluator, and review metadata.
- **Dataset**: Feature MUST preserve report rows from CSV exports regardless of dataset size, as long as the CSV conforms to the harness report format.
- **Langfuse Logging**: Feature MUST NOT require new Langfuse traces, scores, syncs, sessions, or model calls; it uses only existing CSV report contents.
- **Prompt and Evaluator Versioning**: Feature MUST expose prompt version, prompt identity fields when present, evaluator score names, and evaluator score values in the workbook.
- **Baseline**: Feature consumes a baseline run ID to locate baseline and candidate report CSVs; it does not create or select a baseline run for experiment execution.
- **Human Review**: Feature MUST preserve available review-relevant fields from the CSV reports in combined workbook data but does not create or modify Human Annotation Queue items.

### Functional Requirements

- **FR-001**: Users MUST be able to invoke a dedicated Excel report target after runs complete, using a baseline run ID as the primary input.
- **FR-002**: Users MUST be able to recreate the Excel workbook at any time from CSV files that still exist locally, without rerunning baseline, candidate, evaluator, sync, or report-generation steps.
- **FR-003**: The system MUST locate the baseline CSV report for the requested baseline run ID and all candidate CSV reports whose baseline reference matches that baseline run ID.
- **FR-003a**: Users MUST be able to choose the report search location so workbooks can be recreated from archived or copied report folders.
- **FR-004**: The system MUST create one workbook that includes a first tab containing one summary row per input run.
- **FR-005**: The first tab MUST include run ID, run type, project, project version, dataset name, dataset version, scenario fields when present, model/provider fields, model parameters or parameter identity, prompt version or prompt identity, baseline reference, candidate or variant identity when present, source report path, and included row count.
- **FR-006**: The workbook MUST include a combined data tab containing the report rows from all input CSV files with enough source/run fields for filtering and auditing.
- **FR-007**: The workbook MUST identify evaluator score columns from numeric score fields and MUST exclude score comment fields from numeric aggregation.
- **FR-008**: The workbook MUST include a native Excel PivotTable showing average score by evaluator score and run.
- **FR-009**: The workbook MUST include a clustered column chart based on the native PivotTable score comparison when at least one numeric evaluator score is available.
- **FR-010**: The system MUST preserve missing score combinations as blank or clearly unavailable rather than converting them to zero.
- **FR-011**: The system MUST report unreadable, missing, or malformed CSV inputs with actionable file-specific messages.
- **FR-012**: The system MUST allow users to choose the workbook output location.
- **FR-013**: The system MUST avoid overwriting existing output unless the user explicitly requests recreation at that path.
- **FR-014**: The workbook MUST remain useful when CSV reports contain different evaluator score sets, different candidate names, or extra metadata columns.
- **FR-015**: The workbook MUST include enough information for a reviewer to determine whether the compared runs belong to the same project, dataset, prompt/evaluator setup, and baseline relationship.

### Key Entities

- **CSV Report Input**: A harness-generated CSV report file for a baseline or candidate run, including trace rows, run metadata, score columns, baseline reference, and source path.
- **Baseline Run ID**: The user-provided run identifier used to find the baseline report and candidate reports that reference it.
- **Run Summary**: One workbook row per report input that captures run identity, model configuration, prompt/evaluator context, baseline/candidate relationship, and row counts.
- **Combined Report Data**: The union of row-level report data from all input CSV files, annotated with source report and run identity.
- **Score Comparison**: A normalized view of numeric evaluator scores grouped by evaluator score name and run, with average score values, presented through a native Excel PivotTable.
- **Excel Workbook**: The generated deliverable containing run summary, combined data, score comparison, and chart worksheets.
- **Score Chart**: A clustered column chart that compares average evaluator scores across baseline and candidate runs, with evaluator scores on the category axis and one series per run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create a comparison workbook from a baseline run ID with one associated candidate report in under 2 minutes without rerunning any experiment.
- **SC-002**: For reports with numeric evaluator scores, 100% of discovered numeric evaluator score columns appear in the native Excel PivotTable.
- **SC-003**: The first workbook tab contains exactly one run-summary row for each input CSV report in 100% of successful workbook generations.
- **SC-004**: Recreating a workbook from unchanged CSV inputs produces the same run summary and score comparison values.
- **SC-005**: Users can identify baseline and candidate model, parameter, prompt, dataset, and run relationships from the first tab without opening the source CSV files.
- **SC-006**: When inputs contain no score columns, users still receive a workbook with run summary and combined data plus a clear no-score indication.

## Assumptions

- Input CSV files are produced by the harness report export format.
- Numeric evaluator score columns use the existing report convention for score fields, while comment fields are non-numeric and not averaged.
- The target workbook format is Excel-compatible and can contain multiple worksheets plus chart objects.
- Workbook generation is a local offline operation and does not contact Langfuse, model providers, or external services.
- The initial feature focuses on aggregate average score comparisons, not statistical significance testing or evaluator calibration analysis.
- The output workbook may include additional helper tabs if needed, as long as the first tab remains the run summary.
