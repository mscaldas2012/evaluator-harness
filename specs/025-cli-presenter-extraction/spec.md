# Feature Specification: CLI Presenter Extraction

**Feature Branch**: `025-cli-presenter-extraction`

**Created**: 2026-06-23

**Status**: Draft

**Input**: User description: "TD-GRAPH-005: Move CLI result presentation out of command bodies — add presenter functions/classes per command group and keep Typer command functions thin"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Thin Command Bodies (Priority: P1)

As a developer adding or modifying a CLI command, I want each Typer command function to contain only parameter declarations, project path resolution, runner invocation, and an exit code decision — so that I can understand what a command does without reading through unrelated formatting logic.

**Why this priority**: This is the direct driver of the technical debt item. Large command bodies that mix concerns require a developer to mentally parse presentation logic to understand control flow.

**Independent Test**: A code reviewer can open `cli.py` and see each command body contain at most one `_handle_command()` call, followed by at most one presenter call, with no `console.print()` statements inline.

**Acceptance Scenarios**:

1. **Given** the `run` command body, **When** a developer reads it, **Then** all `console.print()` calls are absent from the command body and delegated to a `present_run_result()` function.
2. **Given** the `campaign` command body, **When** a developer reads it, **Then** all `console.print()` calls (except progress callbacks) are absent from the command body and delegated to a `present_campaign_result()` function.
3. **Given** the `sync-prompts` command body, **When** a developer reads it, **Then** all `console.print()` calls are absent and delegated to a `present_sync_prompts_result()` function.
4. **Given** the `sync-all` command body, **When** a developer reads it, **Then** all `console.print()` calls are absent and delegated to a `present_sync_all_result()` function.
5. **Given** the `select-review` command body, **When** a developer reads it, **Then** all `console.print()` calls are absent and delegated to a presenter function.

---

### User Story 2 - Isolated Presentation Tests (Priority: P2)

As a developer writing tests for CLI output format, I want to call a presenter function directly with a result object — so that tests do not need to invoke the full CLI pipeline to verify what gets printed.

**Why this priority**: This directly addresses the second stated problem — "command tests sensitive to presentation details." Isolated presenter tests are faster and less brittle.

**Independent Test**: A test can import `present_run_result(result, console, ...)` and assert on captured output without invoking `typer.testing.CliRunner`.

**Acceptance Scenarios**:

1. **Given** a mock `RunResult` object, **When** `present_run_result()` is called, **Then** output contains the expected `run:`, `completed/failed:`, optional `baseline-reference:`, and optional warning lines.
2. **Given** a mock `CampaignResult` with failures, **When** `present_campaign_result()` is called, **Then** output contains the expected `campaign: completed-with-failures` header and failure lines.
3. **Given** a mock `SyncPromptsResult` with conflicts, **When** `present_sync_prompts_result()` is called, **Then** output contains the expected per-item and summary lines.

---

### User Story 3 - Consistent Presenter Location (Priority: P3)

As a developer, I want all CLI presentation logic to live in a dedicated `cli_presenters.py` module — so that the location of presentation logic is predictable and discoverable.

**Why this priority**: Centralizing presenters prevents presentation code from drifting back into command bodies and makes the module boundary clear.

**Independent Test**: `grep -r "console.print" src/evaluator_harness/cli.py` returns only calls inside the `_runner()`, `_handle_command()`, `_resolve_project_path()`, `_selected_reports_dir()` utility helpers and progress callbacks — not inside command body `if result is not None:` blocks.

**Acceptance Scenarios**:

1. **Given** a new presenter module `cli_presenters.py`, **When** it is imported, **Then** it exports one presenter function per command that has result output.
2. **Given** `cli.py`, **When** it is inspected, **Then** it imports presenters from `cli_presenters` and calls them after `_handle_command()` returns a non-None result.

---

### Edge Cases

- What happens when a result object is `None` (runner returned nothing)? Presenter functions must not be called; guard remains in the command body.
- What happens when a result has optional fields that may be absent (`getattr` access patterns)? Presenters must preserve existing defensive `getattr()` calls.
- What happens when a command raises `typer.Exit(code=1)` based on result content (e.g., `sync-prompts` on conflict)? Exit code decisions that depend on result content remain in the command body after the presenter call, not inside the presenter.
- What happens when a command has intermediate console output before the final result (e.g., `run` mixed-variant confirmation prompt)? Interactive prompts stay in the command body; only post-result presentation moves to the presenter.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A `cli_presenters.py` module MUST be created in `src/evaluator_harness/` containing one presenter function per command that currently has inline `console.print()` result output.
- **FR-002**: Each presenter function MUST accept exactly two parameters: the result object and a `Console` instance (`result, console`). No additional CLI-level parameters (like `baseline`, `skip_sync`) are permitted; context needed for output MUST be included in the result object by the runner.
- **FR-003**: The `run` command body MUST NOT contain `console.print()` calls inside its `if result is not None:` block; all output MUST be delegated to `present_run_result()`.
- **FR-004**: The `campaign` command body MUST NOT contain `console.print()` calls inside its `if result is not None:` block; all output MUST be delegated to `present_campaign_result()`.
- **FR-005**: The `sync-prompts` command body MUST NOT contain `console.print()` calls inside its `if result is not None:` block; output MUST be delegated to `present_sync_prompts_result()`.
- **FR-006**: The `sync-all` command body MUST NOT contain `console.print()` calls inside its `if result is not None:` block; output MUST be delegated to `present_sync_all_result()`.
- **FR-007**: The `validate`, `sync-dataset`, `sync-score-configs`, `sync-annotation-queue`, `render-judge-prompts`, `export`, `select-review`, `sync-judge-evaluators`, `comparison-report`, and `excel-report` command bodies MUST similarly delegate their result output to presenter functions.
- **FR-008**: The existing `_print_comparison_report_outputs()` and `_print_judge_setup_result()` helpers in `cli.py` MUST be relocated to `cli_presenters.py` and renamed following the `present_*` convention.
- **FR-009**: Exit code decisions (e.g., `raise typer.Exit(code=1)`) MUST remain in the command body and MUST NOT be moved inside presenter functions.
- **FR-010**: Interactive console prompts (e.g., mixed-variant confirmation in `run`) MUST remain in the command body and MUST NOT be moved to presenter functions.
- **FR-011**: The `cli_presenters.py` module MUST be tested via unit tests that construct result objects directly and assert on captured output, without invoking the Typer CLI runner.
- **FR-012**: All existing CLI command tests MUST continue to pass without modification; the refactor MUST be behavior-preserving.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 12+ Typer command bodies in `cli.py` contain zero `console.print()` calls inside their `if result is not None:` result-presentation blocks after the refactor.
- **SC-002**: A new `cli_presenters.py` module exists with one presenter function per command group that has output.
- **SC-003**: All existing non-live tests continue to pass (currently 610 passing).
- **SC-004**: At least one unit test exists per presenter function that validates output directly without CLI invocation.
- **SC-005**: No behavioral change to any CLI command's output as observed by end-to-end CLI runner tests.

## Clarifications

### Session 2026-06-23

- Q: Should presenter functions be allowed to accept additional parameters beyond `result` and `console`? → A: No. All presenters use uniform signature `(result, console)`. Commands that need context from CLI parameters (e.g., `baseline` in `comparison-report`) must pass that context through the result object returned by the runner, ensuring result objects are self-contained.

## Assumptions

- This refactor is behavior-preserving only; no new CLI output or changed formatting is in scope.
- The `Console` instance is passed as a parameter to presenter functions (not retrieved via a global) to allow easy test injection.
- Result objects are self-contained: all data needed for presentation (including values derived from CLI parameters) is included in the result object, not passed separately to the presenter.
- Progress callbacks (e.g., `on_run_start` in campaign) are not considered "result presentation" and remain inline.
- The `export_evaluator_setup` command's trivial single-line result (`console.print(f"export: {result}")`) will still receive its own presenter for consistency, even if minimal.
- The `_handle_command()` helper and error/exit-code logic in `cli.py` are out of scope for this refactor.
