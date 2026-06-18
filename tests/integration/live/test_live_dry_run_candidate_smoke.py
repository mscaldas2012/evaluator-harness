from __future__ import annotations

import pytest

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider
from tests.fixtures.live_env import require_live_langfuse


@pytest.mark.live
def test_live_dry_run_candidate_smoke() -> None:
    require_live_langfuse()
    langfuse = DefaultLangfuseGateway.from_env()
    baseline_runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output for dry-run smoke")
        ),
    )
    baseline_runner.run("configs/projects/rewrite_quality.yaml", "baseline")

    candidate = ExperimentRunner(langfuse_gateway=langfuse).run(
        "configs/projects/rewrite_quality.yaml",
        "candidate",
        candidate="dry-run-candidate",
        baseline="latest-compatible",
    )

    assert candidate.run_type == "candidate"
    assert candidate.completed_count >= 1
