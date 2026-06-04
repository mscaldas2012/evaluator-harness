from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.config import ConfigError, load_project_config
from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


SCENARIO_PROJECT = Path("tests/fixtures/projects/config_refs/valid_scenario_project.yaml")


def test_accepts_complete_scenario_identity() -> None:
    config = load_project_config(SCENARIO_PROJECT)

    assert config.scenario is not None
    assert config.scenario.group == "fixture"
    assert config.scenario.name == "scenario_one"
    assert config.scenario.display_name == "Scenario One"


def test_rejects_incomplete_scenario_identity() -> None:
    with pytest.raises(ConfigError, match="scenario.*display_name"):
        load_project_config(
            Path("tests/fixtures/projects/config_refs/incomplete_scenario_project.yaml")
        )


def test_baseline_trace_and_request_metadata_include_scenario_fields() -> None:
    langfuse = LangfuseClient()
    provider = FakeModelProvider()
    runner = ExperimentRunner(
        langfuse_client=langfuse,
        provider_factory=lambda _config: provider,
    )

    runner.run(SCENARIO_PROJECT, "baseline", select_human_review=False)

    trace_metadata = langfuse.traces[0]["metadata"]
    request_metadata = provider.calls[0].metadata
    assert trace_metadata["scenario_group"] == "fixture"
    assert trace_metadata["scenario_name"] == "scenario_one"
    assert trace_metadata["scenario_display_name"] == "Scenario One"
    assert request_metadata["scenario_group"] == "fixture"
    assert request_metadata["scenario_name"] == "scenario_one"
    assert request_metadata["scenario_display_name"] == "Scenario One"


def test_candidate_trace_metadata_include_scenario_fields() -> None:
    langfuse = LangfuseClient()
    provider = FakeModelProvider()
    runner = ExperimentRunner(
        langfuse_client=langfuse,
        provider_factory=lambda _config: provider,
    )
    baseline_result = runner.run(SCENARIO_PROJECT, "baseline", select_human_review=False)
    assert baseline_result.baseline_reference is not None

    runner.run(
        SCENARIO_PROJECT,
        "candidate",
        candidate="dry-run-candidate",
        baseline=baseline_result.baseline_reference.baseline_run_id,
        select_human_review=False,
    )

    candidate_trace = [
        trace
        for trace in langfuse.traces
        if trace["metadata"]["run_type"] == "candidate"
    ][0]
    assert candidate_trace["metadata"]["scenario_group"] == "fixture"
    assert candidate_trace["metadata"]["scenario_name"] == "scenario_one"
    assert candidate_trace["metadata"]["scenario_display_name"] == "Scenario One"


def test_run_metadata_include_scenario_fields() -> None:
    langfuse = LangfuseClient()
    runner = ExperimentRunner(
        langfuse_client=langfuse,
        provider_factory=lambda _config: FakeModelProvider(),
    )

    result = runner.run(SCENARIO_PROJECT, "baseline", select_human_review=False)

    run_metadata = langfuse.runs[result.run_id]["kwargs"]["metadata"]
    assert run_metadata["scenario_group"] == "fixture"
    assert run_metadata["scenario_name"] == "scenario_one"
    assert run_metadata["scenario_display_name"] == "Scenario One"


def test_non_scenario_project_traces_do_not_require_scenario_fields() -> None:
    langfuse = LangfuseClient()
    runner = ExperimentRunner(
        langfuse_client=langfuse,
        provider_factory=lambda _config: FakeModelProvider(),
    )

    runner.run(
        Path("tests/fixtures/projects/valid_prompt_sync.yaml"),
        "baseline",
        select_human_review=False,
    )

    metadata = langfuse.traces[0]["metadata"]
    assert "scenario_group" not in metadata
    assert "scenario_name" not in metadata
    assert "scenario_display_name" not in metadata
