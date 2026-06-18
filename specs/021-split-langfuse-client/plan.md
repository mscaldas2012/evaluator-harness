# Implementation Plan: Split Langfuse Client

**Branch**: `021-split-langfuse-client` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/021-split-langfuse-client/spec.md`

## Summary

Refactor the current `LangfuseClient` god object into a compatibility facade backed by focused Langfuse boundaries for in-memory behavior, live SDK behavior, REST-compatible fallback behavior, object normalization, and retry/error handling. The public harness workflows and current callers continue using `LangfuseClient`, while delegated modules take ownership of dataset sync, score configs, prompts, traces, evaluator setup, annotation queues, mapping, and error policy. The acceptance bar is behavior preservation plus measurable quality improvement: `langfuse_client.py` must improve from maintainability `C (0.00)` and the public facade must contain no D-ranked complexity blocks.

## Technical Context

**Language/Version**: Python 3.12 project using modern type annotations and Pydantic models.

**Primary Dependencies**: Langfuse SDK/API, Pydantic, Typer CLI, pytest, Ruff, Pyright, Radon, Vulture, Import Linter, existing `uv` managed environment.

**Python Environment Management**: Use `uv` for environment management, dependency setup, lockfile management, and command execution. Prefer `uv sync` and `uv run ...`.

**Storage**: Langfuse remains the system of record. Local state remains limited to filesystem project config, datasets, prompts, generated reports, and existing annotation queue binding files.

**Testing**: `pytest` for unit, contract, integration, and live tests. Quality verification uses the local quality report script for Ruff, Pyright, Radon, Vulture, Import Linter, and coverage reporting.

**Target Platform**: Local developer machines running the Python CLI; live validation requires configured Langfuse credentials and reachable external services.

**Project Type**: Local Python CLI/library package.

**Performance Goals**: Preserve current workflow behavior and avoid additional live API calls beyond existing SDK/REST fallback needs. Retry and pagination behavior must remain bounded.

**Constraints**: Keep current CLI/project YAML compatibility, keep `LangfuseClient` as the public facade, avoid new services or long-lived local stores, preserve secret redaction, and pass the full live test suite before acceptance.

**Scale/Scope**: One architectural refactor centered on `src/evaluator_harness/langfuse_client.py` and extracted Langfuse support modules. Existing callers should need minimal or no changes outside focused test updates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The refactor preserves Langfuse as the system of record and keeps Langfuse-native traces, scores, prompts, evaluators, annotation queues, and comparisons. REST fallback is retained only for documented SDK capability gaps already present in current behavior.
- **Thin harness scope**: PASS. The design remains a local Python CLI/library refactor with small modules and no services, orchestration framework, or custom platform.
- **Dataset simplicity**: PASS. Existing CSV dataset semantics, including the `input` column default, are preserved.
- **Reproducibility metadata**: PASS. The facade must preserve current provider, model, prompt, evaluator, token, latency, dataset, baseline, run, and config metadata logging.
- **Baseline-centric workflow**: PASS. Baseline lookup/reuse behavior remains part of the Langfuse boundary and current comparison semantics are preserved.
- **Minimal local state**: PASS. No new local database, queue, cache, or service is introduced. Existing filesystem artifacts remain the only local state.
- **Human review awareness**: PASS. Annotation queue routing and review handles remain Langfuse-backed and visible for human review.
- **Local-first execution**: PASS. Development, tests, and reports continue through `uv run ...` commands.

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
|-- langfuse_client.py              # Compatibility facade retained for callers
|-- langfuse_gateways.py            # Boundary protocols and gateway factory
|-- langfuse_in_memory.py           # Deterministic test/dry-run gateway
|-- langfuse_sdk.py                 # SDK-backed live operations
|-- langfuse_rest.py                # REST-compatible fallback operations
|-- langfuse_mappers.py             # Object/dict to internal record normalization
|-- langfuse_retry.py               # Retry, pagination, and error wrapping helpers
|-- langfuse_records.py             # Typed records shared across gateways
|-- annotation_queues.py            # Existing queue orchestration remains compatible
|-- langfuse_evaluator_setup.py     # Existing evaluator setup consumes facade/boundary
`-- runner.py                       # Existing workflow caller, minimal changes only

tests/
|-- unit/
|   |-- test_langfuse_gateways.py
|   |-- test_langfuse_in_memory.py
|   |-- test_langfuse_mappers.py
|   `-- test_langfuse_retry.py
|-- integration/
|   |-- test_langfuse_client_facade.py
|   `-- live/
|       `-- existing live smoke tests
`-- contract/
    `-- existing CLI/project contract tests

reports/quality/
|-- ruff-check.txt
|-- pyright.txt
|-- radon-complexity.txt
`-- radon-maintainability.txt
```

**Structure Decision**: Keep `LangfuseClient` in `langfuse_client.py` as the compatibility facade and extract implementation responsibilities into sibling modules under `src/evaluator_harness/`. This keeps the harness simple, avoids a package-wide relocation, and lets tests cover each responsibility independently.

## Complexity Tracking

No constitution violations are introduced.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Phase 0: Research Summary

See [research.md](research.md). Main decisions:

- Use a facade plus protocol-backed gateway strategy rather than migrating callers to new APIs.
- Use typed internal records and mapper functions to reduce Pyright uncertainty from SDK objects and dictionaries.
- Keep SDK and REST behavior separate so fallback capability gaps are explicit.
- Use targeted extraction based on current Radon hotspots before broader cleanup.

## Current `langfuse_client.py` Quality Baseline

Baseline source files:

- `src/evaluator_harness/langfuse_client.py`
- `reports/quality/ruff-check.txt`
- `reports/quality/pyright.txt`
- `reports/quality/radon-complexity.txt`
- `reports/quality/radon-maintainability.txt`

| Measure | Current Baseline |
|---------|------------------|
| Physical lines | 2,400 |
| Radon maintainability | `C (0.00)` |
| Radon D-ranked complexity blocks | 2 |
| Radon C-ranked complexity blocks | 15 |
| Ruff diagnostics in file | 56 total: `E501` 54, `I001` 2 |
| Pyright errors in file | 10 |

Top Radon complexity hotspots in the current file:

| Rank | Symbol | Grade |
|------|--------|-------|
| 1 | `_object_to_evaluator_dict` | `D (22)` |
| 2 | `LangfuseClient.sync_dataset` | `D (22)` |
| 3 | `LangfuseClient._lookup_live_baseline` | `C (20)` |
| 4 | `_object_to_score_dict` | `C (19)` |
| 5 | `_object_to_score_config_dict` | `C (17)` |
| 6 | `LangfuseClient._load_live_score_configs_by_name` | `C (16)` |
| 7 | `LangfuseClient._live_list_prompt_versions` | `C (16)` |
| 8 | `_rest_evaluation_rule_update_payload` | `C (15)` |
| 9 | `LangfuseClient.traces_for_run` | `C (15)` |

Pyright error themes in the current file:

- Optional call safety.
- Nullable IDs passed where non-null strings are required.
- Dictionary value type mismatch.
- Nullable dictionary returns.
- Unknown context-manager protocol for object-typed spans.
- Unknown or nullable values passed into integer conversion.

## Phase 1: Design Summary

See [data-model.md](data-model.md) and [contracts/langfuse-boundary.md](contracts/langfuse-boundary.md).

The design defines a stable `LangfuseGateway` boundary with typed records for datasets, runs, traces, scores, prompts, evaluators, annotation queues, and operation failures. The facade delegates to:

- in-memory gateway for deterministic tests and dry runs,
- SDK gateway for primary live behavior,
- REST fallback gateway for live operations not exposed by the SDK,
- mappers for defensive object normalization,
- retry/error policy helpers for bounded live operation handling.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. No local replacement for Langfuse features is planned.
- **Thin harness scope**: PASS. The design uses explicit Python modules and protocols, not a framework or service.
- **Dataset simplicity**: PASS. Dataset shape is unchanged.
- **Reproducibility metadata**: PASS. Current metadata contract is preserved through typed records and facade compatibility.
- **Baseline-centric workflow**: PASS. Baseline lookup remains a boundary operation.
- **Minimal local state**: PASS. No new durable local state is introduced.
- **Human review awareness**: PASS. Annotation queue behavior remains in scope and Langfuse-backed.
- **Local-first execution**: PASS. Verification commands remain local `uv run ...` commands.

## Verification Plan

1. `uv run pytest -p no:cacheprovider`
2. `uv run pytest --no-cov -p no:cacheprovider -m live -vv` with live credentials configured
3. `uv run python scripts/quality_report.py`
4. Confirm regenerated reports show:
   - `langfuse_client.py` maintainability improved from `C (0.00)`
   - no D-ranked complexity blocks in the public facade
   - no new Ruff or Pyright diagnostic categories in changed Langfuse-related files
   - updated line count and diagnostic counts documented against the baseline above
