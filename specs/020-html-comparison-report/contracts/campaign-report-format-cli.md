# Contract: Campaign Report Format CLI

## Command

```powershell
uv run python run_experiment.py campaign `
  --project configs/projects/rewrite_quality.yaml `
  --report-format html
```

## Purpose

Run a campaign and choose which final comparison artifact formats are generated after CSV exports.

## Options

| Option | Required | Description |
|--------|----------|-------------|
| `--project` | Yes | Project YAML path or shorthand. |
| `--report-format` | No | Final artifact format: `excel`, `html`, or `both`. Defaults to `excel`. |
| `--skip-sync` | No | Skip dataset and score-config sync before each run. |
| `--skip-human-review` | No | Disable automatic human review selection for campaign runs. |
| `--no-report` | No | Do not export CSV reports or create final comparison artifacts. |
| `--overwrite` | No | Permit replacing existing final comparison artifacts. |
| `--confirm-mixed-variant` | No | Permit included candidates that change prompt plus another comparison axis. |

## Execution Rules

1. If no candidates are eligible, exit before running a baseline.
2. Run the baseline first.
3. Run included candidates against the campaign baseline.
4. Export per-run CSV reports unless `--no-report` is passed.
5. Generate final report artifacts from the campaign baseline run ID and campaign report directory unless `--no-report` is passed.
6. Default final artifact generation is Excel only.
7. `--report-format html` generates HTML only.
8. `--report-format both` generates Excel and HTML from the same CSV reports.

## Successful Output

Excel-only output:

```text
campaign: completed
baseline: <baseline-run-id>
candidate: <candidate-name> <candidate-run-id>
report: <csv-path>
excel-report: <xlsx-path>
```

HTML-only output:

```text
campaign: completed
baseline: <baseline-run-id>
candidate: <candidate-name> <candidate-run-id>
report: <csv-path>
html-report: <html-path>
```

Both formats:

```text
campaign: completed
baseline: <baseline-run-id>
candidate: <candidate-name> <candidate-run-id>
report: <csv-path>
excel-report: <xlsx-path>
html-report: <html-path>
```

## Failure Output

Unsupported report format values MUST fail before running the campaign:

```text
Unsupported report format '<value>'. Supported formats: excel, html, both.
```

If final artifact generation fails after successful runs and CSV exports, campaign mode MUST preserve successful CSV outputs and include a warning:

```text
warning: <message>
```
