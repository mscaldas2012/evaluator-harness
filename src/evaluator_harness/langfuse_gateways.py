from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from evaluator_harness.config import LiveSettings
from evaluator_harness.langfuse_records import (
    AnnotationQueueRecord,
    DatasetItemRecord,
    DatasetRecord,
    EvaluatorRecord,
    PromptRecord,
    RunRecord,
    ScoreConfigRecord,
    ScoreRecord,
    TraceRecord,
)


class LangfuseGateway(Protocol):
    def check_reachable(self, *, operation: str) -> None: ...

    def sync_dataset(
        self,
        name: str,
        items: list[DatasetItemRecord],
    ) -> DatasetRecord: ...

    def record_dataset_run_item(
        self,
        run: RunRecord,
        item: DatasetItemRecord,
    ) -> None: ...

    def list_score_configs(self) -> list[ScoreConfigRecord]: ...

    def list_prompt_versions(self, name: str) -> list[PromptRecord]: ...

    def traces_for_run(self, run_id: str) -> list[TraceRecord]: ...

    def scores_for_traces(self, trace_ids: list[str]) -> list[ScoreRecord]: ...

    def list_evaluators(self) -> list[EvaluatorRecord]: ...

    def list_annotation_queues(self) -> list[AnnotationQueueRecord]: ...


@dataclass(frozen=True)
class GatewayFactoryInput:
    client: Any | None = None
    settings: LiveSettings | None = None
    http_transport: Any | None = None
    reachable: bool = True


def should_use_in_memory_gateway(config: GatewayFactoryInput) -> bool:
    return config.client is None


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
