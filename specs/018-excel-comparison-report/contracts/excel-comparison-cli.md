# Contract: Excel Comparison CLI

## Command

```powershell
uv run python run_experiment.py excel-report `
  --baseline baseline-7140f0ce98a9 `
  --reports-dir reports `
  --output reports/baseline-7140f0ce98a9-comparison.xlsx
```

## Purpose

Create one Excel workbook from existing harness CSV reports for a baseline run and all locally available candidate reports associated with that baseline.

## Inputs

| Option | Required | Description |
|--------|----------|-------------|
| `--baseline` | Yes | Baseline run ID used to find the baseline report and associated candidate reports. |
| `--reports-dir` | No | Directory to scan for CSV reports. Defaults to `reports`. |
| `--output` | No | Workbook output path. Defaults to a baseline-specific `.xlsx` path under the reports directory. |
| `--overwrite` | No | Permit replacing an existing output workbook. |

## Discovery Rules

1. Scan `--reports-dir` for `*.csv`.
2. Identify the baseline report by `run_id == --baseline`.
3. Identify candidate reports by `baseline_run_id == --baseline`.
4. Include the baseline report first, then associated candidates sorted by run ID and path.
5. Ignore unrelated CSV reports.

## Successful Output

Console output MUST include:

```text
excel-report: <output-path>
baseline: <baseline-run-id>
reports: <included-report-count>
rows: <combined-row-count>
score-observations: <numeric-score-count>
```

If no candidate reports are found, console output MUST also include:

```text
warning: no associated candidate reports found
```

If no numeric scores are found, console output MUST also include:

```text
warning: no numeric score columns found
```

## Workbook Contract

The workbook MUST contain:

1. `Run Summary` as the first worksheet.
2. `Combined Data` worksheet containing all rows from included CSV reports.
3. `Score Data` worksheet when numeric score observations exist.
4. `Score Pivot` worksheet with a native Excel PivotTable when numeric score observations exist.
5. `Score Chart` worksheet with a clustered column chart when numeric score observations exist.

## Error Output

The command MUST exit with a non-zero status and actionable message when:

- `--baseline` is missing or blank.
- `--reports-dir` does not exist.
- No baseline report is found for the baseline run ID.
- A discovered CSV is unreadable or malformed.
- `--output` exists and `--overwrite` is not provided.
- Native Excel automation is unavailable.

Example:

```text
No baseline CSV report found for baseline-7140f0ce98a9 in reports
```

## Non-Goals

- Does not run baseline or candidate experiments.
- Does not create CSV reports.
- Does not call Langfuse.
- Does not create or update evaluator scores.
- Does not route human review items.
