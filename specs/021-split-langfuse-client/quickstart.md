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

## Implementation Checkpoints

1. Keep `LangfuseClient` as the public compatibility facade.
2. Extract mapper behavior into focused normalization functions with tests.
3. Extract in-memory behavior behind the same boundary as live behavior.
4. Extract SDK-backed live behavior and REST-compatible fallback behavior.
5. Extract retry/error handling so live operations use one redaction policy.
6. Update facade methods to delegate to the new focused modules.
7. Preserve current CLI, YAML, and caller behavior.

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

- `langfuse_client.py` maintainability improves from `C (0.00)`.
- No D-ranked complexity blocks remain in the public client facade.
- Changed Langfuse-related files introduce no new Ruff or Pyright diagnostic categories.
