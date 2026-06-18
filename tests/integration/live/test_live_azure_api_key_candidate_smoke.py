from __future__ import annotations

import os

import pytest

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.model_output_targeting import MODEL_OUTPUT_ROLE, RUN_ITEM_ROLE
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
    runner = ExperimentRunner(langfuse_gateway=DefaultLangfuseGateway.from_env())

    baseline = runner.run("configs/projects/rewrite_quality.yaml", "baseline")
    result = runner.run(
        "configs/projects/rewrite_quality.yaml",
        "candidate",
        candidate="azure-mistral-large-3",
        baseline=baseline.run_id,
    )

    assert result.run_type == "candidate"
    traces = runner.langfuse_gateway.traces_for_run(result.run_id)
    assert traces
    errors = [
        str(trace.get("error") or (trace.get("metadata") or {}).get("error"))
        for trace in traces
        if trace.get("error") or (trace.get("metadata") or {}).get("error")
    ]
    assert result.completed_count >= 1, (
        f"candidate run completed 0 items and failed {result.failed_count}; "
        f"errors: {'; '.join(errors[:3])}"
    )
    metadata = traces[0]["metadata"]
    assert metadata["observation_role"] == RUN_ITEM_ROLE
    assert (
        metadata["provider_tracing_strategy"]["standard_observation_role"]
        == MODEL_OUTPUT_ROLE
    )
    assert metadata["project"] == "rewrite-quality"
    assert metadata["model_name"] == "azure-mistral-large-3"
    assert metadata["baseline_reference"]["baseline_run_id"] == baseline.run_id
