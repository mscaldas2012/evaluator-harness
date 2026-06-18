# Implementation Plan: HTML Comparison Report

**Branch**: `020-html-comparison-report` | **Date**: 2026-06-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/020-html-comparison-report/spec.md`

## Summary

Add a browser-viewable HTML comparison report that uses the same baseline-run CSV discovery, run summary extraction, score normalization, warnings, and overwrite rules as the existing Excel comparison workbook. Refactor the current Excel-only report module into shared comparison-report preparation plus format-specific renderers, add a standalone comparison report CLI that can produce Excel, HTML, or both while preserving `excel-report`, and extend campaign mode with a final report format option that defaults to Excel only.

The HTML output will be a self-contained local report file with a polished dashboard-style layout: first-view run context, run summary, pivot-style average score table, and chart. HTML report implementation MUST use the installed `frontend-design` skill guidance before coding the renderer, committing to a refined editorial dashboard aesthetic with intentional typography, restrained but memorable visual hierarchy, clear baseline/candidate distinction, and a presentation-ready composition. It will not require Microsoft Excel and will not contact Langfuse or model providers.

## Technical Context

**Language/Version**: Python 3.11+ as configured by `pyproject.toml`

**Primary Dependencies**: Standard library CSV/path/HTML/JSON handling; Typer CLI integration; existing `pywin32` Windows Excel automation for `.xlsx`; no required runtime web framework

**Python Environment Management**: Use `uv` for environment management, dependency setup, lockfile management, and command execution. Prefer `uv sync` and `uv run ...`.

**Storage**: Local CSV report files and generated local `.xlsx` and `.html` report files only

**Testing**: Pytest unit tests for shared report payload, HTML rendering, output validation, and campaign report selection; contract tests for CLI output and option validation; existing Excel tests retained

**HTML Design Quality**: Use `frontend-design` during implementation of `html_reports.py`. The generated report should avoid generic unstyled tables and generic AI-looking layouts; it should have an explicit aesthetic direction, cohesive CSS variables, polished typography, readable dense tables, accessible chart labels, responsive behavior for typical desktop and narrow browser widths, and clear visual treatment for warnings/no-score states.

**Target Platform**: Local developer workstation. HTML report generation is cross-platform and browser-viewable. Excel workbook generation remains Windows plus Microsoft Excel for native PivotTable/chart creation.

**Project Type**: Local Python CLI

**Performance Goals**: Generate HTML or Excel comparison artifacts from typical harness CSV reports in under 2 minutes; support one baseline and at least 10 associated candidates with up to 10,000 combined report rows

**Constraints**: Must not contact Langfuse, model providers, evaluator services, or external CDNs during report generation; must not rerun experiments; must avoid overwriting existing output files unless explicitly requested; must keep generated HTML self-contained and readable without a build step

**Visual Verification**: Planning and tasks must include browser/screenshot inspection of a generated sample HTML report. Verification should check first-view composition, table legibility, chart readability, warning states, no-score states, and absence of incoherent overlap or clipped text at desktop and narrow widths.

**Scale/Scope**: One baseline run ID per comparison report operation; all associated candidate CSV reports found in the selected reports directory; average numeric score comparison only; no hosted web app, live filtering service, or statistical significance analysis

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature packages already-exported local CSV reports after Langfuse-backed runs and scores exist. It does not replace Langfuse traces, evaluator execution, dashboards, scoring, or system-of-record behavior.
- **Thin harness scope**: PASS. The feature remains a local Python CLI flow plus small local renderer modules. No service, API, database, or orchestration framework is introduced.
- **Dataset simplicity**: PASS. Dataset requirements do not change; the feature consumes existing CSV report exports.
- **Reproducibility metadata**: PASS. The run summary surfaces existing metadata from CSV reports, including run, baseline, model, parameter, dataset, and prompt fields when present.
- **Baseline-centric workflow**: PASS. Report selection remains driven by a baseline run ID, and candidates are included only when their baseline reference matches that ID.
- **Minimal local state**: PASS. New local state is limited to user-requested generated report files.
- **Human review awareness**: PASS. Reports preserve review-relevant source data where available and present scores as comparison artifacts, not objective truth.
- **Local-first execution**: PASS. Workflows run through `uv run python run_experiment.py ...` or the existing console script.

## Project Structure

### Documentation (this feature)

```text
specs/020-html-comparison-report/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- comparison-report-cli.md
|   `-- campaign-report-format-cli.md
`-- tasks.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
|-- cli.py                  # add comparison-report command and campaign format option
|-- runner.py               # campaign report format selection and result fields
|-- excel_reports.py        # keep compatibility facade and Excel writer
|-- comparison_reports.py   # shared discovery, payload, output orchestration
`-- html_reports.py         # self-contained HTML renderer

tests/
|-- contract/
|   |-- test_cli_comparison_report.py
|   |-- test_cli_campaign.py
|   `-- test_cli_excel_comparison.py
|-- integration/
|   `-- test_html_comparison_report.py
`-- unit/
    |-- test_comparison_reports.py
    |-- test_html_reports.py
    |-- test_excel_reports.py
    `-- test_campaign.py

docs/
`-- user-guide.md
```

**Structure Decision**: Use one shared comparison-report preparation layer for CSV discovery, run summaries, combined rows, score observations, warnings, and output path validation. Keep Excel and HTML rendering separate because their output mechanics differ materially: Excel uses native workbook automation for PivotTables/charts, while HTML generates a self-contained browser document.

## Phase 0: Research

See [research.md](./research.md).

## Phase 1: Design

See [data-model.md](./data-model.md), [contracts/comparison-report-cli.md](./contracts/comparison-report-cli.md), [contracts/campaign-report-format-cli.md](./contracts/campaign-report-format-cli.md), and [quickstart.md](./quickstart.md).

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Design consumes exported data and does not duplicate Langfuse scoring, trace inspection, or evaluator execution.
- **Thin harness scope**: PASS. Design adds local modules and CLI options only. The HTML report is static, not a hosted application.
- **Dataset simplicity**: PASS. No dataset behavior changes.
- **Reproducibility metadata**: PASS. Shared payload explicitly models run summaries and source report paths.
- **Baseline-centric workflow**: PASS. Baseline run ID remains the selector across standalone and campaign flows.
- **Minimal local state**: PASS. Generated `.html` and `.xlsx` artifacts are explicit user outputs.
- **Human review awareness**: PASS. Source report data is preserved for audit and follow-up in Langfuse.
- **Local-first execution**: PASS. HTML generation requires only local Python; Excel retains existing local Excel requirement.

## Complexity Tracking

No constitution violations recorded.
