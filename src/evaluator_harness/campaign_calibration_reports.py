from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from evaluator_harness.campaign_calibration import CampaignCalibrationRun
from evaluator_harness.errors import ConfigError, RuntimeDependencyError


@dataclass(frozen=True)
class CampaignCalibrationReportPayload:
    baseline_run_id: str
    output_path: Path
    generated_at: str
    run_results: list[Any]
    evaluator_summaries: list[dict[str, Any]]
    paired_records: list[dict[str, Any]]
    pending_records: list[dict[str, Any]]
    run_config_summaries: dict[str, dict[str, str]]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CampaignCalibrationReportOutput:
    output_path: Path
    summary_count: int
    paired_record_count: int
    pending_record_count: int
    warnings: tuple[str, ...] = ()


def derive_campaign_calibration_report_path(
    baseline_run_id: str,
    *,
    reports_dir: Path,
    output_path: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    if output_path is not None and output_dir is not None:
        raise ConfigError("--output and --output-dir cannot be used together.")
    if output_path is not None:
        path = Path(output_path)
    else:
        directory = Path(output_dir) if output_dir is not None else Path(reports_dir)
        path = directory / f"{baseline_run_id}-calibration-report.html"
    path = path.resolve()
    if path.suffix.lower() != ".html":
        raise ConfigError("Campaign calibration report output must use a .html suffix.")
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_campaign_calibration_report_payload(
    campaign_run: CampaignCalibrationRun,
    *,
    output_path: Path,
) -> CampaignCalibrationReportPayload:
    summaries: list[dict[str, Any]] = []
    paired_records: list[dict[str, Any]] = []
    pending_records: list[dict[str, Any]] = []
    run_config_summaries: dict[str, dict[str, str]] = {}
    warnings = list(campaign_run.warnings)
    references_by_run_id = {
        reference.run_id: reference for reference in campaign_run.run_references
    }
    for result in campaign_run.run_results:
        if result.summary_path is not None:
            summaries.extend(_load_json_list(result.summary_path))
        if result.snapshot_path is not None:
            for record in _load_json_list(result.snapshot_path):
                if record.get("paired"):
                    paired_records.append(record)
                elif record.get("pending_label"):
                    pending_records.append(record)
        config_summary = _load_run_config_summary(
            result.run_id,
            references_by_run_id.get(result.run_id),
            result.snapshot_path,
        )
        if config_summary:
            run_config_summaries[result.run_id] = config_summary
        for warning in result.warnings:
            qualified = f"{result.run_id}: {warning}"
            if qualified not in warnings:
                warnings.append(qualified)
    return CampaignCalibrationReportPayload(
        baseline_run_id=campaign_run.baseline_run_id,
        output_path=Path(output_path),
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        run_results=list(campaign_run.run_results),
        evaluator_summaries=summaries,
        paired_records=paired_records,
        pending_records=pending_records,
        run_config_summaries=run_config_summaries,
        warnings=tuple(warnings),
    )


def create_campaign_calibration_report(
    campaign_run: CampaignCalibrationRun,
    *,
    reports_dir: Path,
    output_path: Path | None = None,
    output_dir: Path | None = None,
) -> CampaignCalibrationReportOutput:
    resolved_output = derive_campaign_calibration_report_path(
        campaign_run.baseline_run_id,
        reports_dir=reports_dir,
        output_path=output_path,
        output_dir=output_dir,
    )
    payload = build_campaign_calibration_report_payload(
        campaign_run,
        output_path=resolved_output,
    )
    resolved_output.write_text(
        render_campaign_calibration_report(payload),
        encoding="utf-8",
    )
    if not resolved_output.exists():
        raise RuntimeDependencyError(
            "Campaign calibration report creation completed but no file was found "
            f"at {resolved_output}."
        )
    return CampaignCalibrationReportOutput(
        output_path=resolved_output,
        summary_count=len(payload.evaluator_summaries),
        paired_record_count=len(payload.paired_records),
        pending_record_count=len(payload.pending_records),
        warnings=payload.warnings,
    )


def render_campaign_calibration_report(
    payload: CampaignCalibrationReportPayload,
) -> str:
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{_e(payload.baseline_run_id)} calibration report</title>",
            "<style>",
            _css(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="report-shell">',
            _hero(payload),
            _run_filter(payload),
            _warnings(payload),
            _run_table(payload),
            _trend_panel(payload),
            _summary_table(payload),
            _largest_delta_table(payload),
            _paired_table(payload),
            _pending_table(payload),
            "</main>",
            "<script>",
            _script(),
            "</script>",
            "</body>",
            "</html>",
        ]
    )


def _hero(payload: CampaignCalibrationReportPayload) -> str:
    run_count = len(payload.run_results)
    run_label = "run" if run_count == 1 else "runs"
    description = (
        f"Baseline <strong>{_e(payload.baseline_run_id)}</strong> "
        f"calibration across {run_count} {run_label}."
    )
    return f"""
<section class="hero-panel">
  <div class="report-kicker">Evaluator Harness</div>
  <h1>Campaign Calibration Report</h1>
  <p>{description}</p>
  <dl class="metric-strip">
    <div><dt>Generated</dt><dd>{_e(payload.generated_at)}</dd></div>
    <div><dt>Evaluator summaries</dt><dd>{len(payload.evaluator_summaries)}</dd></div>
    <div><dt>Paired records</dt><dd>{len(payload.paired_records)}</dd></div>
    <div><dt>Pending records</dt><dd>{len(payload.pending_records)}</dd></div>
  </dl>
</section>"""


def _run_filter(payload: CampaignCalibrationReportPayload) -> str:
    options = ['<option value="all">All runs</option>']
    for result in payload.run_results:
        label = result.candidate_name or result.run_id
        options.append(f'<option value="{_e(result.run_id)}">{_e(label)}</option>')
    return f"""
<section class="filter-panel">
  <label for="run-filter">Run filter</label>
  <select id="run-filter" aria-label="Filter report rows by run">
    {''.join(options)}
  </select>
</section>"""


def _warnings(payload: CampaignCalibrationReportPayload) -> str:
    if not payload.warnings:
        return ""
    items = "".join(f"<li>{_e(warning)}</li>" for warning in payload.warnings)
    return (
        '<details class="notice-panel" open>'
        "<summary><h2>Warnings</h2></summary>"
        f"<ul>{items}</ul></details>"
    )


def _run_table(payload: CampaignCalibrationReportPayload) -> str:
    run_context = _run_context(payload)
    baseline_config = payload.run_config_summaries.get(payload.baseline_run_id, {})
    rows = "".join(
        _row(
            [
                _run_badge_for_run_id(
                    result.run_id,
                    result.role,
                    result.candidate_name,
                    run_context,
                ),
                _status_badge(result.status),
                _e(result.candidate_name or ""),
                _run_diff_chips(
                    result.run_id,
                    payload.run_config_summaries.get(result.run_id, {}),
                    baseline_config,
                    run_context,
                ),
                str(result.paired_count),
                str(result.pending_count),
            ],
            row_class=_run_row_class(result.run_id, run_context),
            run_id=result.run_id,
        )
        for result in payload.run_results
    )
    return _html_table(
        "Run Overview",
        ["Run", "Status", "Candidate", "Candidate diff", "Paired", "Pending"],
        rows,
    )


def _trend_panel(payload: CampaignCalibrationReportPayload) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for summary in payload.evaluator_summaries:
        evaluator = str(summary.get("evaluator_name", ""))
        grouped.setdefault(evaluator, []).append(summary)
    if not grouped:
        return _table("Evaluator Trend", ["Evaluator", "Trend"], [])
    rows = "".join(
        _row(
            [
                _e(evaluator),
                _sparkline(summaries),
                _trend_points(summaries),
            ],
            run_ids=[str(summary.get("run_id", "")) for summary in summaries],
        )
        for evaluator, summaries in grouped.items()
    )
    return _html_table(
        "Evaluator Trend",
        ["Evaluator", "Directional bias", "Runs"],
        rows,
    )


def _summary_table(payload: CampaignCalibrationReportPayload) -> str:
    run_context = _run_context(payload)
    rows = "".join(
        _row(
            [
                _run_badge_for_summary(summary, run_context),
                _e(summary.get("evaluator_name", "")),
                _metric_cell(summary.get("paired_coverage")),
                _metric_cell(summary.get("disagreement_rate")),
                _metric_cell(summary.get("mean_absolute_score_delta")),
                _delta_cell(summary.get("directional_bias")),
            ],
            row_class=_run_row_class(summary.get("run_id"), run_context),
            run_id=summary.get("run_id", ""),
        )
        for summary in payload.evaluator_summaries
    )
    return _html_table(
        "Evaluator Comparison",
        [
            "Run",
            "Evaluator",
            "Paired coverage",
            "Disagreement rate",
            "Mean absolute score delta",
            "Directional bias",
        ],
        rows,
    )


def _largest_delta_table(payload: CampaignCalibrationReportPayload) -> str:
    run_context = _run_context(payload)
    records = sorted(
        payload.paired_records,
        key=lambda record: _absolute_delta(record.get("score_delta")),
        reverse=True,
    )[:25]
    rows = "".join(
        _row(
            [
                _run_badge_for_record(record, run_context),
                _e(record.get("item_id", "")),
                _e(record.get("trace_id", "")),
                _e(record.get("evaluator_name", "")),
                _metric_cell(record.get("automated_score")),
                _metric_cell(record.get("human_score")),
                _delta_cell(record.get("score_delta")),
            ],
            row_class=_run_row_class(record.get("run_id"), run_context),
            run_id=record.get("run_id", ""),
        )
        for record in records
    )
    return _html_table(
        "Largest Deltas",
        ["Run", "Item", "Trace", "Evaluator", "Automated", "Human", "Delta"],
        rows,
    )


def _paired_table(payload: CampaignCalibrationReportPayload) -> str:
    run_context = _run_context(payload)
    rows = "".join(
        _row(
            [
                _run_badge_for_record(record, run_context),
                _e(record.get("item_id", "")),
                _e(record.get("trace_id", "")),
                _e(record.get("evaluator_name", "")),
                _metric_cell(record.get("automated_score")),
                _metric_cell(record.get("human_score")),
                _delta_cell(record.get("score_delta")),
            ],
            row_class=_run_row_class(record.get("run_id"), run_context),
            run_id=record.get("run_id", ""),
        )
        for record in payload.paired_records[:100]
    )
    return _html_table(
        "Paired Record Details",
        ["Run", "Item", "Trace", "Evaluator", "Automated", "Human", "Delta"],
        rows,
    )


def _pending_table(payload: CampaignCalibrationReportPayload) -> str:
    run_context = _run_context(payload)
    rows = "".join(
        _row(
            [
                _run_badge_for_record(record, run_context),
                _e(record.get("item_id", "")),
                _e(record.get("trace_id", "")),
                _e(record.get("evaluator_name", "")),
                _metric_cell(record.get("automated_score")),
            ],
            row_class=_run_row_class(record.get("run_id"), run_context),
            run_id=record.get("run_id", ""),
        )
        for record in payload.pending_records[:100]
    )
    return _html_table(
        "Pending Records",
        ["Run", "Item", "Trace", "Evaluator", "Automated"],
        rows,
    )


def _html_table(title: str, headers: list[str], row_html: str) -> str:
    header_html = "".join(f"<th>{_e(header)}</th>" for header in headers)
    if not row_html:
        row_html = f'<tr><td colspan="{len(headers)}">No records</td></tr>'
    return f"""
<details class="table-panel" open>
  <summary><h2>{_e(title)}</h2></summary>
  <div class="table-wrap">
    <table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table>
  </div>
</details>"""


def _row(
    cells: list[str],
    *,
    row_class: str | None = None,
    run_id: object | None = None,
    run_ids: list[str] | None = None,
) -> str:
    class_attr = f' class="{_e(row_class)}"' if row_class else ""
    run_attr = f' data-run-id="{_e(run_id)}"' if run_id not in {None, ""} else ""
    if run_ids:
        clean_run_ids = " ".join(_e(run_id) for run_id in run_ids if run_id)
        run_attr = f' data-run-ids="{clean_run_ids}"'
    cells_html = "".join(f"<td>{cell}</td>" for cell in cells)
    return f"<tr{class_attr}{run_attr}>{cells_html}</tr>"


def _table(title: str, headers: list[str], rows: list[list[str]]) -> str:
    header_html = "".join(f"<th>{_e(header)}</th>" for header in headers)
    if rows:
        row_html = "".join(
            "<tr>" + "".join(f"<td>{_e(value)}</td>" for value in row) + "</tr>"
            for row in rows
        )
    else:
        row_html = f'<tr><td colspan="{len(headers)}">No records</td></tr>'
    return f"""
<details class="table-panel" open>
  <summary><h2>{_e(title)}</h2></summary>
  <div class="table-wrap">
    <table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table>
  </div>
</details>"""


def _run_context(payload: CampaignCalibrationReportPayload) -> dict[str, Any]:
    return {
        result.run_id: {
            "role": result.role,
            "candidate_name": result.candidate_name,
            "color_class": f"run-color-{index}",
        }
        for index, result in enumerate(payload.run_results)
    }


def _run_summary_metrics(payload: CampaignCalibrationReportPayload) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for summary in payload.evaluator_summaries:
        grouped.setdefault(str(summary.get("run_id", "")), []).append(summary)
    metrics: dict[str, Any] = {}
    for run_id, summaries in grouped.items():
        metrics[run_id] = {
            "paired_coverage": _mean_metric(summaries, "paired_coverage"),
            "disagreement_rate": _mean_metric(summaries, "disagreement_rate"),
            "mean_absolute_score_delta": _mean_metric(
                summaries,
                "mean_absolute_score_delta",
            ),
            "directional_bias": _mean_metric(summaries, "directional_bias"),
        }
    return metrics


def _mean_metric(summaries: list[dict[str, Any]], key: str) -> float | None:
    values = [
        number
        for summary in summaries
        if (number := _as_float(summary.get(key))) is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _run_diff_chips(
    run_id: str,
    config_summary: dict[str, str],
    baseline_config: dict[str, str],
    run_context: dict[str, Any],
) -> str:
    if str(run_context.get(run_id, {}).get("role")) == "baseline":
        return '<span class="pivot-run-summary">baseline</span>'
    items = [
        _config_diff_item("model", config_summary, baseline_config),
        _config_diff_item("prompt", config_summary, baseline_config),
        _config_diff_item("temp", config_summary, baseline_config),
    ]
    chips = "".join(item for item in items if item)
    if not chips:
        return ""
    return f'<span class="pivot-run-diff">{chips}</span>'


def _config_diff_item(
    label: str,
    config_summary: dict[str, str],
    baseline_config: dict[str, str],
) -> str:
    value = config_summary.get(label, "").strip()
    baseline_value = baseline_config.get(label, "").strip()
    if not value or value == baseline_value:
        return ""
    text = f"{label}: {value}"
    return f'<span class="pivot-run-diff-item">{_e(text)}</span>'


def _run_badge_for_summary(
    summary: dict[str, Any],
    run_context: dict[str, Any],
) -> str:
    run_id = str(summary.get("run_id", ""))
    context = run_context.get(run_id, {})
    return _run_badge_for_run_id(
        run_id,
        context.get("role", ""),
        context.get("candidate_name"),
        run_context,
    )


def _run_badge_for_record(record: dict[str, Any], run_context: dict[str, Any]) -> str:
    run_id = str(record.get("run_id", ""))
    context = run_context.get(run_id, {})
    return _run_badge_for_run_id(
        run_id,
        context.get("role", ""),
        context.get("candidate_name"),
        run_context,
    )


def _run_badge_for_run_id(
    run_id: object,
    role: object,
    candidate_name: object,
    run_context: dict[str, Any],
) -> str:
    context = run_context.get(str(run_id), {})
    color_class = str(context.get("color_class") or "")
    return _run_badge(run_id, role, candidate_name, color_class=color_class)


def _run_badge(
    run_id: object,
    role: object,
    candidate_name: object = None,
    *,
    color_class: str = "",
) -> str:
    role_text = str(role or "run")
    label = candidate_name or run_id
    class_name = f"run-badge {_e(role_text)} {_e(color_class)}".strip()
    return (
        f'<span class="{class_name}">'
        f'<span>{_e(role_text)}</span>{_e(label)}</span>'
    )


def _run_row_class(run_id: object, run_context: dict[str, Any]) -> str:
    context = run_context.get(str(run_id), {})
    role = str(context.get("role") or "run")
    color_class = str(context.get("color_class") or "")
    return f"run-row {role}-row {color_class}".strip()


def _status_badge(status: object) -> str:
    status_text = str(status or "unknown")
    return f'<span class="status-badge {status_text}">{_e(status_text)}</span>'


def _metric_cell(value: object) -> str:
    return f'<span class="metric-value">{_e(_format_number(value))}</span>'


def _delta_cell(value: object) -> str:
    number = _as_float(value)
    if number is None:
        return '<span class="delta delta-neutral">n/a</span>'
    if number > 0:
        return f'<span class="delta delta-up"><span>&#9650;</span>{number:.3g}</span>'
    if number < 0:
        return f'<span class="delta delta-down"><span>&#9660;</span>{number:.3g}</span>'
    return '<span class="delta delta-neutral">0</span>'


def _sparkline(summaries: list[dict[str, Any]]) -> str:
    values = [
        _as_float(summary.get("directional_bias")) or 0.0
        for summary in summaries
    ]
    if not values:
        return '<svg class="sparkline" viewBox="0 0 180 44"></svg>'
    max_abs = max(max(abs(value) for value in values), 0.1)
    if len(values) == 1:
        points = [(90, 22 - (values[0] / max_abs) * 16)]
    else:
        points = [
            (index * (180 / (len(values) - 1)), 22 - (value / max_abs) * 16)
            for index, value in enumerate(values)
        ]
    line_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    circles = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3"></circle>' for x, y in points
    )
    return (
        '<svg class="sparkline" viewBox="0 0 180 44" role="img" '
        'aria-label="Directional bias trend">'
        '<line class="sparkline-zero" x1="0" y1="22" x2="180" y2="22"></line>'
        f'<polyline points="{line_points}"></polyline>{circles}</svg>'
    )


def _trend_points(summaries: list[dict[str, Any]]) -> str:
    return "".join(
        '<span class="trend-point">'
        f'<span data-run-id="{_e(summary.get("run_id", ""))}">'
        f'{_e(summary.get("run_id", ""))} '
        f'{_delta_cell(summary.get("directional_bias"))}'
        "</span></span>"
        for summary in summaries
    )


def _script() -> str:
    return """
const runFilter = document.getElementById('run-filter');
function rowMatchesRun(row, selectedRun) {
  if (selectedRun === 'all') return true;
  if (row.dataset.runId) return row.dataset.runId === selectedRun;
  if (row.dataset.runIds) return row.dataset.runIds.split(' ').includes(selectedRun);
  return true;
}
function applyRunFilter() {
  const selectedRun = runFilter ? runFilter.value : 'all';
  document.querySelectorAll('[data-run-id], [data-run-ids]').forEach((element) => {
    element.classList.toggle('is-hidden', !rowMatchesRun(element, selectedRun));
  });
}
if (runFilter) {
  runFilter.addEventListener('change', applyRunFilter);
  applyRunFilter();
}
"""


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Malformed calibration artifact {path}: {exc}") from exc
    if not isinstance(payload, list):
        raise ConfigError(f"Malformed calibration artifact {path}: expected list.")
    return [item for item in payload if isinstance(item, dict)]


def _load_run_config_summary(
    run_id: str,
    reference: Any,
    snapshot_path: Path | None,
) -> dict[str, str]:
    csv_path = getattr(reference, "csv_report_path", None)
    if csv_path is None and snapshot_path is not None:
        calibration_dir = Path(snapshot_path).parent
        csv_path = calibration_dir.parent / f"{run_id}.csv"
    if csv_path is None or not Path(csv_path).exists():
        return {}
    try:
        with Path(csv_path).open(newline="", encoding="utf-8-sig") as handle:
            row = next(csv.DictReader(handle), None)
    except OSError:
        return {}
    if row is None:
        return {}
    model = _first_non_empty(row, "model", "model_name", "candidate_model")
    prompt = _first_non_empty(row, "prompt_version", "task_prompt_version")
    temperature = _first_non_empty(row, "temperature")
    if not temperature:
        temperature = _temperature_value(
            _first_non_empty(row, "parameters", "model_parameters")
        )
    return {
        "model": model,
        "prompt": prompt,
        "temp": temperature,
    }


def _first_non_empty(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value and value.lower() != "unknown":
            return value
    return ""


def _temperature_value(parameters: str) -> str:
    text = str(parameters).strip()
    if not text:
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


def _absolute_delta(value: object) -> float:
    number = _as_float(value)
    return abs(number) if number is not None else 0.0


def _as_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: object) -> str:
    number = _as_float(value)
    if number is None:
        return str(value)
    return f"{number:.3g}"


def _e(value: object) -> str:
    return escape(str(value))


def _css() -> str:
    return """
:root {
  color-scheme: light;
  font-family: Aptos, Segoe UI, Tahoma, sans-serif;
  --ink: #172033;
  --muted: #5d687c;
  --line: #d8deea;
  --panel: #ffffff;
  --baseline: #245f73;
  --candidate: #72552b;
  --green: #137a45;
  --green-bg: #e9f7ef;
  --red: #b42318;
  --red-bg: #fff0ed;
}
body { margin: 0; background: #f4f6f9; color: var(--ink); }
.report-shell { max-width: 1180px; margin: 0 auto; padding: 28px; }
.hero-panel, .notice-panel, .table-panel {
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  margin-bottom: 18px; padding: 20px;
}
details > summary {
  align-items: center; cursor: pointer; display: flex; gap: 10px;
  list-style: none;
}
details > summary::-webkit-details-marker { display: none; }
details > summary::before {
  border: solid var(--muted); border-width: 0 2px 2px 0; content: "";
  height: 7px; margin-top: -3px; transform: rotate(45deg); width: 7px;
}
details:not([open]) > summary::before {
  margin-top: 2px; transform: rotate(-45deg);
}
.report-kicker {
  color: #4b5f83; font-size: 12px; font-weight: 700;
  text-transform: uppercase;
}
h1 { margin: 8px 0; font-size: 32px; }
h2 { margin: 0 0 12px; font-size: 18px; }
.metric-strip {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;
}
dt { color: var(--muted); font-size: 12px; }
dd { margin: 3px 0 0; font-size: 20px; font-weight: 700; }
.notice-panel { border-color: #f0c36a; background: #fff9e8; }
.filter-panel {
  align-items: center; background: #ffffff; border: 1px solid var(--line);
  border-radius: 8px; display: inline-flex; gap: 10px; margin-bottom: 18px;
  padding: 12px 14px;
}
.filter-panel label {
  color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase;
}
.filter-panel select {
  background: #f8fbfd; border: 1px solid var(--line); border-radius: 6px;
  color: var(--ink); font: inherit; min-width: 220px; padding: 7px 10px;
}
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; min-width: 100%; font-size: 13px; }
th, td { border-bottom: 1px solid #e4e8f0; padding: 9px 10px; text-align: left; }
th { background: #eef2f8; color: #25324a; font-weight: 700; }
.run-row.baseline-row td { background: #f1f8fa; }
.run-row.candidate-row td { background: #fff9ec; }
.run-row.run-color-0 td { background: #eff8fb; }
.run-row.run-color-1 td { background: #fff6e8; }
.run-row.run-color-2 td { background: #f0f7ed; }
.run-row.run-color-3 td { background: #f8f1fb; }
.run-row.run-color-4 td { background: #fdf2f2; }
.run-row.run-color-0 td:first-child { border-left: 6px solid #2f7f96; }
.run-row.run-color-1 td:first-child { border-left: 6px solid #c26a1b; }
.run-row.run-color-2 td:first-child { border-left: 6px solid #4f8f3a; }
.run-row.run-color-3 td:first-child { border-left: 6px solid #8a64a8; }
.run-row.run-color-4 td:first-child { border-left: 6px solid #c94f57; }
.run-row + .run-row td { border-top: 1px solid #d7dde8; }
.is-hidden { display: none !important; }
.run-badge, .status-badge, .delta, .trend-point {
  align-items: center; border-radius: 999px; display: inline-flex;
  font-weight: 700; gap: 6px; line-height: 1; white-space: nowrap;
}
.run-badge {
  border: 1px solid currentColor; padding: 6px 8px;
}
.run-badge span {
  font-size: 10px; letter-spacing: .04em; opacity: .72; text-transform: uppercase;
}
.run-badge.baseline { color: var(--baseline); }
.run-badge.candidate { color: var(--candidate); }
.run-badge.run-color-0 { background: #eff8fb; color: #2f7f96; }
.run-badge.run-color-1 { background: #fff6e8; color: #a55412; }
.run-badge.run-color-2 { background: #f0f7ed; color: #4f8f3a; }
.run-badge.run-color-3 { background: #f8f1fb; color: #765392; }
.run-badge.run-color-4 { background: #fdf2f2; color: #a83f46; }
.status-badge {
  background: #eef2f8; color: #33415c; font-size: 12px; padding: 6px 8px;
}
.status-badge.completed { background: var(--green-bg); color: var(--green); }
.status-badge.warning { background: #fff6db; color: #8a5a00; }
.status-badge.failed { background: var(--red-bg); color: var(--red); }
.metric-value { font-variant-numeric: tabular-nums; }
.delta {
  font-variant-numeric: tabular-nums; min-width: 62px; padding: 6px 8px;
}
.delta-up { background: var(--green-bg); color: var(--green); }
.delta-down { background: var(--red-bg); color: var(--red); }
.delta-neutral { background: #eef2f8; color: #566177; }
.sparkline { height: 44px; overflow: visible; width: 180px; }
.sparkline polyline {
  fill: none; stroke: #2f6f88; stroke-linecap: round; stroke-width: 2.5;
}
.sparkline circle { fill: white; stroke: #2f6f88; stroke-width: 2; }
.sparkline-zero { stroke: #c7cfdd; stroke-dasharray: 4 4; }
.pivot-run-diff {
  color: #315c80; display: grid; gap: 4px; line-height: 1.3;
}
.pivot-run-diff-item {
  background: #eef6fb; border-radius: 999px; display: inline-flex;
  font-size: 12px; font-weight: 800; padding: 4px 8px; white-space: nowrap;
}
.pivot-run-summary {
  background: #eef2f8; border-radius: 999px; color: var(--muted);
  display: inline-flex; font-size: 12px; font-weight: 800; padding: 4px 8px;
}
.trend-point {
  background: #f6f8fb; color: #25324a; margin: 2px 4px 2px 0; padding: 4px 6px;
}
@media (max-width: 760px) { .metric-strip { grid-template-columns: 1fr 1fr; } }
"""
