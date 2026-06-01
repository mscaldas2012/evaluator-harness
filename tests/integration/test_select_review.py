from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner


def test_select_review_routes_configured_queue_items() -> None:
    langfuse = LangfuseClient()
    langfuse.traces.extend(
        [
            {
                "trace_id": "trace-1",
                "run_id": "candidate-1",
                "input": "Source 1",
                "output": "Candidate 1",
                "error": "provider timeout",
                "metadata": {
                    "dataset_item_id": "1",
                    "ground_truth": "Expected 1",
                    "baseline_reference": {"baseline_run_id": "baseline-1"},
                    "provider": "ollama",
                    "model": "llama3",
                },
            },
            {
                "trace_id": "trace-2",
                "run_id": "candidate-1",
                "input": "Source 2",
                "output": "Candidate 2",
                "metadata": {
                    "dataset_item_id": "2",
                    "ground_truth": "Expected 2",
                    "baseline_reference": {"baseline_run_id": "baseline-1"},
                },
            },
            {
                "trace_id": "trace-baseline-1",
                "run_id": "baseline-1",
                "output": "Baseline 1",
                "metadata": {"dataset_item_id": "1"},
            },
        ]
    )
    langfuse.scores["candidate-1"] = [{"trace_id": "trace-2", "score": 0.2, "confidence": 0.4}]

    result = ExperimentRunner(langfuse_client=langfuse).select_review(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
    )

    assert result.selected_count >= 1
    assert result.queued_count == result.selected_count
    assert result.queue_id == "annotation-queue-1"
    assert langfuse.annotation_queue_items[0]["baseline_output"] == "Baseline 1"


def test_select_review_uses_live_trace_lookup_across_runner_instances() -> None:
    langfuse = LangfuseClient()
    langfuse.traces.append(
        {
            "trace_id": "trace-1",
            "run_id": "candidate-1",
            "input": "Source 1",
            "output": "Candidate 1",
            "metadata": {
                "run_id": "candidate-1",
                "dataset_item_id": "1",
                "dataset_name": "rewrite-quality/v1",
                "dataset_version": "latest",
                "baseline_reference": {"baseline_run_id": "baseline-1"},
            },
        }
    )
    fresh_client = LangfuseClient(client=FakeTraceApi(langfuse.traces))

    result = ExperimentRunner(langfuse_client=fresh_client).select_review(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
    )

    assert result.selected_count == 1
    assert result.queued_count == 1


def test_select_review_uses_project_dataset_name_for_live_dataset_run_lookup() -> None:
    langfuse = DatasetScopedTraceClient()

    result = ExperimentRunner(langfuse_client=langfuse).select_review(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
    )

    assert langfuse.requested_dataset_names == ["rewrite-quality/v1"]
    assert result.selected_count == 1
    assert result.queued_count == 1


def test_select_review_samples_only_unqueued_items() -> None:
    langfuse = LangfuseClient()
    for index in range(1, 4):
        langfuse.traces.append(
            {
                "trace_id": f"trace-{index}",
                "run_id": "candidate-1",
                "input": f"Source {index}",
                "output": f"Candidate {index}",
                "metadata": {
                    "run_id": "candidate-1",
                    "dataset_item_id": str(index),
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                },
            }
        )
    langfuse.annotation_queue_items.extend(
        [
            {"queue_id": "annotation-queue-1", "object_id": "trace-1"},
            {"queue_id": "annotation-queue-1", "object_id": "trace-2"},
        ]
    )

    result = ExperimentRunner(langfuse_client=langfuse).select_review(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
        sample_strategy="random",
    )

    assert result.selected_count == 1
    assert result.queued_count == 1
    assert langfuse.annotation_queue_items[-1]["object_id"] == "trace-3"


def test_select_review_returns_zero_when_all_items_already_queued() -> None:
    langfuse = LangfuseClient()
    for index in range(1, 4):
        trace_id = f"trace-{index}"
        langfuse.traces.append(
            {
                "trace_id": trace_id,
                "run_id": "candidate-1",
                "input": f"Source {index}",
                "output": f"Candidate {index}",
                "metadata": {
                    "run_id": "candidate-1",
                    "dataset_item_id": str(index),
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                },
            }
        )
        langfuse.annotation_queue_items.append(
            {"queue_id": "annotation-queue-1", "object_id": trace_id}
        )

    result = ExperimentRunner(langfuse_client=langfuse).select_review(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
        sample_strategy="random",
    )

    assert result.selected_count == 0
    assert result.queued_count == 0
    assert result.skipped_duplicate_count == 0


class FakeTraceApi:
    def __init__(self, traces):
        self.api = type(
            "Api",
            (),
            {
                "trace": self,
                "score_configs": FakeScoreConfigsApi(),
            },
        )()
        self._traces = traces

    def auth_check(self):
        return True

    def list(self, **kwargs):
        run_id = kwargs.get("filter")
        data = []
        for trace in self._traces:
            if run_id and str(trace["metadata"]["run_id"]) not in str(run_id):
                continue
            data.append(type("Trace", (), trace)())
        return type("Page", (), {"data": data})()


class FakeScoreConfigsApi:
    def get(self, *, limit):
        return type(
            "Page",
            (),
            {
                "data": [
                    {
                        "id": "score-config-1",
                        "name": "eh_rewrite_quality_clarity",
                        "data_type": "NUMERIC",
                        "min_value": 0,
                        "max_value": 1,
                        "categories": None,
                        "is_archived": False,
                    }
                ]
            },
        )()

    def create(self, **kwargs):
        raise AssertionError("score config should be reused")


class DatasetScopedTraceClient(LangfuseClient):
    def __init__(self) -> None:
        super().__init__()
        self.requested_dataset_names: list[str] | None = None

    def traces_for_run(self, run_id: str, *, dataset_names=None):
        self.requested_dataset_names = dataset_names
        if dataset_names != ["rewrite-quality/v1"]:
            return []
        traces = [
            {
                "trace_id": "trace-1",
                "run_id": run_id,
                "input": "Source 1",
                "output": "Candidate 1",
                "metadata": {
                    "run_id": run_id,
                    "dataset_item_id": "1",
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                },
            }
        ]
        self.traces.extend(traces)
        return traces
