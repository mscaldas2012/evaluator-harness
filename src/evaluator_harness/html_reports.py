from __future__ import annotations

import json
from html import escape
from pathlib import Path

from evaluator_harness.comparison_reports import (
    ComparisonReportOutput,
    ComparisonReportPayload,
    ReportFormat,
    build_comparison_payload,
)
from evaluator_harness.errors import RuntimeDependencyError


class HtmlReportWriter:
    """Render a refined editorial dashboard as a self-contained HTML report."""

    def write(self, payload: ComparisonReportPayload) -> None:
        html = render_html_report(payload)
        payload.output_path.write_text(html, encoding="utf-8")


def create_html_report(
    baseline_run_id: str,
    *,
    reports_dir: Path = Path("reports"),
    output_path: Path | None = None,
    overwrite: bool = False,
    writer: HtmlReportWriter | None = None,
) -> ComparisonReportOutput:
    payload = build_comparison_payload(
        baseline_run_id,
        reports_dir=reports_dir,
        report_format=ReportFormat.HTML,
        output_path=output_path,
        overwrite=overwrite,
    )
    (writer or HtmlReportWriter()).write(payload)
    if not payload.output_path.exists():
        raise RuntimeDependencyError(
            f"HTML report creation completed but no file was found at {payload.output_path}."
        )
    return ComparisonReportOutput(
        format=ReportFormat.HTML.value,
        output_path=payload.output_path,
        report_count=len(payload.run_summaries),
        row_count=len(payload.combined_rows),
        score_observation_count=len(payload.score_observations),
        warnings=tuple(payload.warnings),
    )


def render_html_report(payload: ComparisonReportPayload) -> str:
    baseline = payload.run_summaries[0] if payload.run_summaries else None
    score_names = sorted({aggregate.score_name for aggregate in payload.score_aggregates})
    run_labels = [summary.run_id for summary in payload.run_summaries]
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{_e(payload.baseline_run_id)} comparison report</title>",
            "<style>",
            _css(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="report-shell">',
            _hero(payload, baseline),
            _warnings(payload),
            _summary_cards(payload),
            _run_summary_table(payload),
            _score_pivot_table(payload, score_names, run_labels),
            _chart_section(payload, score_names, run_labels),
            _combined_data_preview(payload),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _hero(payload: ComparisonReportPayload, baseline: object | None) -> str:
    project = getattr(baseline, "project", "unknown")
    dataset = getattr(baseline, "dataset", "unknown")
    candidates = max(0, len(payload.run_summaries) - 1)
    return f"""
<section class="hero-panel">
  <div class="report-kicker">Evaluator Harness Comparison</div>
  <div class="hero-grid">
    <div>
      <h1>{_e(project)} Score Review</h1>
      <p class="lede">Baseline <strong>{_e(payload.baseline_run_id)}</strong> compared against {_e(str(candidates))} candidate run{'' if candidates == 1 else 's'} from local CSV reports.</p>
    </div>
    <dl class="hero-facts">
      <div><dt>Dataset</dt><dd>{_e(dataset)}</dd></div>
      <div><dt>Generated</dt><dd>{_e(payload.generated_at)}</dd></div>
      <div><dt>Rows</dt><dd>{len(payload.combined_rows)}</dd></div>
      <div><dt>Scores</dt><dd>{len(payload.score_observations)}</dd></div>
    </dl>
  </div>
</section>"""


def _warnings(payload: ComparisonReportPayload) -> str:
    if not payload.warnings:
        return ""
    items = "\n".join(f"<li>{_e(warning)}</li>" for warning in payload.warnings)
    return f'<section class="notice-panel" aria-label="Report warnings"><h2>Review Notes</h2><ul>{items}</ul></section>'


def _summary_cards(payload: ComparisonReportPayload) -> str:
    candidate_count = max(0, len(payload.run_summaries) - 1)
    score_count = len({observation.score_name for observation in payload.score_observations})
    cards = [
        ("Included runs", str(len(payload.run_summaries))),
        ("Candidates", str(candidate_count)),
        ("Combined rows", str(len(payload.combined_rows))),
        ("Score dimensions", str(score_count)),
    ]
    return '<section class="metric-strip">' + "".join(
        f'<article class="metric-card"><span>{_e(label)}</span><strong>{_e(value)}</strong></article>'
        for label, value in cards
    ) + "</section>"


def _run_summary_table(payload: ComparisonReportPayload) -> str:
    headers = [
        "Run",
        "Type",
        "Model",
        "Candidate",
        "Variant",
        "Parameters",
        "Prompt",
        "Dataset",
        "Rows",
        "Source",
    ]
    rows = []
    for summary in payload.run_summaries:
        rows.append(
            [
                summary.run_id,
                summary.run_type,
                summary.model,
                summary.candidate,
                summary.variant,
                summary.parameters,
                summary.prompt_version,
                summary.dataset,
                str(summary.row_count),
                summary.source_report,
            ]
        )
    return _table_section("Run Summary", "Configuration context for every included run.", headers, rows)


def _combined_data_preview(payload: ComparisonReportPayload) -> str:
    if not payload.combined_rows:
        return ""
    source_columns: list[str] = []
    for row in payload.combined_rows[:20]:
        for key in row.values:
            if key not in source_columns:
                source_columns.append(key)
        if len(source_columns) >= 6:
            break
    source_columns = source_columns[:6]
    headers = ["Run", "Type", "Source", *source_columns]
    rows = [
        [
            row.included_run_id,
            row.included_run_type,
            row.source_report,
            *[row.values.get(column, "") for column in source_columns],
        ]
        for row in payload.combined_rows[:20]
    ]
    return _table_section(
        "Source Data Preview",
        "First report rows preserved from the combined CSV inputs for audit context.",
        headers,
        rows,
        wrapper="details",
    )


def _score_pivot_table(
    payload: ComparisonReportPayload,
    score_names: list[str],
    run_labels: list[str],
) -> str:
    if not payload.score_aggregates:
        return (
            '<section class="section-card"><h2>Score Pivot</h2>'
            f'<div class="empty-state">{_e(_score_empty_message(payload))}</div></section>'
        )
    aggregate_map = {
        (aggregate.score_name, aggregate.run_id): aggregate.average_score
        for aggregate in payload.score_aggregates
    }
    baseline_run_id = payload.baseline_run_id
    summaries_by_run_id = {summary.run_id: summary for summary in payload.run_summaries}
    baseline_summary = summaries_by_run_id.get(baseline_run_id)
    head = "".join(
        _score_pivot_header(
            run_id,
            baseline_run_id,
            summaries_by_run_id,
            baseline_summary,
        )
        for run_id in ["Score", *run_labels]
    )
    rows = []
    for score_name in score_names:
        cells = [f"<td>{_e(score_name)}</td>"]
        baseline_value = aggregate_map.get((score_name, baseline_run_id))
        for run_id in run_labels:
            value = aggregate_map.get((score_name, run_id))
            cells.append(_score_pivot_cell(value, baseline_value, is_baseline=run_id == baseline_run_id))
        rows.append("<tr>" + "".join(cells) + "</tr>")
    body = "\n".join(rows)
    footer = _score_pivot_footer(run_labels, baseline_run_id, aggregate_map, score_names)
    return f"""
<section class="section-card score-table">
  <div class="section-heading">
    <h2>Score Pivot</h2>
    <p>Average numeric evaluator score by score dimension and run.</p>
  </div>
  <div class="table-frame">
    <table>
      <thead><tr>{head}</tr></thead>
      <tbody>{body}</tbody>
      {footer}
    </table>
  </div>
</section>"""


def _score_pivot_header(
    run_id: str,
    baseline_run_id: str,
    summaries_by_run_id: dict[str, object],
    baseline_summary: object | None,
) -> str:
    if run_id == "Score" or run_id == baseline_run_id:
        return f"<th>{_e(run_id)}</th>"
    summary = summaries_by_run_id.get(run_id)
    diff_label = _run_difference_label(summary, baseline_summary)
    if not diff_label:
        return f"<th>{_e(run_id)}</th>"
    diff_items = "".join(
        f'<span class="pivot-run-diff-item">{_e(item)}</span>'
        for item in diff_label.split("; ")
        if item
    )
    return f'<th>{_e(run_id)}<span class="pivot-run-diff">{diff_items}</span></th>'


def _score_pivot_footer(
    run_labels: list[str],
    baseline_run_id: str,
    aggregate_map: dict[tuple[str, str], float],
    score_names: list[str],
) -> str:
    cells = ['<th scope="row">Candidate summary</th>']
    for run_id in run_labels:
        if run_id == baseline_run_id:
            cells.append("<td></td>")
            continue
        summary = _score_delta_summary(run_id, baseline_run_id, aggregate_map, score_names)
        cells.append(f'<td><span class="pivot-run-summary">{_e(summary)}</span></td>' if summary else "<td></td>")
    return '<tfoot class="pivot-summary-footer"><tr>' + "".join(cells) + "</tr></tfoot>"


def _score_delta_summary(
    run_id: str,
    baseline_run_id: str,
    aggregate_map: dict[tuple[str, str], float],
    score_names: list[str],
) -> str:
    deltas = [
        value - baseline_value
        for score_name in score_names
        if (value := aggregate_map.get((score_name, run_id))) is not None
        and (baseline_value := aggregate_map.get((score_name, baseline_run_id))) is not None
    ]
    if not deltas:
        return ""
    improved = sum(1 for delta in deltas if delta > 0)
    declined = sum(1 for delta in deltas if delta < 0)
    average_delta = sum(deltas) / len(deltas)
    return f"▲ {improved} / ▼ {declined} · avg Δ {average_delta:+.3f}"


def _run_difference_label(summary: object | None, baseline_summary: object | None) -> str:
    if summary is None or baseline_summary is None:
        return ""
    parts: list[str] = []
    if getattr(summary, "model", "") != getattr(baseline_summary, "model", ""):
        parts.append(f"model: {getattr(summary, 'model', '')}")
    if getattr(summary, "prompt_version", "") != getattr(baseline_summary, "prompt_version", ""):
        parts.append(f"prompt: {getattr(summary, 'prompt_version', '')}")
    summary_temp = _temperature_value(getattr(summary, "parameters", ""))
    baseline_temp = _temperature_value(getattr(baseline_summary, "parameters", ""))
    if summary_temp and baseline_temp and summary_temp != baseline_temp:
        parts.append(f"temp: {summary_temp}")
    return "; ".join(parts)


def _temperature_value(parameters: str) -> str:
    text = str(parameters).strip()
    if not text or text == "unknown":
        return ""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict) and parsed.get("temperature") is not None:
        return str(parsed["temperature"])
    for item in text.split(","):
        key, separator, value = item.partition("=")
        if separator and key.strip() == "temperature":
            return value.strip()
    return ""


def _score_pivot_cell(
    value: float | None,
    baseline_value: float | None,
    *,
    is_baseline: bool,
) -> str:
    if value is None:
        return "<td></td>"
    value_html = f'<span class="score-value">{value:.3f}</span>'
    if is_baseline or baseline_value is None:
        return f"<td>{value_html}</td>"
    delta = value - baseline_value
    if delta > 0:
        return (
            f'<td>{value_html} <span class="score-delta score-up" '
            f'aria-label="up {delta:.3f}">▲ +{delta:.3f}</span></td>'
        )
    if delta < 0:
        return (
            f'<td>{value_html} <span class="score-delta score-down" '
            f'aria-label="down {abs(delta):.3f}">▼ {delta:.3f}</span></td>'
        )
    return (
        f"<td>{value_html} "
        '<span class="score-delta score-even" aria-label="unchanged">0.000</span></td>'
    )


def _chart_section(
    payload: ComparisonReportPayload,
    score_names: list[str],
    run_labels: list[str],
) -> str:
    if not payload.score_aggregates:
        return (
            '<section class="section-card"><h2>Average evaluator scores</h2>'
            f'<div class="empty-state">{_e(_score_empty_message(payload))}</div></section>'
        )
    return f"""
<section class="section-card chart-card">
  <div class="section-heading">
    <h2>Average evaluator scores</h2>
    <p>Grouped by score dimension with one bar per run.</p>
  </div>
  {_score_chart(payload, score_names, run_labels)}
</section>"""


def _score_chart(
    payload: ComparisonReportPayload,
    score_names: list[str],
    run_labels: list[str],
) -> str:
    width = 980
    height = max(280, 120 + len(score_names) * 86)
    left = 150
    top = 36
    chart_width = width - left - 40
    row_height = (height - top - 58) / max(1, len(score_names))
    bar_gap = 5
    aggregate_map = {
        (aggregate.score_name, aggregate.run_id): aggregate.average_score
        for aggregate in payload.score_aggregates
    }
    colors = ["#0f766e", "#d45d4c", "#315c80", "#9a6b1f", "#6f5aa8", "#2f855a"]
    parts = [
        f'<svg class="score-chart" viewBox="0 0 {width} {height}" role="img" aria-label="Average evaluator scores by run">',
        '<line class="axis" x1="150" y1="28" x2="150" y2="{0}" />'.format(height - 44),
    ]
    for index in range(6):
        x = left + chart_width * index / 5
        label = index / 5
        parts.append(f'<line class="grid-line" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height - 44}" />')
        parts.append(f'<text class="axis-label" x="{x:.1f}" y="{height - 22}">{label:.1f}</text>')
    for score_index, score_name in enumerate(score_names):
        y = top + score_index * row_height
        parts.append(f'<text class="score-label" x="18" y="{y + 24:.1f}">{_e(score_name)}</text>')
        bar_height = max(8, (row_height - 18) / max(1, len(run_labels)) - bar_gap)
        for run_index, run_id in enumerate(run_labels):
            value = aggregate_map.get((score_name, run_id))
            if value is None:
                continue
            bar_width = max(1, min(1, value) * chart_width)
            bar_y = y + 8 + run_index * (bar_height + bar_gap)
            color = colors[run_index % len(colors)]
            parts.append(
                f'<rect class="bar" x="{left}" y="{bar_y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{color}"><title>{_e(run_id)} {_e(score_name)} {value:.3f}</title></rect>'
            )
    legend_x = left
    for run_index, run_id in enumerate(run_labels):
        color = colors[run_index % len(colors)]
        x = legend_x + run_index * 190
        parts.append(f'<rect x="{x}" y="{height - 14}" width="12" height="12" rx="2" fill="{color}" />')
        parts.append(f'<text class="legend-label" x="{x + 18}" y="{height - 4}">{_e(run_id)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _table_section(
    title: str,
    description: str,
    headers: list[str],
    rows: list[list[str]],
    *,
    class_name: str = "",
    wrapper: str = "section",
) -> str:
    head = "".join(f"<th>{_e(header)}</th>" for header in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{_e(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    content = f"""
  <div class="section-heading">
    <h2>{_e(title)}</h2>
    <p>{_e(description)}</p>
  </div>
  <div class="table-frame">
    <table>
      <thead><tr>{head}</tr></thead>
      <tbody>{body}</tbody>
    </table>
  </div>"""
    if wrapper == "details":
        return f"""
<details class="source-data-panel">
  <summary>{_e(title)}</summary>
  {content}
</details>"""
    return f"""
<section class="section-card {class_name}">
{content}
</section>"""


def _score_empty_message(payload: ComparisonReportPayload) -> str:
    for warning in payload.warnings:
        if warning.startswith("No score columns") or warning.startswith("No numeric score"):
            return warning
    return "No score data available."


def _css() -> str:
    return """
:root {
  --ink: #17211f;
  --muted: #5c6864;
  --paper: #f4f7f6;
  --panel: #ffffff;
  --line: #d8e0dc;
  --accent: #0f766e;
  --ember: #d45d4c;
  --shadow: 0 20px 55px rgba(23, 33, 31, 0.12);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 34rem),
    linear-gradient(135deg, #f8fbfa 0%, var(--paper) 48%, #eef4f2 100%);
  font-family: "Aptos", "Candara", "Trebuchet MS", sans-serif;
}
.report-shell {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 34px 0 54px;
}
.hero-panel, .section-card, .notice-panel, .metric-card, .source-data-panel {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}
.hero-panel {
  padding: clamp(28px, 5vw, 54px);
  border-radius: 6px;
  position: relative;
  overflow: hidden;
}
.hero-panel::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 6px;
  background: linear-gradient(90deg, var(--accent), var(--ember), #315c80);
}
.report-kicker {
  color: var(--accent);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(300px, 0.8fr);
  gap: clamp(24px, 5vw, 58px);
  align-items: end;
}
h1 {
  margin: 14px 0 12px;
  font-family: "Constantia", "Cambria", Georgia, serif;
  font-size: clamp(2.4rem, 6vw, 5.8rem);
  line-height: 0.95;
  letter-spacing: 0;
}
.lede {
  max-width: 70ch;
  color: var(--muted);
  font-size: clamp(1.02rem, 2vw, 1.25rem);
  line-height: 1.55;
}
.hero-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}
.hero-facts div, .metric-card {
  border-radius: 6px;
  padding: 16px;
}
.hero-facts div { background: #eef5f3; border: 1px solid var(--line); }
dt, .metric-card span {
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
}
dd, .metric-card strong {
  display: block;
  margin: 6px 0 0;
  font-size: 1.15rem;
  font-weight: 800;
  overflow-wrap: anywhere;
}
.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 18px 0;
}
.section-card, .notice-panel, .source-data-panel {
  border-radius: 6px;
  margin: 18px 0;
  padding: clamp(18px, 3vw, 28px);
}
.source-data-panel summary {
  cursor: pointer;
  color: var(--ink);
  font-family: "Constantia", "Cambria", Georgia, serif;
  font-size: 1.45rem;
  font-weight: 800;
}
.source-data-panel summary::marker { color: var(--accent); }
.source-data-panel .section-heading { margin-top: 18px; }
.notice-panel { border-left: 6px solid var(--ember); }
.notice-panel h2, .section-heading h2 {
  margin: 0;
  font-family: "Constantia", "Cambria", Georgia, serif;
  font-size: 1.65rem;
}
.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: end;
  margin-bottom: 16px;
}
.section-heading p { color: var(--muted); margin: 0; max-width: 54ch; }
.table-frame {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
}
table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  background: var(--panel);
}
th, td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}
th {
  position: sticky;
  top: 0;
  background: #e8f1ef;
  color: #213531;
  font-size: 0.76rem;
  text-transform: uppercase;
}
.pivot-run-diff {
  display: block;
  margin-top: 6px;
  color: #315c80;
  font-size: 0.72rem;
  font-weight: 800;
  line-height: 1.35;
  text-transform: none;
  white-space: normal;
}
.pivot-run-diff-item {
  display: block;
}
.pivot-summary-footer th, .pivot-summary-footer td {
  background: #dfeee9;
  border-top: 2px solid var(--line);
  border-bottom: 0;
}
.pivot-summary-footer th {
  color: #213531;
}
.pivot-run-summary {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 9px;
  color: var(--muted);
  background: #ffffff;
  font-size: 0.78rem;
  font-weight: 900;
  line-height: 1.35;
  white-space: nowrap;
}
tbody tr:nth-child(even) td { background: #f8fbfa; }
.score-value {
  font-variant-numeric: tabular-nums;
  font-weight: 800;
}
.score-delta {
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 0.78rem;
  font-weight: 900;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.score-up {
  color: #126a3a;
  background: #dff3e7;
}
.score-down {
  color: #9c2c25;
  background: #f8dfdc;
}
.score-even {
  color: var(--muted);
  background: #eef2f0;
}
.score-chart {
  width: 100%;
  height: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: linear-gradient(180deg, #ffffff, #f7faf9);
}
.axis, .grid-line { stroke: #c9d5d1; stroke-width: 1; }
.axis-label, .legend-label { fill: var(--muted); font-size: 12px; }
.score-label { fill: var(--ink); font-weight: 800; font-size: 13px; }
.bar { rx: 4; filter: drop-shadow(0 1px 1px rgba(23, 33, 31, 0.18)); }
.empty-state {
  border: 1px dashed var(--line);
  border-radius: 6px;
  padding: 26px;
  color: var(--muted);
  background: #f8fbfa;
}
@media (max-width: 760px) {
  .report-shell { width: min(100vw - 18px, 1180px); padding-top: 12px; }
  .hero-grid, .section-heading, .metric-strip { grid-template-columns: 1fr; display: grid; }
  .hero-facts { grid-template-columns: 1fr; }
  h1 { font-size: clamp(2.2rem, 14vw, 4.2rem); }
  .section-card, .notice-panel, .hero-panel { padding: 18px; }
  table { min-width: 680px; }
}
"""


def _e(value: object) -> str:
    return escape(str(value), quote=True)
