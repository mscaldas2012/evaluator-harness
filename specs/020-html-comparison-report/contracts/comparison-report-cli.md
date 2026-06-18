# Contract: Comparison Report CLI

## Command

```powershell
uv run python run_experiment.py comparison-report `
  --project rewrite-quality `
  --baseline baseline-7140f0ce98a9 `
  --format html
```

## Purpose

Create final comparison artifacts from existing local CSV reports without rerunning experiments. Supported final formats are Excel, HTML, and both.

## Options

| Option | Required | Description |
|--------|----------|-------------|
| `--baseline` | Yes | Baseline run ID used to find the baseline CSV and associated candidate CSVs. |
| `--format` | No | Final artifact format: `excel`, `html`, or `both`. Defaults to `excel`. |
| `--project` | No | Project path or shorthand used to derive `reports/<project-name>/` when `--reports-dir` is omitted. |
| `--reports-dir` | No | Directory containing CSV reports. Overrides the project-derived report directory. |
| `--output` | No | Explicit output file path for single-format generation. Invalid with `--format both`. |
| `--output-dir` | No | Directory for generated artifacts. Useful with `--format both`. |
| `--overwrite` | No | Permit replacing existing generated final artifacts. |

## Selection Rules

1. Resolve the report directory from `--reports-dir`, or from `--project`, or use `reports`.
2. Find exactly one baseline CSV whose `run_id` matches `--baseline`.
3. Include each candidate CSV whose `baseline_run_id` matches `--baseline`.
4. Sort included candidates by run ID after the baseline.
5. Use the same included reports for every requested final format.

## Output Rules

1. Excel output uses `.xlsx`.
2. HTML output uses `.html`.
3. Default output names are:
   - `<baseline-run-id>-comparison.xlsx`
   - `<baseline-run-id>-comparison.html`
4. Existing output files are errors unless `--overwrite` is passed.
5. `--output` is accepted only for `--format excel` or `--format html`.
6. `--output-dir` controls where default output names are written.

## Successful Output

Console output MUST include one line per generated final artifact:

```text
excel-report: <xlsx-path>
html-report: <html-path>
baseline: <baseline-run-id>
reports: <included-report-count>
rows: <combined-row-count>
score-observations: <numeric-score-observation-count>
```

Warnings MUST be surfaced as:

```text
warning: <message>
```

## Failure Output

Unsupported format values MUST fail with a message listing supported formats:

```text
Unsupported report format '<value>'. Supported formats: excel, html, both.
```

Missing or malformed CSV inputs MUST fail with file-specific messages.

## Compatibility Command

The existing command remains available:

```powershell
uv run python run_experiment.py excel-report `
  --project rewrite-quality `
  --baseline baseline-7140f0ce98a9
```

It is equivalent to:

```powershell
uv run python run_experiment.py comparison-report `
  --project rewrite-quality `
  --baseline baseline-7140f0ce98a9 `
  --format excel
```
