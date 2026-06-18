from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


def test_dry_run_candidate_reuses_langfuse_baseline_across_runner_instances() -> None:
    langfuse = DefaultLangfuseGateway()
    baseline_runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output")
        ),
    )
    baseline = baseline_runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")

    candidate_runner = ExperimentRunner(langfuse_gateway=langfuse)
    candidate = candidate_runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate",
        candidate="dry-run-candidate",
        baseline="latest-compatible",
    )

    assert candidate.baseline_reference == baseline.baseline_reference
    assert candidate.completed_count == 2
    trace = langfuse.traces_for_run(candidate.run_id)[0]
    assert trace["metadata"]["baseline_reference"]["baseline_run_id"] == baseline.run_id
    assert trace["metadata"]["dataset_item_id"]


def test_candidate_partial_failures_record_successful_and_failed_items() -> None:
    langfuse = DefaultLangfuseGateway()
    baseline_runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output")
        ),
    )
    baseline_runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")

    class PartialProvider:
        def generate(self, request):
            if request.metadata["item_id"] == "2":
                raise TimeoutError("candidate timeout")
            return ModelResponse(output="candidate output")

    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: PartialProvider(),
    )
    candidate = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate",
        candidate="dry-run-candidate",
        baseline="latest-compatible",
    )

    assert candidate.completed_count == 1
    assert candidate.failed_count == 1
    traces = langfuse.traces_for_run(candidate.run_id)
    assert any(trace["output"] == "candidate output" for trace in traces)
    assert any(trace["error"] for trace in traces)
