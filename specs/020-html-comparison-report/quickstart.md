# Quickstart: HTML Comparison Report

## Prerequisites

Set up the Python environment:

```powershell
uv sync
```

Run or collect baseline and candidate CSV reports under the project report directory:

```text
reports/<project-name>/<run-id>.csv
```

## Generate HTML From Existing CSV Reports

```powershell
uv run python run_experiment.py comparison-report `
  --project rewrite-quality `
  --baseline baseline-7140f0ce98a9 `
  --format html
```

Expected output includes:

```text
html-report: reports\rewrite-quality\baseline-7140f0ce98a9-comparison.html
baseline: baseline-7140f0ce98a9
reports: 2
rows: 20
score-observations: 40
```

Open the generated `.html` file in a browser. It should include:

- Run context and high-level summary near the top
- Run Summary section
- Pivot-style average score table
- Score chart when numeric score data exists
- Clear warnings when candidates or numeric scores are unavailable

## HTML Design Review

Before accepting the HTML renderer implementation, use the `frontend-design`
skill guidance to review the generated report as a designed frontend artifact,
not only as a data export. The report should have a refined editorial dashboard
direction, clear typography hierarchy, polished table and chart presentation,
cohesive colors, accessible labels, and no clipped or overlapping text.

Inspect a generated report in a browser at desktop and narrow widths. Verify:

- The first view clearly communicates project, baseline, candidates, and score context.
- Run Summary and pivot-style score tables remain readable with multiple candidates.
- The chart is legible and visually aligned with the report style.
- Warning and no-score states look intentional rather than broken.
- The report remains self-contained and does not load external assets.

## Generate Both HTML and Excel

```powershell
uv run python run_experiment.py comparison-report `
  --project rewrite-quality `
  --baseline baseline-7140f0ce98a9 `
  --format both `
  --overwrite
```

Expected output includes both:

```text
excel-report: reports\rewrite-quality\baseline-7140f0ce98a9-comparison.xlsx
html-report: reports\rewrite-quality\baseline-7140f0ce98a9-comparison.html
```

## Keep Existing Excel Workflow

The existing Excel command remains supported:

```powershell
uv run python run_experiment.py excel-report `
  --project rewrite-quality `
  --baseline baseline-7140f0ce98a9
```

This remains Excel-only and requires Microsoft Excel on Windows for native PivotTable and chart creation.

## Use a Custom Report Directory

```powershell
uv run python run_experiment.py comparison-report `
  --baseline baseline-7140f0ce98a9 `
  --reports-dir reports/rewrite-quality `
  --format html `
  --output reports/rewrite-quality/baseline-7140f0ce98a9-review.html
```

## Run a Campaign With HTML Output

```powershell
uv run python run_experiment.py campaign `
  --project configs/projects/rewrite_quality.yaml `
  --report-format html
```

Campaign mode still exports per-run CSV reports and then creates the requested final artifact.

## Run a Campaign With Both Formats

```powershell
uv run python run_experiment.py campaign `
  --project configs/projects/rewrite_quality.yaml `
  --report-format both `
  --overwrite
```

The default campaign behavior remains Excel-only when `--report-format` is omitted.

## Verification Commands

Run focused tests:

```powershell
uv run pytest -p no:cacheprovider `
  tests/unit/test_comparison_reports.py `
  tests/unit/test_html_reports.py `
  tests/unit/test_excel_reports.py `
  tests/unit/test_campaign.py `
  tests/contract/test_cli_comparison_report.py `
  tests/contract/test_cli_campaign.py `
  tests/contract/test_cli_excel_comparison.py
```

Run the full suite when ready:

```powershell
uv run pytest -p no:cacheprovider
```
