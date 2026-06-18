from __future__ import annotations

from pathlib import Path

from evaluator_harness.config import load_project_config, validate_project_config
from evaluator_harness.evaluators import managed_score_name
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.config_refs import assert_same_evaluation_config


DFE_PROJECTS = [
    (
        Path("configs/projects/dfe-general-public.yaml"),
        "dfe-general-public",
        "dfe/general-public/v1",
        Path("prompts/dfe/task_prompt_generic.md"),
        "general_public",
        "General public",
    ),
    (
        Path("configs/projects/dfe-healthcare-provider.yaml"),
        "dfe-healthcare-provider",
        "dfe/healthcare-provider/v1",
        Path("prompts/dfe/task_prompt_hcp.md"),
        "healthcare_provider",
        "Health care provider",
    ),
    (
        Path("configs/projects/dfe-public-health-sme.yaml"),
        "dfe-public-health-sme",
        "dfe/public-health-sme/v1",
        Path("prompts/dfe/task_prompt_php.md"),
        "public_health_sme",
        "Public health SME",
    ),
]


def test_dfe_scenario_project_configs_validate() -> None:
    for path, *_ in DFE_PROJECTS:
        config = load_project_config(path)

        validate_project_config(config)


def test_dfe_scenario_projects_share_evaluation_config() -> None:
    configs = [load_project_config(path) for path, *_ in DFE_PROJECTS]

    for config in configs[1:]:
        assert_same_evaluation_config(configs[0], config)


def test_dfe_scenario_projects_keep_distinct_scenario_artifacts() -> None:
    for (
        path,
        project_name,
        dataset_name,
        prompt_path,
        scenario_name,
        display_name,
    ) in DFE_PROJECTS:
        config = load_project_config(path)

        assert config.project.name == project_name
        assert config.dataset.langfuse_dataset_name == dataset_name
        assert config.task_prompt.path == prompt_path
        assert config.scenario is not None
        assert config.scenario.group == "dfe"
        assert config.scenario.name == scenario_name
        assert config.scenario.display_name == display_name


def test_dfe_scenario_score_config_names_fit_langfuse_limit() -> None:
    for path, *_ in DFE_PROJECTS:
        config = load_project_config(path)

        names = [
            managed_score_name(config, evaluator.score)
            for evaluator in config.evaluators
        ]
        assert all(len(name) <= 35 for name in names)


def test_dfe_judge_setup_carries_langfuse_model_provider_and_model() -> None:
    runner = ExperimentRunner(langfuse_gateway=DefaultLangfuseGateway())

    result = runner.sync_judge_evaluators(
        Path("configs/projects/dfe-general-public.yaml"),
        dry_run=True,
    )

    assert result.evaluators
    assert result.evaluators[0].judge_model == "gpt-5.4-mini"
    assert result.evaluators[0].llm_connection == "Azure (Peraton)"
