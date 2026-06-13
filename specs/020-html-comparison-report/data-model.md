# Data Model: HTML Comparison Report

## Baseline Run Selection

Represents the user request to build comparison artifacts for one baseline run.

**Fields**:

- `baseline_run_id`: Required non-empty run identifier.
- `reports_dir`: Directory containing harness-generated CSV reports.
- `formats`: Requested final artifact formats: `excel`, `html`, or `both`.
- `output_path`: Optional explicit output file path for single-format generation.
- `output_dir`: Optional output directory for multi-format generation.
- `overwrite`: Whether existing final artifacts may be replaced.

**Validation rules**:

- `baseline_run_id` must not be blank.
- `reports_dir` must exist and be a directory.
- `output_path` is valid only when exactly one final format is requested.
- Excel output paths must use `.xlsx`.
- HTML output paths must use `.html`.
- Existing output files require `overwrite`.

## CSV Report Input

Represents one harness-generated CSV report discovered in a report directory.

**Fields**:

- `path`: CSV file path.
- `run_id`: Run identifier read from the CSV.
- `run_type`: `baseline` or `candidate`, inferred when absent.
- `baseline_run_id`: Candidate baseline reference when present.
- `rows`: CSV rows as string-keyed values.
- `columns`: CSV header names in source order.

**Validation rules**:

- CSV must have a header row.
- CSV must include `run_id`.
- At least one row must provide a non-empty `run_id`.
- Malformed CSV errors must identify the affected file.

## Run Summary

Represents one summary entry for each included baseline or candidate report.

**Fields**:

- `run_id`
- `run_type`
- `baseline_run_id`
- `source_report`
- `row_count`
- `project`
- `project_version`
- `dataset`
- `dataset_version`
- `prompt_version`
- `model`
- `parameters`
- `candidate`
- `variant`

**Validation rules**:

- One run summary is produced for each included CSV report.
- Missing optional metadata is represented as `unknown` or unavailable, not as an error.
- Baseline summary appears before candidate summaries.

## Combined Report Row

Represents one original CSV row annotated with source report and included run identity.

**Fields**:

- `source_report`
- `included_run_id`
- `included_run_type`
- `values`

**Validation rules**:

- All source CSV columns are preserved.
- Extra columns from one report are allowed even if absent in other reports.

## Score Observation

Represents one numeric score value extracted from an included report row.

**Fields**:

- `run_id`
- `run_label`
- `run_type`
- `score_name`
- `score_value`
- `source_report`
- `trace_id`
- `item_id`

**Validation rules**:

- Numeric score columns are CSV columns beginning with `score_`.
- Score comment fields ending with `_comment` are excluded.
- Non-numeric or blank score values are skipped, not converted to zero.

## Score Aggregate

Represents average score values grouped for pivot-style report display.

**Fields**:

- `score_name`
- `run_id`
- `run_label`
- `average_score`
- `observation_count`

**Validation rules**:

- Average values are calculated only from numeric score observations.
- Missing score/run combinations remain blank or unavailable.
- Aggregates are stable for unchanged CSV input.

## Comparison Report Payload

Shared normalized data used by Excel and HTML renderers.

**Fields**:

- `baseline_run_id`
- `output_path`
- `run_summaries`
- `combined_rows`
- `score_observations`
- `score_aggregates`
- `warnings`
- `generated_at`

**Validation rules**:

- Payload generation does not write output artifacts.
- Payload generation does not contact Langfuse or model providers.
- Warnings include no-candidate, no-score, and metadata mismatch conditions.

## Comparison Report Output

Represents one generated final artifact.

**Fields**:

- `format`: `excel` or `html`
- `output_path`
- `report_count`
- `row_count`
- `score_observation_count`
- `warnings`

**Validation rules**:

- `format` matches the file extension.
- Output path is reported to CLI and campaign summaries.

## Campaign Report Selection

Represents final report generation choices during campaign mode.

**Fields**:

- `report_format`: `excel`, `html`, or `both`.
- `no_report`: Whether CSV and final report generation are disabled.
- `overwrite`: Whether final artifacts can replace existing files.

**State transitions**:

- Default state: `report_format=excel`, `no_report=false`.
- When `no_report=true`, no CSV reports or final report artifacts are generated.
- When `report_format=both`, successful campaign CSV reports feed both final artifact renderers.
