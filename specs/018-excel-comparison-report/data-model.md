# Data Model: Excel Comparison Report

## BaselineRunSelection

Represents the user's request to build a workbook for a baseline run.

Fields:

- `baseline_run_id`: Required run identifier, expected to match a baseline report `run_id`.
- `reports_dir`: Directory searched for harness CSV reports. Defaults to `reports`.
- `output_path`: Desired workbook path. Required or derived from the baseline run ID.
- `overwrite`: Whether an existing workbook at `output_path` may be replaced.

Validation rules:

- `baseline_run_id` must be non-empty.
- `reports_dir` must exist and be readable.
- `output_path` must have an Excel workbook extension.
- Existing `output_path` is an error unless `overwrite` is enabled.

## CsvReportInput

Represents one discovered harness CSV report.

Fields:

- `path`: Local CSV file path.
- `run_id`: Run ID found in report rows.
- `run_type`: Baseline or candidate, inferred from report rows and baseline reference.
- `baseline_run_id`: Candidate baseline reference when present.
- `rows`: Parsed report rows.
- `row_count`: Number of parsed rows.
- `columns`: Header fields from the CSV.

Validation rules:

- File must be readable as CSV with a header row.
- Report must contain a `run_id` column.
- Baseline report must have at least one row whose `run_id` equals `baseline_run_id`.
- Candidate report is associated when at least one row has `baseline_run_id` equal to the selected baseline run ID.
- A malformed report is reported with its path and does not silently contribute partial data.

## RunSummary

Represents one row on the first workbook tab.

Fields:

- `run_id`
- `run_type`
- `project`
- `project_version`
- `scenario_group`
- `scenario_name`
- `scenario_display_name`
- `dataset_name`
- `dataset_version`
- `provider`
- `model`
- `model_name`
- `temperature`
- `parameter_identity`
- `generation_parameter_hash`
- `variant_identity`
- `prompt_version`
- `prompt_shape`
- `prompt_artifact_type`
- `prompt_artifact_name`
- `prompt_local_path`
- `prompt_content_identity`
- `prompt_managed_name`
- `langfuse_prompt_name`
- `langfuse_prompt_version`
- `langfuse_prompt_labels`
- `evaluator_set_id`
- `baseline_run_id`
- `source_report`
- `included_row_count`
- `comparison_warning`

Validation rules:

- Exactly one summary row is produced per included report.
- Fields are populated from the first non-empty value across report rows for that run.
- Missing metadata is left blank and does not block workbook generation.
- `comparison_warning` is populated when project, dataset, prompt, or evaluator context differs from the baseline summary.

## CombinedReportRow

Represents one source CSV row copied into the combined-data worksheet.

Fields:

- All source CSV columns from all discovered reports.
- `source_report`: Path to the source report file.
- `included_run_id`: Run ID used for workbook grouping.
- `included_run_type`: Baseline or candidate.

Validation rules:

- The combined worksheet contains the union of all discovered CSV columns.
- Missing values for columns not present in a source CSV are blank.
- Row order is stable: baseline report rows first, then candidate reports sorted by run ID and path.

## ScoreObservation

Represents one numeric score value normalized for PivotTable input.

Fields:

- `run_id`
- `run_label`
- `run_type`
- `score_name`
- `score_value`
- `source_report`
- `trace_id`
- `item_id`

Validation rules:

- Score columns are source columns named `score_<name>`.
- Columns ending in `_comment` are excluded.
- Values must parse as numeric to become `score_value`.
- Blank, missing, or non-numeric score values are omitted from score observations.
- Missing run/score combinations remain blank in the PivotTable.

## WorkbookOutput

Represents the generated Excel workbook.

Worksheets:

- `Run Summary`: First tab; one row per included run.
- `Combined Data`: All report rows from the baseline and associated candidate reports.
- `Score Data`: Long-form normalized score observations used as the PivotTable source.
- `Score Pivot`: Native Excel PivotTable comparing average score by evaluator score and run.
- `Score Chart`: Clustered column chart based on the PivotTable.

Validation rules:

- `Run Summary` is the first worksheet.
- `Combined Data` includes all rows from included reports.
- `Score Pivot` exists when numeric score observations exist.
- `Score Chart` exists when numeric score observations exist.
- When no numeric scores exist, the workbook includes a clear no-score message instead of an empty misleading chart.
