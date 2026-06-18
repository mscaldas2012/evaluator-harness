from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


PROJECT = Path("configs/projects/rewrite_quality.yaml")


def _runner(langfuse: DefaultLangfuseGateway, output: str = "output") -> ExperimentRunner:
    return ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output=output)
        ),
    )


def _traces_by_item(langfuse: DefaultLangfuseGateway, run_id: str) -> dict[str, dict]:
    return {
        str(trace["metadata"]["dataset_item_id"]): trace
        for trace in langfuse.traces_for_run(run_id)
    }


def test_baseline_traces_contain_official_and_metadata_session_ids() -> None:
    langfuse = DefaultLangfuseGateway()
    baseline = _runner(langfuse, "baseline output").run(
        PROJECT,
        "baseline",
        select_human_review=False,
    )

    trace = langfuse.traces_for_run(baseline.run_id)[0]
    metadata = trace["metadata"]

    assert trace["session_id"]
    assert metadata["item_comparison_session_id"] == trace["session_id"]
    assert metadata["item_comparison_session_inputs"]["baseline_anchor"] == baseline.run_id
    assert metadata["item_comparison_session_inputs"]["dataset_item_id"]


def test_baseline_and_candidate_same_item_share_session_id() -> None:
    langfuse = DefaultLangfuseGateway()
    runner = _runner(langfuse, "baseline output")
    baseline = runner.run(PROJECT, "baseline", select_human_review=False)
    candidate = runner.run(
        PROJECT,
        "candidate",
        candidate="dry-run-candidate",
        baseline=baseline.run_id,
        select_human_review=False,
    )

    baseline_traces = _traces_by_item(langfuse, baseline.run_id)
    candidate_traces = _traces_by_item(langfuse, candidate.run_id)
    item_id = sorted(baseline_traces)[0]

    assert candidate_traces[item_id]["session_id"] == baseline_traces[item_id]["session_id"]
    assert (
        candidate_traces[item_id]["metadata"]["item_comparison_session_id"]
        == baseline_traces[item_id]["metadata"]["item_comparison_session_id"]
    )


def test_different_dataset_items_do_not_share_session_id() -> None:
    langfuse = DefaultLangfuseGateway()
    baseline = _runner(langfuse, "baseline output").run(
        PROJECT,
        "baseline",
        select_human_review=False,
    )
    sessions = {
        trace["metadata"]["dataset_item_id"]: trace["session_id"]
        for trace in langfuse.traces_for_run(baseline.run_id)
    }

    assert len(sessions) >= 2
    assert len(set(sessions.values())) == len(sessions)


def test_multiple_candidates_against_same_baseline_reuse_item_sessions() -> None:
    langfuse = DefaultLangfuseGateway()
    runner = _runner(langfuse, "baseline output")
    baseline = runner.run(PROJECT, "baseline", select_human_review=False)
    first = runner.run(
        PROJECT,
        "candidate",
        candidate="dry-run-candidate",
        baseline=baseline.run_id,
        select_human_review=False,
    )
    second = runner.run(
        PROJECT,
        "candidate",
        candidate="dry-run-candidate",
        baseline=baseline.run_id,
        select_human_review=False,
    )

    baseline_traces = _traces_by_item(langfuse, baseline.run_id)
    first_traces = _traces_by_item(langfuse, first.run_id)
    second_traces = _traces_by_item(langfuse, second.run_id)

    for item_id, baseline_trace in baseline_traces.items():
        assert first_traces[item_id]["session_id"] == baseline_trace["session_id"]
        assert second_traces[item_id]["session_id"] == baseline_trace["session_id"]


def test_review_candidate_traces_retain_item_comparison_session_id() -> None:
    langfuse = DefaultLangfuseGateway()
    runner = _runner(langfuse, "baseline output")
    baseline = runner.run(PROJECT, "baseline", select_human_review=False)
    candidate = runner.run(
        PROJECT,
        "candidate",
        candidate="dry-run-candidate",
        baseline=baseline.run_id,
    )

    candidate_trace = langfuse.traces_for_run(candidate.run_id)[0]

    assert candidate.review_selection is not None
    assert candidate.review_selection.selected_count > 0
    assert candidate_trace["metadata"]["item_comparison_session_id"] == candidate_trace["session_id"]


def test_review_selection_reasons_do_not_depend_on_session_metadata() -> None:
    langfuse = DefaultLangfuseGateway()
    runner = _runner(langfuse, "baseline output")
    baseline = runner.run(PROJECT, "baseline", select_human_review=False)
    candidate = runner.run(
        PROJECT,
        "candidate",
        candidate="dry-run-candidate",
        baseline=baseline.run_id,
    )

    assert candidate.review_selection is not None
    assert candidate.review_selection.reasons
