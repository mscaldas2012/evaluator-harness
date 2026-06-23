# Implementation Plan: CLI Presenter Extraction

**Branch**: `025-cli-presenter-extraction` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/025-cli-presenter-extraction/spec.md`

## Summary

Refactor `src/evaluator_harness/cli.py` so Typer command bodies remain thin and delegate result rendering to a dedicated presenter module. The implementation introduces `src/evaluator_harness/cli_presenters.py`, moves command-specific `console.print(...)` output logic into `present_*` functions, preserves command exit-code decisions in command bodies, and adds focused presenter unit tests. Output behavior remains unchanged.

## Technical Context

**Language/Version**: Python 3.12 project standard

**Primary Dependencies**: Typer CLI, Rich `Console`, pytest, existing evaluator harness result models and command return types

**Python Environment Management**: Use `uv` for environment management, dependency setup, lockfile management, and command execution. Prefer `uv sync` and `uv run ...`.

**Storage**: N/A (no new persistence; file-only code refactor)

**Testing**: pytest (unit + contract/integration regression checks)

**Target Platform**: Local CLI execution on developer machines

**Project Type**: Python CLI/library package

**Performance Goals**: No measurable runtime regression; constant-time function delegation only

**Constraints**: Preserve user-visible CLI output and exit semantics; presenter signatures are uniform `(result, console)` only; no command-level formatting regressions

**Scale/Scope**: Focused CLI-layer refactor touching `src/evaluator_harness/cli.py`, new `src/evaluator_harness/cli_presenters.py`, and related tests under `tests/unit` and selected CLI contract tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature only reorganizes CLI presentation code and does not replace or bypass Langfuse functionality.
- **Thin harness scope**: PASS. This is a local Python CLI refactor that reduces command complexity.
- **Dataset simplicity**: PASS. No dataset schema or loading changes.
- **Reproducibility metadata**: PASS. No run metadata collection or logging changes.
- **Baseline-centric workflow**: PASS. Baseline and candidate workflow behavior remains unchanged.
- **Minimal local state**: PASS. No new state mechanisms introduced.
- **Human review awareness**: PASS. Existing human-review selection and output remain unchanged.
- **Local-first execution**: PASS. Verification and use remain local via `uv run ...`.

## Project Structure

### Documentation (this feature)

```text
specs/025-cli-presenter-extraction/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- cli-presentation-contract.md
|-- checklists/
|   `-- requirements.md
`-- tasks.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
|-- cli.py                            # command orchestration, option parsing, exit decisions
`-- cli_presenters.py                 # new presentation-only functions

tests/
|-- unit/
|   `-- test_cli_presenters.py        # new presenter-focused output tests
|-- contract/
|   `-- test_cli_project_env_files.py # existing command behavior regression coverage
`-- integration/
    `-- test_run_baseline.py          # existing workflow regression coverage
```

**Structure Decision**: Keep existing single-project Python CLI layout. Introduce one dedicated presenter module to centralize output formatting while retaining command orchestration in `cli.py`.

## Complexity Tracking

No constitution violations are introduced.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Phase 0: Research Summary

See [research.md](research.md). Decisions:

- Use a dedicated `cli_presenters.py` boundary with one `present_*` function per command output group.
- Enforce uniform presenter signatures: `(result, console)` only.
- Keep `typer.Exit(...)` decisions and interactive prompts in command bodies.
- Preserve CLI output behavior by asserting parity with focused presenter unit tests plus existing CLI tests.
- Carry command-derived presentation values via result objects (or enriched return objects from called APIs) rather than extra presenter parameters.

## Phase 1: Design Summary

See [data-model.md](data-model.md) and [contracts/cli-presentation-contract.md](contracts/cli-presentation-contract.md).

The design defines:

- presenter input/output entities and invariants;
- command-to-presenter mapping and ownership boundaries;
- enriched result payload requirement for self-contained presentation context;
- parity and non-regression validation strategy.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Langfuse integrations and metadata flows are untouched.
- **Thin harness scope**: PASS. Command bodies become smaller; no new architecture layers beyond one local module.
- **Dataset simplicity**: PASS. No changes.
- **Reproducibility metadata**: PASS. No changes.
- **Baseline-centric workflow**: PASS. No changes.
- **Minimal local state**: PASS. No changes.
- **Human review awareness**: PASS. No changes.
- **Local-first execution**: PASS. Local `uv run` workflow remains unchanged.

## Verification Plan

1. Run new presenter unit tests:
   `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_cli_presenters.py -vv`
2. Run core CLI regression coverage:
   `uv run pytest --no-cov -p no:cacheprovider tests/contract/test_cli_project_env_files.py -vv`
3. Run focused integration sanity checks for run/campaign paths:
   `uv run pytest --no-cov -p no:cacheprovider tests/integration/test_run_baseline.py -vv`
4. Run broad non-live suite before merge:
   `uv run pytest --no-cov -p no:cacheprovider -m "not live"`
5. Run lint/type checks for touched files:
   `uv run ruff check src/evaluator_harness/cli.py src/evaluator_harness/cli_presenters.py tests/unit/test_cli_presenters.py --no-cache`
   `uv run pyright src/evaluator_harness/cli.py src/evaluator_harness/cli_presenters.py`
6. Refresh code graph after implementation:
   `graphify update .`
