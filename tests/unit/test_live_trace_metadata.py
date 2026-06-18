from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


def test_live_trace_metadata_contains_dataset_item_correlation_fields() -> None:
    langfuse = DefaultLangfuseGateway()
    provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )

    result = runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")

    trace = langfuse.traces_for_run(result.run_id)[0]
    metadata = trace["metadata"]
    assert metadata["dataset_name"] == "rewrite-quality/v1"
    assert metadata["dataset_compatibility_version"].startswith("sha256:")
    assert metadata["dataset_item_id"]
    assert metadata["langfuse_dataset_item_id"]
    assert metadata["dataset_run_item_id"]
