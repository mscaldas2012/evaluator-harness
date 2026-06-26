# Implementation Plan: Automatic Evaluator Calibration Support

**Branch**: `026-evaluator-calibration` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/026-evaluator-calibration/spec.md`

## Summary

Add an optional calibration workflow that captures review-selected run items, automated evaluator scores, and completed human annotation labels into machine-readable calibration artifacts, then summarizes disagreement and drift across snapshots. The design reuses existing Langfuse traces, scores, annotation queues, and stable review selection so calibration remains Langfuse-first and does not introduce a separate local review system.

## Technical Context

**Language/Version**: Python 3.12 project standard

**Primary Dependencies**: Typer CLI, Rich console rendering, pytest, existing Langfuse gateway abstractions, project config/data models, and report/export helpers

**Python Environment Management**: Use `uv` for environment management, dependency setup, lockfile management, and command execution. Prefer `uv sync` and `uv run ...`.

**Storage**: Filesystem artifacts under `reports/<project>/calibration/` plus existing Langfuse traces, scores, and annotation queue records as system of record

**Testing**: pytest (unit, integration, and CLI contract coverage)

**Target Platform**: Local CLI execution on developer machines

**Project Type**: Python CLI/library package

**Performance Goals**: Calibration snapshot generation should remain in the same operational class as existing run export/reporting paths for the same run size, with no observable slowdown beyond the additional score and annotation lookups required for calibration output

**Constraints**: Keep Langfuse as the system of record; preserve existing run execution behavior; reuse deterministic review selection for stable calibration cohorts; avoid introducing a new local database or review subsystem; keep calibration optional and command-driven

**Scale/Scope**: Run-scoped calibration for existing projects and datasets, typically tens to hundreds of reviewed items per run, with summaries aggregated by evaluator dimension and project version

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. Calibration reads Langfuse traces, scores, and annotation queues instead of introducing a local scoring or review store.
- **Thin harness scope**: PASS. The feature stays inside the existing Python CLI and file-based reporting model.
- **Dataset simplicity**: PASS. Existing CSV dataset identity and trace-to-item linkage remain unchanged.
- **Reproducibility metadata**: PASS. Calibration artifacts preserve project, dataset, run, prompt, evaluator, and score-source context for later comparison.
- **Baseline-centric workflow**: PASS. Calibration supports baseline and candidate runs but does not replace baseline-first comparison semantics.
- **Minimal local state**: PASS. The only new local outputs are generated calibration artifacts and summaries.
- **Human review awareness**: PASS. Human Annotation Queue workflows remain the review source, and sampled/disputed items stay Langfuse-native.
- **Local-first execution**: PASS. The feature remains runnable locally through the existing CLI and `uv run` workflow.

## Project Structure

### Documentation (this feature)

```text
specs/026-evaluator-calibration/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── calibration-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
├── cli.py
├── cli_presenters.py
├── runner.py
├── review_selection.py
├── review_routing.py
├── exports.py
├── run_exports.py
├── langfuse_default_gateway.py
├── langfuse_gateways.py
└── calibration.py            # new calibration capture and summary helpers

tests/
├── unit/
│   ├── test_review_selection.py
│   └── test_calibration.py   # new calibration metric and artifact tests
├── integration/
│   └── test_calibration_capture.py  # new end-to-end calibration flow coverage
└── contract/
    └── test_cli_calibration.py      # new CLI surface regression coverage
```

**Structure Decision**: Keep the existing single-project Python CLI layout and add one focused calibration module plus matching tests and docs. Calibration is implemented as an optional reporting workflow layered on top of existing run/review infrastructure, not as a new service or store.

## Complexity Tracking

No constitution violations are introduced.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Phase 0: Research Summary

See [research.md](research.md). Decisions:

- Use existing Langfuse traces, scores, and annotation queues as the source data for calibration capture.
- Reuse the deterministic stable review cohort so calibration samples stay comparable across compatible runs.
- Represent calibration output as filesystem artifacts, not a local database or dashboard.
- Surface calibration through CLI commands that capture snapshots and generate summaries, rather than coupling it to baseline/candidate execution.
- Treat missing human labels as partial calibration data, not as a fatal run error.

## Phase 1: Design Summary

See [data-model.md](data-model.md), [contracts/calibration-cli.md](contracts/calibration-cli.md), and [quickstart.md](quickstart.md).

The design defines:

- calibration snapshot, record, summary, and drift entities;
- the CLI workflow for capturing and summarizing calibration data;
- the file-based artifact layout for machine-readable calibration outputs;
- deterministic pairing and aggregation rules for paired and unpaired records;
- validation and warning behavior for incomplete score or annotation retrieval.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Calibration remains a consumer of Langfuse-native records and queues.
- **Thin harness scope**: PASS. The feature adds only one small local module and a reporting workflow.
- **Dataset simplicity**: PASS. No dataset schema changes are needed.
- **Reproducibility metadata**: PASS. Snapshot and summary outputs preserve the identifiers needed to reproduce calibration analysis.
- **Baseline-centric workflow**: PASS. Baseline and candidate runs remain the source runs, with calibration layered on top.
- **Minimal local state**: PASS. Only generated artifacts are added locally.
- **Human review awareness**: PASS. Human annotation data remains the calibration source for disputed or sampled items.
- **Local-first execution**: PASS. The workflow is fully supported by local CLI execution.

## Verification Plan

1. Run calibration unit tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_calibration.py -vv`
2. Run review-selection regression coverage to ensure sampling and routing remain stable:
   `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_review_selection.py tests/integration/test_select_review.py tests/integration/test_select_review_managed_queue.py -vv`
3. Run calibration CLI contract coverage:
   `uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_calibration.py -vv`
4. Run the broad non-live suite before merge:
   `uv run pytest --no-cov -p no:cacheprovider -m "not live"`
5. Refresh the knowledge graph after implementation:
   `graphify update .`
