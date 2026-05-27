from __future__ import annotations

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


def test_baseline_and_candidate_traces_include_model_output_filter_metadata() -> None:
    client = LangfuseClient()
    runner = ExperimentRunner(
        langfuse_client=client,
        provider_factory=lambda _config: FakeModelProvider(),
    )

    baseline = runner.run("configs/projects/rewrite_quality.yaml", "baseline")
    candidate = runner.run(
        "configs/projects/rewrite_quality.yaml",
        "candidate",
        candidate="dry-run-candidate",
        baseline=baseline.run_id,
    )

    traces = client.traces_for_run(baseline.run_id) + client.traces_for_run(candidate.run_id)
    assert traces
    for trace in traces:
        metadata = trace["metadata"]
        assert metadata["project"] == "rewrite-quality"
        assert metadata["project_version"] == "v1"
        assert metadata["observation_role"] == "model_output"
        assert metadata["evaluator_set_id"]
        assert metadata["dataset_name"]
        assert metadata["dataset_item_id"]
        assert metadata["prompt_version"] == "v1"
