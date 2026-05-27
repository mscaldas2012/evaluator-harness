from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


def test_candidate_variants_and_repeated_runs_share_baseline_reference() -> None:
    langfuse = LangfuseClient()

    def provider_factory(_config):
        return FakeModelProvider(response=ModelResponse(output="output"))

    runner = ExperimentRunner(langfuse_client=langfuse, provider_factory=provider_factory)
    baseline = runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")

    first = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate",
        candidate="llama3-local",
        baseline=baseline.run_id,
    )
    second = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate",
        candidate="llama3-local-temp-high",
        baseline="latest-compatible",
    )
    repeated = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate",
        candidate="llama3-local",
        baseline="latest-compatible",
    )

    assert {first.run_id, second.run_id, repeated.run_id} == {
        first.run_id,
        second.run_id,
        repeated.run_id,
    }
    assert first.run_id != repeated.run_id
    assert first.baseline_reference == baseline.baseline_reference
    assert second.baseline_reference == baseline.baseline_reference
    assert repeated.baseline_reference == baseline.baseline_reference
    first_trace = [trace for trace in langfuse.traces if trace["run_id"] == first.run_id][0]
    second_trace = [trace for trace in langfuse.traces if trace["run_id"] == second.run_id][0]
    assert first_trace["metadata"]["parameter_hash"] != second_trace["metadata"]["parameter_hash"]
