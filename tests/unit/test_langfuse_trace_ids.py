from __future__ import annotations

import re

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


class FakeScoreConfigsApi:
    def __init__(self) -> None:
        self.created: list[object] = []

    def get(self, *, limit):
        return type("Page", (), {"data": []})()

    def create(self, **kwargs):
        created = type(
            "Created",
            (),
            {"id": f"score-config-{len(self.created) + 1}"},
        )()
        self.created.append(created)
        return created


def test_runner_uses_langfuse_valid_trace_ids_for_outputs() -> None:
    langfuse = DefaultLangfuseGateway()
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output")
        ),
    )

    runner.run("configs/projects/rewrite_quality.yaml", "baseline")

    assert langfuse.traces
    assert all(
        re.fullmatch(r"[0-9a-f]{32}", str(trace["trace_id"]))
        for trace in langfuse.traces
    )
    assert {trace["name"] for trace in langfuse.traces} == {
        "test/rewrite-quality/baseline-gpt5.2-dgw-default",
    }


def test_live_log_trace_passes_trace_context_to_create_event() -> None:
    class FakeLiveClient:
        def __init__(self) -> None:
            self.trace_contexts = []

        def create_event(self, **kwargs):
            self.trace_contexts.append(kwargs["trace_context"])

        def flush(self) -> None:
            pass

    live_client = FakeLiveClient()
    langfuse = DefaultLangfuseGateway(client=live_client)
    trace_id = langfuse.create_trace_id("run:item")

    langfuse.log_trace(
        {
            "trace_id": trace_id,
            "name": "test",
            "input": "input",
            "output": "output",
            "metadata": {},
        }
    )

    assert live_client.trace_contexts == [{"trace_id": trace_id}]


def test_create_run_does_not_emit_empty_live_trace_event() -> None:
    class FakeLiveClient:
        def __init__(self) -> None:
            self.create_event_called = False

        def create_event(self, **kwargs):
            self.create_event_called = True

    live_client = FakeLiveClient()
    langfuse = DefaultLangfuseGateway(client=live_client)

    langfuse.create_run(run_id="baseline-1", run_name="empty-run-event")

    assert live_client.create_event_called is False


def test_runner_nests_openai_generation_under_parent_trace_span() -> None:
    class FakeObservation:
        id = "abcdef1234567890"

        def __init__(self) -> None:
            self.updates = []

        def update(self, **kwargs):
            self.updates.append(kwargs)

    class FakeSpanContext:
        def __init__(self, observation: FakeObservation) -> None:
            self.observation = observation

        def __enter__(self) -> FakeObservation:
            return self.observation

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class FakeLiveClient:
        def __init__(self) -> None:
            self.observations: list[FakeObservation] = []
            self.started: list[dict] = []
            self.create_event_called = False
            self.flush_count = 0
            self.api = type(
                "Api",
                (),
                {"score_configs": FakeScoreConfigsApi()},
            )()

        def start_as_current_observation(self, **kwargs):
            self.started.append(kwargs)
            observation = FakeObservation()
            self.observations.append(observation)
            return FakeSpanContext(observation)

        def create_event(self, **kwargs):
            self.create_event_called = True

        def flush(self) -> None:
            self.flush_count += 1

    captured_requests = []
    live_client = FakeLiveClient()
    langfuse = DefaultLangfuseGateway(client=live_client)

    def provider_factory(config):
        from evaluator_harness.providers.openai_compatible import (
            OpenAICompatibleProvider,
        )

        class Provider:
            def generate(self, request):
                captured_requests.append(request)
                return ModelResponse(output="baseline output")

        provider = OpenAICompatibleProvider(config, generator=Provider().generate)
        return provider

    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=provider_factory,
    )

    runner.run(
        "configs/projects/rewrite_quality.yaml",
        "baseline",
        select_human_review=False,
    )

    assert captured_requests
    assert all(
        request.metadata["parent_observation_id"] == "abcdef1234567890"
        for request in captured_requests
    )
    assert live_client.create_event_called is False
    assert all(observation.updates for observation in live_client.observations)
    assert {started["as_type"] for started in live_client.started} == {
        "span",
        "generation",
    }
    generation_starts = [
        started for started in live_client.started if started["as_type"] == "generation"
    ]
    assert generation_starts
    assert all(started["name"] == "OpenAI-generation" for started in generation_starts)
    assert all("trace_context" not in started for started in generation_starts)
    assert all(
        started["metadata"]["project"] == "rewrite-quality"
        for started in generation_starts
    )
    assert all(started["metadata"]["project_version"] == "v1" for started in generation_starts)
    assert all(started["metadata"]["run_type"] == "baseline" for started in generation_starts)
    assert all(
        started["metadata"]["evaluator_set_id"] == "clarity:v1"
        for started in generation_starts
    )
    assert all(
        started["metadata"]["observation_role"] == "model_output"
        for started in generation_starts
    )


def test_runner_does_not_create_openai_generation_for_non_openai_provider() -> None:
    class FakeObservation:
        id = "abcdef1234567890"

        def update(self, **kwargs):
            pass

    class FakeSpanContext:
        def __enter__(self) -> FakeObservation:
            return FakeObservation()

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class FakeLiveClient:
        def __init__(self) -> None:
            self.started: list[dict] = []
            self.api = type(
                "Api",
                (),
                {"score_configs": FakeScoreConfigsApi()},
            )()

        def start_as_current_observation(self, **kwargs):
            self.started.append(kwargs)
            return FakeSpanContext()

        def flush(self) -> None:
            pass

    live_client = FakeLiveClient()
    langfuse = DefaultLangfuseGateway(client=live_client)
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="baseline output")
        ),
    )

    runner.run(
        "configs/projects/rewrite_quality.yaml",
        "baseline",
        select_human_review=False,
    )

    assert live_client.started
    assert {started["as_type"] for started in live_client.started} == {"span"}
