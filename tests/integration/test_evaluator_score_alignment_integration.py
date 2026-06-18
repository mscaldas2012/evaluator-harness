from __future__ import annotations

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.runner import ExperimentRunner


def test_annotation_queue_uses_managed_evaluator_score_config(tmp_path) -> None:
    client = DefaultLangfuseGateway()
    runner = ExperimentRunner(langfuse_gateway=client)
    runner.annotation_queue_store.base_dir = tmp_path

    result = runner.sync_annotation_queue("configs/projects/rewrite_quality.yaml")

    assert result.score_config_ids == ["score-config-1"]
    assert client.annotation_queues[result.queue_id]["score_config_ids"] == [
        "score-config-1"
    ]
