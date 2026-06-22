# Implementation Plan: Shared Run Item Execution

**Branch**: `023-shared-run-execution` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/023-shared-run-execution/spec.md`

## Summary

Extract the duplicated baseline and candidate per-item execution mechanics from `ExperimentRunner` into a shared execution path driven by run-type-specific plans. The implementation will preserve current user-visible behavior exactly, except for any explicitly documented and regression-tested parity fixes, while keeping baseline creation and candidate comparison semantics distinct.

## Technical Context

**Language/Version**: Python 3.12 project using modern type annotations and dataclasses/Pydantic models where already established.

**Primary Dependencies**: Langfuse SDK/API through existing gateway adapters, Pydantic, Typer CLI, pytest, Ruff, Pyright, Radon, Vulture, Import Linter, existing `uv` managed environment.

**Python Environment Management**: Use `uv` for environment management, dependency setup, lockfile management, and command execution. Prefer `uv sync` and `uv run ...`.

**Storage**: Langfuse remains the system of record. Local state remains limited to existing filesystem datasets, prompts, project config, generated reports, baseline references, and temporary run artifacts. This feature introduces no new durable store.

**Testing**: `pytest` for unit, integration, and contract tests. Verification focuses on existing baseline/candidate integration tests plus new shared-run-item assertions where needed.

**Target Platform**: Local developer machines running the Python CLI/library package.

**Project Type**: Local Python CLI/library package.

**Performance Goals**: Preserve current per-item run throughput and avoid additional provider calls, Langfuse calls, dataset scans, or evaluator queue operations beyond current behavior.

**Constraints**: Preserve command names, project YAML shape, dataset formats, report formats, live/dry-run behavior, Langfuse warning behavior from feature 022, baseline/candidate semantics, and credential-free non-live tests. Any parity correction must be explicit and regression-tested.

**Scale/Scope**: Focused refactor in `ExperimentRunner` item execution. Expected touch points are `src/evaluator_harness/runner.py` and focused tests in baseline/candidate integration and contract suites. No new subsystem, service, queue, database, or CLI surface is planned.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature preserves existing Langfuse traces, observations, dataset run item linkage, baseline references, evaluator payloads, warnings, and comparison metadata.
- **Thin harness scope**: PASS. The design remains a local Python CLI/library refactor and does not add services, orchestration, distributed execution, or local APIs.
- **Dataset simplicity**: PASS. CSV datasets with an `input` column and existing Langfuse dataset behavior are preserved unchanged.
- **Reproducibility metadata**: PASS. The purpose of the shared path is to preserve and verify model, prompt, parameter, dataset, baseline, trace, session, and evaluator metadata consistently.
- **Baseline-centric workflow**: PASS. Baseline runs still create/record compatible baseline references before candidate comparison; candidates still consume a resolved baseline.
- **Minimal local state**: PASS. No new persistent state is introduced; existing local baseline references remain as-is.
- **Human review awareness**: PASS. Trace, score, dataset item, and run metadata remain available for downstream review and annotation workflows.
- **Local-first execution**: PASS. Implementation and verification use local `uv run ...` commands.

## Project Structure

### Documentation (this feature)

```text
specs/023-shared-run-execution/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- run-item-execution.md
|-- checklists/
|   `-- requirements.md
`-- tasks.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
`-- runner.py                      # shared per-item run execution and run plans

tests/
|-- integration/
|   |-- test_run_baseline.py       # baseline behavior preservation and failure evidence
|   `-- test_run_candidate.py      # candidate behavior preservation and parity checks
|-- contract/
|   |-- test_cli_run_baseline.py   # command/result behavior preservation
|   `-- test_cli_run_candidate.py  # command/result behavior preservation
`-- unit/
    `-- test_langfuse_gateway_warnings.py  # warning behavior remains covered from feature 022
```

**Structure Decision**: Keep the work inside the existing runner owner boundary unless implementation proves a small helper module is necessary. The first design target is shared item execution plus run-type-specific plan/result records close to `ExperimentRunner`, because this removes duplication without adding a new architecture layer.

## Complexity Tracking

No constitution violations are introduced.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Phase 0: Research Summary

See [research.md](research.md). Decisions:

- Use a shared per-item execution path driven by explicit baseline/candidate run plans.
- Keep run setup/finalization in the existing baseline and candidate methods.
- Preserve behavior strictly; only documented, regression-tested parity fixes are allowed.
- Keep Langfuse warning and partial-persistence propagation unchanged.
- Use focused shared assertions and existing workflow tests rather than broad report rewrites.

## Phase 1: Design Summary

See [data-model.md](data-model.md) and [contracts/run-item-execution.md](contracts/run-item-execution.md).

The design defines:

- `RunItemExecutionPlan` for shared item inputs and run-type-specific context;
- `RunItemExecutionResult` for completed/failed item evidence and evaluator payload inputs;
- baseline and candidate evaluator payload responsibilities;
- success/failure trace and dataset run item linkage contract;
- verification expectations for preserving current command and report behavior.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The plan preserves Langfuse as the evidence and comparison system, with no local replacement.
- **Thin harness scope**: PASS. The design refactors local control flow only.
- **Dataset simplicity**: PASS. Dataset loading and dataset identity behavior remain unchanged.
- **Reproducibility metadata**: PASS. Shared execution centralizes reproducibility metadata preparation and verification.
- **Baseline-centric workflow**: PASS. Candidate execution remains dependent on a compatible baseline reference.
- **Minimal local state**: PASS. No new state is added.
- **Human review awareness**: PASS. Existing trace and annotation inputs remain available.
- **Local-first execution**: PASS. Local `uv run` verification remains sufficient for non-live paths.

## Verification Plan

1. Run baseline/candidate workflow tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py -vv`
2. Run CLI contract tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_run_baseline.py tests/contract/test_cli_run_candidate.py -vv`
3. Run focused Langfuse warning regression tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_gateway_warnings.py -vv`
4. Run broader non-live tests when implementation is complete:
   `uv run pytest --no-cov -p no:cacheprovider -m "not live"`
5. Run focused quality checks:
   `uv run ruff check src/evaluator_harness/runner.py tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py --no-cache`
   `uv run pyright src/evaluator_harness/runner.py`
6. Run `graphify update .` after code changes.
