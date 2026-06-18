from __future__ import annotations

from pathlib import Path

from radon.complexity import cc_rank, cc_visit

PUBLIC_FACADE_METHODS = {
    "sync_dataset",
    "record_dataset_run_item",
    "sync_score_configs",
    "list_evaluators",
    "get_evaluator",
    "create_evaluator",
    "update_evaluator",
    "lookup_baseline",
    "fetch_scores",
    "list_prompt_versions",
    "create_prompt_version",
    "traces_for_run",
    "route_annotation_items",
    "annotation_queue_object_ids",
    "create_annotation_queue",
    "list_annotation_queues",
    "get_annotation_queue",
}


def test_langfuse_gateway_public_facade_has_no_d_ranked_blocks() -> None:
    source = Path("src/evaluator_harness/langfuse_default_gateway.py").read_text(
        encoding="utf-8"
    )
    blocks = cc_visit(source)
    facade_methods = [
        block
        for block in blocks
        if getattr(block, "classname", None) == "DefaultLangfuseGateway"
        and block.name in PUBLIC_FACADE_METHODS
    ]

    assert {block.name for block in facade_methods} == PUBLIC_FACADE_METHODS
    assert {
        block.name: cc_rank(block.complexity)
        for block in facade_methods
        if cc_rank(block.complexity) >= "D"
    } == {}
