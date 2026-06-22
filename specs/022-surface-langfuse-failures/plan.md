# Implementation Plan: Surface Live Langfuse Failures

**Branch**: `022-surface-langfuse-failures` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/022-surface-langfuse-failures/spec.md`

## Summary

Surface live Langfuse partial persistence and lookup failures as structured run outcomes instead of silently converting failures into `None`, `{}`, or `[]`. The implementation will add a shared operation-outcome model and warning aggregation path, then apply it to baseline lookup, dataset run metadata lookup, dataset item lookup, dataset run item recording, trace lookup, and score retrieval while preserving expected not-found behavior and non-live workflows.

## Technical Context

**Language/Version**: Python 3.12 project using modern type annotations and Pydantic models.

**Primary Dependencies**: Langfuse SDK/API, Pydantic, Typer CLI, pytest, Ruff, Pyright, Radon, Vulture, Import Linter, existing `uv` managed environment.

**Python Environment Management**: Use `uv` for environment management, dependency setup, lockfile management, and command execution. Prefer `uv sync` and `uv run ...`.

**Storage**: Langfuse remains the system of record. Local state remains limited to filesystem datasets, prompts, project config, generated reports, and temporary run artifacts. New failure outcomes are carried in run/report results rather than persisted in a new store.

**Testing**: `pytest` for unit, contract, integration, and live tests. Quality verification uses focused Ruff/Pyright checks for touched Langfuse modules and the local quality report script where practical.

**Target Platform**: Local developer machines running the Python CLI; live validation requires configured Langfuse credentials and reachable external services.

**Project Type**: Local Python CLI/library package.

**Performance Goals**: Preserve current workflow throughput; warning aggregation must be bounded and avoid extra live calls beyond the existing lookup/persistence attempts.

**Constraints**: Keep CLI/project YAML compatibility, keep dry-run and non-live tests credential-free, redact secrets from surfaced diagnostics, distinguish expected not-found from live lookup failure, and avoid adding services, queues, or durable local stores.

**Scale/Scope**: Focused architectural hardening across live Langfuse lookup/persistence workflows. Expected touch points include `langfuse_records.py`, `langfuse_baselines.py`, `langfuse_dataset.py`, `langfuse_traces.py`, `langfuse_scores.py`, `langfuse_default_gateway.py`, `runner.py`, `exports.py`, CLI output, and relevant tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature improves confidence in Langfuse-backed traces, scores, baselines, dataset links, and review handles rather than replacing Langfuse.
- **Thin harness scope**: PASS. The design remains a local Python CLI/library change with explicit records and warning propagation. No services or framework changes are introduced.
- **Dataset simplicity**: PASS. Dataset shape remains unchanged and CSV with `input` stays supported.
- **Reproducibility metadata**: PASS. The feature increases visibility when reproducibility metadata cannot be persisted or confirmed in Langfuse.
- **Baseline-centric workflow**: PASS. Baseline lookup remains central and will now distinguish absent compatible baselines from failed live lookup.
- **Minimal local state**: PASS. No new durable local state is introduced; outcomes are carried in command/report results.
- **Human review awareness**: PASS. Annotation/review linkage warnings remain visible so humans can inspect incomplete Langfuse evidence.
- **Local-first execution**: PASS. Verification uses local `uv run ...` commands.

## Project Structure

### Documentation (this feature)

```text
specs/022-surface-langfuse-failures/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- langfuse-failure-surface.md
|-- checklists/
|   `-- requirements.md
`-- tasks.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
|-- langfuse_records.py          # shared operation outcome and warning records
|-- langfuse_baselines.py        # baseline lookup outcome classification
|-- langfuse_dataset.py          # dataset item/run item persistence outcomes
|-- langfuse_traces.py           # trace lookup outcome classification
|-- langfuse_scores.py           # score lookup outcome classification
|-- langfuse_default_gateway.py  # gateway result/warning aggregation surface
|-- langfuse_gateways.py         # protocol updates for outcome-aware methods
|-- runner.py                    # run summary and warning propagation
|-- exports.py                   # export warning propagation where applicable
`-- cli.py                       # user-facing warning/status output

tests/
|-- unit/
|   |-- test_langfuse_baselines.py
|   |-- test_langfuse_dataset_sync.py
|   |-- test_langfuse_traces.py
|   |-- test_langfuse_scores.py
|   |-- test_langfuse_gateway_warnings.py
|   `-- test_exports.py
|-- integration/
|   |-- test_run_baseline.py
|   |-- test_run_candidate.py
|   `-- test_langfuse_failure_surface.py
|-- contract/
|   |-- test_cli_run_baseline.py
|   |-- test_cli_run_candidate.py
|   `-- test_cli_export.py
`-- integration/live/
    `-- existing live smoke tests
```

**Structure Decision**: Keep the existing Langfuse owner-module architecture from TD-GRAPH-001. Add shared typed outcome records and warning aggregation without creating a new subsystem.

## Complexity Tracking

No constitution violations are introduced.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Phase 0: Research Summary

See [research.md](research.md). Decisions:

- Use explicit operation outcomes for live lookup/persistence calls instead of sentinel-only `None`, `{}`, or `[]`.
- Preserve expected not-found as a first-class non-error outcome.
- Aggregate warnings at the gateway/run-result boundary so CLI, exports, and tests see consistent messages.
- Treat missing required live identities as workflow-blocking failures only when downstream output would otherwise be misleading.
- Reuse existing secret-redaction helpers for all surfaced diagnostics.

## Phase 1: Design Summary

See [data-model.md](data-model.md) and [contracts/langfuse-failure-surface.md](contracts/langfuse-failure-surface.md).

The design defines:

- `LangfuseOperationOutcome` for success, expected not-found, partial success, and failure;
- `LangfuseWarning` for user-facing diagnostics with redacted detail;
- warning aggregation on run/export summaries;
- outcome-aware behavior for baseline, dataset, trace, and score workflows;
- CLI/report expectations for partial persistence and lookup failures.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Langfuse remains the system of record; the feature exposes when Langfuse persistence/lookup confidence is incomplete.
- **Thin harness scope**: PASS. The design adds records and propagation through existing CLI/library paths.
- **Dataset simplicity**: PASS. No dataset schema changes.
- **Reproducibility metadata**: PASS. Missing or unconfirmed reproducibility metadata becomes visible.
- **Baseline-centric workflow**: PASS. Baseline not-found and lookup-failed states are separated.
- **Minimal local state**: PASS. No new local persistence.
- **Human review awareness**: PASS. Review linkage issues become visible warnings.
- **Local-first execution**: PASS. Local `uv run` verification remains sufficient for non-live paths.

## Verification Plan

1. Run focused unit tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_baselines.py tests/unit/test_langfuse_dataset_sync.py tests/unit/test_langfuse_traces.py tests/unit/test_langfuse_scores.py tests/unit/test_langfuse_gateway_warnings.py`
2. Run workflow integration tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py tests/integration/test_langfuse_failure_surface.py`
3. Run CLI contract tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_run_baseline.py tests/contract/test_cli_run_candidate.py tests/contract/test_cli_export.py`
4. Run broader non-live tests:
   `uv run pytest --no-cov -p no:cacheprovider -m "not live"`
5. Run live tests when credentials and service availability are present:
   `uv run pytest --no-cov -p no:cacheprovider -m live -vv`
6. Run focused quality checks:
   `uv run ruff check src/evaluator_harness/langfuse_*.py src/evaluator_harness/runner.py tests/unit/test_langfuse_*.py --no-cache`
   `uv run pyright src/evaluator_harness/langfuse_records.py src/evaluator_harness/langfuse_baselines.py src/evaluator_harness/langfuse_dataset.py src/evaluator_harness/langfuse_traces.py src/evaluator_harness/langfuse_scores.py src/evaluator_harness/runner.py`
7. Run `graphify update .` after code changes.
