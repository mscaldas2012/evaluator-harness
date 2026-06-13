# Research: HTML Comparison Report

## Decision: Shared Comparison Payload Before Format Rendering

**Decision**: Extract CSV discovery, baseline/candidate selection, run summary construction, combined row construction, numeric score observation extraction, warnings, and output path policy into a shared comparison report layer. Excel and HTML renderers consume that same payload.

**Rationale**: The existing Excel module already contains the canonical behavior for finding the baseline CSV, selecting candidates by `baseline_run_id`, detecting numeric `score_*` columns, preserving missing scores, and surfacing warnings. Reusing that logic prevents the HTML report from drifting away from Excel semantics and keeps campaign mode from having two separate discovery paths.

**Alternatives considered**:

- Duplicate the Excel report logic into an HTML module. Rejected because future changes to CSV report shape, warnings, or score detection would need parallel edits.
- Make the HTML renderer parse CSV files directly. Rejected because it would bypass the existing report contract and increase test surface.

## Decision: Keep Format-Specific Renderers Separate

**Decision**: Keep Excel workbook writing and HTML document rendering separate behind shared payload/result types.

**Rationale**: Excel requires native workbook automation to create PivotTables and charts, while HTML needs self-contained markup, styling, and client-side or static chart representation. A forced generic renderer abstraction would hide important differences without reducing meaningful complexity.

**Alternatives considered**:

- One generic report writer with many conditional branches. Rejected because the output formats have different validation, dependencies, file extensions, and visual constraints.
- Replace Excel generation with HTML-only. Rejected because existing Excel behavior and campaign default must remain available.

## Decision: Add a General Comparison Report Command and Preserve `excel-report`

**Decision**: Add a new standalone comparison report command that accepts a report format selection of `excel`, `html`, or `both`, and keep `excel-report` working as compatibility behavior that delegates to the Excel path.

**Rationale**: The user asked for a better coding design without breaking existing behavior. A general command gives a single documented path for multi-format generation, while preserving `excel-report` avoids breaking existing scripts and docs references.

**Alternatives considered**:

- Add only `html-report` beside `excel-report`. Rejected because `both` would require either two commands or special campaign-only logic.
- Rename `excel-report` and remove the old command. Rejected because it creates unnecessary migration work.

## Decision: Campaign Defaults to Excel Only

**Decision**: Campaign mode continues to generate Excel only when no final report format is specified. Users can explicitly request `html` or `both`.

**Rationale**: This matches the accepted clarification and preserves the current campaign behavior. HTML becomes an opt-in deliverable, avoiding surprise for current users who rely on Excel artifacts.

**Alternatives considered**:

- Default to HTML only. Rejected because it changes current behavior.
- Default to both. Rejected because it creates an extra artifact and can trigger more overwrite conflicts without user intent.

## Decision: Self-Contained HTML Report

**Decision**: Generate a single self-contained `.html` file with embedded CSS and data needed to render the report. Avoid external CDN dependencies.

**Rationale**: Report generation is local-first and should work in offline or restricted environments. A single file is easy to share, archive, and open in a browser. It also keeps the harness from becoming a web application.

**Alternatives considered**:

- Generate a folder with assets and JavaScript bundles. Rejected because it adds file management complexity and a build-like artifact shape.
- Reference external chart libraries by CDN. Rejected because network access may be restricted and report rendering would no longer be self-contained.

## Decision: Use Static SVG or Inline HTML/CSS for Charts

**Decision**: Render the score chart as deterministic inline markup, preferably SVG generated from the shared score aggregate data.

**Rationale**: Inline SVG keeps the report self-contained, testable, and browser-native without adding dependencies. It also allows accessibility labels and visual styling to be validated from generated HTML.

**Alternatives considered**:

- Add a JavaScript chart dependency. Rejected for v1 because the required chart is a simple grouped score comparison and can be generated statically.
- Use canvas. Rejected because it is harder to test and less accessible in a static report.

## Decision: Refined Editorial Dashboard Aesthetic

**Decision**: Use a polished, restrained editorial dashboard aesthetic: strong typography hierarchy, dense but readable tables, purposeful accent colors, clear baseline/candidate distinction, and no generic decorative hero treatment.

**Rationale**: The HTML report is an evaluation artifact for reviewers and stakeholders. It should look presentation-ready while prioritizing scanability, comparison, and repeated review. The installed frontend-design guidance favors intentional visual direction; for this domain, refined dashboard design is more appropriate than a marketing page.

**Alternatives considered**:

- Plain unstyled HTML. Rejected because the user explicitly requires visual appeal.
- Highly animated or decorative app-like UI. Rejected because generated reports should remain stable, printable, and easy to review.
