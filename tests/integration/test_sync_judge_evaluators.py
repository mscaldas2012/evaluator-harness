from __future__ import annotations

from pathlib import Path

from evaluator_harness.evaluator_bindings import EvaluatorBindingStore, load_evaluator_bindings
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


def test_sync_judge_evaluators_partial_success_preserves_created_evaluator(tmp_path: Path) -> None:
    class FailingSecondCreateClient(LangfuseClient):
        def create_evaluator(self, payload):
            if self.evaluators:
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
