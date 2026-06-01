from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from evaluator_harness.annotation_queues import (
    AnnotationQueueReference,
    AnnotationQueueReferenceStore,
    queue_review_policy_version,
    sync_annotation_queue,
)
from evaluator_harness.config import load_project_config, validate_project_config
from evaluator_harness.evaluator_bindings import load_evaluator_bindings
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_client import LangfuseClient, ScoreConfigSyncResult


@dataclass(frozen=True)
class QueueResetPlan:
    project_path: Path
    project_name: str
    project_version: str
    review_policy_version: str
    reference_path: Path
    existing_reference: AnnotationQueueReference | None
    score_config_names_by_id: dict[str, str]


def build_reset_plan(
    project_path: Path,
    *,
    reference_dir: Path | str | None = None,
) -> QueueResetPlan:
    config = load_project_config(project_path)
    validate_project_config(config)
    if not config.human_review.enabled:
        raise ConfigError("human review is disabled for this project")
    if config.human_review.queue_ownership != "managed_by_harness":
        raise ConfigError("queue reset only applies to managed_by_harness queues")

    store = AnnotationQueueReferenceStore(reference_dir) if reference_dir else AnnotationQueueReferenceStore()
    review_policy_version = queue_review_policy_version(config)
    reference_path = store.path_for(
        config.project.name,
        config.project.version,
        review_policy_version,
    )
    existing_reference = store.load(
        config.project.name,
        config.project.version,
        review_policy_version,
    )
    names_by_id = score_config_names_by_id(config)
    if existing_reference is not None:
        names_by_id.update(
            score_config_names_by_reference_order(config, existing_reference.score_config_ids)
        )
    return QueueResetPlan(
        project_path=project_path,
        project_name=config.project.name,
        project_version=config.project.version,
        review_policy_version=review_policy_version,
        reference_path=reference_path,
        existing_reference=existing_reference,
        score_config_names_by_id=names_by_id,
    )


def print_plan(plan: QueueResetPlan) -> None:
    print(f"project: {plan.project_name}/{plan.project_version}")
    print(f"review-policy: {plan.review_policy_version}")
    print(f"reference: {plan.reference_path}")
    if plan.existing_reference is None:
        print("current-reference: none")
        return
    print(f"current-queue-id: {plan.existing_reference.queue_id}")
    print(f"current-queue-name: {plan.existing_reference.queue_name}")
    print(
        "current-score-configs: "
        f"{format_score_config_ids(plan.existing_reference.score_config_ids, plan.score_config_names_by_id)}"
    )


def format_score_config_ids(score_config_ids: list[str], names_by_id: dict[str, str]) -> str:
    if not score_config_ids:
        return "none"
    return ", ".join(
        f"{names_by_id[score_config_id]} ({score_config_id})"
        if score_config_id in names_by_id
        else score_config_id
        for score_config_id in score_config_ids
    )


def score_config_names_by_id(config: object) -> dict[str, str]:
    names_by_id = {
        str(evaluator.score.langfuse_score_config_id): evaluator.score.name
        for evaluator in config.evaluators
        if evaluator.score.langfuse_score_config_id
    }
    binding_path = config.judge_setup.binding_path or (
        Path("configs/langfuse/evaluator_bindings") / f"{config.project.name}.yaml"
    )
    bindings = load_evaluator_bindings(binding_path)
    for binding in bindings.bindings:
        if (
            binding.project == config.project.name
            and binding.project_version == config.project.version
        ):
            names_by_id[binding.score_config_id] = binding.score_config_name
    return names_by_id


def score_config_names_by_reference_order(
    config: object,
    score_config_ids: list[str],
) -> dict[str, str]:
    if len(score_config_ids) != len(config.evaluators):
        return {}
    return {
        score_config_id: f"{config.project.score_config_prefix}{evaluator.score.name}"
        for score_config_id, evaluator in zip(score_config_ids, config.evaluators, strict=True)
    }


def confirm_remote_queue_deleted(plan: QueueResetPlan) -> bool:
    print("")
    print("Delete the existing Human Annotation Queue in Langfuse before continuing.")
    if plan.existing_reference is not None:
        print(f"Queue ID:   {plan.existing_reference.queue_id}")
        print(f"Queue name: {plan.existing_reference.queue_name}")
    print("")
    response = input("Type 'deleted' after the Langfuse queue is deleted, or anything else to abort: ")
    return response.strip().lower() == "deleted"


def delete_local_reference(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True


def reset_queue(
    project_path: Path,
    *,
    client: LangfuseClient | None = None,
    reference_dir: Path | str | None = None,
) -> tuple[list[ScoreConfigSyncResult], object]:
    config = load_project_config(project_path)
    validate_project_config(config)
    langfuse_client = client or LangfuseClient.from_env()
    store = AnnotationQueueReferenceStore(reference_dir) if reference_dir else AnnotationQueueReferenceStore()
    score_results = langfuse_client.sync_score_configs(config)
    queue_result = sync_annotation_queue(
        config,
        langfuse_client,
        score_results,
        store=store,
    )
    return score_results, queue_result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reset a managed annotation queue reference for one project after the "
            "existing Langfuse queue has been deleted manually."
        )
    )
    parser.add_argument("--project", required=True, help="Project YAML path.")
    parser.add_argument(
        "--reference-dir",
        default=None,
        help="Override local queue reference directory. Intended for tests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the reset plan without deleting the local reference or syncing Langfuse.",
    )
    args = parser.parse_args()

    project_path = Path(args.project)
    plan = build_reset_plan(
        project_path,
        reference_dir=Path(args.reference_dir) if args.reference_dir else None,
    )
    print_plan(plan)

    if args.dry_run:
        print("")
        print("Dry run only.")
        print("Would ask you to delete the existing queue in Langfuse.")
        print("Would delete the local queue reference if present.")
        print("Would sync score configs.")
        print("Would recreate or sync the managed annotation queue.")
        return 0

    if not confirm_remote_queue_deleted(plan):
        print("Aborted. No local files were changed and no Langfuse sync was run.")
        return 1

    deleted = delete_local_reference(plan.reference_path)
    print(f"deleted-local-reference: {str(deleted).lower()}")

    score_results, queue_result = reset_queue(
        project_path,
        reference_dir=Path(args.reference_dir) if args.reference_dir else None,
    )
    print(f"score-configs: {', '.join(result.name for result in score_results)}")
    print(f"queue: {getattr(queue_result, 'queue_id', None) or 'none'}")
    print(f"name: {getattr(queue_result, 'queue_name', None) or 'none'}")
    print(f"status: {getattr(queue_result, 'status', 'unknown')}")
    print(f"reference: {getattr(queue_result, 'reference_path', None) or plan.reference_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
