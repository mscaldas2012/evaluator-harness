from __future__ import annotations

import ast
import inspect
from io import StringIO
from types import SimpleNamespace

from rich.console import Console

from evaluator_harness import cli
from evaluator_harness.cli_presenters import (
    ComparisonReportPresentationResult,
    RunPresentationResult,
    present_campaign_result,
    present_comparison_report_result,
    present_export_result,
    present_judge_setup_result,
    present_render_judge_prompts_result,
    present_run_result,
    present_select_review_result,
    present_sync_all_result,
    present_sync_annotation_queue_result,
    present_sync_dataset_result,
    present_sync_prompts_result,
    present_sync_score_configs_result,
    present_validate_result,
)


def _capture_console() -> tuple[Console, StringIO]:
    stream = StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None, width=200)
    return console, stream


def _text_for(presenter, result) -> str:
    console, stream = _capture_console()
    presenter(result, console)
    return stream.getvalue().replace("\\", "/")


def test_present_validate_result_outputs_expected_lines() -> None:
    result = SimpleNamespace(
        project_name="rewrite-quality",
        project_version="v1",
        dataset_kind="local_csv",
        item_count=2,
        baseline_name="baseline-1",
        candidate_names=["cand-a", "cand-b"],
        evaluator_names=["clarity"],
        evaluator_targets=["observation"],
        score_targets=["quality"],
        judge_setup_status="configured",
        judge_default="gpt-4.1-mini",
        binding_path="configs/langfuse/evaluator_bindings/rewrite.yaml",
    )

    output = _text_for(present_validate_result, result)

    assert "project: rewrite-quality/v1" in output
    assert "dataset: local_csv (2 items)" in output
    assert "candidates: cand-a, cand-b" in output
    assert "judge-default: gpt-4.1-mini" in output


def test_present_sync_dataset_and_score_configs_output() -> None:
    dataset_result = SimpleNamespace(
        name="rewrite-quality/v1",
        version="v1",
        compatibility_version="v1",
        item_count=2,
        rejected_count=0,
        status="resolved",
    )
    output = _text_for(present_sync_dataset_result, dataset_result)
    assert "dataset: rewrite-quality/v1" in output
    assert "status: resolved" in output

    score_results = [
        SimpleNamespace(
            name="eh_quality",
            status="created",
            ownership="managed",
            score_config_id="score_123",
        )
    ]
    output = _text_for(present_sync_score_configs_result, score_results)
    assert "score-config: eh_quality" in output
    assert "id: score_123" in output


def test_present_sync_prompts_result_outputs_items() -> None:
    item = SimpleNamespace(
        artifact=SimpleNamespace(
            artifact_type="task_prompt",
            artifact_name="rewrite",
            artifact_version="v1",
            prompt_shape="text",
        ),
        managed_name="rewrite_prompt",
        status="created",
        langfuse_prompt_version="17",
        message="created",
        remediation=None,
    )
    result = SimpleNamespace(
        project="rewrite-quality",
        project_version="v1",
        mode="sync",
        binding_path="configs/langfuse/prompt_bindings/rewrite.yaml",
        total_count=1,
        created_count=1,
        reused_count=0,
        conflict_count=0,
        failed_count=0,
        items=[item],
    )

    output = _text_for(present_sync_prompts_result, result)

    assert "project: rewrite-quality/v1" in output
    assert "prompt: task_prompt/rewrite/v1" in output
    assert "managed-name: rewrite_prompt" in output


def test_present_sync_all_result_outputs_summary() -> None:
    result = SimpleNamespace(
        dataset=SimpleNamespace(name="rewrite/v1", status="resolved", item_count=2),
        prompts=SimpleNamespace(
            mode="sync",
            created_count=1,
            reused_count=0,
            conflict_count=0,
            failed_count=0,
        ),
        score_configs=[SimpleNamespace(name="quality", status="created")],
        judge_evaluators=SimpleNamespace(mode="sync", overall_status="success"),
        annotation_queue=SimpleNamespace(
            status="ready", queue_id="queue_1", message="ok"
        ),
    )

    output = _text_for(present_sync_all_result, result)

    assert "Report" in output
    assert "dataset: rewrite/v1 (resolved, 2 items)" in output
    assert "score-configs: quality=created" in output
    assert "annotation-queue: ready (queue_1)" in output


def test_present_run_result_outputs_report_and_warning_dedupe() -> None:
    run_result = SimpleNamespace(
        run_id="run_1",
        run_type="baseline",
        completed_count=2,
        failed_count=0,
        baseline_reference=SimpleNamespace(baseline_run_id="base_1"),
        model_output_targeting_status="applied",
        model_output_targeting_message="targeted",
        langfuse_status="partial",
        langfuse_warnings=("warn-a",),
        review_selection=SimpleNamespace(
            selected_count=2,
            queued_count=1,
            skipped_duplicate_count=0,
        ),
    )
    report = SimpleNamespace(
        output_path="reports/run.csv",
        row_count=2,
        warnings=("warn-a", "warn-b"),
    )
    result = RunPresentationResult(
        run_result=run_result,
        skip_sync=True,
        skip_human_review=False,
        report=report,
    )

    output = _text_for(present_run_result, result)

    assert "run: run_1" in output
    assert "sync: skipped" in output
    assert "baseline-reference: base_1" in output
    assert "warning: warn-a" in output
    assert output.count("warning: warn-a") == 1
    assert "warning: warn-b" in output
    assert "report: reports/run.csv" in output


def test_present_campaign_result_outputs_completed_and_skipped() -> None:
    result = SimpleNamespace(
        baseline_run=SimpleNamespace(run_id="baseline_1"),
        candidate_runs=[
            SimpleNamespace(
                candidate_name="cand-a",
                run_result=SimpleNamespace(run_id="cand_run_1"),
                status="completed",
                message=None,
            )
        ],
        skipped_candidates=[
            SimpleNamespace(candidate_name="cand-b", reason="incompatible")
        ],
        csv_reports=[SimpleNamespace(output_path="reports/campaign.csv")],
        final_reports=[
            SimpleNamespace(format="excel", output_path="reports/final.xlsx")
        ],
        excel_report=None,
        warnings=("campaign-warning",),
    )

    output = _text_for(present_campaign_result, result)

    assert "campaign: completed" in output
    assert "baseline: baseline_1" in output
    assert "candidate: cand-a cand_run_1" in output
    assert "skipped: cand-b incompatible" in output
    assert "excel-report: reports/final.xlsx" in output


def test_present_select_review_and_export_outputs() -> None:
    review_result = SimpleNamespace(
        selected_count=4,
        queued_count=2,
        queue_id="queue_1",
        queue_ownership="managed",
        skipped_duplicate_count=1,
        reasons={"top_score": 2, "random": 2},
    )
    output = _text_for(present_select_review_result, review_result)
    assert "selected: 4" in output
    assert "queue-ownership: managed" in output
    assert "reasons: random=2, top_score=2" in output

    export_result = SimpleNamespace(
        output_path="reports/export.csv",
        row_count=12,
        warnings=("w1",),
    )
    output = _text_for(present_export_result, export_result)
    assert "export: reports/export.csv" in output
    assert "rows: 12" in output
    assert "warning-count: 1" in output


def test_present_annotation_queue_and_render_judge_outputs() -> None:
    queue_result = SimpleNamespace(
        queue_id="queue_1",
        queue_name="Queue Name",
        status="ready",
        ownership="managed",
        score_config_ids=["score-1", "score-2"],
        reference_path="refs/queue.json",
        manual_fallback_reason=None,
        message="ok",
    )
    output = _text_for(present_sync_annotation_queue_result, queue_result)
    assert "queue: queue_1" in output
    assert "score-configs: score-1, score-2" in output

    render_result = [
        SimpleNamespace(
            evaluator_name="clarity",
            evaluator_version="v1",
            target="observation",
            score="quality",
            shared_with_human_annotation_queue=True,
            score_sources={"llm_judge": "quality"},
            filters=SimpleNamespace(
                project="rewrite-quality",
                project_version="v1",
                evaluator_set_id="set_1",
                run_types=[SimpleNamespace(value="baseline")],
                observation_role="model_output",
                observation_name=None,
            ),
            prompt_path="prompts/judge.md",
        )
    ]
    output = _text_for(present_render_judge_prompts_result, render_result)
    assert "evaluator: clarity/v1" in output
    assert "run_type: baseline" in output
    assert "prompt: prompts/judge.md" in output


def test_present_judge_setup_result_outputs_nested_fields() -> None:
    evaluator = SimpleNamespace(
        evaluator_name="clarity",
        evaluator_version="v1",
        source_type="custom",
        target="observation",
        operation=SimpleNamespace(value="upsert"),
        managed_display_name="Clarity",
        score_target=SimpleNamespace(name="quality", score_config_id="score_1"),
        judge_model="gpt-4.1-mini",
        llm_connection="openai",
        activation_state="active",
        sampling_percent=100,
        backfill_status=SimpleNamespace(value="disabled"),
        binding_status="bound",
        filters={"project": "rewrite-quality"},
        variables={"input": "{{input}}"},
        remediation=None,
    )
    result = SimpleNamespace(
        project="rewrite-quality",
        project_version="v1",
        mode="sync",
        overall_status="success",
        binding_path="configs/langfuse/evaluator_bindings/rewrite.yaml",
        evaluators=[evaluator],
    )

    output = _text_for(present_judge_setup_result, result)

    assert "project: rewrite-quality/v1" in output
    assert "evaluator: clarity/v1" in output
    assert "score-config: quality (score_1)" in output
    assert "variables:" in output


def test_present_comparison_report_result_outputs_baseline_and_warnings() -> None:
    outputs = [
        SimpleNamespace(
            format="excel",
            output_path="reports/final.xlsx",
            report_count=2,
            row_count=5,
            score_observation_count=9,
            warnings=("warn-1",),
        )
    ]
    result = ComparisonReportPresentationResult(outputs=outputs, baseline="baseline_1")

    output = _text_for(present_comparison_report_result, result)

    assert "excel-report: reports/final.xlsx" in output
    assert "baseline: baseline_1" in output
    assert "score-observations: 9" in output
    assert "warning: warn-1" in output


def test_presenter_signatures_use_result_console_contract() -> None:
    presenter_names = [
        "present_validate_result",
        "present_sync_dataset_result",
        "present_sync_score_configs_result",
        "present_sync_prompts_result",
        "present_sync_all_result",
        "present_sync_annotation_queue_result",
        "present_render_judge_prompts_result",
        "present_export_evaluator_setup_result",
        "present_judge_setup_result",
        "present_run_result",
        "present_select_review_result",
        "present_export_result",
        "present_campaign_result",
        "present_comparison_report_result",
    ]

    module = inspect.getmodule(present_validate_result)
    assert module is not None

    for name in presenter_names:
        fn = getattr(module, name)
        signature = inspect.signature(fn)
        assert list(signature.parameters.keys()) == ["result", "console"]


def test_cli_command_functions_do_not_print_results_inline() -> None:
    source = inspect.getsource(cli)
    tree = ast.parse(source)
    command_functions = {
        "validate",
        "sync_dataset",
        "sync_score_configs",
        "sync_prompts",
        "sync_all",
        "sync_annotation_queue",
        "render_judge_prompts",
        "export_evaluator_setup",
        "sync_judge_evaluators",
        "run",
        "select_review",
        "export",
        "campaign",
        "comparison_report",
        "excel_report",
    }

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name not in command_functions:
            continue

        offenders: list[int] = []

        class _Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, _node):
                # Skip nested helper functions; only inspect top-level command body.
                return

            def visit_Call(self, call):
                func = call.func
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "console"
                    and func.attr == "print"
                ):
                    offenders.append(call.lineno)
                self.generic_visit(call)

        for stmt in node.body:
            _Visitor().visit(stmt)

        assert not offenders, f"{node.name} has inline console.print at {offenders}"
