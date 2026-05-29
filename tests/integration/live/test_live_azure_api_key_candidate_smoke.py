from __future__ import annotations

import os

import pytest

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.live_env import require_live_langfuse


def require_live_azure_api_key_candidate() -> None:
    missing = [
        name
        for name in (
            "REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY",
            "REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT",
            "REWRITE_QUALITY_MISTRAL_LARGE_3_API_VERSION",
        )
        if not os.getenv(name)
    ]
    if missing:
        pytest.skip(
            "Missing Azure API-key candidate environment variables: "
            + ", ".join(missing)
        )


@pytest.mark.live
def test_live_azure_api_key_candidate_smoke() -> None:
    require_live_langfuse()
    require_live_azure_api_key_candidate()
    runner = ExperimentRunner(langfuse_client=LangfuseClient.from_env())

    baseline = runner.run("configs/projects/rewrite_quality.yaml", "baseline")
    result = runner.run(
        "configs/projects/rewrite_quality.yaml",
        "candidate",
        candidate="azure-mistral-large-3",
        baseline=baseline.run_id,
    )

    assert result.run_type == "candidate"
    assert result.completed_count + result.failed_count >= 1
    traces = runner.langfuse_client.traces_for_run(result.run_id)
    assert traces
    metadata = traces[0]["metadata"]
    assert metadata["observation_role"] == "model_output"
    assert metadata["project"] == "rewrite-quality"
    assert metadata["model_name"] == "azure-mistral-large-3"
    assert metadata["baseline_reference"]["baseline_run_id"] == baseline.run_id
