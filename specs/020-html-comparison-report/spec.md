# Feature Specification: HTML Comparison Report

**Feature Branch**: `020-html-comparison-report`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "create a html report in the same way we have a excel report. the HTML should have the Run Summary, the Pivot table and the chart. the campaign can pass a flag to indicate whether the excel or HTML report should be generated (maybe both is an option too?) we can create a new target for the HTML report or rename the excel report target and have that one accept the flag of format. but need to update all documentation. implement it the way it is better coding without duplication of code, or keep it separate if they are truly very different. THE HTML must be visually appealing, so use a frontend skill if you have to"

## Clarifications

### Session 2026-06-13

- Q: What should campaign mode generate by default when no final report format is specified? -> A: Excel only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Shareable HTML Comparison Report (Priority: P1)

An evaluator operator has existing baseline and candidate CSV reports and needs a browser-viewable comparison report that contains the same core comparison content as the Excel workbook: run summary, pivot-style score comparison, and a chart.

**Why this priority**: This is the primary requested outcome and gives users a report format that can be opened without desktop spreadsheet software.

**Independent Test**: Provide a baseline run ID with a matching baseline CSV and at least one associated candidate CSV, generate an HTML report, and verify that the report opens locally with a run summary section, score comparison table, and chart.

**Acceptance Scenarios**:

1. **Given** a baseline CSV report and a candidate CSV report from the harness, **When** the user generates an HTML comparison report for the baseline run ID, **Then** the system creates one HTML file containing the baseline and associated candidate comparison.
2. **Given** multiple candidate CSV reports associated with one baseline CSV report, **When** the HTML report is generated, **Then** all associated successful runs appear in the run summary, comparison table, and chart where score data exists.
3. **Given** the original CSV reports remain on disk, **When** the user regenerates the HTML report later with the same baseline run ID, **Then** no model run, evaluator run, sync, or CSV export is required.

---

### User Story 2 - Choose Report Format During Campaign (Priority: P2)

A project owner running a campaign chooses whether the final comparison artifact should be Excel, HTML, or both, so the campaign produces the right deliverable for the audience without extra manual steps.

**Why this priority**: Campaign mode is the main end-to-end workflow. Users should not have to run a separate report command immediately after a campaign to get the desired format.

**Independent Test**: Run campaign mode with each supported report format selection and verify that the campaign summary lists exactly the requested final artifacts while still exporting required CSV reports.

**Acceptance Scenarios**:

1. **Given** a campaign with successful baseline and candidate runs, **When** the user requests HTML output, **Then** campaign mode creates an HTML comparison report and reports its path in the final summary.
2. **Given** a campaign with successful baseline and candidate runs, **When** the user requests Excel output, **Then** campaign mode creates the Excel comparison workbook and reports its path in the final summary.
3. **Given** a campaign with successful baseline and candidate runs, **When** the user requests both report formats, **Then** campaign mode creates both final artifacts from the same campaign CSV reports and reports both paths.

---

### User Story 3 - Review a Polished Browser Report (Priority: P3)

An evaluator reviewer opens the HTML report and can quickly understand the comparison because the page is visually polished, readable, and organized for presentation rather than appearing as a raw export.

**Why this priority**: HTML is often used for sharing and review. The report must be credible and easy to scan for non-technical stakeholders.

**Independent Test**: Open a generated HTML report in a browser and verify that the first view communicates project/run context, the score comparison is legible, the chart is clear, and the layout remains usable with several candidates and evaluators.

**Acceptance Scenarios**:

1. **Given** a generated HTML report, **When** a reviewer opens it, **Then** the first visible content clearly identifies the project, baseline, compared runs, report creation context, and high-level score summary.
2. **Given** runs with numeric evaluator scores, **When** a reviewer scans the HTML report, **Then** score averages are shown in a readable pivot-style table with baseline and candidates distinguishable by run.
3. **Given** score comparison data exists, **When** a reviewer views the chart, **Then** the chart clearly compares average evaluator scores across the baseline and candidates without requiring the source CSV files.

---

### User Story 4 - Use a Consistent Report Command (Priority: P4)

An evaluator operator wants a predictable command structure for final comparison reports, whether they are generating Excel, HTML, or both. Existing Excel users should not lose their current workflow without a clear replacement.

**Why this priority**: Clear commands and documentation reduce operational mistakes and preserve compatibility for current users.

**Independent Test**: Follow the updated user documentation to generate Excel only, HTML only, and both report formats from existing CSV reports.

**Acceptance Scenarios**:

1. **Given** an existing Excel report workflow, **When** the command naming or options change, **Then** documentation clearly explains the current command and any compatibility behavior.
2. **Given** a user has existing CSV reports, **When** they use the documented standalone report workflow, **Then** they can generate HTML without running a campaign.
3. **Given** a user requests an unsupported format value, **When** they run the command, **Then** the system rejects it with a clear message listing supported formats.

### Edge Cases

- The baseline run ID has no associated candidate CSV reports.
- CSV inputs include no numeric score columns.
- CSV inputs have different evaluator score sets across runs.
- A score column exists for one run but is missing for another run.
- A report output path already exists.
- Campaign mode has partial candidate failures but successful CSV reports exist for other runs.
- Users request final report generation while also disabling report generation for the campaign.
- HTML report generation runs in an environment without spreadsheet software.
- The report includes many candidates or evaluator scores and must remain readable.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature consumes existing harness project and report metadata already present in CSV exports, including project identity, dataset, baseline, candidate, evaluator, and review context.
- **Dataset**: Feature MUST preserve support for CSV reports generated from existing project datasets and MUST NOT change dataset requirements.
- **Langfuse Logging**: Feature MUST NOT require new Langfuse traces, scores, syncs, sessions, or model calls; it uses existing local CSV report contents.
- **Prompt and Evaluator Versioning**: Feature MUST expose available prompt version, prompt identity, evaluator score names, and evaluator score values in generated comparison reports.
- **Baseline**: Feature consumes a baseline run ID to locate the baseline report and associated candidate reports; it does not create or select a baseline except when invoked through campaign mode.
- **Human Review**: Feature MUST preserve available review-relevant fields in report source data and MUST NOT create or modify Human Annotation Queue items.

### Functional Requirements

- **FR-001**: Users MUST be able to generate an HTML comparison report from existing local CSV reports using a baseline run ID.
- **FR-002**: The HTML report MUST include a run summary containing one summary entry per included baseline or candidate report.
- **FR-003**: The run summary MUST include run ID, run type, project, project version, dataset name, dataset version, model or provider fields, model parameters or parameter identity, prompt version or prompt identity, baseline reference, candidate or variant identity when present, source report path, and included row count when those values are available.
- **FR-004**: The HTML report MUST include a pivot-style score comparison table showing average numeric evaluator score by evaluator score name and run.
- **FR-005**: The HTML report MUST include a chart that compares average evaluator scores across the baseline and candidate runs when numeric score data exists.
- **FR-006**: The HTML report MUST clearly indicate when no numeric score data exists while still providing the run summary.
- **FR-007**: The HTML report MUST preserve missing score combinations as blank or unavailable rather than treating missing values as zero.
- **FR-008**: The HTML report MUST be visually polished, readable, and presentation-ready, with clear hierarchy, legible spacing, distinguishable baseline and candidate runs, and a layout that remains usable for multiple candidates and evaluators.
- **FR-009**: Users MUST be able to choose final comparison report output format for campaign mode: Excel only, HTML only, or both.
- **FR-009a**: Campaign mode MUST default to Excel-only final report generation when the user does not specify a final report format.
- **FR-010**: Campaign mode MUST continue exporting the per-run CSV reports needed to create final comparison artifacts unless users explicitly disable report generation.
- **FR-011**: Campaign mode MUST list each generated final comparison artifact path in the final campaign summary.
- **FR-012**: Standalone report generation MUST support creating Excel only, HTML only, or both from the same baseline run ID and report search location.
- **FR-013**: Existing Excel report behavior MUST remain available, either through the current command or through a clearly documented replacement that preserves the same capability.
- **FR-014**: Users MUST be able to choose the output location for generated final comparison reports.
- **FR-015**: The system MUST avoid overwriting existing output files unless the user explicitly requests overwrite behavior.
- **FR-016**: The system MUST report unreadable, missing, malformed, or incompatible CSV inputs with actionable file-specific messages.
- **FR-017**: The system MUST reject unsupported report format selections with a clear message listing supported values.
- **FR-018**: Documentation MUST describe the standalone comparison report workflow, campaign report format selection, supported formats, overwrite behavior, no-score behavior, and examples for Excel only, HTML only, and both.

### Key Entities *(include if feature involves data)*

- **CSV Report Input**: A harness-generated CSV report file for a baseline or candidate run, including row-level outputs, run metadata, score columns, baseline reference, and source path.
- **Baseline Run ID**: The user-provided run identifier used to find the baseline report and candidate reports that reference it.
- **Run Summary**: One report section or table row per included run that captures run identity, model configuration, prompt/evaluator context, baseline/candidate relationship, source report, and row counts.
- **Score Comparison**: A normalized aggregate view of numeric evaluator scores grouped by evaluator score name and run, using average score values.
- **Comparison Chart**: A visual representation of the score comparison, showing baseline and candidate score averages by evaluator score.
- **HTML Comparison Report**: A generated browser-viewable report artifact containing run summary, score comparison table, chart, and clear no-data messages when applicable.
- **Report Format Selection**: User choice that determines whether final comparison report generation creates Excel, HTML, or both artifacts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can generate an HTML comparison report from a baseline run ID and existing CSV reports in under 2 minutes without rerunning any experiment.
- **SC-002**: For reports with numeric evaluator scores, 100% of discovered numeric evaluator score columns appear in the HTML score comparison table.
- **SC-003**: The HTML report contains exactly one run-summary entry for each included CSV report in 100% of successful HTML generations.
- **SC-004**: Campaign mode can produce Excel only, HTML only, and both final report formats from the same successful campaign CSV reports.
- **SC-005**: Reviewers can identify baseline and candidate model, parameter, prompt, dataset, and run relationships from the HTML report without opening the source CSV files.
- **SC-006**: When inputs contain no score columns, users still receive an HTML report with run summary plus a clear no-score indication.
- **SC-007**: Updated documentation enables a user to run the standalone and campaign report workflows for each supported format without needing undocumented options.

## Assumptions

- Input CSV files are produced by the harness report export format.
- The HTML report should use the same report discovery and score aggregation rules as the Excel comparison workflow whenever the user asks for the same baseline run ID.
- The default campaign final report format remains Excel only unless the user explicitly requests HTML or both.
- "Both" means one Excel workbook and one HTML report generated from the same discovered baseline and candidate CSV reports.
- The HTML artifact is intended for local browser viewing and sharing as a generated report file, not as a hosted web application.
- Visual polish is part of acceptance for the HTML artifact, but the feature does not require interactive filtering or live data loading unless later specified.
