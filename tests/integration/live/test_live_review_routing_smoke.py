from __future__ import annotations
import re
from pathlib import Path

import pytest

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider
from tests.fixtures.live_env import require_live_langfuse


@pytest.mark.live
def test_live_review_routing_smoke() -> None:
    require_live_langfuse()
    langfuse = DefaultLangfuseGateway.from_env()
    project_path = Path(".evaluator-harness") / "rewrite_quality_live_review.yaml"
    project_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.write_text(
        Path("configs/projects/rewrite_quality.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output for review smoke")
        ),
    )
    runner.sync_annotation_queue(project_path)
    result = runner.run(project_path, "baseline")
    for trace in langfuse.traces_for_run(result.run_id):
        langfuse.scores.setdefault(result.run_id, []).append(
            {"trace_id": trace["trace_id"], "confidence": 0.4}
        )

    review = runner.select_review(project_path, result.run_id)

    assert review.selected_count >= 1
    queue_items = langfuse.client.api.annotation_queues.list_queue_items(
        str(review.queue_id),
        limit=20,
    ).data
    assert any(
        re.fullmatch(r"[0-9a-f]{32}", item.object_id)
        for item in queue_items
    )
