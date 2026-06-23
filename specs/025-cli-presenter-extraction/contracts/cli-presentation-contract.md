# Contract: CLI Presentation Boundary

## Scope

Defines how `cli.py` and `cli_presenters.py` interact for command result rendering.

## Function Contract

All presenter functions MUST conform to:

```python
def present_<command>_result(result: object, console: Console) -> None:
    ...
```

Rules:

1. Exactly two parameters: `result` and `console`.
2. Return `None`.
3. Perform output only through `console.print(...)` (and equivalent Rich rendering APIs).
4. Do not call runner/service functions.
5. Do not read command-local variables.
6. Do not raise `typer.Exit`.

## Command Boundary Contract

Each command in `cli.py` MUST:

1. Resolve project path and parse options.
2. Execute `_handle_command(...)` for runner/service invocation.
3. If result is not `None`, call exactly one presenter function for final result output.
4. Apply command-specific exit policy in command code (`raise typer.Exit(...)` when needed).

## Command Presenter Mapping

| Command | Presenter |
|---------|-----------|
| `validate` | `present_validate_result` |
| `sync-dataset` | `present_sync_dataset_result` |
| `sync-score-configs` | `present_sync_score_configs_result` |
| `sync-prompts` | `present_sync_prompts_result` |
| `sync-all` | `present_sync_all_result` |
| `sync-annotation-queue` | `present_sync_annotation_queue_result` |
| `render-judge-prompts` | `present_render_judge_prompts_result` |
| `export-evaluator-setup` | `present_export_evaluator_setup_result` |
| `sync-judge-evaluators` | `present_judge_setup_result` |
| `run` | `present_run_result` |
| `select-review` | `present_select_review_result` |
| `export` | `present_export_result` |
| `campaign` | `present_campaign_result` |
| `comparison-report` | `present_comparison_report_result` |
| `excel-report` | `present_comparison_report_result` |

## Self-Contained Result Contract

Any displayed value that originated from command flags must be present in the `result` object passed to a presenter.

Examples:

- If presentation needs a baseline identifier, the result object must include it.
- If presentation needs mode/skip indicators, the result object must include normalized display fields.

## Output Parity Contract

Refactor must preserve existing user-visible output behavior:

- Same line labels and value formatting.
- Same warning visibility and ordering.
- Same success/failure summary semantics.

Minor internal differences allowed:

- Function names and module boundaries.
- Internal helper decomposition inside presenter module.

## Test Contract

Minimum required coverage:

1. Presenter unit tests for each presenter function asserting expected output lines.
2. Existing CLI contract/integration tests continue to pass without command option changes.
3. Non-live suite remains green for touched behavior paths.
