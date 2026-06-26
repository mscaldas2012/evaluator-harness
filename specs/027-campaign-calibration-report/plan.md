# Implementation Plan: Campaign Calibration Report

**Branch**: `027-campaign-calibration-report` | **Date**: 2026-06-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/027-campaign-calibration-report/spec.md`

## Summary

Add a post-campaign CLI workflow that starts from a baseline run ID, resolves the campaign's baseline and candidate run IDs, runs the existing single-run calibration capture and summary logic for each run, and writes one static HTML campaign calibration report. The implementation will keep Langfuse as the system of record for traces, scores, and human annotations, while adding only local manifest/report artifacts needed to resume the workflow after the human annotation delay.

## Technical Context

**Language/Version**: Python 3.11+ (project standard)

**Primary Dependencies**:
- `src/evaluator_harness/runner.py` for `ExperimentRunner.calibration_capture()`, `ExperimentRunner.calibration_summary()`, and campaign orchestration entry points
- `src/evaluator_harness/calibration.py` for row-level snapshots and evaluator summary metric definitions
- `src/evaluator_harness/campaigns.py` for campaign result/run reference shapes
- `src/evaluator_harness/comparison_reports.py` and `src/evaluator_harness/html_reports.py` for fallback campaign run discovery and static HTML rendering conventions
- `src/evaluator_harness/cli.py` and `src/evaluator_harness/cli_presenters.py` for Typer command and user-facing output

**Python Environment Management**: Use `uv sync` and `uv run ...` per project constitution

**Storage**: Local filesystem artifacts under the project reports directory, plus Langfuse as the trace/score/human annotation system of record

**Testing**: pytest with existing unit and contract test structure

**Target Platform**: Local CLI execution on developer machines

**Project Type**: Python library/CLI (thin harness)

**Performance Goals**: Process campaign runs sequentially with no material overhead beyond existing per-run calibration capture and summary; HTML report generation should be bounded by local snapshot/summary artifact size

**Constraints**:
- Must not rerun generation or automated evaluator scoring
- Must treat completed Langfuse Human Annotation Queue items as human labels
- Must use the provided baseline run ID as the campaign anchor
- Must discover candidate runs from a persisted campaign manifest first, then from comparison/export artifacts
- Must overwrite snapshots, summaries, and campaign HTML report from the latest available Langfuse state on rerun
- Must support baseline-only campaigns

**Scale/Scope**: One new post-campaign CLI command, one campaign calibration orchestration module, one optional campaign manifest writer/reader, one HTML report renderer, and focused tests for run discovery, orchestration, reporting, and CLI output

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. Langfuse remains the source for traces, scores, and Human Annotation Queue labels. Local artifacts only resume/report the workflow after human review delay.
- **Thin harness scope**: PASS. Design is a local Typer CLI command plus plain Python orchestration; no services, workers, APIs, databases, or schedulers.
- **Dataset simplicity**: PASS. Dataset format is unchanged; calibration preserves item identities from existing campaign outputs.
- **Reproducibility metadata**: PASS. Existing calibration records preserve run IDs, evaluator versions, prompt versions, score sources, dataset identity, and item/trace IDs; campaign report aggregates those artifacts.
- **Baseline-centric workflow**: PASS. The baseline run ID is the required anchor and is always included before candidate runs.
- **Minimal local state**: PASS. New local state is limited to a campaign manifest and generated calibration/report files.
- **Human review awareness**: PASS. The feature is explicitly about completed human annotation queue items and visible missing-annotation warnings.
- **Local-first execution**: PASS. Workflow runs through `uv run python run_experiment.py campaign-calibration-report ...`.

**Constitutional Status**: **PASS** - The feature composes existing local CLI behavior and Langfuse-backed calibration without expanding the harness into a service or custom evaluation platform.

## Project Structure

### Documentation (this feature)

```text
specs/027-campaign-calibration-report/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- campaign-calibration-report.md
`-- tasks.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
|-- calibration.py                    # REUSE: snapshot and summary metric definitions
|-- campaign_calibration.py           # NEW: campaign run discovery, orchestration, result model
|-- campaign_calibration_reports.py   # NEW: campaign calibration HTML payload/rendering
|-- campaigns.py                      # UPDATE: optionally write campaign manifest after campaign run
|-- cli.py                            # UPDATE: add campaign-calibration-report command
|-- cli_presenters.py                 # UPDATE: present campaign calibration results
|-- comparison_reports.py             # REUSE: fallback discovery from existing CSV comparison inputs
`-- runner.py                         # UPDATE: add runner method delegating to campaign calibration module

tests/
|-- contract/
|   `-- test_cli_campaign_calibration_report.py
|-- unit/
|   |-- test_campaign_calibration.py
|   `-- test_campaign_calibration_reports.py
`-- integration/
    `-- test_campaign_calibration_flow.py
```

**Structure Decision**: Keep the feature in the existing single-package CLI structure. Add narrow modules for campaign-level calibration orchestration and report rendering, while reusing single-run calibration functions and existing comparison report discovery where possible.

## Complexity Tracking

No constitution violations.

---

## Phase 0: Research & Resolution

**See**: [research.md](research.md)

Key decisions:
- Use `--baseline <baseline-run-id>` as the required user anchor.
- Resolve run IDs from a campaign manifest first, then fallback comparison/export artifacts.
- Add a manifest because current campaign mode does not persist a first-class campaign ID or durable campaign run list.
- Compose existing single-run calibration capture and summary logic instead of duplicating pairing logic.
- Exit successfully for human-review incompleteness with warnings, but fail for technical blockers that prevent usable artifacts.

---

## Phase 1: Design & Contracts

### Data Model

**See**: [data-model.md](data-model.md)

Key entities:
- `CampaignManifest`
- `CampaignRunReference`
- `CampaignCalibrationRun`
- `CampaignRunCalibrationResult`
- `CampaignCalibrationReportPayload`

### CLI Contract

**See**: [contracts/campaign-calibration-report.md](contracts/campaign-calibration-report.md)

The public interface is a new local CLI command:

```text
eval campaign-calibration-report --project <project> --baseline <baseline-run-id>
```

### Quickstart

**See**: [quickstart.md](quickstart.md)

The quickstart covers campaign execution, delayed human annotation, campaign calibration capture/summary, and opening the generated HTML report.

### Agent Context

`AGENTS.md` now points to this feature plan for current Speckit context.

---

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Report generation consumes Langfuse-derived calibration artifacts and does not replace Langfuse review.
- **Thin harness scope**: PASS. Implementation remains local Python modules and Typer commands.
- **Dataset simplicity**: PASS. No dataset schema change.
- **Reproducibility metadata**: PASS. Manifest and report preserve run IDs and existing snapshot metadata.
- **Baseline-centric workflow**: PASS. Baseline run ID is the required anchor and artifact naming root.
- **Minimal local state**: PASS. Manifest is a plain local resumability artifact, not a database.
- **Human review awareness**: PASS. Warnings and partial coverage are first-class outputs.
- **Local-first execution**: PASS. Uses existing `uv run` CLI workflow.

**Post-design status**: **PASS**.

## Next Steps

1. Run `/speckit-tasks` to generate implementation tasks.
2. Implement manifest/run discovery first, then campaign calibration orchestration, then HTML reporting.
3. Verify with focused unit/contract tests and a local dry-run flow using existing calibration artifacts.
