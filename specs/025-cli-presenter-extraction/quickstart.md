# Quickstart: CLI Presenter Extraction

## Prerequisites

- In repository root: `C:/_projects/oc/EvaluatorHarness`
- Branch: `025-cli-presenter-extraction`
- Dependencies installed: `uv sync`

## Implement the Refactor

1. Create `src/evaluator_harness/cli_presenters.py`.
2. Move command result rendering from `cli.py` into `present_*` functions.
3. Keep command-owned exit logic and interactive prompts in `cli.py`.
4. Ensure presenters accept only `(result, console)`.
5. Ensure result payloads include all display-required context.

## Run Focused Tests

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_cli_presenters.py -vv
```

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_project_env_files.py -vv
```

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py -vv
```

## Run Broad Validation

```powershell
uv run pytest --no-cov -p no:cacheprovider -m "not live"
```

## Lint and Type Check

```powershell
uv run ruff check src/evaluator_harness/cli.py src/evaluator_harness/cli_presenters.py tests/unit/test_cli_presenters.py --no-cache
uv run pyright src/evaluator_harness/cli.py src/evaluator_harness/cli_presenters.py
```

## Refresh Graph

```powershell
graphify update .
```

## Implementation Validation Notes (2026-06-23)

- `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_cli_presenters.py -q` -> 12 passed
- `uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_project_env_files.py tests/integration/test_run_baseline.py -q` -> 13 passed
- `uv run pyright src/evaluator_harness/cli.py src/evaluator_harness/cli_presenters.py` -> 0 errors
- `uv run ruff check src/evaluator_harness/cli.py src/evaluator_harness/cli_presenters.py tests/unit/test_cli_presenters.py --no-cache` -> clean
- `uv run pytest --no-cov -p no:cacheprovider -m "not live" -q` -> 622 passed, 5 skipped, 9 deselected
