from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from evaluator_harness.comparison_reports import (
    BaselineRunSelection,
    discover_reports_with_warnings,
    select_reports,
)
from evaluator_harness.config import ProjectConfig
from evaluator_harness.errors import ConfigError

RunRole = Literal["baseline", "candidate"]
ResolutionSource = Literal["manifest", "fallback-artifacts"]


@dataclass(frozen=True)
class CampaignRunReference:
    run_id: str
    role: RunRole
    candidate_name: str | None = None
    status: str = "completed"
    csv_report_path: Path | None = None
    comparison_source_path: Path | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        run_id = self.run_id.strip()
        if not run_id:
            raise ConfigError("Campaign run reference requires a non-empty run ID.")
        if self.role not in {"baseline", "candidate"}:
            raise ConfigError(f"Unsupported campaign run role: {self.role}")
        object.__setattr__(self, "run_id", run_id)
        if self.csv_report_path is not None:
            object.__setattr__(self, "csv_report_path", Path(self.csv_report_path))
        if self.comparison_source_path is not None:
            object.__setattr__(
                self,
                "comparison_source_path",
                Path(self.comparison_source_path),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "role": self.role,
            "candidate_name": self.candidate_name,
            "status": self.status,
            "csv_report_path": _path_to_json(self.csv_report_path),
            "comparison_source_path": _path_to_json(self.comparison_source_path),
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CampaignRunReference:
        return cls(
            run_id=str(payload.get("run_id") or ""),
            role=str(payload.get("role") or ""),
            candidate_name=payload.get("candidate_name"),
            status=str(payload.get("status") or "completed"),
            csv_report_path=_path_from_json(payload.get("csv_report_path")),
            comparison_source_path=_path_from_json(
                payload.get("comparison_source_path")
            ),
            message=payload.get("message"),
        )


@dataclass(frozen=True)
class CampaignManifest:
    project_name: str
    project_version: str
    baseline_run_id: str
    reports_dir: Path
    generated_at: str
    runs: list[CampaignRunReference]
    comparison_reports: tuple[Path, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        baseline_run_id = self.baseline_run_id.strip()
        if not baseline_run_id:
            raise ConfigError("Campaign manifest requires a baseline run ID.")
        object.__setattr__(self, "baseline_run_id", baseline_run_id)
        object.__setattr__(self, "reports_dir", Path(self.reports_dir))
        object.__setattr__(self, "runs", list(self.runs))
        object.__setattr__(
            self,
            "comparison_reports",
            tuple(Path(path) for path in self.comparison_reports),
        )
        object.__setattr__(self, "warnings", tuple(self.warnings))
        baseline_refs = [
            run
            for run in self.runs
            if run.role == "baseline" and run.run_id == baseline_run_id
        ]
        if len(baseline_refs) != 1:
            raise ConfigError(
                f"Campaign manifest for baseline run {baseline_run_id} must include "
                "exactly one matching baseline run reference."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_version": self.project_version,
            "baseline_run_id": self.baseline_run_id,
            "reports_dir": str(self.reports_dir),
            "generated_at": self.generated_at,
            "runs": [run.to_dict() for run in self.runs],
            "comparison_reports": [str(path) for path in self.comparison_reports],
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CampaignManifest:
        runs_payload = payload.get("runs")
        if not isinstance(runs_payload, list):
            raise ConfigError("Campaign manifest missing runs list.")
        return cls(
            project_name=str(payload.get("project_name") or ""),
            project_version=str(payload.get("project_version") or ""),
            baseline_run_id=str(payload.get("baseline_run_id") or ""),
            reports_dir=Path(str(payload.get("reports_dir") or "reports")),
            generated_at=str(payload.get("generated_at") or ""),
            runs=[CampaignRunReference.from_dict(run) for run in runs_payload],
            comparison_reports=tuple(
                Path(str(path)) for path in payload.get("comparison_reports", [])
            ),
            warnings=tuple(str(warning) for warning in payload.get("warnings", [])),
        )


@dataclass(frozen=True)
class CampaignRunReferenceResolution:
    runs: list[CampaignRunReference]
    source: ResolutionSource
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CampaignRunCalibrationResult:
    run_id: str
    role: RunRole
    candidate_name: str | None
    status: str
    snapshot_path: Path | None = None
    snapshot_row_count: int = 0
    summary_path: Path | None = None
    summary_count: int = 0
    paired_count: int = 0
    pending_count: int = 0
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CampaignCalibrationRun:
    project_name: str
    project_version: str
    baseline_run_id: str
    source: ResolutionSource
    run_references: list[CampaignRunReference]
    run_results: list[CampaignRunCalibrationResult]
    warnings: tuple[str, ...] = ()
    html_report_path: Path | None = None
    started_at: str = ""
    completed_at: str = ""

    @property
    def run_count(self) -> int:
        return len(self.run_references)

    @property
    def captured_count(self) -> int:
        return sum(1 for result in self.run_results if result.status != "failed")

    @property
    def summarized_count(self) -> int:
        return sum(
            1 for result in self.run_results if result.summary_path is not None
        )


CaptureRun = Callable[[str], Any]
SummarizeRun = Callable[[str], Any]


def campaign_manifest_path(reports_dir: Path, baseline_run_id: str) -> Path:
    return Path(reports_dir) / "campaign-manifests" / f"{baseline_run_id}.json"


def write_campaign_manifest(manifest: CampaignManifest) -> Path:
    output_path = campaign_manifest_path(manifest.reports_dir, manifest.baseline_run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def load_campaign_manifest(
    reports_dir: Path,
    baseline_run_id: str,
) -> CampaignManifest | None:
    path = campaign_manifest_path(reports_dir, baseline_run_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Malformed campaign manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"Malformed campaign manifest {path}: expected object.")
    return CampaignManifest.from_dict(payload)


def manifest_from_campaign_result(
    *,
    config: ProjectConfig,
    result: Any,
    reports_dir: Path,
) -> CampaignManifest:
    if result.baseline_run is None:
        raise ConfigError("Cannot create campaign manifest without a baseline run.")
    baseline_run_id = str(result.baseline_run.run_id)
    csv_by_run_id = {
        report.output_path.stem: report.output_path
        for report in getattr(result, "csv_reports", [])
    }
    runs = [
        CampaignRunReference(
            run_id=baseline_run_id,
            role="baseline",
            csv_report_path=csv_by_run_id.get(baseline_run_id),
        )
    ]
    for candidate in getattr(result, "candidate_runs", []):
        if candidate.run_result is None:
            continue
        run_id = str(candidate.run_result.run_id)
        runs.append(
            CampaignRunReference(
                run_id=run_id,
                role="candidate",
                candidate_name=candidate.candidate_name,
                status=candidate.status,
                csv_report_path=(
                    candidate.csv_report.output_path
                    if candidate.csv_report is not None
                    else csv_by_run_id.get(run_id)
                ),
                message=candidate.message,
            )
        )
    final_reports = getattr(result, "final_reports", None) or []
    return CampaignManifest(
        project_name=config.project.name,
        project_version=config.project.version,
        baseline_run_id=baseline_run_id,
        reports_dir=reports_dir,
        generated_at=_now_utc(),
        runs=runs,
        comparison_reports=tuple(report.output_path for report in final_reports),
        warnings=tuple(getattr(result, "warnings", ())),
    )


def write_campaign_manifest_from_result(
    *,
    config: ProjectConfig,
    result: Any,
    reports_dir: Path,
) -> Path | None:
    if result.baseline_run is None:
        return None
    manifest = manifest_from_campaign_result(
        config=config,
        result=result,
        reports_dir=reports_dir,
    )
    return write_campaign_manifest(manifest)


def resolve_campaign_run_references(
    baseline_run_id: str,
    *,
    reports_dir: Path,
) -> CampaignRunReferenceResolution:
    manifest = load_campaign_manifest(reports_dir, baseline_run_id)
    if manifest is not None:
        return CampaignRunReferenceResolution(
            runs=manifest.runs,
            source="manifest",
            warnings=manifest.warnings,
        )
    reports, warnings = discover_reports_with_warnings(reports_dir)
    try:
        selected_reports = select_reports(
            BaselineRunSelection(
                baseline_run_id=baseline_run_id,
                reports_dir=reports_dir,
            ),
            reports=reports,
        )
    except ConfigError as exc:
        raise ConfigError(
            f"No campaign manifest or CSV report could identify baseline run "
            f"'{baseline_run_id}' in {reports_dir}."
        ) from exc
    references = [
        CampaignRunReference(
            run_id=report.run_id,
            role="baseline" if report.run_id == baseline_run_id else "candidate",
            candidate_name=_first_non_empty(
                report.rows,
                ["candidate_name", "candidate"],
            ),
            csv_report_path=report.path,
            comparison_source_path=report.path,
        )
        for report in selected_reports
    ]
    return CampaignRunReferenceResolution(
        runs=references,
        source="fallback-artifacts",
        warnings=tuple(warnings),
    )


def capture_campaign_calibration(
    *,
    project_name: str,
    project_version: str,
    baseline_run_id: str,
    source: ResolutionSource,
    run_references: list[CampaignRunReference],
    capture_run: CaptureRun,
    warnings: tuple[str, ...] = (),
) -> CampaignCalibrationRun:
    started_at = _now_utc()
    run_results: list[CampaignRunCalibrationResult] = []
    all_warnings = list(warnings)
    for reference in run_references:
        try:
            snapshot = capture_run(reference.run_id)
        except Exception as exc:
            message = f"{reference.run_id}: {exc}"
            all_warnings.append(message)
            run_results.append(
                CampaignRunCalibrationResult(
                    run_id=reference.run_id,
                    role=reference.role,
                    candidate_name=reference.candidate_name,
                    status="failed",
                    warnings=(str(exc),),
                )
            )
            continue
        snapshot_warnings = tuple(getattr(snapshot, "warnings", ()))
        for warning in snapshot_warnings:
            all_warnings.append(f"{reference.run_id}: {warning}")
        run_results.append(
            CampaignRunCalibrationResult(
                run_id=reference.run_id,
                role=reference.role,
                candidate_name=reference.candidate_name,
                status="warning" if snapshot_warnings else "completed",
                snapshot_path=getattr(snapshot, "output_path", None),
                snapshot_row_count=int(getattr(snapshot, "row_count", 0)),
                paired_count=int(getattr(snapshot, "paired_count", 0)),
                pending_count=int(getattr(snapshot, "pending_count", 0)),
                warnings=snapshot_warnings,
            )
        )
    return CampaignCalibrationRun(
        project_name=project_name,
        project_version=project_version,
        baseline_run_id=baseline_run_id,
        source=source,
        run_references=run_references,
        run_results=run_results,
        warnings=tuple(all_warnings),
        started_at=started_at,
        completed_at=_now_utc(),
    )


def summarize_campaign_calibration(
    campaign_run: CampaignCalibrationRun,
    *,
    summarize_run: SummarizeRun,
) -> CampaignCalibrationRun:
    run_results: list[CampaignRunCalibrationResult] = []
    all_warnings = list(campaign_run.warnings)
    for result in campaign_run.run_results:
        if result.status == "failed":
            run_results.append(result)
            continue
        try:
            summary = summarize_run(result.run_id)
        except Exception as exc:
            message = f"{result.run_id}: {exc}"
            all_warnings.append(message)
            run_results.append(
                replace(
                    result,
                    status="failed",
                    warnings=(*result.warnings, str(exc)),
                )
            )
            continue
        summary_warnings = tuple(getattr(summary, "warnings", ()))
        for warning in summary_warnings:
            all_warnings.append(f"{result.run_id}: {warning}")
        combined_warnings = (*result.warnings, *summary_warnings)
        run_results.append(
            replace(
                result,
                status="warning" if combined_warnings else "completed",
                summary_path=getattr(summary, "output_path", None),
                summary_count=int(getattr(summary, "summary_count", 0)),
                paired_count=int(getattr(summary, "paired_count", result.paired_count)),
                pending_count=int(
                    getattr(summary, "pending_count", result.pending_count)
                ),
                warnings=combined_warnings,
            )
        )
    return replace(
        campaign_run,
        run_results=run_results,
        warnings=tuple(all_warnings),
        completed_at=_now_utc(),
    )


def _first_non_empty(rows: list[dict[str, str]], keys: list[str]) -> str | None:
    for row in rows:
        for key in keys:
            value = row.get(key)
            if value and value.strip():
                return value.strip()
    return None


def _path_to_json(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def _path_from_json(value: Any) -> Path | None:
    return Path(str(value)) if value else None


def _now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
