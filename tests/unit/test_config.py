from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.config import (
    AuthMode,
    ConfigError,
    ProviderName,
    load_project_config,
)


def test_loads_valid_project_config_from_yaml() -> None:
    config = load_project_config(Path("configs/projects/rewrite_quality.yaml"))

    assert config.project.name == "rewrite-quality"
    assert config.baseline.auth_mode == AuthMode.AZURE_CLIENT_CREDENTIALS
    assert config.baseline.provider == ProviderName.OPENAI_COMPATIBLE
    assert config.candidates[0].name == "llama3-local"
    assert config.evaluators[0].score.managed_by_harness is True


def test_rejects_config_missing_required_sections() -> None:
    with pytest.raises(ConfigError, match="dataset"):
        load_project_config(Path("tests/fixtures/projects/invalid_missing_dataset.yaml"))


def test_rejects_literal_provider_secret_values(tmp_path: Path) -> None:
    project = tmp_path / "project.yaml"
    project.write_text(
        """
project:
  name: invalid-secrets
  version: v1
  score_config_prefix: eh_invalid_
dataset:
  kind: local_csv
  path: datasets/rewrite_quality.csv
task_prompt:
  path: prompts/rewrite_quality/task_prompt.md
  version: v1
baseline:
  name: baseline
  provider: openai_compatible
  auth_mode: azure_client_credentials
  model: gpt-4.1
  azure:
    tenant_id_env: 00000000-0000-0000-0000-000000000000
    client_id_env: EDAV_CLIENT_ID
    client_secret_env: EDAV_CLIENT_SECRET
    scope_env: EDAV_SCOPE_TOKEN_AUDIENCE
    subscription_key_env: EDAV_SUBSCRIPTION_KEY
    api_version_env: EDAV_AZURE_OPENAI_API_VERSION
    endpoint_env: EDAV_AZURE_OPENAI_ENDPOINT
  parameters:
    temperature: 0.2
candidates:
  - name: candidate
    provider: ollama
    auth_mode: none
    model: llama3
    parameters:
      temperature: 0.2
evaluators:
  - name: clarity
    type: llm_as_judge
    version: v1
    prompt_path: prompts/rewrite_quality/evaluators/clarity.md
    score:
      name: clarity
      data_type: NUMERIC
      min_value: 0
      max_value: 1
    modes: [baseline]
    variables: [input, output]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="environment variable name"):
        load_project_config(project)
