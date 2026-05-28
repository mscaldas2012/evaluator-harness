from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from evaluator_harness.cli import app


def test_new_openai_compatible_candidate_config_needs_no_cli_or_dataset_change(
    tmp_path: Path,
) -> None:
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

    result = CliRunner().invoke(app, ["validate", "--project", str(project_path)])

    assert result.exit_code == 0
    assert "azure-candidate-low-temp" in result.stdout


def test_azure_api_key_candidate_config_needs_no_cli_or_dataset_change(
    tmp_path: Path,
) -> None:
    source = Path("configs/projects/rewrite_quality.yaml")
    project = yaml.safe_load(source.read_text(encoding="utf-8"))
    project["candidates"].append(
        {
            "name": "azure-api-key-candidate",
            "provider": "openai_compatible",
            "auth_mode": "api_key",
            "model": "mistral-large-3",
            "azure_api_key": {
                "api_key_env": "REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY",
                "endpoint_env": "REWRITE_QUALITY_MISTRAL_LARGE_3_ENDPOINT",
                "api_version_env": "REWRITE_QUALITY_MISTRAL_LARGE_3_API_VERSION",
            },
            "parameters": {
                "temperature": 0.2,
                "top_p": 1.0,
                "max_tokens": 2048,
                "token_limit_parameter": "max_completion_tokens",
            },
        }
    )
    project_path = tmp_path / "project.yaml"
    project_path.write_text(yaml.safe_dump(project), encoding="utf-8")

    result = CliRunner().invoke(app, ["validate", "--project", str(project_path)])

    assert result.exit_code == 0
    assert "azure-api-key-candidate" in result.stdout
