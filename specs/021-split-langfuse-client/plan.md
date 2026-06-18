# Implementation Plan: Split Langfuse Client

**Branch**: `021-split-langfuse-client` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/021-split-langfuse-client/spec.md`

## Summary

Complete the Langfuse architecture migration by deprecating `LangfuseClient` as an active runtime facade and moving internal project workflows to the Langfuse gateway boundary, gateway factory, concrete gateway classes, and focused owner modules. Existing CLI commands, project YAML, run behavior, Langfuse metadata, dry-run behavior, and live fallback behavior must remain compatible for users, while active internal source and tests stop depending on `LangfuseClient` for workflow execution.

The previous phase split the original god object into focused modules. This plan updates the end state: `LangfuseClient` may remain only as a documented non-runtime compatibility shim, or it may be removed if no supported internal or external contract requires it.

## Technical Context

**Language/Version**: Python 3.12 project using modern type annotations and Pydantic models.

**Primary Dependencies**: Langfuse SDK/API, Pydantic, Typer CLI, pytest, Ruff, Pyright, Radon, Vulture, Import Linter, existing `uv` managed environment.

**Python Environment Management**: Use `uv` for environment management, dependency setup, lockfile management, and command execution. Prefer `uv sync` and `uv run ...`.

**Storage**: Langfuse remains the system of record. Local state remains limited to filesystem project config, datasets, prompts, generated reports, and existing annotation queue binding files.

**Testing**: `pytest` for unit, contract, integration, and live tests. Quality verification uses focused Ruff/Radon checks plus the local quality report script where practical.

**Target Platform**: Local developer machines running the Python CLI; live validation requires configured Langfuse credentials and reachable external services.

**Project Type**: Local Python CLI/library package.

**Performance Goals**: Preserve current workflow behavior and avoid additional live API calls beyond existing SDK/REST fallback needs. Retry and pagination behavior must remain bounded.

**Constraints**: Keep current CLI/project YAML compatibility, avoid new services or long-lived local stores, preserve secret redaction, keep in-memory tests credential-free, and pass the full live test suite before final acceptance when live service access is available.

**Scale/Scope**: One architectural migration across Langfuse integration callers. Expected touch points include `runner.py`, `annotation_queues.py`, `prompt_sync.py`, `langfuse_evaluator_setup.py`, cleanup scripts, contract tests, integration tests, and Langfuse gateway tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The migration preserves Langfuse as the system of record and keeps traces, scores, prompts, evaluators, annotation queues, baselines, and comparisons Langfuse-backed.
- **Thin harness scope**: PASS. The design uses explicit Python modules and gateway classes already present in the codebase. It does not introduce services, orchestration frameworks, or dependency injection frameworks.
- **Dataset simplicity**: PASS. Dataset shape and project YAML semantics remain unchanged.
- **Reproducibility metadata**: PASS. The gateway boundary must preserve provider, model, prompt, evaluator, token, latency, dataset, baseline, run, and config metadata logging.
- **Baseline-centric workflow**: PASS. Baseline lookup/reuse remains part of focused Langfuse owner modules and the gateway-backed workflow.
- **Minimal local state**: PASS. No new durable local state is introduced.
- **Human review awareness**: PASS. Annotation queue behavior remains Langfuse-backed and visible for human review.
- **Local-first execution**: PASS. Verification remains through `uv run ...` commands.

## Project Structure

### Documentation (this feature)

```text
specs/021-split-langfuse-client/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- langfuse-boundary.md
|-- checklists/
|   `-- requirements.md
`-- tasks.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
|-- langfuse_gateways.py            # Boundary protocols and gateway factory
|-- langfuse_in_memory.py           # Deterministic test/dry-run gateway
|-- langfuse_sdk.py                 # SDK-backed live gateway
|-- langfuse_rest.py                # REST-compatible fallback operations
|-- langfuse_records.py             # Typed records shared across gateways
|-- langfuse_mappers.py             # Object/dict normalization
|-- langfuse_retry.py               # Retry, pagination, and error wrapping helpers
|-- langfuse_dataset.py             # Dataset sync and run item operations
|-- langfuse_score_configs.py       # Score config sync operations
|-- langfuse_observations.py        # Trace/span/run observation operations
|-- langfuse_annotation_ops.py      # Annotation queue operations
|-- langfuse_evaluator_ops.py       # Evaluator operations
|-- langfuse_baselines.py           # Baseline lookup workflows
|-- langfuse_prompts.py             # Prompt version workflows
|-- langfuse_traces.py              # Trace and run-output workflows
|-- langfuse_scores.py              # Score retrieval workflows
|-- langfuse_settings.py            # Langfuse polling/settings helpers
|-- langfuse_default_gateway.py     # Default concrete gateway/state holder behind builders
|-- annotation_queues.py            # Migrate from client facade to gateway-backed calls
|-- prompt_sync.py                  # Migrate from client facade to gateway-backed calls
|-- langfuse_evaluator_setup.py     # Migrate from client facade to gateway-backed calls
`-- runner.py                       # Migrate from client facade to gateway-backed calls

scripts/
|-- cleanup_duplicate_score_configs.py
|-- cleanup_invalid_annotation_queue_items.py
`-- reset_annotation_queue_for_project.py

tests/
|-- unit/
|   |-- test_langfuse_gateways.py
|   |-- test_langfuse_in_memory.py
|   |-- test_langfuse_mappers.py
|   |-- test_langfuse_retry.py
|   |-- test_langfuse_baselines.py
|   |-- test_langfuse_prompts.py
|   |-- test_langfuse_scores.py
|   |-- test_langfuse_settings.py
|   `-- test_langfuse_traces.py
|-- integration/
|   |-- test_langfuse_default_gateway.py # default gateway integration tests
|   `-- live/
|       `-- existing live smoke tests
`-- contract/
    `-- existing CLI/project contract tests
```

**Structure Decision**: Use the existing Langfuse gateway and owner modules as the active internal integration surface. Migrate project workflows to a small gateway construction context rather than preserving the legacy client facade as the runtime entry point.

## Complexity Tracking

No constitution violations are introduced.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Phase 0: Research Summary

See [research.md](research.md). Updated decisions:

- Deprecate `LangfuseClient` as an active runtime facade.
- Use `LangfuseGateway` and focused owner modules as the internal integration surface.
- Keep CLI/YAML/user behavior stable while allowing internal caller churn.
- Keep any legacy `LangfuseClient` symbol as a documented shim only if needed for compatibility; otherwise remove it.

## Current Quality Baseline

Baseline source files:

- `src/evaluator_harness/langfuse_client.py` (removed in Phase 8)
- `src/evaluator_harness/langfuse_default_gateway.py`
- `src/evaluator_harness/langfuse_*.py`
- `reports/quality/ruff-check.txt`
- `reports/quality/pyright.txt`
- `reports/quality/radon-complexity.txt`
- `reports/quality/radon-maintainability.txt`

Original `langfuse_client.py` baseline:

| Measure | Original Baseline |
|---------|-------------------|
| Physical lines | 2,400 |
| Radon maintainability | `C (0.00)` |
| Radon D-ranked complexity blocks | 2 |
| Radon C-ranked complexity blocks | 15 |
| Ruff diagnostics in file | 56 total: `E501` 54, `I001` 2 |
| Pyright errors in file | 10 |

Current post-split direction:

- `langfuse_client.py` has been removed in favor of direct `LangfuseGateway` dependencies and `langfuse_default_gateway.py` as the default concrete state holder.
- `langfuse_queries.py` has been removed after owner-module extraction.
- Gateway and owner modules become the quality surface for future Langfuse work.

## Phase 1: Design Summary

See [data-model.md](data-model.md) and [contracts/langfuse-boundary.md](contracts/langfuse-boundary.md).

The design defines:

- a `LangfuseGateway` boundary for dataset, run, trace, score, prompt, evaluator, annotation queue, baseline, and metadata operations,
- a gateway factory for selecting in-memory, SDK-backed, and fallback-capable live behavior,
- focused owner modules for workflow orchestration and normalization,
- a migration path for `runner.py`, CLI support modules, scripts, and tests to stop constructing or depending on `LangfuseClient`.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. No local replacement for Langfuse features is planned.
- **Thin harness scope**: PASS. The design uses explicit Python modules and a small gateway boundary, not a framework or service.
- **Dataset simplicity**: PASS. Dataset shape is unchanged.
- **Reproducibility metadata**: PASS. Current metadata contract is preserved through gateway-backed workflows.
- **Baseline-centric workflow**: PASS. Baseline lookup remains a Langfuse workflow.
- **Minimal local state**: PASS. No new durable local state is introduced.
- **Human review awareness**: PASS. Annotation queue behavior remains in scope and Langfuse-backed.
- **Local-first execution**: PASS. Verification commands remain local `uv run ...` commands.

## Verification Plan

1. Search for active legacy client usage:
   `rg "LangfuseClient|langfuse_client" src tests scripts`
2. Run gateway and owner-module tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_gateways.py tests/unit/test_langfuse_in_memory.py tests/unit/test_langfuse_mappers.py tests/unit/test_langfuse_retry.py tests/unit/test_langfuse_baselines.py tests/unit/test_langfuse_prompts.py tests/unit/test_langfuse_traces.py tests/unit/test_langfuse_scores.py tests/unit/test_langfuse_settings.py`
3. Run migrated workflow regression tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_dataset_sync.py tests/unit/test_langfuse_score_config_sync.py tests/unit/test_langfuse_evaluator_rest.py tests/integration/test_select_review.py`
4. Run broader non-live tests:
   `uv run pytest --no-cov -p no:cacheprovider -m "not live"`
5. Run live tests when credentials and service availability are present:
   `uv run pytest --no-cov -p no:cacheprovider -m live -vv`
6. Run focused quality checks:
   `uv run ruff check src/evaluator_harness/langfuse_*.py tests/unit/test_langfuse_*.py --no-cache`
   `uv run radon mi src/evaluator_harness -s`
   `uv run radon cc src/evaluator_harness -s`
7. Run `graphify update .` after code changes.
