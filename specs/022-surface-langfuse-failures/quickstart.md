# Quickstart: Surface Live Langfuse Failures

## Setup

```powershell
uv sync --extra dev
```

## Validate the Spec Baseline

Review the current silent fallback hotspots before implementation:

```powershell
rg "except Exception|return None|return \\{\\}|return \\[\\]" src/evaluator_harness/langfuse_baselines.py src/evaluator_harness/langfuse_dataset.py src/evaluator_harness/langfuse_traces.py src/evaluator_harness/langfuse_scores.py
```

Expected focus areas:

- baseline lookup and dataset run metadata lookup
- dataset item lookup and dataset run item recording
- live trace lookup and dataset run trace lookup
- live score retrieval

Phase 1-3 target call sites:

- `src/evaluator_harness/langfuse_dataset.py`: `record_dataset_run_item_workflow`
  must surface live dataset run item persistence failures after primary and fallback
  create attempts fail.
- `src/evaluator_harness/langfuse_scores.py`: `live_scores_for_traces` and
  `_scores_for_trace` must surface live score lookup/page retrieval failures instead
  of returning an unqualified empty or partial score set.
- `src/evaluator_harness/langfuse_default_gateway.py`: gateway warning state owns
  aggregation and bounded examples for warnings produced by lower-level workflows.
- `src/evaluator_harness/runner.py`, `src/evaluator_harness/cli.py`, and
  `src/evaluator_harness/exports.py`: run/export user surfaces must preserve and
  print partial Langfuse persistence warnings.

## Verify Focused Behavior

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_baselines.py tests/unit/test_langfuse_dataset_sync.py tests/unit/test_langfuse_traces.py tests/unit/test_langfuse_scores.py
```

## Verify User-Facing Surfaces

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_run_baseline.py tests/contract/test_cli_run_candidate.py tests/contract/test_cli_export.py
```

## Verify Broader Non-Live Behavior

```powershell
uv run pytest --no-cov -p no:cacheprovider -m "not live"
```

## Verify Live Behavior

Requires valid live environment credentials and reachable Langfuse service.

```powershell
uv run pytest --no-cov -p no:cacheprovider -m live -vv
```

## Acceptance Checks

- Simulated live persistence failures produce warnings rather than silent success.
- Expected not-found outcomes remain distinct from lookup failures.
- Live lookup failures are not returned as unqualified empty results.
- Required missing live linkage fails the workflow with a clear reason.
- Warning messages identify affected run/item/trace/score/baseline context.
- Warning diagnostics are redacted.
- Non-live workflows still pass without live credentials.

## Phase 6 Verification Results

Verified on 2026-06-22:

- `uv run pytest --no-cov -p no:cacheprovider -m "not live"`
  passed: 561 passed, 9 deselected.
- `uv run pytest --no-cov -p no:cacheprovider -m live -vv`
  passed with live credentials: 9 passed, 561 deselected.
- `uv run pyright src/evaluator_harness/langfuse_records.py src/evaluator_harness/langfuse_baselines.py src/evaluator_harness/langfuse_dataset.py src/evaluator_harness/langfuse_traces.py src/evaluator_harness/langfuse_scores.py src/evaluator_harness/runner.py`
  passed: 0 errors, 0 warnings.
- `uv run ruff check src/evaluator_harness/langfuse_*.py src/evaluator_harness/runner.py src/evaluator_harness/exports.py src/evaluator_harness/cli.py tests/unit/test_langfuse_*.py tests/integration/test_langfuse_failure_surface.py --no-cache`
  still reports existing lint debt in the broad focused glob: 86 `E501`
  line-length findings and 2 `UP042` enum modernization findings. The findings
  cluster in `runner.py`, `langfuse_evaluator_setup.py`, `cli.py`,
  `exports.py`, and pre-existing Langfuse unit tests.

Live caveat: the live suite requires valid Langfuse credentials and reachable
workspace access. Failures from unavailable credentials or service access should
be treated as environment failures, not feature regressions.
