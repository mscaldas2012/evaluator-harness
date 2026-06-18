from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from evaluator_harness.config import LiveSettings


class LangfuseGateway(Protocol):
    client: Any | None
    traces: list[dict[str, Any]]
    scores: dict[str, list[dict[str, Any]]]
    baseline_references: dict[str, Any]
    baseline_evaluator_payloads: list[dict[str, Any]]
    candidate_evaluator_payloads: list[dict[str, Any]]

    def check_reachable(
        self,
        *,
        operation: str,
        dataset_item_id: str | None = None,
    ) -> None: ...

    def sync_dataset(self, *args: Any, **kwargs: Any) -> Any: ...

    def record_dataset_run_item(self, *args: Any, **kwargs: Any) -> None: ...

    def list_score_configs(self) -> list[Any]: ...

    def sync_score_configs(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_prompt_versions(self, *args: Any, **kwargs: Any) -> Any: ...

    def create_prompt_version(self, *args: Any, **kwargs: Any) -> Any: ...

    def find_prompt_version(self, *args: Any, **kwargs: Any) -> Any: ...

    def traces_for_run(self, *args: Any, **kwargs: Any) -> Any: ...

    def trace_by_id(self, *args: Any, **kwargs: Any) -> Any: ...

    def fetch_scores(self, *args: Any, **kwargs: Any) -> Any: ...

    def output_for(self, *args: Any, **kwargs: Any) -> Any: ...

    def scores_for_traces(self, trace_ids: list[str]) -> list[Any]: ...

    def list_evaluators(self) -> list[dict[str, Any]]: ...

    def get_evaluator(self, *args: Any, **kwargs: Any) -> Any: ...

    def create_evaluator(self, *args: Any, **kwargs: Any) -> Any: ...

    def update_evaluator(self, *args: Any, **kwargs: Any) -> Any: ...

    def inactivate_evaluator(self, *args: Any, **kwargs: Any) -> Any: ...

    def supports_evaluator_backfill(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_annotation_queues(self) -> list[dict[str, Any]]: ...

    def get_annotation_queue(self, *args: Any, **kwargs: Any) -> Any: ...

    def create_annotation_queue(self, *args: Any, **kwargs: Any) -> Any: ...

    def build_annotation_queue_payload(self, *args: Any, **kwargs: Any) -> Any: ...

    def route_annotation_items(self, *args: Any, **kwargs: Any) -> Any: ...

    def annotation_queue_object_ids(self, *args: Any, **kwargs: Any) -> Any: ...

    def align_score_config_to_existing_id(self, *args: Any, **kwargs: Any) -> Any: ...

    def create_run(self, *args: Any, **kwargs: Any) -> Any: ...

    def log_trace(self, *args: Any, **kwargs: Any) -> Any: ...

    def trace_span(self, *args: Any, **kwargs: Any) -> Any: ...

    def generation_span(self, *args: Any, **kwargs: Any) -> Any: ...

    def observation_id(self, *args: Any, **kwargs: Any) -> Any: ...

    def update_trace_span(self, *args: Any, **kwargs: Any) -> Any: ...

    def update_generation_span(self, *args: Any, **kwargs: Any) -> Any: ...

    def create_trace_id(self, *args: Any, **kwargs: Any) -> str: ...

    def supports_observation_spans(self) -> bool: ...

    def record_baseline_reference(self, *args: Any, **kwargs: Any) -> None: ...

    def lookup_baseline(self, *args: Any, **kwargs: Any) -> Any: ...

    def enqueue_baseline_evaluator_payload(self, *args: Any, **kwargs: Any) -> None: ...

    def enqueue_candidate_evaluator_payload(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...


@dataclass(frozen=True)
class GatewayFactoryInput:
    client: Any | None = None
    settings: LiveSettings | None = None
    http_transport: Any | None = None
    reachable: bool = True


def should_use_in_memory_gateway(config: GatewayFactoryInput) -> bool:
    return config.client is None


def gateway_config_from_connection(
    *,
    client: Any | None,
    settings: LiveSettings | None,
    http_transport: Any | None,
    reachable: bool,
) -> GatewayFactoryInput:
    return GatewayFactoryInput(
        client=client,
        settings=settings,
        http_transport=http_transport,
        reachable=reachable,
    )


def build_langfuse_gateway(*, owner: Any, config: GatewayFactoryInput) -> Any:
    if should_use_in_memory_gateway(config):
        from evaluator_harness.langfuse_in_memory import InMemoryLangfuseGateway

        return InMemoryLangfuseGateway(owner=owner)

    from evaluator_harness.langfuse_rest import LangfuseRestGateway
    from evaluator_harness.langfuse_sdk import LangfuseSdkGateway

    rest = LangfuseRestGateway(
        owner=owner,
        settings=config.settings,
        http_transport=config.http_transport,
    )
    return LangfuseSdkGateway(owner=owner, client=config.client, rest=rest)


def build_default_langfuse_gateway() -> LangfuseGateway:
    from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway

    return DefaultLangfuseGateway()


def build_langfuse_gateway_from_env() -> LangfuseGateway:
    from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway

    return DefaultLangfuseGateway.from_env()
