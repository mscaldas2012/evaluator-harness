from __future__ import annotations

import pytest

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.model_output_targeting import MODEL_OUTPUT_ROLE, RUN_ITEM_ROLE
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.live_env import require_live_azure_openai, require_live_langfuse


@pytest.mark.live
def test_live_azure_baseline_smoke() -> None:
    require_live_langfuse()
    require_live_azure_openai()
    runner = ExperimentRunner(langfuse_gateway=DefaultLangfuseGateway.from_env())

    result = runner.run("configs/projects/rewrite_quality.yaml", "baseline")

    assert result.run_type == "baseline"
    assert result.completed_count >= 1
    traces = runner.langfuse_gateway.traces_for_run(result.run_id)
    assert traces
    metadata = traces[0]["metadata"]
    assert metadata["observation_role"] == RUN_ITEM_ROLE
    assert (
        metadata["provider_tracing_strategy"]["standard_observation_role"]
        == MODEL_OUTPUT_ROLE
    )
    assert metadata["project"] == "rewrite-quality"
    assert metadata["evaluator_set_id"]
