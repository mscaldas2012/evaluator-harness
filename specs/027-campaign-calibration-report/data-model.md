# Data Model: Campaign Calibration Report

## CampaignManifest

Durable local record written by campaign execution and read by the later campaign calibration command.

**Fields**:
- `project_name`: Project display/name key from project config.
- `project_version`: Project config version.
- `baseline_run_id`: Baseline run ID used as campaign anchor.
- `reports_dir`: Local project report directory.
- `generated_at`: UTC timestamp when the manifest was written.
- `runs`: Ordered list of `CampaignRunReference` values, baseline first.
- `comparison_reports`: Optional paths to generated campaign comparison reports.
- `warnings`: Campaign execution warnings that may matter during calibration.

**Validation**:
- `baseline_run_id` is required and non-empty.
- Exactly one run reference has `role = "baseline"` and its `run_id` matches `baseline_run_id`.
- Candidate run references are optional.
- Paths are project-relative or absolute filesystem paths.

## CampaignRunReference

Identifies one run that belongs to a campaign.

**Fields**:
- `run_id`: Baseline or candidate run ID.
- `role`: `baseline` or `candidate`.
- `candidate_name`: Candidate config name when `role = "candidate"`.
- `status`: Campaign execution status such as `completed`, `failed`, or `skipped`.
- `csv_report_path`: Optional local CSV export path.
- `comparison_source_path`: Optional report/export artifact used to discover this run.
- `message`: Optional failure/skipped message from campaign execution.

**Validation**:
- `run_id` is required for processed runs.
- `candidate_name` is required for candidate references when known.
- Failed/skipped candidates may have no calibration outputs but must be reported as warnings.

## CampaignCalibrationRun

Top-level result for one post-campaign calibration command invocation.

**Fields**:
- `project_name`
- `project_version`
- `baseline_run_id`
- `source`: `manifest` or `fallback-artifacts`
- `run_references`: Ordered list of campaign run references.
- `run_results`: Ordered list of `CampaignRunCalibrationResult` values.
- `html_report_path`
- `started_at`
- `completed_at`
- `warnings`

**Validation**:
- Baseline reference must always be present.
- Baseline-only campaign calibration is valid.
- The result may contain run warnings without failing the command.

## CampaignRunCalibrationResult

Per-run capture and summary outcome inside a campaign calibration run.

**Fields**:
- `run_id`
- `role`
- `candidate_name`
- `snapshot_path`
- `summary_path`
- `snapshot_row_count`
- `summary_count`
- `paired_count`
- `pending_count`
- `status`: `completed`, `warning`, or `failed`.
- `warnings`

**Validation**:
- `completed` requires both snapshot and summary paths.
- `warning` can include zero paired coverage or missing annotations.
- `failed` records the error and does not block other run references unless the baseline cannot be processed at all.

## CampaignCalibrationReportPayload

Normalized data sent to the campaign calibration HTML renderer.

**Fields**:
- `baseline_run_id`
- `output_path`
- `generated_at`
- `run_results`
- `evaluator_summaries`: Flattened evaluator-level summary rows across runs.
- `paired_records`: Flattened paired calibration records across runs.
- `pending_records`: Optional pending/unpaired calibration records for warning detail.
- `warnings`

**Validation**:
- `output_path` must end in `.html`.
- Summary rows are grouped by run ID and evaluator name.
- Report includes completed and warning runs; failed/skipped runs appear in warnings.

## State Transitions

```text
Campaign completed
  -> manifest/run references available
  -> human annotations completed later in Langfuse
  -> campaign calibration capture starts from baseline run ID
  -> per-run snapshots overwritten from latest Langfuse state
  -> per-run summaries overwritten from latest snapshots
  -> campaign HTML report overwritten from latest summaries
```
