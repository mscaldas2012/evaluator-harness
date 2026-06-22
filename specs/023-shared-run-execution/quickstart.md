# Quickstart: Shared Run Item Execution

## Prerequisites

- Python dependencies installed with `uv sync`.
- Current branch: `023-shared-run-execution`.
- Active feature directory: `specs/023-shared-run-execution`.

## Validate the Current Feature Plan

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py -vv
```

## Validate CLI Behavior

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_run_baseline.py tests/contract/test_cli_run_candidate.py -vv
```

## Validate Langfuse Warning Behavior

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_gateway_warnings.py -vv
```

## Run Broader Non-Live Verification

```powershell
uv run pytest --no-cov -p no:cacheprovider -m "not live"
```

## Quality Checks

```powershell
uv run ruff check src/evaluator_harness/runner.py tests/integration/test_run_baseline.py tests/integration/test_run_candidate.py --no-cache
uv run pyright src/evaluator_harness/runner.py
```

## Graph Update After Implementation

```powershell
graphify update .
```
