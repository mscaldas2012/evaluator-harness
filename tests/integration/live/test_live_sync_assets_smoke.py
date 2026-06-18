from __future__ import annotations

import pytest

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.live_env import require_live_langfuse


@pytest.mark.live
def test_live_sync_assets_smoke() -> None:
    require_live_langfuse()
    runner = ExperimentRunner(langfuse_gateway=DefaultLangfuseGateway.from_env())

    dataset = runner.sync_dataset("configs/projects/rewrite_quality.yaml")
    scores = runner.sync_score_configs("configs/projects/rewrite_quality.yaml")

    assert dataset.item_count >= 1
    assert scores
