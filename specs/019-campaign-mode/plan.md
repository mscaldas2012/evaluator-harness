# Implementation Plan: Campaign Mode

**Branch**: `019-campaign-mode` | **Date**: 2026-06-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/019-campaign-mode/spec.md`

## Summary

Add a campaign execution path that runs one fresh baseline, runs all explicitly campaign-included candidates against that baseline, exports CSV reports under the project report folder, and creates the existing Excel comparison workbook from those reports. The implementation will extend the existing local Python CLI and `ExperimentRunner` orchestration, add a candidate-level campaign exclusion flag to project YAML parsing, and reuse current baseline, candidate, sync, human review, CSV export, and Excel report behavior.

## Technical Context

**Language/Version**: Python 3.14 in the current `uv` environment.

**Primary Dependencies**: Typer CLI, Pydantic project config models, PyYAML config loading, Langfuse client abstractions, existing provider adapters, existing CSV export and Excel report modules.

**Python Environment Management**: Use `uv` for environment management, dependency setup, lockfile management, and command execution. Prefer `uv sync` and `uv run ...`.

**Storage**: Local YAML project files, local CSV/Excel reports under `reports/<project-name>/`, existing local prompt/dataset files, and Langfuse as the system of record for traces/runs/scores.

**Testing**: Pytest unit, contract, and integration tests through `uv run pytest`.

**Target Platform**: Local developer workstation; Excel workbook creation still requires Windows with Microsoft Excel for native PivotTables/charts.

**Project Type**: Local Python CLI evaluation harness.

**Performance Goals**: Campaign overhead should be limited to orchestration work; model/provider runtime remains dominated by the existing baseline and candidate run paths.

**Constraints**: Preserve existing baseline compatibility checks, model-output targeting metadata, automatic report export behavior, optional human-review selection, and `--skip-sync` semantics.

**Scale/Scope**: One project campaign runs one baseline plus all candidates that do not set `exclude-from-campaign: true`. No parallel execution, scheduler, resume engine, or campaign persistence database in this feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. Campaign mode reuses existing Langfuse-backed baseline and candidate runs; it does not introduce local scoring or comparison logic beyond the already approved Excel report export artifact.
- **Thin harness scope**: PASS. The feature remains a local CLI workflow and runner method.
- **Dataset simplicity**: PASS. Campaign mode uses the project's existing runnable dataset without changing dataset shape.
- **Reproducibility metadata**: PASS. Campaign runs reuse existing run methods that log project, dataset, prompt, evaluator, model, parameter, baseline reference, latency, token, timestamp, and run metadata.
- **Baseline-centric workflow**: PASS. Campaign mode creates a fresh baseline before candidates and passes that baseline run ID into each candidate run.
- **Minimal local state**: PASS. Local state remains generated report files; Langfuse remains the system of record.
- **Human review awareness**: PASS. Campaign mode preserves the existing human-review selection behavior and skip option.
- **Local-first execution**: PASS. Campaign mode will run through `uv run python run_experiment.py`.

## Project Structure

### Documentation (this feature)

```text
specs/019-campaign-mode/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── campaign-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
├── cli.py                 # add campaign CLI target/options and summary output
├── config.py              # add candidate campaign exclusion setting
├── runner.py              # add campaign orchestration and result objects
└── excel_reports.py       # reused for final workbook creation

tests/
├── contract/
│   └── test_cli_campaign.py
├── integration/
│   └── test_campaign.py
└── unit/
    ├── test_config.py
    └── test_campaign.py
```

**Structure Decision**: Extend the existing single-project CLI harness. Campaign orchestration belongs with `ExperimentRunner` because it composes existing run/export/report behavior. Configuration support belongs in `config.py` because the new flag is part of each candidate model config.

## Complexity Tracking

No constitution violations.
