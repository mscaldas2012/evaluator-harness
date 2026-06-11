# Quickstart: Excel Comparison Report

## Prerequisites

- Baseline and candidate CSV reports already exist locally.
- Candidate reports include `baseline_run_id` values that reference the baseline run.
- Microsoft Excel is installed on the local Windows machine so the workbook can contain a native PivotTable.

## Generate Reports

Run a baseline and one or more candidates as usual. Reports are generated automatically unless `--no-report` is used.

```powershell
uv run python run_experiment.py run `
  --project configs/projects/dfe-general-public.yaml `
  --mode baseline
```

Example baseline output:

```text
run: baseline-7140f0ce98a9
report: reports/dfe-general-public/baseline-7140f0ce98a9.csv
```

Run candidates against that baseline.

```powershell
uv run python run_experiment.py run `
  --project configs/projects/dfe-general-public.yaml `
  --mode candidate `
  --candidate <candidate-name> `
  --baseline baseline-7140f0ce98a9
```

## Create The Workbook

```powershell
uv run python run_experiment.py excel-report `
  --baseline baseline-7140f0ce98a9 `
  --reports-dir reports/dfe-general-public `
  --output reports/dfe-general-public/baseline-7140f0ce98a9-comparison.xlsx
```

Expected output:

```text
excel-report: reports/dfe-general-public/baseline-7140f0ce98a9-comparison.xlsx
baseline: baseline-7140f0ce98a9
reports: 3
rows: 300
score-observations: 3300
```

## Recreate The Workbook

Use `--overwrite` when recreating the same workbook path.

```powershell
uv run python run_experiment.py excel-report `
  --baseline baseline-7140f0ce98a9 `
  --reports-dir reports/dfe-general-public `
  --output reports/dfe-general-public/baseline-7140f0ce98a9-comparison.xlsx `
  --overwrite
```

## Workbook Tabs

1. `Run Summary`: first tab; baseline and candidate run metadata.
2. `Combined Data`: all rows from included baseline and candidate CSV reports.
3. `Score Data`: normalized score rows used by the PivotTable.
4. `Score Pivot`: native Excel PivotTable comparing average scores by run.
5. `Score Chart`: clustered column chart based on the PivotTable.

## Expected Warnings

If no candidates are associated with the baseline:

```text
warning: no associated candidate reports found
```

If no numeric scores are available:

```text
warning: no numeric score columns found
```

## Troubleshooting

- If the baseline report cannot be found, confirm the CSV exists in `--reports-dir` and contains `run_id` matching `--baseline`.
- If candidates are missing, confirm their CSV reports contain `baseline_run_id` matching the baseline run ID.
- If native Excel automation is unavailable, run the command on a Windows workstation with Microsoft Excel installed.
- If the output file already exists, either choose a new `--output` path or pass `--overwrite`.
