# Langfuse Dashboard: Baseline vs Candidate Scores

Use this guide to create a Langfuse dashboard widget that compares baseline
scores against candidate variant scores.

## Prerequisites

Make sure each baseline and candidate run logs scores with consistent names,
for example:

- `overall_quality`
- `correctness`
- `rewrite_quality`
- `format_compliance`

Make sure the baseline/candidate identity is present on a Langfuse field that
is available as a widget **Breakdown Dimension**, such as:

- `version`: `baseline`, `candidate-a`, `candidate-b`
- `release`: `rewrite-quality-baseline`, `rewrite-quality-candidate-a`
- `tags`: `baseline`, `candidate-a`

Prefer `version` or `release` when possible, since they are more likely to be
available as score widget breakdown dimensions.

Current harness note: the harness records baseline/candidate identity in trace
metadata such as `run_type`, `model_name`, `variant_identity`, and
`baseline_reference`. It does not currently set first-class Langfuse
`version`, `release`, or `tags` fields on traces. If those metadata fields are
not available in the widget's **Breakdown Dimension** dropdown, use separate
filtered widgets or update the harness to set first-class Langfuse dimensions.

## Create the Score Widget

1. Open the Langfuse project.
2. Go to **Dashboards**.
3. Open the **Widgets** tab.
4. Click **New Widget**.
5. Choose data source **Evaluation Scores** or **Scores**.
6. Choose the score type:
   - Use numeric scores for averages, min/max, histograms, and similar charts.
   - Use categorical scores if the evaluator returns labels.
7. Set the metric:
   - Measure: `value`
   - Aggregation: `avg`
8. Add a filter for the score name:
   - `name = <your_score_name>`
   - Example: `name = rewrite_quality`
9. Add a **Breakdown Dimension**. This is Langfuse's widget UI term for
   grouping/splitting the chart:
   - Use `traceVersion` if baseline/candidate is logged as trace version.
   - Use `traceRelease` if baseline/candidate is logged as release.
   - Use `tags` if traces are tagged by variant.
10. Pick a chart:
    - Use a bar chart for direct baseline vs candidate comparison.
    - Use a line chart for comparison over time.
    - Use a pivot/table widget, if available, to compare multiple score names
      side by side.
11. Save the widget with a name such as `Rewrite quality by variant`.

## Create the Dashboard

1. Go back to the **Dashboards** tab.
2. Click **New Dashboard**.
3. Name it, for example, `Rewrite Quality Evaluation`.
4. Add the saved widget.
5. Repeat widget creation for each score name you want to compare, or use a
   table/pivot-style widget if the UI supports breakdowns by both score `name`
   and variant.
6. Set the dashboard time range wide enough to include the baseline and
   candidate experiment runs.

## Notes

If the goal is to compare exact Langfuse dataset runs or experiments, the
built-in **Experiment Compare** view is usually better than a custom dashboard.

Custom dashboards are best when baseline/candidate identity is encoded into
trace fields such as `version`, `release`, or tags.
