from __future__ import annotations

from types import SimpleNamespace

import pytest

from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_traces import (
    dataset_run_items,
    live_trace_to_dict,
    merge_traces,
    output_for_workflow,
    trace_by_id_workflow,
    trace_from_metadata,
)


def test_trace_by_id_workflow_returns_matching_trace() -> None:
    owner = SimpleNamespace(traces=[{"trace_id": "trace-1", "output": "done"}])

    assert trace_by_id_workflow(owner, "trace-1")["output"] == "done"
    with pytest.raises(ConfigError):
        trace_by_id_workflow(owner, "missing")


def test_output_for_workflow_matches_run_item_metadata() -> None:
    owner = SimpleNamespace(
        traces=[
            {
                "trace_id": "trace-1",
                "run_id": "run-1",
                "output": "candidate output",
                "metadata": {"dataset_item_id": "item-1"},
            }
        ],
    )

    assert (
        output_for_workflow(owner, run_id="run-1", item_id="item-1")
        == "candidate output"
    )
    assert output_for_workflow(owner, run_id="run-1", item_id="missing") is None


def test_merge_traces_prefers_primary_trace_with_same_id() -> None:
    merged = merge_traces(
        [{"trace_id": "trace-1", "output": "primary"}],
        [{"trace_id": "trace-1", "output": "fallback"}],
    )

    assert merged == [{"trace_id": "trace-1", "output": "primary"}]


def test_trace_from_metadata_and_live_trace_to_dict_normalize_trace_shapes() -> None:
    metadata_trace = trace_from_metadata(
        {"trace_id": "trace-1", "run_id": "run-1", "error": "none"},
        run_id="fallback-run",
    )
    live_trace = live_trace_to_dict(
        SimpleNamespace(
            id="trace-2",
            name="trace",
            input={"question": "Q"},
            output="A",
            metadata={"run_id": "run-2"},
            timestamp="now",
        ),
    )

    assert metadata_trace["run_id"] == "run-1"
    assert live_trace["trace_id"] == "trace-2"
    assert live_trace["run_id"] == "run-2"


def test_dataset_run_items_accepts_common_sdk_shapes() -> None:
    assert dataset_run_items(SimpleNamespace(dataset_run_items=[1, 2])) == [1, 2]
    assert dataset_run_items(SimpleNamespace(items=[3])) == [3]
    assert dataset_run_items(SimpleNamespace(data=[4])) == [4]
