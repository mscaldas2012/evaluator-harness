# Data Model: Campaign Mode

## ModelConfig

Existing candidate model configuration.

### New Field

- `exclude_from_campaign: bool = false`
  - YAML alias: `exclude-from-campaign`
  - Applies only to candidate entries.
  - `false` or omitted means the candidate is included in campaign mode.
  - `true` means the candidate is skipped by campaign mode.

### Validation

- Must be boolean when present.
- Existing model/provider/auth/parameter validation remains unchanged.

## CampaignCandidateSelection

Represents the candidate selection decision for campaign mode.

### Fields

- `candidate_name: str`
- `included: bool`
- `reason: str`

### Rules

- Included when `exclude_from_campaign is False`.
- Skipped when `exclude_from_campaign is True`.

## CampaignRunResult

Top-level result returned by campaign orchestration.

### Fields

- `baseline_run: RunResult | None`
- `candidate_runs: list[CampaignCandidateRun]`
- `skipped_candidates: list[CampaignCandidateSelection]`
- `csv_reports: list[ExportResult]`
- `excel_report: WorkbookOutput | None`
- `warnings: list[str]`

### State Rules

- If no candidates are eligible, `baseline_run` is `None`, `candidate_runs` is empty, and no CSV or Excel report is created.
- If baseline fails before producing a run result, no candidate runs are attempted.
- Successful candidate runs always reference `baseline_run.run_id`.
- Excel report is attempted after all included candidate runs have been attempted and at least the baseline CSV report exists.

## CampaignCandidateRun

Captures one included candidate's campaign outcome.

### Fields

- `candidate_name: str`
- `run_result: RunResult | None`
- `csv_report: ExportResult | None`
- `status: "completed" | "failed"`
- `message: str | None`

### State Rules

- `completed` requires a candidate run result.
- `failed` includes an actionable message.
- CSV report may be absent when export fails after a completed candidate run.

## Campaign Summary Output

User-facing CLI output assembled from `CampaignRunResult`.

### Required Output Fields

- Baseline run ID when present.
- Candidate run IDs for successful candidates.
- Skipped candidate names with reasons.
- Failed candidate names with messages.
- CSV report paths.
- Excel workbook path when created.
- Excel warnings when present.
