from __future__ import annotations

from pathlib import Path

from evaluator_harness.evaluator_bindings import load_evaluator_bindings
from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner


def _project_with_binding(tmp_path: Path, source: str = "tests/fixtures/projects/valid_rewrite_quality.yaml") -> Path:
    project = tmp_path / "project.yaml"
    binding = tmp_path / "bindings.yaml"
    text = Path(source).read_text(encoding="utf-8")
    text = text.replace(
        "  binding_path: configs/langfuse/evaluator_bindings/rewrite-quality.yaml",
        f"  binding_path: {binding.as_posix()}",
    )
    project.write_text(text, encoding="utf-8")
    return project


def test_sync_judge_evaluators_apply_creates_active_fake_evaluator(tmp_path: Path) -> None:
    client = LangfuseClient()
    runner = ExperimentRunner(langfuse_client=client)
    project = _project_with_binding(tmp_path)
    path = tmp_path / "bindings.yaml"

    result = runner.sync_judge_evaluators(project)

    assert result.overall_status == "success"
    assert result.evaluators[0].operation.value == "create"
    assert next(iter(client.evaluators.values()))["active"] is True
    assert load_evaluator_bindings(path).bindings[0].langfuse_evaluator_id == "eval-1"


def test_sync_judge_evaluators_apply_uses_resolved_score_config_id(tmp_path: Path) -> None:
    client = LangfuseClient()
    runner = ExperimentRunner(langfuse_client=client)
    project = _project_with_binding(tmp_path)
    path = tmp_path / "bindings.yaml"

    result = runner.sync_judge_evaluators(project)

    created = next(iter(client.evaluators.values()))
    binding = load_evaluator_bindings(path).bindings[0]
    assert result.evaluators[0].score_target.score_config_id == "score-config-1"
    assert result.evaluators[0].managed_display_name == "eh_rewrite_quality_clarity"
    assert created["display_name"] == "eh_rewrite_quality_clarity"
    assert created["score_config_id"] == "score-config-1"
    assert binding.score_config_id == "score-config-1"
    assert binding.langfuse_display_name == "eh_rewrite_quality_clarity"


def test_sync_judge_evaluators_dry_run_does_not_mutate_fake_state(tmp_path: Path) -> None:
    client = LangfuseClient()
    runner = ExperimentRunner(langfuse_client=client)
    project = _project_with_binding(tmp_path)

    result = runner.sync_judge_evaluators(
        project,
        dry_run=True,
    )

    assert result.mode == "preview"
    assert client.evaluators == {}


def test_sync_judge_evaluators_apply_updates_mismatched_score_config_id(tmp_path: Path) -> None:
    client = LangfuseClient()
    runner = ExperimentRunner(langfuse_client=client)
    project = _project_with_binding(tmp_path)

    first = runner.sync_judge_evaluators(project)
    evaluator_id = str(first.evaluators[0].remote_evaluator_id)
    client.evaluators[evaluator_id]["score_config_id"] = "stale-score-config"

    second = runner.sync_judge_evaluators(project)

    assert second.evaluators[0].operation.value == "update"
    assert second.evaluators[0].changes == {"score_config_id": "score-config-1"}
    assert client.evaluators[evaluator_id]["score_config_id"] == "score-config-1"


def test_sync_judge_evaluators_partial_success_preserves_created_evaluator(tmp_path: Path) -> None:
    class FailingSecondCreateClient(LangfuseClient):
        def create_evaluator(self, payload):
            if self.evaluators:
                store = load_evaluator_bindings(tmp_path / "bindings.yaml")
                assert len(store.bindings) == 1
                assert store.bindings[0].langfuse_evaluator_id == "eval-1"
                raise RuntimeError("simulated remote failure")
            return super().create_evaluator(payload)

    client = FailingSecondCreateClient()
    runner = ExperimentRunner(langfuse_client=client)
    project = _project_with_binding(tmp_path)
    text = project.read_text(encoding="utf-8")
    second = text[text.index("  - name: clarity") :].replace(
        "name: clarity",
        "name: clarity-second",
        1,
    ).replace(
        "evaluator_set_id: clarity:v1",
        "evaluator_set_id: clarity-second:v1",
        1,
    )
    project.write_text(text + "\n" + second, encoding="utf-8")

    result = runner.sync_judge_evaluators(project)

    assert result.overall_status == "partial_success"
    assert len(client.evaluators) == 1
