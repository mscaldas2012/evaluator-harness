from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeDefaultLangfuseGateway:
    reachable: bool = True
    datasets: dict[str, Any] = field(default_factory=dict)
    runs: dict[str, Any] = field(default_factory=dict)
    traces: list[dict[str, Any]] = field(default_factory=list)
    score_configs: dict[str, Any] = field(default_factory=dict)
    scores: list[dict[str, Any]] = field(default_factory=list)
    prompts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    annotation_queue_items: list[dict[str, Any]] = field(default_factory=list)
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def check_reachable(self) -> None:
        self.calls.append(("check_reachable", {}))
        if not self.reachable:
            raise ConnectionError("Langfuse is unreachable")

    def sync_dataset(self, name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls.append(("sync_dataset", {"name": name, "item_count": len(items)}))
        dataset = {"name": name, "version": "fake-version", "items": items}
        self.datasets[name] = dataset
        return dataset

    def create_run(self, run_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("create_run", {"run_id": run_id, "metadata": metadata}))
        run = {"run_id": run_id, "metadata": metadata}
        self.runs[run_id] = run
        return run

    def log_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("log_trace", trace))
        self.traces.append(trace)
        return trace

    def upsert_score_config(self, name: str, config: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("upsert_score_config", {"name": name, "config": config}))
        existing = self.score_configs.get(name)
        if existing is not None:
            return existing
        created = {"id": f"score-config-{len(self.score_configs) + 1}", **config}
        self.score_configs[name] = created
        return created

    def create_score(self, score: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("create_score", score))
        self.scores.append(score)
        return score

    def list_prompts(self, name: str | None = None) -> list[dict[str, Any]]:
        self.calls.append(("list_prompts", {"name": name}))
        if name is not None:
            return list(self.prompts.get(name, []))
        return [prompt for versions in self.prompts.values() for prompt in versions]

    def create_prompt(self, prompt: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("create_prompt", prompt))
        versions = self.prompts.setdefault(str(prompt["name"]), [])
        created = {"version": len(versions) + 1, **prompt}
        versions.append(created)
        return created

    def add_annotation_queue_item(self, item: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("add_annotation_queue_item", item))
        self.annotation_queue_items.append(item)
        return item
