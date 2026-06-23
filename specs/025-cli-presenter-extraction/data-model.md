# Data Model: CLI Presenter Extraction

## Overview

This feature introduces a presentation layer model for CLI command results while preserving existing command orchestration and exit behavior.

## Entity: PresenterFunction

Represents a pure output function that renders one command result shape.

Fields and invariants:

- `name`: Canonical function name following `present_<command>_result`.
- `input_result`: The result object returned from runner or service call.
- `console`: A Rich `Console` instance supplied by command code.
- `side_effects`: Console output only (no file writes, network calls, or exits).

Validation rules:

- Must accept exactly two parameters: `(result, console)`.
- Must not raise `typer.Exit`.
- Must preserve existing output ordering and labels.

## Entity: PresentationPayload

Represents the effective data consumed by a presenter.

Fields:

- `core_result`: Existing command result object (run result, sync result, report result, etc.).
- `derived_display_fields`: Additional display fields that originate from command options but are embedded in the result payload before presentation.

Validation rules:

- Payload must be self-contained for rendering.
- Presenter must not require command-local variables outside `result`.

## Entity: CommandOrchestrationBlock

Represents the minimal command body control flow retained in `cli.py`.

Fields:

- `option_parsing`: Typer option parsing and input preparation.
- `invocation`: `_handle_command(...)` runner/service call.
- `interaction`: optional user prompt/confirmation before invocation.
- `presentation_call`: single presenter invocation for non-None result.
- `exit_policy`: command-owned `typer.Exit(...)` logic.

Validation rules:

- No inline result rendering in the post-result block.
- Interactive prompts remain before result presentation.
- Exit decisions remain in command code after presentation call when needed.

## Relationships

- One `CommandOrchestrationBlock` invokes zero or one `PresenterFunction` per execution path.
- One `PresenterFunction` renders one `PresentationPayload` type.
- Multiple command functions may share a presenter when output format is intentionally identical.

## State Transitions

```text
command-entered -> result-produced -> presented -> exit-decided -> command-complete
```

Alternative path:

```text
command-entered -> prompt-cancelled -> error-raised -> command-complete
```

## Compatibility Constraints

- Existing CLI command names and options remain unchanged.
- Existing output text semantics remain unchanged.
- Existing test fixtures for command behavior remain valid.
