from __future__ import annotations

from evaluator_harness.config import load_project_config
from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.review_selection import ReviewCandidate, select_review_items


def test_builds_candidate_annotation_payload_without_provider_identity_for_blind_evaluator() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = LangfuseClient()
    trace = {
        "trace_id": "trace-candidate",
        "run_id": "candidate-1",
        "input": "Source",
        "output": "Candidate",
        "metadata": {
            "dataset_item_id": "1",
            "provider": "ollama",
            "model": "llama3",
            "model_name": "llama3-local",
            "ground_truth": "Expected",
            "baseline_reference": {"baseline_run_id": "baseline-1"},
        },
    }
    client.traces.append(trace)
    client.traces.append(
        {
            "trace_id": "trace-baseline",
            "run_id": "baseline-1",
            "output": "Baseline",
            "metadata": {"dataset_item_id": "1"},
        }
    )

    payload = client.build_annotation_queue_payload(
        config,
        select_review_items([ReviewCandidate.from_trace(trace, scores=[])], config.human_review)[0],
    )

    assert payload["input"] == "Source"
    assert payload["candidate_output"] == "Candidate"
    assert payload["baseline_output"] == "Baseline"
    assert payload["ground_truth"] == "Expected"
    evaluator_payload = payload["evaluators"][0]
    assert evaluator_payload["name"] == "clarity"
    assert "provider" not in evaluator_payload
    assert "model" not in evaluator_payload
    assert "vendor" not in evaluator_payload


def test_builds_baseline_annotation_payload_with_optional_ground_truth() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = LangfuseClient()
    trace = {
        "trace_id": "trace-baseline",
        "run_id": "baseline-1",
        "input": "Source",
        "output": "Baseline",
        "metadata": {"dataset_item_id": "1", "ground_truth": "Expected"},
    }
    client.traces.append(trace)

    payload = client.build_annotation_queue_payload(
        config,
        ReviewCandidate.from_trace(trace, scores=[]).to_selection("sample"),
    )

    assert payload["baseline_output"] == "Baseline"
    assert payload["candidate_output"] is None
    assert payload["ground_truth"] == "Expected"


def test_annotation_queue_routing_skips_duplicate_items() -> None:
    client = LangfuseClient()
    payload = {"trace_id": "trace-1", "item_id": "1", "run_id": "run-1"}

    result = client.route_annotation_items("queue-1", [payload, payload])

    assert result.queued_count == 1
    assert result.skipped_duplicate_count == 1
    assert len(client.annotation_queue_items) == 1
