from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.config import (
    AuthMode,
    ConfigError,
    ProviderName,
    load_project_config,
    validate_project_config,
)


def test_loads_valid_project_config_from_yaml() -> None:
    config = load_project_config(Path("configs/projects/rewrite_quality.yaml"))

    assert config.project.name == "rewrite-quality"
    assert config.baseline.auth_mode == AuthMode.AZURE_CLIENT_CREDENTIALS
    assert config.baseline.provider == ProviderName.OPENAI_COMPATIBLE
    assert [candidate.name for candidate in config.candidates] == [
        "gpt5.2-dgw-default-prompt-v2",
        "gpt5.2-dgw-default-temp-high",
        "dry-run-candidate",
        "azure-mistral-large-3",
    ]
    assert config.evaluators[0].score.managed_by_harness is True


def test_standard_model_output_judge_does_not_require_observation_name() -> None:
    config = load_project_config(Path("configs/projects/rewrite_quality.yaml"))

    evaluator = config.evaluators[0]

    assert evaluator.target_observation_role == "model_output"
    assert evaluator.target_observation_name is None
    validate_project_config(config)


def test_loads_valid_azure_api_key_candidate_config() -> None:
    config = load_project_config(
        Path("tests/fixtures/projects/valid_azure_api_key_candidate.yaml")
    )

    candidate = config.candidates[0]
    assert candidate.provider == ProviderName.OPENAI_COMPATIBLE
    assert candidate.auth_mode == AuthMode.API_KEY
    assert candidate.azure is None
    assert candidate.azure_api_key is not None
    assert candidate.azure_api_key.api_key_env == "API_KEY_PROJECT_MISTRAL_LARGE_3_API_KEY"
    assert candidate.azure_api_key.endpoint_env == "API_KEY_PROJECT_MISTRAL_LARGE_3_ENDPOINT"
    assert (
        candidate.azure_api_key.api_version_env
        == "API_KEY_PROJECT_MISTRAL_LARGE_3_API_VERSION"
    )


def test_accepts_candidate_level_task_prompt_override() -> None:
    config = load_project_config(
        Path("tests/fixtures/projects/valid_prompt_variant_candidate.yaml")
    )

    candidate = config.candidates[0]
    assert candidate.task_prompt is not None
    assert candidate.task_prompt.path == Path(
        "tests/fixtures/prompts/rewrite_quality_task_prompt_v2.md"
    )
    assert candidate.task_prompt.version == "v2"
    validate_project_config(config)


def test_rejects_duplicate_candidate_names(tmp_path: Path) -> None:
    project = tmp_path / "project.yaml"
    project.write_text(
        """
project:
  name: duplicate-candidates
  version: v1
  score_config_prefix: eh_duplicate_
dataset:
  kind: local_csv
  path: datasets/rewrite_quality.csv
task_prompt:
  path: prompts/rewrite_quality/task_prompt.md
  version: v1
baseline:
  name: baseline
  provider: dry_run
  auth_mode: none
  model: dry-run
  parameters:
    temperature: 0.0
candidates:
  - name: candidate
    provider: dry_run
    auth_mode: none
    model: dry-run
    parameters:
      temperature: 0.0
  - name: candidate
    provider: dry_run
    auth_mode: none
    model: dry-run
    parameters:
      temperature: 0.0
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
    modes: [baseline, candidate]
    variables: [input, output, baseline_output]
    required_inputs: [input, output, baseline_output]
    output_schema:
      reasoning: string
      score:
        type: number
        minimum: 0
        maximum: 1
      confidence:
        type: number
        minimum: 0
        maximum: 1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="Candidate names must be unique"):
        load_project_config(project)


def test_rejects_candidate_prompt_override_with_missing_file() -> None:
    config = load_project_config(
        Path("tests/fixtures/projects/invalid_prompt_variant_missing_prompt.yaml")
    )

    with pytest.raises(ConfigError, match="Prompt file not found"):
        validate_project_config(config)


def test_rejects_candidate_prompt_override_without_required_input_variable() -> None:
    config = load_project_config(
        Path("tests/fixtures/projects/invalid_prompt_variant_missing_input.yaml")
    )

    with pytest.raises(ConfigError, match="must declare variable input"):
        validate_project_config(config)


def test_generation_parameter_identity_changes_when_parameters_change() -> None:
    from evaluator_harness.runner import generation_parameter_hash

    config = load_project_config(
        Path("tests/fixtures/projects/valid_parameter_variants.yaml")
    )

    assert generation_parameter_hash(config.candidates[0]) != generation_parameter_hash(
        config.candidates[1]
    )


def test_rejects_api_key_auth_without_api_key_refs() -> None:
    with pytest.raises(ConfigError, match="azure_api_key credential env references"):
        load_project_config(
            Path("tests/fixtures/projects/invalid_azure_api_key_candidate_missing_refs.yaml")
        )


def test_rejects_api_key_auth_with_tenant_client_refs(tmp_path: Path) -> None:
    project = tmp_path / "project.yaml"
    project.write_text(
        """
project:
  name: invalid-mixed-auth
  version: v1
  score_config_prefix: eh_invalid_mixed_
dataset:
  kind: local_csv
  path: datasets/rewrite_quality.csv
task_prompt:
  path: prompts/rewrite_quality/task_prompt.md
  version: v1
baseline:
  name: baseline
  provider: dry_run
  auth_mode: none
  model: dry-run
  parameters:
    temperature: 0.0
candidates:
  - name: candidate
    provider: openai_compatible
    auth_mode: api_key
    model: mistral-large-3
    azure:
      tenant_id_env: EDAV_TENANT_ID
      client_id_env: EDAV_CLIENT_ID
      client_secret_env: EDAV_CLIENT_SECRET
      scope_env: EDAV_SCOPE_TOKEN_AUDIENCE
      subscription_key_env: EDAV_SUBSCRIPTION_KEY
      api_version_env: EDAV_AZURE_OPENAI_API_VERSION
      endpoint_env: EDAV_AZURE_OPENAI_ENDPOINT
    azure_api_key:
      api_key_env: CANDIDATE_API_KEY
      endpoint_env: CANDIDATE_ENDPOINT
      api_version_env: CANDIDATE_API_VERSION
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
    variables: [input, output]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="must not include azure credential refs"):
        load_project_config(project)


def test_auth_mode_is_not_inferred_from_available_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CANDIDATE_API_KEY", "secret")
    monkeypatch.setenv("CANDIDATE_ENDPOINT", "https://example.test")
    monkeypatch.setenv("CANDIDATE_API_VERSION", "2024-12-01-preview")

    config = load_project_config(
        Path("tests/fixtures/projects/valid_azure_api_key_candidate.yaml")
    )

    assert config.baseline.provider == ProviderName.DRY_RUN
    assert config.baseline.auth_mode == AuthMode.NONE
    assert config.candidates[0].auth_mode == AuthMode.API_KEY


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


def test_rejects_literal_api_key_candidate_secret_values() -> None:
    with pytest.raises(ConfigError, match="environment variable name"):
        load_project_config(
            Path("tests/fixtures/projects/invalid_azure_api_key_candidate_literal_secret.yaml")
        )
