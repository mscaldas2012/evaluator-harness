from __future__ import annotations

from evaluator_harness.langfuse_in_memory import InMemoryLangfuseGateway
from evaluator_harness.langfuse_records import (
    DatasetItemRecord,
    RunRecord,
    ScoreRecord,
    TraceRecord,
)


def test_in_memory_gateway_stores_dataset_runs_traces_and_scores() -> None:
    gateway = InMemoryLangfuseGateway()
    item = DatasetItemRecord(
        id="dataset-a:item-1",
        dataset_name="dataset-a",
        item_id="item-1",
        input={"text": "Rewrite"},
        expected_output="Rewritten",
    )

    dataset = gateway.sync_dataset("dataset-a", [item])
    gateway.record_dataset_run_item(
        RunRecord(id="run-1", name="baseline", dataset_name="dataset-a"),
        item,
    )
    gateway.log_trace(
        TraceRecord(
            id="trace-1",
            run_id="run-1",
            name="candidate",
            output="Result",
            metadata={"dataset_item_id": "item-1"},
        )
    )
    gateway.record_score(
        ScoreRecord(
            id="score-1",
            name="clarity",
            value=1,
            trace_id="trace-1",
        )
    )

    assert dataset.name == "dataset-a"
    assert gateway.dataset_items["dataset-a"] == [item]
    assert gateway.traces_for_run("run-1")[0].id == "trace-1"
    assert gateway.scores_for_traces(["trace-1"])[0].name == "clarity"


def test_in_memory_gateway_stores_prompts_evaluators_and_annotation_queues() -> None:
    gateway = InMemoryLangfuseGateway()

    prompt = gateway.create_prompt_version(
        {"name": "rewrite", "prompt": "Rewrite {{input}}", "labels": ["prod"]}
    )
    evaluator = gateway.create_evaluator(
        {
            "name": "clarity",
            "active": True,
            "score_config_id": "score-config-1",
        }
    )
    updated = gateway.update_evaluator(str(evaluator.id), {"active": False})
    queue = gateway.create_annotation_queue(
        name="Review",
        score_config_ids=["score-config-1"],
        description="Human review",
    )
    routed = gateway.route_annotation_items(
        queue.id,
        [{"trace_id": "trace-1"}, {"object_id": "trace-2"}],
    )

    assert prompt.version == 1
    assert gateway.list_prompt_versions("rewrite") == [prompt]
    assert updated.active is False
    assert gateway.get_evaluator(str(evaluator.id)) == updated
    assert gateway.list_annotation_queues() == [queue]
    assert routed.queued_count == 2
    assert gateway.annotation_queue_object_ids(queue.id) == {"trace-1", "trace-2"}
