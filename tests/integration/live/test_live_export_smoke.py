from __future__ import annotations

import pytest

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider
from tests.fixtures.live_env import require_live_langfuse


@pytest.mark.live
def test_live_export_smoke() -> None:
    require_live_langfuse()
    langfuse = LangfuseClient.from_env()
    runner = ExperimentRunner(
        langfuse_client=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output for export smoke")
        ),
    )
    result = runner.run("configs/projects/rewrite_quality.yaml", "baseline")

    export = runner.export("configs/projects/rewrite_quality.yaml", result.run_id, "csv")

    assert export.row_count >= 1
