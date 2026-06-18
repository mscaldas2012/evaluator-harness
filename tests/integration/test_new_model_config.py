from __future__ import annotations

from pathlib import Path

import yaml

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


def test_new_configured_candidate_uses_existing_runner_workflow(tmp_path: Path) -> None:
    source = Path("configs/projects/rewrite_quality.yaml")
    project = yaml.safe_load(source.read_text(encoding="utf-8"))
    project["candidates"].append(
        {
            "name": "azure-candidate-low-temp",
            "provider": "openai_compatible",
            "auth_mode": "azure_client_credentials",
            "model": "gpt-4.1-mini",
            "azure": project["baseline"]["azure"],
            "parameters": {
                "temperature": 0.1,
                "top_p": 1.0,
                "max_tokens": 1024,
            },
        }
    )
    project_path = tmp_path / "project.yaml"
    project_path.write_text(yaml.safe_dump(project), encoding="utf-8")
    langfuse = DefaultLangfuseGateway()

    def provider_factory(_config):
        return FakeModelProvider(response=ModelResponse(output="configured output"))

    runner = ExperimentRunner(langfuse_gateway=langfuse, provider_factory=provider_factory)
    baseline = runner.run(project_path, "baseline")
    candidate = runner.run(
        project_path,
        "candidate",
        candidate="azure-candidate-low-temp",
        baseline=baseline.run_id,
    )

    assert candidate.completed_count == 2
    trace = [trace for trace in langfuse.traces if trace["run_id"] == candidate.run_id][0]
    assert trace["metadata"]["model_name"] == "azure-candidate-low-temp"
    assert trace["metadata"]["model"] == "gpt-4.1-mini"
