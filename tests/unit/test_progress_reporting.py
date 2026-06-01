from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from evaluator_harness.config import load_project_config
from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


class RecordingProgress:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, int | None]] = []

    @contextmanager
    def task(self, description: str, *, total: int | None = None):
        self.events.append(("start", description, total))
        task = RecordingTask(self.events, description)
        try:
            yield task
        finally:
            self.events.append(("end", description, total))


class RecordingTask:
    def __init__(
        self,
        events: list[tuple[str, str, int | None]],
        description: str,
    ) -> None:
        self.events = events
        self.description = description

    def advance(self, amount: int = 1) -> None:
        self.events.append(("advance", self.description, amount))


def test_run_baseline_reports_progress_for_dataset_items() -> None:
    progress = RecordingProgress()
    runner = ExperimentRunner(
        langfuse_client=LangfuseClient(),
        provider_factory=lambda _config: FakeModelProvider(),
        progress=progress,
    )

    runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")

    assert ("start", "Running baseline items", 2) in progress.events
    assert progress.events.count(("advance", "Running baseline items", 1)) == 2
    assert ("end", "Running baseline items", 2) in progress.events


def test_score_config_sync_reports_progress_for_evaluators() -> None:
    progress = RecordingProgress()
    config = load_project_config(Path("configs/projects/rewrite_quality.yaml"))

    LangfuseClient().sync_score_configs(config, progress=progress)

    assert ("start", "Syncing score configs", 1) in progress.events
    assert progress.events.count(("advance", "Syncing score configs", 1)) == 1
    assert ("end", "Syncing score configs", 1) in progress.events


def test_dataset_sync_reports_progress_for_local_items() -> None:
    progress = RecordingProgress()
    config = load_project_config(Path("configs/projects/rewrite_quality.yaml"))
    items = ExperimentRunner(langfuse_client=LangfuseClient())._validate_dataset(config)

    LangfuseClient().sync_dataset(config.dataset, items, progress=progress)

    assert ("start", "Syncing dataset items", 2) in progress.events
    assert progress.events.count(("advance", "Syncing dataset items", 1)) == 2
    assert ("end", "Syncing dataset items", 2) in progress.events


def test_select_review_reports_progress_for_live_steps() -> None:
    progress = RecordingProgress()
    client = LangfuseClient()
    client.traces.extend(
        [
            {
                "trace_id": "trace-1",
                "run_id": "candidate-1",
                "input": "Source 1",
                "output": "Candidate 1",
                "metadata": {
                    "run_id": "candidate-1",
                    "dataset_item_id": "1",
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                    "baseline_reference": {"baseline_run_id": "baseline-1"},
                },
            },
            {
                "trace_id": "trace-baseline-1",
                "run_id": "baseline-1",
                "output": "Baseline 1",
                "metadata": {"dataset_item_id": "1"},
            },
        ]
    )
    runner = ExperimentRunner(langfuse_client=client, progress=progress)

    runner.select_review(Path("configs/projects/rewrite_quality.yaml"), "candidate-1")

    assert ("start", "Syncing score configs", 1) in progress.events
    assert ("start", "Resolving annotation queue", None) in progress.events
    assert ("start", "Fetching review traces", None) in progress.events
    assert ("start", "Checking existing review items", None) in progress.events
    assert ("start", "Building review payloads", 1) in progress.events
    assert ("advance", "Building review payloads", 1) in progress.events
    assert ("start", "Routing review items", None) in progress.events


def test_judge_evaluator_apply_reports_progress_for_plans(tmp_path: Path) -> None:
    progress = RecordingProgress()
    client = LangfuseClient()
    runner = ExperimentRunner(langfuse_client=client, progress=progress)
    project = tmp_path / "project.yaml"
    binding = tmp_path / "bindings.yaml"
    text = Path("tests/fixtures/projects/valid_rewrite_quality.yaml").read_text(
        encoding="utf-8"
    )
    project.write_text(
        text.replace(
            "  binding_path: configs/langfuse/evaluator_bindings/rewrite-quality.yaml",
            f"  binding_path: {binding.as_posix()}",
        ),
        encoding="utf-8",
    )

    runner.sync_judge_evaluators(project)

    assert ("start", "Applying judge evaluators", 1) in progress.events
    assert progress.events.count(("advance", "Applying judge evaluators", 1)) == 1
    assert ("end", "Applying judge evaluators", 1) in progress.events
