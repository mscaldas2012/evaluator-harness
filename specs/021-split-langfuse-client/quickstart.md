# Quickstart: Split Langfuse Client

## Setup

```powershell
uv sync --extra dev
```

## Inspect the Baseline

```powershell
uv run python scripts/quality_report.py
```

Review:

- `reports/quality/radon-maintainability.txt`
- `reports/quality/radon-complexity.txt`
- `reports/quality/pyright.txt`
- `reports/quality/ruff-check.txt`

Current acceptance baseline for this feature:

- `src\evaluator_harness\langfuse_client.py - C (0.00)`
- D-ranked facade hotspots include `LangfuseClient.sync_dataset` and `_object_to_evaluator_dict`
- Physical lines in `langfuse_client.py`: 2,400
- Ruff diagnostics in `langfuse_client.py`: 56 total, with `E501` 54 and `I001` 2
- Pyright errors in `langfuse_client.py`: 10
- Radon C-ranked complexity blocks in `langfuse_client.py`: 15

Post-refactor snapshot from local commands:

- `src\evaluator_harness\langfuse_client.py - A (26.97)`
- `radon raw src\evaluator_harness\langfuse_client.py`: LOC 833, SLOC 732, LLOC 288
- `radon cc src\evaluator_harness\langfuse_client.py -s`: all reported blocks are A-ranked; no public facade D-ranked blocks remain
- Refactor-scoped Ruff check passed for changed Langfuse modules and related tests
- Focused non-live regression suite passed: 75 tests

Generated quality report status:

- `uv run python scripts/quality_report.py` wrote reports under `reports/quality/`
- Full report currently fails repo-wide Ruff check/format, Pyright, and pytest
- Ruff failures include unrelated scripts and project-wide formatting debt outside the extracted Langfuse modules
- Pytest failed before collection because coverage could not remove `.coverage` on Windows: `PermissionError: [WinError 5] Access is denied`
- Pyright report still includes broad repository diagnostics and environment/module-resolution diagnostics; inspect `reports/quality/pyright.txt` before treating it as a refactor-only gate

Final Phase 5/6 verification snapshot:

- Focused in-memory and dry-run suite passed: `13 passed`
- Refactor-scoped Ruff passed for `langfuse_in_memory.py`, in-memory tests, gateway tests, and facade tests
- Exact non-live command `uv run pytest -p no:cacheprovider` was blocked before collection by Windows coverage file permissions on `.coverage`
- Non-live behavior without coverage passed: `519 passed, 9 deselected`
- Live suite with `RUN_LIVE_TESTS=1` selected 9 tests: `1 passed`, `8 failed` because Langfuse HTTP calls were refused with `[WinError 10061]`
- Quality report regenerated under `reports/quality/`; import-linter and Radon gates passed, while repo-wide Ruff, Ruff format, Pyright, pytest coverage save, and coverage summary remain failing gates
- `graphify update .` completed after code changes and refreshed `graphify-out/`

Final Phase 7 query split verification snapshot:

- Focused owner-module query tests passed: `17 passed`
- Facade/gateway regression tests passed: `19 passed`
- Phase 7 touched-file Ruff check passed
- Exact broad query split Ruff command still fails on pre-existing findings in `langfuse_evaluator_setup.py`, `tests/unit/test_langfuse_evaluator_rest.py`, and `tests/unit/test_langfuse_trace_ids.py`
- `src\evaluator_harness\langfuse_queries.py` was removed after all source and test imports moved to focused owner modules
- New owner module Radon maintainability:
  - `src\evaluator_harness\langfuse_baselines.py - A (27.24)`
  - `src\evaluator_harness\langfuse_prompts.py - A (35.24)`
  - `src\evaluator_harness\langfuse_scores.py - A (46.35)`
  - `src\evaluator_harness\langfuse_settings.py - A (65.47)`
  - `src\evaluator_harness\langfuse_traces.py - A (23.76)`
- New owner module Radon complexity has no D-ranked blocks; highest remaining query workflow blocks are C-ranked in baseline and trace workflows

Final Phase 8 legacy client removal snapshot:

- `src\evaluator_harness\langfuse_client.py` was removed.
- The default concrete gateway/state holder is now `src\evaluator_harness\langfuse_default_gateway.py`.
- Active source, tests, and scripts no longer contain `LangfuseClient`, `langfuse_client`, or `test_langfuse_client_facade`.
- Boundary search passed with no matches:
  `rg "LangfuseClient|langfuse_client|test_langfuse_client_facade" src tests scripts`
- Boundary and runtime gateway tests passed: `5 passed`.
- Broad non-live suite passed: `537 passed, 9 deselected`.
- Migration-scoped Ruff passed for `langfuse_default_gateway.py`, gateway modules, boundary tests, quality baseline test, and default gateway integration test.
- Radon maintainability reports `src\evaluator_harness\langfuse_default_gateway.py - A (26.86)`.
- Live suite selected 9 tests: `1 passed`, `8 failed` because Langfuse HTTP calls were refused with `[WinError 10061]`.
- `graphify update .` completed after runtime migration changes.

Final direct gateway dependency snapshot:

- `ExperimentRunner` depends on the `LangfuseGateway` protocol and receives a gateway instance through constructor injection.
- Gateway construction is centralized in `src\evaluator_harness\langfuse_gateways.py` through `build_default_langfuse_gateway()` and `build_langfuse_gateway_from_env()`.
- `DefaultLangfuseGateway` remains the concrete in-memory/live state owner, but it is no longer exposed as a runtime facade dependency for project workflows.
- Active source, tests, and scripts no longer contain `LangfuseRuntime`, `langfuse_runtime`, `LangfuseClient`, or `langfuse_client`.
- Boundary search passed with no matches:
  `rg "LangfuseRuntime|langfuse_runtime|LangfuseClient|langfuse_client" src tests scripts`
- Focused gateway migration regression suite passed: `80 passed`.
- Focused Ruff checks passed for migrated gateway files and touched runner/script imports.

## Implementation Checkpoints

1. Do not keep a `LangfuseClient` symbol or `langfuse_client.py` module in active source.
2. Route active project workflows through the Langfuse gateway boundary, gateway factory, concrete gateways, and focused owner modules.
3. Preserve current CLI, YAML, dataset, run, export, review, and Langfuse metadata behavior.
4. Preserve deterministic in-memory behavior for tests and dry runs without live credentials.
5. Preserve SDK-backed live behavior and REST-compatible fallback behavior.
6. Preserve retry/error handling and secret redaction.
7. Keep Langfuse query business logic in focused owner modules; `langfuse_queries.py` is no longer part of the implementation.
8. Use `LangfuseGateway` as the active project dependency; concrete gateway classes remain behind gateway builders.

## Verify Legacy Client Migration

```powershell
rg "LangfuseRuntime|langfuse_runtime|LangfuseClient|langfuse_client" src tests scripts
```

Expected result: no matches in active source, tests, or scripts.

## Verify Non-Live Behavior

```powershell
uv run pytest -p no:cacheprovider
```

## Verify Live Behavior

Requires valid live environment credentials.

```powershell
uv run pytest --no-cov -p no:cacheprovider -m live -vv
```

## Regenerate Quality Reports

```powershell
uv run python scripts/quality_report.py
```

Acceptance checks:

- `langfuse_client.py` is removed.
- Internal project workflows use the gateway boundary and focused owner modules.
- Changed Langfuse-related files introduce no new Ruff or Pyright diagnostic categories.
