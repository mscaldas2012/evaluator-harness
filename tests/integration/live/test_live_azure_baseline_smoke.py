from __future__ import annotations

import pytest

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.live_env import require_live_azure_openai, require_live_langfuse


@pytest.mark.live
def test_live_azure_baseline_smoke() -> None:
    require_live_langfuse()
    require_live_azure_openai()
    runner = ExperimentRunner(langfuse_client=LangfuseClient.from_env())

    result = runner.run("configs/projects/rewrite_quality.yaml", "baseline")

    assert result.run_type == "baseline"
    assert result.completed_count + result.failed_count >= 1
