# Implementation Plan: Excel Comparison Report

**Branch**: `018-excel-comparison-report` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/018-excel-comparison-report/spec.md`

## Summary

Add a dedicated `run_experiment.py` target that accepts a baseline run ID, scans an existing reports directory for the matching baseline CSV and candidate CSV reports that reference that baseline, and creates a local Excel workbook. The workbook will put run metadata first, preserve all combined report rows, create a native Excel PivotTable comparing average evaluator scores per run, and add a clustered column chart based on that PivotTable.

The design keeps discovery and score normalization in pure Python using CSV/filesystem operations, and isolates native Excel PivotTable/chart creation behind a small Windows Excel automation adapter. This is necessary because openpyxl preserves existing PivotTables but does not intend client code to create new ones, while the native Excel object model supports creating PivotCaches, PivotTables, and embedded charts.

## Technical Context

**Language/Version**: Python 3.11+ as configured by `pyproject.toml`

**Primary Dependencies**: Standard library CSV/path handling; `typer` CLI integration; Windows-only Excel automation dependency (`pywin32`) for native PivotTable and chart authoring

**Python Environment Management**: For Python features, use `uv` for environment management, dependency setup, lockfile management, and command execution. Prefer `uv sync` and `uv run ...`.

**Storage**: Local report CSV files and generated `.xlsx` workbook files only

**Testing**: `pytest` unit tests for report discovery, CSV normalization, score detection, and run summary extraction; contract tests for the CLI target; adapter tests with a fake Excel writer

**Target Platform**: Local Windows workstation with Microsoft Excel installed for native PivotTable generation; non-Windows or missing Excel reports a clear actionable error

**Project Type**: Local Python CLI

**Performance Goals**: Create a workbook from typical harness reports in under 2 minutes; handle at least one baseline report and 10 associated candidate reports with up to 10,000 combined rows

**Constraints**: Must not contact Langfuse, model providers, or evaluator services; must not rerun reports; must avoid overwriting an existing workbook unless explicitly requested; must preserve all discovered report rows in the combined-data worksheet

**Scale/Scope**: One baseline run ID per workbook; all associated candidate CSV reports found in the selected report directory; average numeric score comparison only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature does not replace Langfuse dashboards or scoring. It packages already-exported local CSV reports into a shareable workbook after Langfuse-backed runs and scores already exist. It does not create traces, scores, or local evaluator logic.
- **Thin harness scope**: PASS. The design adds one CLI target plus small local modules for report discovery, normalization, and workbook writing. No services, APIs, databases, or orchestration are introduced.
- **Dataset simplicity**: PASS. The feature consumes existing CSV report exports and does not alter dataset requirements.
- **Reproducibility metadata**: PASS. The first worksheet surfaces existing run metadata from report CSVs, including model, parameters, prompt, dataset, and baseline relationships.
- **Baseline-centric workflow**: PASS. The baseline run ID is the primary selector, and candidate reports are included only when their baseline reference matches that run ID.
- **Minimal local state**: PASS. The only new artifact is an explicitly generated `.xlsx` workbook. Langfuse remains the system of record for traces and scores.
- **Human review awareness**: PASS. The workbook preserves review-relevant report fields where present but does not replace Langfuse trace inspection or Human Annotation Queues.
- **Local-first execution**: PASS. The workflow runs from `uv run python run_experiment.py ...` on a local workstation.

## Project Structure

### Documentation (this feature)

```text
specs/018-excel-comparison-report/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── excel-comparison-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
├── cli.py
├── excel_reports.py
└── exports.py

tests/
├── contract/
│   └── test_cli_excel_comparison.py
├── integration/
│   └── test_excel_comparison_workbook.py
└── unit/
    └── test_excel_reports.py
```

**Structure Decision**: Add a focused `excel_reports.py` module for report discovery, CSV normalization, score aggregation, and workbook writer orchestration. Keep CLI wiring in `cli.py`. Existing `exports.py` remains responsible for generating per-run CSV reports; the new module consumes those CSVs.

## Phase 0: Research

See [research.md](./research.md).

## Phase 1: Design

See [data-model.md](./data-model.md), [contracts/excel-comparison-cli.md](./contracts/excel-comparison-cli.md), and [quickstart.md](./quickstart.md).

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Design consumes exported data and does not duplicate Langfuse scoring or trace storage.
- **Thin harness scope**: PASS. Design uses local files and a single CLI workflow; native Excel automation is isolated behind one adapter.
- **Dataset simplicity**: PASS. No dataset behavior changes.
- **Reproducibility metadata**: PASS. Run summary fields are explicitly modeled and validated.
- **Baseline-centric workflow**: PASS. Candidate discovery is driven by `baseline_run_id`.
- **Minimal local state**: PASS. Generated workbook is a user-requested output artifact.
- **Human review awareness**: PASS. Combined data preserves trace and review-relevant columns for follow-up in Langfuse.
- **Local-first execution**: PASS. Requires local Python and, for native PivotTables, local desktop Excel.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Windows Excel automation dependency | The clarified requirement explicitly calls for a native Excel PivotTable, not a generated summary table. | openpyxl can preserve existing PivotTables but does not provide a creation API; pure Python summary tables would not satisfy the native PivotTable requirement. |
