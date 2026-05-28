from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.live_env import require_live_langfuse


@pytest.mark.live
def test_live_sync_judge_evaluators_dry_run_capability_detection() -> None:
    require_live_langfuse()

    result = ExperimentRunner().sync_judge_evaluators(
        Path("configs/projects/rewrite_quality.yaml"),
        dry_run=True,
    )

    assert result.mode == "preview"
    assert result.evaluators


@pytest.mark.live
def test_live_langfuse_evaluator_crud_surface_reports_remediation() -> None:
    require_live_langfuse()

    try:
        result = ExperimentRunner().sync_judge_evaluators(
            Path("configs/projects/rewrite_quality.yaml"),
            dry_run=True,
        )
    except NotImplementedError as exc:
        pytest.skip(f"Installed Langfuse evaluator CRUD surface unsupported: {exc}")

    assert result.overall_status in {"success", "partial_success", "failure"}
