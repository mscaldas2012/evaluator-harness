from __future__ import annotations

from typing import Any

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.model_output_targeting import (
    MODEL_OUTPUT_ROLE,
    RUN_ITEM_ROLE,
    diagnose_model_output_targeting,
    model_output_observations,
)
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.providers.openai_compatible import OpenAICompatibleProvider
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider
from tests.unit.test_langfuse_trace_ids import FakeScoreConfigsApi


class FakeObservation:
    id = "abcdef1234567890"

    def __init__(self, started: dict[str, Any]) -> None:
        self.started = started
        self.updates: list[dict[str, Any]] = []

    def update(self, **kwargs: Any) -> None:
        self.updates.append(kwargs)


class FakeSpanContext:
    def __init__(self, observation: FakeObservation) -> None:
        self.observation = observation

    def __enter__(self) -> FakeObservation:
        return self.observation

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class FakeLiveClient:
    def __init__(self) -> None:
        self.observations: list[FakeObservation] = []
        self.started: list[dict[str, Any]] = []
        self.api = type(
            "Api",
            (),
            {"score_configs": FakeScoreConfigsApi()},
        )()

    def start_as_current_observation(self, **kwargs: Any) -> FakeSpanContext:
        self.started.append(kwargs)
        observation = FakeObservation(kwargs)
        self.observations.append(observation)
        return FakeSpanContext(observation)

    def flush(self) -> None:
        pass


def _final_observation_snapshots(client: FakeLiveClient) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for observation in client.observations:
        metadata = dict(observation.started.get("metadata") or {})
        for update in observation.updates:
            if update.get("metadata") is not None:
                metadata.update(update["metadata"])
        snapshots.append(
            {
                "trace_id": (
                    observation.started.get("trace_context") or {}
                ).get("trace_id")
                or metadata.get("trace_id"),
                "name": observation.started.get("name"),
                "as_type": observation.started.get("as_type"),
                "metadata": metadata,
            }
        )
    return snapshots


def test_manual_generation_provider_marks_only_generation_as_model_output() -> None:
    live_client = FakeLiveClient()
    langfuse = DefaultLangfuseGateway(client=live_client)

    def provider_factory(config: Any) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            config,
            generator=lambda _request: ModelResponse(output="baseline output"),
        )

    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=provider_factory,
    )

    result = runner.run(
        "configs/projects/rewrite_quality.yaml",
        "baseline",
        select_human_review=False,
    )

    observations = _final_observation_snapshots(live_client)
    eligible = model_output_observations(observations)
    assert len(eligible) == result.completed_count
    assert {observation["as_type"] for observation in eligible} == {"generation"}
    assert {observation["name"] for observation in eligible} == {"OpenAI-generation"}
    assert all(
        observation["metadata"]["observation_role"] == RUN_ITEM_ROLE
        for observation in observations
        if observation["as_type"] == "span"
    )


def test_non_generation_provider_marks_parent_span_as_single_model_output() -> None:
    live_client = FakeLiveClient()
    langfuse = DefaultLangfuseGateway(client=live_client)
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output")
        ),
    )

    result = runner.run(
        "configs/projects/rewrite_quality.yaml",
        "baseline",
        select_human_review=False,
    )

    observations = _final_observation_snapshots(live_client)
    eligible = model_output_observations(observations)
    assert len(eligible) == result.completed_count
    assert {observation["as_type"] for observation in eligible} == {"span"}
    assert all(
        observation["metadata"]["observation_role"] == MODEL_OUTPUT_ROLE
        for observation in eligible
    )


def test_model_output_targeting_diagnostic_detects_duplicate_role_markers() -> None:
    diagnostic = diagnose_model_output_targeting(
        [
            {
                "trace_id": "trace-1",
                "name": "parent",
                "metadata": {"observation_role": MODEL_OUTPUT_ROLE},
            },
            {
                "trace_id": "trace-1",
                "name": "generation",
                "metadata": {"observation_role": MODEL_OUTPUT_ROLE},
            },
        ],
        expected_completed_count=1,
    )

    assert diagnostic.status == "duplicate"
    assert "trace-1" in diagnostic.message
