# Implementation Plan: Project-Specific Environment Files

**Branch**: `016-project-env-files` | **Date**: 2026-06-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/016-project-env-files/spec.md`

## Summary

Load project-specific environment files for project-scoped harness commands.
The implementation will keep root `.env` as the shared fallback, overlay
`.env.<project-name>` for the active project, and preserve pre-existing shell
environment variables as the highest-priority source. The change stays in the
existing local CLI/config loading path and does not alter project YAML secret
handling.

## Technical Context

**Language/Version**: Python >=3.11

**Primary Dependencies**: Pydantic, Typer, Rich, PyYAML, pytest; existing
Langfuse/OpenAI/Azure dependencies remain unchanged

**Python Environment Management**: Use `uv` for environment management,
dependency setup, lockfile management, and command execution. Prefer `uv sync`
and `uv run ...`.

**Storage**: Local `.env` and `.env.<project-name>` files only; no database or
new durable local state

**Testing**: pytest unit, integration, and CLI contract tests

**Target Platform**: Local CLI execution on developer machines

**Project Type**: Python CLI evaluation harness

**Performance Goals**: Environment resolution should add no noticeable delay to
project commands; loading two small environment files should complete within
normal command startup time.

**Constraints**: Preserve shell environment override behavior; do not print or
commit secret values; do not require project-specific env files; avoid changing
dataset, run, evaluator, or Langfuse logging semantics.

**Scale/Scope**: Applies to project-scoped commands that load a project config:
validate, sync, setup, run, review, export, and helper commands that render or
describe project artifacts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. This feature only changes local credential/settings
  resolution before existing Langfuse operations. Langfuse remains the system
  of record for traces, evaluator scores, dashboards, and comparison.
- **Thin harness scope**: PASS. The design stays in local file loading and
  existing CLI/config code. No services, schedulers, APIs, or orchestration are
  introduced.
- **Dataset simplicity**: PASS. Dataset formats and CSV `input` behavior are
  unchanged.
- **Reproducibility metadata**: PASS. Run metadata is unchanged. Secret values
  remain excluded from project config, traces, exports, and errors.
- **Baseline-centric workflow**: PASS. Baseline creation, lookup, reuse, and
  candidate comparison behavior are unchanged.
- **Minimal local state**: PASS. No new durable state is added. Optional local
  env files are existing filesystem-style configuration inputs.
- **Human review awareness**: PASS. Human Annotation Queue behavior is
  unchanged, while queue-related environment values can come from the
  project-specific env file.
- **Local-first execution**: PASS. Feature works with existing
  `uv run python run_experiment.py ...` commands.

## Project Structure

### Documentation (this feature)

```text
specs/016-project-env-files/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- env-resolution-contract.md
|-- checklists/
|   `-- requirements.md
`-- spec.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
|-- config.py      # env-file loading, precedence, project config loading hooks
|-- runner.py      # project-scoped command entry points/load timing
`-- cli.py         # CLI command paths that construct runners or validate projects

tests/
|-- unit/
|   `-- test_live_settings.py
|-- integration/
|   `-- test_project_env_files.py
`-- contract/
    `-- test_cli_project_env_files.py
```

**Structure Decision**: Use the existing single Python CLI structure. Keep the
change close to `config.py` and `runner.py`; add focused tests for precedence,
missing-file behavior, and CLI project command behavior.

## Complexity Tracking

No constitution violations.

## Phase 0: Research

See [research.md](research.md).

## Phase 1: Design And Contracts

See [data-model.md](data-model.md), [contracts/env-resolution-contract.md](contracts/env-resolution-contract.md), and [quickstart.md](quickstart.md).

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Env resolution feeds existing Langfuse client and
  provider setup but does not replace Langfuse capabilities.
- **Thin harness scope**: PASS. The design is a small deterministic loader
  change and test coverage, not a secret-management subsystem.
- **Dataset simplicity**: PASS. No dataset behavior changes.
- **Reproducibility metadata**: PASS. Secret values remain outside metadata;
  only variable names continue to appear in config/errors.
- **Baseline-centric workflow**: PASS. No baseline semantics change.
- **Minimal local state**: PASS. Optional env files are local inputs, not a new
  state store.
- **Human review awareness**: PASS. Review queue settings can resolve through
  the same env layering without changing review workflows.
- **Local-first execution**: PASS. Verified design remains local CLI driven via
  `uv run`.
