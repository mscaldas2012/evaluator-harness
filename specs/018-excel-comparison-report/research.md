# Research: Excel Comparison Report

## Decision: Use a baseline run ID to discover report CSVs

**Decision**: The Excel report target will accept a baseline run ID and a report search directory. It will find `baseline-<id>.csv` or any CSV whose row `run_id` matches the baseline ID, then include candidate CSVs whose `baseline_run_id` column matches that baseline ID.

**Rationale**: This matches the clarified user workflow and avoids requiring users to remember every candidate report path. It also keeps workbook recreation offline because it scans local CSV files only.

**Alternatives considered**:

- Explicit CSV file list: reliable but rejected because the user prefers passing only the baseline run ID.
- Query Langfuse for candidate runs: rejected because the feature must recreate workbooks as long as CSV reports exist and must not require live Langfuse access.
- Infer candidates from filename only: rejected because candidate association is already represented in report data via `baseline_run_id`.

## Decision: Use native Excel automation for PivotTable and chart creation

**Decision**: Generate native Excel PivotTables and clustered column charts through the Microsoft Excel object model, isolated behind a workbook writer adapter.

**Rationale**: The clarified requirement requires a native Excel PivotTable. openpyxl documentation states that it provides read support and preservation for PivotTables and that client code is not intended to create them. Microsoft Excel exposes PivotCache and PivotTable creation through its native object model. XlsxWriter is suitable for many XLSX authoring tasks, including worksheets and charts, but native PivotTable creation is not a documented core feature in its public table of contents.

**Sources**:

- openpyxl Pivot Tables: https://openpyxl.readthedocs.io/en/stable/pivot.html
- Microsoft PivotCaches.Create: https://learn.microsoft.com/en-us/office/vba/api/excel.pivotcaches.create
- Microsoft PivotCache.CreatePivotTable: https://learn.microsoft.com/en-us/office/vba/api/excel.pivotcache.createpivottable
- Microsoft ChartObjects.Add: https://learn.microsoft.com/en-us/office/vba/api/excel.chartobjects.add

**Alternatives considered**:

- Generated pivot-style worksheet: rejected by clarification because the workbook must contain a native Excel PivotTable.
- openpyxl-only workbook generation: rejected because PivotTable creation is not supported as a normal client workflow.
- Langfuse dashboard comparison: rejected for this feature because the user needs a standalone Excel artifact from existing CSV reports.

## Decision: Keep data preparation pure and testable

**Decision**: Separate CSV discovery, parsing, run summary extraction, score-column detection, and normalized score-row construction from the Excel automation adapter.

**Rationale**: Native Excel automation is platform-specific and hard to exercise in CI. The correctness of report selection and score comparison can be verified in pure unit and integration tests with fixture CSVs, while the Excel adapter can be covered by a fake adapter contract and optional local smoke testing.

**Alternatives considered**:

- Put all logic directly in the CLI command: rejected because it would make parsing, discovery, and workbook behavior difficult to test.
- Put all logic inside the Excel automation adapter: rejected because it would couple report semantics to platform-specific workbook operations.

## Decision: Normalize scores into long-form comparison data

**Decision**: Convert wide `score_<name>` CSV columns into long-form rows with fields such as `run_id`, `run_label`, `score_name`, and `score_value` before creating the PivotTable.

**Rationale**: A long-form source table is the natural input shape for an Excel PivotTable that averages values by score name and run. It also handles different evaluator score sets across runs by leaving missing combinations blank in the pivot.

**Alternatives considered**:

- Pivot directly from the combined wide report data: rejected because each score column would become a separate measure, making per-run comparison less consistent and harder to chart.
- Precompute averages only and pivot the aggregate table: rejected because the workbook should retain auditable source score rows for the PivotTable.

## Decision: Fail clearly when native Excel prerequisites are unavailable

**Decision**: If the user requests workbook generation on a machine without Windows Excel automation support, the command reports a clear actionable error rather than silently creating a non-native substitute.

**Rationale**: The spec requires a native Excel PivotTable. Producing a workbook without one would be misleading. A clear error preserves correctness and tells the user what is missing.

**Alternatives considered**:

- Automatically fall back to a generated summary worksheet: rejected because it contradicts the clarified native PivotTable requirement.
- Skip the PivotTable but create other tabs: rejected because the primary value of the target is the comparison workbook.
