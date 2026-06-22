from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider

PROJECT = Path("configs/projects/rewrite_quality.yaml")


class FailingDatasetRunItems:
    def create(self, **_kwargs):
        raise RuntimeError("dataset run item write failed")


class EmptyDatasetItems:
    def list(self, **_kwargs):
        return SimpleNamespace(data=[])


class LiveClientWithFailingRunItems:
    api = SimpleNamespace(
        dataset_run_items=FailingDatasetRunItems(),
        dataset_items=EmptyDatasetItems(),
    )


class LiveClientWithFailingBaselineLookup(LiveClientWithFailingRunItems):
    def get_dataset_runs(self, **_kwargs):
        raise RuntimeError("baseline lookup unavailable")


def test_candidate_run_surfaces_partial_langfuse_persistence_warning() -> None:
    langfuse = DefaultLangfuseGateway(client=LiveClientWithFailingRunItems())
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output")
        ),
    )
    runner.run(PROJECT, "baseline", skip_sync=True, select_human_review=False)

    candidate = runner.run(
        PROJECT,
        "candidate",
        candidate="dry-run-candidate",
        baseline="latest-compatible",
        skip_sync=True,
        select_human_review=False,
    )

    assert candidate.completed_count == 2
    assert candidate.langfuse_status == "complete-with-warnings"
    assert any(
        "Langfuse dataset run item was not recorded." in warning
        for warning in candidate.langfuse_warnings
    )


def test_candidate_run_preserves_baseline_lookup_failure_when_falling_back() -> None:
    langfuse = DefaultLangfuseGateway(client=LiveClientWithFailingBaselineLookup())
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output")
        ),
    )
    baseline = runner.run(
        PROJECT,
        "baseline",
        skip_sync=True,
        select_human_review=False,
    )

    candidate = runner.run(
        PROJECT,
        "candidate",
        candidate="dry-run-candidate",
        baseline=baseline.run_id,
        skip_sync=True,
        select_human_review=False,
    )

    assert candidate.baseline_reference == baseline.baseline_reference
    assert candidate.langfuse_status == "complete-with-warnings"
    assert any(
        "Langfuse baseline lookup failed." in warning
        for warning in candidate.langfuse_warnings
    )
