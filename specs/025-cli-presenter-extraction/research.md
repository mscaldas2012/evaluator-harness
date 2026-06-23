# Research: CLI Presenter Extraction

## Decision 1: Introduce a dedicated presenter module

- Decision: Create `src/evaluator_harness/cli_presenters.py` and move command result rendering logic there.
- Rationale: Centralizing presentation removes formatting noise from command bodies and gives one discoverable location for output behavior.
- Alternatives considered:
  - Keep helper functions in `cli.py`: rejected because command and presentation concerns remain mixed.
  - One presenter class with mutable state: rejected as unnecessary complexity for mostly stateless formatting logic.

## Decision 2: Enforce uniform presenter signature

- Decision: All presenter functions accept exactly `(result, console)`.
- Rationale: A single function contract simplifies tests, reviewer expectations, and future command additions.
- Alternatives considered:
  - Per-presenter custom parameters: rejected because signatures become inconsistent and couple presenters to command options.
  - Global module-level console usage: rejected because it harms test isolation and dependency injection.

## Decision 3: Keep command responsibilities explicit

- Decision: Command bodies keep only parameter parsing, project resolution, runner/service invocation, interactive prompts, and `typer.Exit(...)` decisions.
- Rationale: Exit-code policy and interactive confirmation are command control-flow concerns, not presentation concerns.
- Alternatives considered:
  - Move exit decisions into presenters: rejected because it conflates display with process control.
  - Move prompts into presenters: rejected because prompts affect execution path before result existence.

## Decision 4: Make presenter inputs self-contained

- Decision: Any data needed for output must be present in the result object passed to a presenter, including values originating from command flags.
- Rationale: Preserves the `(result, console)` contract and avoids hidden dependencies on command-local variables.
- Alternatives considered:
  - Pass extra arguments (for example `baseline`) to presenters: rejected by feature clarification.
  - Let presenters read global state or re-open config: rejected due to brittleness and test complexity.

## Decision 5: Validate behavior parity with layered tests

- Decision: Add focused presenter unit tests for line-level output while retaining existing contract/integration tests for CLI behavior.
- Rationale: Unit tests reduce brittleness for formatting checks; existing CLI tests ensure no behavior drift in command orchestration.
- Alternatives considered:
  - CLI-runner-only tests: rejected because they are slower and harder to maintain for pure formatting assertions.
  - Snapshot-only testing: rejected because broad snapshots are noisy and obscure intent for targeted output lines.
