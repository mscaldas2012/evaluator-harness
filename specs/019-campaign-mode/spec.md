# Feature Specification: Campaign Mode

**Feature Branch**: `019-campaign-mode`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Implement campaign mode where the user can run the baseline and all candidates in one go. Add a flag to project.yaml to `exclude-from-campaign: [true|false]` for each candidate in case we don't want to keep that candidate as part of the campaign, like dry-run candidates. Default to false so candidates are included unless explicitly excluded. After all the runs, create the Excel report with all the CSV reports using the new `excel-report` CLI."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Full Campaign (Priority: P1)

A project owner starts one campaign command for a project and receives a completed baseline run, completed eligible candidate runs, CSV reports for each run, and one Excel comparison workbook for the campaign.

**Why this priority**: This is the core workflow reduction. It removes the need to manually run the baseline, copy the baseline run ID, run each candidate, and then create the workbook.

**Independent Test**: Configure a project with one baseline and two campaign-eligible candidates, run campaign mode, and verify that the baseline, both candidates, all CSV reports, and a final Excel workbook are produced.

**Acceptance Scenarios**:

1. **Given** a valid project with two candidates that omit `exclude-from-campaign` or set it to `false`, **When** the user runs campaign mode, **Then** the system runs the baseline first, runs both eligible candidates against that exact baseline, exports CSV reports for all three runs, and creates one Excel comparison workbook for the baseline.
2. **Given** a candidate run fails while other eligible candidates remain, **When** campaign mode completes, **Then** the system reports the failed candidate, keeps successful run outputs and CSV reports, and does not hide partial results.
3. **Given** the Excel workbook output path already exists, **When** campaign mode reaches report creation, **Then** the system follows the same overwrite behavior exposed by the Excel report target and tells the user how to resolve the conflict.

---

### User Story 2 - Exclude Candidates From Campaign (Priority: P2)

A project owner controls which candidates are included in campaign runs directly in the project YAML, so utility candidates such as dry-run or experimental variants are not run accidentally.

**Why this priority**: Campaign mode can spend time and provider budget. Candidate-level exclusion keeps the workflow safe and intentional.

**Independent Test**: Configure a project with one candidate set to `exclude-from-campaign: false`, one candidate set to `exclude-from-campaign: true`, and one candidate with no flag. Run campaign mode and verify that the false and omitted candidates run while the true candidate is skipped.

**Acceptance Scenarios**:

1. **Given** a candidate has `exclude-from-campaign: false`, **When** campaign mode selects candidates, **Then** that candidate is included.
2. **Given** a candidate has `exclude-from-campaign: true`, **When** campaign mode selects candidates, **Then** that candidate is skipped and listed as skipped in the campaign summary.
3. **Given** a candidate omits `exclude-from-campaign`, **When** campaign mode selects candidates, **Then** that candidate defaults to included and is run.

---

### User Story 3 - Inspect Campaign Summary (Priority: P3)

A project owner sees a clear command summary showing the baseline run ID, each included candidate run ID, skipped candidates, report paths, and the final Excel workbook path.

**Why this priority**: Campaign mode is a multi-run operation. Users need an audit trail at the end without digging through logs.

**Independent Test**: Run campaign mode on a project with included and excluded candidates, then verify the command output includes the campaign summary fields needed to find the runs and reports.

**Acceptance Scenarios**:

1. **Given** campaign mode finishes successfully, **When** the user reviews the command output, **Then** it includes the baseline run ID, candidate run IDs, skipped candidate names and reasons, CSV report paths, and Excel workbook path.
2. **Given** no candidates are eligible for campaign mode, **When** the user runs campaign mode, **Then** the system does not run a baseline by default and reports that no candidates are eligible.

---

### Edge Cases

- No candidates are configured in the project.
- All candidates are omitted from campaign mode because the flag is set to true.
- A candidate changes multiple comparison axes and would normally require mixed-variant confirmation.
- Baseline run succeeds but one or more candidate runs fail.
- CSV report export fails after a run completes.
- Excel comparison report creation fails after successful CSV exports.
- Automatic human review is enabled and each run would normally select review items.
- A user wants to skip sync before the campaign because project assets are already current.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: The feature applies to existing evaluation project YAML files with a baseline, candidates, dataset, prompts, evaluators, and review policy.
- **Dataset**: Campaign mode MUST use the same dataset configured for ordinary baseline and candidate runs.
- **Langfuse Logging**: Campaign mode MUST preserve the same trace, observation, score, run metadata, evaluator metadata, baseline reference, and comparison metadata behavior as separate baseline and candidate runs.
- **Prompt and Evaluator Versioning**: Campaign mode MUST preserve the same prompt version and evaluator version associations currently recorded for individual runs.
- **Baseline**: Campaign mode MUST create a new baseline run first and use that exact baseline run ID for all included candidate runs in the campaign.
- **Human Review**: Campaign mode MUST preserve existing automatic human review behavior unless the user chooses an existing skip option for the campaign.

### Functional Requirements

- **FR-001**: Users MUST be able to start a campaign for a project with a single command.
- **FR-002**: Campaign mode MUST run the project baseline before any candidate runs.
- **FR-003**: Campaign mode MUST run every candidate whose project YAML entry omits `exclude-from-campaign` or has `exclude-from-campaign: false`.
- **FR-004**: Candidates with `exclude-from-campaign: true` MUST be skipped by campaign mode.
- **FR-005**: Candidates that omit `exclude-from-campaign` MUST default to included in campaign mode.
- **FR-006**: Campaign mode MUST use the newly created campaign baseline run ID as the baseline reference for every included candidate run.
- **FR-007**: Campaign mode MUST export a CSV report for the baseline and for each included candidate unless the user explicitly disables report generation for the campaign.
- **FR-008**: Campaign mode MUST create an Excel comparison workbook after all attempted runs using the campaign baseline run ID and the CSV reports available in the configured reports directory.
- **FR-009**: Campaign mode MUST surface the same Excel report warnings that the standalone Excel report target would surface, including missing candidates or missing numeric scores.
- **FR-010**: Campaign mode MUST show a final summary with baseline run ID, included candidate run IDs, skipped candidates, failed candidates, CSV report paths, and Excel workbook path when available.
- **FR-011**: Campaign mode MUST stop before running a baseline when no candidates are eligible, unless a future option explicitly requests a baseline-only campaign.
- **FR-012**: Campaign mode MUST report candidate failures without discarding successful baseline or candidate outputs.
- **FR-013**: Campaign mode MUST support the existing skip-sync behavior for users who know project assets are already current.
- **FR-014**: Campaign mode MUST support the existing skip-human-review behavior for users who do not want automatic review selection during campaign runs.
- **FR-015**: Campaign mode MUST handle mixed-variant confirmation consistently with ordinary candidate runs.
- **FR-016**: Project validation MUST accept `exclude-from-campaign` only as a boolean candidate-level setting.

### Key Entities *(include if feature involves data)*

- **Campaign Run**: A coordinated operation that includes one new baseline run, zero or more attempted candidate runs, CSV report exports, skipped candidate records, failed candidate records, and one optional Excel workbook.
- **Campaign Candidate Setting**: Candidate-level project YAML setting named `exclude-from-campaign` that determines whether campaign mode includes the candidate.
- **Campaign Summary**: User-facing output that records run IDs, candidate statuses, report paths, warnings, and final workbook path.
- **Excel Comparison Workbook**: The workbook generated from campaign CSV reports after campaign execution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can run a baseline, all eligible candidates, CSV exports, and Excel comparison workbook generation with one command.
- **SC-002**: In a project with three candidates where two are included or unspecified and one is excluded, campaign mode runs exactly two candidates.
- **SC-003**: Candidate runs created by campaign mode all reference the campaign baseline run ID in their CSV reports and comparison metadata.
- **SC-004**: The final campaign summary identifies every candidate as included, skipped, or failed.
- **SC-005**: When all runs succeed and numeric score columns exist, the generated Excel workbook compares the baseline and all successful campaign candidates.
- **SC-006**: When no candidates are eligible, the command exits without creating an unnecessary baseline run and explains why.

## Assumptions

- The campaign command is a new mode or target in the existing command-line workflow.
- `exclude-from-campaign` is intentionally opt-out by using a default value of false.
- Existing candidate run compatibility checks, mixed-variant confirmation behavior, sync behavior, report export behavior, and human review behavior remain authoritative.
- The Excel workbook should be generated from local CSV reports after run completion, using the existing Excel report capability.
- Failed candidate runs should not prevent users from inspecting successful run outputs, but they should be visible in the final command outcome.
